"""
Markov-Switching Regression Model for Time Series Lab.

Fits a Markov-switching model using statsmodels MarkovRegression.
Allows regime-dependent mean, variance, and autoregressive parameters.
"""

import numpy as np
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

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
    "Fast": {"k_regimes": 2, "order": 0, "switching_variance": False, "maxiter": 200},
    "Balanced": {"k_regimes": 2, "order": 1, "switching_variance": True, "maxiter": 500},
    "Thorough": {"k_regimes": 3, "order": 2, "switching_variance": True, "maxiter": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a Markov-switching regression model.

    Parameters (via ctx.params)
    ---------------------------
    k_regimes : int, optional
        Number of regimes. Default 2 (Fast/Balanced) or 3 (Thorough).
    order : int, optional
        Autoregressive order for each regime. Preset-dependent.
    switching_variance : bool, optional
        Allow variance to differ across regimes. Preset-dependent.
    switching_trend : bool, optional
        Allow intercept to differ across regimes. Default True.
    horizon : int
        Forecast horizon. Default 10.

    Series layout
    -------------
    First series -> observed time series.
    Additional series -> exogenous regressors (optional).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Exogenous
        all_series = ctx.get_all_series()
        exog_arrays = []
        exog_names = []
        for sname, svals in all_series[1:]:
            if len(svals) >= n:
                exog_arrays.append(svals[:n])
                exog_names.append(sname)

        if exog_arrays:
            exog = np.column_stack(exog_arrays)
        else:
            exog = None

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 10:
            warnings.append(f"{nan_count} missing values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
            if exog is not None:
                for col in range(exog.shape[1]):
                    nans_e = np.where(np.isnan(exog[:, col]))[0]
                    valid_e = np.where(~np.isnan(exog[:, col]))[0]
                    if len(nans_e) > 0 and len(valid_e) > 2:
                        exog[nans_e, col] = np.interp(nans_e, valid_e, exog[valid_e, col])
        elif nan_count >= n - 10:
            return make_error_response(ctx, "Too few non-missing values to fit Markov-switching model.")
        else:
            filled = values

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        k_regimes = int(ctx.get_param("k_regimes", cfg["k_regimes"]))
        order = int(ctx.get_param("order", cfg["order"]))
        switching_var = ctx.get_param("switching_variance", cfg["switching_variance"])
        switching_trend = ctx.get_param("switching_trend", True)
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        maxiter = cfg["maxiter"]

        if k_regimes < 2:
            k_regimes = 2
            warnings.append("k_regimes must be >= 2. Set to 2.")
        if k_regimes > 4:
            k_regimes = 4
            warnings.append("k_regimes capped at 4 to avoid over-parameterization.")

        min_obs = k_regimes * (order + 3) * 3
        if n < min_obs:
            return make_error_response(
                ctx,
                f"Only {n} observations for {k_regimes} regimes with AR({order}). "
                f"Need at least {min_obs}.",
                error_fixes=["Reduce k_regimes or order, or provide more data."],
            )

        progress_callback(f"Fitting Markov-switching model ({k_regimes} regimes)", 20)

        try:
            model = MarkovRegression(
                filled,
                k_regimes=k_regimes,
                order=order,
                trend="c",
                switching_trend=switching_trend,
                switching_variance=switching_var,
                exog=exog,
            )
            fit = model.fit(maxiter=maxiter, search_reps=25)
        except Exception as e1:
            # Fallback: simpler model
            warnings.append(f"Full model failed ({e1}). Trying simpler specification.")
            try:
                model = MarkovRegression(
                    filled,
                    k_regimes=2,
                    order=0,
                    trend="c",
                    switching_trend=True,
                    switching_variance=False,
                )
                fit = model.fit(maxiter=maxiter, search_reps=25)
                k_regimes = 2
                order = 0
                switching_var = False
            except Exception as e2:
                return make_error_response(
                    ctx,
                    f"Markov-switching model failed: {e2}",
                    error_fixes=[
                        "Ensure data is numeric and not constant.",
                        "Try k_regimes=2 with order=0.",
                    ],
                )

        progress_callback("Extracting regime probabilities", 55)

        # Smoothed regime probabilities
        smoothed_probs = fit.smoothed_marginal_probabilities
        if hasattr(smoothed_probs, 'values'):
            smoothed_probs = smoothed_probs.values
        smoothed_probs = np.asarray(smoothed_probs)
        if smoothed_probs.ndim == 1:
            smoothed_probs = smoothed_probs.reshape(-1, 1)

        # Most likely regime at each time
        n_probs = smoothed_probs.shape[0]
        most_likely_regime = np.argmax(smoothed_probs, axis=1)

        # Fitted values
        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = filled - fitted

        progress_callback("Extracting regime parameters", 65)

        # Regime-specific parameters
        params = fit.params
        param_names_list = params.index.tolist() if hasattr(params, 'index') else [f"p{i}" for i in range(len(params))]

        # Transition matrix
        transition_matrix = np.zeros((k_regimes, k_regimes))
        for i, pn in enumerate(param_names_list):
            if 'p[' in pn.lower() or 'regime_transition' in pn.lower():
                try:
                    val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
                    # Parse indices from parameter name
                    # e.g., "p[0->0]" or similar patterns
                    pass
                except Exception:
                    pass

        # Try to extract transition matrix from model
        try:
            tp = fit.regime_transition
            if hasattr(tp, 'values'):
                tp = tp.values
            transition_matrix = np.asarray(tp)
            if transition_matrix.ndim == 3:
                transition_matrix = transition_matrix[:, :, 0]
        except Exception:
            # Build from smoothed probabilities
            for t in range(1, n_probs):
                r_prev = most_likely_regime[t - 1]
                r_curr = most_likely_regime[t]
                if r_prev < k_regimes and r_curr < k_regimes:
                    transition_matrix[r_prev, r_curr] += 1
            row_sums = transition_matrix.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1
            transition_matrix = transition_matrix / row_sums

        progress_callback("Building output tables", 75)

        tables = []

        # ---- Regime probabilities table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= n_probs else list(range(1, n_probs + 1))
        prob_rows = []
        for t in range(n_probs):
            row = [time_col[t] if t < len(time_col) else t + 1]
            row.append(float(filled[t]) if t < n else None)
            for r in range(min(k_regimes, smoothed_probs.shape[1])):
                row.append(round(float(smoothed_probs[t, r]), 4))
            row.append(int(most_likely_regime[t]))
            prob_rows.append(row)
        regime_cols = [f"P(Regime {r})" for r in range(min(k_regimes, smoothed_probs.shape[1]))]
        tables.append(make_table(
            "Regime Probabilities",
            ["Time", name] + regime_cols + ["Most Likely Regime"],
            prob_rows,
        ))

        # ---- Transition matrix ----
        trans_rows = []
        for i in range(k_regimes):
            row = [f"From Regime {i}"]
            for j in range(k_regimes):
                row.append(round(float(transition_matrix[i, j]), 4) if i < transition_matrix.shape[0] and j < transition_matrix.shape[1] else None)
            trans_rows.append(row)
        tables.append(make_table(
            "Transition Matrix",
            [""] + [f"To Regime {j}" for j in range(k_regimes)],
            trans_rows,
        ))

        # ---- All parameters ----
        param_rows = []
        for i, pn in enumerate(param_names_list):
            val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
            param_rows.append([pn, round(val, 6)])
        tables.append(make_table("Model Parameters", ["Parameter", "Value"], param_rows))

        # ---- Regime summary ----
        regime_summary_rows = []
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            count_r = int(mask_r.sum())
            pct_r = count_r / n_probs * 100 if n_probs > 0 else 0.0
            mean_r = float(np.mean(filled[:n_probs][mask_r])) if count_r > 0 else None
            std_r = float(np.std(filled[:n_probs][mask_r], ddof=1)) if count_r > 1 else None
            regime_summary_rows.append([
                f"Regime {r}",
                count_r,
                round(pct_r, 1),
                round(mean_r, 4) if mean_r is not None else None,
                round(std_r, 4) if std_r is not None else None,
            ])
        tables.append(make_table(
            "Regime Summary",
            ["Regime", "Periods", "% of Time", "Mean", "Std Dev"],
            regime_summary_rows,
        ))

        # ---- Forecast ----
        # For Markov-switching, forecast is regime-weighted average
        progress_callback("Generating forecasts", 85)
        try:
            fc_result = fit.get_forecast(steps=horizon)
            fc_mean = fc_result.predicted_mean
            if hasattr(fc_mean, 'values'):
                fc_mean = fc_mean.values
            fc_mean = np.asarray(fc_mean, dtype=np.float64)

            ci_df = fc_result.conf_int(alpha=0.10)
            if hasattr(ci_df, 'values'):
                ci = ci_df.values
            else:
                ci = np.asarray(ci_df)

            fc_rows = []
            for h in range(horizon):
                fc_rows.append([
                    n + h + 1,
                    round(float(fc_mean[h]), 6),
                    round(float(ci[h, 0]), 6),
                    round(float(ci[h, 1]), 6),
                ])
            tables.append(make_table("Forecast", ["Step", "Forecast", "Lower 90%", "Upper 90%"], fc_rows))
        except Exception as fc_e:
            warnings.append(f"Forecasting not available for this model configuration: {fc_e}")

        # ---- Model summary ----
        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None

        # Expected regime duration
        durations = []
        for r in range(k_regimes):
            if r < transition_matrix.shape[0] and r < transition_matrix.shape[1]:
                p_stay = transition_matrix[r, r]
                dur = 1 / (1 - p_stay) if p_stay < 1 else float('inf')
                durations.append(round(dur, 2))
            else:
                durations.append(None)

        summary_rows = [
            ["Model", f"Markov-Switching (k={k_regimes}, AR={order})"],
            ["Regimes", k_regimes],
            ["AR Order", order],
            ["Switching Variance", switching_var],
            ["Observations", n],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["Forecast Horizon", horizon],
        ]
        for r in range(k_regimes):
            summary_rows.append([f"Expected Duration Regime {r}", durations[r] if r < len(durations) else None])

        if exog_names:
            summary_rows.append(["Exogenous Variables", ", ".join(exog_names)])
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        current_regime = int(most_likely_regime[-1]) if n_probs > 0 else 0
        plain = (
            f"Markov-switching model with {k_regimes} regimes fitted to '{name}' ({n} observations). "
            f"The series is currently in Regime {current_regime}. "
        )
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            if mask_r.any():
                mean_r = float(np.mean(filled[:n_probs][mask_r]))
                plain += f"Regime {r}: mean={mean_r:.4f} ({mask_r.sum()} periods). "
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += f"AIC = {fit.aic:.1f}."

        charting = (
            "Two-panel chart: (1) Original series colored by most likely regime, with "
            "regime probability bands. (2) Smoothed regime probabilities over time, "
            "one line per regime. Regime transitions shown as vertical dashed lines."
        )

        progress_callback("Done", 100)

        audit = {
            "k_regimes": k_regimes,
            "order": order,
            "switching_variance": switching_var,
            "current_regime": current_regime,
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "log_likelihood": round(float(fit.llf), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "expected_durations": durations,
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
            f"Markov-switching model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Try k_regimes=2 with order=0 as a simpler model.",
                "Check for constant series or extreme outliers.",
                "Markov-switching models can be sensitive to initial values; try again with different seed.",
            ],
        )
