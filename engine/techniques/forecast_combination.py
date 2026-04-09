"""
Forecast Combination for Time Series Lab.

Combines forecasts from multiple models (ETS, ARIMA, Theta) using:
- Simple average
- Inverse-MSE weighting
- OLS combination (regression-based)
"""

import numpy as np
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"max_p": 2, "max_q": 2, "stepwise": True},
    "Balanced": {"max_p": 5, "max_q": 5, "stepwise": True},
    "Thorough": {"max_p": 7, "max_q": 7, "stepwise": False},
}


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([]), 0
    trimmed = values[first_valid:last_valid + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
        else:
            trimmed = trimmed[~np.isnan(trimmed)]
            nan_count = 0
    return trimmed, nan_count


def _infer_m(frequency):
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    f = (frequency or "").strip().upper()
    return freq_map.get(f, 1)


def _fit_arima(train, seasonal, m, preset_cfg):
    """Fit auto_arima model."""
    import pmdarima as pm
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        model = pm.auto_arima(
            train, seasonal=seasonal, m=m,
            stepwise=preset_cfg["stepwise"],
            max_p=preset_cfg["max_p"], max_q=preset_cfg["max_q"],
            suppress_warnings=True, error_action="ignore", trace=False,
        )
    return model


def _fit_ets(train, seasonal_periods):
    """Fit ETS model via statsmodels ExponentialSmoothing."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        # Try with trend and seasonality first, fall back to simpler
        try:
            if seasonal_periods > 1 and len(train) >= 2 * seasonal_periods:
                model = ExponentialSmoothing(
                    train, trend="add", seasonal="add",
                    seasonal_periods=seasonal_periods,
                    initialization_method="estimated",
                ).fit(optimized=True)
            else:
                model = ExponentialSmoothing(
                    train, trend="add", seasonal=None,
                    initialization_method="estimated",
                ).fit(optimized=True)
        except Exception:
            model = ExponentialSmoothing(
                train, trend=None, seasonal=None,
                initialization_method="estimated",
            ).fit(optimized=True)
    return model


def _fit_theta(train):
    """Fit Theta model via statsmodels."""
    from statsmodels.tsa.forecasting.theta import ThetaModel
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        model = ThetaModel(train, deseasonalize=False).fit()
    return model


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Combine forecasts from ETS, ARIMA, and Theta methods.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    seasonal : bool
        Whether to use seasonal models. Default False.
    m : int
        Seasonal period. Auto-inferred if not given.
    holdout_fraction : float
        Fraction of data used to compute combination weights. Default 0.2.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")
        n = len(clean)

        if n < 20:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Forecast combination needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1
        seasonal = ctx.get_param("seasonal", False)
        m_val = int(ctx.get_param("m", _infer_m(ctx.frequency)))
        if seasonal and m_val <= 1:
            m_val = _infer_m(ctx.frequency)
            if m_val <= 1:
                m_val = 12
        holdout_frac = float(ctx.get_param("holdout_fraction", 0.2))

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Split into fit and holdout for weight estimation
        n_holdout = max(5, int(n * holdout_frac))
        n_fit = n - n_holdout
        if n_fit < 15:
            n_fit = 15
            n_holdout = n - n_fit
        if n_holdout < 3:
            n_holdout = 3
            n_fit = n - n_holdout

        fit_data = clean[:n_fit]
        holdout = clean[n_fit:]
        actual_holdout_len = len(holdout)

        # Fit each model and get holdout forecasts
        model_names = []
        holdout_forecasts = {}
        full_forecasts = {}
        model_info = {}

        # --- ARIMA ---
        progress_callback("Fitting ARIMA model", 15)
        try:
            arima_model = _fit_arima(fit_data, seasonal, m_val if seasonal else 1, preset_cfg)
            arima_holdout_fc = arima_model.predict(n_periods=actual_holdout_len)
            # Refit on full data for final forecast
            arima_full = _fit_arima(clean, seasonal, m_val if seasonal else 1, preset_cfg)
            arima_final_fc = arima_full.predict(n_periods=horizon)
            model_names.append("ARIMA")
            holdout_forecasts["ARIMA"] = arima_holdout_fc
            full_forecasts["ARIMA"] = arima_final_fc
            model_info["ARIMA"] = f"({arima_full.order[0]},{arima_full.order[1]},{arima_full.order[2]})"
        except Exception as e:
            warn_list.append(f"ARIMA model failed: {e}")

        # --- ETS ---
        progress_callback("Fitting ETS model", 35)
        try:
            ets_model = _fit_ets(fit_data, m_val if seasonal else 1)
            ets_holdout_fc = ets_model.forecast(actual_holdout_len)
            ets_full = _fit_ets(clean, m_val if seasonal else 1)
            ets_final_fc = ets_full.forecast(horizon)
            model_names.append("ETS")
            holdout_forecasts["ETS"] = np.array(ets_holdout_fc)
            full_forecasts["ETS"] = np.array(ets_final_fc)
            model_info["ETS"] = "ExponentialSmoothing"
        except Exception as e:
            warn_list.append(f"ETS model failed: {e}")

        # --- Theta ---
        progress_callback("Fitting Theta model", 55)
        try:
            theta_model = _fit_theta(fit_data)
            theta_holdout_fc = theta_model.forecast(actual_holdout_len)
            theta_full = _fit_theta(clean)
            theta_final_fc = theta_full.forecast(horizon)
            model_names.append("Theta")
            holdout_forecasts["Theta"] = np.array(theta_holdout_fc)
            full_forecasts["Theta"] = np.array(theta_final_fc)
            model_info["Theta"] = "ThetaModel"
        except Exception as e:
            warn_list.append(f"Theta model failed: {e}")

        if len(model_names) < 2:
            return make_error_response(
                ctx,
                f"Only {len(model_names)} model(s) fitted successfully. "
                "Need at least 2 for combination.",
                error_fixes=[
                    "Check data quality - some models may need longer series.",
                    "Try with seasonal=True if data has seasonality.",
                ],
            )

        progress_callback("Computing combination weights", 70)

        # Compute individual holdout MSEs
        holdout_mses = {}
        for mname in model_names:
            fc = holdout_forecasts[mname]
            mse = float(np.mean((holdout - fc[:actual_holdout_len]) ** 2))
            holdout_mses[mname] = max(mse, 1e-10)  # avoid division by zero

        # --- Simple Average ---
        k = len(model_names)
        simple_weights = {m: 1.0 / k for m in model_names}

        # --- Inverse-MSE Weights ---
        inv_mses = {m: 1.0 / holdout_mses[m] for m in model_names}
        total_inv = sum(inv_mses.values())
        imse_weights = {m: inv_mses[m] / total_inv for m in model_names}

        # --- OLS Combination ---
        # Regression: actual = w1*fc1 + w2*fc2 + ... (with intercept)
        X = np.column_stack([holdout_forecasts[m][:actual_holdout_len] for m in model_names])
        X_with_const = np.column_stack([np.ones(actual_holdout_len), X])
        try:
            # OLS: beta = (X'X)^-1 X'y
            beta = np.linalg.lstsq(X_with_const, holdout, rcond=None)[0]
            ols_intercept = float(beta[0])
            ols_weights_raw = beta[1:]
            # Normalize non-negative weights
            ols_weights_raw = np.maximum(ols_weights_raw, 0)
            ols_sum = ols_weights_raw.sum()
            if ols_sum > 0:
                ols_weights = {m: float(ols_weights_raw[i] / ols_sum) for i, m in enumerate(model_names)}
            else:
                ols_weights = simple_weights.copy()
                warn_list.append("OLS weights were all non-positive. Falling back to equal weights.")
                ols_intercept = 0.0
        except Exception:
            ols_weights = simple_weights.copy()
            ols_intercept = 0.0
            warn_list.append("OLS regression failed. Using equal weights for OLS combination.")

        progress_callback("Generating combined forecasts", 80)

        # Generate combined forecasts
        def _combine(weights, intercept=0.0):
            combined = np.full(horizon, intercept)
            for m in model_names:
                combined = combined + weights[m] * full_forecasts[m][:horizon]
            return combined

        fc_simple = _combine(simple_weights)
        fc_imse = _combine(imse_weights)
        fc_ols = _combine(ols_weights, ols_intercept)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            row = [i + 1]
            for m in model_names:
                row.append(round(float(full_forecasts[m][i]), 6))
            row.extend([
                round(float(fc_simple[i]), 6),
                round(float(fc_imse[i]), 6),
                round(float(fc_ols[i]), 6),
            ])
            fc_rows.append(row)

        fc_cols = ["Step"] + model_names + ["Simple Avg", "Inv-MSE", "OLS"]
        fc_table = make_table("Combined Forecasts", fc_cols, fc_rows)

        # Weights table
        weight_rows = []
        for m in model_names:
            weight_rows.append([
                m,
                model_info.get(m, ""),
                round(holdout_mses[m], 6),
                round(simple_weights[m], 4),
                round(imse_weights[m], 4),
                round(ols_weights[m], 4),
            ])
        weight_table = make_table(
            "Combination Weights",
            ["Model", "Specification", "Holdout MSE", "Simple Wt", "Inv-MSE Wt", "OLS Wt"],
            weight_rows,
        )

        # Holdout performance
        holdout_rows = []
        combinations = {
            "Simple Average": (simple_weights, 0.0),
            "Inverse-MSE": (imse_weights, 0.0),
            "OLS": (ols_weights, ols_intercept),
        }
        for m in model_names:
            fc_h = holdout_forecasts[m][:actual_holdout_len]
            mse = holdout_mses[m]
            mae = float(np.mean(np.abs(holdout - fc_h)))
            holdout_rows.append([m, round(mse, 6), round(mae, 6)])

        for cname, (wts, intercept) in combinations.items():
            fc_h = np.full(actual_holdout_len, intercept)
            for m in model_names:
                fc_h = fc_h + wts[m] * holdout_forecasts[m][:actual_holdout_len]
            mse = float(np.mean((holdout - fc_h) ** 2))
            mae = float(np.mean(np.abs(holdout - fc_h)))
            holdout_rows.append([cname, round(mse, 6), round(mae, 6)])

        holdout_table = make_table(
            "Holdout Performance",
            ["Method", "MSE", "MAE"],
            holdout_rows,
        )

        # Find best method
        best_method = min(holdout_rows, key=lambda r: r[1])
        best_name = best_method[0]
        best_mse = best_method[1]

        # Dominant model
        dominant_model = max(imse_weights, key=imse_weights.get)
        dom_weight = imse_weights[dominant_model]

        plain_english = (
            f"Forecast combination for '{name}' ({n} observations) using {len(model_names)} models: "
            f"{', '.join(model_names)}. "
            f"On the holdout set ({actual_holdout_len} points), the best method was "
            f"'{best_name}' (MSE={best_mse:.4f}). "
            f"By inverse-MSE weighting, {dominant_model} dominates with weight {dom_weight:.2f}."
        )

        if dom_weight > 0.8:
            warn_list.append(
                f"One model ({dominant_model}) dominates the inverse-MSE weights ({dom_weight:.2f}). "
                "Combination may not offer much improvement over this single model."
            )

        charting = (
            "Line chart showing the original series and forecast continuations for each individual "
            "model plus the three combination methods (simple average, inverse-MSE, OLS). "
            "Use distinct line styles/colors. Bar chart inset showing combination weights."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[fc_table, weight_table, holdout_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "models": model_names,
                "n_holdout": actual_holdout_len,
                "holdout_mses": {m: round(holdout_mses[m], 6) for m in model_names},
                "imse_weights": {m: round(imse_weights[m], 4) for m in model_names},
                "ols_weights": {m: round(ols_weights[m], 4) for m in model_names},
                "best_holdout_method": best_name,
                "best_holdout_mse": best_mse,
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Forecast combination failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try setting seasonal=True if data has seasonality.",
                "Check that pmdarima and statsmodels are installed.",
            ],
        )
