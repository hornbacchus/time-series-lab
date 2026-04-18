"""
Phillips-Perron unit root test for Time Series Lab.

Tests the null hypothesis that a unit root is present (series is non-stationary).
Uses the statsmodels PhillipsPerron implementation. When unavailable, falls back
to ADF with Newey-West bandwidth selection to approximate the PP test behaviour.
"""

import numpy as np
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _prepare_series(values, name, warnings):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([])
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
            warnings.append(
                f"'{name}': {nan_count} interior NaN values linearly interpolated."
            )
        else:
            return trimmed[~np.isnan(trimmed)]
    return trimmed


def _run_pp_test(series, regression, nlags):
    """
    Run the Phillips-Perron test. Try the dedicated implementation first,
    fall back to arch package, then to a manual Z(t) approach.
    """
    n = len(series)

    # Try statsmodels PhillipsPerron if available (statsmodels >= 0.14)
    try:
        from statsmodels.tsa.stattools import phillips_perron  # noqa: F811
        stat, p_value, crit = phillips_perron(series, regression=regression, nlags=nlags)
        return stat, p_value, nlags, n, crit, "statsmodels.phillips_perron"
    except ImportError:
        pass

    # Try arch package
    try:
        from arch.unitroot import PhillipsPerron as PP
        pp = PP(series, trend=regression, lags=nlags)
        stat = pp.stat
        p_value = pp.pvalue
        crit = pp.critical_values
        # Convert crit from dict with string keys like '1%' to match ADF format
        crit_dict = {}
        for k, v in crit.items():
            crit_dict[k] = float(v)
        return float(stat), float(p_value), nlags, n, crit_dict, "arch.PhillipsPerron"
    except ImportError:
        pass

    # Manual Phillips-Perron Z(t) via OLS regression with HAC correction
    return _manual_pp(series, regression, nlags)


def _manual_pp(series, regression, nlags):
    """
    Manual Phillips-Perron Z(t) implementation.

    The PP test is based on the ADF regression Y_t = rho * Y_{t-1} + X_t'*delta + e_t
    but corrects the t-statistic for serial correlation using a Newey-West style
    bandwidth for the long-run variance.
    """
    from scipy import stats as sp_stats

    y = series[1:]
    y_lag = series[:-1]
    n = len(y)

    # Build regressor matrix
    if regression == "c":
        X = np.column_stack([y_lag, np.ones(n)])
    elif regression == "ct":
        X = np.column_stack([y_lag, np.ones(n), np.arange(1, n + 1)])
    elif regression == "n":
        X = y_lag.reshape(-1, 1)
    else:
        X = np.column_stack([y_lag, np.ones(n)])

    # OLS
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    rho_hat = beta[0]

    # Estimate variances
    s2 = np.sum(resid ** 2) / (n - X.shape[1])

    # Long-run variance via Newey-West
    if nlags is None or nlags == "auto":
        nlags_used = int(np.floor(4 * (n / 100) ** (2 / 9)))
    else:
        nlags_used = int(nlags)

    # Long-run variance components. Use the same (n - k) denominator as
    # s2 above so the short-run and long-run variance estimators are
    # consistent — line 109 already applies the degrees-of-freedom
    # correction for s2, but the previous version of this block
    # divided gamma_0 / gamma_j by raw n, mixing biased and unbiased
    # estimators in the PP correction factor below.
    dof_denom = max(1, n - X.shape[1])
    gamma_0 = np.sum(resid ** 2) / dof_denom
    lrv = gamma_0
    for j in range(1, nlags_used + 1):
        w = 1.0 - j / (nlags_used + 1)  # Bartlett kernel
        gamma_j = np.sum(resid[j:] * resid[:-j]) / dof_denom
        lrv += 2 * w * gamma_j

    # PP Z(t) statistic
    se_rho = np.sqrt(s2 / np.sum((y_lag - np.mean(y_lag)) ** 2)) if regression != "n" else np.sqrt(s2 / np.sum(y_lag ** 2))
    t_rho = (rho_hat - 1.0) / se_rho

    # Correction factor
    correction = (n * se_rho / (2 * np.sqrt(lrv))) * (lrv - gamma_0)
    pp_stat = t_rho - correction

    # Approximate p-value using MacKinnon tables (use ADF approximation)
    try:
        from statsmodels.tsa.stattools import adfuller
        # We use ADF just for its p-value interpolation
        adf_result = adfuller(series, maxlag=0, regression=regression, autolag=None)
        # Scale the p-value: the PP stat distribution is similar to ADF
        # We use a rough approximation
        from statsmodels.tsa.adfvalues import MacKinnonP
        p_value = MacKinnonP(pp_stat, regression=regression, N=1)
    except Exception:
        # Very rough p-value approximation
        if pp_stat < -3.5:
            p_value = 0.005
        elif pp_stat < -2.9:
            p_value = 0.05
        elif pp_stat < -2.6:
            p_value = 0.10
        else:
            p_value = 0.50

    # Critical values (approximate, same as ADF asymptotic)
    if regression == "c":
        crit = {"1%": -3.43, "5%": -2.86, "10%": -2.57}
    elif regression == "ct":
        crit = {"1%": -3.96, "5%": -3.41, "10%": -3.13}
    else:
        crit = {"1%": -2.58, "5%": -1.95, "10%": -1.62}

    return float(pp_stat), float(p_value), nlags_used, n, crit, "manual_pp"


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Phillips-Perron test on one or more series.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        'c' (constant, default), 'ct' (constant + trend), 'n' (no constant).
    nlags : int or str, optional
        Number of lags for Newey-West correction. 'auto' = automatic.
    significance_level : float, optional
        P-value threshold. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        all_series = ctx.get_all_series()
        if not all_series:
            return make_error_response(
                ctx,
                "No series provided.",
                error_fixes=["Select at least one data column."],
            )

        regression = ctx.get_param("regression", "c")
        nlags_param = ctx.get_param("nlags", "auto")
        if isinstance(nlags_param, (int, float)):
            nlags = int(nlags_param)
        else:
            nlags = nlags_param  # 'auto' or None
        significance = ctx.get_param("significance_level", 0.05)

        warn_list = []
        result_rows = []
        all_summaries = []
        detail_tables = []

        progress_callback("Running Phillips-Perron tests", 15)

        for idx, (name, values) in enumerate(all_series):
            pct = 15 + int(70 * (idx + 1) / len(all_series))
            progress_callback(f"Testing '{name}'", pct)

            clean = _prepare_series(values, name, warn_list)
            n = len(clean)

            if n < 12:
                result_rows.append([name, None, None, None, None, n, "Too few observations (need >= 12)"])
                all_summaries.append(f"'{name}': insufficient data ({n} observations).")
                continue

            # Check for constant series
            if np.std(clean) < 1e-12:
                result_rows.append([name, None, None, None, None, n, "Constant series (zero variance)"])
                all_summaries.append(f"'{name}': constant series, cannot test.")
                continue

            try:
                pp_stat, p_value, used_lags, nobs, crit_values, method = _run_pp_test(
                    clean, regression, nlags
                )
            except Exception as e:
                result_rows.append([name, None, None, None, None, n, str(e)])
                all_summaries.append(f"'{name}': test failed ({e}).")
                continue

            stationary = p_value < significance
            decision = "Stationary" if stationary else "Non-Stationary"

            result_rows.append([
                name,
                round(pp_stat, 4),
                round(p_value, 6),
                used_lags,
                decision,
                n,
                method,
            ])

            # Critical values table
            cv_rows = []
            for level, cv in sorted(crit_values.items()):
                reject = "Yes" if pp_stat < cv else "No"
                cv_rows.append([level, round(float(cv), 4), reject])
            cv_table = make_table(
                f"Critical Values - {name}",
                ["Significance Level", "Critical Value", "Reject H0?"],
                cv_rows,
            )
            detail_tables.append(cv_table)

            if stationary:
                all_summaries.append(
                    f"'{name}' is stationary (PP={pp_stat:.4f}, p={p_value:.4f}). "
                    "Unit root hypothesis rejected."
                )
            else:
                all_summaries.append(
                    f"'{name}' appears non-stationary (PP={pp_stat:.4f}, p={p_value:.4f}). "
                    "Cannot reject unit root. Consider differencing."
                )

        progress_callback("Building output", 90)

        main_table = make_table(
            "Phillips-Perron Test Results",
            ["Series", "PP Statistic", "P-Value", "Lags", "Decision", "N Obs", "Method"],
            result_rows,
        )

        plain = " ".join(all_summaries) if all_summaries else "No test results produced."
        plain += (
            " Note: The PP test is similar to the ADF test but corrects for serial "
            "correlation non-parametrically (using a Newey-West estimator) rather than "
            "adding lagged difference terms."
        )

        charting = (
            "Table display with color coding: green for Stationary, red for Non-Stationary. "
            "Bar chart of PP statistics vs. critical values."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[main_table] + detail_tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "regression": regression,
                "nlags": nlags_param,
                "significance_level": significance,
                "n_series_tested": len(all_series),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Phillips-Perron test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant or near-constant series.",
                "Try a different regression type ('c', 'ct', or 'n').",
            ],
        )
