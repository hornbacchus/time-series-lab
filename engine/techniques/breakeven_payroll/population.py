"""CNI 16+ population construction and the labor-force product-rule decomposition.

Frozen conventions (conventions.py):
  * 13-month centered MA on the population LEVEL.
  * Diff-splice at the MA boundary for vintage joins (not a level-splice).
  * 2026 standalone block off the V2025 base (274,585k), no V2024->V2025 chaining.
"""

from __future__ import annotations

import logging

import pandas as pd

from .conventions import V2025_BASE_THOUSANDS, StitchSpec
from .stitch import centered_ma, quarterly_to_monthly, to_fraction

logger = logging.getLogger(__name__)

_DEC_2025 = pd.Timestamp(2025, 12, 1)


def _as_series(obj, value_col: str = "value") -> pd.Series:
    if isinstance(obj, pd.Series):
        return obj
    df = obj.copy()
    if "date" in df.columns:
        df = df.set_index("date")
    col = value_col if value_col in df.columns else df.columns[-1]
    return df[col]


def build_population(
    hplfs: pd.DataFrame,
    cnp16ov: pd.DataFrame | pd.Series | None = None,
    *,
    monthly_change_thousands: float = 90.0,
    base_thousands: float = V2025_BASE_THOUSANDS,
    through: str = "2026-12",
) -> pd.DataFrame:
    """Construct the monthly CNI 16+ LEVEL (thousands).

    History + H1 2025 from HPLFS (pn16); Jun-Dec 2025 bridged via CNP16OV
    month-over-month changes (diff-splice from the last HPLFS month); 2026 as a
    standalone block anchored at the V2025 Dec-2025 base + ~90k/mo.
    """
    pop = hplfs["pn16"].astype(float).copy()
    pop.index = pd.DatetimeIndex(pop.index)
    last_hplfs = pop.index.max()

    # --- Jun-Dec 2025 bridge via CNP16OV diff-splice ---
    if cnp16ov is not None:
        cnp = _as_series(cnp16ov).astype(float)
        cnp.index = pd.DatetimeIndex(cnp.index)
        cnp_chg = cnp.diff()
        bridge_idx = pd.date_range(last_hplfs + pd.DateOffset(months=1), _DEC_2025, freq="MS")
        cur = float(pop.loc[last_hplfs])
        for m in bridge_idx:
            ch = cnp_chg.get(pd.Timestamp(m))
            if pd.notna(ch):
                cur = cur + float(ch)
                pop.loc[pd.Timestamp(m)] = cur

    # --- 2026 standalone block off the V2025 base (no seam chaining) ---
    pop.loc[_DEC_2025] = float(base_thousands)  # block anchor (V2025 Dec-2025 base)
    end = pd.Timestamp(through + "-01") if len(through) == 7 else pd.Timestamp(through)
    block_idx = pd.date_range(_DEC_2025 + pd.DateOffset(months=1), end, freq="MS")
    for k, m in enumerate(block_idx, start=1):
        pop.loc[pd.Timestamp(m)] = float(base_thousands) + monthly_change_thousands * k

    pop = pop.sort_index()
    # Continuous monthly index: linearly interpolate any interior gap (e.g. a month
    # absent from CNP16OV such as Oct-2025) so no month is dropped from a centered-MA
    # window or a quarterly aggregate.
    full_idx = pd.date_range(pop.index.min(), pop.index.max(), freq="MS")
    pop = pop.reindex(full_idx).interpolate(method="linear", limit_area="inside")
    pop.index.name = "date"
    return pop.to_frame("pop_level")


def potential_labor_force(
    pop_level: pd.DataFrame | pd.Series,
    pot_lfpr_quarterly: pd.Series,
    spec: StitchSpec,
    *,
    projection_start: str | pd.Timestamp | None = None,
    projection_flow: float | None = None,
) -> pd.DataFrame:
    """LF = (13-mo centered MA of CNI 16+ level) * (potential LFPR aligned to monthly).

    The 2026 standalone block must NOT be blended with the 2025 immigration surge by
    the centered MA. When ``projection_start`` is given, the population trend is the
    13-mo centered MA of the REAL data (strictly before that date), then projected
    forward at ``projection_flow`` (the scenario pace) -- so 2026 d_pop reflects the
    standalone-block flow, not a window reaching back into the 2025 surge.
    """
    level = _as_series(pop_level, "pop_level")
    if projection_start is not None:
        ps = pd.Timestamp(projection_start)
        real = level[level.index < ps]
        proj_idx = level.index[level.index >= ps]
        pop = centered_ma(real, spec.monthly_ma, center=spec.center, endpoint="raw")
        if len(proj_idx):
            flow = projection_flow
            if flow is None:
                flow = float(level.loc[proj_idx].diff().dropna().median())
            anchor = float(pop.iloc[-1])
            proj = pd.Series([anchor + flow * (k + 1) for k in range(len(proj_idx))], index=proj_idx)
            pop = pd.concat([pop, proj])
    else:
        pop = centered_ma(level, spec.monthly_ma, center=spec.center, endpoint="raw")
    # Interpolate LFPR on a CONTINUOUS monthly index (independent of population-index
    # gaps and the standalone 2026 block) so the 2025->2026 boundary slope is preserved,
    # then align to the population index.
    cont = pd.date_range(pop.index.min(), pop.index.max(), freq="MS")
    lfpr = quarterly_to_monthly(to_fraction(pot_lfpr_quarterly), cont, spec).reindex(pop.index)
    lf = pop * lfpr
    out = pd.DataFrame({"pop": pop, "lfpr": lfpr, "lf": lf})
    out.index.name = "date"
    return out


def delta_lf_decomposition(pop: pd.Series, lfpr: pd.Series) -> pd.DataFrame:
    """Exact product rule:

        d_pop = pop.diff(); d_lfpr = lfpr.diff()
        contrib_pop   = d_pop * lfpr
        contrib_lfpr  = d_lfpr * pop.shift(1)
        delta_lf      = contrib_pop + contrib_lfpr
    """
    pop = pop.astype(float)
    lfpr = lfpr.astype(float)
    d_pop = pop.diff()
    d_lfpr = lfpr.diff()
    contrib_pop = d_pop * lfpr
    contrib_lfpr = d_lfpr * pop.shift(1)
    delta_lf = contrib_pop + contrib_lfpr
    out = pd.DataFrame(
        {
            "d_pop": d_pop,
            "d_lfpr": d_lfpr,
            "contrib_pop": contrib_pop,
            "contrib_lfpr": contrib_lfpr,
            "delta_lf": delta_lf,
        }
    )
    out.index.name = "date"
    return out
