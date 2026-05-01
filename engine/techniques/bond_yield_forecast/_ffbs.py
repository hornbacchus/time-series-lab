"""Forward-filter / backward-sample (Carter-Kohn 1994) for log-volatility AR(1).

Univariate state-space:
    obs[t] = 2 * h_t + N(0, R[t])                    # KSC mixture branch
    h_t = phi * h_{t-1} + (1 - phi) * mu + omega * eta_t,  eta_t ~ N(0, 1)

The univariate inner loop runs (T, n) * n_iters times during BVAR-SV
estimation, making it the bottleneck. Numba JIT speeds it up 5-10x
versus pure Python.

Random draws are PRE-GENERATED in the outer Python loop using the
caller's np.random.Generator and passed in as a plain ndarray, so seed
reproducibility is guaranteed independent of numba's internal RNG.

A trivial JIT compile is run at module import to fail fast if numba is
broken — better than hitting a confusing error inside Gibbs iteration 1.
"""

from __future__ import annotations

import numpy as np

try:
    from numba import jit
except ImportError as exc:
    raise ImportError(
        "numba is required for BVAR-SV estimation; install with `pip install numba>=0.58`."
    ) from exc


@jit(nopython=True, cache=True)
def _jit_smoke(x: float) -> float:
    return x + 1.0


try:
    _jit_smoke(0.0)
except Exception as exc:
    raise ImportError(
        "Numba JIT failed; FFBS sampler cannot run. "
        "Install numba >=0.58 via `pip install numba`."
    ) from exc


@jit(nopython=True, cache=True)
def ffbs_one_equation(
    obs: np.ndarray,
    R: np.ndarray,
    phi: float,
    mu: float,
    omega: float,
    rng_normals: np.ndarray,
) -> np.ndarray:
    """Sample h_{0..T-1} from p(h | obs, params) via Carter-Kohn FFBS.

    Parameters
    ----------
    obs : (T,) — KSC-debiased log squared residual = log(e_t^2) - mix_means[s_t]
    R   : (T,) — KSC-conditional observation variance = mix_vars[s_t]
    phi : AR(1) persistence
    mu  : AR(1) unconditional mean (held fixed across iterations)
    omega : AR(1) innovation standard deviation
    rng_normals : (T,) — pre-drawn N(0, 1) standard normals

    Returns
    -------
    h : (T,) sampled log-volatility states
    """
    T = obs.shape[0]
    omega2 = omega * omega
    if abs(phi) < 1.0:
        P0 = omega2 / (1.0 - phi * phi)
    else:
        P0 = omega2 * 1000.0  # diffuse for non-stationary chain

    h_filt = np.empty(T)
    P_filt = np.empty(T)

    # Forward filter
    h_pred = mu
    P_pred = P0
    for t in range(T):
        F = 4.0 * P_pred + R[t]
        K = 2.0 * P_pred / F
        innov = obs[t] - 2.0 * h_pred
        h_filt[t] = h_pred + K * innov
        P_filt[t] = R[t] * P_pred / F

        if t < T - 1:
            h_pred = phi * h_filt[t] + (1.0 - phi) * mu
            P_pred = phi * phi * P_filt[t] + omega2

    # Backward sample
    h = np.empty(T)
    h[T - 1] = h_filt[T - 1] + np.sqrt(P_filt[T - 1]) * rng_normals[T - 1]
    for t in range(T - 2, -1, -1):
        inv_var = 1.0 / P_filt[t] + phi * phi / omega2
        P_smooth = 1.0 / inv_var
        h_smooth = P_smooth * (
            h_filt[t] / P_filt[t]
            + phi * (h[t + 1] - (1.0 - phi) * mu) / omega2
        )
        h[t] = h_smooth + np.sqrt(P_smooth) * rng_normals[t]

    return h
