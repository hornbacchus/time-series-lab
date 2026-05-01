"""Convergence and fit diagnostics for the BVAR-SV Markov chain.

Implements Geweke (1992) z-statistic with Bartlett-window spectral-density
numerical standard errors, and effective sample size via the initial
positive-sequence estimator (Geyer 1992).

Citation:
    Geweke, J. (1992). "Evaluating the accuracy of sampling-based approaches
    to the calculation of posterior moments," in Bayesian Statistics 4
    (J.M. Bernardo et al., eds.), Oxford University Press.
"""

from __future__ import annotations

import numpy as np


def _bartlett_spectral_density(x: np.ndarray, bandwidth: int) -> float:
    """Spectral density at frequency 0 with a Bartlett window of given bandwidth."""
    n = x.shape[0]
    x_centered = x - x.mean()
    s0 = float(np.var(x_centered, ddof=0))
    var = s0
    for k in range(1, bandwidth + 1):
        autocov = float(np.mean(x_centered[k:] * x_centered[:-k]))
        weight = 1.0 - k / (bandwidth + 1)
        var += 2.0 * weight * autocov
    return max(var, 0.0)


def bartlett_nse(draws: np.ndarray, bandwidth_factor: float = 4.0) -> float:
    """Numerical standard error via Bartlett-window spectral density.

    Bandwidth = round(bandwidth_factor * (n/100)**(2/9)) per Geweke (1992).
    """
    n = draws.shape[0]
    bw = max(1, int(round(bandwidth_factor * (n / 100.0) ** (2.0 / 9.0))))
    bw = min(bw, max(1, n - 1))
    s0 = _bartlett_spectral_density(draws, bw)
    return float(np.sqrt(s0 / n))


def geweke_z(
    draws: np.ndarray,
    first_frac: float = 0.1,
    last_frac: float = 0.5,
    bandwidth_factor: float = 4.0,
) -> tuple[float, float, float]:
    """Geweke (1992) z-statistic comparing first 10% to last 50% of draws.

    Returns
    -------
    z         : test statistic (|z| < 1.96 ⇒ converged at 95% level)
    nse_first : NSE of the first segment mean
    nse_last  : NSE of the last segment mean
    """
    n = draws.shape[0]
    n_first = max(2, int(np.floor(first_frac * n)))
    n_last = max(2, int(np.floor(last_frac * n)))
    first = draws[:n_first]
    last = draws[n - n_last:]

    mean_diff = float(first.mean() - last.mean())
    nse_first = bartlett_nse(first, bandwidth_factor=bandwidth_factor)
    nse_last = bartlett_nse(last, bandwidth_factor=bandwidth_factor)
    se = float(np.sqrt(nse_first * nse_first + nse_last * nse_last))
    if se == 0.0:
        return (0.0, nse_first, nse_last)
    z = mean_diff / se
    return (z, nse_first, nse_last)


def effective_sample_size(draws: np.ndarray) -> float:
    """Initial positive-sequence ESS estimator (Geyer 1992).

    Sums consecutive lag-pair autocorrelations until the pair sum is no
    longer positive, then ESS = n / (1 + 2 * sum_of_positive_pair_sums).
    """
    n = draws.shape[0]
    if n < 4:
        return float(n)
    x = draws - draws.mean()
    var = float(np.dot(x, x) / n)
    if var == 0.0:
        return float(n)

    rho_sum = 0.0
    max_lag = (n - 1) // 2
    for k in range(0, max_lag):
        lag1 = 2 * k + 1
        lag2 = 2 * k + 2
        if lag2 >= n:
            break
        rho1 = float(np.dot(x[lag1:], x[:-lag1]) / (n * var))
        rho2 = float(np.dot(x[lag2:], x[:-lag2]) / (n * var))
        pair = rho1 + rho2
        if pair <= 0.0:
            break
        rho_sum += pair

    ess = n / (1.0 + 2.0 * rho_sum)
    return float(min(ess, n))
