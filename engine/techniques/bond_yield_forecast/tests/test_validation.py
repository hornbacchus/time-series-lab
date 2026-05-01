"""Tests for src/bvar/validation.py — Step 2.5 validation harness."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.estimation import BVARSV
from techniques.bond_yield_forecast.priors import MinnesotaPrior
from techniques.bond_yield_forecast.validation import ValidationHarness


def _quick_panel_for_econ_check(seed: int = 7) -> pd.DataFrame:
    """Tiny synthetic panel for the format-only economic-check test."""
    rng = np.random.default_rng(seed)
    n_vars, n_lags, T = 2, 1, 80
    Y = np.zeros((T + n_lags, n_vars))
    Y[:n_lags] = rng.standard_normal((n_lags, n_vars))
    for t in range(n_lags, T + n_lags):
        Y[t] = 0.5 * Y[t - 1] + 0.5 * rng.standard_normal(n_vars)
    quarters = pd.period_range("1990-Q1", periods=T + n_lags, freq="Q-DEC")
    return pd.DataFrame(Y, index=quarters, columns=["v0", "v1"])


def test_posterior_recovery_test_runs_and_reports_format():
    """Smoke: small custom config runs end-to-end and returns the right keys."""
    harness = ValidationHarness()
    result = harness.posterior_recovery_test(
        n_vars=2, n_lags=1, T=150, n_simulations=2, seed_base=42,
    )
    assert "custom" in result
    assert "pass" in result
    custom = result["custom"]
    for k in ("config", "B", "A", "omega", "phi", "mu", "pass"):
        assert k in custom, f"missing key {k}"
    for stat_key in ("bias_mean_max_abs", "coverage_rate_mean"):
        assert stat_key in custom["B"]
    assert custom["config"]["n_vars"] == 2
    assert custom["config"]["n_lags"] == 1


def test_analytic_invariant_tests_run():
    """Smoke: end-to-end on default small synthetic panel; assert format."""
    harness = ValidationHarness()
    result = harness.analytic_invariant_tests()
    for k in ("loose_prior_limit", "high_lag_decay_limit", "constant_vol_limit", "all_pass"):
        assert k in result
    # Constant-vol now runs (Step 2.5 follow-up: force_constant_h flag).
    assert "skipped" not in result["constant_vol_limit"]
    assert result["constant_vol_limit"]["pass"]
    # All three sub-tests should report 'pass' and 'tolerance'.
    for k in ("loose_prior_limit", "high_lag_decay_limit", "constant_vol_limit"):
        assert "pass" in result[k]
        assert "tolerance" in result[k]


def test_real_data_economic_checks_run():
    """Smoke on synthetic; assert dict format. Doesn't enforce econ assertions
    on synthetic since the panel doesn't have named real-data variables."""
    panel = _quick_panel_for_econ_check()
    prior = MinnesotaPrior(
        n_vars=2, n_lags=1, training_data=panel,
        persistence_prior={"v0": 0.5, "v1": 0.5},
        variable_names=list(panel.columns),
    )
    bvar = BVARSV(panel, n_lags=1, prior=prior, n_draws=300, n_burn=100, seed=0)
    res = bvar.estimate()
    pca_dict = {
        "loadings": np.eye(2),
        "mean": np.zeros(2),
        "explained_variance_ratio": np.ones(2) / 2,
        "yield_names": ["v0", "v1"],
        "component_names": ["v0", "v1"],
    }
    harness = ValidationHarness()
    result = harness.real_data_economic_checks(res, panel, pca_dict)
    for k in ("var_stability", "irf_check", "forecast_curve_sanity", "all_pass"):
        assert k in result
    # var_stability has shape and key contract regardless of data
    assert "max_modulus" in result["var_stability"]


def test_stochvol_cross_validation_gracefully_skips_without_rpy2():
    """If rpy2 is not importable, harness returns a skip dict rather than crashing."""
    try:
        import rpy2  # noqa: F401
        pytest.skip("rpy2 is installed; skip-path test is not meaningful here")
    except ImportError:
        pass

    # Build a quick BVARSVResults to feed in.
    panel = _quick_panel_for_econ_check(seed=11)
    prior = MinnesotaPrior(
        n_vars=2, n_lags=1, training_data=panel,
        persistence_prior={"v0": 0.5, "v1": 0.5},
        variable_names=list(panel.columns),
    )
    bvar = BVARSV(panel, n_lags=1, prior=prior, n_draws=300, n_burn=100, seed=0)
    res = bvar.estimate()

    harness = ValidationHarness()
    out = harness.stochvol_sv_cross_validation(res)
    assert out.get("skipped") == "rpy2_unavailable"
