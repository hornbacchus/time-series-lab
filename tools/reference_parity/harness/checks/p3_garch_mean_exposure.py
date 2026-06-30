"""Phase 4b + Tier-B capstone — GARCH mean + ar_lags discrimination (garch / egarch / gjr_garch).

`mean` (the conditional-mean model) was engine-read (garch_model.py, default
"Constant") but catalog-absent on all 3 GARCH techniques. 4b exposed it as
["Constant","Zero"]; the Tier-B capstone RE-ADDED "AR" and exposed `ar_lags` (the
engine now passes lags=ar_lags), making mean="AR" GENUINE.

★ Lessons embedded in this check:
  - The GARCH FORECAST path is NON-DETERMINISTIC (simulation, not seed-pinned), so
    a forecast-digest discrimination is unreliable. This check validates via the
    DETERMINISTIC fitted PARAMETER TABLE instead.
  - 4b's Constant-vs-"AR" contrast was DEGENERATE (mean="AR" without lags collapses
    to a constant, relabelled mu->Const) -> it false-NEGATIVEd, so 4b used the clean
    Constant-vs-Zero contrast (Constant fits `mu`; Zero drops it). ★ The CAPSTONE
    RESOLVES the degeneracy: mean="AR" with ar_lags>=1 adds an AR coefficient
    (`y[1]`), genuinely differing from Constant -- so AR is no longer inert.

Asserts, per technique: (1) Constant fits `mu`, Zero drops it (mean has effect);
(2) absent == Constant (byte-identical-on-default); (3) ★ mean="AR", ar_lags=1
gains an AR coef `y[1]` and DIFFERS from Constant (ar_lags makes AR genuine -- the
feature-is-real proof); (4) mean="Constant" with ar_lags=3 == Constant (arch
ignores lags for ConstantMean, so ar_lags is naturally inert for non-AR means --
the unconditional-pass guard). All via the deterministic param table.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _param_names(res: dict):
    for tb in res.get("tables", []) or []:
        if "param" in str(tb.get("name", "")).lower():
            return tuple(str(r[0]) for r in tb.get("rows", []) if r)
    return None


class GarchMeanExposureParity(P3ParityCheck):
    technique_id = "p3_garch_mean_exposure"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Knob-gap exposure for GARCH `mean`, validated via the DETERMINISTIC "
        "fitted param table (the GARCH forecast is non-deterministic). The "
        "minimal-distinguishing contrast Constant-vs-Zero (mean parameter "
        "appears/disappears) proves effect on all 3; a degenerate Constant-vs-AR "
        "contrast would false-negative. No effect -> BLOCK."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(9)
        n = 400
        r = np.zeros(n)
        s = np.ones(n)
        for i in range(1, n):
            s[i] = np.sqrt(0.02 + 0.1 * r[i - 1] ** 2 + 0.85 * s[i - 1] ** 2)
            r[i] = s[i] * rng.standard_normal()
        # NON-CENTERED (mean ~3) so Constant (fits mu) differs from Zero (no mean).
        return {"ret": (r * 10 + 3.0).tolist()}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib

        ret = fixture["ret"]

        def run(tid, params):
            mod = importlib.import_module(registry.TECHNIQUE_REGISTRY[tid])
            ctx = RunContext({"run_id": "p3_garch_mean", "technique_id": tid, "preset": "Balanced",
                              "seed": 42, "frequency": "", "time": list(range(len(ret))),
                              "series": [{"name": "y", "values": ret}], "params": params})
            return mod.run(ctx, lambda *a, **k: None)

        out = {}
        for tid in ("garch", "egarch", "gjr_garch"):
            p_absent = _param_names(run(tid, {}))
            p_const = _param_names(run(tid, {"mean": "Constant"}))
            p_zero = _param_names(run(tid, {"mean": "Zero"}))
            # Capstone: ar_lags makes mean=AR GENUINE (the 4b degeneracy resolved).
            p_ar1 = _param_names(run(tid, {"mean": "AR", "ar_lags": 1}))
            # Guard: ar_lags is IGNORED for Constant (arch ignores lags for
            # ConstantMean) -> byte-identical, so ar_lags is naturally inert for
            # non-AR means (not a bug; the unconditional-pass is safe).
            p_const_lags3 = _param_names(run(tid, {"mean": "Constant", "ar_lags": 3}))
            out[tid] = {
                "ok": all(x is not None for x in (p_absent, p_const, p_zero, p_ar1)),
                "byte_identical": p_absent == p_const,
                "effect": (p_const is not None and p_zero is not None
                           and "mu" in p_const and "mu" not in p_zero),
                # mean=AR(lags=1) gains an AR coefficient `y[1]` and DIFFERS from
                # Constant -- the feature-is-real proof (vs AR(0) == Constant in 4b).
                "ar_genuine": (p_ar1 is not None and p_ar1 != p_const
                               and any("y[" in str(x) for x in p_ar1)),
                "ar_lags_inert_for_constant": (p_const_lags3 is not None
                                               and p_const_lags3 == p_const),
            }
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "Constant fits mu; Zero drops it; absent == Constant"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {}
        for tid, r in tsl.items():
            passed = (r["ok"] and r["byte_identical"] and r["effect"]
                      and r["ar_genuine"] and r["ar_lags_inert_for_constant"])
            primary[tid] = {"status": "PASS" if passed else "BLOCK",
                            "byte_identical": r["byte_identical"], "mean_has_effect": r["effect"],
                            "ar_genuine_with_lags": r["ar_genuine"],
                            "ar_lags_inert_for_constant": r["ar_lags_inert_for_constant"]}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(technique_id=self.technique_id, outcome=outcome,
                            metrics={"primary": primary}, diagnostics={"n": len(tsl)})
