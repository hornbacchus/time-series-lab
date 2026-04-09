"""
Granger Causality test for Time Series Lab.

Tests whether past values of series X help predict series Y
beyond what past values of Y alone can predict.
"""

import numpy as np
from statsmodels.tsa.stattools import grangercausalitytests

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run Granger causality tests between two series at multiple lags.

    Requires exactly 2 series: Y (dependent) and X (potential cause).
    The first selected series is treated as Y, the second as X.

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag to test. Default depends on preset:
        Fast=4, Balanced=8, Thorough=16.
    significance_level : float, optional
        P-value threshold for declaring significance. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        y_name, y_vals = all_series[0]
        x_name, x_vals = all_series[1]
        warnings = []

        # Align and drop NaN
        if len(y_vals) != len(x_vals):
            return make_error_response(
                ctx,
                f"Series lengths differ: '{y_name}' has {len(y_vals)} values, "
                f"'{x_name}' has {len(x_vals)} values. They must be the same length.",
                error_fixes=["Select two columns of equal length."],
            )

        y_clean, x_clean = dropna_aligned(y_vals, x_vals)
        n_dropped = len(y_vals) - len(y_clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to missing values in either series.")

        n = len(y_clean)
        if n < 10:
            return make_error_response(
                ctx,
                f"Only {n} valid observations after removing missing values. "
                "Need at least 10 for Granger causality testing.",
                error_fixes=["Provide a longer series or fill missing values."],
            )

        # Determine max_lag
        preset_defaults = {"Fast": 4, "Balanced": 8, "Thorough": 16}
        max_lag = ctx.get_param("max_lag")
        if max_lag is None:
            max_lag = preset_defaults.get(ctx.preset, 8)
        max_lag = int(max_lag)

        # Cap max_lag to avoid running out of degrees of freedom
        max_feasible = max(1, (n // 3) - 1)
        if max_lag > max_feasible:
            warnings.append(
                f"max_lag reduced from {max_lag} to {max_feasible} due to series length ({n})."
            )
            max_lag = max_feasible

        if max_lag < 1:
            return make_error_response(
                ctx,
                "Series is too short to test even 1 lag of Granger causality.",
                error_fixes=["Provide a longer time series."],
            )

        significance = ctx.get_param("significance_level", 0.05)

        progress_callback("Running Granger causality tests", 20)

        # statsmodels wants a 2D array [Y, X] in columns
        data = np.column_stack([y_clean, x_clean])

        # Run tests; verbose=False suppresses print output
        results = grangercausalitytests(data, maxlag=max_lag, verbose=False)

        progress_callback("Compiling results", 70)

        # Extract F-test results for each lag
        rows = []
        best_lag = None
        best_p = 1.0
        for lag in range(1, max_lag + 1):
            test_dict = results[lag]
            # test_dict is (dict_of_tests, [ols_restricted, ols_unrestricted, ...])
            f_test = test_dict[0]["ssr_ftest"]
            f_stat = f_test[0]
            p_value = f_test[1]
            df_denom = f_test[2]
            df_num = f_test[3]

            significant = "Yes" if p_value < significance else "No"

            rows.append([lag, round(f_stat, 4), round(p_value, 6), int(df_num), int(df_denom), significant])

            if p_value < best_p:
                best_p = p_value
                best_lag = lag

        results_table = make_table(
            "Granger Causality (F-test)",
            ["Lag", "F-Statistic", "P-Value", "df_num", "df_denom", "Significant"],
            rows,
        )

        # Summary table
        decision = "Yes" if best_p < significance else "No"
        summary_rows = [
            ["Dependent (Y)", y_name],
            ["Potential Cause (X)", x_name],
            ["Optimal Lag", best_lag],
            ["Best P-Value", round(best_p, 6)],
            ["Significance Level", significance],
            ["Granger-Causes?", decision],
            ["Observations (after NaN removal)", n],
            ["Max Lag Tested", max_lag],
        ]
        summary_table = make_table("Summary", ["Field", "Value"], summary_rows)

        # Plain English
        if best_p < significance:
            plain_english = (
                f"'{x_name}' Granger-causes '{y_name}' at lag {best_lag} "
                f"(p={best_p:.4f}, significance level={significance}). "
                f"Past values of '{x_name}' contain statistically significant "
                f"information for predicting '{y_name}' beyond its own history."
            )
        else:
            plain_english = (
                f"'{x_name}' does NOT Granger-cause '{y_name}' at any tested lag "
                f"(best p={best_p:.4f}, significance level={significance}). "
                f"Past values of '{x_name}' do not add significant predictive power "
                f"for '{y_name}' beyond its own past values."
            )

        # Check for reverse causality hint
        if ctx.preset == "Thorough":
            progress_callback("Testing reverse direction", 85)
            data_rev = np.column_stack([x_clean, y_clean])
            results_rev = grangercausalitytests(data_rev, maxlag=max_lag, verbose=False)
            rev_best_p = 1.0
            rev_best_lag = None
            for lag in range(1, max_lag + 1):
                p_rev = results_rev[lag][0]["ssr_ftest"][1]
                if p_rev < rev_best_p:
                    rev_best_p = p_rev
                    rev_best_lag = lag

            if rev_best_p < significance:
                plain_english += (
                    f" Note: reverse test shows '{y_name}' also Granger-causes '{x_name}' "
                    f"(lag {rev_best_lag}, p={rev_best_p:.4f}), suggesting bidirectional causality."
                )
                warnings.append(
                    f"Bidirectional Granger causality detected. Consider a VAR model for joint modeling."
                )

        charting = (
            "Bar chart of F-statistics by lag, with a horizontal dashed line at the "
            f"critical F-value for alpha={significance}. Highlight significant lags."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[results_table, summary_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "y_series": y_name,
                "x_series": x_name,
                "max_lag": max_lag,
                "optimal_lag": best_lag,
                "best_p_value": round(best_p, 6),
                "significant": decision == "Yes",
                "significance_level": significance,
                "n_valid": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Granger causality test failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Check for excessive missing values.",
                "Try reducing max_lag if the series is short.",
            ],
        )
