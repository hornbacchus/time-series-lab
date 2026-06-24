"""Phase 4b — forecast-horizon exposure discrimination (knob-gap, 5 techniques).

`horizon` is the canonical forecaster knob; the engine reads it (default 10) but
5 techniques did not expose it (dynamic_factor_model, hmm, markov_switching,
particle_filter, tar_setar). Phase 4b adds the catalog control (int, default 10 =
engine default -> byte-identical-on-default). This check proves the newly-exposed
control HAS EFFECT: at horizon 5 vs 20 the engine output differs. A control with
no effect would mean it isn't really a standalone forecaster knob -> BLOCK.
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


class HorizonExposureParity(P3ParityCheck):
    technique_id = "p3_horizon_exposure"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Knob-gap exposure discrimination: the newly-exposed `horizon` control "
        "must change the engine's (deterministic) output at two distinct values "
        "on each of the 5 techniques. No effect -> the param is not a standalone "
        "forecaster knob (wrong disposition) -> BLOCK."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(7)
        n = 160
        t = np.arange(n)
        uni = (50 + 0.1 * t + 8 * np.sin(2 * np.pi * t / 12)
               + rng.standard_normal(n) * 2).tolist()
        multi = [{"name": f"s{i}",
                  "values": (50 + 0.1 * t + (i + 1) * 4 * np.sin(2 * np.pi * t / 12)
                             + rng.standard_normal(n) * 2).tolist()} for i in range(3)]
        return {"uni": uni, "multi": multi}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib

        uni = [{"name": "y", "values": fixture["uni"]}]
        multi = fixture["multi"]
        targets = [("dynamic_factor_model", multi), ("hmm", uni),
                   ("markov_switching", uni), ("particle_filter", uni),
                   ("tar_setar", uni)]
        out = {}
        for tid, series in targets:
            mod = importlib.import_module(registry.TECHNIQUE_REGISTRY[tid])
            n = len(series[0]["values"])
            tcol = [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01" for i in range(n)]

            def run(h):
                ctx = RunContext({"run_id": "p3_horizon", "technique_id": tid,
                                  "preset": "Balanced", "seed": 42, "frequency": "M",
                                  "time": tcol, "series": series, "params": {"horizon": h}})
                return mod.run(ctx, lambda *a, **k: None)
            r5, r20 = run(5), run(20)
            out[tid] = {"ok": r5.get("status") == "success" and r20.get("status") == "success",
                        "differs": _digest(r5) != _digest(r20)}
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "horizon changes output on every technique"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {tid: {"status": "PASS" if (r["ok"] and r["differs"]) else "BLOCK",
                         "differs": r["differs"]} for tid, r in tsl.items()}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_techniques": len(tsl)})
