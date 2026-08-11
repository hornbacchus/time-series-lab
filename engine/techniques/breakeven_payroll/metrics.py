"""Anchor-metric helpers — extracted VERBATIM from the source repo's reconcile.py
(99c03ba; unchanged since 826d1d0) so the TSL port computes the 6 reconciliation anchors exactly as the
authoritative pipeline does. No math change; only the acquisition-coupled
orchestration (rebuild_path / run_reconciliation) is omitted (the TSL dispatch
reconstructs the path from the workbook instead of live fetchers).
"""

from __future__ import annotations

import pandas as pd


def to_period(s) -> pd.Period:
    # Accept "1970-Q1", "1970Q1", or "1970-01"-style labels.
    return pd.Period(str(s).replace("-Q", "Q"), freq="Q")


def iter_targets(targets: dict) -> list[dict]:
    t = targets.get("targets", {})
    return list(t.get("decade_averages", [])) + list(t.get("points", []))


def scope(t: dict) -> str:
    return f"{t['window'][0]}..{t['window'][1]}" if "window" in t else t.get("period", "")


def metric_value(qp: pd.Series, t: dict) -> float:
    """Mean over a window, or a single-quarter point value, from a quarter-indexed
    Series ``qp`` (PeriodIndex, persons/month)."""
    if "window" in t:
        a, b = t["window"]
        mask = (qp.index >= to_period(a)) & (qp.index <= to_period(b))
        seg = qp[mask]
        return float(seg.mean()) if len(seg) else float("nan")
    p = to_period(t["period"])
    return float(qp.loc[p]) if p in qp.index else float("nan")
