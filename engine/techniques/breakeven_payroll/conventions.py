"""Frozen, validated methodology conventions for breakeven-payrolls.

These constants encode the Phase-1-validated conventions. They are FROZEN: the
reconciliation harness and the production math BOTH import them, so the path the
tool produces is the path the reconciliation validates -- by construction.

Do NOT move these into params.yaml and do NOT round them. Changing any value here
changes the validated methodology and requires re-reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

QMMethod = Literal["ffill", "step", "linear", "cubic"]
QMAnchor = Literal["quarter_start", "quarter_mid", "quarter_end"]
MQAgg = Literal["mean", "last", "sum"]
EndpointPolicy = Literal["raw", "trailing"]


@dataclass(frozen=True)
class StitchSpec:
    """Frequency-stitching convention (quarterly <-> monthly) + smoother windows.

    qm_method / qm_anchor : how a quarterly series (potential LFPR, u*) maps onto
        the monthly grid.
    mq_agg : how a monthly series (breakeven) aggregates to quarterly.
    monthly_ma / quarterly_ma : centered moving-average window lengths.
    quarterly_ma_endpoint : how to fill the quarterly MA where a full centered
        window is unavailable -- "raw" uses the raw quarterly value (NOT a
        gap-spanning trailing average).
    """

    qm_method: QMMethod = "linear"
    qm_anchor: QMAnchor = "quarter_mid"
    mq_agg: MQAgg = "mean"
    monthly_ma: int = 13
    quarterly_ma: int = 5
    center: bool = True
    quarterly_ma_endpoint: EndpointPolicy = "raw"


# --- THE frozen convention (Phase-1 validated) -------------------------------
FROZEN_STITCH = StitchSpec(
    qm_method="linear",           # quarterly LFPR / u* -> monthly by linear interpolation
    qm_anchor="quarter_mid",      # ... anchored at the middle month of each quarter
    mq_agg="mean",                # monthly breakeven -> quarterly by mean
    monthly_ma=13,                # 13-month centered MA on the population LEVEL
    quarterly_ma=5,               # 5-quarter centered MA on quarterly breakeven
    center=True,
    quarterly_ma_endpoint="raw",  # raw quarterly endpoint where the centered-5 window is unavailable
)

# --- Population construction -------------------------------------------------
# Vintage joins splice on first differences at the moving-average boundary, NOT
# on levels, so the centered MA stays continuous across the seam.
POP_SPLICE = "diff_at_ma_boundary"

# Dec-2025 vintage-2025 CNI 16+ population base (thousands). The 2026 block is
# built STANDALONE off this base -- no chaining across the V2024->V2025 control seam.
V2025_BASE_THOUSANDS = 274585.0

# --- Scenario engine ---------------------------------------------------------
# Validated 2026 labor-force participation rate, in PERCENT. Scenario math uses
# LFPR26 / 100. Do NOT round to 0.625.
LFPR26 = 62.3954

__all__ = [
    "StitchSpec",
    "FROZEN_STITCH",
    "POP_SPLICE",
    "V2025_BASE_THOUSANDS",
    "LFPR26",
]
