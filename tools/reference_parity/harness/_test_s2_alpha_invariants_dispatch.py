"""Phase 5 S2-alpha per-wrapper smoke tests for kalman_filter +
johansen_bartlett structural-invariants dispatch.

Verifies the ``check_invariants`` lifecycle method on
``P3ParityCheck`` (added Phase 5 S2-alpha) dispatches each
wrapper's declared invariant correctly with synthetic input
satisfying the invariant's PASS condition.

Lightweight unit tests — no R/MCMC, no live ``run_tsl``
pipeline. Cross-wrapper acceptance + end-to-end runner
dispatch integration test deferred to S2-β alongside
evt_ferro_segers integration.

Run via::

    PYTHONPATH=tools python tools/reference_parity/harness/_test_s2_alpha_invariants_dispatch.py
"""

from __future__ import annotations

import sys

import numpy as np

from reference_parity.harness.checks.kalman_filter import (
    KalmanFilterParity,
)
from reference_parity.harness.checks.johansen_bartlett import (
    JohansenBartlettParity,
)


def test_kalman_filter_check_invariants_dispatch() -> None:
    """KalmanFilterParity.check_invariants dispatches the
    kalman_covariance_ordering invariant; PASS on synthetic
    P_filt <= P_pred 1-D arrays.
    """
    check = KalmanFilterParity()
    # 1-D state synthetic: filtered <= predicted at every t.
    tsl = {
        "filtered_state_cov": np.array([0.5] * 10),
        "predicted_state_cov": np.array([1.0] * 10),
        "smoothed_state_cov": np.array([0.4] * 10),
    }
    results = check.check_invariants(tsl, {}, {})
    assert "kalman_covariance_ordering" in results, results
    r = results["kalman_covariance_ordering"]
    assert r["status"] == "PASS", r
    print(f"  test_kalman_filter_check_invariants_dispatch: PASS ({r['status']})")


def test_johansen_bartlett_check_invariants_dispatch() -> None:
    """JohansenBartlettParity.check_invariants dispatches the
    vecm_cointegration_rank invariant; PASS on matching ranks.
    """
    check = JohansenBartlettParity()
    tsl = {"cointegrating_rank": 1}
    ref = {"cointegrating_rank": 1}
    results = check.check_invariants(tsl, ref, {})
    assert "vecm_cointegration_rank" in results, results
    r = results["vecm_cointegration_rank"]
    assert r["status"] == "PASS", r
    print(f"  test_johansen_bartlett_check_invariants_dispatch: PASS ({r['status']})")


def main() -> int:
    print(
        "Phase 5 S2-alpha — per-wrapper structural-invariants "
        "dispatch smoke tests"
    )
    try:
        test_kalman_filter_check_invariants_dispatch()
        test_johansen_bartlett_check_invariants_dispatch()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll S2-alpha dispatch smoke tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
