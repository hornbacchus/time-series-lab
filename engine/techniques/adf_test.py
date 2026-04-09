"""
Augmented Dickey-Fuller (ADF) unit root test for Time Series Lab.

Tests the null hypothesis that a unit root is present (series is non-stationary).
Rejecting H0 suggests the series is stationary.
"""

import numpy as np
from statsmodels.tsa.stattools import adfuller

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Augmented Dickey-Fuller test on one or more series.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        Regression type: 'c' (constant only, default), 'ct' (constant + trend),
        'ctt' (constant + linear + quadratic trend), 'n' (no constant).
    max_lag : int or None, optional
        Maximum lag for the test. None = auto-select via AIC (default).
    autolag : str, optional
        Method for automatic lag selection: 'AIC' (default), 'BIC', 't-stat', None.
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
        max_lag_param = ctx.get_param("max_lag", None)
        maxlag = int(max_lag_param) if max_lag_param is not None else None
        autolag_param = ctx.get_param("autolag", "AIC")
        # If user provided a fixed maxlag with no autolag, disable autolag
        if max_lag_param is not None and autolag_param is None:
            autolag = None
        else:
            autolag = autolag_param
        significance = ctx.get_param("significance_level", 0.05)

        warnings = []
        result_rows = []
        all_summaries = []
        detail_tables = []

        progress_callback("Running ADF tests", 15)

        for idx, (name, values) in enumerate(all_series):
            pct = 15 + int(70 * (idx + 1) / len(all_series))
            progress_callback(f"Testing '{name}'", pct)

            # Drop NaN from edges, interpolate interior if needed
            clean = _prepare_series(values, name, warnings)
            n = len(clean)

            if n < 12:
                result_rows.append([
                    name, None, None, None, None, None, n, "Too few observations (need >= 12)"
                ])
                all_summaries.append(f"'{name}': insufficient data ({n} observations).")
                continue

            try:
                adf_stat, p_value, used_lag, nobs, critical_values, ic_best = adfuller(
                    clean,
                    maxlag=maxlag,
                    regression=regression,
                    autolag=autolag,
                )
            except Exception as e:
                result_rows.append([name, None, None, None, None, None, n, str(e)])
                all_summaries.append(f"'{name}': test failed ({e}).")
                continue

            stationary = p_value < significance
            decision = "Stationary" if stationary else "Non-Stationary"

            result_rows.append([
                name,
                round(adf_stat, 4),
                round(p_value, 6),
                used_lag,
                nobs,
                decision,
                n,
                "",
            ])

            # Critical values sub-table
            cv_rows = []
            for level, cv in sorted(critical_values.items()):
                cv_rows.append([level, round(cv, 4), "Yes" if adf_stat < cv else "No"])
            cv_table = make_table(
                f"Critical Values - {name}",
                ["Significance Level", "Critical Value", "Reject H0?"],
                cv_rows,
            )
            detail_tables.append(cv_table)

            # Summary sentence
            if stationary:
                all_summaries.append(
                    f"'{name}' is stationary (ADF={adf_stat:.4f}, p={p_value:.4f}, lag={used_lag}). "
                    "The unit root hypothesis is rejected."
                )
            else:
                all_summaries.append(
                    f"'{name}' appears non-stationary (ADF={adf_stat:.4f}, p={p_value:.4f}, lag={used_lag}). "
                    "Cannot reject the unit root hypothesis. Consider differencing."
                )

        progress_callback("Building output", 90)

        main_table = make_table(
            "ADF Test Results",
            ["Series", "ADF Statistic", "P-Value", "Lags Used", "N Obs", "Decision", "N Total", "Notes"],
            result_rows,
        )

        plain_english = " ".join(all_summaries) if all_summaries else "No test results produced."

        charting = (
            "Table display with color coding: green for Stationary, red/orange for Non-Stationary. "
            "Optionally show a bar chart comparing ADF statistics to critical values."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[main_table] + detail_tables,
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "regression": regression,
                "autolag": autolag,
                "max_lag_param": maxlag,
                "significance_level": significance,
                "n_series_tested": len(all_series),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"ADF test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant or near-constant series (zero variance).",
                "Try a different regression type ('c', 'ct', or 'n').",
            ],
        )


def _prepare_series(values: np.ndarray, name: str, warnings: list) -> np.ndarray:
    """
    Strip leading/trailing NaN and linearly interpolate interior NaN.
    """
    # Strip leading NaN
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    # Strip trailing NaN
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1

    if first_valid > last_valid:
        return np.array([])

    trimmed = values[first_valid:last_valid + 1].copy()

    # Interpolate interior NaN
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
            warnings.append(
                f"'{name}': {nan_count} interior NaN values linearly interpolated for ADF test."
            )
        else:
            return trimmed[~np.isnan(trimmed)]

    return trimmed
