"""
TAR / SETAR Threshold Autoregressive Model for Time Series Lab.

Implements Self-Exciting Threshold AutoRegressive (SETAR) models where
the AR dynamics switch between regimes based on a threshold variable
(typically a lagged value of the series itself).

Implemented with numpy/scipy (no external TAR library).
"""

import numpy as np
from scipy import stats as sp_stats
from itertools import product

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
    "Fast": {"max_ar": 2, "n_regimes": 2, "threshold_search": "grid_coarse"},
    "Balanced": {"max_ar": 4, "n_regimes": 2, "threshold_search": "grid_fine"},
    "Thorough": {"max_ar": 6, "n_regimes": 3, "threshold_search": "grid_fine"},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a SETAR model.

    Parameters (via ctx.params)
    ---------------------------
    ar_order : int or list[int], optional
        AR order(s) per regime. Single int applies to all regimes.
        List specifies per-regime orders. Preset-dependent max.
    n_regimes : int, optional
        Number of regimes (2 or 3). Default preset-dependent.
    delay : int, optional
        Delay parameter d: threshold variable is y(t-d). Default 1.
    thresholds : list[float], optional
        Fixed threshold value(s). If omitted, searched automatically.
    trim : float, optional
        Fraction of data excluded from threshold search at each end. Default 0.15.
    horizon : int
        Forecast horizon. Default 10.

    Series layout
    -------------
    First series -> observed time series.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 10:
            warnings.append(f"{nan_count} NaN values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
        elif nan_count >= n - 10:
            return make_error_response(ctx, "Too few non-missing values to fit SETAR model.")
        else:
            filled = values

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_regimes = int(ctx.get_param("n_regimes", cfg["n_regimes"]))
        delay = int(ctx.get_param("delay", 1))
        trim = float(ctx.get_param("trim", 0.15))
        horizon = max(1, int(ctx.get_param("horizon", 10)))

        n_regimes = max(2, min(n_regimes, 3))
        n_thresholds = n_regimes - 1

        ar_param = ctx.get_param("ar_order")
        if ar_param is None:
            ar_orders = [min(cfg["max_ar"], max(1, n // 10))] * n_regimes
        elif isinstance(ar_param, (int, float)):
            ar_orders = [int(ar_param)] * n_regimes
        elif isinstance(ar_param, (list, tuple)):
            ar_orders = [int(x) for x in ar_param]
            while len(ar_orders) < n_regimes:
                ar_orders.append(ar_orders[-1])
        else:
            ar_orders = [2] * n_regimes

        max_ar = max(ar_orders)
        start_idx = max(max_ar, delay)

        if n < start_idx + 15:
            return make_error_response(
                ctx,
                f"Only {n} observations for SETAR with AR orders {ar_orders} and delay {delay}. "
                f"Need at least {start_idx + 15}.",
                error_fixes=["Reduce AR order or delay, or provide more data."],
            )

        progress_callback("Searching for threshold(s)", 15)

        # Threshold variable: y(t - delay)
        thresh_var = filled[start_idx - delay: n - delay]
        y_dep = filled[start_idx:]
        effective_n = len(y_dep)

        # Build lag matrix for all observations
        lag_matrix = np.column_stack([
            filled[start_idx - j: n - j] for j in range(1, max_ar + 1)
        ])

        # Threshold search
        thresholds_param = ctx.get_param("thresholds")
        if thresholds_param is not None:
            if isinstance(thresholds_param, (int, float)):
                thresholds = [float(thresholds_param)]
            else:
                thresholds = sorted([float(x) for x in thresholds_param])
        else:
            thresholds = _search_thresholds(
                y_dep, lag_matrix, thresh_var, ar_orders, n_thresholds,
                trim, cfg["threshold_search"], progress_callback,
            )

        if len(thresholds) < n_thresholds:
            # Not enough thresholds found, reduce regime count
            n_regimes = len(thresholds) + 1
            n_thresholds = len(thresholds)
            ar_orders = ar_orders[:n_regimes]
            warnings.append(f"Reduced to {n_regimes} regimes based on threshold search.")

        progress_callback("Fitting regime-specific AR models", 55)

        # Assign observations to regimes
        regime_assignment = _assign_regimes(thresh_var, thresholds)

        # Fit AR model per regime
        regime_results = []
        total_sse = 0.0
        total_params = 0
        fitted_all = np.full(effective_n, np.nan)
        resid_all = np.full(effective_n, np.nan)

        for r in range(n_regimes):
            mask = regime_assignment == r
            count_r = int(mask.sum())

            if count_r < ar_orders[r] + 2:
                warnings.append(
                    f"Regime {r} has only {count_r} observations for AR({ar_orders[r]}). "
                    "Estimates may be unreliable."
                )
                if count_r < 2:
                    regime_results.append({
                        "regime": r, "count": count_r,
                        "ar_order": ar_orders[r],
                        "intercept": 0.0, "ar_coefs": np.zeros(ar_orders[r]),
                        "sigma": 0.0, "sse": 0.0,
                    })
                    continue

            y_r = y_dep[mask]
            X_r_parts = [np.ones((count_r, 1))]  # intercept
            for j in range(ar_orders[r]):
                X_r_parts.append(lag_matrix[mask, j:j+1])
            X_r = np.hstack(X_r_parts)

            # OLS
            beta_r, _, _, _ = np.linalg.lstsq(X_r, y_r, rcond=None)
            y_hat_r = X_r @ beta_r
            resid_r = y_r - y_hat_r
            sse_r = float(np.sum(resid_r ** 2))
            sigma_r = float(np.sqrt(sse_r / max(count_r - len(beta_r), 1)))

            fitted_all[mask] = y_hat_r
            resid_all[mask] = resid_r

            regime_results.append({
                "regime": r,
                "count": count_r,
                "ar_order": ar_orders[r],
                "intercept": float(beta_r[0]),
                "ar_coefs": beta_r[1:].flatten(),
                "sigma": sigma_r,
                "sse": sse_r,
            })

            total_sse += sse_r
            total_params += len(beta_r)

        # Information criteria
        total_params += n_thresholds  # threshold parameters
        aic = effective_n * np.log(total_sse / effective_n) + 2 * total_params
        bic = effective_n * np.log(total_sse / effective_n) + total_params * np.log(effective_n)
        rmse = float(np.sqrt(total_sse / effective_n))

        progress_callback("Generating forecasts", 70)

        # Multi-step forecast via simulation
        n_sims = 500
        fc_paths = np.zeros((n_sims, horizon))

        for sim in range(n_sims):
            history = list(filled[-max(max_ar, delay):])
            for h in range(horizon):
                # Determine regime from threshold variable
                t_var = history[-(delay)]
                regime = _assign_single(t_var, thresholds)
                rr = regime_results[min(regime, len(regime_results) - 1)]

                # Compute AR prediction
                pred = rr["intercept"]
                for j in range(rr["ar_order"]):
                    if j < len(history):
                        pred += rr["ar_coefs"][j] * history[-(j + 1)]

                # Add noise
                pred += rr["sigma"] * np.random.randn()
                fc_paths[sim, h] = pred
                history.append(pred)

        fc_mean = np.mean(fc_paths, axis=0)
        fc_q05 = np.percentile(fc_paths, 5, axis=0)
        fc_q95 = np.percentile(fc_paths, 95, axis=0)

        progress_callback("Building output tables", 80)

        tables = []

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc_mean[h]), 6),
                round(float(fc_q05[h]), 6),
                round(float(fc_q95[h]), 6),
            ])
        tables.append(make_table("Forecast", ["Step", "Forecast", "Lower 90%", "Upper 90%"], fc_rows))

        # ---- Regime-specific coefficients ----
        coef_rows = []
        for rr in regime_results:
            r = rr["regime"]
            coef_rows.append([f"Regime {r}", "Intercept", round(rr["intercept"], 6), "", ""])
            for j, c in enumerate(rr["ar_coefs"]):
                coef_rows.append([f"Regime {r}", f"AR({j+1})", round(float(c), 6), "", ""])
            coef_rows.append([f"Regime {r}", "Sigma", round(rr["sigma"], 6), "", ""])
            coef_rows.append([f"Regime {r}", "Obs Count", rr["count"], "", ""])
        tables.append(make_table(
            "Regime Coefficients",
            ["Regime", "Parameter", "Value", "", ""],
            coef_rows,
        ))

        # ---- Threshold info ----
        thresh_rows = []
        for i, th in enumerate(thresholds):
            thresh_rows.append([f"Threshold {i+1}", round(th, 6)])
        thresh_rows.append(["Delay (d)", delay])
        thresh_rows.append(["Threshold Variable", f"{name}(t-{delay})"])
        tables.append(make_table("Threshold Parameters", ["Parameter", "Value"], thresh_rows))

        # ---- Regime assignment table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else list(range(1, n + 1))
        assign_rows = []
        for t in range(effective_n):
            assign_rows.append([
                time_col[start_idx + t] if start_idx + t < len(time_col) else start_idx + t + 1,
                round(float(filled[start_idx + t]), 6),
                int(regime_assignment[t]),
                round(float(fitted_all[t]), 6) if not np.isnan(fitted_all[t]) else None,
                round(float(resid_all[t]), 6) if not np.isnan(resid_all[t]) else None,
            ])
        tables.append(make_table(
            "Regime Assignment",
            ["Time", name, "Regime", "Fitted", "Residual"],
            assign_rows,
        ))

        # ---- Model summary ----
        summary_rows = [
            ["Model", f"SETAR({n_regimes}; {','.join(str(o) for o in ar_orders[:n_regimes])})"],
            ["Regimes", n_regimes],
            ["Thresholds", ", ".join([f"{th:.4f}" for th in thresholds])],
            ["Delay (d)", delay],
            ["Observations (effective)", effective_n],
            ["Total Parameters", total_params],
            ["RMSE", round(rmse, 4)],
            ["AIC", round(float(aic), 2)],
            ["BIC", round(float(bic), 2)],
            ["Forecast Horizon", horizon],
        ]
        for rr in regime_results:
            summary_rows.append([f"Regime {rr['regime']} Count", rr["count"]])
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Linearity test (Hansen-style) ----
        progress_callback("Testing for threshold nonlinearity", 90)
        if n_regimes == 2:
            # Approximate F-test: SETAR vs linear AR
            linear_sse = _linear_ar_sse(y_dep, lag_matrix, max(ar_orders))
            if linear_sse > 0:
                f_stat = ((linear_sse - total_sse) / n_thresholds) / (total_sse / max(effective_n - total_params, 1))
                f_pval = 1 - sp_stats.f.cdf(f_stat, n_thresholds, max(effective_n - total_params, 1))
            else:
                f_stat = 0.0
                f_pval = 1.0

            test_rows = [
                ["F-statistic (SETAR vs AR)", round(float(f_stat), 4)],
                ["P-value (approx)", round(float(f_pval), 6)],
                ["Nonlinearity Significant?", "Yes" if f_pval < 0.05 else "No"],
            ]
            tables.append(make_table("Linearity Test", ["Metric", "Value"], test_rows))

            if f_pval > 0.10:
                warnings.append(
                    "Threshold effect may not be statistically significant (p > 0.10). "
                    "A linear AR model might be sufficient."
                )

        # ---- Plain English ----
        thresh_str = ", ".join([f"{th:.4f}" for th in thresholds])
        plain = (
            f"SETAR({n_regimes}) model fitted to '{name}' ({n} observations). "
            f"Threshold(s) at {thresh_str} with delay d={delay}. "
        )
        for rr in regime_results:
            plain += f"Regime {rr['regime']}: AR({rr['ar_order']}), {rr['count']} obs, sigma={rr['sigma']:.4f}. "
        plain += f"RMSE = {rmse:.4f}, AIC = {aic:.1f}."

        charting = (
            "Time series colored by regime assignment. Overlay fitted values. "
            "Horizontal dashed line(s) at threshold value(s) on the threshold variable plot. "
            "Scatter plot of y(t) vs y(t-d) colored by regime showing threshold boundaries."
        )

        progress_callback("Done", 100)

        audit = {
            "model": f"SETAR({n_regimes})",
            "ar_orders": ar_orders[:n_regimes],
            "thresholds": [round(th, 6) for th in thresholds],
            "delay": delay,
            "n_regimes": n_regimes,
            "rmse": round(rmse, 4),
            "aic": round(float(aic), 2),
            "bic": round(float(bic), 2),
            "n_effective": effective_n,
            "regime_counts": [rr["count"] for rr in regime_results],
            "horizon": horizon,
        }

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"SETAR model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Reduce AR order or number of regimes.",
                "Try specifying a threshold value manually.",
                "Check for constant series.",
            ],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _search_thresholds(y, lag_matrix, thresh_var, ar_orders, n_thresholds,
                       trim, search_type, progress_callback):
    """Grid search for optimal threshold(s) minimizing total SSE."""
    sorted_tv = np.sort(thresh_var)
    n_t = len(sorted_tv)
    lo = int(n_t * trim)
    hi = int(n_t * (1 - trim))

    if search_type == "grid_coarse":
        n_grid = min(50, hi - lo)
    else:
        n_grid = min(200, hi - lo)

    candidates = sorted_tv[np.linspace(lo, hi - 1, n_grid, dtype=int)]
    candidates = np.unique(candidates)

    if n_thresholds == 1:
        best_sse = np.inf
        best_thresh = [float(np.median(thresh_var))]

        for i, c in enumerate(candidates):
            if i % max(1, len(candidates) // 10) == 0:
                pct = 15 + int(35 * i / len(candidates))
                progress_callback(f"Testing threshold {c:.4f}", pct)

            sse = _compute_setar_sse(y, lag_matrix, thresh_var, [c], ar_orders)
            if sse < best_sse:
                best_sse = sse
                best_thresh = [float(c)]

        return best_thresh

    elif n_thresholds == 2:
        best_sse = np.inf
        best_thresh = [float(np.percentile(thresh_var, 33)),
                       float(np.percentile(thresh_var, 67))]

        # Coarser grid for 2 thresholds
        n_grid2 = min(30, len(candidates))
        candidates2 = candidates[np.linspace(0, len(candidates) - 1, n_grid2, dtype=int)]

        for i, c1 in enumerate(candidates2):
            for c2 in candidates2:
                if c2 <= c1:
                    continue
                sse = _compute_setar_sse(y, lag_matrix, thresh_var, [c1, c2], ar_orders)
                if sse < best_sse:
                    best_sse = sse
                    best_thresh = [float(c1), float(c2)]

            if i % max(1, len(candidates2) // 5) == 0:
                pct = 15 + int(35 * i / len(candidates2))
                progress_callback(f"Searching 2D threshold grid ({i+1}/{len(candidates2)})", pct)

        return best_thresh

    return [float(np.median(thresh_var))]


def _compute_setar_sse(y, lag_matrix, thresh_var, thresholds, ar_orders):
    """Compute total SSE for a given set of thresholds."""
    regimes = _assign_regimes(thresh_var, thresholds)
    n_regimes = len(thresholds) + 1
    total_sse = 0.0

    for r in range(n_regimes):
        mask = regimes == r
        count_r = int(mask.sum())
        ar_order = ar_orders[min(r, len(ar_orders) - 1)]

        if count_r < ar_order + 2:
            total_sse += 1e10  # penalty for too few obs
            continue

        y_r = y[mask]
        X_r_parts = [np.ones((count_r, 1))]
        for j in range(ar_order):
            if j < lag_matrix.shape[1]:
                X_r_parts.append(lag_matrix[mask, j:j+1])
        X_r = np.hstack(X_r_parts)

        try:
            beta_r, _, _, _ = np.linalg.lstsq(X_r, y_r, rcond=None)
            resid_r = y_r - X_r @ beta_r
            total_sse += float(np.sum(resid_r ** 2))
        except Exception:
            total_sse += 1e10

    return total_sse


def _assign_regimes(thresh_var, thresholds):
    """Assign each observation to a regime based on threshold values."""
    n = len(thresh_var)
    regimes = np.zeros(n, dtype=int)
    for th in sorted(thresholds):
        regimes += (thresh_var > th).astype(int)
    return regimes


def _assign_single(value, thresholds):
    """Assign a single value to a regime."""
    regime = 0
    for th in sorted(thresholds):
        if value > th:
            regime += 1
    return regime


def _linear_ar_sse(y, lag_matrix, ar_order):
    """Fit a simple linear AR model and return SSE."""
    n_t = len(y)
    ar_order = min(ar_order, lag_matrix.shape[1])
    X = np.hstack([np.ones((n_t, 1)), lag_matrix[:, :ar_order]])
    try:
        beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        return float(np.sum(resid ** 2))
    except Exception:
        return float(np.sum(y ** 2))
