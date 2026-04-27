"""
KPSS stationarity test for Time Series Lab.

The KPSS null hypothesis is that the series IS stationary (around a constant
or around a linear trend). Rejecting the null suggests the series is
non-stationary — which is the opposite orientation of ADF (whose null is
the presence of a unit root). When used together with ADF + PP, the joint
verdict under the ``adf_test`` triage path is more conclusive than any
single test alone.

This wrapper exposes ``_run_kpss_single(clean, regression, nlags)`` for the
triage path in ``adf_test.py`` to call directly, bypassing the per-series
progress-callback / response-building overhead.
"""

import warnings as _warnings
import numpy as np
from statsmodels.tsa.stattools import kpss

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
    order_critical_values,
)


_REGRESSION_LABEL = {
    "c":  "level stationarity",
    "ct": "trend stationarity",
}


def _prepare_series(values: np.ndarray, name: str, warnings: list) -> np.ndarray:
    """Strip edge NaN and linearly interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([])
    trimmed = values[first_valid:last_valid + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
            warnings.append(
                f"'{name}': {nan_count} interior NaN values linearly "
                "interpolated for KPSS test."
            )
        else:
            return trimmed[~np.isnan(trimmed)]
    return trimmed


def _run_kpss_single(clean: np.ndarray, regression: str, nlags):
    """Run KPSS on one prepared series. Returns a raw-results dict.

    Keys:
        stat, pvalue, used_lag, critical_values_ordered (list of
        (level, value, rejects_H0) tuples — note KPSS rejects when
        stat > CV, not <), regression, regression_label, nlags_rule,
        decision_h0_rejected, error (str or None), pvalue_clipped (bool:
        True when statsmodels reports the p-value at a boundary).
    """
    out = {
        "stat": None, "pvalue": None, "used_lag": None,
        "critical_values_ordered": [], "regression": regression,
        "regression_label": _REGRESSION_LABEL.get(regression, regression),
        "nlags_rule": nlags, "decision_h0_rejected": None,
        "error": None, "pvalue_clipped": False,
    }
    n = len(clean)
    if n < 12:
        out["error"] = f"Too few observations ({n}; need ≥ 12)"
        return out
    try:
        with _warnings.catch_warnings(record=True) as caught:
            _warnings.simplefilter("always")
            kpss_stat, p_value, used_lags, crit_vals = kpss(
                clean, regression=regression, nlags=nlags,
            )
            for w in caught:
                msg = str(w.message).lower()
                if "p-value" in msg or "p value" in msg:
                    out["pvalue_clipped"] = True
    except Exception as e:
        out["error"] = str(e)
        return out
    ordered = order_critical_values(crit_vals)
    out["stat"] = float(kpss_stat)
    out["pvalue"] = (float(p_value) if p_value is not None else None)
    out["used_lag"] = int(used_lags)
    # KPSS rejects H0 (stationarity) when stat > critical value.
    out["critical_values_ordered"] = [
        (lvl, cv, kpss_stat > cv) for (lvl, cv) in ordered
    ]
    return out


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the KPSS stationarity test on one or more series.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        'c' for level stationarity (default), 'ct' for trend stationarity.
    nlags : int or str, optional
        Bandwidth rule: 'auto' (default, data-driven), 'legacy', or integer.
    significance_level : float, optional
        P-value threshold. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        all_series = ctx.get_all_series()
        if not all_series:
            return make_error_response(
                ctx,
                "No series provided. Please select at least one data column.",
                error_fixes=["Select a column of numeric data in Excel."],
            )

        regression = ctx.get_param("regression", "c")
        nlags_param = ctx.get_param("nlags", "auto")
        if isinstance(nlags_param, (int, float)):
            nlags = int(nlags_param)
        else:
            nlags = str(nlags_param)
        significance = float(ctx.get_param("significance_level", 0.05))

        # CAI Phase 2 Session 17 fix (F-ST-KPSS-REGRESSION,
        # F-ST-KPSS-NLAGS): explicit allowlist gates. Pre-fix,
        # invalid `regression` / `nlags` strings flowed into
        # statsmodels.kpss which raised ValueError caught inside
        # _run_kpss_single — wrapper still returned status=success
        # with audit_fields recording user's invalid value.
        _REGRESSION_OPTS = ("c", "ct")
        if regression not in _REGRESSION_OPTS:
            return make_error_response(
                ctx,
                f"Unknown regression '{regression}'. Must be one "
                f"of: {', '.join(_REGRESSION_OPTS)}.",
                error_fixes=[
                    "Use 'c' (level stationarity; default) or "
                    "'ct' (trend stationarity).",
                ],
            )
        # nlags accepts: int, "auto", or "legacy"
        if isinstance(nlags, str) and nlags not in ("auto", "legacy"):
            return make_error_response(
                ctx,
                f"Unknown nlags '{nlags}'. Must be 'auto', "
                "'legacy', or an integer.",
                error_fixes=[
                    "Use 'auto' (default; data-driven bandwidth "
                    "via Hobijn-Franses-Ooms 1998), 'legacy' "
                    "(Schwert-style int(12*(n/100)^(1/4))), or "
                    "supply an explicit integer bandwidth.",
                ],
            )

        warn_list = []
        result_rows = []
        all_summaries = []
        detail_tables = []
        # Track first-series data for the interpretation block (the spec
        # renders a single-series verdict; multi-series runs use the
        # first series as a representative summary).
        _first_interp_dict = None

        progress_callback("Running KPSS tests", 15)

        for idx, (name, values) in enumerate(all_series):
            pct = 15 + int(70 * (idx + 1) / len(all_series))
            progress_callback(f"Testing '{name}'", pct)

            clean = _prepare_series(values, name, warn_list)
            single = _run_kpss_single(clean, regression, nlags)

            if single["error"] is not None:
                result_rows.append([
                    name, None, None, None,
                    f"{regression} ({single['regression_label']})",
                    len(clean), single["error"],
                ])
                all_summaries.append(f"'{name}': {single['error']}.")
                continue

            if single["pvalue_clipped"]:
                warn_list.append(
                    f"'{name}': KPSS p-value is at a table boundary; exact "
                    "p-value interpolation is approximate."
                )

            rejected = (
                single["pvalue"] is not None
                and single["pvalue"] < significance
            )
            single["decision_h0_rejected"] = bool(rejected)
            decision = (
                "Reject H0 (stationarity)" if rejected
                else "Fail to reject H0 (stationarity)"
            )

            result_rows.append([
                name,
                round(single["stat"], 4),
                (round(single["pvalue"], 6)
                 if single["pvalue"] is not None else None),
                single["used_lag"],
                f"{regression} ({single['regression_label']})",
                len(clean),
                decision,
            ])

            # Capture first-series data for the interp block (below).
            if _first_interp_dict is None:
                _crit_at_sig = None
                # lvl is a string like "1%", "5%", "10%"; parse to float
                for (lvl, cv, _rej) in single["critical_values_ordered"]:
                    try:
                        lvl_f = float(str(lvl).rstrip("%")) / 100.0
                    except (ValueError, TypeError):
                        continue
                    if abs(lvl_f - significance) < 1e-9:
                        _crit_at_sig = float(cv)
                        break
                if _crit_at_sig is None and single["critical_values_ordered"]:
                    _crit_at_sig = float(single["critical_values_ordered"][0][1])
                _first_interp_dict = {
                    "series_name": name,
                    "rejected": bool(rejected),
                    "stat_value": float(single["stat"]),
                    "p_value": (float(single["pvalue"])
                                if single["pvalue"] is not None else None),
                    "crit_value": _crit_at_sig or 0.0,
                    "significance": float(significance),
                    "regression": regression,
                    "n_obs": int(len(clean)),
                    "bandwidth": single.get("used_lag"),
                    "trending": None,
                    "effective_sample_size": None,
                    # FIX 8: surface the p-value-at-table-boundary flag
                    # so the spec's Tier 2 can disclose the clipping.
                    "pvalue_clipped": bool(single.get("pvalue_clipped", False)),
                }

            cv_rows = [
                [lvl, round(cv, 4), "Yes" if rej else "No"]
                for (lvl, cv, rej) in single["critical_values_ordered"]
            ]
            detail_tables.append(make_table(
                f"Critical Values - {name}",
                ["Significance Level", "Critical Value",
                 "Stat > CV? (Reject H0)"],
                cv_rows,
            ))

            # P.2 summary language — KPSS null IS stationarity, so
            # "stationarity null not rejected" DOES warrant saying "is
            # stationary" in the caveat.
            if rejected:
                all_summaries.append(
                    f"'{name}': stationarity null rejected at the "
                    f"{significance*100:.0f}% level "
                    f"(KPSS={single['stat']:.4f}, p={single['pvalue']:.4f}, "
                    f"regression='{regression}' / {single['regression_label']}, "
                    f"lag={single['used_lag']}). Series appears non-stationary; "
                    "consider differencing."
                )
            else:
                pv_str = (f"p={single['pvalue']:.4f}"
                          if single["pvalue"] is not None else "p>=0.10")
                all_summaries.append(
                    f"'{name}': stationarity null not rejected at the "
                    f"{significance*100:.0f}% level "
                    f"(KPSS={single['stat']:.4f}, {pv_str}, "
                    f"regression='{regression}' / {single['regression_label']}, "
                    f"lag={single['used_lag']}). Series appears stationary; "
                    "pair with ADF + PP via the Stationarity Triage "
                    "for a confirmatory joint verdict."
                )

        progress_callback("Building output", 90)

        main_table = make_table(
            "KPSS Test Results",
            ["Series", "KPSS Statistic", "P-Value", "Lags Used",
             "Regression", "N Total", "Decision"],
            result_rows,
        )

        plain_english = (" ".join(all_summaries)
                         if all_summaries else "No test results produced.")

        charting = (
            "Table display color-coded by decision. KPSS's null IS "
            "stationarity, so 'fail to reject' means the series looks "
            "stationary — pair with ADF for a confirmatory joint verdict."
        )

        progress_callback("Done", 100)

        interp = (
            build_interpretation("kpss_test", _first_interp_dict)
            if _first_interp_dict else None
        )

        return make_response(
            ctx,
            tables=[main_table] + detail_tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "regression": regression,
                "regression_label": _REGRESSION_LABEL.get(regression, regression),
                "nlags_rule": nlags,
                "significance_level": significance,
                "n_series_tested": len(all_series),
                **format_significance_disclosure(
                    test_name="KPSS stationarity test",
                    critical_value_formula=(
                        "Kwiatkowski-Phillips-Schmidt-Shin critical values "
                        "via statsmodels.tsa.stattools.kpss; Newey-West-style "
                        "long-run variance estimator handles serial correlation"
                    ),
                    ac_corrected=True,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"KPSS test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant series (zero variance causes KPSS to fail).",
                "Try regression='ct' for trend-stationarity testing.",
            ],
        )
