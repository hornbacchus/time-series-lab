"""
Kalman Smoother Imputation for Time Series Lab.

Uses a local linear trend state-space model (UnobservedComponents from statsmodels)
to impute missing values via the Kalman smoother. The smoother provides optimal
estimates and uncertainty bounds for each imputed value.
"""

import numpy as np
import warnings as _warnings

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
)


_PRESET_CONFIG = {
    "Fast": {"model": "local level"},
    "Balanced": {"model": "local linear trend"},
    "Thorough": {"model": "local linear trend"},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Kalman smoother imputation for missing values.

    Parameters (via ctx.params)
    ---------------------------
    model_type : str, optional
        "local level" or "local linear trend". Default from preset.
    confidence_level : float, optional
        Confidence level for imputation intervals. Default 0.95.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        n = len(values)

        # Identify missing positions
        nan_mask = np.isnan(values)
        n_missing = int(nan_mask.sum())
        n_valid = n - n_missing

        if n_missing == 0:
            return make_error_response(
                ctx,
                f"Series '{name}' has no missing values. "
                "Kalman imputation requires at least one missing value.",
                error_fixes=[
                    "This technique is designed for filling gaps in time series.",
                    "Select a series with missing values.",
                ],
            )

        if n_valid < 5:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n_valid} non-missing values. "
                "Need at least 5 valid observations for Kalman imputation.",
                error_fixes=["Provide more data points."],
            )

        missing_frac = n_missing / n
        if missing_frac > 0.5:
            warn_list.append(
                f"Over {missing_frac*100:.0f}% of the series is missing. "
                "Imputation quality may be poor."
            )

        conf_level = float(ctx.get_param("confidence_level", 0.95))
        alpha = 1.0 - conf_level

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        model_type = ctx.get_param("model_type", preset_cfg["model"])
        # CAI Phase 2 Session 19 fix (F-MD-KALMAN-MODELTYPE):
        # explicit allowlist gate. Pre-fix, invalid `model_type`
        # silently fell through the if/else chain to "local linear
        # trend" default; audit_fields recorded user's invalid
        # value verbatim. Session 18 silent-fall-through pattern.
        _MODEL_TYPE_OPTS = ("local level", "local linear trend")
        if model_type not in _MODEL_TYPE_OPTS:
            return make_error_response(
                ctx,
                f"Unknown model_type '{model_type}'. Must be one "
                f"of: {', '.join(_MODEL_TYPE_OPTS)}.",
                error_fixes=[
                    "Use 'local level' (random walk + noise; "
                    "minimal model) or 'local linear trend' "
                    "(default for non-Fast presets; adds "
                    "stochastic slope state).",
                ],
            )

        progress_callback("Fitting state-space model", 20)

        from statsmodels.tsa.statespace.structural import UnobservedComponents

        # Create series with NaN where missing (statsmodels handles this)
        series = values.copy()

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            if model_type == "local level":
                model = UnobservedComponents(series, level="local level")
            else:
                model = UnobservedComponents(series, level="local linear trend")

            try:
                result = model.fit(disp=False, maxiter=500)
            except Exception:
                # Fall back to simpler model
                warn_list.append(
                    f"Model '{model_type}' failed to converge. Falling back to local level."
                )
                model = UnobservedComponents(series, level="local level")
                result = model.fit(disp=False, maxiter=500)
                model_type = "local level"

        progress_callback("Running Kalman smoother", 50)

        # Get smoothed state (level) which provides imputed values
        smoothed_state = result.smoothed_state[0]  # level component
        smoothed_state_cov = result.smoothed_state_cov[0, 0]  # variance of level

        # The fitted values from the model represent the smoothed estimates
        # For observed values, this is close to the actual; for missing, it's the imputation
        imputed_series = values.copy()
        imputed_values_info = []

        # The confidence band around each imputed value is ± z * posterior_se
        # where posterior_se comes from the Kalman smoother's state
        # covariance. Coverage is correct under model-specification (the
        # chosen UnobservedComponents variant captures the true dynamics).
        # If the model is misspecified, the reported band understates true
        # imputation uncertainty — disclose this honestly rather than
        # applying a pseudo-correction that the state-space math does not
        # support.
        from scipy import stats as sp_stats
        z = sp_stats.norm.ppf(1.0 - alpha / 2)

        for i in range(n):
            if nan_mask[i]:
                imputed_val = smoothed_state[i]
                # Confidence interval from smoothed state covariance
                if isinstance(smoothed_state_cov, np.ndarray) and smoothed_state_cov.ndim > 0:
                    se = np.sqrt(max(0, smoothed_state_cov[i]))
                else:
                    se = np.sqrt(max(0, float(smoothed_state_cov)))
                ci_lo = imputed_val - z * se
                ci_hi = imputed_val + z * se
                imputed_series[i] = imputed_val
                imputed_values_info.append((i, imputed_val, se, ci_lo, ci_hi))

        progress_callback("Building output", 80)

        # Full series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        series_rows = []
        for i in range(n):
            series_rows.append([
                time_col[i],
                values[i] if not nan_mask[i] else None,
                round(float(imputed_series[i]), 6),
                "Imputed" if nan_mask[i] else "Observed",
            ])
        series_table = make_table(
            "Imputed Series",
            ["Time", "Original", "Imputed", "Status"],
            series_rows,
        )

        # Imputed values detail table
        ci_label = f"{conf_level*100:.0f}%"
        imp_rows = []
        for idx, val, se, lo, hi in imputed_values_info:
            imp_rows.append([
                time_col[idx],
                idx + 1,
                round(val, 6),
                round(se, 6),
                round(lo, 6),
                round(hi, 6),
            ])
        imp_table = make_table(
            "Imputed Values Detail",
            ["Time", "Index", "Imputed Value", "Std Error", f"Lower {ci_label}", f"Upper {ci_label}"],
            imp_rows,
        )

        # Diagnostics
        # Compute residuals on observed values
        observed_residuals = []
        for i in range(n):
            if not nan_mask[i]:
                observed_residuals.append(values[i] - smoothed_state[i])
        observed_residuals = np.array(observed_residuals)

        rmse = float(np.sqrt(np.mean(observed_residuals ** 2))) if len(observed_residuals) > 0 else None
        mae = float(np.mean(np.abs(observed_residuals))) if len(observed_residuals) > 0 else None

        # Gap analysis: identify contiguous gaps
        gap_starts = []
        gap_lengths = []
        in_gap = False
        for i in range(n):
            if nan_mask[i]:
                if not in_gap:
                    gap_starts.append(i)
                    in_gap = True
            else:
                if in_gap:
                    gap_lengths.append(i - gap_starts[-1])
                    in_gap = False
        if in_gap:
            gap_lengths.append(n - gap_starts[-1])

        max_gap = max(gap_lengths) if gap_lengths else 0
        n_gaps = len(gap_lengths)

        diag_rows = [
            ["Model", model_type.title()],
            ["Total Observations", n],
            ["Missing Values", n_missing],
            ["Missing Fraction", f"{missing_frac*100:.1f}%"],
            ["Number of Gaps", n_gaps],
            ["Longest Gap", max_gap],
            ["Smoothing RMSE (observed)", round(rmse, 6) if rmse else "N/A"],
            ["Smoothing MAE (observed)", round(mae, 6) if mae else "N/A"],
            ["Log-Likelihood", round(float(result.llf), 2)],
            ["AIC", round(float(result.aic), 2)],
        ]
        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        # Plain English
        avg_se = float(np.mean([info[2] for info in imputed_values_info])) if imputed_values_info else 0
        plain_english = (
            f"Kalman smoother imputation of '{name}' using a {model_type} model. "
            f"{n_missing} missing values in {n_gaps} gap(s) were imputed "
            f"(longest gap: {max_gap} periods). "
            f"Average standard error of imputed values: {avg_se:.4f}."
        )
        if rmse is not None:
            plain_english += f" Model RMSE on observed values: {rmse:.4f}."
        if max_gap > n * 0.2:
            warn_list.append(
                f"The longest gap ({max_gap} periods) is over 20% of the series length. "
                "Imputed values in this region have high uncertainty."
            )

        warn_list.append(
            "Imputation confidence bands assume the chosen state-space model "
            "captures the true dynamics. If residual diagnostics show "
            "unexplained structure (check Ljung-Box via the Structural TS "
            "technique on the same series), the reported bands understate "
            "true uncertainty — consider a bootstrap re-fit for calibrated "
            "coverage."
        )

        charting = (
            "Line chart of the imputed series with observed values as solid dots and "
            f"imputed values as open circles with {ci_label} error bars or shaded intervals. "
            "Highlight gap regions with a light background shading."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("kalman_imputation", {
            "series_name": name,
            "n_obs": int(n),
            "n_missing": int(n_missing),
            "model_type": model_type,
            "n_gaps": int(n_gaps),
            "max_gap": int(max_gap),
            "avg_imputation_se": float(avg_se),
            "rmse": float(rmse) if rmse else None,
            "aic": float(result.aic),
        })
        return make_response(
            ctx,
            tables=[series_table, imp_table, diag_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "model_type": model_type,
                "n_missing": n_missing,
                "n_gaps": n_gaps,
                "max_gap_length": max_gap,
                "missing_fraction": round(missing_frac, 4),
                "rmse_observed": round(rmse, 6) if rmse else None,
                "aic": round(float(result.aic), 2),
                "avg_imputation_se": round(avg_se, 6),
                **format_significance_disclosure(
                    test_name="Kalman smoother state-covariance credible band",
                    critical_value_formula=(
                        "imputed ± z(1-α/2) · sqrt(smoothed_state_cov) from "
                        "statsmodels.tsa.statespace.structural.UnobservedComponents"
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
            f"Kalman imputation failed: {e}",
            error_fixes=[
                "Ensure your data is numeric.",
                "Try model_type='local level' if 'local linear trend' fails.",
                "Check that you have enough non-missing values (>=5).",
                "Ensure statsmodels is installed.",
            ],
        )
