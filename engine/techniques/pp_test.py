"""
Phillips-Perron unit-root test for Time Series Lab.

Tests the null hypothesis that a unit root is present (series is
non-stationary). Like ADF in orientation, but corrects for serial
correlation non-parametrically (via a Newey-West long-run variance
estimator) instead of by adding lagged differences.

Tries in order:
    1. ``statsmodels.tsa.stattools.phillips_perron`` (statsmodels ≥ 0.14)
    2. ``arch.unitroot.PhillipsPerron``
    3. A manual Z(t) implementation using Newey-West HAC correction.

Exposes ``_run_pp_single(clean, regression, lags)`` for the triage path
in ``adf_test.py``.
"""

import numpy as np
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
    order_critical_values,
)


_REGRESSION_LABEL = {
    "c":  "constant only",
    "ct": "constant + linear trend",
    "n":  "no deterministic term",
    "nc": "no deterministic term",
}


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
    """Back-end dispatcher: try statsmodels, then arch, then manual.

    Returns (stat, p_value, used_lags, n, crit_dict, method_label).
    """
    n = len(series)

    # statsmodels >= 0.14
    try:
        from statsmodels.tsa.stattools import phillips_perron  # noqa: F401
        stat, p_value, crit = phillips_perron(
            series, regression=regression, nlags=nlags,
        )
        return (float(stat), float(p_value), nlags, n,
                {k: float(v) for k, v in crit.items()},
                "statsmodels.phillips_perron")
    except ImportError:
        pass

    # arch package (common in TSL)
    try:
        from arch.unitroot import PhillipsPerron as PP
        trend = regression if regression in ("n", "c", "ct") else "c"
        pp = PP(series, trend=trend, lags=(None if nlags == "auto" else nlags))
        stat = float(pp.stat)
        p_value = float(pp.pvalue)
        crit = {k: float(v) for k, v in pp.critical_values.items()}
        used = getattr(pp, "lags", nlags if nlags != "auto" else None)
        return stat, p_value, used, n, crit, "arch.PhillipsPerron"
    except ImportError:
        pass

    # Manual Z(t) fallback.
    return _manual_pp(series, regression, nlags)


def _manual_pp(series, regression, nlags):
    """Manual Z(t) Phillips-Perron using Newey-West HAC correction."""
    y = series[1:]
    y_lag = series[:-1]
    n = len(y)

    if regression == "c":
        X = np.column_stack([y_lag, np.ones(n)])
    elif regression == "ct":
        X = np.column_stack([y_lag, np.ones(n), np.arange(1, n + 1)])
    elif regression in ("n", "nc"):
        X = y_lag.reshape(-1, 1)
    else:
        X = np.column_stack([y_lag, np.ones(n)])

    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    rho_hat = beta[0]

    s2 = np.sum(resid ** 2) / (n - X.shape[1])

    if nlags is None or nlags == "auto":
        nlags_used = int(np.floor(4 * (n / 100) ** (2 / 9)))
    else:
        nlags_used = int(nlags)

    dof_denom = max(1, n - X.shape[1])
    gamma_0 = np.sum(resid ** 2) / dof_denom
    lrv = gamma_0
    for j in range(1, nlags_used + 1):
        w = 1.0 - j / (nlags_used + 1)
        gamma_j = np.sum(resid[j:] * resid[:-j]) / dof_denom
        lrv += 2 * w * gamma_j

    if regression in ("n", "nc"):
        se_rho = np.sqrt(s2 / np.sum(y_lag ** 2))
    else:
        se_rho = np.sqrt(s2 / np.sum((y_lag - np.mean(y_lag)) ** 2))

    t_rho = (rho_hat - 1.0) / se_rho
    correction = (n * se_rho / (2 * np.sqrt(lrv))) * (lrv - gamma_0)
    pp_stat = t_rho - correction

    try:
        from statsmodels.tsa.adfvalues import MacKinnonP
        p_value = MacKinnonP(pp_stat, regression=regression, N=1)
    except Exception:
        if pp_stat < -3.5:
            p_value = 0.005
        elif pp_stat < -2.9:
            p_value = 0.05
        elif pp_stat < -2.6:
            p_value = 0.10
        else:
            p_value = 0.50

    if regression == "c":
        crit = {"1%": -3.43, "5%": -2.86, "10%": -2.57}
    elif regression == "ct":
        crit = {"1%": -3.96, "5%": -3.41, "10%": -3.13}
    else:
        crit = {"1%": -2.58, "5%": -1.95, "10%": -1.62}

    return float(pp_stat), float(p_value), nlags_used, n, crit, "manual_pp"


def _run_pp_single(clean: np.ndarray, regression: str, lags):
    """Run PP on one prepared series. Returns a raw-results dict in the
    same shape as ``_run_adf_single`` / ``_run_kpss_single`` so the triage
    path can consume all three uniformly.

    Keys: stat, pvalue, used_lag, critical_values_ordered, regression,
    regression_label, method, decision_h0_rejected, error.
    """
    out = {
        "stat": None, "pvalue": None, "used_lag": None,
        "critical_values_ordered": [], "regression": regression,
        "regression_label": _REGRESSION_LABEL.get(regression, regression),
        "method": None, "decision_h0_rejected": None, "error": None,
    }
    n = len(clean)
    if n < 12:
        out["error"] = f"Too few observations ({n}; need ≥ 12)"
        return out
    if np.std(clean) < 1e-12:
        out["error"] = "Constant series (zero variance)"
        return out
    try:
        stat, p_value, used_lag, _nobs, crit, method = _run_pp_test(
            clean, regression, lags if lags is not None else "auto",
        )
    except Exception as e:
        out["error"] = str(e)
        return out
    ordered = order_critical_values(crit)
    out["stat"] = float(stat)
    out["pvalue"] = float(p_value)
    out["used_lag"] = used_lag
    out["method"] = method
    out["critical_values_ordered"] = [
        (lvl, cv, stat < cv) for (lvl, cv) in ordered
    ]
    return out


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Phillips-Perron unit-root test on one or more series.

    Parameters (via ctx.params)
    ---------------------------
    regression : str, optional
        'c' (constant, default), 'ct' (constant + trend), 'n' (no constant).
    nlags : int or str, optional
        Truncation lag for the Newey-West correction. 'auto' uses the
        standard Schwert-style ``floor(4 · (n/100)^(2/9))``.
    significance_level : float, optional
        P-value threshold. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        all_series = ctx.get_all_series()
        if not all_series:
            return make_error_response(
                ctx, "No series provided.",
                error_fixes=["Select at least one data column."],
            )

        regression = ctx.get_param("regression", "c")
        nlags_param = ctx.get_param("nlags", "auto")
        if isinstance(nlags_param, (int, float)):
            lags = int(nlags_param)
        else:
            lags = nlags_param
        significance = float(ctx.get_param("significance_level", 0.05))

        warn_list = []
        result_rows = []
        all_summaries = []
        detail_tables = []

        progress_callback("Running Phillips-Perron tests", 15)

        for idx, (name, values) in enumerate(all_series):
            pct = 15 + int(70 * (idx + 1) / len(all_series))
            progress_callback(f"Testing '{name}'", pct)

            clean = _prepare_series(values, name, warn_list)
            single = _run_pp_single(clean, regression, lags)

            if single["error"] is not None:
                result_rows.append([
                    name, None, None, None,
                    f"{regression} ({single['regression_label']})",
                    single["method"] or "—", len(clean), single["error"],
                ])
                all_summaries.append(f"'{name}': {single['error']}.")
                continue

            rejected = single["pvalue"] < significance
            single["decision_h0_rejected"] = bool(rejected)
            decision = (
                "Reject H0 (UR null)" if rejected
                else "Fail to reject H0"
            )

            result_rows.append([
                name,
                round(single["stat"], 4),
                round(single["pvalue"], 6),
                single["used_lag"],
                f"{regression} ({single['regression_label']})",
                single["method"],
                len(clean),
                decision,
            ])

            cv_rows = [
                [lvl, round(cv, 4), "Yes" if rej else "No"]
                for (lvl, cv, rej) in single["critical_values_ordered"]
            ]
            detail_tables.append(make_table(
                f"Critical Values - {name}",
                ["Significance Level", "Critical Value", "Reject H0?"],
                cv_rows,
            ))

            # P.2 language — PP shares ADF's null (unit root).
            if rejected:
                all_summaries.append(
                    f"'{name}': unit root rejected at the "
                    f"{significance*100:.0f}% level "
                    f"(PP={single['stat']:.4f}, p={single['pvalue']:.4f}, "
                    f"regression='{regression}' / {single['regression_label']}, "
                    f"truncation lag={single['used_lag']}, "
                    f"method={single['method']})."
                )
            else:
                all_summaries.append(
                    f"'{name}': unit root not rejected at the "
                    f"{significance*100:.0f}% level "
                    f"(PP={single['stat']:.4f}, p={single['pvalue']:.4f}, "
                    f"regression='{regression}' / {single['regression_label']}, "
                    f"truncation lag={single['used_lag']}, "
                    f"method={single['method']}). Consider differencing."
                )

        progress_callback("Building output", 90)

        main_table = make_table(
            "Phillips-Perron Test Results",
            ["Series", "PP Statistic", "P-Value", "Truncation Lag",
             "Regression", "Method", "N Total", "Decision"],
            result_rows,
        )

        plain = (" ".join(all_summaries)
                 if all_summaries else "No test results produced.")
        plain += (
            " PP shares ADF's null (unit root) but corrects for serial "
            "correlation non-parametrically via a Newey-West long-run "
            "variance estimator. For a confirmatory joint verdict, use "
            "the Stationarity Triage path (ADF + KPSS + PP together)."
        )

        charting = (
            "Table display color-coded by decision. PP statistic plotted "
            "against 1%/5%/10% Dickey-Fuller critical values."
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
                "regression_label": _REGRESSION_LABEL.get(regression, regression),
                "nlags": nlags_param,
                "significance_level": significance,
                "n_series_tested": len(all_series),
                **format_significance_disclosure(
                    test_name="Phillips-Perron unit-root test",
                    critical_value_formula=(
                        "Newey-West spectral correction of the DF test "
                        "statistic with Dickey-Fuller critical values"
                    ),
                    ac_corrected=True,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx, f"Phillips-Perron test failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check for constant or near-constant series.",
                "Try a different regression type ('c', 'ct', or 'n').",
            ],
        )
