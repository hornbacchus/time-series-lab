"""Phase 4b — Tier-2 knob-gap exposure discrimination (6 controls).

Each newly-exposed Tier-2 control must change the engine's output at two distinct
values (the inverse of the inert checks). Byte-identical-on-default verified
separately. Controls: bocpd.threshold (0.3/0.7), pelt_change_points.jump (1/5 on a
CLOSE-changepoint series), dynamic_factor_model.k_factors (1/2), theta_forecast.period
(4/12), denton_chowlin_disaggregation.rho (auto/0.9), x13_seasonal_adjust.transform
(log/none). No effect -> wrong disposition -> BLOCK.

(GARCH `mean` was held out of this batch: the GARCH forecast path is
non-deterministic, and `mean` shows effect on egarch but not garch/gjr_garch on the
test series -- its disposition is being re-adjudicated separately.)
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


class Tier2KnobGapParity(P3ParityCheck):
    technique_id = "p3_tier2_knobgap_exposure"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Knob-gap exposure discrimination for 6 Tier-2 controls: each must change "
        "the engine's deterministic output at two distinct values. No effect -> "
        "wrong disposition -> BLOCK. Hard per-control assertions."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(9)
        n, t = 300, np.arange(300)
        cps = np.concatenate([rng.standard_normal(100), 6 + rng.standard_normal(100),
                              rng.standard_normal(100)]).tolist()
        cps_close = np.concatenate([rng.standard_normal(30), 5 + rng.standard_normal(8),
                                    rng.standard_normal(30), 5 + rng.standard_normal(8),
                                    rng.standard_normal(30)]).tolist()
        seas = (50 + 0.1 * t + 8 * np.sin(2 * np.pi * t / 12) + rng.standard_normal(n)).tolist()
        pos = (200 + np.arange(144) * 1.5 + 30 * np.sin(2 * np.pi * np.arange(144) / 12)
               + rng.standard_normal(144) * 3).tolist()
        multi = [{"name": f"s{i}",
                  "values": (50 + 0.1 * t[:160] + (i + 1) * 4 * np.sin(2 * np.pi * t[:160] / 12)
                             + rng.standard_normal(160)).tolist()} for i in range(3)]
        quarterly = (100 + np.arange(48) * 2 + rng.standard_normal(48)).tolist()
        return {"cps": cps, "cps_close": cps_close, "seas": seas, "pos": pos,
                "multi": multi, "quarterly": quarterly}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib

        def run(tid, series, params, freq="M"):
            mod = importlib.import_module(registry.TECHNIQUE_REGISTRY[tid])
            nn = len(series[0]["values"])
            tcol = [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01" for i in range(nn)]
            ctx = RunContext({"run_id": "p3_tier2", "technique_id": tid, "preset": "Balanced",
                              "seed": 42, "frequency": freq, "time": tcol,
                              "series": series, "params": params})
            return mod.run(ctx, lambda *a, **k: None)

        uni = lambda v: [{"name": "y", "values": v}]
        # (label, tid, series, key, v1, v2, freq, extra)
        cases = [
            ("bocpd.threshold", "bocpd", uni(fixture["cps"]), "threshold", 0.3, 0.7, "", {}),
            ("pelt_change_points.jump", "pelt_change_points", uni(fixture["cps_close"]), "jump", 1, 5, "", {}),
            ("dynamic_factor_model.k_factors", "dynamic_factor_model", fixture["multi"], "k_factors", 1, 2, "M", {}),
            ("theta_forecast.period", "theta_forecast", uni(fixture["seas"]), "period", 4, 12, "M", {}),
            ("denton_chowlin_disaggregation.rho", "denton_chowlin_disaggregation", uni(fixture["quarterly"]),
             "rho", "auto", "0.9", "Q", {"conversion_ratio": 3}),
            ("x13_seasonal_adjust.transform", "x13_seasonal_adjust", uni(fixture["pos"]), "transform", "log", "none", "M", {}),
        ]
        out = {}
        for label, tid, series, key, v1, v2, freq, extra in cases:
            r1 = run(tid, series, {**extra, key: v1}, freq)
            r2 = run(tid, series, {**extra, key: v2}, freq)
            out[label] = {"ok": r1.get("status") == "success" and r2.get("status") == "success",
                          "differs": _digest(r1) != _digest(r2)}
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "every Tier-2 control changes output"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {k: {"status": "PASS" if (r["ok"] and r["differs"]) else "BLOCK",
                       "differs": r["differs"]} for k, r in tsl.items()}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(technique_id=self.technique_id, outcome=outcome,
                            metrics={"primary": primary}, diagnostics={"n": len(tsl)})
