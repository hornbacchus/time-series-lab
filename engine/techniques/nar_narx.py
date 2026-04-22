"""
NAR / NARX Nonlinear AutoRegressive Model for Time Series Lab.

Implements Nonlinear AutoRegressive (NAR) and Nonlinear AutoRegressive
with eXogenous inputs (NARX) using a Multi-Layer Perceptron (MLP) from
scikit-learn. Supports configurable hidden layer architecture.
"""

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit

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
    "Fast": {
        "hidden_layers": (10,),
        "max_iter": 200,
        "ar_lags": 3,
        "cv_folds": 0,
    },
    "Balanced": {
        "hidden_layers": (20, 10),
        "max_iter": 500,
        "ar_lags": 5,
        "cv_folds": 3,
    },
    "Thorough": {
        "hidden_layers": (50, 25, 10),
        "max_iter": 1000,
        "ar_lags": 8,
        "cv_folds": 5,
    },
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a NAR/NARX model using MLP.

    Parameters (via ctx.params)
    ---------------------------
    ar_lags : int, optional
        Number of autoregressive lags. Preset-dependent.
    hidden_layers : list[int], optional
        Hidden layer sizes. Preset-dependent.
    activation : str, optional
        'relu' (default), 'tanh', 'logistic'.
    learning_rate_init : float, optional
        Initial learning rate. Default 0.001.
    alpha : float, optional
        L2 regularization strength. Default 0.0001.
    horizon : int
        Forecast horizon. Default 10.
    exog_lags : int, optional
        Number of lags for exogenous variables. Default = ar_lags.

    Series layout
    -------------
    First series -> endogenous target (y).
    Additional series -> exogenous inputs (x).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, y = ctx.get_primary_series()
        n = len(y)

        # Exogenous
        all_series = ctx.get_all_series()
        exog_names = []
        exog_arrays = []
        for sname, svals in all_series[1:]:
            exog_names.append(sname)
            exog_arrays.append(svals)

        for ex in ctx.exog:
            arr = np.array(ex.get("values", []), dtype=np.float64)
            exog_arrays.append(arr)
            exog_names.append(ex.get("name", f"Exog{len(exog_names)+1}"))

        has_exog = len(exog_arrays) > 0
        model_name = "NARX" if has_exog else "NAR"

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        ar_lags = int(ctx.get_param("ar_lags", cfg["ar_lags"]))
        exog_lags = int(ctx.get_param("exog_lags", ar_lags))
        hidden_param = ctx.get_param("hidden_layers")
        if hidden_param is not None:
            if isinstance(hidden_param, (list, tuple)):
                hidden_layers = tuple(int(x) for x in hidden_param)
            else:
                hidden_layers = (int(hidden_param),)
        else:
            hidden_layers = cfg["hidden_layers"]
        activation = ctx.get_param("activation", "relu")
        lr_init = float(ctx.get_param("learning_rate_init", 0.001))
        alpha_reg = float(ctx.get_param("alpha", 0.0001))
        max_iter = int(ctx.get_param("max_iter", cfg["max_iter"]))
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        cv_folds = int(ctx.get_param("cv_folds", cfg["cv_folds"]))

        # Handle NaN in target
        nan_count = int(np.isnan(y).sum())
        if nan_count > 0 and nan_count < n - ar_lags - 5:
            warnings.append(f"{nan_count} NaN values in target linearly interpolated.")
            nans = np.where(np.isnan(y))[0]
            valid = np.where(~np.isnan(y))[0]
            y_filled = y.copy()
            y_filled[nans] = np.interp(nans, valid, y[valid])
        elif nan_count >= n - ar_lags - 5:
            return make_error_response(ctx, "Too few non-missing target values.")
        else:
            y_filled = y.copy()

        # Handle exogenous NaN
        if has_exog:
            min_len = min(n, *(len(a) for a in exog_arrays))
            if min_len < n:
                warnings.append(f"Exogenous series trimmed to length {min_len}.")
                n = min_len
                y_filled = y_filled[:n]
            for i in range(len(exog_arrays)):
                arr = exog_arrays[i][:n].copy()
                nans_e = np.where(np.isnan(arr))[0]
                if len(nans_e) > 0:
                    valid_e = np.where(~np.isnan(arr))[0]
                    if len(valid_e) > 2:
                        arr[nans_e] = np.interp(nans_e, valid_e, arr[valid_e])
                    else:
                        warnings.append(f"Exogenous '{exog_names[i]}' has too many NaN; filled with mean.")
                        arr[nans_e] = np.nanmean(arr)
                exog_arrays[i] = arr

        max_lag = max(ar_lags, exog_lags if has_exog else 0)
        effective_n = n - max_lag

        if effective_n < 15:
            return make_error_response(
                ctx,
                f"Only {effective_n} effective observations after lagging. Need at least 15.",
                error_fixes=["Reduce ar_lags or provide more data."],
            )

        progress_callback("Building feature matrix", 15)

        # Build feature matrix
        feature_names = []
        feature_cols = []

        # AR lags
        for lag in range(1, ar_lags + 1):
            col = y_filled[max_lag - lag: n - lag]
            feature_cols.append(col)
            feature_names.append(f"{name}_lag{lag}")

        # Exogenous lags
        if has_exog:
            for ex_idx, (ex_name, ex_arr) in enumerate(zip(exog_names, exog_arrays)):
                for lag in range(0, exog_lags + 1):
                    if lag == 0:
                        col = ex_arr[max_lag:]
                    else:
                        col = ex_arr[max_lag - lag: n - lag]
                    feature_cols.append(col)
                    feature_names.append(f"{ex_name}_lag{lag}")

        X = np.column_stack(feature_cols)
        y_target = y_filled[max_lag:]

        # Standardize
        scaler_X = StandardScaler()
        scaler_y = StandardScaler()
        X_scaled = scaler_X.fit_transform(X)
        y_scaled = scaler_y.fit_transform(y_target.reshape(-1, 1)).ravel()

        progress_callback("Fitting MLP model", 25)

        # Cross-validation for error estimation
        cv_rmse = None
        if cv_folds > 1 and effective_n > 30:
            tscv = TimeSeriesSplit(n_splits=cv_folds)
            cv_errors = []
            for train_idx, test_idx in tscv.split(X_scaled):
                mlp_cv = MLPRegressor(
                    hidden_layer_sizes=hidden_layers,
                    activation=activation,
                    learning_rate_init=lr_init,
                    alpha=alpha_reg,
                    max_iter=max_iter,
                    random_state=ctx.seed,
                    early_stopping=True,
                    validation_fraction=0.1,
                )
                mlp_cv.fit(X_scaled[train_idx], y_scaled[train_idx])
                pred_cv = mlp_cv.predict(X_scaled[test_idx])
                pred_orig = scaler_y.inverse_transform(pred_cv.reshape(-1, 1)).ravel()
                actual_orig = y_target[test_idx]
                cv_errors.append(float(np.sqrt(np.mean((pred_orig - actual_orig) ** 2))))
            cv_rmse = float(np.mean(cv_errors))
            progress_callback(f"Cross-validation RMSE: {cv_rmse:.4f}", 45)

        # Fit final model on all data
        progress_callback("Training final model", 50)
        mlp = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation=activation,
            learning_rate_init=lr_init,
            alpha=alpha_reg,
            max_iter=max_iter,
            random_state=ctx.seed,
            early_stopping=True,
            validation_fraction=0.1,
        )
        mlp.fit(X_scaled, y_scaled)

        # In-sample fitted values
        fitted_scaled = mlp.predict(X_scaled)
        fitted_orig = scaler_y.inverse_transform(fitted_scaled.reshape(-1, 1)).ravel()
        residuals = y_target - fitted_orig
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))

        progress_callback("Generating forecasts", 65)

        # Multi-step forecast (iterative)
        fc = np.zeros(horizon)
        y_history = list(y_filled[-max_lag:])
        if has_exog:
            exog_last = [arr[-exog_lags - 1:].tolist() for arr in exog_arrays]
        else:
            exog_last = None

        for h in range(horizon):
            x_h = []
            # AR features
            for lag in range(1, ar_lags + 1):
                x_h.append(y_history[-lag])
            # Exogenous features (carry forward last known values)
            if has_exog:
                for ex_idx in range(len(exog_arrays)):
                    for lag in range(0, exog_lags + 1):
                        # Use last known exogenous value
                        idx = -(lag + 1) if lag < len(exog_last[ex_idx]) else 0
                        x_h.append(exog_last[ex_idx][idx])

            x_h = np.array(x_h).reshape(1, -1)
            x_h_scaled = scaler_X.transform(x_h)
            pred_scaled = mlp.predict(x_h_scaled)
            pred = scaler_y.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()[0]
            fc[h] = pred
            y_history.append(pred)

        # Forecast uncertainty via bootstrap residuals
        n_boot = 200
        fc_boot = np.zeros((n_boot, horizon))
        resid_pool = residuals.copy()

        for b in range(n_boot):
            y_hist_b = list(y_filled[-max_lag:])
            for h in range(horizon):
                x_h = []
                for lag in range(1, ar_lags + 1):
                    x_h.append(y_hist_b[-lag])
                if has_exog:
                    for ex_idx in range(len(exog_arrays)):
                        for lag in range(0, exog_lags + 1):
                            idx = -(lag + 1) if lag < len(exog_last[ex_idx]) else 0
                            x_h.append(exog_last[ex_idx][idx])

                x_h = np.array(x_h).reshape(1, -1)
                x_h_scaled = scaler_X.transform(x_h)
                pred_scaled = mlp.predict(x_h_scaled)
                pred = scaler_y.inverse_transform(pred_scaled.reshape(-1, 1)).ravel()[0]
                pred += resid_pool[np.random.randint(len(resid_pool))]
                fc_boot[b, h] = pred
                y_hist_b.append(pred)

        fc_q05 = np.percentile(fc_boot, 5, axis=0)
        fc_q95 = np.percentile(fc_boot, 95, axis=0)

        progress_callback("Building output tables", 80)

        tables = []

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc[h]), 6),
                round(float(fc_q05[h]), 6),
                round(float(fc_q95[h]), 6),
            ])
        tables.append(make_table("Forecast", ["Step", "Forecast", "Lower 90%", "Upper 90%"], fc_rows))

        # ---- Fitted values table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else list(range(1, n + 1))
        fit_rows = []
        for t in range(effective_n):
            fit_rows.append([
                time_col[max_lag + t] if max_lag + t < len(time_col) else max_lag + t + 1,
                round(float(y_target[t]), 6),
                round(float(fitted_orig[t]), 6),
                round(float(residuals[t]), 6),
            ])
        tables.append(make_table(
            "Fitted Values",
            ["Time", name, "Fitted", "Residual"],
            fit_rows,
        ))

        # ---- Feature importance (permutation-based) ----
        progress_callback("Computing feature importance", 88)
        importances = _permutation_importance(mlp, X_scaled, y_scaled, feature_names, ctx.seed)
        imp_rows = []
        for fname, imp in sorted(importances.items(), key=lambda x: -x[1]):
            imp_rows.append([fname, round(imp, 4)])
        tables.append(make_table("Feature Importance (Permutation)", ["Feature", "Importance"], imp_rows))

        # ---- Network architecture ----
        arch_rows = [
            ["Input Features", X.shape[1]],
            ["Hidden Layers", str(hidden_layers)],
            ["Activation", activation],
            ["Total Parameters", sum(
                np.prod(w.shape) for w in mlp.coefs_
            ) + sum(len(b) for b in mlp.intercepts_)],
            ["Training Iterations", mlp.n_iter_],
            ["Final Loss", round(float(mlp.loss_), 6)],
        ]
        tables.append(make_table("Network Architecture", ["Property", "Value"], arch_rows))

        # ---- Model summary ----
        r_squared = 1 - np.sum(residuals ** 2) / np.sum((y_target - np.mean(y_target)) ** 2)
        summary_rows = [
            ["Model", model_name],
            ["AR Lags", ar_lags],
            ["Exogenous Variables", ", ".join(exog_names) if has_exog else "None"],
            ["Exogenous Lags", exog_lags if has_exog else "N/A"],
            ["Hidden Layers", str(hidden_layers)],
            ["Activation", activation],
            ["L2 Regularization (alpha)", alpha_reg],
            ["Observations (effective)", effective_n],
            ["RMSE (in-sample)", round(rmse, 4)],
            ["MAE (in-sample)", round(mae, 4)],
            ["R-squared", round(float(r_squared), 4)],
        ]
        if cv_rmse is not None:
            summary_rows.append(["RMSE (CV)", round(cv_rmse, 4)])
        summary_rows.append(["Forecast Horizon", horizon])
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Residual diagnostics ----
        progress_callback("Residual diagnostics", 92)
        diag_rows = []
        if len(residuals) > 1:
            diag_rows.append(["Residual Mean", round(float(np.mean(residuals)), 6)])
            diag_rows.append(["Residual Std", round(float(np.std(residuals, ddof=1)), 6)])
        if len(residuals) > 10:
            from scipy import stats as sp_stats
            jb, jb_p = sp_stats.jarque_bera(residuals)
            diag_rows.append(["Jarque-Bera", round(float(jb), 4)])
            diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
            if jb_p < 0.05:
                warnings.append("Residuals may not be normally distributed.")
            dw = float(np.sum(np.diff(residuals) ** 2) / np.sum(residuals ** 2))
            diag_rows.append(["Durbin-Watson", round(dw, 4)])
            if dw < 1.5:
                warnings.append(
                    f"Durbin-Watson={dw:.2f} suggests residual autocorrelation. "
                    "Consider increasing ar_lags."
                )
        tables.append(make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows))

        # Overfitting check
        if cv_rmse is not None and cv_rmse > rmse * 1.5:
            warnings.append(
                f"CV RMSE ({cv_rmse:.4f}) is much larger than in-sample RMSE ({rmse:.4f}), "
                "suggesting overfitting. Try increasing alpha (regularization) or reducing hidden layers."
            )

        if has_exog:
            warnings.append(
                "Future exogenous values not available; last observed values are carried forward "
                "for multi-step forecasting."
            )

        # ---- Plain English ----
        plain = (
            f"{model_name} model (MLP with {hidden_layers} architecture) fitted to '{name}' "
            f"({effective_n} effective observations). "
        )
        if has_exog:
            plain += f"Exogenous inputs: {', '.join(exog_names)}. "
        plain += f"In-sample RMSE = {rmse:.4f}, R-squared = {r_squared:.3f}. "
        if cv_rmse is not None:
            plain += f"Cross-validated RMSE = {cv_rmse:.4f}. "
        plain += f"{horizon}-step forecast produced with bootstrap confidence intervals."

        # Most important feature
        top_feature = max(importances, key=importances.get) if importances else None
        if top_feature:
            plain += f" Most important feature: {top_feature}."

        charting = (
            "Line chart with original series, fitted values, and forecast continuation "
            "with 90% confidence band. Bar chart of feature importance. "
            "Scatter plot of actual vs predicted values."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _top_features = [
            {"name": str(fn), "importance": round(float(imp), 4)}
            for fn, imp in sorted(importances.items(), key=lambda x: -x[1])[:5]
        ]
        _series_mean = float(np.mean(y))
        _series_std = float(np.std(y, ddof=1)) if len(y) > 1 else 0.0
        _last_observed_value = float(y[-1])
        # For nar_narx, `fc` is the forecast array
        _forecast_end_value = None
        try:
            _forecast_end_value = float(fc[-1])
        except Exception:
            pass

        audit = {
            "model": model_name,
            "ar_lags": ar_lags,
            "exogenous": exog_names,
            "exog_lags": exog_lags if has_exog else None,
            "hidden_layers": list(hidden_layers),
            "activation": activation,
            "alpha_reg": alpha_reg,
            "rmse_insample": round(rmse, 4),
            "mae_insample": round(mae, 4),
            "r_squared": round(float(r_squared), 4),
            "rmse_cv": round(cv_rmse, 4) if cv_rmse is not None else None,
            "n_effective": effective_n,
            "n_features": X.shape[1],
            "n_params": int(sum(np.prod(w.shape) for w in mlp.coefs_) + sum(len(b) for b in mlp.intercepts_)),
            "training_iters": int(mlp.n_iter_),
            "horizon": horizon,
            "top_feature": top_feature,
            "top_features": _top_features,
            "series_mean": round(_series_mean, 6),
            "series_std": round(_series_std, 6),
            "last_observed_value": round(_last_observed_value, 6),
            "forecast_end_value": round(_forecast_end_value, 6) if _forecast_end_value is not None else None,
            "n_obs": int(len(y)),
            "series_name": name,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("nar_narx", dict(audit))

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
            f"{model_name if 'model_name' in dir() else 'NAR/NARX'} model failed: {e}",
            error_fixes=[
                "Ensure all series are numeric.",
                "Try reducing ar_lags or hidden layer sizes.",
                "Increase max_iter if the model didn't converge.",
                "Try activation='tanh' if 'relu' fails.",
            ],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _permutation_importance(model, X, y, feature_names, seed, n_repeats=5):
    """Simple permutation importance."""
    rng = np.random.RandomState(seed)
    baseline = float(np.mean((model.predict(X) - y) ** 2))
    importances = {}

    for i, fname in enumerate(feature_names):
        scores = []
        for _ in range(n_repeats):
            X_perm = X.copy()
            X_perm[:, i] = rng.permutation(X_perm[:, i])
            score = float(np.mean((model.predict(X_perm) - y) ** 2))
            scores.append(score - baseline)
        importances[fname] = float(np.mean(scores))

    # Normalize
    max_imp = max(importances.values()) if importances else 1.0
    if max_imp > 0:
        importances = {k: v / max_imp for k, v in importances.items()}

    return importances
