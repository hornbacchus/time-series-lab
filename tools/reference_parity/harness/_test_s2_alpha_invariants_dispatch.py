"""Phase 5 S2-α per-wrapper smoke tests for structural-
invariants dispatch (Decision 32B per-wrapper natural seam).

S2-α-1 (this file at land time): kalman_filter dispatch
smoke test only. S2-α-2 will append johansen_bartlett
dispatch smoke test to this same file.

Verifies the ``check_invariants`` lifecycle method on
``P3ParityCheck`` (added Phase 5 S2-α-1) dispatches each
wrapper's declared invariant correctly with synthetic input
satisfying the invariant's PASS condition.

Lightweight unit tests — no R, no MCMC, no live ``run_tsl``
pipeline. Cross-wrapper acceptance + end-to-end runner
dispatch integration test deferred to S2-β.

Run via::

    PYTHONPATH=tools python tools/reference_parity/harness/_test_s2_alpha_invariants_dispatch.py
"""

from __future__ import annotations

import sys

import numpy as np

from reference_parity.harness.checks.kalman_filter import (
    KalmanFilterParity,
)


def test_kalman_filter_check_invariants_dispatch() -> None:
    """KalmanFilterParity.check_invariants dispatches the
    kalman_covariance_ordering invariant; PASS on synthetic
    1-D state P_filt <= P_pred arrays.
    """
    check = KalmanFilterParity()
    tsl = {
        "filtered_state_cov": np.array([0.5] * 10),
        "predicted_state_cov": np.array([1.0] * 10),
        "smoothed_state_cov": np.array([0.4] * 10),
    }
    results = check.check_invariants(tsl, {}, {})
    assert "kalman_covariance_ordering" in results, results
    r = results["kalman_covariance_ordering"]
    assert r["status"] == "PASS", r
    print(
        f"  test_kalman_filter_check_invariants_dispatch: "
        f"PASS ({r['status']})"
    )


def main() -> int:
    print(
        "Phase 5 S2-alpha-1 - per-wrapper structural-"
        "invariants dispatch smoke tests"
    )
    try:
        test_kalman_filter_check_invariants_dispatch()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll S2-alpha-1 dispatch smoke tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
