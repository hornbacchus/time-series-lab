"""Tests for the KSC-1998 7-component mixture used by the SV step."""

from __future__ import annotations

import numpy as np

from techniques.bond_yield_forecast._ksc_mixture import (
    KSC_MEANS,
    KSC_PROBABILITIES,
    KSC_VARIANCES,
    sample_mixture_indicators,
)


def test_ksc_mixture_weights_match_published_table():
    """KSC-1998 Table 4 (Review of Economic Studies 65, p. 371)."""
    expected_p = [0.00730, 0.10556, 0.00002, 0.04395, 0.34001, 0.24566, 0.25750]
    expected_m = [-10.12999, -3.97281, -8.56686, 2.77786, 0.61942, 1.79518, -1.08819]
    expected_v = [5.79596, 2.61369, 5.17950, 0.16735, 0.64009, 0.34023, 1.26261]
    assert np.allclose(KSC_PROBABILITIES, expected_p)
    assert np.allclose(KSC_MEANS, expected_m)
    assert np.allclose(KSC_VARIANCES, expected_v)
    # Probabilities sum to 1 within rounding error.
    assert abs(KSC_PROBABILITIES.sum() - 1.0) < 1e-3


def test_sample_mixture_indicators_returns_valid_indices():
    rng = np.random.default_rng(42)
    log_e2 = rng.standard_normal((50, 3))
    h = rng.standard_normal((50, 3)) * 0.5
    s = sample_mixture_indicators(log_e2, h, rng)
    assert s.shape == (50, 3)
    assert s.dtype.kind in ("i", "u")
    assert (s >= 0).all() and (s <= 6).all()
