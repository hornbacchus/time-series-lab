# Phase 5 Session 2-α-2-redux — johansen_bartlett allowlist addition (per-wrapper field-availability protocol per S2-α-1-redux pattern)

**Date:** 2026-05-05
**Scope:** Add `3d_johansen_bartlett` to
`_INVARIANTS_DISPATCH_ALLOWLIST` per per-wrapper field-
availability protocol established at S2-α-1-redux
(B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION).
Investigation determined Case (iii): engine wrapper
audit_fields exposes `cointegrating_rank` (line 528 of
`engine/techniques/johansen_cointegration.py`; Phase 4 S8
P4-1.2 codification) but harness `run_tsl()` doesn't surface
it; `run_reference()` doesn't compute rank. Both expanded
this session per Q-Field-α-2/3 discipline.
**Status:** COMPLETE.

## §1 Implementation summary

- **`johansen_bartlett.py` harness wrapper expansion** (~16 LOC):
  `run_tsl()` extracts `wrapper_audit["cointegrating_rank"]`
  (already populated by engine wrapper); `run_reference()`
  extends R subprocess to extract 5%-level critical values
  + computes rank via `sum(trace_stats > cvals_5pct)`. Both
  exposed at output top level. Q-Field-α-2=(b) per-session
  scope: ONLY rank exposed; Q-Field-α-3=(b) NO try/except.
- **`check_base.py` lifecycle method extended** (~10 LOC):
  `check_invariants(tsl, ref=None, fixture=None)` signature
  extended for multi-side invariants (backward-compat:
  S2-α-1-redux test calling with single arg continues to
  work); `_INVARIANT_REQUIRED_FIELDS` adds
  `vecm_cointegration_rank`.
- **`runner.py` allowlist extension** (~4 LOC):
  `_INVARIANTS_DISPATCH_ALLOWLIST` extends from
  `("2a_kalman_filter_smoother",)` to include
  `"3d_johansen_bartlett"`; step 4.5 dispatch passes
  `tsl_out, ref_out, fixture` per extended signature.

## §2 Test summary

`_test_s2_alpha_invariants_dispatch.py` extended with
`test_johansen_bartlett_real_dispatch` (~50 LOC content):
loads real fixture; runs `check.run_tsl(fixture)` +
`check.run_reference(fixture)`; verifies field exposure on
both sides; dispatches via lifecycle method with multi-side
signature; verifies `vecm_cointegration_rank` returns PASS
(tsl_rank=1, ref_rank=1, abs_diff=0). Allowlist-gating test
updated to verify both kalman + johansen in allowlist.
3 tests PASS.

**Local parity-fast tier verification:** overall CAVEAT (5
pre-existing CAVEAT outcomes preserved; 0 BLOCK; 0 ERROR; no
new regressions). Both allowlist invariants fire PASS:
`metric.invariants.kalman_covariance_ordering: PASS` +
`metric.invariants.vecm_cointegration_rank: PASS`.

**§13.4 compliance:** S2-α-2-redux commit delta verified at
staging time per Code's chunking judgment.

## Disposition

S2-α-2-redux LANDED. johansen_bartlett activated via
allowlist + harness wrapper expansion (TSL + ref both
expose `cointegrating_rank`); lifecycle method signature
extended for multi-side invariants. Per-wrapper field-
availability protocol empirically validated at second
wrapper (Case (iii) outcome confirms protocol's case-
analysis structure; harness-side expansion preserves master
plan v1.1 §15 S2 engine-touch narrowing).

S2-β-redux ahead per master plan v1.1 §15 S2 + Decision 31ζ:
- `evt_ferro_segers` allowlist addition with field-
  availability protocol (verify `theta` field for
  `evt_extremal_index` invariant)
- Cross-wrapper acceptance tests (verifies all 3 S2 wrappers
  fire end-to-end via dispatch)
- Dispatch test infrastructure per Code's structural
  judgment

After S2-β-redux closes clean + CI green, **S2 first
execution-class session COMPLETE under refined dispatch
design**; master plan v1.1 §15 S3 (MCMC-stochastic-vol pair)
follows with v1.1 standing discipline 3-criteria gate
prospectively applied.
