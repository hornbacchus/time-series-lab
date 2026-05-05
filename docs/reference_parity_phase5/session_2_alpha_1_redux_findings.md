# Phase 5 Session 2-α-1-redux — kalman_filter structural-invariants integration via allowlist mechanism + harness wrapper expansion (Decision Q-Re-exec-1=(β) + Q-Allowlist-1/2/3 + Q-Field-α-1/2/3)

**Date:** 2026-05-05
**Scope:** Re-execute S2-α-1 under refined dispatch design after
Phase 5 halt-and-revert at `dd368b3` per
B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE banking. Implements
allowlist-gated dispatch (kalman-only initial population) +
harness-side kalman_filter wrapper expansion exposing
`filtered_state_cov` + `predicted_state_cov` (Q-Field-α-2=(b)
per-session scope; Q-Field-α-3=(b) NO try/except defensive
wrapper). Locally exercises full parity-fast tier per
B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE discipline.
**Status:** COMPLETE.

## §1 Implementation summary

- **`kalman_filter.py` harness wrapper expansion** (~16 LOC):
  `_run_tsl_one()` exposes `filtered_state_cov` +
  `predicted_state_cov` (statsmodels API result transposed
  from (k,k,T) → (T,k,k); predicted sliced to T entries
  matching filtered length). `run_tsl()` spreads fields to
  top level (so checker accesses without nested navigation).
- **`check_base.py` lifecycle method** (~75 LOC):
  `P3ParityCheck.check_invariants(tsl_output) → dict` with
  defensive field check (Q-Allowlist-3=(c)) — required-
  fields map per `_INVARIANT_REQUIRED_FIELDS`; missing fields
  → INFO outcome (audit-trail signal, not parity outcome).
- **`runner.py` step 4.5 + allowlist** (~33 LOC):
  Module-level `_INVARIANTS_DISPATCH_ALLOWLIST = ("2a_kalman_filter_smoother",)`
  (Q-Allowlist-1=(a) + Q-Allowlist-2=(a)). Step 4.5 gates
  dispatch via `tid in _INVARIANTS_DISPATCH_ALLOWLIST`;
  worst-non-INFO status propagates to outcome via
  `aggregate_outcomes`.
- **Field verification at authoring** (Q-Allowlist-3=(b)):
  Real `run_tsl` output verified to expose
  `filtered_state_cov` + `predicted_state_cov` at top level
  + correct shape (T, k, k); kalman added to allowlist after
  verification.

## §2 Test summary

NEW `_test_s2_alpha_invariants_dispatch.py` (~135 LOC; 2
tests):
- `test_kalman_filter_real_run_tsl_dispatch`: loads real
  fixture via `FixtureLoader`, runs `check.run_tsl(fixture)`
  end-to-end (NO synthesis), dispatches via lifecycle method,
  verifies kalman_covariance_ordering returns PASS. PASS.
- `test_allowlist_gating`: verifies allowlist contains
  kalman + excludes johansen (gating semantic). PASS.

**Local parity-fast tier sweep** (per B-Phase5-S2-CI-VS-
LOCAL-GATES-DIVERGENCE discipline): overall CAVEAT (5
pre-existing CAVEAT; 0 BLOCK; 0 ERROR). kalman PASS with
`metric.invariants.kalman_covariance_ordering: PASS`. CI
workflow exit code 2 maps to 0 per §6.4 workflow YAML.

**§13.4 compliance:** Phase 2-α-1-redux commit delta verified
at staging time per Code's chunking judgment.

## §3 Banking entries

**B-Phase5-S2-α-1-redux-ORIGIN — Re-execution origin per
Decision Q-Revert + Q-Re-design + Q-Re-exec sequence.**
Original S2-α-1 (`f771ec6` + `c329b83`) reverted per Phase 5
halt-and-revert (Decision Q-Revert-1=(a) + Q-Revert-2=(b))
per CI failure regression at `f771ec6`. Root cause: dispatch
step 4.5 + lifecycle method fired structural-invariants for
all wrappers with declared invariants (incl. wrappers without
TSL field availability). Re-execution applies refined
dispatch design per Q-Re-design-1=(i) allowlist mechanism +
Q-Allowlist-1/2/3 dispositions. Cross-references:
B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE at `dd368b3`;
revert sequence `9b81510` + `6b3f6af` + `dc84e4c` +
`c075476` + `a28036f`; Phase 5 standing revert-and-re-execute
pattern per Decision 30D + 32B + S1-A-1-a-CORRECTED.
Forward-looking: per-wrapper allowlist additions through S2
sub-sessions; field-availability verification protocol per
Code authoring before allowlist addition.

**B-Phase5-S2-α-1-redux-ALLOWLIST-MECHANISM — Module-level
constant in `runner.py` restricts invariants dispatch to
verified-field-availability wrappers.** Per Q-Allowlist-1=(a)
module constant chosen over (b) class-attribute or (c) config
file: observable + grep-able + clean for ~10 entries max.
Per Q-Allowlist-2=(a) kalman-only initial population
(`_INVARIANTS_DISPATCH_ALLOWLIST = ("2a_kalman_filter_smoother",)`):
per-wrapper natural seam for additions. Per Q-Allowlist-3=(b)
Code-authoring field verification + (c) defensive lifecycle
method check: primary verification at authoring; defensive
layer handles design errors gracefully via INFO outcomes.
Cross-references: master plan v1.1 §15 S2 standing
discipline; Q-Re-design-1=(i) chosen over (ii) field-
availability check + (iii) engine output expansion;
B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE root cause framing.
Forward-looking: per-wrapper allowlist additions through
S2-S5 sub-sessions; allowlist artifact lifecycle reviewed at
S13 (cycle-internal vs master plan §15 reference vs runtime
config).

**B-Phase5-S2-α-1-redux-CI-VERIFICATION-PROTOCOL — Local
parity-fast tier execution before commit.** Pre-commit gates
must exercise the same parity-fast tier the CI workflow
runs, against real wrapper output (not synthetic test
inputs). For single commits, explicit CI green verification
before next trigger ships. For multi-commit sequences
(chunked splits, revert sequences), CI green verification at
sequence END (intermediate-state CI status informational;
sequence-end clean state is gating signal). Revert sequences
in reverse chronological order produce mechanically expected
intermediate-state failures (root cause not removed until
last revert); only end-state CI matters. Code's closeout
reports actual CI status (verified via `gh run list` or
equivalent), not "⏸ pending"; Chat does not ship next
trigger until actual CI status confirmed. Cross-references:
B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE at `dd368b3`
(divergence diagnosis); revert sequence empirical evidence
(reverts 5 + banking commit passed clean per workflow runs
#161 + #162). Forward-looking: protocol applies to S2-S5 +
remaining Phase 5 sessions; trigger drafting includes
explicit CI verification gating; verbal "CI green confirmed"
suffices when explicit + references workflow run.

**B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION —
Harness-side wrapper output expansion vs engine-side
modification scope distinction.** At S2-α-1-redux authoring,
kalman_filter TSL output (`run_tsl`) was found to NOT expose
`filtered_state_cov` + `predicted_state_cov` fields required
by `kalman_covariance_ordering` invariant (CI failure root
cause at `f771ec6` per B-Phase5-S2-CI-VS-LOCAL-GATES-
DIVERGENCE). Resolution: harness-side wrapper expansion
(`tools/reference_parity/harness/checks/kalman_filter.py`
`_run_tsl_one()` + `run_tsl()`) to expose fields directly
from statsmodels API result object. This is HARNESS scope
(audit-side wrapper exposes existing engine output through
harness interface), NOT ENGINE scope (engine implementation
modification). Master plan v1.1 §15 S2 engine-touch
narrowing preserved. Per Q-Field-α-2=(b) per-session scope
discipline: expose ONLY invariant-required fields (filtered
+ predicted; skip smoothed); future invariants handle their
additions at future-session scope. Per Q-Field-α-3=(b) NO
try/except defensive wrapper: loud failure on statsmodels
API change is institutionally preferable to silent field
absence + invariant-check-disabled-but-CI-green. Cross-
references: master plan v1.1 §15 S2 engine-touch scope
framing; Q-Re-design-1=(i) allowlist mechanism (defers to
per-wrapper field expansion); B-Phase5-S2-CI-VS-LOCAL-GATES-
DIVERGENCE empirical origin. Forward-looking: standing
per-wrapper protocol for Phase 5 sub-domain (i): (1) verify
wrapper TSL output exposes invariant-required fields at
authoring; (2) if missing, harness-side wrapper expansion
in scope IF engine API exposes the data; (3) if engine API
doesn't expose data, surface to Chat for design revision
(engine-touch scope decision OR alternative approach). At
S2-α-2-redux + S2-β-redux + future Phase 5 sub-sessions,
this protocol applies.

## Disposition

S2-α-1-redux LANDED. kalman_filter activated via allowlist
mechanism + harness wrapper expansion; lifecycle method +
step 4.5 dispatch infrastructure live. S2-α-2-redux ahead
per per-wrapper allowlist addition + per-wrapper field
verification protocol established at this session
(B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION).
johansen_bartlett `rank` field verification at S2-α-2-redux
authoring; evt_ferro_segers `theta` field verification at
S2-β-redux authoring.
