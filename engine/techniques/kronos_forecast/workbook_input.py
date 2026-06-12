"""Workbook-read layer for the Kronos Forecast template (kronos_input sheet).

Template contract (built by tools/make_kronos_template.py; the bundled copy
lives in resources/templates/):
  * The EXPERIMENTAL status block occupies the top rows (display only).
  * Parameters are key-value pairs scanned from column A (key) / column B
    (value): lookback_L, horizon_H, paths_M, seed, show_raw_ohlc, T, top_p.
    T/top_p are DISPLAY-ONLY (the characterized sampling config 0.6/0.90);
    edited values are ignored with a warning, never honored.
  * The data block starts at the row whose column-A cell is "Date":
    Date | Open | High | Low | Close | Volume, read until the first blank
    Date. Volume may be blank (zero-filled -- the validated FX path).

Validation (the brief's SS3, exactly):
  * < 120 data rows -> friendly error.
  * non-numeric or <= 0 prices -> error (NaNs in price columns would RAISE
    inside upstream; zero/negative prices are economically invalid input).
  * H > 25 or M > 50 -> clamped with a note; L clamped into
    [120, min(250, n_rows)] with a note.
"""

from __future__ import annotations

import datetime as _dt

import pandas as pd

H_CAP = 25
M_CAP = 50
L_MIN, L_MAX = 120, 250

_PARAM_KEYS = ("lookback_L", "horizon_H", "paths_M", "seed",
               "show_raw_ohlc", "T", "top_p")


class TemplateError(ValueError):
    """A friendly, user-actionable template problem."""


def read_workbook(path: str) -> dict:
    """Read the kronos_input sheet -> {params, clamp_notes, df}."""
    try:
        raw = pd.read_excel(path, sheet_name="kronos_input", header=None,
                            engine="openpyxl")
    except ValueError as e:
        raise TemplateError(
            "The workbook has no 'kronos_input' sheet. Use 'Open Input "
            "Template' to get the Kronos Forecast template.") from e

    colA = raw.iloc[:, 0].astype(str).str.strip()

    params: dict = {}
    for key in _PARAM_KEYS:
        hits = colA[colA == key].index
        if len(hits):
            params[key] = raw.iat[hits[0], 1]

    hdr_rows = colA[colA == "Date"].index
    if not len(hdr_rows):
        raise TemplateError("No 'Date' header row found on kronos_input.")
    h = hdr_rows[0]
    df = raw.iloc[h + 1:, 0:6].copy()
    df.columns = ["timestamps", "open", "high", "low", "close", "volume"]
    # The data block ends at the FIRST blank Date -- footer notes may sit
    # below it; never sweep them in.
    df = df.reset_index(drop=True)
    blanks = df.index[df["timestamps"].isna()]
    if len(blanks):
        df = df.iloc[:blanks[0]]
    df = df.reset_index(drop=True)

    if len(df) < L_MIN:
        raise TemplateError(
            f"Only {len(df)} data rows found -- Kronos needs at least "
            f"{L_MIN} rows of OHLC history (the minimum lookback). Paste a "
            f"longer series into the Date/Open/High/Low/Close block.")

    df["timestamps"] = pd.to_datetime(df["timestamps"])
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
        if df[c].isna().any():
            raise TemplateError(
                f"Non-numeric value(s) in the '{c.title()}' column. Every "
                f"price cell must be a positive number.")
        if (df[c] <= 0).any():
            raise TemplateError(
                f"Zero/negative value(s) in the '{c.title()}' column -- "
                f"prices must be positive.")
    # Volume: blank -> 0 (the validated FX path; upstream zero-fills anyway).
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0.0)
    if not df["timestamps"].is_monotonic_increasing:
        df = df.sort_values("timestamps").reset_index(drop=True)

    clamp_notes: list[str] = []

    def _int(key, default):
        v = params.get(key, default)
        try:
            return int(float(v))
        except (TypeError, ValueError):
            clamp_notes.append(f"{key} '{v}' not numeric -- default {default} used.")
            return default

    L = _int("lookback_L", 120)
    H = _int("horizon_H", 10)
    M = _int("paths_M", 10)
    seed = _int("seed", 9000)

    l_hi = min(L_MAX, len(df))
    if L < L_MIN or L > l_hi:
        clamped = min(max(L, L_MIN), l_hi)
        clamp_notes.append(f"lookback_L {L} outside [{L_MIN}, {l_hi}] -- clamped to {clamped}.")
        L = clamped
    if H > H_CAP:
        clamp_notes.append(
            f"horizon_H {H} exceeds the tested envelope -- clamped to {H_CAP} "
            f"trading days (beyond it is unexplored and compounding-degraded).")
        H = H_CAP
    if H < 1:
        clamp_notes.append("horizon_H < 1 -- set to 1.")
        H = 1
    if M > M_CAP:
        clamp_notes.append(f"paths_M {M} exceeds the cap -- clamped to {M_CAP} "
                           f"(latency is roughly linear in M).")
        M = M_CAP
    if M < 1:
        clamp_notes.append("paths_M < 1 -- set to 1.")
        M = 1

    # T / top_p are display-only constants; an edited value is ignored.
    for key, fixed in (("T", 0.6), ("top_p", 0.90)):
        v = params.get(key)
        try:
            if v is not None and abs(float(v) - fixed) > 1e-9:
                clamp_notes.append(
                    f"{key}={v} edited but {key} is a display-only constant "
                    f"(fixed {fixed}, the characterized sampling config) -- ignored.")
        except (TypeError, ValueError):
            pass

    show_raw = str(params.get("show_raw_ohlc", "")).strip().lower() in ("true", "1", "yes")

    return {"df": df, "L": L, "H": H, "M": M, "seed": seed,
            "show_raw_ohlc": show_raw, "clamp_notes": clamp_notes,
            "read_stamp": _dt.datetime.now().isoformat(timespec="seconds")}
