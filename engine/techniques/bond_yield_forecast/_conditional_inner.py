"""Numba-JIT'd inner loop for BGL-2015 conditional forecasting.

The hot path is the per-(draw, path, t) Gaussian conditioning step:
build mu_y / Sigma_y, partition into target/macro blocks, compute
the conditional Gaussian moments, sample via Cholesky, evolve h.
Python overhead dominates this small dense-matrix sequence; numba
JIT pushes the production-default forecast (1000 draws × 50 paths
× 8 horizons × 6 vars) from ~3 minutes to ~30 seconds.

Pre-generated standard normals are passed in from the outer Python
loop, so seed reproducibility is owned by the caller's
np.random.Generator and independent of numba's RNG state.

A trivial JIT compile is run at module import to fail fast if numba
is broken — same pattern as src/bvar/_ffbs.py.

Sampling uses Cholesky-based MVN sampling (sample = mean + L @ z
with L = cholesky(cov + 1e-12 * I)). NumPy's default
Generator.multivariate_normal uses SVD-based sampling instead, so
per-path values differ from the pre-numba implementation at the
floating-point level. Posterior medians agree statistically within
MC noise (well below desk-grade tolerances). The Cholesky basis is
the standard, faster choice for theoretically-PSD covariances like
our Schur complements.
"""

from __future__ import annotations

import numpy as np

try:
    from numba import jit
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "numba is required for conditional forecasting; "
        "install with `pip install numba>=0.58`."
    ) from exc


@jit(nopython=True, cache=True)
def _jit_smoke(x: float) -> float:
    return x + 1.0


try:
    _jit_smoke(0.0)
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "Numba JIT failed; conditional forecaster cannot run. "
        "Install numba >=0.58 via `pip install numba`."
    ) from exc


@jit(nopython=True, cache=True)
def conditional_forecast_inner_loop(
    B: np.ndarray,
    A_inv: np.ndarray,
    h_T: np.ndarray,
    omega: np.ndarray,
    phi: np.ndarray,
    mu: np.ndarray,
    state_init: np.ndarray,
    projection: np.ndarray,
    target_idx: np.ndarray,
    macro_idx: np.ndarray,
    strict: bool,
    R_diag: np.ndarray,
    rng_z_target: np.ndarray,
    rng_z_macro: np.ndarray,
    rng_z_h: np.ndarray,
):
    """Run n_paths conditional-Gaussian simulations for one posterior draw.

    Parameters
    ----------
    B            : (n_vars, n_kp1) — VAR coefficient matrix for this draw.
    A_inv        : (n_vars, n_vars) — inverse of the lower-triangular A.
    h_T          : (n_vars,) — terminal in-sample log-volatility.
    omega        : (n_vars,) — log-vol AR(1) innovation std.
    phi          : (n_vars,) — log-vol AR(1) persistence.
    mu           : (n_vars,) — unconditional log-vol mean.
    state_init   : (n_lags, n_vars) — most-recent in-sample observations.
    projection   : (horizon, n_macro) — economist projection of macros.
    target_idx   : (n_target,) int64 — column indices of target variables.
    macro_idx    : (n_macro,)  int64 — column indices of conditioned vars.
    strict       : bool — strict-match (True) or soft-match (False).
    R_diag       : (n_macro,) — used only when strict=False; ignored otherwise.
    rng_z_target : (n_paths, horizon, n_target) — pre-drawn standard normals.
    rng_z_macro  : (n_paths, horizon, n_macro)  — pre-drawn (used in soft mode).
    rng_z_h      : (n_paths, horizon, n_vars)   — pre-drawn (h evolution).

    Returns
    -------
    target_paths : (n_paths, horizon, n_target).
    macro_paths  : (n_paths, horizon, n_macro).
    """
    n_vars = B.shape[0]
    n_kp1 = B.shape[1]
    n_t = target_idx.shape[0]
    n_m = macro_idx.shape[0]
    n_lags = state_init.shape[0]
    n_paths = rng_z_target.shape[0]
    horizon = rng_z_target.shape[1]

    target_paths = np.empty((n_paths, horizon, n_t))
    macro_paths = np.empty((n_paths, horizon, n_m))

    eye_t = np.eye(n_t)
    eye_joint = np.eye(n_t + n_m)
    ridge = 1e-12

    for path in range(n_paths):
        # State + h initialized fresh per path (each path is a forward
        # simulation from the in-sample seed).
        state = state_init.copy()
        h = h_T.copy()

        for t in range(horizon):
            # 1. x = [1, state[T-1], state[T-2], ..., state[T-n_lags]] flat,
            #    most-recent first to match _build_lag_design's column layout.
            x = np.empty(n_kp1)
            x[0] = 1.0
            offset = 1
            for l in range(n_lags):
                row = state[n_lags - 1 - l]
                for j in range(n_vars):
                    x[offset + j] = row[j]
                offset += n_vars

            # 2. mu_y = B @ x.
            mu_y = B @ x

            # 3. Sigma_y = A_inv @ diag(exp(h)) @ A_inv.T.
            #    Computed as (A_inv * exp(h)[None, :]) @ A_inv.T —
            #    elementwise scale of columns then matmul.
            scaled = np.empty((n_vars, n_vars))
            for i in range(n_vars):
                D_j = 0.0  # placeholder; computed inside loop
                for j in range(n_vars):
                    scaled[i, j] = A_inv[i, j] * np.exp(h[j])
            Sigma_y = scaled @ A_inv.T

            # 4. Partition Sigma_y into S_tt, S_tm, S_mm via target_idx/macro_idx.
            S_tt = np.empty((n_t, n_t))
            S_tm = np.empty((n_t, n_m))
            S_mm = np.empty((n_m, n_m))
            mu_t = np.empty(n_t)
            mu_m = np.empty(n_m)
            for i in range(n_t):
                mu_t[i] = mu_y[target_idx[i]]
                for j in range(n_t):
                    S_tt[i, j] = Sigma_y[target_idx[i], target_idx[j]]
                for j in range(n_m):
                    S_tm[i, j] = Sigma_y[target_idx[i], macro_idx[j]]
            for i in range(n_m):
                mu_m[i] = mu_y[macro_idx[i]]
                for j in range(n_m):
                    S_mm[i, j] = Sigma_y[macro_idx[i], macro_idx[j]]

            proj_t = projection[t]

            if strict:
                # Strict match: macro_t = projection_t exactly.
                resid = np.linalg.solve(S_mm, proj_t - mu_m)
                cond_mean_t = mu_t + S_tm @ resid
                K = np.linalg.solve(S_mm, S_tm.T)  # (n_m, n_t)
                cond_cov_t = S_tt - S_tm @ K

                L = np.linalg.cholesky(cond_cov_t + ridge * eye_t)
                target_t = cond_mean_t + L @ rng_z_target[path, t]
                macro_t = proj_t.copy()
            else:
                # Soft match: projection_t = macro_t + eta, eta ~ N(0, diag(R_diag)).
                S_pp = S_mm.copy()
                for i in range(n_m):
                    S_pp[i, i] = S_pp[i, i] + R_diag[i]

                resid = np.linalg.solve(S_pp, proj_t - mu_m)
                cond_mean_t = mu_t + S_tm @ resid
                cond_mean_m = mu_m + S_mm @ resid

                K_pp = np.linalg.solve(S_pp, S_tm.T)
                cond_cov_t = S_tt - S_tm @ K_pp
                K_pm = np.linalg.solve(S_pp, S_mm)
                cond_cov_m = S_mm - S_mm @ K_pm
                cond_cov_tm = S_tm - S_tm @ K_pm

                # Joint (target, macro) mean + covariance.
                joint_cov = np.empty((n_t + n_m, n_t + n_m))
                for i in range(n_t):
                    for j in range(n_t):
                        joint_cov[i, j] = cond_cov_t[i, j]
                    for j in range(n_m):
                        joint_cov[i, n_t + j] = cond_cov_tm[i, j]
                for i in range(n_m):
                    for j in range(n_t):
                        joint_cov[n_t + i, j] = cond_cov_tm[j, i]
                    for j in range(n_m):
                        joint_cov[n_t + i, n_t + j] = cond_cov_m[i, j]

                joint_mean = np.empty(n_t + n_m)
                for i in range(n_t):
                    joint_mean[i] = cond_mean_t[i]
                for i in range(n_m):
                    joint_mean[n_t + i] = cond_mean_m[i]

                # Concatenate target + macro pre-drawn standard normals
                # in target-first, macro-second order.
                z_joint = np.empty(n_t + n_m)
                for i in range(n_t):
                    z_joint[i] = rng_z_target[path, t, i]
                for i in range(n_m):
                    z_joint[n_t + i] = rng_z_macro[path, t, i]

                Lj = np.linalg.cholesky(joint_cov + ridge * eye_joint)
                sample = joint_mean + Lj @ z_joint
                target_t = sample[:n_t]
                macro_t = sample[n_t:]

            # 5. Store path values.
            for i in range(n_t):
                target_paths[path, t, i] = target_t[i]
            for i in range(n_m):
                macro_paths[path, t, i] = macro_t[i]

            # 6. Reassemble y_t and roll the state.
            y_t = np.empty(n_vars)
            for i in range(n_t):
                y_t[target_idx[i]] = target_t[i]
            for i in range(n_m):
                y_t[macro_idx[i]] = macro_t[i]
            for l in range(n_lags - 1):
                state[l] = state[l + 1]
            state[n_lags - 1] = y_t

            # 7. Evolve volatility (timing matches
            #    posterior_predictive_unconditional in estimation.py).
            for i in range(n_vars):
                h[i] = (
                    phi[i] * h[i]
                    + (1.0 - phi[i]) * mu[i]
                    + omega[i] * rng_z_h[path, t, i]
                )

    return target_paths, macro_paths
