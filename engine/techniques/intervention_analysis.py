"""
Intervention Analysis using ARIMA with intervention dummies for Time Series Lab.

Models the impact of known interventions (events, policy changes, shocks) on
a time series by incorporating dummy variables into an ARIMA model.

Supports three types of intervention effects:
- Pulse (temporary): a one-time shock at the intervention point.
- Step (permanent level shift): a permanent shift starting at the intervention.
- Ramp (gradual): a linearly increasing effect starting at the intervention.

The model is: Y_t = ARIMA(p,d,q) + sum_i(omega_i * D_i(t)) + eps_t
where D_i(t) are intervention dummy variables.
"""

import re

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"auto_order": False, "default_order": (1, 1, 1), "max_pq": 3},
    "Balanced": {"auto_order": True,  "default_order": (1, 1, 1), "max_pq": 5},
    "Thorough": {"auto_order": True,  "default_order": (1, 1, 1), "max_pq": 7},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Intervention analysis with ARIMA + intervention dummies.

    Parameters (via ctx.params)
    ---------------------------
    interventions : list[dict], required
        List of intervention specifications. Each dict has:
        - 'index' or 'time': position of the intervention.
        - 'type': 'pulse', 'step', or 'ramp'.
        - 'name': optional label.
        Example: [{"index": 50, "type": "step", "name": "Policy Change"}]
    order : list[int], optional
        ARIMA order [p, d, q]. If omitted, auto-selected.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Handle NaN
        nan_mask = np.isnan(values)
        if np.any(nan_mask):
            # Interpolate
            filled = values.copy()
            nans = np.where(nan_mask)[0]
            valid = np.where(~nan_mask)[0]
            if len(valid) < 10:
                return make_error_response(
                    ctx,
                    "Too few non-missing values for intervention analysis.",
                    error_fixes=["Provide a series with fewer missing values."],
                )
            filled[nans] = np.interp(nans, valid, values[valid])
            warnings.append(f"{len(nans)} missing values linearly interpolated.")
        else:
            filled = values.copy()

        n = len(filled)

        # Parse interventions. Precedence: an explicit `interventions` list
        # (UDF / programmatic back-compat) > the flat dialog inputs
        # (intervention_dates + intervention_type) > auto-detect.
        # F-CP-INT-WIRE: the dialog's flat date/type inputs were previously never
        # read (the engine always auto-detected, silently ignoring user-specified
        # interventions); they are now translated into the interventions list here
        # and fed to the existing _parse_interventions (which already resolves a
        # 'time' date against the time column or an integer 'index').
        interventions_raw = ctx.get_param("interventions")
        if interventions_raw is None or not isinstance(interventions_raw, list) or len(interventions_raw) == 0:
            dates_param = ctx.get_param("intervention_dates")
            if dates_param is not None and str(dates_param).strip():
                itype = str(ctx.get_param("intervention_type", "step")).strip().lower()
                interventions_raw = []
                for j, tok in enumerate(str(dates_param).split(",")):
                    tok = tok.strip()
                    if not tok:
                        continue
                    spec = {"type": itype, "name": f"Intervention {j + 1}"}
                    # An integer token is an observation position; anything else is
                    # a date matched against the time column by _parse_interventions.
                    if re.fullmatch(r"-?\d+", tok):
                        spec["index"] = int(tok)
                    else:
                        spec["time"] = tok
                    interventions_raw.append(spec)
            else:
                # No interventions specified -> auto-detect a single structural break.
                warnings.append(
                    "No interventions specified. Auto-detecting a single structural break point."
                )
                interventions_raw = [_auto_detect_intervention(filled, ctx.time)]

        interventions = _parse_interventions(interventions_raw, n, ctx.time)

        if len(interventions) == 0:
            return make_error_response(
                ctx,
                "No valid intervention points found.",
                error_fixes=[
                    "Provide interventions as a list of {index, type, name} dicts.",
                    "Ensure intervention indices are within the series range.",
                ],
            )

        if n < 30:
            return make_error_response(
                ctx,
                f"Only {n} observations. Intervention analysis needs at least 30.",
                error_fixes=["Provide a longer series."],
            )

        progress_callback("Building intervention dummies", 15)

        # CAI Phase 2 Session 15 fix (F-CP-INT-TYPE): explicit
        # allowlist gate. Pre-fix, invalid intervention `type`
        # strings fell through the if/elif/else chain to a silent
        # coercion to "step" (with a warning). The audit_fields
        # `interventions` list still recorded the user's invalid
        # type, misrepresenting the model that actually ran.
        # Now: any unknown type returns make_error_response with
        # the allowlist enumerated.
        _INTERVENTION_TYPE_OPTS = ("pulse", "step", "ramp")
        for i, intv in enumerate(interventions):
            itype = intv.get("type")
            if itype not in _INTERVENTION_TYPE_OPTS:
                iname = intv.get("name", f"Intervention_{i+1}")
                return make_error_response(
                    ctx,
                    f"Unknown intervention type '{itype}' for "
                    f"{iname}. Must be one of: "
                    f"{', '.join(_INTERVENTION_TYPE_OPTS)}.",
                    error_fixes=[
                        "Use 'pulse' (one-time shock at the "
                        "intervention index), 'step' (permanent "
                        "level shift starting at the index), or "
                        "'ramp' (linearly increasing effect from "
                        "the index onward).",
                    ],
                )

        # Build dummy variables
        X_interventions = np.zeros((n, len(interventions)))
        dummy_names = []

        for i, intv in enumerate(interventions):
            idx = intv["index"]
            itype = intv["type"]
            iname = intv.get("name", f"Intervention_{i+1}")

            if itype == "pulse":
                X_interventions[idx, i] = 1.0
                dummy_names.append(f"{iname} (pulse@{idx})")
            elif itype == "step":
                X_interventions[idx:, i] = 1.0
                dummy_names.append(f"{iname} (step@{idx})")
            else:  # itype == "ramp" (allowlist guarantees this)
                for t in range(idx, n):
                    X_interventions[t, i] = t - idx + 1
                dummy_names.append(f"{iname} (ramp@{idx})")

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Determine ARIMA order
        order_param = ctx.get_param("order")
        if order_param is not None and isinstance(order_param, (list, tuple)) and len(order_param) == 3:
            order = tuple(int(v) for v in order_param)
        elif cfg["auto_order"]:
            progress_callback("Auto-selecting ARIMA order", 25)
            order = _auto_select_order(filled, X_interventions, cfg["max_pq"])
        else:
            order = cfg["default_order"]

        progress_callback(f"Fitting ARIMA{order} with interventions", 40)

        # Fit ARIMA with exogenous intervention dummies
        try:
            from statsmodels.tsa.arima.model import ARIMA

            model = ARIMA(filled, order=order, exog=X_interventions)
            fit = model.fit()
        except Exception as fit_err:
            # Fallback: try simpler order
            warnings.append(f"ARIMA{order} failed ({fit_err}). Trying (1,0,0).")
            try:
                order = (1, 0, 0)
                model = ARIMA(filled, order=order, exog=X_interventions)
                fit = model.fit()
            except Exception as fit_err2:
                return make_error_response(
                    ctx,
                    f"ARIMA fitting failed: {fit_err2}",
                    error_fixes=[
                        "Try specifying a simpler order (e.g., [1,0,0]).",
                        "Check for non-numeric data or extreme values.",
                    ],
                )

        progress_callback("Extracting intervention effects", 65)

        # Extract intervention coefficients
        # In statsmodels ARIMA with exog, the exog coefficients come after ARIMA params
        params = fit.params
        bse = fit.bse
        pvalues = fit.pvalues
        conf_int = fit.conf_int()

        # Identify exog parameter positions
        # The parameter names in statsmodels include exog names
        param_names = list(fit.param_names) if hasattr(fit, 'param_names') else [f"x{i}" for i in range(len(params))]

        # Find exogenous variable parameters
        # They are typically named x1, x2, etc., or the custom names
        n_exog = X_interventions.shape[1]
        exog_start = len(params) - n_exog

        intv_rows = []
        significant_effects = []

        for i in range(n_exog):
            pidx = exog_start + i
            coef = float(params[pidx])
            se = float(bse[pidx])
            pval = float(pvalues[pidx])
            ci = conf_int[pidx]
            t_stat = coef / se if se > 0 else 0

            is_sig = pval < 0.05
            if is_sig:
                significant_effects.append((dummy_names[i], coef, pval))

            intv_rows.append([
                dummy_names[i],
                round(coef, 6),
                round(se, 6),
                round(t_stat, 4),
                round(pval, 6),
                round(float(ci[0]), 6),
                round(float(ci[1]), 6),
                "Yes" if is_sig else "No",
            ])

        intv_table = make_table(
            "Intervention Effects",
            ["Intervention", "Coefficient", "Std Error", "t-stat", "p-value",
             "CI 2.5%", "CI 97.5%", "Significant"],
            intv_rows,
        )

        # ARIMA parameters
        arima_rows = []
        for i in range(exog_start):
            arima_rows.append([
                param_names[i] if i < len(param_names) else f"param_{i}",
                round(float(params[i]), 6),
                round(float(bse[i]), 6),
                round(float(pvalues[i]), 6),
            ])

        arima_table = make_table(
            f"ARIMA{order} Parameters",
            ["Parameter", "Estimate", "Std Error", "p-value"],
            arima_rows,
        )

        # Model diagnostics
        resid = fit.resid
        aic = float(fit.aic)
        bic = float(fit.bic)

        # Ljung-Box on residuals
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox
            lb_result = acorr_ljungbox(resid, lags=[10], return_df=True)
            lb_stat = float(lb_result.iloc[0]["lb_stat"])
            lb_pval = float(lb_result.iloc[0]["lb_pvalue"])
        except Exception:
            lb_stat = None
            lb_pval = None

        # Jarque-Bera
        jb_stat, jb_pval = sp_stats.jarque_bera(resid)

        diag_rows = [
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["Residual std", round(float(np.std(resid)), 6)],
            ["Ljung-Box Q(10)", round(lb_stat, 4) if lb_stat is not None else "N/A"],
            ["Ljung-Box p-value", round(lb_pval, 6) if lb_pval is not None else "N/A"],
            ["Jarque-Bera", round(float(jb_stat), 4)],
            ["Jarque-Bera p-value", round(float(jb_pval), 6)],
        ]
        diag_table = make_table("Model Diagnostics", ["Metric", "Value"], diag_rows)

        progress_callback("Building fitted values table", 85)

        # Fitted values and counterfactual (without interventions)
        fitted = fit.fittedvalues
        # Counterfactual: fitted values minus intervention effects
        intervention_effect = X_interventions @ params[exog_start:]
        counterfactual = fitted - intervention_effect

        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        max_display = 500
        step_ts = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step_ts):
            ts_rows.append([
                time_col[i],
                round(float(filled[i]), 6),
                round(float(fitted[i]), 6),
                round(float(counterfactual[i]), 6),
                round(float(intervention_effect[i]), 6),
                round(float(resid[i]), 6),
            ])

        ts_table = make_table(
            "Fitted Values & Counterfactual",
            ["Time", "Actual", "Fitted", "Counterfactual", "Intervention Effect", "Residual"],
            ts_rows,
        )

        # Plain English
        n_sig = len(significant_effects)
        plain_english = (
            f"Intervention analysis of '{name}' ({n} observations) using "
            f"ARIMA{order} with {len(interventions)} intervention(s). "
        )

        if n_sig == 0:
            plain_english += "No interventions have a statistically significant effect at 5% level."
        else:
            plain_english += f"{n_sig} intervention(s) have significant effects: "
            parts = []
            for iname, coef, pval in significant_effects:
                direction = "positive" if coef > 0 else "negative"
                parts.append(f"{iname} ({direction}, coef={coef:.4f}, p={pval:.4f})")
            plain_english += "; ".join(parts) + "."

        if lb_pval is not None and lb_pval < 0.05:
            warnings.append(
                "Ljung-Box test indicates residual autocorrelation. "
                "Consider a higher ARIMA order."
            )

        charting = (
            "Time series chart showing actual values, fitted values, and counterfactual "
            "(what would have happened without interventions) as lines. "
            "Vertical dashed lines at intervention points. "
            "Shade the area between fitted and counterfactual to show intervention effect. "
            "Include a residual subplot."
        )

        progress_callback("Done", 100)

        # Additional compute for the interpretation spec:
        # - series_std on the filled series for scale reference
        # - aic_no_intervention: refit ARIMA without intervention dummies
        _series_std = float(np.std(filled)) if len(filled) > 0 else None
        _aic_no_intervention = None
        try:
            _no_int_fit = ARIMA(filled, order=order).fit()
            _aic_no_intervention = float(_no_int_fit.aic)
        except Exception:
            _aic_no_intervention = None

        # Pick the top intervention (largest absolute effect) for Tier 1.
        _top_idx = None
        _top_abs = -1.0
        for i, row in enumerate(intv_rows):
            c = row[1]
            if c is None:
                continue
            if abs(float(c)) > _top_abs:
                _top_abs = abs(float(c))
                _top_idx = i
        _top_date = None
        _top_label = None
        _top_coef = None
        _top_p = None
        _top_ci_lo = None
        _top_ci_hi = None
        if _top_idx is not None:
            # Strip the raw "(type@index)" annotation from the display
            # label so the interpretation layer shows the user-friendly
            # name (e.g., "COVID shock"). The resolved date is attached
            # separately below.
            import re as _re_label
            _raw_label = str(intv_rows[_top_idx][0])
            _top_label = _re_label.sub(
                r"\s*\([^)]*@\d+\)\s*$", "", _raw_label
            ).strip()
            # Resolve the intervention's display date. FIX 2: previously
            # fell back to the raw integer index ("intervention on 262")
            # because the parsed intervention dict only carries `index`.
            # Look up the corresponding date in ctx.time and format via
            # the frequency-aware helper so user-facing text reads
            # "2020-Q1" / "2020-03" / etc.
            if _top_idx < len(interventions):
                iv = interventions[_top_idx]
                if isinstance(iv, dict):
                    _iv_idx = iv.get("index")
                    _iv_date_raw = iv.get("date")
                    if _iv_date_raw is not None:
                        _top_date = str(_iv_date_raw)
                    elif (
                        _iv_idx is not None
                        and ctx.time
                        and 0 <= int(_iv_idx) < len(ctx.time)
                    ):
                        try:
                            from interpretation.primitives import format_break_date
                            _top_date = format_break_date(
                                ctx.time[int(_iv_idx)],
                                ctx.frequency or "",
                            )
                        except Exception:
                            _top_date = str(ctx.time[int(_iv_idx)])
                    elif _iv_idx is not None:
                        _top_date = f"index {int(_iv_idx)}"
            _top_coef = intv_rows[_top_idx][1]
            _top_p = intv_rows[_top_idx][4]
            _top_ci_lo = intv_rows[_top_idx][5]
            _top_ci_hi = intv_rows[_top_idx][6]

        interp = build_interpretation("intervention_analysis", {
            "series_name": name,
            "n_interventions": int(len(interventions)),
            "n_significant": int(n_sig),
            "top_intervention_date": _top_date,
            "top_intervention_label": _top_label,
            "top_intervention_coef": _top_coef,
            "top_intervention_p_value": _top_p,
            "top_intervention_ci_lower": _top_ci_lo,
            "top_intervention_ci_upper": _top_ci_hi,
            "series_std": _series_std,
            "arima_order": list(order),
            "ljung_box_p_value": lb_pval,
            "aic": float(aic),
            "aic_no_intervention": _aic_no_intervention,
        })
        return make_response(
            ctx,
            tables=[intv_table, arima_table, diag_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "arima_order": list(order),
                "n_interventions": len(interventions),
                "interventions": interventions,
                "n_significant": n_sig,
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "n_obs": n,
                **format_significance_disclosure(
                    test_name=(
                        "ARIMA-intervention MLE t-tests on intervention "
                        "coefficients"
                    ),
                    critical_value_formula=(
                        "statsmodels ARIMA standard errors via MLE hessian; "
                        "two-sided t-tests at α; no HAC/Newey-West correction "
                        "applied — intervention SE assumes the ARIMA errors "
                        "are white noise"
                    ),
                    ac_corrected=False,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Intervention analysis failed: {e}",
            error_fixes=[
                "Ensure interventions are provided as a list of dicts with 'index' and 'type'.",
                "Try specifying a simpler ARIMA order.",
                "Check that intervention indices are within the data range.",
            ],
        )


def _parse_interventions(raw_list, n, time_col):
    """Parse intervention specifications into standardized format."""
    interventions = []

    for i, item in enumerate(raw_list):
        if not isinstance(item, dict):
            continue

        idx = item.get("index")
        time_val = item.get("time")
        itype = item.get("type", "step").lower()
        iname = item.get("name", f"Intervention_{i+1}")

        if idx is not None:
            idx = int(idx)
        elif time_val is not None and time_col:
            # Try to find matching time
            for j, t in enumerate(time_col):
                if str(t) == str(time_val):
                    idx = j
                    break

        if idx is None or idx < 0 or idx >= n:
            continue

        interventions.append({
            "index": idx,
            "type": itype,
            "name": iname,
        })

    return interventions


def _auto_detect_intervention(data, time_col):
    """
    Auto-detect a single structural break point using maximum CUSUM statistic.
    Returns an intervention dict.
    """
    n = len(data)
    mu = np.mean(data)
    cusum = np.cumsum(data - mu)

    # Find the point of maximum absolute CUSUM
    break_idx = int(np.argmax(np.abs(cusum)))

    # Determine if it's more like a step or pulse
    mean_before = np.mean(data[:break_idx]) if break_idx > 0 else mu
    mean_after = np.mean(data[break_idx:]) if break_idx < n else mu
    shift = abs(mean_after - mean_before)
    point_dev = abs(data[break_idx] - mu)

    itype = "step" if shift > 1.5 * np.std(data) else "pulse"

    return {
        "index": break_idx,
        "type": itype,
        "name": "Auto-detected break",
    }


def _auto_select_order(data, exog, max_pq):
    """Auto-select ARIMA order using AIC."""
    from statsmodels.tsa.arima.model import ARIMA

    best_aic = np.inf
    best_order = (1, 0, 0)

    for d in [0, 1]:
        for p in range(0, min(max_pq + 1, 4)):
            for q in range(0, min(max_pq + 1, 4)):
                if p == 0 and q == 0 and d == 0:
                    continue
                try:
                    model = ARIMA(data, order=(p, d, q), exog=exog)
                    fit = model.fit()
                    if fit.aic < best_aic:
                        best_aic = fit.aic
                        best_order = (p, d, q)
                except Exception:
                    continue

    return best_order
