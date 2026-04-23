"""
HAR-CJ (Heterogeneous Autoregressive with Continuous + Jump
decomposition) — Andersen, Bollerslev & Diebold (2007).

Distinct from HAR-RV (Corsi 2009; C6): HAR-RV treats realized
variance as a single cascade (daily / weekly / monthly averages of
past RV). HAR-CJ first decomposes each day's RV into a continuous
component C_t and a jump component J_t via the Barndorff-Nielsen-
Shephard (BNS) ratio test, then fits a 7-regressor HAR-family
regression with separate cascades for C and J:

    y_t = beta_0
        + beta_cd * C_{t-1} + beta_cw * avg_wk(C) + beta_cm * avg_mo(C)
        + beta_jd * J_{t-1} + beta_jw * avg_wk(J) + beta_jm * avg_mo(J)
        + epsilon_t

Expected empirical finding (ABD 2007): jumps have near-zero
persistence (beta_j's small, often insignificant) while continuous
volatility is highly persistent (Sigma beta_c ≈ 0.7-0.9). Users
doing operational risk management get a direct read on whether
realized volatility variation is driven by persistent continuous
dynamics or transient jumps.

Input contract (positional multi-series):
    series[0] = RV series (required; primary)
    series[1] = BV series (required; bipower variation)
    series[2] = TQ series (optional; realized tripower quarticity.
                If absent, TQ is approximated as BV^2 with Tier 3
                D2 honest-disclosure trigger.)

Required ctx.params:
    M : int
        Intraday sampling frequency (number of intraday return
        intervals used when computing RV and BV upstream). No
        default — the BNS z-statistic scales with sqrt(M) and has
        no robust default across asset classes / session lengths.

Optional ctx.params:
    jump_alpha : float (default 0.01)
        Significance level for the BNS jump test. Lower is more
        conservative (fewer jumps detected).
    h_ahead, daily_lag, weekly_lag, monthly_lag, use_log :
        Same semantics as HAR-RV (Corsi 2009). h_ahead forward-
        averages the dependent variable; use_log applies log
        transform (warned against on HAR-CJ because J=0 days
        create log-space spikes).

Follow-up 3b. See planning doc for Q1-Q8 and D5-D9 decision
rationale.

TODO(follow-up 3c): extract shared helpers (cascade-regressor
construction, OLS + stats, residual diagnostics) to a
_har_common.py module once a third HAR variant lands. For 3b,
helpers are inlined per the user's "don't refactor har_rv this
round" directive.
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
    Estimate a HAR-CJ model on paired realized-volatility and
    bipower-variation series.

    See module docstring for input contract and parameter
    semantics.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)
        warnings = []

        # ── Input validation ───────────────────────────────────────
        series_list = ctx.get_all_series()
        if len(series_list) < 2:
            return make_error_response(
                ctx,
                "HAR-CJ requires RV and BV as separate input series: "
                "position 1 = realized variance, position 2 = "
                "bipower variation. Position 3 may optionally carry "
                "realized tripower quarticity (TQ); if absent, TQ is "
                "approximated as BV^2 with honest disclosure "
                "(see Tier 2 / Tier 3 D2 trigger).",
                error_fixes=[
                    "Select both RV and BV columns when running HAR-CJ.",
                    "If BV is not pre-computed upstream, use HAR-RV "
                    "instead (single-series wrapper).",
                ],
            )

        rv_name, rv = series_list[0]
        bv_name, bv = series_list[1]
        if len(series_list) >= 3:
            tq_name, tq = series_list[2]
        else:
            tq_name, tq = None, None

        M_raw = ctx.get_param("M", None)
        if M_raw is None:
            return make_error_response(
                ctx,
                "HAR-CJ requires ctx.params['M']: intraday sampling "
                "frequency (number of intraday return intervals used "
                "when computing RV and BV upstream). The BNS jump-"
                "detection z-statistic depends on M and has no "
                "robust default across asset classes — user must "
                "supply it.",
                error_fixes=[
                    "Set params M to your upstream intraday "
                    "sampling count (e.g., 79 for 5-minute returns "
                    "in a 6.5-hour US equity session).",
                ],
            )
        try:
            M = int(M_raw)
        except Exception:
            return make_error_response(
                ctx, f"M must be a positive integer, got {M_raw!r}.",
            )
        if M <= 0:
            return make_error_response(
                ctx, f"M must be positive, got {M}.",
            )

        # Align lengths
        n_raw = min(len(rv), len(bv))
        if tq is not None:
            n_raw = min(n_raw, len(tq))
        rv = np.asarray(rv[:n_raw], dtype=np.float64)
        bv = np.asarray(bv[:n_raw], dtype=np.float64)
        if tq is not None:
            tq = np.asarray(tq[:n_raw], dtype=np.float64)

        # Drop NaN (any position with NaN in any series)
        if tq is not None:
            mask = ~(np.isnan(rv) | np.isnan(bv) | np.isnan(tq))
        else:
            mask = ~(np.isnan(rv) | np.isnan(bv))
        n_dropped = int((~mask).sum())
        if n_dropped > 0:
            warnings.append(
                f"{n_dropped} rows with NaN in RV / BV / TQ dropped."
            )
        rv = rv[mask]
        bv = bv[mask]
        if tq is not None:
            tq = tq[mask]
        n = len(rv)

        if n < 50:
            return make_error_response(
                ctx,
                f"Only {n} valid RV / BV observations after cleaning. "
                f"HAR-CJ needs at least 50 for reliable estimation.",
            )

        # RV/BV non-negativity
        if np.any(rv < 0) or np.any(bv < 0):
            warnings.append(
                "Negative values detected in RV or BV; these "
                "quantities should be non-negative by construction. "
                "Results may be unreliable — verify upstream "
                "computation."
            )

        # TQ fallback (Phase 1 Q4: BV^2 as jump-robust lower bound)
        tq_approximated = False
        if tq is None:
            tq = bv ** 2
            tq_approximated = True

        # ── BNS jump detection ─────────────────────────────────────
        progress_callback("BNS jump detection", 20)

        jump_alpha = float(ctx.get_param("jump_alpha", 0.01))
        if not (0.0 < jump_alpha < 0.5):
            return make_error_response(
                ctx,
                f"jump_alpha must be in (0, 0.5), got {jump_alpha}.",
            )
        jump_threshold = float(sp_stats.norm.ppf(1.0 - jump_alpha))
        # theta constant from Huang & Tauchen (2005) / ABD 2007
        theta_const = (np.pi / 2.0) ** 2 + np.pi - 5.0

        # z-statistic: (RV - BV) / sqrt(theta * max(TQ, BV^2) / M)
        denom = np.sqrt(
            np.maximum(theta_const * np.maximum(tq, bv ** 2) / M, 1e-24)
        )
        z_stat = (rv - bv) / denom
        is_jump = z_stat > jump_threshold
        # D6 safeguard: when RV < BV (numerical / microstructure
        # artifact), force is_jump=False regardless of z_stat sign.
        is_jump = is_jump & (rv >= bv)

        # Decomposition
        j_series = np.where(is_jump, np.maximum(rv - bv, 0.0), 0.0)
        c_series = rv - j_series

        n_jumps = int(is_jump.sum())
        jump_fraction = n_jumps / n if n > 0 else 0.0
        mean_jump_contrib = (
            float(j_series.mean() / rv.mean())
            if rv.mean() > 0 else 0.0
        )
        mean_cont_contrib = 1.0 - mean_jump_contrib
        bns_z_max = float(z_stat.max()) if n > 0 else 0.0

        # ── HAR-CJ regressor construction ──────────────────────────
        progress_callback("Constructing HAR-CJ regressors", 35)

        daily_lag = int(ctx.get_param("daily_lag", 1))
        weekly_lag = int(ctx.get_param("weekly_lag", 5))
        monthly_lag = int(ctx.get_param("monthly_lag", 22))
        use_log = bool(ctx.get_param("use_log", False))
        h_ahead = int(ctx.get_param("h_ahead", 1))

        min_obs = monthly_lag + h_ahead + 10
        if n < min_obs:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. HAR-CJ needs at "
                f"least {min_obs} (monthly_lag={monthly_lag} + "
                f"h_ahead={h_ahead} + 10).",
            )

        # D5: use_log on HAR-CJ is awkward because J has many zeros.
        # Warn but allow.
        if use_log and jump_fraction < 0.10:
            warnings.append(
                f"use_log=True applied to HAR-CJ with low jump "
                f"fraction ({jump_fraction:.1%}). J (jump component) "
                f"has many zero values on non-jump days; log(J + "
                f"epsilon) introduces large negative values that may "
                f"distort OLS. Prefer use_log=False for HAR-CJ "
                f"unless you have a specific reason."
            )

        if use_log:
            rv_work = np.log(np.where(rv > 0, rv, np.finfo(float).eps))
            c_work = np.log(np.where(c_series > 0, c_series, np.finfo(float).eps))
            j_work = np.log(j_series + 1e-10)
        else:
            rv_work = rv
            c_work = c_series
            j_work = j_series

        start = monthly_lag
        end = len(rv_work) - (h_ahead - 1) if h_ahead > 1 else len(rv_work)
        T = end - start

        if T < 10:
            return make_error_response(
                ctx,
                "Not enough observations after HAR-CJ regressor "
                "construction (need at least 10 usable rows).",
            )

        y = np.zeros(T)
        X_cd = np.zeros(T); X_cw = np.zeros(T); X_cm = np.zeros(T)
        X_jd = np.zeros(T); X_jw = np.zeros(T); X_jm = np.zeros(T)

        for t_idx in range(T):
            t = start + t_idx
            if h_ahead > 1:
                y[t_idx] = np.mean(rv_work[t:t + h_ahead])
            else:
                y[t_idx] = rv_work[t]
            X_cd[t_idx] = np.mean(c_work[t - daily_lag:t])
            X_cw[t_idx] = np.mean(c_work[t - weekly_lag:t])
            X_cm[t_idx] = np.mean(c_work[t - monthly_lag:t])
            X_jd[t_idx] = np.mean(j_work[t - daily_lag:t])
            X_jw[t_idx] = np.mean(j_work[t - weekly_lag:t])
            X_jm[t_idx] = np.mean(j_work[t - monthly_lag:t])

        X = np.column_stack([
            np.ones(T), X_cd, X_cw, X_cm, X_jd, X_jw, X_jm,
        ])
        coef_names = [
            "Intercept (beta_0)",
            "Continuous daily (beta_cd)",
            "Continuous weekly (beta_cw)",
            "Continuous monthly (beta_cm)",
            "Jump daily (beta_jd)",
            "Jump weekly (beta_jw)",
            "Jump monthly (beta_jm)",
        ]

        progress_callback("Running OLS estimation", 50)
        beta, resid, R2, se, t_stats, p_vals = _ols_with_stats(X, y)
        if beta is None:
            return make_error_response(
                ctx,
                "OLS regression failed (singular matrix). The "
                "regressors may be perfectly collinear — likely "
                "because jumps are never detected (all J=0), leaving "
                "duplicate continuous cascades.",
                error_fixes=[
                    "Try a larger jump_alpha (more liberal threshold).",
                    "Verify M matches the intraday sampling rate.",
                    "Use HAR-RV instead if this series has no "
                    "detectable jumps.",
                ],
            )

        y_hat = X @ beta
        resid = y - y_hat
        k = X.shape[1]
        R2_adj = (
            1 - (1 - R2) * (T - 1) / (T - k - 1)
            if T > k + 1 else R2
        )

        dof = T - k
        sigma2 = (
            float(np.sum(resid ** 2) / dof)
            if dof > 0 else float(np.sum(resid ** 2) / T)
        )
        log_lik = -T / 2 * (
            np.log(2 * np.pi) + np.log(max(sigma2, 1e-24)) + 1
        )
        aic = -2 * log_lik + 2 * k
        bic = -2 * log_lik + k * np.log(T)

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Computing diagnostics", 65)

        # Bootstrap confidence intervals (Balanced/Thorough)
        ci_low = [None] * k
        ci_high = [None] * k
        if cfg["bootstrap_samples"] > 0:
            progress_callback("Bootstrap confidence intervals", 72)
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

        # Residual diagnostics
        lb_stat = lb_pval = None
        jb_stat = jb_pval = None
        dw = None
        if cfg["compute_residual_diag"]:
            try:
                lb_stat, lb_pval = _ljung_box(resid, 10)
            except Exception:
                pass
            try:
                jb_stat, jb_pval = sp_stats.jarque_bera(resid)
                jb_stat = float(jb_stat)
                jb_pval = float(jb_pval)
            except Exception:
                pass
            try:
                if np.sum(resid ** 2) > 0:
                    dw = float(
                        np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2)
                    )
            except Exception:
                pass

        progress_callback("Building output tables", 85)

        # ── Output tables (D8 order) ───────────────────────────────
        # 1. HAR-CJ Coefficients
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
        coef_table = make_table(
            "HAR-CJ Coefficients",
            ["Coefficient", "Estimate", "Std Error", "t-stat",
             "p-value", "CI 2.5%", "CI 97.5%"],
            coef_rows,
        )

        # 2. Jump Detection Summary (D8 — new table for HAR-CJ)
        jds_rows = [
            ["Jump alpha (BNS test)", round(jump_alpha, 6)],
            ["Jump z-threshold", round(jump_threshold, 4)],
            ["Intraday M", M],
            ["Jump days count", n_jumps],
            ["Jump days fraction", round(jump_fraction, 6)],
            ["Mean jump contribution", round(mean_jump_contrib, 6)],
            ["Mean continuous contribution", round(mean_cont_contrib, 6)],
            ["BNS z-statistic max", round(bns_z_max, 4)],
            ["TQ approximated (BV^2)", "Yes" if tq_approximated else "No"],
        ]
        jds_table = make_table(
            "Jump Detection Summary", ["Metric", "Value"], jds_rows,
        )

        # 3. Model Fit
        fit_rows = [
            ["R-squared", round(R2, 6)],
            ["Adjusted R-squared", round(R2_adj, 6)],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["Residual Std Error", round(float(np.sqrt(max(sigma2, 0.0))), 6)],
            ["Observations (T)", T],
            ["Model", "log-HAR-CJ" if use_log else "HAR-CJ"],
            ["Forecast horizon (h)", h_ahead],
            ["Daily lag", daily_lag],
            ["Weekly lag", weekly_lag],
            ["Monthly lag", monthly_lag],
        ]
        fit_table = make_table("Model Fit", ["Metric", "Value"], fit_rows)

        # 4. Residual Diagnostics (optional)
        diag_rows = []
        if lb_pval is not None:
            diag_rows.append(["Ljung-Box Q(10)", round(float(lb_stat), 4), round(float(lb_pval), 6)])
        if jb_pval is not None:
            diag_rows.append(["Jarque-Bera", round(float(jb_stat), 4), round(float(jb_pval), 6)])
        if dw is not None:
            diag_rows.append(["Durbin-Watson", round(float(dw), 4), ""])
        diag_table = None
        if diag_rows:
            diag_table = make_table(
                "Residual Diagnostics",
                ["Test", "Statistic", "p-value"], diag_rows,
            )

        # 5. Fitted Values (subsampled for large T)
        time_col = (
            ctx.time if ctx.time and len(ctx.time) >= start + T
            else list(range(1, T + 1))
        )
        if isinstance(time_col, list) and len(time_col) >= start + T:
            time_subset = time_col[start:start + T]
        else:
            time_subset = list(range(start + 1, start + T + 1))
        max_display = 500
        step = max(1, T // max_display)
        ts_rows = []
        for i in range(0, T, step):
            ts_rows.append([
                time_subset[i],
                round(float(y[i]), 6),
                round(float(y_hat[i]), 6),
                round(float(resid[i]), 6),
            ])
        ts_table = make_table(
            "Fitted Values",
            ["Time", "Actual", "Fitted", "Residual"],
            ts_rows,
        )

        # ── Baseline RMSE: rolling-22-period mean RV (D9) ──────────
        try:
            baseline_forecasts = np.zeros(T)
            for t_idx in range(T):
                t = start + t_idx
                baseline_forecasts[t_idx] = (
                    np.mean(rv_work[t - 22:t]) if t >= 22
                    else np.mean(rv_work[:t + 1])
                )
            _baseline_rmse = float(np.sqrt(np.mean((y - baseline_forecasts) ** 2)))
        except Exception:
            _baseline_rmse = None
        _fit_rmse = float(np.sqrt(np.mean(resid ** 2)))

        # 1-step-ahead forecast from last in-sample state
        try:
            _last_c_d = float(np.mean(c_work[-daily_lag:]))
            _last_c_w = float(np.mean(c_work[-weekly_lag:]))
            _last_c_m = float(np.mean(c_work[-monthly_lag:]))
            _last_j_d = float(np.mean(j_work[-daily_lag:]))
            _last_j_w = float(np.mean(j_work[-weekly_lag:]))
            _last_j_m = float(np.mean(j_work[-monthly_lag:]))
            _forecast_next = float(
                beta[0]
                + beta[1] * _last_c_d + beta[2] * _last_c_w + beta[3] * _last_c_m
                + beta[4] * _last_j_d + beta[5] * _last_j_w + beta[6] * _last_j_m
            )
            if use_log:
                _forecast_end_value = float(np.exp(_forecast_next))
                _last_observed_value = float(np.exp(rv_work[-1]))
            else:
                _forecast_end_value = _forecast_next
                _last_observed_value = float(rv_work[-1])
        except Exception:
            _forecast_end_value = None
            _last_observed_value = None

        try:
            _series_mean = float(np.mean(rv_work))
            _series_std = (
                float(np.std(rv_work, ddof=1)) if len(rv_work) > 1 else None
            )
        except Exception:
            _series_mean = None
            _series_std = None

        # ── Plain-English summary ──────────────────────────────────
        cont_persist = float(beta[1] + beta[2] + beta[3])
        jump_persist = float(beta[4] + beta[5] + beta[6])
        plain_english = (
            f"HAR-CJ model estimated on '{rv_name}' "
            f"({T} effective observations; h={h_ahead}). "
            f"{n_jumps} of {n} days ({jump_fraction:.1%}) classified "
            f"as jumps (BNS ratio test at alpha={jump_alpha:.2f}). "
            f"Continuous persistence sum = {cont_persist:.3f}; "
            f"jump persistence sum = {jump_persist:+.3f}. "
            f"R-squared = {R2:.4f}."
        )
        if tq_approximated:
            plain_english += (
                " TQ was approximated as BV^2 (see Tier 3 D2)."
            )

        charting = (
            "Three-panel chart: top panel shows RV with jump days "
            "highlighted; middle panel decomposes into continuous C "
            "and jump J series; bottom panel shows fitted vs actual "
            "RV with residuals."
        )

        progress_callback("Done", 100)

        # ── Audit fields ──────────────────────────────────────────
        audit = {
            "series_name": rv_name,
            "model": "log-HAR-CJ" if use_log else "HAR-CJ",
            "use_log": use_log,
            "daily_lag": daily_lag,
            "weekly_lag": weekly_lag,
            "monthly_lag": monthly_lag,
            "h_ahead": h_ahead,

            # Jump-detection fields
            "M_sampling_frequency": M,
            "jump_alpha": round(jump_alpha, 6),
            "jump_detection_threshold": round(jump_threshold, 6),
            "jump_days_count": n_jumps,
            "jump_days_fraction": round(jump_fraction, 6),
            "mean_jump_contribution": round(mean_jump_contrib, 6),
            "mean_continuous_contribution": round(mean_cont_contrib, 6),
            "bns_test_statistic_max": round(bns_z_max, 6),
            "tq_approximated": bool(tq_approximated),

            # Regression coefficients
            "beta_0": round(float(beta[0]), 6),
            "beta_cd": round(float(beta[1]), 6),
            "beta_cw": round(float(beta[2]), 6),
            "beta_cm": round(float(beta[3]), 6),
            "beta_jd": round(float(beta[4]), 6),
            "beta_jw": round(float(beta[5]), 6),
            "beta_jm": round(float(beta[6]), 6),

            # p-values (for D3 trigger: significantly-negative jump β)
            "beta_jd_pvalue": round(float(p_vals[4]), 6) if p_vals[4] is not None else None,
            "beta_jw_pvalue": round(float(p_vals[5]), 6) if p_vals[5] is not None else None,
            "beta_jm_pvalue": round(float(p_vals[6]), 6) if p_vals[6] is not None else None,

            # Persistence-sum breakdown
            "continuous_persistence_sum": round(cont_persist, 4),
            "jump_persistence_sum": round(jump_persist, 4),

            # Fit quality + forecaster-family Tier 1 inputs
            "R2": round(R2, 6),
            "R2_adj": round(R2_adj, 6),
            "aic": round(aic, 2),
            "bic": round(bic, 2),
            "n_obs": T,
            "n_obs_raw": n,
            "bootstrap_samples": cfg["bootstrap_samples"],
            "fit_rmse": round(_fit_rmse, 6),
            "baseline_rmse": round(_baseline_rmse, 6) if _baseline_rmse is not None else None,
            "baseline_label": "rolling-22-period mean RV",
            "forecast_end_value": round(_forecast_end_value, 6) if _forecast_end_value is not None else None,
            "last_observed_value": round(_last_observed_value, 6) if _last_observed_value is not None else None,
            "series_mean": round(_series_mean, 6) if _series_mean is not None else None,
            "series_std": round(_series_std, 6) if _series_std is not None else None,
            "ljung_box_lag10_pvalue": (
                round(float(lb_pval), 6) if lb_pval is not None else None
            ),
            "jarque_bera_pvalue": (
                round(float(jb_pval), 6) if jb_pval is not None else None
            ),
            **format_significance_disclosure(
                test_name=(
                    "HAR-CJ OLS t-tests on continuous and jump "
                    "cascade coefficients + BNS jump-detection "
                    "z-test"
                ),
                critical_value_formula=(
                    "OLS p = 2*(1 - t.cdf(|t_stat|, T-k)); standard "
                    "errors assume iid homoskedastic residuals "
                    "(NOT HAC-corrected). BNS jump test: z > "
                    "Phi_inverse(1 - alpha) at alpha=jump_alpha."
                ),
                ac_corrected=False,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("har_cj", dict(audit))

        tables = [coef_table, jds_table, fit_table]
        if diag_table is not None:
            tables.append(diag_table)
        tables.append(ts_table)

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
            f"HAR-CJ estimation failed: {e}",
            error_fixes=[
                "Ensure RV and BV are supplied as separate series.",
                "Verify M parameter matches upstream intraday "
                "sampling rate.",
                "Check for sufficient observations "
                "(need > monthly_lag + h_ahead + 10).",
                "Try a more liberal jump_alpha if detection is "
                "rejecting all candidate jumps.",
            ],
        )


# ---------------------------------------------------------------------
# Inline helpers
# TODO(follow-up 3c): migrate to engine/techniques/_har_common.py
# once a third HAR variant lands. For 3b, these duplicate HAR-RV's
# equivalent helpers to avoid refactoring har_rv as part of this
# follow-up (per Phase 1 Q1 decision).
# ---------------------------------------------------------------------


def _ols_with_stats(X, y):
    """OLS estimation with standard errors, t-stats, and p-values.
    Returns (beta, residuals, R2, se, t_stats, p_vals)."""
    n, k = X.shape
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        return None, None, None, [None] * k, [None] * k, [None] * k

    y_hat = X @ beta
    resid = y - y_hat
    SS_res = float(np.sum(resid ** 2))
    SS_tot = float(np.sum((y - np.mean(y)) ** 2))
    R2 = 1 - SS_res / SS_tot if SS_tot > 0 else 0.0

    sigma2 = SS_res / (n - k) if n > k else SS_res / max(n, 1)
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(sigma2 * XtX_inv))
        t_stats = beta / np.where(se > 0, se, 1e-24)
        p_vals = 2 * (1 - sp_stats.t.cdf(np.abs(t_stats), df=n - k))
    except np.linalg.LinAlgError:
        se = [None] * k
        t_stats = [None] * k
        p_vals = [None] * k

    return beta, resid, R2, se, t_stats, p_vals


def _ljung_box(resid, max_lag):
    """Simple Ljung-Box Q-statistic (matches HAR-RV's helper)."""
    n = len(resid)
    acf_vals = np.correlate(
        resid - np.mean(resid), resid - np.mean(resid), mode="full",
    )
    acf_vals = acf_vals[n - 1:] / acf_vals[n - 1]  # normalize
    Q = 0.0
    for k in range(1, min(max_lag + 1, n)):
        Q += acf_vals[k] ** 2 / (n - k)
    Q *= n * (n + 2)
    p_val = 1 - sp_stats.chi2.cdf(Q, df=max_lag)
    return float(Q), float(p_val)
