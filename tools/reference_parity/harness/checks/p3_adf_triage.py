"""Phase 7+ deeper-validation, scope-extension PILOT — ``adf_test``
JOINT TRIAGE VERDICT parity check (additive; ``p3_adf`` unchanged).

The ribbon's DEFAULT (triage) path for ``adf_test`` emits a joint
ADF/KPSS/PP **stationarity verdict** (``engine/techniques/adf_test.py``
``_joint_verdict`` + ``_run_triage``). The pre-existing ``p3_adf`` check
validates only the single ADF math layer. This check ADDS coverage of
the emitted composite, decomposed per sub-surface and validated each by
its right mode:

  COMPONENTS arm (cross-package vs R urca, at the engine's REALIZED
    triage lags read back from the engine helpers):
      - ADF  vs ``urca::ur.df``   — bit-exact band  (library-selected lag, disclosed)
      - KPSS vs ``urca::ur.kpss`` — bit-exact band  (library-selected lag, disclosed)
      - PP   vs ``urca::ur.pp``   — Pattern-J band   (kernel/divisor divergence;
        triage auto-bandwidth Schwert(2/9); runtime backend recorded)

  ORCHESTRATION arm (no independent impl — the 2x2 rubric is TSL-specific
    → self-parity + a LOAD-BEARING, verified-discriminating functional check):
      - RULE test: assert the engine ``_joint_verdict`` over all four
        boolean input combinations matches the analytic truth table
        (exhaustive, deterministic, no seed); plus two NEGATIVE-CONTROL
        mutants (ignore-KPSS, inverted) that MUST each mismatch >=1 cell
        — this is the discrimination guard (pre-verified: 2/4 mismatch each).
      - INTEGRATION test: 3 robust seeded cells (series -> engine component
        tests -> reject booleans -> emitted verdict) must match the oracle
        label. A ``_mutant`` fixture hook injects a mutant verdict to
        demonstrate the integration arm BLOCKs on a wrong orchestration.

PER-SUB-SURFACE TIERING (honest; do NOT flatten to "bit-exact"): the
joint verdict is **T3 functionally-validated orchestration over bit-exact
(ADF, KPSS) inputs** — bounded by its weakest LAYER (the self-parity +
functional rule), not by its T1 component inputs. PP bounds only the
CONFLICTING tie-breaker text (PP is NOT in the verdict). ``verdict_class``
here is the harness taxonomy field (``closed_form`` — closed-form
components + a deterministic rule); the trust-inventory §2.5 entry records
the full T3-over-T1 per-sub-surface decomposition.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._stationarity_components import (
    adf_reference, kpss_reference, pp_reference,
)
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

SIG = 0.05  # mirrors the ribbon triage default significance_level

# Verdict labels are the engine's exact strings (adf_test.py:200-228).
_STATIONARY = "STATIONARY"
_UNIT_ROOT = "UNIT ROOT (I(1))"
_CONFLICTING = "CONFLICTING"
_INCONCLUSIVE = "INCONCLUSIVE"

# Exhaustive 2x2 truth table over (adf_rejected, kpss_rejected), keyed by
# a 2-char string so tsl/ref dicts stay plainly comparable.
_COMBOS = {"TF": (True, False), "FT": (False, True),
           "TT": (True, True), "FF": (False, False)}
_EXPECTED_RULE = {"TF": _STATIONARY, "FT": _UNIT_ROOT,
                  "TT": _CONFLICTING, "FF": _INCONCLUSIVE}


def _ar1(*, seed: int, n: int, phi: float, sigma: float = 1.0,
         burn: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn) * sigma
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return y[burn:]


def _build_cells() -> dict[str, np.ndarray]:
    """The 3 robust integration cells (pinned seeds; pre-verified)."""
    rng = np.random.default_rng(40)
    rw = np.cumsum(rng.standard_normal(500))
    conf = _ar1(seed=50, n=400, phi=0.3) + np.where(np.arange(400) >= 200, 0.8, 0.0)
    return {
        _STATIONARY: _ar1(seed=11, n=400, phi=0.5),   # ADF rej, KPSS no-rej
        _UNIT_ROOT: rw,                                 # ADF no-rej, KPSS rej
        _CONFLICTING: conf,                             # both reject
    }


def _mutant_ignore_kpss(a: bool, k: bool) -> str:
    """Negative control: drop the KPSS bit (collapses 2x2 -> 2 outcomes)."""
    return _STATIONARY if a else _UNIT_ROOT


class AdfTriageParity(P3ParityCheck):
    """ADF joint-triage verdict scope-extension (additive over p3_adf)."""

    technique_id = "p3_adf_triage"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Components (ADF/KPSS/PP test statistics) are closed-form and "
        "validated cross-package vs urca at the engine's realized triage "
        "lag; the joint verdict is a deterministic 2x2 rule over the "
        "two reject booleans. The harness verdict_class is closed_form; "
        "the TRUST-INVENTORY tiering is honest T3-over-T1 (self-parity + "
        "verified-discriminating functional check on the orchestration, "
        "over bit-exact ADF/KPSS inputs) — see the §2.5 entry. PP is the "
        "Pattern-J component and bounds only the CONFLICTING tie-breaker "
        "text, NOT the verdict (PP is not an input to _joint_verdict)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # Cells use pinned internal seeds for determinism (verdict cells
        # must not drift with the harness seed). ``_mutant`` is the
        # negative-control hook (None = real engine verdict).
        return {"cells": _build_cells(), "_mutant": None}

    # -- shared engine invocation at the triage default params -----------
    @staticmethod
    def _engine(y: np.ndarray):
        from techniques.adf_test import _run_adf_single  # noqa: E402
        from techniques.kpss_test import _run_kpss_single  # noqa: E402
        from techniques.pp_test import _run_pp_single  # noqa: E402
        adf = _run_adf_single(y, "c", None, "AIC")
        kpss = _run_kpss_single(y, "c", "auto")
        pp = _run_pp_single(y, "c", None)
        a = bool(adf["pvalue"] < SIG)
        k = bool(kpss["pvalue"] < SIG)
        return adf, kpss, pp, a, k

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.adf_test import _joint_verdict  # noqa: E402
        cells = fixture["cells"]
        mutant = fixture.get("_mutant")

        # COMPONENTS arm (validated on the STATIONARY cell series).
        adf, kpss, pp, _, _ = self._engine(cells[_STATIONARY])
        components = {
            "adf": {"stat": float(adf["stat"]), "lag": int(adf["used_lag"]),
                    "regression": adf["regression"]},
            "kpss": {"stat": float(kpss["stat"]), "lag": int(kpss["used_lag"]),
                     "regression": kpss["regression"]},
            "pp": {"stat": float(pp["stat"]), "lag": int(pp["used_lag"]),
                   "regression": pp["regression"], "method": pp.get("method")},
        }

        # ORCHESTRATION rule arm — exhaustive 2x2 + 2 negative-control mutants.
        rule = {key: _joint_verdict(a, k)[0] for key, (a, k) in _COMBOS.items()}
        mut_ign = {key: _mutant_ignore_kpss(a, k)
                   for key, (a, k) in _COMBOS.items()}
        mut_inv = {key: _joint_verdict(k, a)[0]  # inverted: swap the bits
                   for key, (a, k) in _COMBOS.items()}

        # ORCHESTRATION integration arm — 3 robust cells (with mutant hook).
        emitted: dict[str, str] = {}
        for cell in (_STATIONARY, _UNIT_ROOT, _CONFLICTING):
            _, _, _, a, k = self._engine(cells[cell])
            if mutant == "ignore_kpss":
                emitted[cell] = _mutant_ignore_kpss(a, k)
            elif mutant == "inverted":
                emitted[cell] = _joint_verdict(k, a)[0]
            else:
                emitted[cell] = _joint_verdict(a, k)[0]

        return {"components": components, "rule": rule, "mut_ign": mut_ign,
                "mut_inv": mut_inv, "emitted": emitted, "_mutant": mutant}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        cells = fixture["cells"]
        y = cells[_STATIONARY]
        # Re-derive the engine's realized lags (deterministic) so urca runs
        # at the matched bandwidth — validates the statistic GIVEN the
        # library-selected lag.
        adf, kpss, pp, _, _ = self._engine(y)
        adf_ref = adf_reference(y, lag=int(adf["used_lag"]), regression="c")
        kpss_ref = kpss_reference(y, lag=int(kpss["used_lag"]), regression="c")
        pp_ref = pp_reference(y, lag=int(pp["used_lag"]), regression="c")
        oracle = {_STATIONARY: _STATIONARY, _UNIT_ROOT: _UNIT_ROOT,
                  _CONFLICTING: _CONFLICTING}
        return {"adf": adf_ref, "kpss": kpss_ref, "pp": pp_ref,
                "expected_rule": dict(_EXPECTED_RULE), "oracle": oracle}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # --- COMPONENTS arm (cross-package, realized-lag) ---
        primary["adf_component"] = _compare_scalar(
            tsl["components"]["adf"]["stat"], ref["adf"]["test_statistic"],
            ladder["adf_component"])
        primary["kpss_component"] = _compare_scalar(
            tsl["components"]["kpss"]["stat"], ref["kpss"]["test_statistic"],
            ladder["kpss_component"])
        primary["pp_component"] = _compare_scalar(
            tsl["components"]["pp"]["stat"], ref["pp"]["test_statistic"],
            ladder["pp_component"])
        for kk in ("adf_component", "kpss_component", "pp_component"):
            statuses.append(primary[kk]["status"])

        # --- ORCHESTRATION rule arm (exhaustive 2x2) ---
        exp = ref["expected_rule"]
        rule_mismatch = [k for k in exp if tsl["rule"][k] != exp[k]]
        rule_status = "PASS" if not rule_mismatch else "BLOCK"
        primary["rule_4cell"] = {"status": rule_status, "tsl": tsl["rule"],
                                 "expected": exp, "mismatch": rule_mismatch}
        statuses.append(rule_status)

        # --- ORCHESTRATION discrimination guard (LOAD-BEARING) ---
        ign_mis = sum(tsl["mut_ign"][k] != exp[k] for k in exp)
        inv_mis = sum(tsl["mut_inv"][k] != exp[k] for k in exp)
        disc_status = "PASS" if (ign_mis >= 1 and inv_mis >= 1) else "BLOCK"
        primary["rule_discrimination"] = {
            "status": disc_status, "ignore_kpss_mismatch": int(ign_mis),
            "inverted_mismatch": int(inv_mis)}
        statuses.append(disc_status)

        # --- ORCHESTRATION integration arm (3 robust cells) ---
        oracle = ref["oracle"]
        integ_mismatch = {c: tsl["emitted"][c] for c in oracle
                          if tsl["emitted"][c] != oracle[c]}
        integ_status = "PASS" if not integ_mismatch else "BLOCK"
        primary["integration"] = {"status": integ_status,
                                  "emitted": tsl["emitted"], "oracle": oracle,
                                  "mismatch": integ_mismatch,
                                  "mutant_hook": tsl.get("_mutant")}
        statuses.append(integ_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "urca_version": ref["adf"].get("urca_version", "unknown"),
                "adf_realized_lag": tsl["components"]["adf"]["lag"],
                "kpss_realized_lag": tsl["components"]["kpss"]["lag"],
                "pp_realized_lag": tsl["components"]["pp"]["lag"],
                "pp_backend": tsl["components"]["pp"]["method"],
                "adf_abs_diff": primary["adf_component"]["abs_diff"],
                "kpss_abs_diff": primary["kpss_component"]["abs_diff"],
                "pp_abs_diff": primary["pp_component"]["abs_diff"],
                "discrimination": (
                    f"ignore_kpss={ign_mis}/4 inverted={inv_mis}/4"),
                "mutant_hook": tsl.get("_mutant"),
            },
        )
