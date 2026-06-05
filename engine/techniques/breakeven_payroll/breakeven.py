"""Core breakeven identity + quarterly 5-quarter centered MA.

Units: population in thousands -> breakeven in thousands of jobs/month. Convert to
persons (x1000) only at the reconciliation / fixture boundary.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from .conventions import StitchSpec
from .population import delta_lf_decomposition, potential_labor_force
from .stitch import centered_ma, monthly_to_quarterly, quarterly_to_monthly, to_fraction

logger = logging.getLogger(__name__)


@dataclass
class BreakevenResult:
    monthly: pd.Series                              # monthly breakeven (thousands/mo)
    quarterly: pd.DataFrame                         # breakeven, breakeven_smoothed (thousands/mo)
    decomposition: pd.DataFrame = field(default_factory=pd.DataFrame)


def breakeven(
    delta_lf: pd.Series, u_star_quarterly: pd.Series, spec: StitchSpec, *, projection_start=None
) -> BreakevenResult:
    """be = delta_lf * (1 - u*); aggregate to quarterly; 5-quarter centered MA.

    The 2026 standalone block is shown raw (not 5q-smoothed across the 2025 boundary):
    when ``projection_start`` is given, quarters at/after it use the raw quarterly
    breakeven instead of the centered MA (which would otherwise blend the high 2025 surge).
    """
    # u* interpolated on a continuous monthly index (continuous through 2025->2026),
    # then aligned to the decomposition index.
    cont = pd.date_range(delta_lf.index.min(), delta_lf.index.max(), freq="MS")
    u_star_m = quarterly_to_monthly(to_fraction(u_star_quarterly), cont, spec).reindex(delta_lf.index)
    be_m = (delta_lf * (1.0 - u_star_m)).rename("breakeven")
    be_q = monthly_to_quarterly(be_m, spec)
    be_q_smooth = centered_ma(
        be_q, spec.quarterly_ma, center=spec.center, endpoint=spec.quarterly_ma_endpoint
    )
    if projection_start is not None:
        pp = pd.Period(pd.Timestamp(projection_start), freq="Q")
        mask = be_q_smooth.index >= pp
        be_q_smooth[mask] = be_q[mask]
    q = pd.DataFrame({"breakeven": be_q, "breakeven_smoothed": be_q_smooth})
    q.index.name = "quarter"
    return BreakevenResult(monthly=be_m, quarterly=q)


def breakeven_from_inputs(
    pop_level, pot_lfpr_quarterly: pd.Series, u_star_quarterly: pd.Series, spec: StitchSpec,
    *, projection_start=None, projection_flow=None,
) -> BreakevenResult:
    """End-to-end: population level -> LF -> product-rule decomposition -> breakeven."""
    lf = potential_labor_force(
        pop_level, pot_lfpr_quarterly, spec,
        projection_start=projection_start, projection_flow=projection_flow,
    )
    dec = delta_lf_decomposition(lf["pop"], lf["lfpr"])
    res = breakeven(dec["delta_lf"], u_star_quarterly, spec, projection_start=projection_start)
    res.decomposition = dec
    return res
