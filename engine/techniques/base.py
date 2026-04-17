"""
Base classes and helpers for Time Series Lab technique modules.

Every technique receives a RunContext and returns a dict matching the RunResponse schema.
"""

import datetime
import numpy as np


# Map human-readable frequency labels emitted by the C# TimeIndexDetector
# to the pandas-style short codes that every technique's _infer_period
# already understands. Unknown values pass through unchanged so that callers
# can still supply raw short codes like "M", "MS", "Q", "QS", "D", etc.
_FREQUENCY_ALIASES = {
    "calendardaily": "D",
    "businessdaily": "B",
    "daily": "D",
    "weekly": "W",
    "monthly": "M",
    "quarterly": "Q",
    "annual": "Y",
    "annually": "Y",
    "yearly": "Y",
}


def _normalize_frequency(raw: str) -> str:
    """Translate detector labels to pandas-style frequency codes."""
    if not raw:
        return ""
    key = str(raw).strip().lower()
    return _FREQUENCY_ALIASES.get(key, str(raw).strip())


class RunContext:
    """
    Encapsulates everything a technique needs to execute.

    Constructed from the JSON RunRequest sent by the C# add-in over Named Pipes.
    """

    def __init__(self, raw: dict):
        self.run_id: str = raw.get("run_id", "")
        self.technique_id: str = raw.get("technique_id", "")
        self.preset: str = raw.get("preset", "Balanced")
        self.seed: int = raw.get("seed", 42)
        # Normalize frequency: the C# TimeIndexDetector emits human-readable
        # labels ("Monthly", "Quarterly", "CalendarDaily", ...) but every
        # technique's _infer_period maps pandas-style short codes ("M", "Q",
        # "D", ...). Translate once here so all techniques work uniformly.
        self.frequency: str = _normalize_frequency(raw.get("frequency", ""))
        self.time: list = raw.get("time", [])
        self.series: list = raw.get("series", [])  # list of {name, values}
        self.exog: list = raw.get("exog", [])       # list of {name, values}
        self.params: dict = raw.get("params", {})
        self.fill_config: dict = raw.get("fill_config", {})
        self.resample_config: dict = raw.get("resample_config", {})

        # Normalize chronological order. Many of our sample CSVs and a
        # common Excel convention are "newest-first" (most recent row at
        # the top of the selection). Every technique's math assumes an
        # oldest-first order — so if we detect the input is descending
        # in time, flip both `time` and every series/exog values array
        # once up-front. Downstream code then never has to think about it.
        self._normalize_chronological_order()

    def _normalize_chronological_order(self) -> None:
        """If `self.time` is strictly descending, reverse it and every
        parallel series/exog values array in place. Leaves things alone
        if the order is already ascending, mixed, or unparseable."""
        if not self.time or len(self.time) < 2:
            return
        try:
            import datetime as _dt
            parsed = []
            for t in self.time:
                s = str(t)
                if "T" in s:
                    s = s.split("T", 1)[0]
                # Accept YYYY-MM-DD, YYYY/MM/DD, and common ISO variants
                s = s.replace("/", "-").replace("Z", "").strip()
                parsed.append(_dt.date.fromisoformat(s[:10]))
        except Exception:
            return  # unparseable — leave as-is
        n = len(parsed)
        # Count how many consecutive steps are ascending vs descending.
        asc = sum(1 for i in range(n - 1) if parsed[i] < parsed[i + 1])
        desc = sum(1 for i in range(n - 1) if parsed[i] > parsed[i + 1])
        # Only reverse if strictly / overwhelmingly descending. A few ties
        # or out-of-order rows are fine; we don't try to fully sort here.
        if desc > asc and desc >= 0.9 * (n - 1):
            self.time = list(reversed(self.time))
            for s in self.series or []:
                vals = s.get("values")
                if isinstance(vals, list):
                    s["values"] = list(reversed(vals))
            for s in self.exog or []:
                vals = s.get("values")
                if isinstance(vals, list):
                    s["values"] = list(reversed(vals))

    # ------------------------------------------------------------------
    # Series helpers
    # ------------------------------------------------------------------

    def get_series_by_name(self, name: str) -> np.ndarray:
        """Return the values array for a named series, or raise."""
        for s in self.series:
            if s.get("name") == name:
                return _to_float_array(s.get("values", []))
        raise ValueError(f"Series '{name}' not found. Available: {[s['name'] for s in self.series]}")

    def get_primary_series(self) -> tuple:
        """Return (name, values) for the first series."""
        if not self.series:
            raise ValueError("No series provided. Please select at least one data column.")
        s = self.series[0]
        return s.get("name", "Series1"), _to_float_array(s.get("values", []))

    def get_all_series(self) -> list:
        """Return list of (name, np.ndarray) for all series."""
        result = []
        for s in self.series:
            name = s.get("name", f"Series{len(result) + 1}")
            values = _to_float_array(s.get("values", []))
            result.append((name, values))
        return result

    def validate_min_series(self, n: int):
        """Raise if fewer than n series are present."""
        if len(self.series) < n:
            raise ValueError(
                f"This technique requires at least {n} series, but only "
                f"{len(self.series)} were provided. Please select more data columns."
            )

    def get_param(self, key: str, default=None):
        """Safely retrieve a technique parameter with a default."""
        return self.params.get(key, default)


# ======================================================================
# Output builders
# ======================================================================

def make_table(name: str, columns: list, rows: list) -> dict:
    """
    Build a single output table dict matching the OutputTable schema.

    Parameters
    ----------
    name : str
        Table name (e.g. "Decomposition", "Test Results").
    columns : list[str]
        Column header names.
    rows : list[list]
        Each inner list is one row of values. Values should be JSON-safe
        (str, int, float, bool, None). numpy types are converted.

    Returns
    -------
    dict with keys: name, columns, rows
    """
    safe_rows = []
    for row in rows:
        safe_row = [_json_safe(v) for v in row]
        safe_rows.append(safe_row)
    return {
        "name": name,
        "columns": list(columns),
        "rows": safe_rows,
    }


def make_response(
    ctx: RunContext,
    *,
    status: str = "success",
    tables: list = None,
    plain_english_summary: str = "",
    warnings: list = None,
    audit_fields: dict = None,
    charting_suggestions: str = "",
    artifacts: dict = None,
    error_message: str = None,
    error_fixes: list = None,
    engine_versions: dict = None,
) -> dict:
    """
    Build a RunResponse dict matching the C# RunResponse schema.

    This is the canonical way for techniques to return results.
    """
    if audit_fields is None:
        audit_fields = {}

    # Stamp standard audit fields
    audit_fields.setdefault("technique_id", ctx.technique_id)
    audit_fields.setdefault("preset", ctx.preset)
    audit_fields.setdefault("seed", ctx.seed)
    audit_fields.setdefault("n_observations", _count_obs(ctx))
    audit_fields.setdefault("timestamp_utc", datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")

    resp = {
        "run_id": ctx.run_id,
        "status": status,
        "plain_english_summary": plain_english_summary,
        "tables": tables or [],
        "artifacts": artifacts or {},
        "warnings": warnings or [],
        "audit_fields": audit_fields,
        "charting_suggestions": charting_suggestions,
    }

    if engine_versions:
        resp["engine_versions"] = engine_versions

    if error_message:
        resp["error_message"] = error_message
    if error_fixes:
        resp["error_fixes"] = error_fixes

    return resp


def make_error_response(
    ctx: RunContext,
    error_message: str,
    error_fixes: list = None,
    warnings: list = None,
    engine_versions: dict = None,
) -> dict:
    """Convenience: build a failure RunResponse."""
    return make_response(
        ctx,
        status="failure",
        error_message=error_message,
        error_fixes=error_fixes or [],
        warnings=warnings or [],
        engine_versions=engine_versions,
    )


# ======================================================================
# Internal helpers
# ======================================================================

def _to_float_array(values: list) -> np.ndarray:
    """
    Convert a list of nullable doubles to a numpy float64 array.

    None / null values become np.nan.
    """
    out = np.empty(len(values), dtype=np.float64)
    for i, v in enumerate(values):
        if v is None:
            out[i] = np.nan
        else:
            try:
                out[i] = float(v)
            except (TypeError, ValueError):
                out[i] = np.nan
    return out


def _json_safe(v):
    """Convert numpy scalars to Python native types for JSON serialisation."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    return v


def _count_obs(ctx: RunContext) -> int:
    """Count observations from first series or time array."""
    if ctx.series:
        vals = ctx.series[0].get("values", [])
        return len(vals)
    return len(ctx.time)


def dropna_aligned(*arrays):
    """
    Drop rows where ANY of the input arrays has NaN.
    Returns a tuple of cleaned arrays (same order).
    """
    mask = np.ones(len(arrays[0]), dtype=bool)
    for a in arrays:
        mask &= ~np.isnan(a)
    return tuple(a[mask] for a in arrays)
