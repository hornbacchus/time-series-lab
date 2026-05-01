"""Kim-Shephard-Chib (1998) 7-component normal mixture for log(chi-squared_1).

Citation:
    Kim, S., Shephard, N., Chib, S. (1998). "Stochastic Volatility:
    Likelihood Inference and Comparison with ARCH Models." Review of
    Economic Studies 65(3):361-393, Table 4 (p. 371).

We use the 7-component table EXACTLY as published in KSC-1998 above.
We deliberately do NOT use the Omori-Chib-Shephard-Nakajima (2007)
10-component refinement; the published Octave/MATLAB BVAR toolboxes
typically use the KSC-1998 7-component table, and Step 2.5 validates
this implementation against one of those toolboxes.
"""

from __future__ import annotations

import numpy as np

KSC_PROBABILITIES = np.array(
    [0.00730, 0.10556, 0.00002, 0.04395, 0.34001, 0.24566, 0.25750]
)
KSC_MEANS = np.array(
    [-10.12999, -3.97281, -8.56686, 2.77786, 0.61942, 1.79518, -1.08819]
)
KSC_VARIANCES = np.array(
    [5.79596, 2.61369, 5.17950, 0.16735, 0.64009, 0.34023, 1.26261]
)

KSC_MIXTURE = {
    "probabilities": KSC_PROBABILITIES,
    "means": KSC_MEANS,
    "variances": KSC_VARIANCES,
}


def sample_mixture_indicators(
    log_e2: np.ndarray,
    h: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample KSC mixture indicators given current log squared residuals + log-vol.

    For each (t, i) cell, the conditional probability of component j is:
        P(s = j | log_e2, h) ~ probabilities[j] *
            Normal(log_e2 - 2*h | means[j], variances[j])

    Parameters
    ----------
    log_e2 : (T, n) — log of orthogonalized squared residuals
    h      : (T, n) — current log-volatility states
    rng    : numpy Generator

    Returns
    -------
    s : (T, n) array of int in [0, 6] — mixture component indicator per cell
    """
    if log_e2.shape != h.shape:
        raise ValueError(
            f"log_e2 shape {log_e2.shape} does not match h shape {h.shape}"
        )

    diff = log_e2 - 2.0 * h
    diff = diff[..., None]
    means = KSC_MEANS[None, None, :]
    variances = KSC_VARIANCES[None, None, :]
    probs = KSC_PROBABILITIES[None, None, :]

    log_pdf = (
        -0.5 * np.log(2.0 * np.pi * variances)
        - 0.5 * (diff - means) ** 2 / variances
    )
    log_w = np.log(probs) + log_pdf
    log_w -= log_w.max(axis=-1, keepdims=True)
    w = np.exp(log_w)
    w /= w.sum(axis=-1, keepdims=True)

    cumw = np.cumsum(w, axis=-1)
    u = rng.random(size=log_e2.shape)[..., None]
    s = (u >= cumw).sum(axis=-1)
    np.clip(s, 0, 6, out=s)
    return s.astype(np.int64)
