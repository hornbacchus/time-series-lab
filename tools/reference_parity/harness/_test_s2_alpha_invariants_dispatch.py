"""Phase 5 S2-α-1-redux + S2-α-2-redux + S2-β-redux + S3
per-wrapper smoke tests + cross-wrapper acceptance + dispatch
infrastructure for structural-invariants dispatch (exercises
REAL run_tsl + run_reference output, not synthetic inputs
per B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE banking
discipline).

S2-α-1-redux: kalman_filter dispatch smoke test against real
run_tsl output (verifies harness wrapper field exposure +
lifecycle method + invariant checker end-to-end).
S2-α-1-redux: allowlist-gating test (verifies allowlist
mechanism gates dispatch).
S2-α-2-redux: johansen_bartlett dispatch smoke test against
real run_tsl + run_reference output (multi-side invariant
requires both TSL + ref `cointegrating_rank` fields).
S2-β-redux: evt_ferro_segers dispatch smoke test (single-
side invariant; theta surfaced from GARCH fixture);
cross-wrapper acceptance (all 3 S2 wrappers fire + aggregate);
dispatch infrastructure (BLOCK propagation; allowlist exclusion
for non-S2 wrapper).
S3: mcmc_sv_gaussian + mcmc_sv_student_t per-wrapper smoke
tests (single-side `mcmc_convergence` invariant; ess_min
field already at top level per Case 0 outcome at S3 pre-flight
`1fd1ad3`); MCMC SV class cross-wrapper acceptance (2-wrapper
class aggregation distinct from S2 trio).

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
from reference_parity.harness.checks.evt_ferro_segers import (
    EvtFerroSegersParity,
)
from reference_parity.harness.checks.mcmc_sv_gaussian import (
    McmcSvGaussianParity,
)
from reference_parity.harness.checks.mcmc_sv_student_t import (
    McmcSvStudentTParity,
)
from reference_parity.harness.base import aggregate_outcomes
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
    """_INVARIANTS_DISPATCH_ALLOWLIST contains full S2 trio
    (kalman + johansen + evt_ferro_segers; S2-β-redux closes
    trio addition) + S3 MCMC SV pair (mcmc_sv_gaussian +
    mcmc_sv_student_t per Case 0 outcome at S3 pre-flight
    `1fd1ad3`); non-allowlist wrappers still excluded.
    """
    kalman_tid = KalmanFilterParity.technique_id
    johansen_tid = JohansenBartlettParity.technique_id
    evt_tid = EvtFerroSegersParity.technique_id
    gaussian_tid = McmcSvGaussianParity.technique_id
    student_t_tid = McmcSvStudentTParity.technique_id
    assert kalman_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"kalman {kalman_tid!r} expected in allowlist; "
        f"got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    assert johansen_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"johansen {johansen_tid!r} expected in allowlist; "
        f"got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    assert evt_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"evt {evt_tid!r} expected in allowlist after S2-β-redux "
        f"addition; got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    assert gaussian_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"gaussian {gaussian_tid!r} expected in allowlist after "
        f"S3 addition; got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    assert student_t_tid in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"student_t {student_t_tid!r} expected in allowlist after "
        f"S3 addition; got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    # Negative check — a non-allowlist wrapper still excluded
    assert "p3_arima" not in _INVARIANTS_DISPATCH_ALLOWLIST, (
        f"p3_arima unexpectedly in allowlist; "
        f"got {_INVARIANTS_DISPATCH_ALLOWLIST}"
    )
    print(
        f"  test_allowlist_gating: PASS "
        f"(S2 trio + S3 MCMC SV pair in; p3_arima out; "
        f"len={len(_INVARIANTS_DISPATCH_ALLOWLIST)})"
    )


def test_evt_ferro_segers_real_dispatch() -> None:
    """EvtFerroSegersParity.check_invariants dispatches the
    evt_extremal_index invariant against REAL run_tsl output
    (single-side invariant; checker consumes tsl["theta"]
    only, no ref required).

    Verifies:
    - Real run_tsl output exposes `theta` at top level (S2-β-
      redux harness wrapper expansion surfaces GARCH fixture's
      theta from nested per-wrapper structure)
    - Lifecycle method dispatches with single-side default
    - evt_extremal_index invariant returns PASS (theta in
      [0, 1] per Ferro-Segers 2003 intervals estimator)
    """
    check = EvtFerroSegersParity()
    loader = FixtureLoader()
    fixture_data, _meta, _sha = loader.load(check.fixture_id)
    fixture = check.setup_fixture(42)
    fixture.update(fixture_data)
    tsl_out = check.run_tsl(fixture)
    assert "theta" in tsl_out, (
        f"theta missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert tsl_out["theta"] is not None
    results = check.check_invariants(tsl_out)
    assert "evt_extremal_index" in results, results
    r = results["evt_extremal_index"]
    assert r["status"] == "PASS", r
    print(
        f"  test_evt_ferro_segers_real_dispatch: "
        f"PASS ({r['status']}; theta={tsl_out['theta']:.4f})"
    )


def test_cross_wrapper_acceptance() -> None:
    """All 3 S2 wrappers fire check_invariants end-to-end
    against real run_tsl + run_reference output; aggregate
    outcome via aggregate_outcomes ranking is PASS (all 3
    invariants PASS).

    Cross-wrapper acceptance test verifying dispatch
    infrastructure works coherently across the S2 closed-
    form-numerical trio.
    """
    loader = FixtureLoader()
    statuses = []
    # Kalman (single-side)
    kalman = KalmanFilterParity()
    kf_data, _, _ = loader.load(kalman.fixture_id)
    kf_fix = kalman.setup_fixture(42)
    kf_fix.update(kf_data)
    kf_tsl = kalman.run_tsl(kf_fix)
    kf_results = kalman.check_invariants(kf_tsl)
    statuses.extend(r["status"] for r in kf_results.values())
    # Johansen (multi-side; needs ref)
    johansen = JohansenBartlettParity()
    jb_data, _, _ = loader.load(johansen.fixture_id)
    jb_fix = johansen.setup_fixture(42)
    jb_fix.update(jb_data)
    jb_tsl = johansen.run_tsl(jb_fix)
    jb_ref = johansen.run_reference(jb_fix)
    jb_results = johansen.check_invariants(jb_tsl, jb_ref, jb_fix)
    statuses.extend(r["status"] for r in jb_results.values())
    # EVT (single-side)
    evt = EvtFerroSegersParity()
    ev_data, _, _ = loader.load(evt.fixture_id)
    ev_fix = evt.setup_fixture(42)
    ev_fix.update(ev_data)
    ev_tsl = evt.run_tsl(ev_fix)
    ev_results = evt.check_invariants(ev_tsl)
    statuses.extend(r["status"] for r in ev_results.values())

    worst = aggregate_outcomes(statuses)
    assert worst == "PASS", (statuses, worst)
    print(
        f"  test_cross_wrapper_acceptance: PASS "
        f"(3 wrappers; statuses={statuses}; aggregate={worst})"
    )


def test_dispatch_block_propagation() -> None:
    """BLOCK from one invariant propagates via aggregate_outcomes
    ranking (verifies runner step 4.5 outcome integration logic).
    Synthetic invariant outcomes; not real-output dependent.
    """
    # Simulate runner step 4.5 outcome aggregation:
    #   inv_outcomes = [r["status"] for r in results.values() if status != INFO]
    #   worst_inv = aggregate_outcomes(inv_outcomes)
    #   final = aggregate_outcomes([compare_outcome, worst_inv])
    inv_statuses = ["PASS", "BLOCK", "PASS"]
    worst = aggregate_outcomes(inv_statuses)
    assert worst == "BLOCK", worst
    final = aggregate_outcomes(["PASS", worst])
    assert final == "BLOCK", final
    print(
        f"  test_dispatch_block_propagation: PASS "
        f"(BLOCK propagates; final={final})"
    )


def test_johansen_bartlett_real_dispatch() -> None:
    """JohansenBartlettParity.check_invariants dispatches the
    vecm_cointegration_rank invariant against REAL run_tsl +
    run_reference output (per B-Phase5-S2-CI-VS-LOCAL-GATES-
    DIVERGENCE discipline; no synthesized inputs).

    Verifies:
    - Real run_tsl output exposes `cointegrating_rank` at top
      level (harness wrapper expansion per S2-α-2-redux
      Case (iii) — engine audit_fields[\"cointegrating_rank\"]
      surfaced through harness)
    - Real run_reference output exposes `cointegrating_rank`
      computed from urca trace stats vs 5pct critical values
    - Lifecycle method dispatches with multi-side signature
      (tsl + ref + fixture)
    - vecm_cointegration_rank invariant returns PASS on real
      output (TSL rank = ref rank for this fixture)
    """
    check = JohansenBartlettParity()
    loader = FixtureLoader()
    fixture_data, _meta, _sha = loader.load(check.fixture_id)
    fixture = check.setup_fixture(42)
    fixture.update(fixture_data)
    tsl_out = check.run_tsl(fixture)
    ref_out = check.run_reference(fixture)
    # Verify field exposure
    assert "cointegrating_rank" in tsl_out, (
        f"cointegrating_rank missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert "cointegrating_rank" in ref_out, (
        f"cointegrating_rank missing from run_reference "
        f"output; keys={list(ref_out.keys())}"
    )
    assert tsl_out["cointegrating_rank"] is not None
    assert ref_out["cointegrating_rank"] is not None
    # Dispatch via lifecycle method (multi-side signature)
    results = check.check_invariants(tsl_out, ref_out, fixture)
    assert "vecm_cointegration_rank" in results, results
    r = results["vecm_cointegration_rank"]
    assert r["status"] == "PASS", r
    print(
        f"  test_johansen_bartlett_real_dispatch: "
        f"PASS ({r['status']}; tsl_rank={r.get('tsl_rank')}, "
        f"ref_rank={r.get('ref_rank')})"
    )


def test_mcmc_sv_gaussian_real_dispatch() -> None:
    """McmcSvGaussianParity.check_invariants dispatches the
    mcmc_convergence invariant against REAL run_tsl output
    (per B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE discipline;
    no synthesized inputs).

    S3 first-wrapper smoke test. Single-side invariant
    (`mcmc_convergence` checker consumes tsl["ess_min"];
    rhat_max + geweke_max_abs_z optional). Per-wrapper field-
    availability protocol Case 0 outcome (ess_min already
    exposed at run_tsl() top level via engine audit_fields
    elevation per Phase 4 S8 P4-1.2 + harness extraction).

    Loose assertion semantic per Q-S3-exec-block-2-A=(α) +
    B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE
    banking: smoke test verifies dispatch infrastructure
    (field present + dispatch fires + checker returns valid
    status), NOT specific PASS outcome. MCMC stochastic
    invariant outcome depends on chain mixing quality which
    is fixture/preset/seed-dependent; PASS-deterministic
    assertion does NOT apply for MCMC class. Distinct from
    S2-redux closed-form trio which assert PASS because
    closed-form math is deterministic on well-behaved fixtures.

    Verifies:
    - Real run_tsl output exposes `ess_min` at top level
      (Case 0 outcome empirically established at S3 pre-flight
      `1fd1ad3`)
    - Lifecycle method dispatches with single-side default
    - mcmc_convergence invariant returns valid status
      (PASS / CAVEAT / BLOCK; not None; not exception)
    """
    check = McmcSvGaussianParity()
    loader = FixtureLoader()
    fixture_data, _meta, _sha = loader.load(check.fixture_id)
    fixture = check.setup_fixture(42)
    fixture.update(fixture_data)
    tsl_out = check.run_tsl(fixture)
    assert "ess_min" in tsl_out, (
        f"ess_min missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert tsl_out["ess_min"] is not None
    results = check.check_invariants(tsl_out)
    assert "mcmc_convergence" in results, results
    r = results["mcmc_convergence"]
    # Loose assertion: dispatch infrastructure verification
    assert r["status"] in ("PASS", "CAVEAT", "BLOCK"), r
    print(
        f"  test_mcmc_sv_gaussian_real_dispatch: "
        f"PASS ({r['status']}; ess_min={tsl_out['ess_min']:.1f})"
    )


def test_mcmc_sv_student_t_real_dispatch() -> None:
    """McmcSvStudentTParity.check_invariants dispatches the
    mcmc_convergence invariant against REAL run_tsl output.

    S3 second-wrapper smoke test. Mirrors gaussian pattern.
    Per-wrapper Case 0 outcome verified per-wrapper at S3
    execution-time (pre-flight authoritative per Q-S3-exec-1=(β)
    interpretation). Loose assertion semantic per Q-S3-exec-
    block-2-A=(α) + B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-
    CLASS-DIVERGENCE banking.

    Verifies:
    - Real run_tsl output exposes `ess_min` at top level
    - Lifecycle method dispatches with single-side default
    - mcmc_convergence invariant returns valid status
      (PASS / CAVEAT / BLOCK; not None; not exception)
    """
    check = McmcSvStudentTParity()
    loader = FixtureLoader()
    fixture_data, _meta, _sha = loader.load(check.fixture_id)
    fixture = check.setup_fixture(42)
    fixture.update(fixture_data)
    tsl_out = check.run_tsl(fixture)
    assert "ess_min" in tsl_out, (
        f"ess_min missing from run_tsl output; "
        f"keys={list(tsl_out.keys())}"
    )
    assert tsl_out["ess_min"] is not None
    results = check.check_invariants(tsl_out)
    assert "mcmc_convergence" in results, results
    r = results["mcmc_convergence"]
    # Loose assertion: dispatch infrastructure verification
    assert r["status"] in ("PASS", "CAVEAT", "BLOCK"), r
    print(
        f"  test_mcmc_sv_student_t_real_dispatch: "
        f"PASS ({r['status']}; ess_min={tsl_out['ess_min']:.1f})"
    )


def test_cross_wrapper_acceptance_mcmc_sv() -> None:
    """Both MCMC SV wrappers fire check_invariants end-to-end
    against real run_tsl output; aggregate outcome via
    aggregate_outcomes ranking is a valid status (PASS /
    CAVEAT / BLOCK).

    S3 cross-wrapper acceptance test for the 2-wrapper MCMC SV
    class. Structurally distinct from S2 closed-form-numerical
    trio cross-wrapper test (different aggregation cardinality;
    different invariant type — mcmc_convergence vs kalman/vecm/
    evt). Validates dispatch infrastructure works coherently
    across the MCMC SV analytical class.

    Loose assertion semantic per Q-S3-exec-block-2-A=(α) +
    B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE
    banking: cross-wrapper test verifies aggregation operates
    correctly across the class, NOT specific PASS-aggregate
    outcome. MCMC class produces status-variable outcomes per
    fixture/preset/seed; aggregation should preserve worst-case
    propagation regardless of specific outcome.
    """
    loader = FixtureLoader()
    statuses = []
    # Gaussian (single-side; mcmc_convergence)
    gaussian = McmcSvGaussianParity()
    g_data, _, _ = loader.load(gaussian.fixture_id)
    g_fix = gaussian.setup_fixture(42)
    g_fix.update(g_data)
    g_tsl = gaussian.run_tsl(g_fix)
    g_results = gaussian.check_invariants(g_tsl)
    statuses.extend(r["status"] for r in g_results.values())
    # Student-t (single-side; mcmc_convergence)
    student_t = McmcSvStudentTParity()
    t_data, _, _ = loader.load(student_t.fixture_id)
    t_fix = student_t.setup_fixture(42)
    t_fix.update(t_data)
    t_tsl = student_t.run_tsl(t_fix)
    t_results = student_t.check_invariants(t_tsl)
    statuses.extend(r["status"] for r in t_results.values())

    worst = aggregate_outcomes(statuses)
    # Loose assertion: aggregation produces valid status
    assert worst in ("PASS", "CAVEAT", "BLOCK"), (statuses, worst)
    # Each per-wrapper status valid (no None / exception)
    for s in statuses:
        assert s in ("PASS", "CAVEAT", "BLOCK"), (statuses, s)
    print(
        f"  test_cross_wrapper_acceptance_mcmc_sv: PASS "
        f"(2 wrappers; statuses={statuses}; aggregate={worst})"
    )


def main() -> int:
    print(
        "Phase 5 S2-redux + S3 - dispatch smoke tests + "
        "cross-wrapper acceptance + dispatch infrastructure"
    )
    try:
        test_kalman_filter_real_run_tsl_dispatch()
        test_allowlist_gating()
        test_johansen_bartlett_real_dispatch()
        test_evt_ferro_segers_real_dispatch()
        test_cross_wrapper_acceptance()
        test_dispatch_block_propagation()
        test_mcmc_sv_gaussian_real_dispatch()
        test_mcmc_sv_student_t_real_dispatch()
        test_cross_wrapper_acceptance_mcmc_sv()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll S2-redux + S3 dispatch smoke tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
