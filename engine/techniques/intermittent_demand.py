"""
Intermittent Demand Forecasting for Time Series Lab.

Implements three methods for forecasting lumpy / intermittent demand:
  - Croston's method (original, 1972)
  - SBA (Syntetos-Boylan Approximation)
  - TSB (Teunter-Syntetos-Babai)

These methods decompose the demand into demand-size and inter-arrival
intervals, updating each with separate exponential smoothing.
"""

import numpy as np

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
    "Fast": {"methods": ["croston"], "alpha_grid": [0.1, 0.2, 0.3]},
    "Balanced": {"methods": ["croston", "sba"], "alpha_grid": [0.05, 0.1, 0.15, 0.2, 0.3]},
    "Thorough": {
        "methods": ["croston", "sba", "tsb"],
        "alpha_grid": [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5],
    },
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit intermittent demand forecasting models.

    Parameters (via ctx.params)
    ---------------------------
    method : str or list[str], optional
        'croston', 'sba', 'tsb', or list of methods. Preset-dependent.
    alpha : float, optional
        Smoothing parameter for demand sizes. If omitted, optimised from grid.
    beta : float, optional
        Smoothing parameter for inter-arrival times (Croston/SBA) or
        probability (TSB). If omitted, set equal to alpha.
    horizon : int
        Forecast horizon (flat forecasts). Default 10.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []

        name, values = ctx.get_primary_series()
        n = len(values)

        # Replace NaN with 0 (standard for intermittent demand)
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0:
            warnings.append(f"{nan_count} NaN values treated as zero demand.")
            values = np.where(np.isnan(values), 0.0, values)

        # Negative values
        neg_count = int((values < 0).sum())
        if neg_count > 0:
            warnings.append(f"{neg_count} negative values detected. Intermittent demand methods assume non-negative demand.")

        if n < 4:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} observations. Need at least 4.",
                error_fixes=["Provide a longer demand series."],
            )

        # Demand characteristics
        zero_count = int((values == 0).sum())
        demand_fraction = 1.0 - zero_count / n
        nonzero_values = values[values > 0]
        cv2_demand = float(np.var(nonzero_values) / np.mean(nonzero_values) ** 2) if len(nonzero_values) > 1 and np.mean(nonzero_values) > 0 else 0.0

        if zero_count == 0:
            warnings.append(
                "No zero-demand periods detected. This series may not be intermittent. "
                "Consider standard exponential smoothing or ARIMA instead."
            )

        if zero_count == n:
            return make_error_response(
                ctx,
                "All demand values are zero. Cannot fit intermittent demand model.",
                error_fixes=["Check that the data contains non-zero demand observations."],
            )

        # Classify demand pattern (Syntetos-Boylan classification)
        adi = n / max(len(nonzero_values), 1)  # average demand interval
        if adi < 1.32 and cv2_demand < 0.49:
            pattern = "Smooth (non-intermittent)"
        elif adi >= 1.32 and cv2_demand < 0.49:
            pattern = "Intermittent"
        elif adi < 1.32 and cv2_demand >= 0.49:
            pattern = "Erratic"
        else:
            pattern = "Lumpy"

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        horizon = max(1, int(ctx.get_param("horizon", 10)))

        methods_param = ctx.get_param("method")
        if methods_param is not None:
            if isinstance(methods_param, str):
                methods = [methods_param.lower()]
            else:
                methods = [m.lower() for m in methods_param]
        else:
            methods = cfg["methods"]

        alpha_param = ctx.get_param("alpha")
        beta_param = ctx.get_param("beta")

        np.random.seed(ctx.seed)

        progress_callback("Fitting intermittent demand models", 20)

        all_results = []
        best_result = None
        best_mse = np.inf

        for method in methods:
            if method not in ("croston", "sba", "tsb"):
                warnings.append(f"Unknown method '{method}' skipped. Use 'croston', 'sba', or 'tsb'.")
                continue

            if alpha_param is not None:
                alphas = [float(alpha_param)]
            else:
                alphas = cfg["alpha_grid"]

            for alpha in alphas:
                beta = float(beta_param) if beta_param is not None else alpha

                if method == "croston":
                    fitted, fc, info = _croston(values, alpha, beta, horizon)
                elif method == "sba":
                    fitted, fc, info = _sba(values, alpha, beta, horizon)
                elif method == "tsb":
                    fitted, fc, info = _tsb(values, alpha, beta, horizon)

                # Compute MSE on non-zero demands
                resid = values - fitted
                mse = float(np.mean(resid ** 2))

                result = {
                    "method": method.upper(),
                    "alpha": alpha,
                    "beta": beta,
                    "fitted": fitted,
                    "forecast": fc,
                    "mse": mse,
                    "info": info,
                }
                all_results.append(result)

                if mse < best_mse:
                    best_mse = mse
                    best_result = result

        if best_result is None:
            return make_error_response(ctx, "No valid method could be fitted.")

        progress_callback("Building output tables", 70)

        # ---- Method comparison table ----
        seen = {}
        comp_rows = []
        for r in all_results:
            key = (r["method"], r["alpha"], r["beta"])
            if key not in seen:
                seen[key] = True
                rmse = np.sqrt(r["mse"])
                comp_rows.append([
                    r["method"],
                    round(r["alpha"], 3),
                    round(r["beta"], 3),
                    round(float(r["mse"]), 4),
                    round(float(rmse), 4),
                    round(float(r["forecast"]), 4),
                ])
        comp_table = make_table(
            "Method Comparison",
            ["Method", "Alpha", "Beta", "MSE", "RMSE", "Flat Forecast"],
            comp_rows,
        )

        # ---- Fitted values table (best model) ----
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        fitted_rows = []
        for i in range(n):
            fitted_rows.append([
                time_col[i],
                float(values[i]),
                round(float(best_result["fitted"][i]), 4),
                round(float(values[i] - best_result["fitted"][i]), 4),
            ])
        fitted_table = make_table(
            "Fitted Values (Best Model)",
            ["Time", "Actual", "Fitted", "Residual"],
            fitted_rows,
        )

        # ---- Forecast table ----
        fc_rows = []
        for h in range(1, horizon + 1):
            fc_rows.append([n + h, round(float(best_result["forecast"]), 4)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # ---- Demand characteristics ----
        char_rows = [
            ["Series", name],
            ["Observations", n],
            ["Zero-Demand Periods", zero_count],
            ["Non-Zero Periods", n - zero_count],
            ["Demand Fraction", round(demand_fraction, 4)],
            ["Average Demand Interval (ADI)", round(adi, 2)],
            ["CV^2 of Demand Sizes", round(cv2_demand, 4)],
            ["Demand Pattern", pattern],
            ["Mean (all)", round(float(np.mean(values)), 4)],
            ["Mean (non-zero)", round(float(np.mean(nonzero_values)), 4) if len(nonzero_values) > 0 else 0],
        ]
        char_table = make_table("Demand Characteristics", ["Metric", "Value"], char_rows)

        # ---- Model summary ----
        best_info = best_result["info"]
        summary_rows = [
            ["Best Method", best_result["method"]],
            ["Alpha", round(best_result["alpha"], 3)],
            ["Beta", round(best_result["beta"], 3)],
            ["MSE", round(float(best_result["mse"]), 4)],
            ["RMSE", round(float(np.sqrt(best_result["mse"])), 4)],
            ["Flat Forecast", round(float(best_result["forecast"]), 4)],
        ]
        for k, v in best_info.items():
            summary_rows.append([k, round(float(v), 4) if isinstance(v, (float, np.floating)) else v])
        summary_table = make_table("Best Model Summary", ["Metric", "Value"], summary_rows)

        # ---- Plain English ----
        plain = (
            f"Intermittent demand analysis of '{name}' ({n} observations, "
            f"{zero_count} zero-demand periods, pattern: {pattern}). "
            f"Best method: {best_result['method']} (alpha={best_result['alpha']:.2f}). "
            f"Flat forecast = {best_result['forecast']:.4f} per period. "
            f"RMSE = {np.sqrt(best_result['mse']):.4f}."
        )

        charting = (
            "Bar chart of actual demand values with the flat forecast overlaid as a horizontal line. "
            "Secondary panel: demand size and inter-arrival time smoothed estimates over time. "
            "Optionally show the Syntetos-Boylan classification quadrant chart."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[comp_table, summary_table, char_table, fitted_table, fc_table],
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "best_method": best_result["method"],
                "alpha": best_result["alpha"],
                "beta": best_result["beta"],
                "mse": round(float(best_result["mse"]), 4),
                "rmse": round(float(np.sqrt(best_result["mse"])), 4),
                "forecast": round(float(best_result["forecast"]), 4),
                "demand_pattern": pattern,
                "adi": round(adi, 2),
                "cv2_demand": round(cv2_demand, 4),
                "zero_fraction": round(1 - demand_fraction, 4),
                "methods_tested": len(all_results),
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Intermittent demand analysis failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check that there are some non-zero demand observations.",
                "Try a different alpha parameter (e.g. 0.1 to 0.3).",
            ],
        )


# ---------------------------------------------------------------------------
# Core methods
# ---------------------------------------------------------------------------

def _croston(values, alpha, beta, horizon):
    """
    Original Croston's method.

    Separate exponential smoothing on demand sizes (z) and
    inter-arrival intervals (p). Forecast = z_hat / p_hat.
    """
    n = len(values)
    fitted = np.zeros(n)

    # Initialise from first non-zero demand
    first_nz = -1
    for i in range(n):
        if values[i] > 0:
            first_nz = i
            break

    if first_nz < 0:
        return fitted, 0.0, {"z_final": 0.0, "p_final": 1.0}

    z_hat = float(values[first_nz])  # demand size estimate
    p_hat = float(first_nz + 1)      # inter-arrival interval estimate
    q = 0  # periods since last demand

    for i in range(n):
        q += 1
        if values[i] > 0:
            z_hat = alpha * values[i] + (1 - alpha) * z_hat
            p_hat = beta * q + (1 - beta) * p_hat
            q = 0
        fitted[i] = z_hat / p_hat if p_hat > 0 else 0.0

    fc = z_hat / p_hat if p_hat > 0 else 0.0
    info = {"z_final": z_hat, "p_final": p_hat}
    return fitted, fc, info


def _sba(values, alpha, beta, horizon):
    """
    Syntetos-Boylan Approximation (SBA).

    Applies a bias correction factor to Croston's method:
    forecast = (1 - beta/2) * z_hat / p_hat
    """
    n = len(values)
    fitted = np.zeros(n)

    first_nz = -1
    for i in range(n):
        if values[i] > 0:
            first_nz = i
            break

    if first_nz < 0:
        return fitted, 0.0, {"z_final": 0.0, "p_final": 1.0}

    z_hat = float(values[first_nz])
    p_hat = float(first_nz + 1)
    q = 0

    for i in range(n):
        q += 1
        if values[i] > 0:
            z_hat = alpha * values[i] + (1 - alpha) * z_hat
            p_hat = beta * q + (1 - beta) * p_hat
            q = 0
        if p_hat > 0:
            fitted[i] = (1 - beta / 2) * z_hat / p_hat
        else:
            fitted[i] = 0.0

    fc = (1 - beta / 2) * z_hat / p_hat if p_hat > 0 else 0.0
    info = {"z_final": z_hat, "p_final": p_hat, "bias_correction": 1 - beta / 2}
    return fitted, fc, info


def _tsb(values, alpha, beta, horizon):
    """
    Teunter-Syntetos-Babai (TSB) method.

    Smooths demand size (z) and demand probability (d) separately.
    forecast = z_hat * d_hat
    """
    n = len(values)
    fitted = np.zeros(n)

    # Initialise
    nonzero = values[values > 0]
    if len(nonzero) == 0:
        return fitted, 0.0, {"z_final": 0.0, "d_final": 0.0}

    z_hat = float(np.mean(nonzero))
    d_hat = float(len(nonzero) / n)

    for i in range(n):
        if values[i] > 0:
            z_hat = alpha * values[i] + (1 - alpha) * z_hat
            d_hat = beta * 1.0 + (1 - beta) * d_hat
        else:
            d_hat = beta * 0.0 + (1 - beta) * d_hat
        fitted[i] = z_hat * d_hat

    fc = z_hat * d_hat
    info = {"z_final": z_hat, "d_final": d_hat}
    return fitted, fc, info
