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


def _spiked_dgp(seed: int, n: int = 300, m: int = 12, n_spikes: int = 8) -> np.ndarray:
    """The seasonal DGP with 8 well-separated ±8.0 spikes (~2.7% contamination
    — the AUD-S3 FROM-BELOW fixture). Fixture-direction record: the
    from-ABOVE direction (45 spikes > the default cap 30) is INFEASIBLE —
    15% contamination inflates the ESD MAD scale (masking) and ZERO anomalies
    are detected; the from-BELOW direction works — with the cap shrunk under
    the clean detection count (pct 0.01 -> cap 3; pct 0.02 -> cap 6), the
    emitted "Detected Anomalies" count EQUALS the cap exactly (probed:
    3/6/10 at pct .01/.02/.10), making the cap's effect observable on
    OUTPUT."""
    y = _seasonal_dgp(seed, n=n, m=m)
    rng = np.random.default_rng(seed + 1)
    idx = np.arange(20, n, 35)[:n_spikes]  # well-separated (no ESD swamping)
    y = y.copy()
    y[idx] += np.where(rng.standard_normal(n_spikes) > 0, 8.0, -8.0)
    return y


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
        return {"y": y, "y_spiked": _spiked_dgp(seed, n=self.DGP_N, m=self.DGP_M)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.stl_esd_anomaly as stl_mod  # type: ignore

        params = _stl_params()
        pct_default = next(
            p for p in params if p["name"] == "max_anomalies_pct"
        ).get("default")
        dialog_params = _dialog_default_params(params)

        def _run(y_arr, extra_params):
            p = dict(dialog_params)
            p.update(extra_params)
            ctx = RunContext({
                "run_id": "p3_stl_max_anomalies_cap",
                "technique_id": "stl_esd_anomaly",
                "preset": "Balanced",
                "seed": 42,
                "frequency": "M",
                "time": list(range(len(y_arr))),
                "series": [{"name": "y", "values": y_arr.tolist()}],
                "params": p,
            })
            resp = stl_mod.run(ctx, lambda *a, **kw: None)
            a = resp.get("audit_fields", {})
            # AUD-S3: count the EMITTED "Detected Anomalies" rows — the cap's
            # EFFECT on output (on the saturated fixture the count == cap).
            tbl = next((t for t in resp.get("tables", [])
                        if t.get("name") == "Detected Anomalies"), None)
            return {
                "status": resp.get("status"),
                "max_anomalies": a.get("max_anomalies"),
                "n_obs": a.get("n_obs"),
                "n_emitted": len((tbl or {}).get("rows", [])),
            }

        y = np.asarray(fixture["y"], dtype=np.float64)
        ys = np.asarray(fixture["y_spiked"], dtype=np.float64)
        return {
            "pct_default": pct_default,
            "clean": _run(y, {}),
            # the FROM-BELOW binding contrast: cap shrunk under the clean
            # detection count -> the emitted count == the cap exactly
            "spiked_low1": _run(ys, {"max_anomalies_pct": 0.01}),
            "spiked_low2": _run(ys, {"max_anomalies_pct": 0.02}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        frac = get_ladder(self.technique_id).get(
            "expected_max_anomalies_fraction", 0.10
        )
        return {"expected_fraction": float(frac)}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        # AUD-S3 upgrade (from-below binding contrast): the load-bearing
        # gates ride the EMITTED "Detected Anomalies" row counts with the cap
        # shrunk UNDER the fixture's clean detection count — the emitted
        # count must EQUAL the computed cap at two pct values (binding
        # visible; the knob moves output). The pct->cap mapping defect class
        # (the original catalog 10.0-vs-0.10 bug) FIRES these gates: a
        # percent-read cap clamps to n//2, unbinds, and the emitted count
        # reverts to the natural detection count != the expected cap. The
        # dialog-DEFAULT cap echo is cross-checked against the intended
        # fraction (link 1 of the two-link framing; at the default the cap
        # is unbinding on realistic data — ESD masking makes a from-above
        # binding fixture infeasible, see _spiked_dgp).
        frac = ref["expected_fraction"]
        s1, s2 = tsl["spiked_low1"], tsl["spiked_low2"]
        n_obs = s1.get("n_obs")
        cap1 = max(1, int(0.01 * n_obs)) if n_obs else None
        cap2 = max(1, int(0.02 * n_obs)) if n_obs else None
        cap_def = max(1, int(frac * n_obs)) if n_obs else None
        structural_max = (n_obs // 2) if n_obs else None

        bind_ok = (s1.get("n_emitted") == cap1)
        knob_ok = (s2.get("n_emitted") == cap2
                   and s1.get("n_emitted") != s2.get("n_emitted"))
        default_ok = (tsl["clean"].get("max_anomalies") == cap_def
                      and cap_def is not None and structural_max is not None
                      and cap_def < structural_max)
        cons_ok = (s1.get("max_anomalies") == cap1
                   and s2.get("max_anomalies") == cap2)
        primary = {
            "cap_binds_on_emitted_output": {
                "status": "PASS" if bind_ok else "BLOCK",
                "emitted_rows": s1.get("n_emitted"), "expected_cap": cap1,
                "note": ("pct=0.01 on the 8-spike fixture: the emitted "
                         "anomaly count must EQUAL the computed cap exactly "
                         "(the cap's effect, observable on output)"),
            },
            "pct_knob_moves_output": {
                "status": "PASS" if knob_ok else "BLOCK",
                "rows_at_0.01": s1.get("n_emitted"),
                "rows_at_0.02": s2.get("n_emitted"), "expected": cap2,
            },
            "default_cap_is_intended_fraction": {
                "status": "PASS" if default_ok else "BLOCK",
                "cap_echo_clean": tsl["clean"].get("max_anomalies"),
                "expected": cap_def, "structural_max_n_half": structural_max,
                "pct_default": tsl.get("pct_default"),
                "note": ("link 1 (pct -> computed cap): echo vs the intended "
                         "fraction; backed by the output-level binding proof "
                         "of the same mapping at pct .01/.02 above"),
            },
            "audit_echo_consistency": {
                "status": "PASS" if cons_ok else "BLOCK",
                "cap_echo_0.01": s1.get("max_anomalies"),
                "cap_echo_0.02": s2.get("max_anomalies"),
            },
        }
        statuses = [v["status"] for v in primary.values()]
        run_ok = all(tsl[k].get("status") == "success"
                     for k in ("clean", "spiked_low1", "spiked_low2"))
        outcome = "BLOCK" if (not run_ok or "BLOCK" in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "run_ok": run_ok,
                "pct_default": tsl.get("pct_default"),
                "n_obs": n_obs, "expected_caps": [cap1, cap2, cap_def],
                "structural_max": structural_max,
                "fixture_directions": ("from-above INFEASIBLE (ESD masking at "
                                       "15% contamination, 0 detected); "
                                       "from-below LANDS (3/6 binding)"),
            },
        )
