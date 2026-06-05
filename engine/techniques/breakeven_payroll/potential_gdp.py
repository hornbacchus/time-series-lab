"""Figure-3 potential-GDP decomposition: potential employment vs productivity."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from .stitch import to_fraction

logger = logging.getLogger(__name__)


def potential_gdp_decomposition(
    potential_lf: pd.Series, u_star: pd.Series, potential_gdp: pd.Series
) -> pd.DataFrame:
    """Split potential-GDP growth into potential-employment and productivity parts.

        potential_employment      = potential_LF * (1 - u*)
        productivity_contribution = dlog(potential_GDP) - dlog(potential_employment)
    """
    lf = potential_lf.astype(float)
    us = to_fraction(u_star)
    gdp = potential_gdp.astype(float)
    idx = lf.index.intersection(us.index).intersection(gdp.index)
    lf, us, gdp = lf.reindex(idx), us.reindex(idx), gdp.reindex(idx)

    pot_emp = lf * (1.0 - us)
    dlog_gdp = np.log(gdp).diff()
    dlog_emp = np.log(pot_emp).diff()
    out = pd.DataFrame(
        {
            "potential_employment": pot_emp,
            "dlog_potential_gdp": dlog_gdp,
            "emp_contribution": dlog_emp,
            "productivity_contribution": dlog_gdp - dlog_emp,
        }
    )
    out.index.name = "quarter"
    return out
