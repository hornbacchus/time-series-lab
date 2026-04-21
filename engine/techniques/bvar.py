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
    "Fast": {"max_lags": 2, "n_draws": 500, "lambda1": 0.1, "lambda2": 0.5},
    "Balanced": {"max_lags": 4, "n_draws": 1000, "lambda1": 0.1, "lambda2": 1.0},
    "Thorough": {"max_lags": 6, "n_draws": 5000, "lambda1": 0.1, "lambda2": 1.0},
}


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
        ]
        for i in range(k):
            summary_rows.append([f"RMSE ({names[i]})", round(rmse_vals[i], 4)])
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)
        tables.append(summary_table)

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
        }

        # Prompt C5 interpretation layer wire-in.
        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        interp = build_interpretation("bvar", {
            "variables": names,
            "n_variables": int(k),
            "lags": int(p),
            "n_effective": int(T),
            "lambda1": float(lambda1),
            "lambda2": float(lambda2),
            "lambda3": float(lambda3),
            "prior_tightness_band": prior_tightness_band,
            "n_draws": int(n_draws),
            "total_params": int(total_params),
            "bic_approx": float(bic_approx),
            "rmse": {names[i]: float(rmse_vals[i]) for i in range(k)},
            "horizon": int(horizon),
            "credible_interval_coverage": 0.90,
        })

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
