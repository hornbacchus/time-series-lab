"""Phase 1 defect #3 — intervention_analysis dialog-input WIRING discrimination.

The catalog exposes flat `intervention_dates` + `intervention_type` inputs, but the
engine previously read only an `interventions` list-of-dicts and AUTO-DETECTED a
single break when that was absent -- so the dialog's date/type inputs never reached
the engine (a NOT-WIRED defect). Auto-detect is structurally limited to ONE
intervention; a user who knows there are several (or knows the exact date/type)
could not get their model.

The fix translates the flat dialog inputs into the interventions list inside the
engine (precedence: explicit `interventions` list > flat `intervention_dates` +
`intervention_type` > auto-detect). This check confirms the wiring: on a fixture
with TWO known interventions (which auto-detect can only half-find), supplying the
flat inputs must make the engine use BOTH user interventions.

Asserts the engine, given the flat inputs, reports n_interventions == 2 at the
USER's indices -- NOT the single auto-detected break.
  PRE-fix (flat ignored -> auto-detect): n_interventions == 1 -> BLOCK.
  POST-fix (flat wired):                  n_interventions == 2 -> PASS.
The fixture uses integer-position tokens so the check is date-format-independent.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _two_intervention_dgp(seed: int, n: int = 240) -> tuple[np.ndarray, int, int]:
    """AR(1) with a step (+5 @ idx1) and a pulse (+8 @ idx2). Auto-detect (single
    max-CUSUM break) can only find one of the two."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n)
    x = np.zeros(n)
    for t in range(1, n):
        x[t] = 0.5 * x[t - 1] + e[t]
    idx1, idx2 = 80, 160
    x[idx1:] += 5.0
    x[idx2] += 8.0
    return x, idx1, idx2


class InterventionWiringParity(P3ParityCheck):
    technique_id = "p3_intervention_wiring"
    tier = "fast"
    fixture_id = ""
    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Wiring discrimination for intervention_analysis: the flat dialog inputs "
        "(intervention_dates + intervention_type) must reach the engine and drive "
        "the model, not be silently ignored in favour of single-break "
        "auto-detect. Hard assertions on the engine's intervention set, not a "
        "numeric parity band."
    )
    DGP_N = 240

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, idx1, idx2 = _two_intervention_dgp(seed, n=self.DGP_N)
        return {"y": y, "idx1": idx1, "idx2": idx2}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.intervention_analysis as ia_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        idx1, idx2 = int(fixture["idx1"]), int(fixture["idx2"])
        ctx = RunContext({
            "run_id": "p3_intervention_wiring",
            "technique_id": "intervention_analysis",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            # The flat dialog inputs (integer-position tokens -> date-format-free).
            "params": {"intervention_dates": f"{idx1},{idx2}",
                       "intervention_type": "step"},
        })
        resp = ia_mod.run(ctx, lambda *a, **kw: None)
        a = resp.get("audit_fields", {})
        ivs = a.get("interventions") or []
        return {
            "status": resp.get("status"),
            "n_interventions": a.get("n_interventions"),
            "indices": sorted(int(iv.get("index")) for iv in ivs
                              if isinstance(iv, dict) and iv.get("index") is not None),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {
            "n_interventions": int(ladder.get("expected_n_interventions", 2)),
            "indices": sorted([int(fixture["idx1"]), int(fixture["idx2"])]),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        n_ok = tsl.get("n_interventions") == ref["n_interventions"]
        idx_ok = tsl.get("indices") == ref["indices"]
        primary = {
            "n_interventions": {
                "status": "PASS" if n_ok else "BLOCK",
                "tsl": tsl.get("n_interventions"), "ref": ref["n_interventions"],
            },
            "user_indices_used": {
                "status": "PASS" if idx_ok else "BLOCK",
                "tsl": tsl.get("indices"), "ref": ref["indices"],
            },
        }
        run_ok = tsl.get("status") == "success"
        statuses = [v["status"] for v in primary.values()]
        outcome = "BLOCK" if (not run_ok or "BLOCK" in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"run_status": tsl.get("status"),
                         "n_interventions": tsl.get("n_interventions"),
                         "indices": tsl.get("indices")},
        )
