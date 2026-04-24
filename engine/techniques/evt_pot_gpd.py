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

Follow-up 3c (decluster=True): Optional Ferro-Segers 2003 intervals
declustering applied before GPD re-fit on cluster peaks. Extremal
index θ estimated from inter-exceedance times; K = ceil(θ · N_u)
cluster peaks identified via the intervals method (K-1 largest gaps
between exceedance times). Post-declustering VaR uses ζ_u = K/n
(cluster-peak rate; Coles 2001) as the tail-scale driver, correcting
the bias that volatility-clustered exceedances introduce into
standard POT/GPD. Default decluster=False preserves backward
compatibility; the existing Tier 3 D5 `_trigger_declustering_
timeseries` pointer at "consider a declustered POT approach" now
has an actionable target.

Confidence-interval caveat
==========================
The bootstrap confidence intervals reported here use the non-parametric
percentile method. That's standard practice but known to be biased
for the GPD shape parameter xi, especially in the regions xi near 0.5
(the boundary of finite variance) and xi near 1 (where the ES integral
diverges) — see Castillo & Padilla (2015). A bias-corrected and
accelerated (BCa) bootstrap or profile-likelihood intervals would give
tighter coverage in those regions. Treat the reported CIs as
informational when |xi_hat| > 0.4 rather than as strict coverage
guarantees; use the point estimate plus the residual plot and QQ-plot
diagnostics to decide whether the tail model looks reliable.
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

        # Goodness of fit: KS test on exceedances.
        #
        # Decision D14 (Prompt C6): the previous implementation also
        # called ``sp_stats.anderson(pit, dist='uniform')`` on the
        # probability-integral transform, but scipy's anderson only
        # accepts {'norm', 'expon', 'logistic', 'gumbel_l', 'gumbel_r',
        # 'weibull_min'} — 'uniform' raised ``Invalid distribution``
        # and blocked every real-data run. We drop the Anderson-Darling
        # row and keep the KS test, which already covers goodness-of-fit
        # on the GPD at a single reported statistic + p-value.
        ks_stat, ks_pval = sp_stats.kstest(
            exceedances, 'genpareto', args=(xi_hat, 0, sigma_hat)
        )

        gof_rows = [
            ["KS statistic", round(float(ks_stat), 6), round(float(ks_pval), 6),
             "Good fit" if ks_pval > 0.05 else "Poor fit (reject GPD at 5%)"],
        ]
        gof_table = make_table(
            "Goodness of Fit",
            ["Test", "Statistic", "p-value", "Note"],
            gof_rows,
        )

        # ── Follow-up 3c — Mean residual life diagnostic (always-on) ─
        # Empirical e(u) vs GPD-implied (σ + ξu)/(1 − ξ). 30% match
        # threshold per Q8. Uses the u used internally (may be negated
        # for lower tail; the check is scale-invariant since both
        # sides use the same u).
        mrl_e_emp, mrl_e_imp, mrl_verdict = _mean_residual_life_diagnostic(
            exceedances, xi_hat, sigma_hat, u,
        )

        # ── Follow-up 3c — Declustering cascade ─────────────────────
        decluster_requested = bool(ctx.get_param("decluster", False))
        decluster_applied = False
        decluster_fallback_reason = None
        extremal_index_theta = None
        extremal_index_method = None
        n_clusters_post = None
        decluster_reduction_ratio = None
        xi_post = None
        sigma_post = None
        ks_stat_post = None
        ks_pval_post = None
        var_values_post = None
        es_values_post = None
        var_bias_corr = None
        var_bias_corr_pct = None
        xi_ci_post = [None, None]
        sigma_ci_post = [None, None]

        if decluster_requested:
            progress_callback("Declustering via Ferro-Segers intervals", 68)
            if n_exceed < 10:
                # Defensive: pre-decluster already enforces n_exceed >= 10,
                # but if the cascade is reached with fewer, flag cleanly.
                decluster_fallback_reason = "insufficient_exceedances"
                warnings.append(
                    f"Declustering requested but only {n_exceed} "
                    f"exceedances above threshold; Ferro-Segers "
                    f"intervals estimator is unreliable with fewer "
                    f"than 10 exceedances. Reverting to pre-"
                    f"declustering GPD fit."
                )
            else:
                try:
                    exceed_positions = np.where(exceedance_mask)[0]
                    T_gaps = np.diff(exceed_positions)
                    theta_hat, ei_branch = _ferro_segers_extremal_index(T_gaps)
                    extremal_index_theta = theta_hat
                    extremal_index_method = (
                        f"ferro_segers_2003 ({ei_branch})"
                    )
                    peaks, K, cluster_assn = _identify_clusters(
                        exceed_positions, exceedances, theta_hat, n_exceed,
                    )
                    n_clusters_post = int(K)
                    decluster_reduction_ratio = float(K) / float(n_exceed)

                    # GPD re-fit on cluster-peak excesses (peaks are
                    # already excesses over u in `exceedances` space)
                    xi_p, _loc_p, sigma_p = sp_stats.genpareto.fit(
                        peaks, floc=0,
                    )
                    if sigma_p <= 0:
                        raise ValueError(
                            f"Post-declustering GPD scale non-positive "
                            f"(sigma={sigma_p:.4g})"
                        )
                    xi_post = float(xi_p)
                    sigma_post = float(sigma_p)

                    # KS goodness-of-fit on cluster peaks
                    ks_stat_p, ks_pval_p = sp_stats.kstest(
                        peaks, 'genpareto',
                        args=(xi_post, 0, sigma_post),
                    )
                    ks_stat_post = float(ks_stat_p)
                    ks_pval_post = float(ks_pval_p)

                    # Post-declustering VaR/ES with ζ_u = K/n
                    zeta_u_post = K / n
                    var_values_post = []
                    es_values_post = []
                    for p in conf_levels:
                        if abs(xi_post) > 1e-10:
                            var_p_post = u + (sigma_post / xi_post) * (
                                ((1 - p) / zeta_u_post) ** (-xi_post) - 1
                            )
                        else:
                            var_p_post = u + sigma_post * np.log(
                                zeta_u_post / (1 - p)
                            )
                        if xi_post < 1.0:
                            es_p_post = var_p_post / (1 - xi_post) + (
                                sigma_post - xi_post * u
                            ) / (1 - xi_post)
                        else:
                            es_p_post = np.inf
                        # Negate for lower tail (display scale)
                        if tail == "lower":
                            var_display_post = -var_p_post
                            es_display_post = -es_p_post
                        else:
                            var_display_post = var_p_post
                            es_display_post = es_p_post
                        var_values_post.append(float(var_display_post))
                        es_values_post.append(
                            float(es_display_post)
                            if np.isfinite(es_display_post) else None
                        )

                    # Bias correction at 99% (or closest)
                    target = 0.99
                    best_idx = None
                    for i, p in enumerate(conf_levels):
                        if abs(float(p) - target) < 1e-9:
                            best_idx = i
                            break
                    if best_idx is None and conf_levels:
                        diffs = [abs(float(p) - target) for p in conf_levels]
                        best_idx = int(np.argmin(diffs))
                    if best_idx is not None:
                        try:
                            # risk_rows: [conf_str, VaR_display, ES_display]
                            var_pre = float(risk_rows[best_idx][1])
                            var_post_at = float(var_values_post[best_idx])
                            var_bias_corr = var_post_at - var_pre
                            if abs(var_pre) > 1e-12:
                                var_bias_corr_pct = var_bias_corr / abs(var_pre)
                        except Exception:
                            pass

                    # Post-declustering bootstrap CIs (D11)
                    if cfg["bootstrap_samples"] > 0 and K >= 10:
                        progress_callback(
                            "Post-decluster bootstrap", 75,
                        )
                        xi_boot_post = []
                        sigma_boot_post = []
                        for b in range(cfg["bootstrap_samples"]):
                            idx_b = np.random.randint(0, K, size=K)
                            peaks_b = peaks[idx_b]
                            try:
                                xi_bp, _, sigma_bp = sp_stats.genpareto.fit(
                                    peaks_b, floc=0,
                                )
                                xi_boot_post.append(xi_bp)
                                sigma_boot_post.append(sigma_bp)
                            except Exception:
                                continue
                        if len(xi_boot_post) > 10:
                            xi_ci_post = [
                                round(float(np.percentile(xi_boot_post, 2.5)), 6),
                                round(float(np.percentile(xi_boot_post, 97.5)), 6),
                            ]
                            sigma_ci_post = [
                                round(float(np.percentile(sigma_boot_post, 2.5)), 6),
                                round(float(np.percentile(sigma_boot_post, 97.5)), 6),
                            ]

                    decluster_applied = True
                except Exception as decl_err:
                    decluster_fallback_reason = (
                        f"runtime_error: {type(decl_err).__name__}: {decl_err}"
                    )
                    warnings.append(
                        f"Declustering raised "
                        f"{type(decl_err).__name__}: {decl_err}. "
                        f"Reverting to pre-declustering GPD fit."
                    )
                    extremal_index_theta = None
                    n_clusters_post = None
                    decluster_reduction_ratio = None
                    xi_post = None
                    sigma_post = None
                    ks_stat_post = None
                    ks_pval_post = None
                    var_values_post = None
                    es_values_post = None
                    var_bias_corr = None
                    var_bias_corr_pct = None

        # Declustering Summary output table (Q9)
        decl_table = None
        if decluster_applied:
            def _fmt_ci(lo, hi):
                if lo is None or hi is None:
                    return "N/A"
                return f"[{lo}, {hi}]"
            decl_rows = [
                ["Extremal index θ (Ferro-Segers 2003)",
                 round(float(extremal_index_theta), 6)],
                ["Estimator branch", extremal_index_method],
                ["N exceedances pre-decluster", int(n_exceed)],
                ["N clusters post-decluster (K)",
                 int(n_clusters_post)],
                ["Reduction ratio K / N_u",
                 round(float(decluster_reduction_ratio), 6)],
                ["GPD shape ξ pre-decluster", round(float(xi_hat), 6)],
                ["GPD shape ξ post-decluster",
                 round(float(xi_post), 6)],
                ["GPD shape ξ pre 95% CI",
                 _fmt_ci(xi_ci[0], xi_ci[1])],
                ["GPD shape ξ post 95% CI",
                 _fmt_ci(xi_ci_post[0], xi_ci_post[1])],
                ["GPD scale σ pre-decluster",
                 round(float(sigma_hat), 6)],
                ["GPD scale σ post-decluster",
                 round(float(sigma_post), 6)],
                ["GPD scale σ pre 95% CI",
                 _fmt_ci(sigma_ci[0], sigma_ci[1])],
                ["GPD scale σ post 95% CI",
                 _fmt_ci(sigma_ci_post[0], sigma_ci_post[1])],
                ["KS p-value post-decluster",
                 round(float(ks_pval_post), 6)],
                ["99% VaR bias correction (post − pre)",
                 round(float(var_bias_corr), 6)
                 if var_bias_corr is not None else None],
                ["99% VaR bias correction %",
                 f"{var_bias_corr_pct * 100:+.2f}%"
                 if var_bias_corr_pct is not None else None],
            ]
            decl_table = make_table(
                "Declustering Summary",
                ["Metric", "Value"],
                decl_rows,
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
        if decl_table is not None:
            # Declustering Summary placed just after gof_table for
            # user-facing salience (Q9 / D8 placement)
            tables.insert(3, decl_table)
        if mef_table is not None:
            tables.append(mef_table)

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C6) ──────────────────────────
        # Flag fields for Tier 3 triggers: D5 declustering caveat
        # always fires for time-indexed input (which is the usual case
        # for financial-return EVT analysis). D6 30-exceedance-
        # sufficiency warning bridges the 10-observation hard minimum
        # and the 30-observation reliable-fit rule-of-thumb.
        _is_time_series = bool(ctx.time) and len(ctx.time) >= 2
        _exceedances_below_30 = bool(10 <= n_exceed < 30)

        # Pack VaR/ES levels + values for spec-side rendering.
        # risk_rows stores conf_level as a formatted string ("95.0%"),
        # so we reconstruct the raw float from conf_levels (the input
        # list) in parallel. This keeps the spec rendering decoupled
        # from the wrapper's display formatting.
        _conf_levels = [float(p) for p in conf_levels]
        _var_values = []
        _es_values = []
        for row in risk_rows:
            try:
                _var_values.append(float(row[1]))
                _es_values.append(float(row[2]) if row[2] is not None else None)
            except Exception:
                continue

        audit = {
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
            "confidence_levels": _conf_levels,
            "var_values": _var_values,
            "es_values": _es_values,
            "is_time_series_input": _is_time_series,
            "exceedances_below_30": _exceedances_below_30,
            "series_name": name,
            # Follow-up 3c — declustering fields (None on
            # decluster=False or fallback)
            "decluster_requested": bool(decluster_requested),
            "decluster_applied": bool(decluster_applied),
            "decluster_fallback_reason": decluster_fallback_reason,
            "extremal_index_theta": (
                round(float(extremal_index_theta), 6)
                if extremal_index_theta is not None else None
            ),
            "extremal_index_method": extremal_index_method,
            "n_clusters_post_decluster": n_clusters_post,
            "decluster_reduction_ratio": (
                round(float(decluster_reduction_ratio), 6)
                if decluster_reduction_ratio is not None else None
            ),
            "xi_post_decluster": (
                round(float(xi_post), 6) if xi_post is not None else None
            ),
            "sigma_post_decluster": (
                round(float(sigma_post), 6)
                if sigma_post is not None else None
            ),
            "ks_stat_post_decluster": (
                round(float(ks_stat_post), 6)
                if ks_stat_post is not None else None
            ),
            "ks_pval_post_decluster": (
                round(float(ks_pval_post), 6)
                if ks_pval_post is not None else None
            ),
            "var_values_post_decluster": var_values_post,
            "es_values_post_decluster": es_values_post,
            "var_bias_correction_at_99pct": (
                round(float(var_bias_corr), 6)
                if var_bias_corr is not None else None
            ),
            "var_bias_correction_pct_at_99pct": (
                round(float(var_bias_corr_pct), 6)
                if var_bias_corr_pct is not None else None
            ),
            # Mean residual life diagnostic (always-on, Q8)
            "mean_excess_at_threshold": (
                round(float(mrl_e_emp), 6) if mrl_e_emp is not None else None
            ),
            "mean_excess_implied_by_gpd": (
                round(float(mrl_e_imp), 6) if mrl_e_imp is not None else None
            ),
            "mean_excess_match_verdict": mrl_verdict,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("evt_pot_gpd", dict(audit))

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
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


# ---------------------------------------------------------------------
# Follow-up 3c — Ferro-Segers (2003) intervals declustering helpers
# ---------------------------------------------------------------------


def _ferro_segers_extremal_index(inter_times):
    """Ferro & Segers (2003) intervals estimator for the extremal
    index θ.

    Branching formula per the paper:
      - If max(T_i) ≤ 2 (all inter-exceedance times are 1 or 2),
        use the simple (Σ T²)-based form.
      - Otherwise, use the bias-corrected (T-1)(T-2)-based form.

    Returns (theta, branch_label). theta is clamped to [1e-6, 1.0].
    """
    T = np.asarray(inter_times, dtype=np.float64)
    n_T = len(T)
    if n_T < 2:
        return 1.0, "degenerate"

    if T.max() > 2:
        num = 2.0 * (np.sum(T - 1.0)) ** 2
        den = n_T * np.sum((T - 1.0) * (T - 2.0))
        branch = "(T_i-1)(T_i-2)"
    else:
        num = 2.0 * (np.sum(T)) ** 2
        den = n_T * np.sum(T ** 2)
        branch = "T_i"

    if den <= 0:
        # Degenerate — fallback to θ=1 (no clustering signal from data)
        return 1.0, branch + "_degenerate"
    theta = num / den
    theta = max(1e-6, min(theta, 1.0))
    return float(theta), branch


def _identify_clusters(exceedance_positions, exceedance_values,
                       theta, n_exceed):
    """Cluster-peak identification via the intervals method.

    1. K = ceil(theta * N_u), capped at N_u.
    2. Find K-1 largest inter-exceedance gaps.
    3. Walk through exceedances, crossing those gaps to partition
       into K clusters.
    4. Each cluster's peak = max excess value within that cluster.

    Returns (cluster_peaks, K, cluster_assignment).
    """
    K = int(np.ceil(theta * n_exceed))
    K = max(1, min(K, n_exceed))

    if K == n_exceed:
        # No meaningful reduction — each exceedance is its own cluster
        return exceedance_values.copy(), K, np.arange(n_exceed)
    if K == 1:
        # Single cluster — sample max
        return np.array([float(exceedance_values.max())]), 1, np.zeros(n_exceed, dtype=int)

    # Inter-exceedance gaps
    T = np.diff(exceedance_positions)  # length N_u - 1
    if len(T) < K - 1:
        # Degenerate — too few gaps to separate K clusters
        return exceedance_values.copy(), n_exceed, np.arange(n_exceed)

    # Indices of the K-1 largest gaps (deterministic via argpartition)
    gap_indices = np.argpartition(T, -(K - 1))[-(K - 1):]
    is_boundary = np.zeros(len(T), dtype=bool)
    is_boundary[gap_indices] = True

    cluster_assignment = np.zeros(n_exceed, dtype=int)
    current_cluster = 0
    for i in range(1, n_exceed):
        if is_boundary[i - 1]:
            current_cluster += 1
        cluster_assignment[i] = current_cluster

    actual_K = int(cluster_assignment.max() + 1)
    cluster_peaks = np.zeros(actual_K, dtype=np.float64)
    for c in range(actual_K):
        mask = cluster_assignment == c
        if mask.any():
            cluster_peaks[c] = float(exceedance_values[mask].max())
    return cluster_peaks, actual_K, cluster_assignment


def _mean_residual_life_diagnostic(exceedances, xi, sigma, threshold):
    """Compare empirical mean excess vs GPD-implied mean excess at
    threshold u.

    Empirical: e_hat(u) = mean(X - u | X > u) = mean(exceedances).
    GPD-implied: e(u) = (σ + ξu) / (1 - ξ) for ξ < 1.

    Returns (e_empirical, e_implied, verdict_str).
    30% match threshold per Q8 / Phase 2 D14.
    """
    try:
        e_emp = float(np.mean(exceedances))
    except Exception:
        return None, None, "unavailable"
    if xi is None or sigma is None:
        return e_emp, None, "implied value unavailable (xi/sigma missing)"
    try:
        xi_f = float(xi)
        if xi_f >= 1.0:
            return e_emp, None, (
                "GPD mean residual life is infinite for ξ ≥ 1; "
                "diagnostic not meaningful"
            )
        e_imp = float((float(sigma) + xi_f * float(threshold)) / (1.0 - xi_f))
        diff = abs(e_imp - e_emp)
        denom = max(abs(e_emp), 1e-9)
        if diff / denom < 0.30:
            verdict = "consistent with GPD"
        else:
            verdict = (
                "notable mismatch — possible threshold or model "
                "mis-specification"
            )
        return e_emp, e_imp, verdict
    except Exception:
        return e_emp, None, "implied value computation failed"
