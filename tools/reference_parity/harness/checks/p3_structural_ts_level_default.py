"""Phase 1 defect #2 — structural_ts dialog-default QUALITY discrimination check.

structural_ts's catalog `level` was a `bool` (default `true`) while the engine
reads `level` as a STRING spec; the dialog-default `level=true` produced a
DEGENERATE but successful model (RMSE ~1210, NO Trend component). This is a
SILENT quality degradation -- the run succeeds, so default_path_integrity (a
crash-only sweep) cannot see it. This check asserts the structural_ts
dialog-default parameter set produces the WORKING decomposition.

It READS the structural_ts catalog default for `level` and builds the dialog
parameter set per the C# emission rule (the same rule default_path_integrity
documents), then runs the engine and asserts:
  1. the catalog `level` default is a STRING spec (not a bool) -- guards against
     a regression of the default back to the broken bool;
  2. the Trend component is PRESENT (the degenerate path dropped it);
  3. RMSE is non-degenerate (<= 300; the degenerate value was ~1210, the working
     value ~69 on this fixture).

Discriminating by construction: PRE-fix (level=true bool) -> string-assert FAIL,
no Trend, RMSE ~1210 -> BLOCK; POST-fix (level="local linear trend") -> all
three PASS.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CATALOG = os.path.join(_ROOT, "resources", "catalog", "techniques_catalog.json")


def _structural_ts_params() -> list[dict]:
    with open(_CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    entries = cat if isinstance(cat, list) else next(
        v for v in cat.values()
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]
    )
    entry = next(t for t in entries if t["id"] == "structural_ts")
    return entry["parameters"]


def _dialog_default_params(params: list[dict]) -> dict[str, Any]:
    """Replicate the C# dialog emission rule: a null default is OMITTED;
    bool -> bool; int/float/string -> the typed default."""
    out: dict[str, Any] = {}
    for p in params:
        d = p.get("default")
        if d is None:
            continue  # null default -> key omitted (engine uses its own default)
        out[p["name"]] = d
    return out


def _trend_seasonal_dgp(seed: int, n: int = 150, m: int = 12) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    level = 50.0 + 0.4 * t
    seasonal = 8.0 * np.sin(2 * np.pi * t / m)
    return level + seasonal + rng.standard_normal(n) * 1.5


class StructuralTsLevelDefaultParity(P3ParityCheck):
    technique_id = "p3_structural_ts_level_default"
    tier = "fast"
    fixture_id = ""
    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Catalog-default integrity check for structural_ts: the dialog-default "
        "level spec must yield a non-degenerate unobserved-components fit (Trend "
        "component present, RMSE non-degenerate). Hard assertions on the "
        "engine's MLE output, not a numeric parity band."
    )
    DGP_N = 150
    DGP_M = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _trend_seasonal_dgp(seed, n=self.DGP_N, m=self.DGP_M)
        return {"y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.structural_ts as sts_mod  # type: ignore

        params = _structural_ts_params()
        level_default = next(p for p in params if p["name"] == "level").get("default")
        dialog_params = _dialog_default_params(params)

        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_structural_ts_level_default",
            "technique_id": "structural_ts",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "M",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": dialog_params,
        })
        resp = sts_mod.run(ctx, lambda *a, **kw: None)
        a = resp.get("audit_fields", {})
        components = a.get("components") or []
        pe = resp.get("plain_english_summary", "")
        rm = re.search(r"RMSE\s*=\s*(\d+\.?\d*)", pe)
        return {
            "status": resp.get("status"),
            "level_default": level_default,
            "level_default_is_string": isinstance(level_default, str),
            "trend_present": "Trend" in components,
            "rmse": float(rm.group(1)) if rm else None,
            "components": list(components),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        band = get_ladder(self.technique_id).get("rmse_degenerate_band", 300.0)
        return {"trend_present": True, "rmse_max": float(band),
                "level_default_is_string": True}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        rmse = tsl.get("rmse")
        primary = {
            "level_default_is_string": {
                "status": "PASS" if tsl["level_default_is_string"] else "BLOCK",
                "level_default": tsl["level_default"],
            },
            "trend_component_present": {
                "status": "PASS" if tsl["trend_present"] else "BLOCK",
                "components": tsl["components"],
            },
            "rmse_non_degenerate": {
                "status": ("PASS" if (rmse is not None and rmse <= ref["rmse_max"])
                           else "BLOCK"),
                "rmse": rmse, "rmse_max": ref["rmse_max"],
            },
        }
        statuses = [v["status"] for v in primary.values()]
        run_ok = tsl.get("status") == "success"
        outcome = "BLOCK" if (not run_ok or "BLOCK" in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "run_status": tsl.get("status"),
                "level_default": tsl["level_default"],
                "components": tsl["components"],
                "rmse": rmse,
            },
        )
