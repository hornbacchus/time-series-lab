"""
LOESS/LOWESS Interpolation for Time Series Lab.

Uses locally weighted scatterplot smoothing (LOWESS) from statsmodels
to interpolate missing values in a time series. The smoother is fit
on observed values and used to predict at missing positions.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"frac": 0.3, "it": 1},
    "Balanced": {"frac": 0.2, "it": 3},
    "Thorough": {"frac": None, "it": 5},  # None = auto-select via CV
}


def _auto_select_frac(x_obs, y_obs, fracs=None):
    """
    Select the best LOWESS fraction via leave-one-out cross-validation
    on the observed values.
    """
    from statsmodels.nonparametric.smoothers_lowess import lowess

    if fracs is None:
        fracs = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]

    n_obs = len(x_obs)
    if n_obs < 10:
        return 0.3  # default for small samples

    best_frac = 0.3
    best_mse = float("inf")

    for frac in fracs:
        mse_total = 0.0
        for i in range(n_obs):
            # Leave one out
            mask = np.ones(n_obs, dtype=bool)
            mask[i] = False
            x_train = x_obs[mask]
            y_train = y_obs[mask]
            x_test = x_obs[i]
            y_test = y_obs[i]

            try:
                fitted = lowess(y_train, x_train, frac=frac, return_sorted=True)
                # Interpolate to get prediction at x_test
                pred = np.interp(x_test, fitted[:, 0], fitted[:, 1])
                mse_total += (y_test - pred) ** 2
            except Exception:
                mse_total += float("inf")
                break

        avg_mse = mse_total / n_obs
        if avg_mse < best_mse:
            best_mse = avg_mse
            best_frac = frac

    return best_frac


def run(ctx: RunContext, progress_callback) -> dict:
    """
    LOESS/LOWESS interpolation for missing values.

    Parameters (via ctx.params)
    ---------------------------
    frac : float, optional
        Smoothing fraction (0, 1]. Default from preset or auto-selected.
    it : int, optional
        Number of robustifying iterations. Default from preset.
    """
    try:
        progress_callback("Validating inputs", 5)

        from statsmodels.nonparametric.smoothers_lowess import lowess

        name, values = ctx.get_primary_series()
        warn_list = []
        n = len(values)

        nan_mask = np.isnan(values)
        n_missing = int(nan_mask.sum())
        n_valid = n - n_missing

        if n_missing == 0:
            return make_error_response(
                ctx,
                f"Series '{name}' has no missing values. "
                "LOESS interpolation requires at least one missing value.",
                error_fixes=["Select a series with missing values."],
            )

        if n_valid < 5:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n_valid} non-missing values. "
                "Need at least 5 valid observations.",
                error_fixes=["Provide more data points."],
            )

        missing_frac = n_missing / n
        if missing_frac > 0.5:
            warn_list.append(
                f"Over {missing_frac*100:.0f}% of the series is missing. "
                "Interpolation quality may be poor."
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Time index as numeric
        x_all = np.arange(n, dtype=float)
        x_obs = x_all[~nan_mask]
        y_obs = values[~nan_mask]

        # Determine smoothing fraction
        frac_param = ctx.get_param("frac", preset_cfg["frac"])
        if frac_param is None:
            progress_callback("Auto-selecting smoothing fraction (CV)", 15)
            frac = _auto_select_frac(x_obs, y_obs)
            warn_list.append(f"Auto-selected LOESS fraction = {frac:.2f} via LOO-CV.")
        else:
            frac = float(frac_param)
            if frac <= 0 or frac > 1:
                frac = 0.3
                warn_list.append("LOESS fraction must be in (0, 1]. Reset to 0.3.")

        it = int(ctx.get_param("it", preset_cfg["it"]))

        progress_callback("Fitting LOWESS smoother", 40)

        # Fit LOWESS on observed values
        fitted = lowess(y_obs, x_obs, frac=frac, it=it, return_sorted=True)
        # fitted is shape (n_obs, 2): sorted (x, y)

        # Interpolate at all positions (including missing)
        imputed_series = values.copy()
        smoothed_all = np.interp(x_all, fitted[:, 0], fitted[:, 1])

        for i in range(n):
            if nan_mask[i]:
                imputed_series[i] = smoothed_all[i]

        progress_callback("Computing residuals and diagnostics", 70)

        # Residuals on observed values
        observed_fitted = np.interp(x_obs, fitted[:, 0], fitted[:, 1])
        residuals = y_obs - observed_fitted
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        max_resid = float(np.max(np.abs(residuals)))

        # Build series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        series_rows = []
        for i in range(n):
            series_rows.append([
                time_col[i],
                values[i] if not nan_mask[i] else None,
                round(float(imputed_series[i]), 6),
                round(float(smoothed_all[i]), 6),
                "Imputed" if nan_mask[i] else "Observed",
            ])
        series_table = make_table(
            "Imputed Series",
            ["Time", "Original", "Imputed", "LOESS Smooth", "Status"],
            series_rows,
        )

        # Imputed values detail
        imp_rows = []
        for i in range(n):
            if nan_mask[i]:
                imp_rows.append([
                    time_col[i],
                    i + 1,
                    round(float(imputed_series[i]), 6),
                ])
        imp_table = make_table(
            "Imputed Values",
            ["Time", "Index", "Imputed Value"],
            imp_rows,
        )

        # Gap analysis
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

        # Diagnostics table
        diag_rows = [
            ["LOESS Fraction", round(frac, 4)],
            ["Robustifying Iterations", it],
            ["Total Observations", n],
            ["Missing Values", n_missing],
            ["Missing Fraction", f"{missing_frac*100:.1f}%"],
            ["Number of Gaps", n_gaps],
            ["Longest Gap", max_gap],
            ["RMSE (observed)", round(rmse, 6)],
            ["MAE (observed)", round(mae, 6)],
            ["Max |Residual|", round(max_resid, 6)],
        ]
        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        plain_english = (
            f"LOESS interpolation of '{name}' with smoothing fraction {frac:.2f}. "
            f"{n_missing} missing values in {n_gaps} gap(s) were interpolated "
            f"(longest gap: {max_gap} periods). "
            f"Smoothing RMSE on observed values: {rmse:.4f}."
        )

        if max_gap > n * 0.2:
            warn_list.append(
                f"Longest gap ({max_gap} periods) exceeds 20% of series length. "
                "Imputed values in this region may be unreliable."
            )

        # Check for extrapolation at edges
        if nan_mask[0] or nan_mask[-1]:
            warn_list.append(
                "Missing values at the series edges require extrapolation, "
                "which is less reliable than interpolation."
            )

        charting = (
            "Line chart with the LOESS smooth curve, observed values as filled dots, "
            "and imputed values as open/highlighted dots. "
            "Gap regions shaded in a light background color."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[series_table, imp_table, diag_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "frac": round(frac, 4),
                "it": it,
                "n_missing": n_missing,
                "n_gaps": n_gaps,
                "max_gap_length": max_gap,
                "missing_fraction": round(missing_frac, 4),
                "rmse_observed": round(rmse, 6),
                "mae_observed": round(mae, 6),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"LOESS interpolation failed: {e}",
            error_fixes=[
                "Ensure your data is numeric.",
                "Try a larger LOESS fraction (e.g., 0.3 or 0.5).",
                "Check that you have enough non-missing values (>=5).",
            ],
        )
