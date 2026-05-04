# Phase 5 Session 2-α — kalman_filter + johansen_bartlett structural-invariants integration (Decision 31ζ pre-split, 1 of 2)

**Date:** 2026-05-04
**Scope:** First execution-class session of Phase 5.
Activates dormant `structural_invariants` declarations on
`KalmanFilterParity` + `JohansenBartlettParity` via new
`check_invariants` lifecycle on `P3ParityCheck` + dispatch
in `runner.py:run_check`. Per Decision 31ζ pre-split:
evt_ferro_segers + cross-wrapper acceptance tests + dispatch
test infrastructure deferred to S2-β.
**Status:** COMPLETE.

## §1 Implementation summary

- **`P3ParityCheck.check_invariants`** added in
  `tools/reference_parity/harness/check_base.py` (~30 LOC):
  class-attribute introspection per S1-B §2.b; iterates
  `structural_invariants`, dispatches via
  `get_invariant_checker`. Empty-tuple backward-compat.
- **`runner.py:run_check` step 4.5** added (~25 LOC): per
  S1-B §2.a (harness-side) + §2.g initial position
  (structural-invariants status integrates via
  `aggregate_outcomes` ranking). `hasattr`/`getattr` guards
  preserve non-P3 backward-compat.
- **kalman_filter + johansen_bartlett:** Phase 4 S9 dormant
  declarations activate automatically via runner dispatch;
  no wrapper-side code change.

## §2 Test summary

NEW `tools/reference_parity/harness/_test_s2_alpha_invariants_dispatch.py`
(~85 LOC): 2 per-wrapper smoke tests verify dispatch with
synthetic PASS-condition inputs. Both PASS.

**§13.4 compliance:** S2-α net commit delta verified at
staging time.

## Disposition

`check_invariants` lifecycle + runner dispatch + 2 wrapper
activations LANDED. evt_ferro_segers + cross-wrapper
acceptance + `_test_runner_invariants_dispatch.py`
infrastructure deferred to S2-β.
