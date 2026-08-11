"""CBO gross-migration derivation — TEMPLATE-FED adaptation of the standalone
repo's migration.py (@ 99c03ba, preset-only re-port).

The standalone derives net migration from the committed 96k-row pub-61879 CSV;
the TSL port has no filesystem data dependency (workbook_input conventions),
so it consumes the `gross_migration_sums` tab instead — the standalone's OWN
groupby output baked at full float precision, which reproduces the derivation
bit-for-bit (u16 + 16plus == all-ages exactly; age -1 counts in u16).
"""
from __future__ import annotations

import pandas as pd


def derived_preset_from_sums(gm_sums: pd.DataFrame, year: int = 2026) -> float:
    """The CBO_Feb2026 preset value: all-ages net migration for ``year`` from
    the sums tab (sum of both age buckets, immigration - emigration, across
    all statuses)."""
    d = gm_sums[gm_sums["year"] == year]
    imm = float(d.loc[d["migration_flow"] == "immigration", "people"].sum())
    emi = float(d.loc[d["migration_flow"] == "emigration", "people"].sum())
    return imm - emi


def net_16plus_from_sums(gm_sums: pd.DataFrame, year: int = 2026) -> float:
    """16+ net migration (diagnostic; the engine's share_16plus scalar stays
    the surprise-flow-basis 0.91 — see the standalone's CFL-525 audit note)."""
    d = gm_sums[(gm_sums["year"] == year) & (gm_sums["bucket"] == "16plus")]
    imm = float(d.loc[d["migration_flow"] == "immigration", "people"].sum())
    emi = float(d.loc[d["migration_flow"] == "emigration", "people"].sum())
    return imm - emi
