"""Phase 1 defect #4 — stl_esd_anomaly max_anomalies_pct UNIT discrimination check.

The catalog exposed `max_anomalies_pct` with default 10.0, but the engine reads
it as a FRACTION (`max_anomalies = max(1, int(n * max_anomalies_pct))`,
stl_esd_anomaly.py:164). With 10.0 the cap is 10n, immediately clamped to the
structural max n_test//2 (line 175) -- so the "max anomalies" ceiling the user
thinks they set is silently DISABLED (up to half the series can be flagged).
The engine, its default (0.10), and the C# stub (0.10) all use the fraction
convention; the catalog 10.0 was the lone outlier. The fix: catalog default
10.0 -> 0.10 (+ honest "fraction" label/description).

The bug is LATENT in the flag count (ESD masking keeps the natural anomaly count
below the cap on realistic data), so the deterministic observable is the COMPUTED
CAP itself (now surfaced in audit_fields["max_anomalies"]). This check reads the
live catalog default, runs the engine on a clean fixture, and asserts the cap is
the intended 10% ceiling -- NOT the disabled structural max.

  PRE-fix  (catalog 10.0): cap = min(10n, n//2) = n//2  -> assertions FAIL -> BLOCK.
  POST-fix (catalog 0.10): cap = int(0.10 * n)          -> PASS.
"""

from __future__ import annotations

import json
import os
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", "..", ".."))
_CATALOG = os.path.join(_ROOT, "resources", "catalog", "techniques_catalog.json")


def _stl_params() -> list[dict]:
    with open(_CATALOG, encoding="utf-8") as f:
        cat = json.load(f)
    entries = cat if isinstance(cat, list) else next(
        v for v in cat.values()
        if isinstance(v, list) and v and isinstance(v[0], dict) and "id" in v[0]
    )
    entry = next(t for t in entries if t["id"] == "stl_esd_anomaly")
    return entry["parameters"]


def _dialog_default_params(params: list[dict]) -> dict[str, Any]:
    """Replicate the C# dialog emission rule: a null default is OMITTED;
    otherwise the typed default is sent."""
    out: dict[str, Any] = {}
    for p in params:
        d = p.get("default")
        if d is None:
            continue
        out[p["name"]] = d
    return out


def _seasonal_dgp(seed: int, n: int = 300, m: int = 12) -> np.ndarray:
    """Clean trend+seasonal+noise, NO NaN -> n_test == n. The check reads the
    cap (computed before detection), so anomaly content is irrelevant."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return 20.0 + 0.01 * t + 4.0 * np.sin(2 * np.pi * t / m) + rng.standard_normal(n) * 0.5


class StlMaxAnomaliesCapParity(P3ParityCheck):
    technique_id = "p3_stl_max_anomalies_cap"
    tier = "fast"
    fixture_id = ""
    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Catalog-default unit check for stl_esd_anomaly: the dialog-default "
        "max_anomalies_pct must produce the intended fraction-of-n cap, not the "
        "disabled structural max (n//2). Hard assertions on the engine's computed "
        "cap, not a numeric parity band."
    )
    DGP_N = 300
    DGP_M = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _seasonal_dgp(seed, n=self.DGP_N, m=self.DGP_M)
        return {"y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.stl_esd_anomaly as stl_mod  # type: ignore

        params = _stl_params()
        pct_default = next(
            p for p in params if p["name"] == "max_anomalies_pct"
        ).get("default")
        dialog_params = _dialog_default_params(params)

        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_stl_max_anomalies_cap",
            "technique_id": "stl_esd_anomaly",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "M",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": dialog_params,
        })
        resp = stl_mod.run(ctx, lambda *a, **kw: None)
        a = resp.get("audit_fields", {})
        return {
            "status": resp.get("status"),
            "pct_default": pct_default,
            "max_anomalies": a.get("max_anomalies"),
            "n_obs": a.get("n_obs"),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        frac = get_ladder(self.technique_id).get(
            "expected_max_anomalies_fraction", 0.10
        )
        return {"expected_fraction": float(frac)}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        n_obs = tsl.get("n_obs")
        cap = tsl.get("max_anomalies")
        frac = ref["expected_fraction"]
        expected_cap = max(1, int(frac * n_obs)) if n_obs else None
        structural_max = (n_obs // 2) if n_obs else None

        cap_ok = (cap is not None and expected_cap is not None
                  and cap == expected_cap)
        ceiling_real = (cap is not None and structural_max is not None
                        and cap < structural_max)
        primary = {
            "cap_is_intended_fraction": {
                "status": "PASS" if cap_ok else "BLOCK",
                "cap": cap, "expected": expected_cap,
                "pct_default": tsl.get("pct_default"),
            },
            "ceiling_not_disabled": {
                "status": "PASS" if ceiling_real else "BLOCK",
                "cap": cap, "structural_max_n_half": structural_max,
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
                "pct_default": tsl.get("pct_default"),
                "max_anomalies": cap, "n_obs": n_obs,
                "expected_cap": expected_cap, "structural_max": structural_max,
            },
        )
