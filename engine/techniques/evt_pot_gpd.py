"""
Extreme Value Theory: Peaks Over Threshold / Generalized Pareto Distribution
for Time Series Lab.

Fits a GPD to exceedances over a high threshold to model tail risk.
Computes Value-at-Risk (VaR) and Expected Shortfall (ES) at specified
confidence levels.

Method:
1. Select threshold u (default: 97.5th percentile of losses).
2. Extract exceedances Y_i = X_i - u for X_i > u.
3. Fit GPD(xi, sigma) to exceedances via MLE (scipy.stats.genpareto).
4. Compute VaR_p and ES_p using the GPD tail estimator.
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)

_PRESET_CONFIG = {
    "Fast":     {"bootstrap_samples": 0,    "n_thresholds_plot": 20},
    "Balanced": {"bootstrap_samples": 500,  "n_thresholds_plot": 50},
    "Thorough": {"bootstrap_samples": 2000, "n_thresholds_plot": 100},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Extreme Value Theory POT/GPD analysis.

    Parameters (via ctx.params)
    ---------------------------
    threshold_quantile : float, optional
        Quantile for threshold selection (default 0.975).
    threshold_value : float, optional
        Explicit threshold value. Overrides threshold_quantile if provided.
    confidence_levels : list[float], optional
        Confidence levels for VaR/ES (default [0.95, 0.99, 0.999]).
    tail : str, optional
        Which tail to analyze: 'upper' (default) or 'lower'.
        'lower' negates the data to analyze the left tail.
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
        if n < 50:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. EVT POT/GPD needs at least 50.",
                error_fixes=["Provide a longer series for reliable tail estimation."],
            )

        tail = ctx.get_param("tail", "upper").lower()
        if tail == "lower":
            data = -clean.copy()
            tail_label = "left (lower)"
        else:
            data = clean.copy()
            tail_label = "right (upper)"

        # Determine threshold
        threshold_value = ctx.get_param("threshold_value")
        threshold_quantile = float(ctx.get_param("threshold_quantile", 0.975))

        if threshold_value is not None:
            u = float(threshold_value)
            if tail == "lower":
                u = -u  # negate for lower tail
        else:
            u = float(np.quantile(data, threshold_quantile))

        progress_callback("Extracting exceedances", 15)

        # Extract exceedances
        exceedance_mask = data > u
        n_exceed = int(exceedance_mask.sum())

        if n_exceed < 10:
            return make_error_response(
                ctx,
                f"Only {n_exceed} exceedances above threshold {u:.4f}. "
                f"Need at least 10 for reliable GPD fitting.",
                error_fixes=[
                    "Lower the threshold_quantile (e.g., 0.95 instead of 0.975).",
                    "Provide a longer series.",
                ],
            )

        exceedances = data[exceedance_mask] - u  # Y_i = X_i - u

        progress_callback("Fitting GPD to exceedances", 30)

        # Fit GPD using scipy.stats.genpareto
        # genpareto parameterization: F(x) = 1 - (1 + xi*x/sigma)^(-1/xi)
        try:
            xi_hat, loc_fit, sigma_hat = sp_stats.genpareto.fit(exceedances, floc=0)
        except Exception as fit_err:
            return make_error_response(
                ctx,
                f"GPD fitting failed: {fit_err}",
                error_fixes=[
                    "Try a different threshold (lower threshold_quantile).",
                    "Check for data issues (constant values, extreme outliers).",
                ],
            )

        # Validate parameters
        if sigma_hat <= 0:
            return make_error_response(
                ctx,
                "GPD scale parameter is non-positive. Fitting failed.",
                error_fixes=["Try a different threshold."],
            )

        progress_callback("Computing VaR and ES", 50)

        # Confidence levels for VaR/ES
        conf_levels = ctx.get_param("confidence_levels", [0.95, 0.99, 0.999])
        if isinstance(conf_levels, (int, float)):
            conf_levels = [conf_levels]

        # Proportion of observations above threshold
        zeta_u = n_exceed / n

        risk_rows = []
        for p in conf_levels:
            # VaR_p = u + (sigma / xi) * ((n/N_u * (1-p))^(-xi) - 1) for xi != 0
            if abs(xi_hat) > 1e-10:
                var_p = u + (sigma_hat / xi_hat) * (
                    ((1 - p) / zeta_u) ** (-xi_hat) - 1
                )
            else:
                # Exponential case (xi -> 0)
                var_p = u + sigma_hat * np.log(zeta_u / (1 - p))

            # ES_p = VaR_p / (1 - xi) + (sigma - xi * u) / (1 - xi)
            if xi_hat < 1.0:
                es_p = var_p / (1 - xi_hat) + (sigma_hat - xi_hat * u) / (1 - xi_hat)
            else:
                es_p = np.inf
                warnings.append(
                    f"xi >= 1 ({xi_hat:.4f}): Expected Shortfall is infinite at {p*100:.1f}% level."
                )

            # If lower tail, negate back
            if tail == "lower":
                var_display = -var_p
                es_display = -es_p
            else:
                var_display = var_p
                es_display = es_p

            risk_rows.append([
                f"{p * 100:.1f}%",
                round(float(var_display), 6),
                round(float(es_display), 6),
            ])

        risk_table = make_table(
            "VaR and Expected Shortfall",
            ["Confidence Level", "VaR", "ES (CVaR)"],
            risk_rows,
        )

        # GPD parameter table
        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Bootstrap confidence intervals for parameters
        xi_ci = [None, None]
        sigma_ci = [None, None]
        if cfg["bootstrap_samples"] > 0:
            progress_callback("Bootstrap confidence intervals", 60)
            xi_boot = []
            sigma_boot = []
            for b in range(cfg["bootstrap_samples"]):
                idx = np.random.randint(0, n_exceed, size=n_exceed)
                exc_b = exceedances[idx]
                try:
                    xi_b, _, sigma_b = sp_stats.genpareto.fit(exc_b, floc=0)
                    xi_boot.append(xi_b)
                    sigma_boot.append(sigma_b)
                except Exception:
                    continue

            if len(xi_boot) > 10:
                xi_ci = [
                    round(float(np.percentile(xi_boot, 2.5)), 6),
                    round(float(np.percentile(xi_boot, 97.5)), 6),
                ]
                sigma_ci = [
                    round(float(np.percentile(sigma_boot, 2.5)), 6),
                    round(float(np.percentile(sigma_boot, 97.5)), 6),
                ]

        progress_callback("Building output", 75)

        param_rows = [
            ["Shape (xi)", round(xi_hat, 6),
             f"[{xi_ci[0]}, {xi_ci[1]}]" if xi_ci[0] is not None else "N/A"],
            ["Scale (sigma)", round(sigma_hat, 6),
             f"[{sigma_ci[0]}, {sigma_ci[1]}]" if sigma_ci[0] is not None else "N/A"],
            ["Threshold (u)", round(float(u if tail != "lower" else -u), 6), ""],
            ["Threshold quantile", round(threshold_quantile, 4), ""],
            ["N exceedances", n_exceed, ""],
            ["N total", n, ""],
            ["Exceedance rate", round(zeta_u, 6), ""],
            ["Tail analyzed", tail_label, ""],
        ]
        param_table = make_table(
            "GPD Parameters",
            ["Parameter", "Value", "95% CI"],
            param_rows,
        )

        # Goodness of fit: KS test on exceedances
        ks_stat, ks_pval = sp_stats.kstest(
            exceedances, 'genpareto', args=(xi_hat, 0, sigma_hat)
        )
        # Anderson-Darling on probability-integral transform
        pit = sp_stats.genpareto.cdf(exceedances, xi_hat, loc=0, scale=sigma_hat)
        ad_stat, ad_crit, ad_sig = sp_stats.anderson(pit, dist='uniform')

        gof_rows = [
            ["KS statistic", round(float(ks_stat), 6), round(float(ks_pval), 6),
             "Good fit" if ks_pval > 0.05 else "Poor fit (reject GPD at 5%)"],
            ["Anderson-Darling", round(float(ad_stat), 6), "",
             f"Critical values: {[round(c, 3) for c in ad_crit]}"],
        ]
        gof_table = make_table(
            "Goodness of Fit",
            ["Test", "Statistic", "p-value", "Note"],
            gof_rows,
        )

        # Mean excess function table for threshold selection diagnostics
        if cfg["n_thresholds_plot"] > 0:
            thresholds = np.linspace(
                float(np.quantile(data, 0.8)),
                float(np.quantile(data, 0.995)),
                cfg["n_thresholds_plot"],
            )
            mef_rows = []
            for thr in thresholds:
                exc = data[data > thr] - thr
                if len(exc) >= 5:
                    mef_rows.append([
                        round(float(thr if tail != "lower" else -thr), 4),
                        int(len(exc)),
                        round(float(np.mean(exc)), 6),
                    ])
            mef_table = make_table(
                "Mean Excess Function",
                ["Threshold", "N Exceedances", "Mean Excess"],
                mef_rows,
            )
        else:
            mef_table = None

        # Exceedance data table
        exceed_indices = np.where(exceedance_mask)[0]
        time_col = ctx.time if ctx.time and len(ctx.time) == len(values) else None
        exc_rows = []
        for i, idx in enumerate(exceed_indices):
            actual_val = float(clean[idx])  # original (un-negated) value
            exc_val = float(exceedances[i])
            t_label = time_col[idx] if time_col else int(idx + 1)
            exc_rows.append([t_label, round(actual_val, 6), round(exc_val, 6)])

        exc_table = make_table(
            "Exceedances",
            ["Time", "Value", "Excess over threshold"],
            exc_rows,
        )

        # Plain English summary
        if xi_hat > 0:
            tail_type = "heavy-tailed (Frechet-type)"
            tail_desc = "Extreme events are more likely than a normal distribution would suggest."
        elif xi_hat < 0:
            tail_type = "bounded (Weibull-type)"
            tail_desc = "The distribution has a finite upper endpoint."
        else:
            tail_type = "exponential-tailed"
            tail_desc = "Tail decay is approximately exponential."

        plain_english = (
            f"EVT Peaks-Over-Threshold analysis of '{name}' ({tail_label} tail, {n} observations). "
            f"Threshold at {('%.4f' % (u if tail != 'lower' else -u))} "
            f"({threshold_quantile*100:.1f}th percentile), yielding {n_exceed} exceedances. "
            f"GPD shape parameter xi = {xi_hat:.4f}, indicating a {tail_type} distribution. "
            f"{tail_desc} "
        )
        # Add VaR/ES at highest confidence level
        highest_conf = conf_levels[-1]
        highest_var = risk_rows[-1][1]
        highest_es = risk_rows[-1][2]
        plain_english += (
            f"At {highest_conf*100:.1f}% confidence: VaR = {highest_var}, ES = {highest_es}."
        )

        if ks_pval <= 0.05:
            warnings.append(
                f"KS test rejects GPD fit (p={ks_pval:.4f}). "
                "Consider adjusting the threshold or checking data quality."
            )

        charting = (
            "Four-panel display: (1) QQ-plot of exceedances vs fitted GPD, "
            "(2) Mean Excess Function plot to validate threshold choice, "
            "(3) Tail probability plot showing empirical vs fitted GPD tail, "
            "(4) Time series with threshold line and exceedance points highlighted."
        )

        tables = [risk_table, param_table, gof_table, exc_table]
        if mef_table is not None:
            tables.append(mef_table)

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "xi": round(xi_hat, 6),
                "sigma": round(sigma_hat, 6),
                "threshold": round(float(u if tail != "lower" else -u), 6),
                "threshold_quantile": threshold_quantile,
                "n_exceedances": n_exceed,
                "exceedance_rate": round(zeta_u, 6),
                "tail": tail,
                "ks_stat": round(float(ks_stat), 6),
                "ks_pval": round(float(ks_pval), 6),
                "n_obs": n,
                "bootstrap_samples": cfg["bootstrap_samples"],
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"EVT POT/GPD analysis failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with sufficient variation.",
                "Try a lower threshold_quantile (e.g., 0.95) for more exceedances.",
                "For loss data, make sure the tail parameter is set correctly.",
            ],
        )
