# Phase 5 Session 2-α-2 — johansen_bartlett structural-invariants integration (Decision 31ζ pre-split, 2 of 2)

**Date:** 2026-05-05
**Scope:** Second wrapper integration in S2 closed-form-numerical
trio per master plan v1.1 §15 S2 + Decision 31ζ pre-split.
johansen_bartlett dormant `vecm_cointegration_rank` declaration
(Phase 4 S9 commit `ff403dd`) ACTIVATED via runner dispatch
infrastructure landed at S2-α-1 (commit `f771ec6`) per
B-Phase5-S2-α-INFRASTRUCTURE-COLOCATION pattern. No wrapper-
side code change required.
**Status:** COMPLETE.

## §1 Implementation summary

- **johansen_bartlett activation:** Phase 4 S9 dormant
  `structural_invariants = (StructuralInvariant("vecm_cointegration_rank",
  ..., tolerance=0.0 strict))` declaration in
  `tools/reference_parity/harness/checks/johansen_bartlett.py`
  fires automatically via S2-α-1 runner dispatch + lifecycle
  method. No wrapper-side edit needed.
- **Test extension:** `_test_s2_alpha_invariants_dispatch.py`
  appended with `test_johansen_bartlett_check_invariants_dispatch`
  (~20 LOC content); reuses S2-α-1 imports + `main()` framing
  per per-wrapper natural seam pattern.

## §2 Test summary

`_test_s2_alpha_invariants_dispatch.py` covers 2 per-wrapper
smoke tests: kalman_filter (S2-α-1) + johansen_bartlett (S2-α-2);
both PASS on synthetic invariant-satisfying inputs.

**§13.4 compliance:** S2-α-2 commit delta verified at staging
time per Code's chunking judgment.

## Disposition

S2 closed-form-numerical trio progress: kalman_filter LANDED
at S2-α-1 (`f771ec6`); johansen_bartlett LANDED at S2-α-2
(this commit). evt_ferro_segers + cross-wrapper acceptance +
dispatch test infrastructure deferred to S2-β per Decision
31ζ. After S2-β closes, S2 first execution-class session
COMPLETE; master plan v1.1 §15 S3 follows with v1.1 standing
discipline 3-criteria gate prospectively applied.
