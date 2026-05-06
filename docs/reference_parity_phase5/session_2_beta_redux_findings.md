# Phase 5 Session 2-β-redux — evt_ferro_segers allowlist + cross-wrapper acceptance + dispatch infrastructure (closes S2 closed-form-numerical trio under refined dispatch)

**Date:** 2026-05-05
**Scope:** Closes S2 closed-form-numerical trio under refined
dispatch design + verified-via-CI framework. Adds
`3c_evt_ferro_segers` to `_INVARIANTS_DISPATCH_ALLOWLIST`
per per-wrapper field-availability protocol; adds cross-
wrapper acceptance test (all 3 wrappers fire end-to-end);
adds dispatch infrastructure test (BLOCK propagation
verification). Plus 2 retrofit banking entries per
Q-S2-α-2-redux-followup-1 + Q-S2-α-2-redux-followup-2.
**Status:** COMPLETE.

## §1 Implementation summary

**evt_ferro_segers integration (Case iii outcome):** Engine
wrapper exposes `extremal_index_theta` in audit_fields; harness
`_run_tsl_one()` already extracts to per-fixture `theta` field;
`run_tsl()` returns nested `{"garch": ..., "iid": ...}`.
S2-β-redux harness expansion: surface GARCH (main) fixture's
`theta` at `run_tsl()` top level (~7 LOC). Q-Field-α-2=(b)
per-session scope (only `theta`); Q-Field-α-3=(b) NO try/except.
Single-side invariant per `_check_evt_extremal_index` checker
(consumes `tsl["theta"]` only; no ref needed).

**Allowlist extension:** `runner.py`
`_INVARIANTS_DISPATCH_ALLOWLIST` extends from 2-tuple
(kalman + johansen) to 3-tuple including `3c_evt_ferro_segers`
(closes S2 trio).

**Required-fields map extension:** `check_base.py`
`_INVARIANT_REQUIRED_FIELDS` adds `evt_extremal_index → ("theta",)`.

**Test extensions** (`_test_s2_alpha_invariants_dispatch.py`):
- `test_evt_ferro_segers_real_dispatch` — real run_tsl;
  invariant PASS (theta=0.618441)
- `test_cross_wrapper_acceptance` — all 3 wrappers fire end-
  to-end via dispatch lifecycle method; aggregate PASS
- `test_dispatch_block_propagation` — synthetic BLOCK
  propagation via `aggregate_outcomes` ranking
- `test_allowlist_gating` updated to verify full S2 trio in
  allowlist + non-S2 wrapper excluded
- 6 tests total (3 per-wrapper + 1 allowlist + 1 cross-wrapper
  + 1 dispatch infrastructure)

## §2 Test summary

All 6 dispatch tests PASS. **Local parity-fast tier
verification** (cycle-wide standing protocol): overall
CAVEAT (5 pre-existing); 0 BLOCK; 0 ERROR; no regressions.
All 3 S2 invariants fire PASS:
- `kalman_covariance_ordering: PASS` (n_violations=0)
- `vecm_cointegration_rank: PASS` (tsl_rank=1, ref_rank=1)
- `evt_extremal_index: PASS` (theta=0.618441 ∈ [-0.01, 1.01])

**§13.4 compliance:** S2-β-redux commit delta verified at
staging time per Code's chunking judgment.

## §3 Banking entries

**B-Phase5-S2-α-2-redux-LIFECYCLE-METHOD-SIGNATURE-EXTENSION
(retrofit per Q-S2-α-2-redux-followup-1=(b)).** At S2-α-2-redux
authoring, `_check_vecm_cointegration_rank` checker discovered
to require BOTH `tsl.get("cointegrating_rank")` AND
`ref.get("cointegrating_rank")`. S2-α-1-redux lifecycle method
signature `check_invariants(tsl_output)` (single-arg; passes
`{}` for ref) couldn't support multi-side invariants. Code
extended signature to
`check_invariants(tsl, ref=None, fixture=None)` with backward-
compat preserved (defaults to None). Architectural decision:
single-side default + multi-side optional via ref/fixture
parameters; runner step 4.5 passes all 3 (`tsl_out, ref_out,
fixture`); existing single-arg test calls continue to work.
Cross-references: B-Phase5-S2-α-1-redux-ALLOWLIST-MECHANISM
(lifecycle method origin); S2-α-2-redux commit `ffc08d3`
(signature extension landing); per-wrapper field-availability
protocol per B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION.
Forward-looking: lifecycle method API supports both single-
side + multi-side invariants; future invariant checkers can
declare required-field structure via `_INVARIANT_REQUIRED_FIELDS`;
Q-banking-categorical applies (API-changing categorical
warrants banking).

**B-Phase5-S2-α-2-redux-Q-BANKING-DISCIPLINE-REFINEMENT
(retrofit per Q-S2-α-2-redux-followup-2=(a)).** At S2-α-2-redux
closeout, lifecycle method signature change applied without
dedicated banking entry per Q-S2-α-2-redux-2=(a) "no banking
unless novel" framing. Chat-side review surfaced gap:
architectural API changes (lifecycle method signature /
dispatch infrastructure / allowlist mechanism) have downstream
impact on all future invariant checkers; institutional record
value high regardless of session-specific judgment of novelty.
**Refined discipline (Q-banking-categorical):** lifecycle
method API changes / dispatch infrastructure changes /
allowlist mechanism changes categorically warrant banking
entries regardless of session-context judgment of novelty.
Observable + grep-able rule, not session-context judgment.
Cross-references: B-Phase5-S2-α-2-redux-LIFECYCLE-METHOD-
SIGNATURE-EXTENSION (proximate cause); S2-α-2-redux commit
`ffc08d3` (signature change without banking);
Q-S2-α-2-redux-followup-2=(a) discipline refinement.
Forward-looking: applies to all Phase 5 sub-domain (i)+
sessions; codified in trigger discipline as standing rule;
Phase 6+ inheritance includes refined discipline (candidate-
pattern framing per `trigger_templates_v1.md` §0 + §8).

## Disposition

S2-β-redux LANDED. **S2 first execution-class session genuinely
COMPLETE under refined dispatch design + verified-via-CI**:
- All 3 S2 closed-form-numerical wrappers (kalman_filter +
  johansen_bartlett + evt_ferro_segers) integrated via
  allowlist mechanism + harness wrapper expansion
- Cross-wrapper acceptance verified via dispatch end-to-end
- Dispatch infrastructure (BLOCK propagation; allowlist
  gating) verified
- Per-wrapper field-availability protocol empirically validated
  at trio scope (3/3 wrappers Case (iii) outcome; harness-side
  expansion preserves master plan v1.1 §15 S2 engine-touch
  narrowing)
- 2 retrofit banking entries codified per Q-S2-α-2-redux-
  followup discipline refinement

S3 (MCMC-stochastic-vol pair) follows per master plan v1.1
§15 S3; first prospective application of v1.1 standing
discipline 3-criteria gate at S3 trigger drafting time. S2
sequence empirical observations inform S3 criterion 3
empirical-validation-envelope assessment.
