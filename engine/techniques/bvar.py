"""
Bayesian VAR with Minnesota / Shrinkage Priors for Time Series Lab.

Implements a Bayesian Vector Autoregression using the Minnesota prior
(Litterman prior) with conjugate Normal-Inverse-Wishart posterior.
Estimation via analytical posterior (no MCMC needed).

Implemented with numpy/scipy only (no external Bayesian library).
"""

import numpy as np
from scipy import stats as sp_stats
from scipy import linalg

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {
        "max_lags": 2, "n_draws": 500, "lambda1": 0.1, "lambda2": 0.5,
        "compute_irf_fevd": False, "irf_horizon": 16,
    },
    "Balanced": {
        "max_lags": 4, "n_draws": 1000, "lambda1": 0.1, "lambda2": 1.0,
        "compute_irf_fevd": True, "irf_horizon": 24,
    },
    "Thorough": {
        "max_lags": 6, "n_draws": 5000, "lambda1": 0.1, "lambda2": 1.0,
        "compute_irf_fevd": True, "irf_horizon": 36,
    },
}


# ---------------------------------------------------------------------------
# IRF / FEVD helpers (Follow-up 1c)
# ---------------------------------------------------------------------------

def _compute_posterior_irf(
    B_post, B_post_var, Sigma_post, k, p, m, include_const,
    n_draws, H, rng,
):
    """Monte Carlo posterior IRF under Cholesky identification.

    Reuses the same coefficient-draw strategy as the forecast MC loop
    (equation-by-equation Normal draws from posterior mean ± std).
    Innovation covariance Σ is held at the posterior point estimate
    (R1 Cholesky disclosure): credible bands therefore reflect VAR
    coefficient uncertainty but not Σ uncertainty. This is a common
    BVAR simplification when avoiding MCMC.

    Returns a dict with:
      median    : (H, k, k)  — [h, response, shock]
      lower_5   : same shape (5th percentile across draws)
      upper_95  : same shape (95th percentile across draws)
      cholesky  : (k, k)     — point-estimate Cholesky lower factor
      tensor    : (n_draws, H, k, k) — kept for FEVD reuse
    """
    try:
        P = np.linalg.cholesky(Sigma_post)
    except np.linalg.LinAlgError:
        # Near-singular Σ — add a tiny ridge so Cholesky succeeds.
        P = np.linalg.cholesky(Sigma_post + 1e-8 * np.eye(k))

    irf_tensor = np.zeros((n_draws, H, k, k))

    for d in range(n_draws):
        # Draw coefficients from posterior (equation-by-equation).
        B_draw = np.zeros((m, k))
        for i in range(k):
            sd = np.sqrt(np.maximum(B_post_var[i], 1e-12))
            B_draw[:, i] = B_post[:, i] + sd * rng.standard_normal(m)

        # Extract A_1, ..., A_p from B_draw (drop constant row if any).
        # B_draw layout: rows [0..k*p-1] stack lag-1 through lag-p
        # blocks; each block is (k, k). Within a block, row j, column
        # i is "equation i's coefficient on variable j at lag-(blk+1)".
        # In the Y_t = A_lag @ Y_{t-lag} convention, A_lag[i, j] is
        # the coefficient on variable j in equation i, so A_lag = block.T.
        A_list = []
        for lag in range(p):
            block = B_draw[lag * k:(lag + 1) * k, :]  # (k, k)
            A_list.append(block.T)

        # MA coefficients via recursion:
        # Phi_0 = I, Phi_h = sum_{j=1..min(h,p)} A_j @ Phi_{h-j}.
        Phi = [np.eye(k)]
        for h in range(1, H):
            Phi_h = np.zeros((k, k))
            for j in range(1, min(h, p) + 1):
                Phi_h += A_list[j - 1] @ Phi[h - j]
            Phi.append(Phi_h)

        # Orthogonalized IRF: Theta_h = Phi_h @ P.
        for h in range(H):
            irf_tensor[d, h] = Phi[h] @ P

    median_irf = np.median(irf_tensor, axis=0)
    lower_5 = np.percentile(irf_tensor, 5, axis=0)
    upper_95 = np.percentile(irf_tensor, 95, axis=0)

    return {
        "median": median_irf,
        "lower_5": lower_5,
        "upper_95": upper_95,
        "cholesky": P,
        "tensor": irf_tensor,
    }


def _compute_posterior_fevd(irf_tensor, horizons):
    """FEVD across posterior draws at specific horizons.

    Args:
      irf_tensor: (n_draws, H_max, k, k) — IRF posterior draws
      horizons:   list of int horizons to report (<=H_max)

    Returns dict:
      median  : {horizon: (k, k)} — [i, j] = share of var i's MSE
                from shock j (rows sum to 1)
      lower_5 : {horizon: (k, k)} — 5th percentile per cell
      upper_95: {horizon: (k, k)} — 95th percentile per cell
    """
    n_draws, H_max, k, _ = irf_tensor.shape
    median_fevd = {}
    lower_5_fevd = {}
    upper_95_fevd = {}

    for h in horizons:
        if h > H_max:
            continue
        # Cumulative squared orthogonalized IRF up to horizon h-1.
        # contrib[d, i, j] = sum_{t=0..h-1} irf[d, t, i, j]^2
        contrib = np.sum(irf_tensor[:, :h, :, :] ** 2, axis=1)
        mse = np.sum(contrib, axis=2, keepdims=True)
        share = contrib / np.maximum(mse, 1e-12)
        median_fevd[int(h)] = np.median(share, axis=0)
        lower_5_fevd[int(h)] = np.percentile(share, 5, axis=0)
        upper_95_fevd[int(h)] = np.percentile(share, 95, axis=0)

    return {
        "median": median_fevd,
        "lower_5": lower_5_fevd,
        "upper_95": upper_95_fevd,
    }


def _collect_zero_straddle_pairs(irf_results, names, k, threshold_frac=0.05):
    """Identify cross-variable shock-response pairs whose 90% credible
    band straddles zero at the peak lag, filtered to non-trivial
    median effects (R2 threshold: |median_at_peak| > threshold_frac
    × max_abs_median across all cross-pairs).

    Returns list of dicts: [{shock, response, peak_horizon,
    median_at_peak, lower_at_peak, upper_at_peak}, ...]
    """
    median = irf_results["median"]
    lower = irf_results["lower_5"]
    upper = irf_results["upper_95"]

    # First pass: find peak |median| across all cross-pairs for
    # threshold calibration.
    cross_peaks = []
    for resp_idx in range(k):
        for shock_idx in range(k):
            if resp_idx == shock_idx:
                continue
            med_path = median[:, resp_idx, shock_idx]
            peak_h = int(np.argmax(np.abs(med_path)))
            cross_peaks.append(abs(float(med_path[peak_h])))
    if not cross_peaks:
        return []
    max_abs_median = max(cross_peaks)
    threshold = threshold_frac * max_abs_median

    # Second pass: collect pairs whose credible band straddles zero
    # AND whose median magnitude exceeds the threshold.
    pairs = []
    for resp_idx in range(k):
        for shock_idx in range(k):
            if resp_idx == shock_idx:
                continue
            med_path = median[:, resp_idx, shock_idx]
            peak_h = int(np.argmax(np.abs(med_path)))
            med_at_peak = float(med_path[peak_h])
            if abs(med_at_peak) <= threshold:
                # R2 filter: essentially-null effect, not "uncertain"
                continue
            lo = float(lower[peak_h, resp_idx, shock_idx])
            hi = float(upper[peak_h, resp_idx, shock_idx])
            if lo <= 0 <= hi:
                pairs.append({
                    "shock": names[shock_idx],
                    "response": names[resp_idx],
                    "peak_horizon": peak_h,
                    "median_at_peak": round(med_at_peak, 6),
                    "lower_at_peak": round(lo, 6),
                    "upper_at_peak": round(hi, 6),
                })
    return pairs


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a Bayesian VAR with Minnesota prior.

    Parameters (via ctx.params)
    ---------------------------
    lags : int, optional
        Number of lags. Preset-dependent.
    lambda1 : float, optional
        Overall tightness of the Minnesota prior. Default 0.1.
        Smaller = stronger shrinkage toward univariate random walks.
    lambda2 : float, optional
        Cross-variable shrinkage. Default preset-dependent.
    lambda3 : float, optional
        Lag decay factor. Default 1 (harmonic decay).
    horizon : int
        Forecast horizon. Default 10.
    include_constant : bool
        Include intercept. Default True.
    n_draws : int, optional
        Number of posterior draws for credible intervals. Preset-dependent.

    Series layout
    -------------
    All series are treated as endogenous variables in the VAR.
    Need at least 2 series.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        arrays = [s[1] for s in all_series]
        k = len(names)  # number of variables

        # Align and drop NaN
        min_len = min(len(a) for a in arrays)
        for i in range(k):
            arrays[i] = arrays[i][:min_len]

        Y_full = np.column_stack(arrays)
        mask = ~np.any(np.isnan(Y_full), axis=1)
        n_dropped = int((~mask).sum())
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to NaN values.")
            Y_full = Y_full[mask]

        T_full = Y_full.shape[0]

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        p = int(ctx.get_param("lags", cfg["max_lags"]))
        lambda1 = float(ctx.get_param("lambda1", cfg["lambda1"]))
        lambda2 = float(ctx.get_param("lambda2", cfg["lambda2"]))
        lambda3 = float(ctx.get_param("lambda3", 1.0))
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        include_const = ctx.get_param("include_constant", True)
        n_draws = int(ctx.get_param("n_draws", cfg["n_draws"]))
        # CAI Phase 2 Session 22 fix (F-MV-BVAR-LAMBDA): explicit
        # range gates. Pre-fix, negative lambda shrinkage values
        # were silently accepted (Minnesota prior undefined for
        # non-positive shrinkage; fitter produced garbage).
        if lambda1 <= 0:
            return make_error_response(
                ctx,
                f"lambda1 must be > 0. Got {lambda1}.",
                error_fixes=[
                    "Use a positive value; typical Minnesota prior "
                    "values are 0.1-0.3 (smaller = more shrinkage).",
                ],
            )
        if lambda2 <= 0:
            return make_error_response(
                ctx,
                f"lambda2 must be > 0. Got {lambda2}.",
                error_fixes=[
                    "Use a positive value (cross-equation shrinkage; "
                    "typical 0.5-1.0).",
                ],
            )
        if lambda3 <= 0:
            return make_error_response(
                ctx,
                f"lambda3 must be > 0. Got {lambda3}.",
                error_fixes=[
                    "Use a positive value (lag-decay parameter; "
                    "typical 1.0 harmonic, 2.0 quadratic).",
                ],
            )
        if p < 1:
            return make_error_response(
                ctx,
                f"lags must be >= 1. Got {p}.",
                error_fixes=[
                    "Use a positive integer; typical macro VAR "
                    "lag orders are 1-12 monthly / 1-4 quarterly.",
                ],
            )

        if T_full < p + 5:
            return make_error_response(
                ctx,
                f"Only {T_full} observations for {k} variables with {p} lags. "
                f"Need at least {p + 5}.",
                error_fixes=["Reduce lags or provide longer series."],
            )

        if k > 10:
            warnings.append(f"BVAR with {k} variables may be slow. Consider reducing the number of series.")

        progress_callback("Building VAR matrices", 15)

        # Build VAR matrices: Y = X @ B + E
        # Y: (T-p) x k
        # X: (T-p) x (k*p + const)
        T = T_full - p
        Y = Y_full[p:]  # (T, k)

        X_parts = []
        for lag in range(1, p + 1):
            X_parts.append(Y_full[p - lag: T_full - lag])
        if include_const:
            X_parts.append(np.ones((T, 1)))
        X = np.hstack(X_parts)  # (T, m) where m = k*p + const

        m = X.shape[1]

        progress_callback("Computing Minnesota prior", 25)

        # Estimate individual AR(1) residual variances for scaling
        sigma_i = np.zeros(k)
        for i in range(k):
            y_i = Y_full[:, i]
            if len(y_i) > 2:
                y_lag = y_i[:-1]
                y_fwd = y_i[1:]
                valid = ~(np.isnan(y_lag) | np.isnan(y_fwd))
                if valid.sum() > 2:
                    beta_ols = np.sum(y_lag[valid] * y_fwd[valid]) / np.sum(y_lag[valid] ** 2)
                    resid = y_fwd[valid] - beta_ols * y_lag[valid]
                    sigma_i[i] = np.var(resid, ddof=1)
                else:
                    sigma_i[i] = np.var(y_i, ddof=1)
            else:
                sigma_i[i] = np.var(y_i, ddof=1)
            sigma_i[i] = max(sigma_i[i], 1e-10)

        # Minnesota prior: B_prior is zero except diagonal = 1 for first own lag (random walk)
        B_prior = np.zeros((m, k))
        for i in range(k):
            B_prior[i, i] = 1.0  # first own lag of variable i -> coefficient 1

        # Prior precision for each coefficient
        V_prior_diag = np.zeros(m)
        for lag in range(1, p + 1):
            for j in range(k):
                idx = (lag - 1) * k + j
                for i in range(k):
                    if j == i:
                        # Own lag: variance = (lambda1 / lag^lambda3)^2
                        V_prior_diag[idx] = max((lambda1 / (lag ** lambda3)) ** 2, 1e-12)
                    else:
                        # Cross lag: variance = (lambda1 * lambda2 / lag^lambda3)^2 * (sigma_i[i] / sigma_i[j])
                        V_prior_diag[idx] = max(
                            (lambda1 * lambda2 / (lag ** lambda3)) ** 2 * (sigma_i[i] / sigma_i[j]),
                            1e-12,
                        )
        # For intercept: diffuse
        if include_const:
            V_prior_diag[-1] = 1e6

        # Note: V_prior_diag stores the variance for each row of B, but B is (m, k).
        # Minnesota prior: each equation estimated separately with same X but different prior.
        # For simplicity, use the Normal-diffuse approach equation by equation.

        progress_callback("Computing posterior", 40)

        # Posterior for each equation i: B_i | data ~ N(b_post_i, V_post_i)
        # b_post_i = V_post_i @ (V_prior_inv @ b_prior_i + X'y_i)
        # V_post_i = (V_prior_inv + X'X)^{-1}

        B_post = np.zeros((m, k))
        B_post_var = []  # store diagonals of posterior variance
        S_post = np.zeros((k, k))

        XtX = X.T @ X

        for i in range(k):
            # Prior for equation i
            v_prior = V_prior_diag.copy()
            # Adjust cross-variable scaling for equation i
            for lag in range(1, p + 1):
                for j in range(k):
                    idx = (lag - 1) * k + j
                    if j != i:
                        v_prior[idx] = max(
                            (lambda1 * lambda2 / (lag ** lambda3)) ** 2 * (sigma_i[i] / max(sigma_i[j], 1e-10)),
                            1e-12,
                        )

            V_prior_inv = np.diag(1.0 / v_prior)

            try:
                V_post_inv = V_prior_inv + XtX
                V_post = np.linalg.inv(V_post_inv)
            except np.linalg.LinAlgError:
                V_post = np.linalg.pinv(V_prior_inv + XtX)
                warnings.append(f"Near-singular posterior for variable '{names[i]}'; pseudo-inverse used.")

            b_prior_i = B_prior[:, i]
            Xty_i = X.T @ Y[:, i]
            b_post_i = V_post @ (V_prior_inv @ b_prior_i + Xty_i)

            B_post[:, i] = b_post_i
            B_post_var.append(np.diag(V_post))

            resid_i = Y[:, i] - X @ b_post_i
            S_post[i, i] = np.sum(resid_i ** 2) / T

        # Cross-equation residual covariance
        E_post = Y - X @ B_post
        Sigma_post = (E_post.T @ E_post) / T

        progress_callback("Generating forecasts", 55)

        # Point forecast (iterate forward)
        fc = np.zeros((horizon, k))
        last_obs = Y_full[-p:]  # (p, k)
        history = last_obs.copy()

        for h in range(horizon):
            x_h = []
            for lag in range(1, p + 1):
                if h - lag + 1 >= 0 and h - lag + 1 < len(fc):
                    if lag <= h:
                        x_h.append(fc[h - lag])
                    else:
                        x_h.append(history[p - (lag - h)])
                else:
                    x_h.append(history[p - (lag - h)])
            x_h = np.concatenate(x_h)
            if include_const:
                x_h = np.append(x_h, 1.0)
            fc[h] = x_h @ B_post

        progress_callback("Drawing posterior samples for intervals", 65)

        # Monte Carlo credible intervals
        fc_draws = np.zeros((n_draws, horizon, k))
        for d in range(n_draws):
            # Draw coefficients from posterior
            B_draw = np.zeros((m, k))
            for i in range(k):
                sd = np.sqrt(np.maximum(B_post_var[i], 1e-12))
                B_draw[:, i] = B_post[:, i] + sd * np.random.randn(m)

            # Simulate forecast path
            hist = history.copy()
            for h_idx in range(horizon):
                x_d = []
                for lag in range(1, p + 1):
                    if h_idx >= lag:
                        x_d.append(fc_draws[d, h_idx - lag])
                    else:
                        x_d.append(hist[p - (lag - h_idx)])
                x_d = np.concatenate(x_d)
                if include_const:
                    x_d = np.append(x_d, 1.0)
                mean_d = x_d @ B_draw
                # Add noise
                noise = np.random.multivariate_normal(np.zeros(k), Sigma_post)
                fc_draws[d, h_idx] = mean_d + noise

        fc_lower = np.percentile(fc_draws, 5, axis=0)
        fc_upper = np.percentile(fc_draws, 95, axis=0)

        # ── IRF / FEVD (Follow-up 1c) ──────────────────────────────────
        compute_irf_fevd = bool(ctx.get_param(
            "compute_irf_fevd", cfg.get("compute_irf_fevd", True)
        ))
        irf_horizon = int(ctx.get_param(
            "irf_horizon", cfg.get("irf_horizon", 24)
        ))
        irf_horizon = max(2, irf_horizon)
        irf_fevd_computed = False
        irf_results = None
        fevd_results = None
        fevd_horizons_used = []
        zero_straddle_pairs = []
        irf_skip_reason = None

        if compute_irf_fevd:
            progress_callback("Computing IRF / FEVD (posterior)", 72)
            try:
                irf_rng = np.random.default_rng(ctx.seed)
                irf_results = _compute_posterior_irf(
                    B_post, B_post_var, Sigma_post,
                    k=k, p=p, m=m, include_const=include_const,
                    n_draws=n_draws, H=irf_horizon, rng=irf_rng,
                )
                fevd_horizons_used = [
                    h for h in [1, 4, 8, 12, 24] if h <= irf_horizon
                ]
                fevd_results = _compute_posterior_fevd(
                    irf_results["tensor"], fevd_horizons_used,
                )
                zero_straddle_pairs = _collect_zero_straddle_pairs(
                    irf_results, names, k,
                )
                irf_fevd_computed = True
            except Exception as e:
                warnings.append(f"IRF/FEVD computation failed: {e}")
                irf_skip_reason = f"computation_error: {e}"
        else:
            if str(ctx.preset).lower() == "fast":
                irf_skip_reason = "fast_preset_default"
            else:
                irf_skip_reason = "user_disabled"

        progress_callback("Building output tables", 80)

        # ---- Forecast table (for each variable) ----
        tables = []
        for i in range(k):
            fc_rows = []
            for h in range(horizon):
                fc_rows.append([
                    h + 1,
                    round(float(fc[h, i]), 6),
                    round(float(fc_lower[h, i]), 6),
                    round(float(fc_upper[h, i]), 6),
                ])
            tables.append(make_table(
                f"Forecast: {names[i]}",
                ["Step", "Forecast", "Lower 90%", "Upper 90%"],
                fc_rows,
            ))

        # ---- Coefficient table ----
        coef_rows = []
        for i in range(k):
            for lag in range(1, p + 1):
                for j in range(k):
                    idx = (lag - 1) * k + j
                    sd = np.sqrt(max(B_post_var[i][idx], 1e-12))
                    z = B_post[idx, i] / sd if sd > 0 else 0.0
                    coef_rows.append([
                        names[i],
                        f"{names[j]}_lag{lag}",
                        round(float(B_post[idx, i]), 6),
                        round(float(sd), 6),
                        round(float(z), 4),
                    ])
            if include_const:
                idx = m - 1
                sd = np.sqrt(max(B_post_var[i][idx], 1e-12))
                coef_rows.append([
                    names[i], "const",
                    round(float(B_post[idx, i]), 6),
                    round(float(sd), 6),
                    round(float(B_post[idx, i] / sd if sd > 0 else 0.0), 4),
                ])
        coef_table = make_table(
            "Posterior Coefficients",
            ["Equation", "Regressor", "Post. Mean", "Post. Std", "z-Score"],
            coef_rows,
        )
        tables.append(coef_table)

        # ---- Residual covariance ----
        cov_rows = []
        for i in range(k):
            row = [names[i]] + [round(float(Sigma_post[i, j]), 6) for j in range(k)]
            cov_rows.append(row)
        cov_table = make_table(
            "Residual Covariance Matrix",
            [""] + names,
            cov_rows,
        )
        tables.append(cov_table)

        # ---- Model summary ----
        # Log marginal likelihood approximation (BIC-like)
        resid_flat = E_post.flatten()
        sse = float(np.sum(resid_flat ** 2))
        total_params = m * k
        bic_approx = T * np.log(sse / (T * k)) + total_params * np.log(T)

        fitted_all = X @ B_post
        rmse_vals = []
        for i in range(k):
            rmse_i = float(np.sqrt(np.mean((Y[:, i] - fitted_all[:, i]) ** 2)))
            rmse_vals.append(rmse_i)

        summary_rows = [
            ["Variables", ", ".join(names)],
            ["Number of Variables", k],
            ["Lags", p],
            ["Observations (effective)", T],
            ["Total Parameters", total_params],
            ["Prior Tightness (lambda1)", lambda1],
            ["Cross-Shrinkage (lambda2)", lambda2],
            ["Lag Decay (lambda3)", lambda3],
            ["BIC Approximation", round(float(bic_approx), 2)],
            ["Posterior Draws", n_draws],
            ["Forecast Horizon", horizon],
            ["IRF/FEVD Computed", irf_fevd_computed],
        ]
        if irf_fevd_computed:
            summary_rows.append(["Identification", "cholesky"])
            summary_rows.append(["Variable Ordering", ", ".join(names)])
            summary_rows.append(["IRF Horizon", irf_horizon])
            summary_rows.append(["FEVD Horizons", str(fevd_horizons_used)])
        else:
            summary_rows.append(["IRF/FEVD Skip Reason", str(irf_skip_reason)])
        for i in range(k):
            summary_rows.append([f"RMSE ({names[i]})", round(rmse_vals[i], 4)])
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)
        tables.append(summary_table)

        # ---- IRF and FEVD tables when computed ----
        if irf_fevd_computed:
            irf_rows = []
            for h in range(irf_horizon):
                for resp_idx in range(k):
                    for shock_idx in range(k):
                        irf_rows.append([
                            h,
                            names[shock_idx],
                            names[resp_idx],
                            round(float(irf_results["median"][h, resp_idx, shock_idx]), 6),
                            round(float(irf_results["lower_5"][h, resp_idx, shock_idx]), 6),
                            round(float(irf_results["upper_95"][h, resp_idx, shock_idx]), 6),
                        ])
            irf_table = make_table(
                "Impulse Response (Posterior Median, 90% Credible Band)",
                ["Period", "Shock", "Response", "Median", "Lower 5%", "Upper 95%"],
                irf_rows,
            )
            tables.append(irf_table)

            fevd_rows = []
            for h in fevd_horizons_used:
                med_h = fevd_results["median"][h]
                lo_h = fevd_results["lower_5"][h]
                hi_h = fevd_results["upper_95"][h]
                for resp_idx in range(k):
                    for shock_idx in range(k):
                        fevd_rows.append([
                            h,
                            names[resp_idx],
                            names[shock_idx],
                            round(float(med_h[resp_idx, shock_idx]), 6),
                            round(float(lo_h[resp_idx, shock_idx]), 6),
                            round(float(hi_h[resp_idx, shock_idx]), 6),
                        ])
            fevd_table = make_table(
                "FEVD (Posterior)",
                ["Horizon", "Variable", "Shock", "Median Share", "Lower 5%", "Upper 95%"],
                fevd_rows,
            )
            tables.append(fevd_table)

        # ---- Plain English ----
        rmse_str = ", ".join([f"{names[i]}={rmse_vals[i]:.4f}" for i in range(k)])
        plain = (
            f"Bayesian VAR({p}) with Minnesota prior fitted to {k} variables "
            f"({', '.join(names)}), {T} effective observations. "
            f"Prior tightness lambda1={lambda1}, cross-shrinkage lambda2={lambda2}. "
            f"RMSE: {rmse_str}. "
            f"{horizon}-step forecasts with 90% credible intervals from {n_draws} posterior draws."
        )

        charting = (
            "Multi-panel line chart: one panel per variable showing original series, "
            "fitted values, and forecast continuation with shaded 90% credible intervals. "
            "Optionally show impulse response functions in a grid layout."
        )

        progress_callback("Done", 100)

        # Prompt C5: prior-tightness adjective band (D12) and credible-
        # interval-semantic label (D2).
        def _prior_tightness_band(lam):
            if lam is None:
                return "unknown"
            v = float(lam)
            if v < 0.1: return "tight"
            if v < 0.3: return "moderate"
            return "loose"
        prior_tightness_band = _prior_tightness_band(lambda1)

        # Follow-up 1c — IRF/FEVD audit fields + scalar summaries.
        own_shock_share_longest = {}
        fevd_longest_h = None
        if irf_fevd_computed and fevd_horizons_used:
            fevd_longest_h = max(fevd_horizons_used)
            diag = np.diag(fevd_results["median"][fevd_longest_h])
            for i in range(k):
                own_shock_share_longest[names[i]] = round(float(diag[i]), 4)

        audit = {
            "variables": names,
            "n_variables": k,
            "lags": p,
            "lambda1": lambda1,
            "lambda2": lambda2,
            "lambda3": lambda3,
            "n_effective": T,
            "total_params": total_params,
            "bic_approx": round(float(bic_approx), 2),
            "n_draws": n_draws,
            "rmse": {names[i]: round(rmse_vals[i], 4) for i in range(k)},
            "horizon": horizon,
            "prior_tightness_band": prior_tightness_band,
            "interval_type": "credible",
            "credible_interval_coverage": 0.90,
            # Follow-up 1c IRF/FEVD fields
            "irf_fevd_computed": irf_fevd_computed,
            "identification_scheme": "cholesky" if irf_fevd_computed else None,
            "variable_ordering": list(names) if irf_fevd_computed else None,
            "irf_horizon": irf_horizon if irf_fevd_computed else None,
            "fevd_horizons": list(fevd_horizons_used) if irf_fevd_computed else [],
            "own_shock_share_longest_horizon": own_shock_share_longest,
            "fevd_longest_horizon": fevd_longest_h,
            "zero_straddle_pairs": zero_straddle_pairs,
            "irf_skip_reason": irf_skip_reason,
            # R1 — Σ point-estimate disclosure flag (honest disclosure
            # that posterior covariance is held at point estimate; VAR
            # coefficient uncertainty propagates but Σ uncertainty
            # does not).
            "sigma_posterior_uncertainty_propagated": False,
        }

        # Prompt C5 + Follow-up 1c interpretation layer wire-in.
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        interp = build_interpretation("bvar", dict(audit))

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
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
            f"Bayesian VAR failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Reduce the number of lags if the series is short.",
                "Increase lambda1 for stronger shrinkage if estimation is unstable.",
                "Check for constant or near-constant series.",
            ],
        )
