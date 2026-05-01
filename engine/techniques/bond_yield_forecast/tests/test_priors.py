"""Tests for the Minnesota prior — moments, dummy form, and metadata."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.priors import MinnesotaPrior


def _toy_panel(n_vars: int = 6, T: int = 200, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = [f"v{i}" for i in range(n_vars)]
    data = rng.standard_normal((T, n_vars)).cumsum(axis=0) * 0.1 + rng.standard_normal((T, n_vars))
    return pd.DataFrame(data, columns=cols)


def _simulate_small_var(T: int = 200, n_vars: int = 2, n_lags: int = 2,
                        rng: np.random.Generator | None = None) -> tuple[np.ndarray, np.ndarray]:
    rng = rng or np.random.default_rng(0)
    n_kp1 = n_vars * n_lags + 1
    Y_full = rng.standard_normal((T + n_lags, n_vars))
    Y = Y_full[n_lags:]
    X = np.empty((T, n_kp1))
    X[:, 0] = 1.0
    for l in range(1, n_lags + 1):
        X[:, 1 + (l - 1) * n_vars: 1 + l * n_vars] = Y_full[n_lags - l: T + n_lags - l]
    return Y, X


def test_minnesota_dummies_have_correct_count():
    """n=6, p=4 → n*p + 2n + 2 = 38 dummy rows. Per-block counts must match."""
    panel = _toy_panel(n_vars=6, T=200, seed=1)
    prior = MinnesotaPrior(
        n_vars=6, n_lags=4, training_data=panel,
        persistence_prior={f"v{i}": (1.0 if i % 2 == 0 else 0.5) for i in range(6)},
    )
    Y_d, X_d = prior.dummy_observations()
    assert Y_d.shape == (38, 6)
    assert X_d.shape == (38, 6 * 4 + 1)
    blocks = prior.dummy_block_counts
    assert blocks == {
        "coefficients": 24,
        "covariance": 6,
        "intercept": 1,
        "sum_of_coefficients": 6,
        "initial_observation": 1,
    }
    assert sum(blocks.values()) == 38


def test_prior_persistence_matches_input():
    persistence = {"v0": 0.5, "v1": 0.9, "v2": 0.0}
    prior = MinnesotaPrior(
        n_vars=3, n_lags=2,
        sigma=np.ones(3), y_bar=np.zeros(3),
        persistence_prior=persistence,
        variable_names=["v0", "v1", "v2"],
    )
    moments = prior.prior_moments()
    for i, name in enumerate(["v0", "v1", "v2"]):
        # Lag-1 own-coefficient for variable i is at column 1 + i.
        assert moments["B_mean"][i, 1 + i] == pytest.approx(persistence[name])
    # All other lag-1 entries should be zero (cross effects).
    for i in range(3):
        for j in range(3):
            if j != i:
                assert moments["B_mean"][i, 1 + j] == 0.0
    # Lag-2 entries should all be zero.
    for i in range(3):
        for j in range(3):
            assert moments["B_mean"][i, 1 + 3 + j] == 0.0


def test_prior_loose_lambda_recovers_ols():
    """With lambda_1 huge AND lambda_sc=lambda_io=0, augmented OLS == plain OLS.

    Deliberate diffuse-everything regime to verify the dummy construction is
    internally consistent — NOT a realistic prior. Block B (covariance) stays
    in place because the prior must remain proper, but it does not contribute
    to the coefficient posterior under the canonical Litterman/Sims-Zha
    factorization.
    """
    rng = np.random.default_rng(0)
    Y, X = _simulate_small_var(T=200, n_vars=2, n_lags=2, rng=rng)
    prior = MinnesotaPrior(
        n_vars=2, n_lags=2,
        lambda_1=1e6,
        lambda_sc=0.0,
        lambda_io=0.0,
        sigma=np.std(Y, axis=0),
        y_bar=Y.mean(axis=0),
        persistence_prior=np.zeros(2),
        variable_names=["v0", "v1"],
    )
    Y_d, X_d = prior.dummy_observations()
    Y_aug = np.vstack([Y, Y_d])
    X_aug = np.vstack([X, X_d])
    B_aug = np.linalg.solve(X_aug.T @ X_aug, X_aug.T @ Y_aug)
    B_ols = np.linalg.solve(X.T @ X, X.T @ Y)
    assert np.allclose(B_aug, B_ols, atol=1e-3)


def test_prior_inspect_is_json_serializable():
    panel = _toy_panel(n_vars=3, T=80, seed=2)
    prior = MinnesotaPrior(
        n_vars=3, n_lags=2,
        training_data=panel,
        persistence_prior={"v0": 0.0, "v1": 0.5, "v2": 1.0},
    )
    info = prior.inspect()
    s = json.dumps(info)
    assert "lambda_1" in s
    assert "dummy_block_counts" in s
    assert "sigma" in s
    # Round-trip via JSON.
    info2 = json.loads(s)
    assert info2["n_vars"] == 3
    assert info2["dummy_block_counts"]["coefficients"] == 6  # n*p = 3*2
