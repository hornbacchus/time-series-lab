"""
HAR-RV (Heterogeneous Autoregressive Realized Volatility) model for Time Series Lab.

Implements the Corsi (2009) HAR-RV model:
    RV_t = beta_0 + beta_d * RV_{t-1} + beta_w * RV_{t-1:t-5} + beta_m * RV_{t-1:t-22} + eps_t

where RV_{t-1:t-k} is the average realized volatility over the past k days.
This captures heterogeneous market participants operating at different time horizons:
daily (1 day), weekly (5 days), monthly (22 days).

Estimation is by OLS. Optionally includes a log-HAR variant.
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"bootstrap_samples": 0,    "compute_residual_diag": False},
    "Balanced": {"bootstrap_samples": 500,  "compute_residual_diag": True},
    "Thorough": {"bootstrap_samples": 2000, "compute_residual_diag": True},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Estimate the HAR-RV model on a realized volatility series.

    Parameters (via ctx.params)
    ---------------------------
    daily_lag : int, optional
        Daily component lag (default 1).
    weekly_lag : int, optional
        Weekly component window (default 5).
    monthly_lag : int, optional
        Monthly component window (default 22).
    use_log : bool, optional
        If True, estimate log-HAR model (default False).
    h_ahead : int, optional
        Forecast horizon: aggregate RV over next h days (default 1).
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN
        clean = values[~np.isnan(values)]
        n_dropped = len(values) - len(clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(clean)
        daily_lag = int(ctx.get_param("daily_lag", 1))
        weekly_lag = int(ctx.get_param("weekly_lag", 5))
        monthly_lag = int(ctx.get_param("monthly_lag", 22))
        use_log = bool(ctx.get_param("use_log", False))
        h_ahead = int(ctx.get_param("h_ahead", 1))

        min_obs = monthly_lag + h_ahead + 10
        if n < min_obs:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. HAR-RV needs at least {min_obs} "
                f"(monthly_lag={monthly_lag} + h_ahead={h_ahead} + 10).",
                error_fixes=[
                    "Provide a longer realized volatility series.",
                    "Reduce monthly_lag or h_ahead parameters.",
                ],
            )

        # Check for non-negative values (RV should be >= 0)
        if np.any(clean < 0):
            warnings.append(
                "Negative values detected in the series. RV should be non-negative. "
                "Results may be unreliable."
            )

        progress_callback("Constructing HAR regressors", 20)

        rv = clean.copy()
        if use_log:
            rv_positive = np.where(rv > 0, rv, np.finfo(float).eps)
            rv = np.log(rv_positive)

        # Build dependent variable: h-period ahead average RV
        if h_ahead > 1:
            y_raw = np.array([
                np.mean(rv[i:i + h_ahead]) for i in range(len(rv) - h_ahead + 1)
            ])
        else:
            y_raw = rv.copy()

        # Build HAR regressors
        # Start index must accommodate the longest lookback
        start = monthly_lag
        end = len(rv) - (h_ahead - 1) if h_ahead > 1 else len(rv)

        if start >= end - 10:
            return make_error_response(
                ctx,
                "Not enough observations after constructing HAR regressors.",
                error_fixes=["Provide a longer series or reduce lag parameters."],
            )

        T = end - start
        y = np.zeros(T)
        X_daily = np.zeros(T)
        X_weekly = np.zeros(T)
        X_monthly = np.zeros(T)

        for t_idx in range(T):
            t = start + t_idx
            # Dependent variable (forward-looking)
            if h_ahead > 1:
                y[t_idx] = np.mean(rv[t:t + h_ahead])
            else:
                y[t_idx] = rv[t]

            # Daily component: RV_{t-1} (or average of last daily_lag days)
            X_daily[t_idx] = np.mean(rv[t - daily_lag:t])

            # Weekly component: average of last weekly_lag days
            X_weekly[t_idx] = np.mean(rv[t - weekly_lag:t])

            # Monthly component: average of last monthly_lag days
            X_monthly[t_idx] = np.mean(rv[t - monthly_lag:t])

        # OLS estimation: y = beta_0 + beta_d * X_d + beta_w * X_w + beta_m * X_m
        X = np.column_stack([np.ones(T), X_daily, X_weekly, X_monthly])

        progress_callback("Running OLS estimation", 40)

        beta, residuals, R2, se, t_stats, p_vals = _ols_with_stats(X, y)

        if beta is None:
            return make_error_response(
                ctx,
                "OLS regression failed (singular matrix). The regressors may be perfectly collinear.",
                error_fixes=["Check that the series has sufficient variation."],
            )

        # Fitted values
        y_hat = X @ beta
        resid = y - y_hat

        # Adjusted R-squared
        k = X.shape[1]
        R2_adj = 1 - (1 - R2) * (T - 1) / (T - k - 1) if T > k + 1 else R2

        # Information criteria. Use the unbiased residual variance (divide
        # by T − k, not T) so the downstream log-likelihood, AIC, and BIC
        # reflect the proper OLS degrees-of-freedom correction. The MLE
        # plug-in σ² (dividing by T) biases AIC/BIC low and makes
        # forecast intervals look narrower than they should be, which
        # matters for any risk-sensitive use (VaR, vol targeting).
        dof = T - k
        sigma2 = np.sum(resid ** 2) / dof if dof > 0 else np.sum(resid ** 2) / T
        log_lik = -T / 2 * (np.log(2 * np.pi) + np.log(sigma2) + 1)
        aic = -2 * log_lik + 2 * k
        bic = -2 * log_lik + k * np.log(T)

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Computing diagnostics", 60)

        # Bootstrap confidence intervals
        ci_low = [None] * k
        ci_high = [None] * k
        if cfg["bootstrap_samples"] > 0:
            progress_callback("Bootstrap confidence intervals", 65)
            boot_betas = np.zeros((cfg["bootstrap_samples"], k))
            for b in range(cfg["bootstrap_samples"]):
                idx = np.random.randint(0, T, size=T)
                X_b = X[idx]
                y_b = y[idx]
                try:
                    beta_b = np.linalg.lstsq(X_b, y_b, rcond=None)[0]
                    boot_betas[b] = beta_b
                except np.linalg.LinAlgError:
                    boot_betas[b] = beta
            for j in range(k):
                ci_low[j] = round(float(np.percentile(boot_betas[:, j], 2.5)), 6)
                ci_high[j] = round(float(np.percentile(boot_betas[:, j], 97.5)), 6)

        progress_callback("Building output tables", 80)

        # Coefficient table
        coef_names = ["Intercept (beta_0)", "Daily (beta_d)", "Weekly (beta_w)", "Monthly (beta_m)"]
        coef_rows = []
        for i, cname in enumerate(coef_names):
            row = [
                cname,
                round(float(beta[i]), 6),
                round(float(se[i]), 6) if se[i] is not None else None,
                round(float(t_stats[i]), 4) if t_stats[i] is not None else None,
                round(float(p_vals[i]), 6) if p_vals[i] is not None else None,
            ]
            if ci_low[i] is not None:
                row.extend([ci_low[i], ci_high[i]])
            else:
                row.extend([None, None])
            coef_rows.append(row)

        coef_cols = ["Coefficient", "Estimate", "Std Error", "t-stat", "p-value", "CI 2.5%", "CI 97.5%"]
        coef_table = make_table("HAR-RV Coefficients", coef_cols, coef_rows)

        # Model fit table
        fit_rows = [
            ["R-squared", round(R2, 6)],
            ["Adjusted R-squared", round(R2_adj, 6)],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["Residual Std Error", round(float(np.sqrt(sigma2)), 6)],
            ["Observations (T)", T],
            ["Model", "log-HAR-RV" if use_log else "HAR-RV"],
            ["Forecast horizon (h)", h_ahead],
            ["Daily lag", daily_lag],
            ["Weekly lag", weekly_lag],
            ["Monthly lag", monthly_lag],
        ]
        fit_table = make_table("Model Fit", ["Metric", "Value"], fit_rows)

        # Residual diagnostics
        diag_rows = []
        if cfg["compute_residual_diag"]:
            # Ljung-Box test on residuals (lag 10)
            lb_stat, lb_pval = _ljung_box(resid, 10)
            diag_rows.append(["Ljung-Box Q(10)", round(lb_stat, 4), round(lb_pval, 6)])

            # Jarque-Bera normality test
            jb_stat, jb_pval = sp_stats.jarque_bera(resid)
            diag_rows.append(["Jarque-Bera", round(float(jb_stat), 4), round(float(jb_pval), 6)])

            # Durbin-Watson
            dw = np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2)
            diag_rows.append(["Durbin-Watson", round(float(dw), 4), ""])

        if diag_rows:
            diag_table = make_table("Residual Diagnostics", ["Test", "Statistic", "p-value"], diag_rows)
        else:
            diag_table = None

        # Fitted values table (subsample for large series)
        time_col = ctx.time if ctx.time and len(ctx.time) >= start + T else list(range(1, T + 1))
        if isinstance(time_col, list) and len(time_col) >= start + T:
            time_subset = time_col[start:start + T]
        else:
            time_subset = list(range(start + 1, start + T + 1))

        max_display = 500
        step = max(1, T // max_display)
        fit_rows_ts = []
        for i in range(0, T, step):
            fit_rows_ts.append([
                time_subset[i],
                round(float(y[i]), 6),
                round(float(y_hat[i]), 6),
                round(float(resid[i]), 6),
            ])

        ts_table = make_table(
            "Fitted Values",
            ["Time", "Actual", "Fitted", "Residual"],
            fit_rows_ts,
        )

        # Plain English summary
        sig_components = []
        for i, cname in enumerate(["daily", "weekly", "monthly"]):
            if p_vals[i + 1] is not None and p_vals[i + 1] < 0.05:
                sig_components.append(cname)

        model_label = "log-HAR-RV" if use_log else "HAR-RV"
        summary = (
            f"{model_label} model estimated on '{name}' ({T} observations, h={h_ahead}). "
            f"R-squared = {R2:.4f} (adj. {R2_adj:.4f}). "
        )
        if sig_components:
            summary += (
                f"Significant components at 5% level: {', '.join(sig_components)}. "
            )
        else:
            summary += "No components are significant at the 5% level. "

        beta_d, beta_w, beta_m = beta[1], beta[2], beta[3]
        dominant = "daily" if abs(beta_d) >= max(abs(beta_w), abs(beta_m)) else (
            "weekly" if abs(beta_w) >= abs(beta_m) else "monthly"
        )
        summary += f"The {dominant} component has the largest coefficient magnitude."

        charting = (
            "Dual-panel chart: top panel shows actual vs fitted RV over time, "
            "bottom panel shows residuals. "
            "Optionally add a bar chart of coefficient magnitudes with error bars."
        )

        tables = [coef_table, fit_table, ts_table]
        if diag_table is not None:
            tables.insert(2, diag_table)

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=summary,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "model": model_label,
                "daily_lag": daily_lag,
                "weekly_lag": weekly_lag,
                "monthly_lag": monthly_lag,
                "h_ahead": h_ahead,
                "beta_0": round(float(beta[0]), 6),
                "beta_d": round(float(beta[1]), 6),
                "beta_w": round(float(beta[2]), 6),
                "beta_m": round(float(beta[3]), 6),
                "R2": round(R2, 6),
                "R2_adj": round(R2_adj, 6),
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "n_obs": T,
                "bootstrap_samples": cfg["bootstrap_samples"],
                **format_significance_disclosure(
                    test_name=(
                        "HAR-RV OLS t-tests on daily/weekly/monthly lag "
                        "coefficients"
                    ),
                    critical_value_formula=(
                        "p = 2·(1 - t.cdf(|t_stat|, T-k)). Standard OLS "
                        "standard errors assume iid homoskedastic residuals; "
                        "NOT AC-aware. For realized-volatility data with "
                        "persistence, consider HAC/Newey-West or a block "
                        "bootstrap of the beta estimates."
                    ),
                    ac_corrected=False,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"HAR-RV estimation failed: {e}",
            error_fixes=[
                "Ensure the series represents realized volatility (non-negative).",
                "Check for sufficient observations (need > monthly_lag + h_ahead).",
                "Try the log-HAR variant if standard HAR has poor fit.",
            ],
        )


def _ols_with_stats(X, y):
    """
    OLS estimation with standard errors, t-stats, and p-values.
    Returns (beta, residuals, R2, se, t_stats, p_vals).
    """
    n, k = X.shape
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None, None, None, [None] * k, [None] * k, [None] * k

    y_hat = X @ beta
    resid = y - y_hat
    SS_res = np.sum(resid ** 2)
    SS_tot = np.sum((y - np.mean(y)) ** 2)
    R2 = 1 - SS_res / SS_tot if SS_tot > 0 else 0.0

    # Standard errors (OLS)
    sigma2 = SS_res / (n - k) if n > k else SS_res / max(n, 1)
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(sigma2 * XtX_inv))
        t_stats = beta / se
        p_vals = 2 * (1 - sp_stats.t.cdf(np.abs(t_stats), df=n - k))
    except np.linalg.LinAlgError:
        se = [None] * k
        t_stats = [None] * k
        p_vals = [None] * k

    return beta, resid, R2, se, t_stats, p_vals


def _ljung_box(resid, max_lag):
    """Simple Ljung-Box Q-statistic."""
    n = len(resid)
    acf_vals = np.correlate(resid - np.mean(resid), resid - np.mean(resid), mode='full')
    acf_vals = acf_vals[n - 1:] / acf_vals[n - 1]  # normalize
    Q = 0.0
    for k in range(1, min(max_lag + 1, n)):
        Q += acf_vals[k] ** 2 / (n - k)
    Q *= n * (n + 2)
    p_val = 1 - sp_stats.chi2.cdf(Q, df=max_lag)
    return Q, p_val
