"""Tests for S0.3: parameter zero-divide guards.

Bounded audit per the prompt:
  - MinnesotaPrior lambdas (lambda_1..lambda_4 strict-positive;
    lambda_sc/lambda_io non-negative)
  - ConditionalForecaster.forecast: n_paths_per_draw >= 1,
    n_draws_subsample >= 1 or None
  - projection_uncertainty: tiered (hard ValueError < 1e-4,
    BVARWarning < 1e-2, clean >= 1e-2)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.exceptions import BVARWarning
from techniques.bond_yield_forecast.priors import MinnesotaPrior


def _toy_panel(T: int = 60, n: int = 2, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    Y = rng.standard_normal((T, n)) * 0.5
    idx = pd.period_range("1990-Q1", periods=T, freq="Q-DEC")
    return pd.DataFrame(Y, index=idx, columns=[f"v{i}" for i in range(n)])


# ---------------------------------------------------------------------------
# MinnesotaPrior lambda guards
# ---------------------------------------------------------------------------


def _make_prior(panel, **kwargs):
    """Construct prior with sensible defaults except for overrides in kwargs."""
    defaults = dict(
        n_vars=panel.shape[1], n_lags=1,
        training_data=panel,
        persistence_prior={c: 0.5 for c in panel.columns},
        variable_names=list(panel.columns),
    )
    defaults.update(kwargs)
    return MinnesotaPrior(**defaults)


def test_minnesota_prior_rejects_zero_lambda_1():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_1 must be positive"):
        _make_prior(panel, lambda_1=0.0)


def test_minnesota_prior_rejects_negative_lambda_1():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_1 must be positive"):
        _make_prior(panel, lambda_1=-0.5)


def test_minnesota_prior_rejects_zero_lambda_2():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_2 must be positive"):
        _make_prior(panel, lambda_2=0.0)


def test_minnesota_prior_rejects_zero_lambda_3():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_3 must be positive"):
        _make_prior(panel, lambda_3=0.0)


def test_minnesota_prior_rejects_zero_lambda_4():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_4 must be positive"):
        _make_prior(panel, lambda_4=0.0)


def test_minnesota_prior_accepts_zero_lambda_sc_and_io():
    """lambda_sc=0 and lambda_io=0 are explicitly allowed (used by
    validation.py's _loose_prior_limit_test to disable SoC/IO dummies)."""
    panel = _toy_panel()
    prior = _make_prior(panel, lambda_sc=0.0, lambda_io=0.0)
    assert prior.lambda_sc == 0.0
    assert prior.lambda_io == 0.0


def test_minnesota_prior_rejects_negative_lambda_sc():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_sc must be non-negative"):
        _make_prior(panel, lambda_sc=-0.1)


def test_minnesota_prior_rejects_negative_lambda_io():
    panel = _toy_panel()
    with pytest.raises(ValueError, match="lambda_io must be non-negative"):
        _make_prior(panel, lambda_io=-0.1)


# ---------------------------------------------------------------------------
# ConditionalForecaster guards
# ---------------------------------------------------------------------------


def _build_minimal_forecaster(strict=True, projection_uncertainty=None):
    """Build a minimal ConditionalForecaster on a tiny synthetic panel.

    Reuses the test_conditioning fixtures by importing them.
    """
    from techniques.bond_yield_forecast.tests.test_conditioning import (
        _toy_results, _toy_projections, _conditioning_config,
    )
    from techniques.bond_yield_forecast.conditioning import ConditionalForecaster

    results = _toy_results(seed=0)
    horizon = 4
    proj = _toy_projections(results.data_used, horizon=horizon, seed=0)
    cfg = _conditioning_config(
        horizon=horizon, n_paths_per_draw=4, n_draws_subsample=10,
        strict=strict, proj_unc=projection_uncertainty,
    )
    return ConditionalForecaster(
        results=results, projections=proj, config_section=cfg, seed=0,
    )


def test_conditioning_rejects_zero_n_paths_per_draw():
    fc = _build_minimal_forecaster()
    with pytest.raises(ValueError, match="n_paths_per_draw must be >= 1"):
        fc.forecast(n_paths_per_draw=0)


def test_conditioning_rejects_zero_n_draws_subsample():
    fc = _build_minimal_forecaster()
    with pytest.raises(ValueError, match="n_draws_subsample must be >= 1 or None"):
        fc.forecast(n_draws_subsample=0)


def test_conditioning_rejects_uncertainty_below_hard_threshold():
    """projection_uncertainty < 1e-4 raises ValueError."""
    proj_unc = {"macro_a": 1e-9, "macro_b": 1e-9}  # well below 1e-4
    fc = _build_minimal_forecaster(strict=False, projection_uncertainty=proj_unc)
    with pytest.raises(ValueError, match="must be >="):
        fc.forecast()


def test_conditioning_warns_at_borderline_uncertainty():
    """1e-4 <= projection_uncertainty < 1e-2 emits BVARWarning, runs."""
    proj_unc = {"macro_a": 5e-3, "macro_b": 5e-3}  # in (1e-4, 1e-2)
    fc = _build_minimal_forecaster(strict=False, projection_uncertainty=proj_unc)
    with pytest.warns(BVARWarning, match="numerically unstable"):
        cf = fc.forecast()
    # Forecast still runs to completion with a valid result.
    assert cf.target_paths.shape[0] > 0


def test_conditioning_clean_at_normal_uncertainty():
    """projection_uncertainty >= 1e-2 emits no warning."""
    import warnings as _warnings
    proj_unc = {"macro_a": 0.5, "macro_b": 0.3}  # well above 1e-2
    fc = _build_minimal_forecaster(strict=False, projection_uncertainty=proj_unc)
    with _warnings.catch_warnings():
        _warnings.simplefilter("error", BVARWarning)
        cf = fc.forecast()  # would raise if BVARWarning fires
    assert cf.target_paths.shape[0] > 0
