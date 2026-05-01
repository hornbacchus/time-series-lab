"""Tests for S0.4: numba JIT cache pre-warmer."""

from __future__ import annotations

import time

import numpy as np
import pytest

from techniques.bond_yield_forecast._jit_warmer import warm_jit_caches


def test_warm_jit_caches_runs_without_error():
    """warm_jit_caches() can be called once with no exception."""
    warm_jit_caches()


def test_warm_jit_caches_is_idempotent():
    """Calling warm_jit_caches() twice in a row works (cache reuse)."""
    warm_jit_caches()
    warm_jit_caches()  # second call hits cache; should not error


def test_jit_post_warm_is_fast():
    """After warming, a subsequent JIT invocation completes in <100 ms.

    Threshold is loose (100 ms) to accommodate Windows filesystem
    latency on the cache lookup. Cold compile is ~2-5 s; cached load
    is typically 1-10 ms; 100 ms still demonstrates >>20x improvement
    over cold compile.
    """
    # Warm first (may be cold or already cached from a prior test).
    warm_jit_caches()

    # Now time a fresh invocation of each JIT function with the SAME
    # signatures (so the warmer's cache entry applies).
    from techniques.bond_yield_forecast._ffbs import ffbs_one_equation
    from techniques.bond_yield_forecast._conditional_inner import conditional_forecast_inner_loop

    obs = np.zeros(2, dtype=float)
    R = np.ones(2, dtype=float)
    rng_normals = np.zeros(2, dtype=float)

    t0 = time.perf_counter()
    ffbs_one_equation(obs, R, 0.5, 0.0, 0.1, rng_normals)
    ffbs_dt = time.perf_counter() - t0

    n_vars, n_lags, horizon, n_paths = 2, 1, 1, 1
    B = np.zeros((n_vars, n_vars * n_lags + 1), dtype=float)
    B[0, 1] = 0.5
    B[1, 2] = 0.5
    A_inv = np.eye(n_vars, dtype=float)
    h_T = np.zeros(n_vars, dtype=float)
    omega = np.full(n_vars, 0.1, dtype=float)
    phi = np.full(n_vars, 0.95, dtype=float)
    mu = np.zeros(n_vars, dtype=float)
    state_init = np.zeros((n_lags, n_vars), dtype=float)
    projection = np.zeros((horizon, 1), dtype=float)
    target_idx = np.array([0], dtype=np.int64)
    macro_idx = np.array([1], dtype=np.int64)
    R_diag = np.array([0.5], dtype=float)
    z_t = np.zeros((n_paths, horizon, 1), dtype=float)
    z_m = np.zeros((n_paths, horizon, 1), dtype=float)
    z_h = np.zeros((n_paths, horizon, n_vars), dtype=float)

    t0 = time.perf_counter()
    conditional_forecast_inner_loop(
        B, A_inv, h_T, omega, phi, mu,
        state_init, projection, target_idx, macro_idx,
        True, R_diag, z_t, z_m, z_h,
    )
    cf_dt = time.perf_counter() - t0

    assert ffbs_dt < 0.1, (
        f"Post-warm ffbs_one_equation took {ffbs_dt*1000:.1f} ms; "
        f"cache may not have hit. Threshold: 100 ms."
    )
    assert cf_dt < 0.1, (
        f"Post-warm conditional_forecast_inner_loop took {cf_dt*1000:.1f} ms; "
        f"cache may not have hit. Threshold: 100 ms."
    )
