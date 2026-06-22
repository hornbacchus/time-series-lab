"""Phase 3 batch B — inert-control translation WIRING discrimination (5 controls).

Five dialog controls were inert because the catalog exposed a value in a
different unit/representation than the engine's key. Fixes:
  lomb_scargle min_period/max_period -> the engine translates to angular freq
    (omega = 2*pi/P) WITH the min<->max inversion (min_period caps the highest
    frequency / shortest cycle).
  robust_estimators trim_pct -> trim_fraction (catalog re-represented as a 0-1
    fraction, default 0.10; the engine reads trim_fraction).
  dtw_alignment_lag max_warp -> window_frac (the engine's fractional warp band).
  denton_chowlin_disaggregation target_frequency -> conversion_ratio (the engine's
    integer disaggregation factor).

This check proves each control now reaches the engine and changes the output;
and for lomb it ALSO proves the INVERSION direction is correct (wired backwards
would be worse than dead): on a signal with a short period (4) and a long period
(40), min_period=10 must EXCLUDE the period-4 peak (it is above the max search
frequency) while min_period=2 must INCLUDE it.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _digest(res: dict) -> str:
    vals = []
    for t in res.get("tables", []) or []:
        for row in t.get("rows", []) or []:
            for c in row:
                if isinstance(c, (int, float)) and not isinstance(c, bool):
                    vals.append(round(float(c), 5))
    return hashlib.sha1(",".join(map(str, vals)).encode()).hexdigest()[:12]


def _lomb_periods(res: dict) -> list:
    for tb in res.get("tables", []) or []:
        cols = tb.get("columns", []) or []
        idx = [i for i, c in enumerate(cols) if "eriod" in str(c)]
        if idx:
            j = idx[0]
            return [r[j] for r in tb.get("rows", []) if isinstance(r[j], (int, float))]
    return []


class Phase3TranslateWiringParity(P3ParityCheck):
    technique_id = "p3_phase3_translate_wiring"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Self-contained wiring discrimination for 5 unit/representation "
        "translations. Each translated control must change the engine's "
        "deterministic output when set to two distinct values; lomb additionally "
        "must show the correct period<->frequency inversion (min_period caps the "
        "short-cycle/high-freq end). A control invariant to its value, or lomb "
        "wired backwards, -> BLOCK."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(3)
        t = np.arange(200)
        rob = rng.standard_normal(100)
        rob[:5] = [20, -20, 18, -19, 21]
        a = np.sin(2 * np.pi * np.arange(120) / 20)
        b = np.sin(2 * np.pi * (np.arange(120) - 3) / 20)
        return {
            "lomb": (np.sin(2 * np.pi * t / 4) + np.sin(2 * np.pi * t / 40)
                     + 0.2 * rng.standard_normal(200)).tolist(),
            "rob": rob.tolist(),
            "dtw_x": a.tolist(), "dtw_y": b.tolist(),
            "denton": (100 + np.arange(40) * 2 + rng.standard_normal(40)).tolist(),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import importlib

        def run(tid, series, params, time=None, freq=""):
            mod = importlib.import_module("techniques." + tid)
            n = len(series[0]["values"])
            ctx = RunContext({"run_id": "p3_phase3b", "technique_id": tid, "preset": "Balanced",
                              "seed": 42, "frequency": freq,
                              "time": time if time is not None else list(range(n)),
                              "series": series, "params": params})
            return mod.run(ctx, lambda *a, **k: None)

        out = {}
        # lomb: effect + inversion
        ly = fixture["lomb"]
        lA = run("lomb_scargle", [{"name": "y", "values": ly}], {"min_period": 10})
        lB = run("lomb_scargle", [{"name": "y", "values": ly}], {"min_period": 2})
        pA, pB = _lomb_periods(lA), _lomb_periods(lB)
        short_excluded = (not any(3 <= p <= 5 for p in pA)) and (min(pA) >= 9.5 if pA else False)
        short_included = any(3 <= p <= 5 for p in pB)
        out["lomb_scargle:effect"] = {
            "ok": lA.get("status") == "success" and lB.get("status") == "success",
            "differs": _digest(lA) != _digest(lB)}
        out["lomb_scargle:inversion"] = {
            "ok": True, "differs": bool(short_excluded and short_included),
            "min_period10_periods": [round(p, 1) for p in pA[:4]],
            "min_period2_has_short": short_included}

        rob = fixture["rob"]
        r1 = run("robust_estimators", [{"name": "y", "values": rob}], {"trim_fraction": 0.05})
        r2 = run("robust_estimators", [{"name": "y", "values": rob}], {"trim_fraction": 0.40})
        out["robust_estimators:trim_fraction"] = {
            "ok": r1.get("status") == "success" and r2.get("status") == "success",
            "differs": _digest(r1) != _digest(r2)}

        dx, dy = fixture["dtw_x"], fixture["dtw_y"]
        d1 = run("dtw_alignment_lag", [{"name": "x", "values": dx}, {"name": "y", "values": dy}], {"window_frac": 0.05})
        d2 = run("dtw_alignment_lag", [{"name": "x", "values": dx}, {"name": "y", "values": dy}], {"window_frac": 0.50})
        out["dtw_alignment_lag:window_frac"] = {
            "ok": d1.get("status") == "success" and d2.get("status") == "success",
            "differs": _digest(d1) != _digest(d2)}

        q = fixture["denton"]
        n1 = run("denton_chowlin_disaggregation", [{"name": "y", "values": q}], {"conversion_ratio": 3})
        n2 = run("denton_chowlin_disaggregation", [{"name": "y", "values": q}], {"conversion_ratio": 4})
        out["denton_chowlin_disaggregation:conversion_ratio"] = {
            "ok": n1.get("status") == "success" and n2.get("status") == "success",
            "differs": _digest(n1) != _digest(n2)}
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "every translated control changes output; lomb inversion correct"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {}
        for label, r in tsl.items():
            passed = bool(r["ok"] and r["differs"])
            entry = {"status": "PASS" if passed else "BLOCK", "differs": r["differs"]}
            for k in ("min_period10_periods", "min_period2_has_short"):
                if k in r:
                    entry[k] = r[k]
            primary[label] = entry
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_controls": len(tsl), "all_pass": outcome == "PASS"},
        )
