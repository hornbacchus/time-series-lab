"""JIT cache pre-warmer for BVAR's numba-jitted inner loops.

Call once on the main thread at process startup, BEFORE spawning
background threads. Triggers JIT compile + cache write for both
``_ffbs.ffbs_one_equation`` and
``_conditional_inner.conditional_forecast_inner_loop`` on minimal-size
dummy inputs (in both strict=True and strict=False modes).

The first JIT call from each thread races to write the same
``__pycache__/<file>.nbc`` cache file. Numba has a process-level lock
that handles this on most platforms but has had historical Windows
intermittent failures. Warming on the main thread before spawning
background threads avoids the race entirely.

Usage (in TSL's engine_worker startup, post-migration)::

    from ._jit_warmer import warm_jit_caches
    warm_jit_caches()
    # ... now spawn background threads safely ...
"""

from __future__ import annotations

import numpy as np


def warm_jit_caches() -> None:
    """Force compile + cache of both BVAR JIT functions.

    Idempotent: subsequent calls hit the cache and return in <100 ms
    on warm cache. Safe to call once at process startup. Single-threaded
    (caller's responsibility to call before spawning threads).

    Cold-compile time on first call is roughly 2-5 s combined for both
    functions; cache binds to (numba version, Python version, platform,
    source-file mtime) so a fresh deployment re-compiles once.
    """
    from ._ffbs import ffbs_one_equation
    from ._conditional_inner import conditional_forecast_inner_loop

    # Minimal FFBS warm: T=2, scalar params, deterministic dummy normals.
    obs = np.zeros(2, dtype=float)
    R = np.ones(2, dtype=float)
    rng_normals = np.zeros(2, dtype=float)
    ffbs_one_equation(obs, R, 0.5, 0.0, 0.1, rng_normals)

    # Minimal conditional-forecast warm: n_vars=2, n_lags=1, horizon=1,
    # n_target=1, n_macro=1, n_paths=1.
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

    # Run BOTH strict=True and strict=False so both JIT branches compile.
    for strict in (True, False):
        conditional_forecast_inner_loop(
            B, A_inv, h_T, omega, phi, mu,
            state_init, projection,
            target_idx, macro_idx,
            strict, R_diag,
            z_t, z_m, z_h,
        )
