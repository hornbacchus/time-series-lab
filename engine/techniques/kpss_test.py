"""
KPSS stationarity test for Time Series Lab.

Tests the null hypothesis that the series IS stationary (or trend-stationary).
Rejecting H0 suggests the series is non-stationary.

Note: KPSS is the complement of ADF. Using both together gives a clearer picture:
- ADF rejects + KPSS fails to reject -> stationary
- ADF fails to reject + KPSS rejects -> non-stationary
- Both reject -> trend-stationary (difference-stationary around a trend)
- Neither rejects -> inconclusive
"""

import warnings as _warnings
import numpy as np
from statsmodels.tsa.stattools import kpss

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the KPSS stationarity test on one or more series.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        'c' for level stationarity (default), 'ct' for trend stationarity.
    nlags : int or str, optional
        Number of lags for HAC covariance. 'auto' (default) = Hobbs formula,
        'legacy' = old formula, or an integer.
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
        nlags_param = ctx.get_param("nlags", "auto")
        if isinstance(nlags_param, (int, float)):
            nlags = int(nlags_param)
        else:
            nlags = str(nlags_param)
        significance = ctx.get_param("significance_level", 0.05)

        warn_list = []
        result_rows = []
        all_summaries = []
        detail_tables = []

        progress_callback("Running KPSS tests", 15)

        for idx, (name, values) in enumerate(all_series):
            pct = 15 + int(70 * (idx + 1) / len(all_series))
            progress_callback(f"Testing '{name}'", pct)

            clean = _prepare_series(values, name, warn_list)
            n = len(clean)

            if n < 12:
                result_rows.append([
                    name, None, None, None, n, "Too few observations (need >= 12)"
                ])
                all_summaries.append(f"'{name}': insufficient data ({n} observations).")
                continue

            try:
                # kpss can emit an interpolation warning for p-values at boundaries
                with _warnings.catch_warnings(record=True) as caught:
                    _warnings.simplefilter("always")
                    kpss_stat, p_value, used_lags, critical_values = kpss(
                        clean, regression=regression, nlags=nlags
                    )
                    for w in caught:
                        if "p-value" in str(w.message).lower():
                            warn_list.append(f"'{name}': {w.message}")
            except Exception as e:
                result_rows.append([name, None, None, None, n, str(e)])
                all_summaries.append(f"'{name}': test failed ({e}).")
                continue

            # KPSS: REJECT H0 (stationary) if stat > critical value, i.e. p < alpha
            non_stationary = p_value < significance
            if non_stationary:
                decision = "Non-Stationary"
            else:
                decision = "Stationary"

            result_rows.append([
                name,
                round(kpss_stat, 4),
                round(p_value, 6) if p_value is not None else None,
                used_lags,
                n,
                decision,
            ])

            # Critical values sub-table
            cv_rows = []
            for level, cv in sorted(critical_values.items(), key=lambda x: x[0]):
                exceeds = "Yes" if kpss_stat > cv else "No"
                cv_rows.append([level, round(cv, 4), exceeds])
            cv_table = make_table(
                f"Critical Values - {name}",
                ["Significance Level", "Critical Value", "Stat > CV? (Reject H0)"],
                cv_rows,
            )
            detail_tables.append(cv_table)

            # Summary sentence
            reg_label = "level" if regression == "c" else "trend"
            if non_stationary:
                all_summaries.append(
                    f"'{name}' is NOT {reg_label}-stationary "
                    f"(KPSS={kpss_stat:.4f}, p={p_value:.4f}). "
                    "The stationarity hypothesis is rejected. Consider differencing."
                )
            else:
                all_summaries.append(
                    f"'{name}' appears {reg_label}-stationary "
                    f"(KPSS={kpss_stat:.4f}, p={p_value:.4f}). "
                    "Cannot reject the stationarity hypothesis."
                )

        progress_callback("Building output", 90)

        main_table = make_table(
            "KPSS Test Results",
            ["Series", "KPSS Statistic", "P-Value", "Lags Used", "N Obs", "Decision"],
            result_rows,
        )

        plain_english = " ".join(all_summaries) if all_summaries else "No test results produced."

        # Add guidance on ADF+KPSS interpretation
        plain_english += (
            " Tip: pair KPSS with the ADF test for a definitive stationarity assessment. "
            "If ADF rejects and KPSS does not reject, the series is stationary. "
            "If both reject, the series may be trend-stationary (try differencing)."
        )

        charting = (
            "Table display with color coding: green for Stationary, red/orange for Non-Stationary. "
            "Optionally show a bar chart of KPSS statistics vs. critical values."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[main_table] + detail_tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "regression": regression,
                "nlags": nlags,
                "significance_level": significance,
                "n_series_tested": len(all_series),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"KPSS test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant series (zero variance causes KPSS to fail).",
                "Try regression='ct' for trend-stationarity testing.",
            ],
        )


def _prepare_series(values: np.ndarray, name: str, warnings: list) -> np.ndarray:
    """Strip leading/trailing NaN and linearly interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1

    if first_valid > last_valid:
        return np.array([])

    trimmed = values[first_valid:last_valid + 1].copy()

    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
            warnings.append(
                f"'{name}': {nan_count} interior NaN values linearly interpolated for KPSS test."
            )
        else:
            return trimmed[~np.isnan(trimmed)]

    return trimmed
