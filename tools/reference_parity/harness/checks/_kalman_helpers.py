"""Shared helpers for KFAS-based parity checks (Batch 5).

Three wrappers (`local_level`, `local_linear_trend`,
`structural_ts`) share statsmodels UnobservedComponents
backbone vs R KFAS. Common patterns:

- DGP generators per state-space model class
- TSL invocation via UnobservedComponents (direct, bypassing
  6-decimal output rounding per Phase 1 finding B8)
- R KFAS invocation template
- Shared output extraction (sigma_eps, sigma_eta, log-lik,
  smoothed states, filtered/smoothed covariances)
- Pattern F invariant data extraction
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np


def generate_local_level_dgp(
    *,
    seed: int,
    n: int = 200,
    sigma_eta: float = 1.0,
    sigma_eps: float = 2.0,
) -> np.ndarray:
    """Local level: mu_t = mu_{t-1} + eta_t; y_t = mu_t + eps_t."""
    rng = np.random.default_rng(seed)
    eta = rng.standard_normal(n) * sigma_eta
    mu = np.cumsum(eta)
    eps = rng.standard_normal(n) * sigma_eps
    return mu + eps


def generate_llt_dgp(
    *,
    seed: int,
    n: int = 200,
    sigma_eta: float = 0.5,    # level noise
    sigma_zeta: float = 0.1,   # slope noise
    sigma_eps: float = 1.0,
) -> np.ndarray:
    """Local linear trend:
        beta_t = beta_{t-1} + zeta_t
        mu_t = mu_{t-1} + beta_{t-1} + eta_t
        y_t = mu_t + eps_t
    """
    rng = np.random.default_rng(seed)
    eta = rng.standard_normal(n) * sigma_eta
    zeta = rng.standard_normal(n) * sigma_zeta
    eps = rng.standard_normal(n) * sigma_eps
    beta = np.cumsum(zeta)
    mu = np.cumsum(beta + eta)
    return mu + eps


def generate_structural_dgp(
    *,
    seed: int,
    n: int = 240,
    m: int = 12,
    sigma_eta: float = 0.5,
    sigma_zeta: float = 0.05,
    sigma_omega: float = 0.5,
    sigma_eps: float = 1.0,
) -> np.ndarray:
    """Local linear trend + dummy seasonal (period m).

    Seasonal s_t evolves so that sum of last m s_t equals omega
    (a Gaussian innovation). Standard structural TS model.
    """
    rng = np.random.default_rng(seed)
    eta = rng.standard_normal(n) * sigma_eta
    zeta = rng.standard_normal(n) * sigma_zeta
    omega = rng.standard_normal(n) * sigma_omega
    eps = rng.standard_normal(n) * sigma_eps
    # State recursion
    beta = np.cumsum(zeta)
    mu = np.cumsum(beta + eta)
    # Seasonal: dummy/Harvey form: s_t = -sum(s_{t-1..t-m+1}) + omega_t
    s = np.zeros(n)
    for t in range(m, n):
        s[t] = -np.sum(s[t-m+1:t]) + omega[t]
    return mu + s + eps


def fit_uc_model(
    y: np.ndarray, *, level: str, **kwargs: Any,
) -> dict[str, Any]:
    """Fit statsmodels UnobservedComponents and extract Kalman
    filter outputs needed for parity comparison + structural
    invariant computation.

    Returns dict with sigma_eps, sigma_eta (and slope/seasonal
    if applicable), log-likelihood, AIC, BIC, smoothed state
    means, smoothed state covariances, filtered state covariances,
    predicted state covariances, innovation variances.
    """
    from statsmodels.tsa.statespace.structural import (  # type: ignore
        UnobservedComponents,
    )
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        model = UnobservedComponents(y, level=level, **kwargs)
        fit = model.fit(disp=False, maxiter=200)

    # Variance parameters. statsmodels UC fit.params is a
    # numpy array; param names live on fit.model.param_names
    # (consistent with MarkovRegression API surface).
    params_arr = np.asarray(fit.params, dtype=np.float64)
    if hasattr(fit.params, "index"):
        param_names = list(fit.params.index)
    else:
        param_names = list(fit.model.param_names)
    params = dict(zip(param_names, params_arr))

    # statsmodels parameter names:
    #   sigma2.irregular = sigma_eps^2
    #   sigma2.level = sigma_eta^2
    #   sigma2.trend = sigma_zeta^2 (LLT)
    #   sigma2.seasonal = sigma_omega^2 (when freq_seasonal/seasonal added)
    sigma_eps2 = params.get("sigma2.irregular")
    sigma_eta2 = params.get("sigma2.level")
    sigma_zeta2 = params.get("sigma2.trend")
    sigma_omega2 = params.get("sigma2.seasonal")

    # Extract Kalman filter outputs from filter_results
    fr = fit.filter_results
    # Smoothed state means: (k_states, T) — transpose to (T, k)
    smoothed_state = np.asarray(
        fit.smoothed_state, dtype=np.float64,
    ).T if hasattr(fit, "smoothed_state") else None
    # Smoothed state covariance: (k_states, k_states, T) → (T, k, k)
    if hasattr(fit, "smoothed_state_cov"):
        smoothed_cov = np.transpose(
            np.asarray(fit.smoothed_state_cov, dtype=np.float64),
            (2, 0, 1),
        )
    else:
        smoothed_cov = None
    # Filtered state covariance
    filtered_cov = np.transpose(
        np.asarray(fr.filtered_state_cov, dtype=np.float64),
        (2, 0, 1),
    )
    # Predicted state covariance
    predicted_cov = np.transpose(
        np.asarray(fr.predicted_state_cov, dtype=np.float64),
        (2, 0, 1),
    )
    # Innovation variance F_t
    forecast_error_cov = np.transpose(
        np.asarray(fr.forecasts_error_cov, dtype=np.float64),
        (2, 0, 1),
    )
    # 1-D series: F_t is (T, 1, 1) → flatten to (T,)
    if forecast_error_cov.ndim == 3 and forecast_error_cov.shape[1:] == (1, 1):
        innovation_var = forecast_error_cov[:, 0, 0]
    else:
        innovation_var = forecast_error_cov

    return {
        "sigma_eps2": sigma_eps2,
        "sigma_eta2": sigma_eta2,
        "sigma_zeta2": sigma_zeta2,
        "sigma_omega2": sigma_omega2,
        "log_likelihood": float(fit.llf),
        "aic": float(fit.aic),
        "bic": float(fit.bic),
        "smoothed_state": smoothed_state,
        "smoothed_state_cov": smoothed_cov,
        "filtered_state_cov": filtered_cov,
        "predicted_state_cov": predicted_cov,
        "innovation_variance": innovation_var,
    }


__all__ = [
    "generate_local_level_dgp",
    "generate_llt_dgp",
    "generate_structural_dgp",
    "fit_uc_model",
]
