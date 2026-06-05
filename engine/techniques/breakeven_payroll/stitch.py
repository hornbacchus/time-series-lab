"""Frequency-stitching helpers (the FROZEN convention's single injection point).

Both production (breakeven.py) and reconciliation call these, so the reconciled
convention IS the production convention. Behaviour is driven by a StitchSpec.
"""

from __future__ import annotations

import logging

import pandas as pd

from .conventions import StitchSpec

logger = logging.getLogger(__name__)


def to_fraction(s: pd.Series) -> pd.Series:
    """Coerce a rate to a 0-1 fraction (divide by 100 if it looks like a percent)."""
    s = s.astype(float)
    med = s.dropna().abs().median()
    if med is not None and med > 1.5:
        return s / 100.0
    return s


def _anchor_month(period: pd.Period, anchor: str) -> pd.Timestamp:
    start = pd.Timestamp(period.start_time.year, period.start_time.month, 1)
    off = {"quarter_start": 0, "quarter_mid": 1, "quarter_end": 2}.get(anchor, 1)
    m = start + pd.DateOffset(months=off)
    return pd.Timestamp(m.year, m.month, 1)


def quarterly_to_monthly(
    q: pd.Series, monthly_index: pd.DatetimeIndex, spec: StitchSpec
) -> pd.Series:
    """Map a quarterly series onto a monthly grid per spec.qm_method/qm_anchor."""
    q = q.dropna()
    if q.empty:
        return pd.Series(index=monthly_index, dtype=float)
    periods = q.index if isinstance(q.index, pd.PeriodIndex) else pd.PeriodIndex(q.index, freq="Q")
    anchors = pd.DatetimeIndex([_anchor_month(p, spec.qm_anchor) for p in periods])
    anchored = pd.Series(q.values, index=anchors).sort_index()
    anchored = anchored[~anchored.index.duplicated(keep="last")]

    full = anchored.index.union(monthly_index)
    s = anchored.reindex(full)
    if spec.qm_method == "linear":
        s = s.interpolate(method="time")
    elif spec.qm_method == "cubic" and len(anchored) >= 4:
        try:
            s = s.interpolate(method="cubicspline")
        except Exception:
            s = s.interpolate(method="time")
    else:  # ffill / step
        s = s.ffill()
    s = s.ffill().bfill()  # hold last/first outside the anchor range
    return s.reindex(monthly_index)


def monthly_to_quarterly(m: pd.Series, spec: StitchSpec) -> pd.Series:
    """Aggregate a monthly series to quarterly per spec.mq_agg."""
    m = m.dropna()
    if m.empty:
        return pd.Series(dtype=float)
    pidx = m.index.to_period("Q")
    grouped = m.groupby(pidx)
    if spec.mq_agg == "last":
        out = grouped.last()
    elif spec.mq_agg == "sum":
        out = grouped.sum()
    else:
        out = grouped.mean()
    out.index.name = "quarter"
    return out


def centered_ma(s: pd.Series, window: int, *, center: bool = True, endpoint: str = "strict") -> pd.Series:
    """Centered moving average.

    endpoint:
      - "strict"  : NaN where a full window is unavailable.
      - "raw"     : fill those positions with the raw series value (frozen
                    convention for the quarterly breakeven MA -- NOT a trailing avg).
      - "shrink"  : fill with a partial (min_periods=1) centered mean.
    """
    base = s.rolling(window, center=center, min_periods=window).mean()
    if endpoint == "raw":
        return base.where(base.notna(), s)
    if endpoint in ("shrink", "trailing"):
        partial = s.rolling(window, center=center, min_periods=1).mean()
        return base.where(base.notna(), partial)
    return base
