"""Phase 4 Pattern A audit cluster — shared helpers.

Phase 4 Session 4 (2026-05-01). Introduced as scaffold for the
Pattern A audit cluster (S4 #2 Minnesota dummy-obs A.3, S5 #1 R
``BVAR`` constant-vol A.2, S6 #3 stochvol partial A.2). These
audits share a small set of common utilities — mostly synthetic
fixture generation and Pattern-A-tolerance comparison helpers
that don't fit cleanly into the more general
``harness/compare.py`` or per-wrapper-helper modules.

The helpers here are deliberately narrow:

  - ``synthesize_bvar_panel``: VAR(p) panel generator with a
    user-specified coefficient matrix and innovation covariance.
    Used by S5 + S6 (S4 doesn't need synthetic data because the
    Minnesota dummy-observation construction operates on
    configuration alone, not panel values).
  - ``synthesize_minnesota_config``: build a full set of
    consistent Minnesota-prior hyperparameters + sigma + y_bar
    for a Pattern A.3 dummy-construction audit. Used by S4.
  - ``compare_array_pair``: Pattern A array comparison wrapper
    around ``_compare_vector`` that handles 2D arrays via
    flattening. Used across S4/S5/S6.

Design discipline (per S4 trigger): helpers accept fixture /
tolerance / comparison parameters via injection, not hard-coded
for any specific audit. S5 and S6 depend on generalizable
scaffold quality.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Synthetic fixture generators
# ---------------------------------------------------------------------------


def synthesize_bvar_panel(
    *,
    seed: int,
    n_vars: int = 3,
    n_lags: int = 2,
    T: int = 200,
    A_blocks: list[np.ndarray] | None = None,
    sigma_innov: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """Generate a synthetic stationary VAR(p) panel.

    Parameters
    ----------
    seed
        Numpy generator seed; deterministic given seed.
    n_vars, n_lags, T
        Panel shape: T observations of n_vars variables; VAR(n_lags)
        DGP. Must satisfy T > n_vars * n_lags + 1 for the panel to
        be useful for downstream estimation.
    A_blocks
        List of length n_lags; each element is an (n_vars, n_vars)
        coefficient matrix. The aggregate companion-form must have
        spectral radius < 1 for the DGP to be stationary. If None,
        defaults to a diagonal block per lag with spectral radius
        1 - 0.05*l (mild persistence; spectral-radius-safe).
    sigma_innov
        Innovation covariance (n_vars, n_vars). If None, defaults
        to identity.

    Returns
    -------
    dict
        ``"y"``  : (T, n_vars) panel.
        ``"A_blocks"`` : list of length n_lags, the (n_vars, n_vars)
                        coefficient matrices used.
        ``"sigma_innov"`` : (n_vars, n_vars) innovation covariance.
        ``"seed"`` : int echo.
    """
    rng = np.random.default_rng(seed)

    if A_blocks is None:
        A_blocks = [
            np.diag(np.full(n_vars, max(0.0, 1.0 - 0.05 * (l + 1))))
            for l in range(n_lags)
        ]
    if sigma_innov is None:
        sigma_innov = np.eye(n_vars)

    chol = np.linalg.cholesky(sigma_innov)
    burn_in = max(50, n_lags * 10)
    total_T = T + burn_in
    y = np.zeros((total_T, n_vars))
    # Burn-in initialization at zero; rely on stationarity to wash out
    for t in range(n_lags, total_T):
        eps = chol @ rng.standard_normal(n_vars)
        y[t] = eps.copy()
        for l in range(n_lags):
            y[t] += A_blocks[l] @ y[t - 1 - l]
    return {
        "y": y[burn_in:],
        "A_blocks": [a.copy() for a in A_blocks],
        "sigma_innov": sigma_innov.copy(),
        "seed": int(seed),
    }


def synthesize_minnesota_config(
    *,
    n_vars: int = 3,
    n_lags: int = 2,
    seed: int = 42,
) -> dict[str, Any]:
    """Build a complete, consistent Minnesota-prior hyperparameter
    configuration suitable for a Pattern A.3 dummy-observation
    construction audit.

    Returns
    -------
    dict
        ``"n_vars"`` : int
        ``"n_lags"`` : int
        ``"sigma"``  : (n_vars,) per-variable AR-1 residual std (synthetic)
        ``"y_bar"``  : (n_vars,) per-variable mean (synthetic)
        ``"persistence"`` : (n_vars,) per-variable persistence prior
                            (1.0 for level series, 0.0 for stationary)
        ``"lambda_1"`` : 0.2 (overall tightness)
        ``"lambda_2"`` : 0.5 (cross-equation tightness; informational)
        ``"lambda_3"`` : 1.0 (lag-decay rate)
        ``"lambda_4"`` : 1e5 (intercept-prior-tightness; matches
                            TSL's MinnesotaPrior default for a
                            diffuse intercept prior)
        ``"lambda_sc"`` : 1.0 (sum-of-coefficients weight)
        ``"lambda_io"`` : 1.0 (initial-observation weight)

    The configuration is chosen to exercise all 5 dummy blocks:
    A (coefficients), B (covariance), C (intercept), D (sum-of-
    coefs), E (initial-obs). lambda_4 is finite (so block C
    contributes); lambda_sc and lambda_io are non-zero (so blocks
    D and E contribute).
    """
    rng = np.random.default_rng(seed)
    sigma = 0.5 + rng.uniform(0.0, 1.0, size=n_vars)
    y_bar = rng.standard_normal(n_vars)
    persistence = np.ones(n_vars)  # level-series prior
    return {
        "n_vars": int(n_vars),
        "n_lags": int(n_lags),
        "sigma": sigma,
        "y_bar": y_bar,
        "persistence": persistence,
        "lambda_1": 0.2,
        "lambda_2": 0.5,
        "lambda_3": 1.0,
        "lambda_4": 1e5,
        "lambda_sc": 1.0,
        "lambda_io": 1.0,
    }


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------


def compare_array_pair(
    tsl: np.ndarray,
    ref: np.ndarray,
    *,
    abs_tol: float,
    rel_tol: float,
    name: str = "array",
) -> dict[str, Any]:
    """Element-wise compare two arrays (any shape) at Pattern A
    tolerance bands. Returns a status dict matching the
    ``_compare_vector`` shape so callers can drop it directly into
    the standard ``ParityResult.metrics`` dict.

    PASS: max_abs_diff <= abs_tol AND max_rel_diff <= rel_tol.
    CAVEAT: max_abs_diff <= 10*abs_tol AND max_rel_diff <= 10*rel_tol.
    BLOCK: otherwise.

    Both arrays must have identical shape. Caller is responsible
    for shape-compatibility before invoking.
    """
    tsl_arr = np.asarray(tsl, dtype=np.float64)
    ref_arr = np.asarray(ref, dtype=np.float64)
    if tsl_arr.shape != ref_arr.shape:
        return {
            "status": "BLOCK",
            "max_abs_diff": float("nan"),
            "max_rel_diff": float("nan"),
            "n_compared": 0,
            "shape_tsl": list(tsl_arr.shape),
            "shape_ref": list(ref_arr.shape),
            "error": (
                f"shape mismatch on {name}: tsl={tsl_arr.shape} "
                f"ref={ref_arr.shape}"
            ),
        }
    diff = tsl_arr - ref_arr
    abs_diff = np.abs(diff)
    max_abs = float(abs_diff.max()) if abs_diff.size > 0 else 0.0
    # Avoid division-by-zero for zero reference values; rel_diff
    # set to 0 where ref is 0 AND tsl is 0 (perfect match);
    # otherwise rel_diff = abs_diff / |ref| (or |tsl| as fallback
    # to avoid nan when both arrays have zero entries).
    denom = np.maximum(np.abs(ref_arr), np.abs(tsl_arr))
    safe_denom = np.where(denom > 0, denom, 1.0)
    rel_arr = np.where(denom > 0, abs_diff / safe_denom, 0.0)
    max_rel = float(rel_arr.max()) if rel_arr.size > 0 else 0.0

    if max_abs <= abs_tol and max_rel <= rel_tol:
        status = "PASS"
    elif max_abs <= 10 * abs_tol and max_rel <= 10 * rel_tol:
        status = "CAVEAT"
    else:
        status = "BLOCK"

    return {
        "status": status,
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "n_compared": int(abs_diff.size),
        "shape": list(tsl_arr.shape),
    }
