# Phase 5 Session 2-α-1 — kalman_filter integration + shared infrastructure (Decision 32B per-wrapper split, 1 of 2)

**Date:** 2026-05-04
**Scope:** Re-execute S2-α per Decision 32B after S2-α
(commit `ad7383d`) reverted at `926dfa3`. Per S1-C §3.c
per-wrapper natural seam: S2-α-1 lands shared infrastructure
(`P3ParityCheck.check_invariants` lifecycle + runner dispatch
step 4.5) + kalman_filter integration + per-wrapper smoke
test. S2-α-2 (next) lands johansen_bartlett integration
reusing infrastructure.
**Status:** COMPLETE.

## §1 Implementation summary

- **`P3ParityCheck.check_invariants`** added in
  `tools/reference_parity/harness/check_base.py` (~50 LOC):
  class-attribute introspection per S1-B §2.b; iterates
  `structural_invariants`, dispatches via
  `get_invariant_checker`. Empty-tuple backward-compat.
- **`runner.py:run_check` step 4.5** (~33 LOC): per S1-B
  §2.a + §2.g initial position; structural-invariants status
  integrates via `aggregate_outcomes`; `hasattr`/`getattr`
  guards preserve non-P3 backward-compat.
- **kalman_filter:** Phase 4 S9 dormant
  `kalman_covariance_ordering` declaration activates
  automatically via runner dispatch; no wrapper-side change.

## §2 Test summary

NEW `tools/reference_parity/harness/_test_s2_alpha_invariants_dispatch.py`
(~60 LOC; kalman test only). S2-α-2 will append johansen
test. Kalman dispatch with synthetic 1-D state
`P_filt <= P_pred`: PASS verified.

**§13.4 compliance:** S2-α-1 net commit delta verified at
staging time.

## Banked observations

**B-Phase5-S2-α-TRIGGER-OVERHEAD-DISPOSITION.** S2-α
trigger CONSTRAINT 4 specified findings doc overhead at
~30-40 LOC but did NOT pre-specify disposition for
authoring-overshoot. Without that pre-specification, Code's
natural disposition was unilateral trim post-hoc rather
than escalation. UPDATED CONSTRAINT 4 (Decision 32B trigger)
pre-specifies authoring-overshoot disposition: surface to
Chat for trigger refinement; do NOT trim post-hoc. Cross-
reference: B-Phase4-S12c-3 trigger-drafting discipline at
analogous trim-disposition scope; Decision 32B revert +
re-execute precedent. Forward-looking: standing trigger-
drafting language now includes authoring-overshoot disposition
clause as default for findings-doc constraints.

**B-Phase5-S2-α-INFRASTRUCTURE-COLOCATION.** Per-wrapper
natural seam (S1-C §3.c recommendation) lands shared
infrastructure (lifecycle method + runner dispatch) at the
first sub-sub-session (S2-α-1, with kalman_filter as anchor
case); subsequent sub-sub-sessions reuse infrastructure
without duplication (S2-α-2 johansen_bartlett activation
needs only test addition; lifecycle/dispatch already live).
Cross-reference: Phase 4 S11a-2 cascading-split codification
discipline (codify infrastructure first; apply to additional
cases subsequently). Forward-looking: when per-wrapper
natural seams split integration sessions, infrastructure
shared across wrappers belongs at first sub-sub-session as
standing pattern.

## Disposition

`P3ParityCheck.check_invariants` lifecycle + runner dispatch
+ kalman_filter activation LANDED. johansen_bartlett
integration + johansen test deferred to S2-α-2 per
Decision 32B per-wrapper split. evt_ferro_segers + cross-
wrapper acceptance + dispatch test infrastructure deferred
to S2-β per Decision 31ζ.
