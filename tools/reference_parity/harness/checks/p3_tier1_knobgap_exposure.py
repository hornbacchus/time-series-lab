"""Phase 4b — Tier-1 knob-gap exposure discrimination (7 controls).

Each newly-exposed Tier-1 control must change the engine's deterministic output at
two distinct values (the inverse of the inert checks). Byte-identical-on-default is
verified separately (omit == the new catalog default). No effect -> the param is
not a standalone user knob (wrong disposition) -> BLOCK.

Controls: transfer_function.polynomial (unrestricted/almon), vecm.deterministic
(ci/n) + vecm.irf_periods (10/30), evt_pot_gpd.tail (upper/lower),
robust_estimators.winsor_fraction (0.05/0.40), stl_esd_anomaly.direction
(both/upper), markov_switching.switching_trend (True/False).
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


def _ar(phi, seed, n):
    r = np.random.default_rng(seed)
    e = r.standard_normal(n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


class Tier1KnobGapParity(P3ParityCheck):
    technique_id = "p3_tier1_knobgap_exposure"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Knob-gap exposure discrimination: each newly-exposed Tier-1 control must "
        "change the engine's deterministic output at two distinct values. No "
        "effect -> wrong disposition -> BLOCK. Hard per-control assertions."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(11)
        n, t = 180, np.arange(180)
        x1 = _ar(0.6, 1, n)
        y1 = 0.5 * np.concatenate([[0, 0], x1[:-2]]) + 0.3 * rng.standard_normal(n)
        coint = np.cumsum(rng.standard_normal(n))
        seas = (50 + 0.1 * t + 8 * np.sin(2 * np.pi * t / 12) + rng.standard_normal(n)).tolist()
        seas2 = list(seas); seas2[80] += 40; seas2[160] -= 35
        heavy600 = (np.random.default_rng(11).standard_t(3, 600) * 5).tolist()
        # markov_switching: a clear two-variance-regime series (low then high) so
        # BOTH switching_trend=True and =False converge (MLE-robust).
        rng_ms = np.random.default_rng(3)
        ms = (0.05 * np.arange(200)
              + np.concatenate([rng_ms.standard_normal(100) * 0.5,
                                rng_ms.standard_normal(100) * 3.0])).tolist()
        return {
            "tf": [{"name": "Y", "values": y1.tolist()}, {"name": "X", "values": x1.tolist()}],
            "ve": [{"name": "a", "values": (coint + rng.standard_normal(n) * 0.5).tolist()},
                   {"name": "b", "values": (coint + rng.standard_normal(n) * 0.5).tolist()}],
            "heavy600": heavy600, "seas": seas, "seas2": seas2, "ms": ms,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib

        def run(tid, series, params, freq="M"):
            mod = importlib.import_module(registry.TECHNIQUE_REGISTRY[tid])
            nn = len(series[0]["values"])
            tcol = [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01" for i in range(nn)]
            ctx = RunContext({"run_id": "p3_tier1", "technique_id": tid, "preset": "Balanced",
                              "seed": 42, "frequency": freq, "time": tcol,
                              "series": series, "params": params})
            return mod.run(ctx, lambda *a, **k: None)

        tf, ve = fixture["tf"], fixture["ve"]
        heavy = [{"name": "y", "values": fixture["heavy600"]}]
        seas2 = [{"name": "y", "values": fixture["seas2"]}]
        ms = [{"name": "y", "values": fixture["ms"]}]
        # (label, tid, series, key, v1, v2, freq)
        cases = [
            ("transfer_function.polynomial", "transfer_function", tf, "polynomial", "unrestricted", "almon", "M"),
            ("vecm.deterministic", "vecm", ve, "deterministic", "ci", "n", "M"),
            ("vecm.irf_periods", "vecm", ve, "irf_periods", 10, 30, "M"),
            ("evt_pot_gpd.tail", "evt_pot_gpd", heavy, "tail", "upper", "lower", ""),
            ("robust_estimators.winsor_fraction", "robust_estimators", heavy, "winsor_fraction", 0.05, 0.40, ""),
            ("stl_esd_anomaly.direction", "stl_esd_anomaly", seas2, "direction", "both", "upper", "M"),
            ("markov_switching.switching_trend", "markov_switching", ms, "switching_trend", True, False, "M"),
        ]
        out = {}
        for label, tid, series, key, v1, v2, freq in cases:
            r1, r2 = run(tid, series, {key: v1}, freq), run(tid, series, {key: v2}, freq)
            out[label] = {"ok": r1.get("status") == "success" and r2.get("status") == "success",
                          "differs": _digest(r1) != _digest(r2)}
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "every Tier-1 control changes output"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {k: {"status": "PASS" if (r["ok"] and r["differs"]) else "BLOCK",
                       "differs": r["differs"]} for k, r in tsl.items()}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(technique_id=self.technique_id, outcome=outcome,
                            metrics={"primary": primary}, diagnostics={"n_controls": len(tsl)})
