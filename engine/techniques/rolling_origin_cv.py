"""
Rolling Origin Cross-Validation for Time Series Lab.

Evaluates forecast accuracy using an expanding-window (rolling origin) approach.
Computes MAE, sMAPE, MASE, and prediction interval coverage.
"""

import numpy as np
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_FOLDS = {"Fast": 2, "Balanced": 3, "Thorough": 5}


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


def _fit_auto_arima(train, seasonal, m):
    """Fit auto_arima on training data, return model."""
    import pmdarima as pm
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        model = pm.auto_arima(
            train, seasonal=seasonal, m=m,
            stepwise=True, suppress_warnings=True,
            error_action="ignore", trace=False,
            max_p=3, max_q=3, max_d=2,
        )
    return model


def _smape(actual, forecast):
    """Symmetric mean absolute percentage error."""
    denom = (np.abs(actual) + np.abs(forecast))
    mask = denom > 0
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(2.0 * np.abs(actual[mask] - forecast[mask]) / denom[mask]) * 100)


def _mase(actual, forecast, train):
    """Mean Absolute Scaled Error using in-sample naive MAE as scale."""
    naive_errors = np.abs(np.diff(train))
    scale = np.mean(naive_errors) if len(naive_errors) > 0 else 1.0
    if scale == 0:
        scale = 1.0
    return float(np.mean(np.abs(actual - forecast)) / scale)


def _infer_m(frequency):
    """Infer seasonal period from frequency string."""
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    f = (frequency or "").strip().upper()
    return freq_map.get(f, 1)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Rolling origin cross-validation.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon per fold. Default 5.
    folds : int, optional
        Number of CV folds. Default from preset (Fast=2, Balanced=3, Thorough=5).
    seasonal : bool
        Whether to use seasonal ARIMA. Default False.
    m : int
        Seasonal period. Auto-inferred if not given.
    confidence_level : float
        Confidence level for prediction intervals. Default 0.95.
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
                "Rolling origin CV needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 5))
        if horizon < 1:
            horizon = 1
        n_folds = int(ctx.get_param("folds", _PRESET_FOLDS.get(ctx.preset, 3)))
        seasonal = ctx.get_param("seasonal", False)
        m = int(ctx.get_param("m", _infer_m(ctx.frequency)))
        if seasonal and m <= 1:
            m = _infer_m(ctx.frequency)
            if m <= 1:
                m = 12
        alpha = 1.0 - float(ctx.get_param("confidence_level", 0.95))

        # Determine fold origins: space them evenly in the last portion of data
        min_train = max(20, n // 3)
        available = n - min_train - horizon
        if available < 1:
            return make_error_response(
                ctx,
                f"Series too short ({n} obs) for {n_folds} folds with horizon {horizon} "
                f"and minimum training size {min_train}.",
                error_fixes=[
                    "Reduce the number of folds or the forecast horizon.",
                    "Provide a longer series.",
                ],
            )

        if n_folds > available:
            n_folds = available
            warn_list.append(f"Reduced folds to {n_folds} due to series length.")

        # Evenly spaced origins
        if n_folds == 1:
            origins = [min_train]
        else:
            step = available / (n_folds - 1) if n_folds > 1 else 1
            origins = [min_train + int(round(i * step)) for i in range(n_folds)]

        progress_callback("Running cross-validation folds", 15)

        fold_rows = []
        all_mae = []
        all_smape = []
        all_mase = []
        all_coverage = []

        for fold_idx, origin in enumerate(origins):
            pct = 15 + int(70 * (fold_idx / n_folds))
            progress_callback(f"Fold {fold_idx + 1}/{n_folds}", pct)

            train = clean[:origin]
            actual_end = min(origin + horizon, n)
            actual = clean[origin:actual_end]
            h = len(actual)
            if h == 0:
                continue

            try:
                model = _fit_auto_arima(train, seasonal, m if seasonal else 1)
                fc, conf_int = model.predict(n_periods=h, return_conf_int=True, alpha=alpha)
            except Exception as e:
                warn_list.append(f"Fold {fold_idx + 1} failed: {e}")
                continue

            # Metrics
            mae_val = float(np.mean(np.abs(actual - fc)))
            smape_val = _smape(actual, fc)
            mase_val = _mase(actual, fc, train)

            # Coverage: fraction of actual values within prediction intervals
            in_interval = np.sum((actual >= conf_int[:, 0]) & (actual <= conf_int[:, 1]))
            coverage = float(in_interval / h) * 100

            all_mae.append(mae_val)
            all_smape.append(smape_val)
            all_mase.append(mase_val)
            all_coverage.append(coverage)

            order_str = f"({model.order[0]},{model.order[1]},{model.order[2]})"
            fold_rows.append([
                fold_idx + 1,
                origin,
                h,
                order_str,
                round(mae_val, 4),
                round(smape_val, 2),
                round(mase_val, 4),
                round(coverage, 1),
            ])

        if len(fold_rows) == 0:
            return make_error_response(
                ctx,
                "All cross-validation folds failed. The data may be unsuitable for ARIMA modeling.",
                error_fixes=[
                    "Check for constant or near-constant series.",
                    "Try a longer series or fewer folds.",
                ],
            )

        progress_callback("Building output", 90)

        fold_table = make_table(
            "Fold Results",
            ["Fold", "Train Size", "Test Size", "Order", "MAE", "sMAPE%", "MASE", "Coverage%"],
            fold_rows,
        )

        # Aggregate metrics
        avg_mae = float(np.mean(all_mae))
        avg_smape = float(np.mean(all_smape))
        avg_mase = float(np.mean(all_mase))
        avg_coverage = float(np.mean(all_coverage))
        std_mae = float(np.std(all_mae, ddof=1)) if len(all_mae) > 1 else 0.0
        std_smape = float(np.std(all_smape, ddof=1)) if len(all_smape) > 1 else 0.0

        summary_rows = [
            ["Mean MAE", round(avg_mae, 4)],
            ["Std MAE", round(std_mae, 4)],
            ["Mean sMAPE (%)", round(avg_smape, 2)],
            ["Std sMAPE (%)", round(std_smape, 2)],
            ["Mean MASE", round(avg_mase, 4)],
            ["Mean Coverage (%)", round(avg_coverage, 1)],
            ["Target Coverage (%)", round((1.0 - alpha) * 100, 1)],
            ["Folds Completed", len(fold_rows)],
            ["Horizon", horizon],
            ["Series Length", n],
        ]
        summary_table = make_table("Aggregate Metrics", ["Metric", "Value"], summary_rows)

        # Interpretation
        target_cov = (1.0 - alpha) * 100
        if avg_coverage < target_cov - 10:
            warn_list.append(
                f"Average coverage ({avg_coverage:.1f}%) is well below the target "
                f"({target_cov:.0f}%). Prediction intervals may be too narrow."
            )
        if avg_mase > 1.0:
            warn_list.append(
                "Mean MASE > 1.0 indicates the model performs worse than a naive forecast on average."
            )

        # Plain English
        quality = "well" if avg_mase < 0.8 else ("adequately" if avg_mase < 1.2 else "poorly")
        plain_english = (
            f"Rolling origin cross-validation of '{name}' with {len(fold_rows)} folds "
            f"and horizon {horizon}. The auto-ARIMA model forecasts {quality} "
            f"(mean MASE={avg_mase:.3f}, mean sMAPE={avg_smape:.1f}%). "
            f"Prediction interval coverage averages {avg_coverage:.1f}% "
            f"vs. {target_cov:.0f}% target."
        )

        charting = (
            "Bar chart comparing MAE/sMAPE/MASE across folds. "
            "Secondary panel: coverage percentage per fold with a horizontal line at the target coverage. "
            "Optionally show each fold's forecast vs. actual as small multiples."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[fold_table, summary_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "n_folds": len(fold_rows),
                "horizon": horizon,
                "mean_mae": round(avg_mae, 4),
                "mean_smape": round(avg_smape, 2),
                "mean_mase": round(avg_mase, 4),
                "mean_coverage": round(avg_coverage, 1),
                "target_coverage": round(target_cov, 1),
                "seasonal": seasonal,
                "m": m,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Rolling origin CV failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations.",
                "Try fewer folds or a smaller forecast horizon.",
                "Check for constant or near-constant series.",
            ],
        )
