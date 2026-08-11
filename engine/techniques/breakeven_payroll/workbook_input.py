"""Workbook-read layer — the core of the TSL port.

The standalone repo acquired its inputs from live/cached sources (acquire.py +
fred_client + vintage). The TSL technique instead reads them from the smoke-tested
10-tab Breakeven_Payrolls_Template.xlsx, producing the SAME structures the repo's
fetchers produced, so the ported math (population/breakeven/scenarios) runs unchanged.

Verified template contract (Breakeven_Payrolls_Template.xlsx):
  * Data tabs put the HEADER on ROW 4 (rows 1-2 = title/description, row 3 blank).
  * cbo_annual.date = integer year; cbo_quarterly.date = text 'YYYYqN'.
  * population_monthly: baked HPLFS region (1960->2025-05) + a separator row
    ("↓ APPEND ...") + a yellow CNP16OV append region (2025-06 onward). Filter to
    rows whose year & month are integers; split on source_segment.
  * fred_cnp16ov append values are blank where FRED has a gap (Oct-2025): blank !=
    error — build_population interpolates the interior gap.
  * scenario_inputs / scalars / _meta are key-value tabs (scan column A for a key).

Per the D1 ruling, the PATH's u*/LFPR come from cbo_quarterly (data-derived in both
repos); the SCENARIO-GRID scalars (u* 0.044 / 0.0456, LFPR26 62.3954, census base /
pace) are the repo's FROZEN LITERALS (assembled in _dispatch), NOT recomputed from
cbo_annual. cbo_annual is provenance/display only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_HEADER_ROW = 4  # 1-based Excel row of the header on the data tabs


def _to_quarter_index(series: pd.Series) -> pd.PeriodIndex:
    """'1949q1' / '1949Q1' -> quarterly PeriodIndex (mirrors the source parser)."""
    s = series.astype(str).str.strip().str.upper()
    return pd.PeriodIndex(s.str.replace(".", "Q", regex=False), freq="Q")


def _match_col(columns, prefix: str):
    """First column whose name starts with ``prefix`` (case-insensitive)."""
    pl = prefix.lower()
    for c in columns:
        if str(c).strip().lower().startswith(pl):
            return c
    return None


def _kv_scan(xlsx_path: str | Path, sheet: str) -> dict:
    """Read a key-value tab: column A = key, column B = value. Robust to the
    header-row offset (we just scan every row's first two cells)."""
    import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb[sheet]
    out: dict = {}
    for row in ws.iter_rows(values_only=True):
        if not row:
            continue
        key = row[0]
        if isinstance(key, str) and key.strip():
            val = row[1] if len(row) > 1 else None
            out.setdefault(key.strip(), val)
    wb.close()
    return out


def read_cbo_quarterly(xlsx_path: str | Path) -> dict[str, pd.Series]:
    """potential_lfpr + u_star (= noncyclical unemployment) quarterly series,
    indexed by quarterly Period. Both in PERCENT (the math's to_fraction handles it)."""
    df = pd.read_excel(xlsx_path, sheet_name="cbo_quarterly", header=_HEADER_ROW - 1)
    date_col = _match_col(df.columns, "date") or df.columns[0]
    lfpr_col = _match_col(df.columns, "potential_lfpr")
    ustar_col = _match_col(df.columns, "noncyclical")
    if lfpr_col is None or ustar_col is None:
        raise ValueError(
            f"cbo_quarterly missing potential_lfpr/noncyclical columns; got {list(df.columns)}"
        )
    df = df.dropna(subset=[date_col])
    qidx = _to_quarter_index(df[date_col])
    lfpr = pd.Series(pd.to_numeric(df[lfpr_col], errors="coerce").values, index=qidx, name="potential_lfpr")
    ustar = pd.Series(pd.to_numeric(df[ustar_col], errors="coerce").values, index=qidx, name="u_star")
    lfpr.index.name = ustar.index.name = "quarter"
    return {"potential_lfpr": lfpr.sort_index(), "u_star": ustar.sort_index()}


def read_population(xlsx_path: str | Path) -> dict:
    """Split population_monthly into the baked HPLFS frame and the CNP16OV append
    series. Filters to integer (year, month) rows (skips the separator); blank pn16
    cells (the Oct-2025 gap, the unfilled 2026 tail) are simply absent from the
    series — build_population interpolates interior gaps."""
    df = pd.read_excel(xlsx_path, sheet_name="population_monthly", header=_HEADER_ROW - 1)
    cols = {str(c).strip().lower(): c for c in df.columns}
    y_col = _match_col(df.columns, "year")
    m_col = _match_col(df.columns, "month")
    pn_col = _match_col(df.columns, "pn16")
    seg_col = _match_col(df.columns, "source_segment")
    if any(c is None for c in (y_col, m_col, pn_col)):
        raise ValueError(f"population_monthly missing year/month/pn16; got {list(df.columns)}")

    y = pd.to_numeric(df[y_col], errors="coerce")
    m = pd.to_numeric(df[m_col], errors="coerce")
    keep = y.notna() & m.notna()  # drops the "↓ APPEND ..." separator + any title bleed
    df = df[keep].copy()
    df["_date"] = pd.to_datetime(
        dict(year=y[keep].astype(int), month=m[keep].astype(int), day=1)
    )
    df["_pn16"] = pd.to_numeric(df[pn_col], errors="coerce")
    seg = df[seg_col].astype(str).str.lower() if seg_col is not None else pd.Series("", index=df.index)

    is_cnp = seg.str.startswith("fred_cnp16ov")
    hplfs_df = df[~is_cnp].dropna(subset=["_pn16"])
    cnp_df = df[is_cnp].dropna(subset=["_pn16"])

    hplfs = pd.DataFrame({"pn16": hplfs_df["_pn16"].astype(float).values},
                         index=pd.DatetimeIndex(hplfs_df["_date"].values, name="date")).sort_index()
    cnp = pd.Series(cnp_df["_pn16"].astype(float).values,
                    index=pd.DatetimeIndex(cnp_df["_date"].values, name="date"), name="cnp16ov").sort_index()
    return {"hplfs": hplfs, "cnp16ov": (cnp if len(cnp) else None)}


def read_gross_migration_sums(xlsx_path: str | Path):
    """Read the v2 `gross_migration_sums` tab (year x status x flow x
    age-bucket people sums, baked from the standalone repo's groupby — see
    the re-port record). TOLERANT: absent tab (a v1 workbook) -> None, so
    pre-re-port working copies keep running."""
    try:
        df = pd.read_excel(str(xlsx_path), sheet_name="gross_migration_sums",
                           header=_HEADER_ROW - 1)
    except (KeyError, ValueError):
        return None
    need = {"year", "immigration_status", "migration_flow", "bucket", "people"}
    if not need <= set(df.columns):
        return None
    return df[list(need)].dropna(subset=["year", "people"])


def read_workbook(xlsx_path: str | Path) -> dict:
    """Read everything the dispatch needs from the 10-tab template."""
    xlsx_path = str(xlsx_path)
    pop = read_population(xlsx_path)
    cbo = read_cbo_quarterly(xlsx_path)
    scalars = _kv_scan(xlsx_path, "scalars")
    scen = _kv_scan(xlsx_path, "scenario_inputs")
    meta = _kv_scan(xlsx_path, "_meta")
    gm_sums = read_gross_migration_sums(xlsx_path)

    def _num(d, key, default=None):
        v = d.get(key)
        try:
            return float(v)
        except (TypeError, ValueError):
            return default

    return {
        "hplfs": pop["hplfs"],
        "cnp16ov": pop["cnp16ov"],
        "potential_lfpr": cbo["potential_lfpr"],
        "u_star": cbo["u_star"],
        "scalars": {
            "pop_base_v2025_dec2025": _num(scalars, "pop_base_v2025_dec2025", 274585.0),
            "ces_se_monthly_nfp_change": _num(scalars, "ces_se_monthly_nfp_change", 61.3),
            "share_16plus": _num(scalars, "share_16plus", 0.91),
            "census_base_pace": _num(scalars, "census_base_pace", 90.0),
            "census_migration_ref": _num(scalars, "census_migration_ref", 320000.0),
        },
        "scenario": {
            "net_migration_all_ages": _num(scen, "net_migration_all_ages", -370000.0),
            "ustar_basis": (scen.get("ustar_basis") or "noncyclical"),
            "last_realized_month": scen.get("last_realized_month"),
        },
        "meta": meta,
        "gross_migration_sums": gm_sums,
    }
