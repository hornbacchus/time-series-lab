"""Phase 5 S2-β cross-wrapper acceptance + dispatch
infrastructure tests (closes S2 closed-form-numerical trio
per master plan v1.1 §15 S2 + Decision 31ζ).

Verifies:
- Cross-wrapper end-to-end: all 3 S2 wrappers
  (kalman_filter + johansen_bartlett + evt_ferro_segers)
  fire ``check_invariants`` correctly via S2-α-1 lifecycle
  method + runner step 4.5 dispatch path
- Outcome aggregation: ``aggregate_outcomes`` ranking
  correctly propagates worst-status across wrappers
  (PASS/CAVEAT/BLOCK ordering)
- Backward-compat: empty ``structural_invariants`` tuple
  short-circuits step 4.5 dispatch (no metrics["invariants"]
  populated; outcome unchanged)

Companion to ``_test_s2_alpha_invariants_dispatch.py``
(per-wrapper smoke tests). This file = cross-wrapper +
runner integration end-to-end coverage per S1-C §3
anticipation.

Run via::

    PYTHONPATH=tools python tools/reference_parity/harness/_test_runner_invariants_dispatch.py
"""

from __future__ import annotations

import sys

import numpy as np

from reference_parity.harness.base import aggregate_outcomes
from reference_parity.harness.checks.kalman_filter import (
    KalmanFilterParity,
)
from reference_parity.harness.checks.johansen_bartlett import (
    JohansenBartlettParity,
)
from reference_parity.harness.checks.evt_ferro_segers import (
    EvtFerroSegersParity,
)


def _kalman_pass_inputs():
    return {
        "filtered_state_cov": np.array([0.5] * 10),
        "predicted_state_cov": np.array([1.0] * 10),
        "smoothed_state_cov": np.array([0.4] * 10),
    }


def _kalman_block_inputs():
    """Synthetic violation: P_filt > P_pred."""
    return {
        "filtered_state_cov": np.array([2.0] * 10),
        "predicted_state_cov": np.array([1.0] * 10),
        "smoothed_state_cov": np.array([0.4] * 10),
    }


def test_cross_wrapper_acceptance_all_pass() -> None:
    """All 3 S2 wrappers' check_invariants() return PASS on
    synthetic invariant-satisfying inputs; aggregate worst-
    status is PASS."""
    kalman = KalmanFilterParity()
    johansen = JohansenBartlettParity()
    evt = EvtFerroSegersParity()

    kr = kalman.check_invariants(_kalman_pass_inputs(), {}, {})
    jr = johansen.check_invariants(
        {"cointegrating_rank": 1}, {"cointegrating_rank": 1}, {},
    )
    er = evt.check_invariants({"theta": 0.65}, {}, {})

    statuses = []
    for results in (kr, jr, er):
        statuses.extend(r["status"] for r in results.values())

    worst = aggregate_outcomes(statuses)
    assert worst == "PASS", (statuses, worst)
    print(
        f"  test_cross_wrapper_acceptance_all_pass: PASS "
        f"(3 wrappers; aggregate={worst})"
    )


def test_cross_wrapper_block_propagation() -> None:
    """If one wrapper invariant BLOCKs, aggregate_outcomes
    propagates BLOCK (verifies ranking BLOCK > PASS used by
    runner.py step 4.5)."""
    kalman = KalmanFilterParity()
    kr = kalman.check_invariants(_kalman_block_inputs(), {}, {})
    statuses = [r["status"] for r in kr.values()]
    assert "BLOCK" in statuses, statuses

    # Simulate runner step 4.5 outcome aggregation:
    #   worst_inv = aggregate_outcomes(inv_outcomes)
    #   final = aggregate_outcomes([compare_outcome, worst_inv])
    compare_outcome = "PASS"
    worst_inv = aggregate_outcomes(statuses)
    final = aggregate_outcomes([compare_outcome, worst_inv])
    assert final == "BLOCK", final
    print(
        f"  test_cross_wrapper_block_propagation: PASS "
        f"(BLOCK propagates via aggregate_outcomes)"
    )


def test_runner_dispatch_empty_invariants_short_circuit() -> None:
    """P3ParityCheck.check_invariants returns {} when
    structural_invariants tuple is empty (backward-compat
    with non-S1 wrappers); runner step 4.5 conditional
    short-circuits."""
    # KalmanFilterParity has structural_invariants tuple set;
    # invariants is empty only for the base P3ParityCheck or
    # explicitly opted-out subclasses. We simulate the empty
    # case by directly inspecting the contract: empty tuple
    # → empty dict result.
    kalman = KalmanFilterParity()
    # Verify the wrapper has invariants declared (sanity)
    assert len(kalman.structural_invariants) > 0
    # Manually exercise the empty-tuple path via subclass
    # introspection: temporarily evaluate check_invariants
    # short-circuit with mock empty-tuple state.
    saved = type(kalman).structural_invariants
    try:
        type(kalman).structural_invariants = ()
        results = kalman.check_invariants({}, {}, {})
        assert results == {}, results
    finally:
        type(kalman).structural_invariants = saved
    print(
        f"  test_runner_dispatch_empty_invariants_short_circuit: "
        f"PASS (empty tuple -> empty dict)"
    )


def main() -> int:
    print(
        "Phase 5 S2-beta - cross-wrapper acceptance + dispatch "
        "infrastructure tests"
    )
    try:
        test_cross_wrapper_acceptance_all_pass()
        test_cross_wrapper_block_propagation()
        test_runner_dispatch_empty_invariants_short_circuit()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll S2-beta cross-wrapper + dispatch tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
