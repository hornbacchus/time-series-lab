"""Deterministic synthetic data for the template workbook and test fixture.

Yields are generated from a 3-factor Nelson-Siegel structure so that PCA
cleanly recovers level/slope/curvature for tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MATURITY_LABELS = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
MATURITY_YEARS = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
NS_TAU = 2.0

MACRO_COLUMNS = [
    "Real GDP Growth (Q/Q SAAR)",
    "Headline CPI Inflation (Q/Q annualized)",
    "Fed Funds Rate (quarterly average)",
]


def _ar1(
    n: int,
    mean: float,
    phi: float,
    sigma: float,
    init: float,
    rng: np.random.Generator,
) -> np.ndarray:
    x = np.empty(n)
    x[0] = init
    for t in range(1, n):
        x[t] = (1.0 - phi) * mean + phi * x[t - 1] + sigma * rng.standard_normal()
    return x


def ns_loadings(
    maturities: np.ndarray = MATURITY_YEARS,
    tau: float = NS_TAU,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Nelson-Siegel basis vectors: (level, slope, curvature) at each maturity."""
    m_over_tau = maturities / tau
    L_level = np.ones_like(maturities)
    L_slope = (1.0 - np.exp(-m_over_tau)) / m_over_tau
    L_curv = L_slope - np.exp(-m_over_tau)
    return L_level, L_slope, L_curv


def synthetic_panel(
    n_quarters: int,
    seed: int = 42,
    round_to: int | None = None,
    start: str = "1990-Q1",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate deterministic synthetic macro and yield DataFrames.

    Parameters
    ----------
    n_quarters : number of quarters to generate
    seed : RNG seed (deterministic output for the same seed)
    round_to : optional decimal rounding for human readability; pass None to
        keep full float precision (required for clean PCA round-trip tests)
    start : starting quarter as 'YYYY-Q#' string

    Returns
    -------
    (macro_df, yields_df) with a 'Quarter' string column in 'YYYY-Q#' format
    and human-readable headers matching config/default.yaml.
    """
    rng = np.random.default_rng(seed)

    start_period = pd.Period(start, freq="Q-DEC")
    quarters = pd.period_range(start=start_period, periods=n_quarters, freq="Q-DEC")
    quarter_strs = [f"{p.year}-Q{p.quarter}" for p in quarters]

    gdp = _ar1(n_quarters, mean=2.5, phi=0.5, sigma=1.0, init=4.2, rng=rng)
    cpi = _ar1(n_quarters, mean=3.0, phi=0.7, sigma=0.5, init=6.5, rng=rng)
    ffr = _ar1(n_quarters, mean=3.5, phi=0.9, sigma=0.3, init=8.25, rng=rng)

    level = _ar1(n_quarters, mean=5.0, phi=0.9, sigma=0.3, init=7.5, rng=rng)
    slope = _ar1(n_quarters, mean=-2.0, phi=0.85, sigma=0.4, init=-0.5, rng=rng)
    curv = _ar1(n_quarters, mean=0.0, phi=0.8, sigma=0.5, init=0.3, rng=rng)

    L_level, L_slope, L_curv = ns_loadings()
    yields = (
        level[:, None] * L_level[None, :]
        + slope[:, None] * L_slope[None, :]
        + curv[:, None] * L_curv[None, :]
    )

    if round_to is not None:
        gdp = np.round(gdp, round_to)
        cpi = np.round(cpi, round_to)
        ffr = np.round(ffr, round_to)
        yields = np.round(yields, round_to)

    macro_df = pd.DataFrame(
        {
            "Quarter": quarter_strs,
            MACRO_COLUMNS[0]: gdp,
            MACRO_COLUMNS[1]: cpi,
            MACRO_COLUMNS[2]: ffr,
        }
    )

    yields_df = pd.DataFrame(
        {
            "Quarter": quarter_strs,
            **{label: yields[:, i] for i, label in enumerate(MATURITY_LABELS)},
        }
    )

    return macro_df, yields_df
