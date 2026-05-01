"""Tests for src/bvar/hyperparameters.py — Step 3.

Five fast tests cover end-to-end behavior. One slow-marked test
cross-checks the closed-form marginal likelihood against a Monte Carlo
integral over the IW prior on Sigma (B integrated out analytically).
The slow test runs once at implementation time and on any future change
to the formula.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.hyperparameters import HyperparameterOptimizer, _log_marginal_likelihood_niw
from techniques.bond_yield_forecast.priors import MinnesotaPrior
from techniques.bond_yield_forecast.validation import _build_lag_design_xy


def _toy_panel(seed: int = 0, T: int = 80, n: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    Y = np.zeros((T, n))
    Y[0] = rng.standard_normal(n)
    for t in range(1, T):
        Y[t] = 0.5 * Y[t - 1] + rng.standard_normal(n) * 0.5
    idx = pd.period_range("1990-Q1", periods=T, freq="Q-DEC")
    return pd.DataFrame(Y, index=idx, columns=[f"v{i}" for i in range(n)])


def test_marginal_likelihood_is_finite_at_default_lambdas():
    """log-MDD evaluates to a finite scalar at sensible defaults."""
    panel = _toy_panel(seed=1)
    opt = HyperparameterOptimizer(panel, n_lags=1, seed=42)
    log_mdd = opt.log_marginal_likelihood(
        lambda_1=0.2, lambda_2=1.0, lambda_3=1.0, lambda_sc=1.0, lambda_io=1.0,
    )
    assert np.isfinite(log_mdd)
    assert isinstance(log_mdd, float)


def test_grid_finds_argmax():
    """Tiny 4-D grid; verify glp_grid's best matches a brute-force argmax."""
    panel = _toy_panel(seed=2)
    opt = HyperparameterOptimizer(panel, n_lags=1, seed=42)
    L1 = np.array([0.1, 0.3])
    L3 = np.array([0.5, 1.5])
    Lsc = np.array([0.0, 1.0])
    Lio = np.array([0.0, 1.0])

    result = opt.glp_grid(L1, L3, Lsc, Lio)

    best_brute = -np.inf
    best_tuple = None
    for l1 in L1:
        for l3 in L3:
            for lsc in Lsc:
                for lio in Lio:
                    v = opt.log_marginal_likelihood(
                        lambda_1=float(l1), lambda_3=float(l3),
                        lambda_sc=float(lsc), lambda_io=float(lio),
                    )
                    if v > best_brute:
                        best_brute = v
                        best_tuple = (float(l1), float(l3), float(lsc), float(lio))

    assert result["best_log_marginal_likelihood"] == pytest.approx(best_brute, rel=1e-10)
    bl = result["best_lambdas"]
    assert (bl["lambda_1"], bl["lambda_3"], bl["lambda_sc"], bl["lambda_io"]) == best_tuple
    assert result["n_evaluations"] == 16
    assert result["n_finite"] == 16


def test_numerical_does_not_regress_on_grid():
    """L-BFGS-B from grid argmax must not return a worse log-MDD."""
    panel = _toy_panel(seed=3)
    opt = HyperparameterOptimizer(panel, n_lags=1, seed=42)
    L1 = np.array([0.1, 0.2, 0.3])
    L3 = np.array([0.5, 1.0])
    Lsc = np.array([1.0])
    Lio = np.array([1.0])

    grid = opt.glp_grid(L1, L3, Lsc, Lio)
    bounds = {
        "lambda_1": (0.01, 1.0), "lambda_3": (0.1, 4.0),
        "lambda_sc": (0.0, 10.0), "lambda_io": (0.0, 10.0),
    }
    num = opt.glp_numerical(starting_point=grid["best_lambdas"], bounds=bounds)
    # Guard against L-BFGS-B saddle/at-bound regressions (rare on toy data).
    assert num["best_log_marginal_likelihood"] >= grid["best_log_marginal_likelihood"] - 1e-6


def test_optimize_seed_reproducible():
    """Same seed + panel + config → bitwise-identical recommended lambdas."""
    panel = _toy_panel(seed=4)
    cfg = {
        "method": "glp_composite",
        "fixed": {"lambda_1": 0.2, "lambda_2": 1.0, "lambda_3": 1.0,
                  "lambda_sc": 1.0, "lambda_io": 1.0},
        "glp_grid": {
            "lambda_1": [0.1, 0.2], "lambda_3": [1.0],
            "lambda_sc": [1.0], "lambda_io": [1.0],
        },
        "glp_numerical": {
            "bounds": {
                "lambda_1": [0.01, 1.0], "lambda_3": [0.1, 4.0],
                "lambda_sc": [0.0, 10.0], "lambda_io": [0.0, 10.0],
            },
            "options": {"eps": 0.001, "maxiter": 50, "ftol": 1.0e-7},
        },
    }
    a = HyperparameterOptimizer(panel, n_lags=1, seed=11).optimize(cfg)
    b = HyperparameterOptimizer(panel, n_lags=1, seed=11).optimize(cfg)
    assert a["recommended"] == b["recommended"]


def test_optimize_method_fixed_short_circuits():
    """method=='fixed' returns the fixed lambdas verbatim; no grid/numerical."""
    panel = _toy_panel(seed=5)
    cfg = {
        "method": "fixed",
        "fixed": {"lambda_1": 0.2, "lambda_2": 0.5, "lambda_3": 1.0,
                  "lambda_sc": 1.0, "lambda_io": 1.0},
    }
    out = HyperparameterOptimizer(panel, n_lags=1).optimize(cfg)
    assert out["method"] == "fixed"
    assert out["recommended"]["lambda_1"] == 0.2
    assert out["recommended"]["lambda_3"] == 1.0
    assert "grid" not in out
    assert "numerical" not in out
    assert out["warnings_hard"] == []


def test_at_bound_warning_fires_when_optimum_at_bound():
    """Refinement 3: lambda within 1% of bound triggers HARD warning."""
    panel = _toy_panel(seed=6)
    cfg = {
        "method": "glp_composite",
        "fixed": {"lambda_1": 0.2, "lambda_2": 1.0, "lambda_3": 1.0,
                  "lambda_sc": 1.0, "lambda_io": 1.0},
        "glp_grid": {
            "lambda_1": [0.1], "lambda_3": [1.0],
            "lambda_sc": [1.0], "lambda_io": [0.0],
        },
        # Deliberately tight bounds so optimizer hits at least one of them.
        "glp_numerical": {
            "bounds": {
                "lambda_1": [0.099, 0.101], "lambda_3": [0.99, 1.01],
                "lambda_sc": [0.99, 1.01], "lambda_io": [0.0, 0.001],
            },
            "options": {"eps": 0.0001, "maxiter": 30, "ftol": 1.0e-7},
        },
    }
    out = HyperparameterOptimizer(panel, n_lags=1, seed=0).optimize(cfg)
    # At least one warning should fire — multiple bounds are tight.
    assert isinstance(out["warnings_hard"], list)
    assert len(out["warnings_hard"]) >= 1
    assert all(w.startswith("WARNING:") for w in out["warnings_hard"])


@pytest.mark.slow
def test_log_marginal_likelihood_matches_numerical_integration():
    """Cross-check closed-form log p(Y) against Monte Carlo over the IW prior.

    Setup: tiny n=2, T=20, p=1, lambda_sc=0, lambda_io=0 (so dummies
    consist of just the n*p coefficient and n covariance blocks plus the
    diffuse intercept; no SoC/IO blocks). Closed-form MDD must agree
    with Monte Carlo to within ~0.1 (MC SE at 20000 draws).

    Reference: BGR-2010 Appendix A; Karlsson 2013 Section 3.

    Algorithm
    ---------
    1. Build the dummy block (Y_d, X_d) at the same lambdas the closed
       form is being verified at.
    2. Closed-form: ``_log_marginal_likelihood_niw(Y, X, Y_d, X_d)``.
    3. Monte Carlo (Sigma-marginalized over the IW prior, B integrated
       analytically):

           Sigma_m ~ IW(S_0, nu_0),      m = 1..M
           log p(Y | Sigma_m) = -(nT/2) log(2*pi)
                                - (n/2) log|M_mat|
                                - (T/2) log|Sigma_m|
                                - 0.5 * tr(Sigma_m^-1 R' M_mat^-1 R)

       where M_mat = I_T + X Omega_0 X', R = Y - X B_0, and
       B_0, Omega_0, S_0, nu_0 are the dummy-implied prior moments.

           log p(Y) ≈ logsumexp({log p(Y|Sigma_m)}) - log M

    This Monte Carlo estimator is exactly the closed-form integrand, so
    they must agree up to sampling noise.
    """
    rng = np.random.default_rng(20260428)
    n, T_full, p = 2, 22, 1

    # Generate test data — independent normals; no real persistence.
    data = rng.standard_normal((T_full, n)) * 0.4
    panel = pd.DataFrame(
        data,
        index=pd.period_range("1990-Q1", periods=T_full, freq="Q-DEC"),
        columns=[f"v{i}" for i in range(n)],
    )

    # Build the design from the post-lag panel (Y has T = T_full - p rows).
    Y, X = _build_lag_design_xy(data, n_lags=p)

    # Build the dummy prior at the verification lambdas (no SoC/IO).
    prior = MinnesotaPrior(
        n_vars=n, n_lags=p,
        lambda_1=0.5, lambda_2=1.0, lambda_3=1.0,
        lambda_sc=0.0, lambda_io=0.0,
        training_data=panel,
        persistence_prior=[0.0, 0.0],
        variable_names=list(panel.columns),
    )
    Y_d, X_d = prior.dummy_observations()

    # Closed form.
    log_mdd_closed = _log_marginal_likelihood_niw(Y, X, Y_d, X_d)
    assert np.isfinite(log_mdd_closed)

    # Prior NIW moments (dummy-implied).
    XtX_d = X_d.T @ X_d
    Omega_0 = np.linalg.inv(XtX_d)
    B_0 = Omega_0 @ (X_d.T @ Y_d)
    R_d = Y_d - X_d @ B_0
    S_0 = R_d.T @ R_d
    n_d, k = X_d.shape
    nu_0 = n_d - k
    assert nu_0 > n - 1, "Prior dof too low for verification."

    T = Y.shape[0]
    M_mat = np.eye(T) + X @ Omega_0 @ X.T  # (T, T)
    sign_M, logdet_M = np.linalg.slogdet(M_mat)
    assert sign_M > 0
    M_inv = np.linalg.inv(M_mat)

    R = Y - X @ B_0  # (T, n)
    R_quad = R.T @ M_inv @ R  # (n, n)

    # Sample Sigma ~ IW(S_0, nu_0). scipy.stats.invwishart works on
    # (df=nu, scale=S) where the IW pdf is proportional to
    # |Sigma|^(-(nu+n+1)/2) exp(-tr(S Sigma^-1)/2). This matches our
    # convention.
    from scipy.stats import invwishart
    M_samples = 20000
    sigmas = invwishart.rvs(df=nu_0, scale=S_0, size=M_samples, random_state=rng)
    if sigmas.ndim == 2:
        sigmas = sigmas[None, ...]  # promote shape (n,n) to (1,n,n)

    log_const = -(n * T / 2.0) * np.log(2.0 * np.pi) - (n / 2.0) * logdet_M

    log_pY_given_sigma = np.empty(M_samples)
    for m in range(M_samples):
        Sigma_m = sigmas[m]
        sign_S, logdet_S = np.linalg.slogdet(Sigma_m)
        Sigma_inv = np.linalg.inv(Sigma_m)
        log_pY_given_sigma[m] = (
            log_const
            - (T / 2.0) * logdet_S
            - 0.5 * np.trace(Sigma_inv @ R_quad)
        )

    # log p(Y) ≈ logsumexp(log p(Y|Sigma_m)) - log M.
    from scipy.special import logsumexp
    log_mdd_mc = logsumexp(log_pY_given_sigma) - np.log(M_samples)

    # MC standard error: empirical std of log p(Y|Sigma_m) / sqrt(M),
    # but logsumexp's SE is closer to std/(sqrt(M) * exp(mean - max)).
    # Conservative tolerance: 0.2 absolute (well above MC noise at M=20000).
    diff = abs(log_mdd_closed - log_mdd_mc)
    assert diff < 0.2, (
        f"Closed-form vs Monte Carlo log-MDD disagree: "
        f"closed={log_mdd_closed:.6f}, mc={log_mdd_mc:.6f}, |diff|={diff:.6f}"
    )
