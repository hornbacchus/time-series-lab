"""Correctness spot-check #1 — stationarity known-answer + ADF/KPSS complementarity.

The stationarity tests (ADF / KPSS / PP -- the shared triage engine) are validated
bit-exact cross-package vs R urca on the STATISTIC: ADF (p3_adf vs urca::ur.df), KPSS
(p3_kpss / p3_kpss_trend vs urca::ur.kpss). PP's cross-package (p3_pp) is only a
TOLERANCE BAND -- an arch-vs-urca HAC-lag/kernel convention divergence -- so PP carries
no FIRM verdict guard.

This (F)-pattern check closes that gap with a KNOWN-ANSWER on controlled DGPs (the
"reference" is analytic truth, not another library): a random walk IS I(1); a stationary
AR(1) with |phi|<1 IS I(0). It also asserts the ADF<->KPSS COMPLEMENTARITY -- the two
tests have OPPOSITE nulls (ADF/PP H0 = unit root; KPSS H0 = stationarity) yet must AGREE
on the I(0)/I(1) direction on a given series -- a cross-test correctness invariant no
per-test check covers.

Verified-discriminating: the I(1) and I(0) verdicts are OPPOSITE per test, so a build
with a stuck verdict or an inverted reject-rule fails one DGP (demonstrated by injecting
a flipped verdict into compare() -> BLOCK).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _triage_rejected(res: dict) -> dict:
    """Map the engine's 'Stationarity Triage' table -> {test: H0_rejected (bool)}.

    Decision strings: "Reject H0 (...)" / "Fail to reject H0 (...)".
    """
    out: dict[str, bool] = {}
    for t in res.get("tables", []) or []:
        if t.get("name") == "Stationarity Triage":
            for row in t.get("rows", []) or []:
                test = str(row[1])        # ADF / KPSS / PP
                decision = str(row[6])    # the Decision column
                out[test] = not decision.strip().lower().startswith("fail")
    return out


def _is_i1(rejected: dict) -> dict:
    """Per-test 'series is I(1)' verdict from the H0-rejected booleans.

    ADF / PP: H0 = unit root -> NOT rejected => I(1).
    KPSS:     H0 = stationarity -> rejected => I(1).
    """
    return {
        "ADF": (None if "ADF" not in rejected else (not rejected["ADF"])),
        "PP":  (None if "PP" not in rejected else (not rejected["PP"])),
        "KPSS": rejected.get("KPSS"),
    }


class StationarityKnownAnswerParity(P3ParityCheck):
    technique_id = "p3_stationarity_known_answer"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Known-answer correctness for the stationarity triage (ADF/KPSS/PP): on a "
        "random walk (I(1)) and a stationary AR(1) (I(0)) each test must return the "
        "KNOWN-CORRECT verdict, and ADF<->KPSS (opposite nulls) must AGREE on "
        "direction. Closes PP's loose-band gap (no firm verdict guard). The "
        "'reference' is analytic truth. Verified-discriminating: I(1) and I(0) "
        "verdicts are opposite per test -> a stuck/inverted build fails one DGP."
    )

    N = 400
    PHI = 0.5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(11)
        i1 = np.cumsum(rng.standard_normal(self.N))                 # random walk -> I(1)
        i0 = np.zeros(self.N)
        for k in range(1, self.N):
            i0[k] = self.PHI * i0[k - 1] + rng.standard_normal()    # AR(1) |phi|<1 -> I(0)
        return {"i1": i1.tolist(), "i0": i0.tolist()}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib
        mod = importlib.import_module(registry.TECHNIQUE_REGISTRY["adf_test"])

        def triage(vals):
            ctx = RunContext({"run_id": "p3_ska", "technique_id": "adf_test",
                              "preset": "Balanced", "seed": 42, "frequency": "",
                              "time": list(range(len(vals))),
                              "series": [{"name": "y", "values": vals}], "params": {}})
            return _triage_rejected(mod.run(ctx, lambda *a, **k: None))

        return {"i1": triage(fixture["i1"]), "i0": triage(fixture["i0"])}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # Analytic truth (no library): random walk is I(1); stationary AR(1) is I(0).
        return {"expected": "I(1): ADF/PP no-reject, KPSS reject; I(0): ADF/PP reject, KPSS no-reject"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        v_i1 = _is_i1(tsl["i1"])   # on the I(1) DGP: each test's 'is I(1)' verdict
        v_i0 = _is_i1(tsl["i0"])   # on the I(0) DGP
        tests = ("ADF", "PP", "KPSS")
        primary: dict[str, Any] = {}

        # (1) known-answer: I(1) DGP -> all three say I(1); I(0) DGP -> all say I(0).
        i1_ok = all(v_i1[t] is True for t in tests)
        i0_ok = all(v_i0[t] is False for t in tests)
        primary["known_answer_I1"] = {"status": "PASS" if i1_ok else "BLOCK", "is_I1": v_i1}
        primary["known_answer_I0"] = {"status": "PASS" if i0_ok else "BLOCK", "is_I1": v_i0}

        # (2) ADF<->KPSS complementarity: opposite nulls agree on direction, both DGPs.
        comp = (v_i1["ADF"] == v_i1["KPSS"]) and (v_i0["ADF"] == v_i0["KPSS"])
        primary["adf_kpss_complementarity"] = {
            "status": "PASS" if comp else "BLOCK",
            "agree_on_I1_dgp": v_i1["ADF"] == v_i1["KPSS"],
            "agree_on_I0_dgp": v_i0["ADF"] == v_i0["KPSS"],
        }

        # (3) verified-discriminating: per test the I(1) and I(0) verdicts are OPPOSITE.
        disc = all(v_i1[t] is not None and v_i0[t] is not None and v_i1[t] != v_i0[t]
                   for t in tests)
        primary["discriminating"] = {
            "status": "PASS" if disc else "BLOCK",
            "per_test_opposite": {t: (v_i1[t] != v_i0[t]) for t in tests},
        }

        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(technique_id=self.technique_id, outcome=outcome,
                            metrics={"primary": primary},
                            diagnostics={"n": self.N, "phi": self.PHI})
