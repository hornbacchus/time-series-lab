"""Phase 5 S2-α-1-redux per-wrapper smoke tests for
structural-invariants dispatch (UPDATED per Q-Field-α
dispositions; exercises REAL run_tsl output, not synthetic
inputs per B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE banking
discipline).

S2-α-1-redux: kalman_filter dispatch smoke test against real
run_tsl output (verifies harness wrapper field exposure +
lifecycle method + invariant checker end-to-end).
S2-α-1-redux: allowlist-exclusion test (verifies non-allowlist
wrapper dispatch skipped via runner step 4.5 conditional).

Verifies:
- Real run_tsl output exposes filtered_state_cov +
  predicted_state_cov fields at top level (per
  B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION banking)
- check_invariants lifecycle method dispatches
  kalman_covariance_ordering checker; returns PASS on real
  output
- _INVARIANTS_DISPATCH_ALLOWLIST gates dispatch correctly
  (kalman in; johansen out)

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
from reference_parity.harness.fixtures import FixtureLoader
from reference_parity.harness.runner import (
    _INVARIANTS_DISPATCH_ALLOWLIST,
)


def test_kalman_filter_real_run_tsl_dispatch() -> None:
    """KalmanFilterParity.check_invariants dispatches the
    kalman_covariance_ordering invariant against REAL run_tsl
    output (per B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE
    discipline; no synthesized inputs).

    Verifies:
    - Real run_tsl output exposes filtered_state_cov +
      predicted_state_cov at top level (harness wrapper
      expansion per B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-
      EXPANSION)
    - Lifecycle method + invariant checker fire end-to-end
    - kalman_covariance_ordering invariant returns PASS on
      real wrapper output (P_filt <= P_pred PSD ordering
      satisfied by Kalman filter math)
    """
    check = KalmanFilterParity()
    loader = FixtureLoader()
    # Load main fixture (matches runner.run_check step 1)
    fixture_data, _meta, _sha = loader.load(check.fixture_id)
    fixture = check.setup_fixture(42)
    fixture.update(fixture_data)
    # Run real run_tsl
    tsl_out = check.run_tsl(fixture)
    # Verify field exposure
    assert "filtered_state_cov" in tsl_out, (
        f"filtered_state_cov missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert "predicted_state_cov" in tsl_out, (
        f"predicted_state_cov missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert tsl_out["filtered_state_cov"] is not None
    assert tsl_out["predicted_state_cov"] is not None
    # Dispatch via lifecycle method
    results = check.check_invariants(tsl_out)
    assert "kalman_covariance_ordering" in results, results
    r = results["kalman_covariance_ordering"]
    assert r["status"] == "PASS", r
    print(
        f"  test_kalman_filter_real_run_tsl_dispatch: "
        f"PASS ({r['status']})"
    )


def test_allowlist_gating() -> None:
    """_INVARIANTS_DISPATCH_ALLOWLIST contains only kalman
    (Q-Allowlist-2=(a) initial population); johansen +
    other wrappers excluded → runner step 4.5 skips dispatch
    for them.

    Tests the allowlist constant directly (the runner
    conditional `tid in _INVARIANTS_DISPATCH_ALLOWLIST` is
    trivially correct given the constant value; this test
    documents the invariant via the technique_id check).
    """
    kalman_tid = KalmanFilterParity.technique_id
    johansen_tid = JohansenBartlettParity.technique_id
    assert kalman_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"kalman {kalman_tid!r} expected in allowlist; "
        f"got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    assert johansen_tid not in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"johansen {johansen_tid!r} expected NOT in allowlist; "
        f"got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    print(
        f"  test_allowlist_gating: PASS "
        f"(kalman in; johansen out; len={len(_INVARIANTS_DISPATCH_ALLOWLIST)})"
    )


def main() -> int:
    print(
        "Phase 5 S2-alpha-1-redux - dispatch smoke tests "
        "(real run_tsl output + allowlist gating)"
    )
    try:
        test_kalman_filter_real_run_tsl_dispatch()
        test_allowlist_gating()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll S2-alpha-1-redux dispatch smoke tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
