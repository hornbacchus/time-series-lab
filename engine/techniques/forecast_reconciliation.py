"""
Hierarchical Forecast Reconciliation for Time Series Lab.

Implements bottom-up, top-down, and OLS (MinT-like) reconciliation
of hierarchical or grouped time series forecasts.

The user provides series in a hierarchy: the first series is the
top-level aggregate, and the remaining series are the bottom-level
components that should sum to the top level.
"""

import numpy as np
from scipy import linalg

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"methods": ["bottom_up"], "horizon": 10},
    "Balanced": {"methods": ["bottom_up", "top_down", "ols"], "horizon": 10},
    "Thorough": {"methods": ["bottom_up", "top_down", "ols"], "horizon": 10},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Reconcile hierarchical forecasts.

    Parameters (via ctx.params)
    ---------------------------
    method : str or list[str], optional
        'bottom_up', 'top_down', 'ols'. Preset-dependent.
    horizon : int
        Forecast horizon. Default 10.
    base_forecaster : str, optional
        How to produce base forecasts: 'naive' (random walk), 'drift', 'ets'.
        Default 'naive'.
    top_down_weights : str, optional
        For top-down: 'proportions_avg' (default) or 'proportions_last'.

    Series layout
    -------------
    First series  -> top-level aggregate.
    Remaining series -> bottom-level components (should sum to top).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        top_name, top_vals = all_series[0]
        bottom_names = [s[0] for s in all_series[1:]]
        bottom_arrays = [s[1] for s in all_series[1:]]
        n_bottom = len(bottom_names)
        n_total = n_bottom + 1  # top + bottom levels

        # Align lengths
        min_len = min(len(top_vals), *(len(a) for a in bottom_arrays))
        top_vals = top_vals[:min_len]
        bottom_arrays = [a[:min_len] for a in bottom_arrays]
        T = min_len

        # Handle NaN via interpolation
        def _fill_nan(arr, label):
            nans = np.where(np.isnan(arr))[0]
            valid = np.where(~np.isnan(arr))[0]
            if len(nans) > 0:
                if len(valid) < 3:
                    raise ValueError(f"Series '{label}' has too few non-missing values.")
                arr = arr.copy()
                arr[nans] = np.interp(nans, valid, arr[valid])
            return arr

        top_vals = _fill_nan(top_vals, top_name)
        for i in range(n_bottom):
            bottom_arrays[i] = _fill_nan(bottom_arrays[i], bottom_names[i])

        if T < 10:
            return make_error_response(
                ctx,
                f"Only {T} observations. Need at least 10 for reconciliation.",
                error_fixes=["Provide longer series."],
            )

        # Check coherence: does sum of bottom ≈ top?
        bottom_sum = np.sum(np.column_stack(bottom_arrays), axis=1)
        max_diff = float(np.max(np.abs(top_vals - bottom_sum)))
        mean_top = float(np.mean(np.abs(top_vals)))
        relative_incoherence = max_diff / mean_top if mean_top > 0 else max_diff
        if relative_incoherence > 0.05:
            warnings.append(
                f"Historical bottom-level series do not exactly sum to the top level "
                f"(max absolute difference = {max_diff:.4f}, relative = {relative_incoherence:.2%}). "
                "Reconciliation will enforce coherence in the forecasts."
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        horizon = max(1, int(ctx.get_param("horizon", cfg["horizon"])))
        methods_param = ctx.get_param("method")
        if methods_param is not None:
            if isinstance(methods_param, str):
                methods = [methods_param.lower()]
            else:
                methods = [m.lower() for m in methods_param]
        else:
            methods = cfg["methods"]
        base_fc_type = ctx.get_param("base_forecaster", "naive")
        td_weights = ctx.get_param("top_down_weights", "proportions_avg")

        progress_callback("Generating base forecasts", 20)

        # Generate base forecasts for all series
        all_vals = [top_vals] + bottom_arrays
        all_names = [top_name] + bottom_names
        base_fc = np.zeros((horizon, n_total))
        base_residuals = np.zeros((T, n_total))

        for i, (sname, svals) in enumerate(zip(all_names, all_vals)):
            fc, resid = _base_forecast(svals, horizon, base_fc_type)
            base_fc[:, i] = fc
            base_residuals[-len(resid):, i] = resid

        progress_callback("Reconciling forecasts", 45)

        # S matrix: maps bottom-level to all levels
        # For 2-level hierarchy: S = [[1, 1, ..., 1], I_n_bottom]
        S = np.vstack([np.ones((1, n_bottom)), np.eye(n_bottom)])  # (n_total, n_bottom)

        results = {}

        for method in methods:
            if method == "bottom_up":
                # G = [0, I] -> reconciled = S @ bottom_base_fc
                fc_bottom = base_fc[:, 1:]  # (horizon, n_bottom)
                fc_reconciled = fc_bottom @ S.T  # This is wrong; we need S @ fc_bottom.T
                fc_reconciled = (S @ fc_bottom.T).T  # (horizon, n_total)
                results["bottom_up"] = fc_reconciled

            elif method == "top_down":
                # Compute proportions
                if td_weights == "proportions_last":
                    props = np.zeros(n_bottom)
                    for j in range(n_bottom):
                        props[j] = bottom_arrays[j][-1] / top_vals[-1] if top_vals[-1] != 0 else 1.0 / n_bottom
                else:
                    # proportions_avg
                    props = np.zeros(n_bottom)
                    for j in range(n_bottom):
                        props[j] = np.mean(bottom_arrays[j]) / np.mean(top_vals) if np.mean(top_vals) != 0 else 1.0 / n_bottom

                # Normalise
                prop_sum = props.sum()
                if prop_sum > 0:
                    props = props / prop_sum

                fc_top = base_fc[:, 0]  # (horizon,)
                fc_reconciled = np.zeros((horizon, n_total))
                fc_reconciled[:, 0] = fc_top
                for j in range(n_bottom):
                    fc_reconciled[:, 1 + j] = fc_top * props[j]

                results["top_down"] = fc_reconciled

            elif method == "ols":
                # OLS reconciliation (Wickramasuriya et al. MinT with OLS shrinkage)
                # Reconciled = S @ (S'S)^{-1} S' @ base_fc
                try:
                    StS_inv = np.linalg.inv(S.T @ S)
                    P = S @ StS_inv @ S.T  # projection matrix (n_total, n_total)
                    fc_reconciled = (P @ base_fc.T).T  # (horizon, n_total)
                except np.linalg.LinAlgError:
                    warnings.append("OLS reconciliation failed (singular S'S). Falling back to bottom-up.")
                    fc_bottom = base_fc[:, 1:]
                    fc_reconciled = (S @ fc_bottom.T).T

                results["ols"] = fc_reconciled

            else:
                warnings.append(f"Unknown method '{method}' skipped.")

        if not results:
            return make_error_response(ctx, "No valid reconciliation method was specified.")

        progress_callback("Building output tables", 70)

        tables = []

        # ---- Reconciled forecasts per method ----
        for method_name, fc_rec in results.items():
            fc_rows = []
            for h in range(horizon):
                row = [h + 1]
                for i in range(n_total):
                    row.append(round(float(fc_rec[h, i]), 4))
                fc_rows.append(row)
            tables.append(make_table(
                f"Reconciled Forecast ({method_name})",
                ["Step"] + all_names,
                fc_rows,
            ))

        # ---- Base vs reconciled comparison ----
        for method_name, fc_rec in results.items():
            comp_rows = []
            for i in range(n_total):
                base_mean = float(np.mean(base_fc[:, i]))
                rec_mean = float(np.mean(fc_rec[:, i]))
                diff = rec_mean - base_mean
                comp_rows.append([
                    all_names[i],
                    round(base_mean, 4),
                    round(rec_mean, 4),
                    round(diff, 4),
                ])
            tables.append(make_table(
                f"Base vs Reconciled Mean ({method_name})",
                ["Series", "Base Mean FC", "Reconciled Mean FC", "Adjustment"],
                comp_rows,
            ))

        # ---- Coherence check on reconciled ----
        for method_name, fc_rec in results.items():
            coh_rows = []
            for h in range(horizon):
                top_fc = fc_rec[h, 0]
                bot_sum = np.sum(fc_rec[h, 1:])
                coh_rows.append([h + 1, round(float(top_fc), 4), round(float(bot_sum), 4),
                                 round(float(top_fc - bot_sum), 6)])
            tables.append(make_table(
                f"Coherence Check ({method_name})",
                ["Step", "Top Forecast", "Bottom Sum", "Difference"],
                coh_rows,
            ))

        # ---- Historical coherence ----
        hist_rows = [
            ["Mean Top Level", round(float(np.mean(top_vals)), 4)],
            ["Mean Bottom Sum", round(float(np.mean(bottom_sum)), 4)],
            ["Max Abs Difference", round(max_diff, 4)],
            ["Relative Incoherence", f"{relative_incoherence:.4%}"],
        ]
        if "top_down" in results:
            prop_rows = []
            props = np.zeros(n_bottom)
            for j in range(n_bottom):
                props[j] = np.mean(bottom_arrays[j]) / np.mean(top_vals) if np.mean(top_vals) != 0 else 1.0 / n_bottom
            prop_sum = props.sum()
            if prop_sum > 0:
                props = props / prop_sum
            for j in range(n_bottom):
                hist_rows.append([f"Proportion ({bottom_names[j]})", round(float(props[j]), 4)])
        tables.append(make_table("Historical Coherence", ["Metric", "Value"], hist_rows))

        # ---- Summary ----
        summary_rows = [
            ["Top-Level Series", top_name],
            ["Bottom-Level Series", ", ".join(bottom_names)],
            ["Number of Bottom Series", n_bottom],
            ["Observations", T],
            ["Forecast Horizon", horizon],
            ["Base Forecaster", base_fc_type],
            ["Methods Applied", ", ".join(results.keys())],
        ]
        tables.append(make_table("Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        method_list = ", ".join(results.keys())
        plain = (
            f"Hierarchical forecast reconciliation for {n_total} series "
            f"({top_name} = sum of {', '.join(bottom_names)}). "
            f"Methods applied: {method_list}. "
            f"Base forecasts generated using '{base_fc_type}' method, "
            f"then reconciled to enforce coherence over {horizon} steps. "
        )
        if relative_incoherence > 0.05:
            plain += f"Note: historical data was {relative_incoherence:.1%} incoherent."

        charting = (
            "Stacked area chart of bottom-level reconciled forecasts summing to top-level. "
            "Line overlay showing original base forecasts vs reconciled. "
            "Bar chart comparing base vs reconciled mean forecasts per series."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C5) ──────────────────────────
        # Primary-method citation convention (Decision D5):
        # MinT-OLS preferred when available; fall back to bottom_up
        # when OLS fails (detected via fallback warning at line 182).
        _methods_ran = list(results.keys())
        if "ols" in _methods_ran:
            _ols_fell_back = any("OLS reconciliation failed" in w for w in warnings)
            primary_method = "bottom_up" if _ols_fell_back else "ols"
        elif "bottom_up" in _methods_ran:
            primary_method = "bottom_up"
        elif "top_down" in _methods_ran:
            primary_method = "top_down"
        else:
            primary_method = _methods_ran[0] if _methods_ran else None

        audit = {
            "top_series": top_name,
            "bottom_series": bottom_names,
            "n_bottom": n_bottom,
            "methods": _methods_ran,
            "primary_method": primary_method,
            "primary_method_fell_back": bool("ols" in _methods_ran and any("OLS reconciliation failed" in w for w in warnings)),
            "base_forecaster": base_fc_type,
            "horizon": horizon,
            "n_observations": T,
            "relative_incoherence": round(relative_incoherence, 4),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        interp = build_interpretation("forecast_reconciliation", _interp_dict)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Forecast reconciliation failed: {e}",
            error_fixes=[
                "Ensure first series is the aggregate and remaining are components.",
                "All series must be numeric and the same length.",
                "Check that bottom-level series approximately sum to the top level.",
            ],
        )


# ---------------------------------------------------------------------------
# Base forecasters
# ---------------------------------------------------------------------------

def _base_forecast(y, horizon, method="naive"):
    """
    Generate base forecasts and in-sample residuals.

    Returns (forecast_array, residual_array).
    """
    n = len(y)

    if method == "drift":
        # Random walk with drift
        drift = (y[-1] - y[0]) / (n - 1) if n > 1 else 0.0
        fc = y[-1] + drift * np.arange(1, horizon + 1)
        fitted = np.full(n, np.nan)
        fitted[1:] = y[:-1] + drift
        resid = y - fitted
        resid = resid[~np.isnan(resid)]
    elif method == "ets":
        # Simple exponential smoothing
        alpha = 0.3
        level = y[0]
        fitted = np.zeros(n)
        for t in range(n):
            fitted[t] = level
            level = alpha * y[t] + (1 - alpha) * level
        fc = np.full(horizon, level)
        resid = y - fitted
    else:
        # naive (random walk)
        fc = np.full(horizon, y[-1])
        fitted = np.full(n, np.nan)
        fitted[1:] = y[:-1]
        resid = y[1:] - y[:-1]

    return fc, resid
