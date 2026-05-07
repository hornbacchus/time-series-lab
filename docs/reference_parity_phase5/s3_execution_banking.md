# Phase 5 S3 execution banking — MCMC SV ess_min empirical bottleneck + smoke test semantics invariant-class divergence + allowlist-vs-parity-slow latent risk

**Date:** 2026-05-07
**Origin:** Q-S3-exec-block-1=(α) investigation step +
Q-S3-exec-block-2-B=(B-1) all 3 entries codified standalone +
Q-S3-exec-block-2-C=(C-γ) banking standalone + Q-Overshoot-A-1=(B)
cascading 3-commit split. S3 single-session execution at Commit
A1 (`9ba96b9`) + Commit A2 (`af07e90`) integrated both MCMC SV
wrappers via 5-tuple allowlist + 9/9 smoke tests with loose
assertion semantic. Three banking entries co-located codifying
institutional learnings surfaced at S3 execution: ess_min
empirical bottleneck pattern + smoke test semantics bifurcation
by invariant class + allowlist-active dispatch latent CI risk
per parity-slow scope expansion scenario.

## B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING — MCMC SV class ess_min empirical bottleneck pattern

At S3 single-session execution, both MCMC SV wrappers
(mcmc_sv_gaussian + mcmc_sv_student_t) discovered to produce
BLOCK on real fixtures per `ess_min` bottleneck. Gaussian:
`ess_min=28.5` on `phi` parameter (high-persistence AR(1) on
log-volatility; slow chain mixing at default Gibbs config).
Student-t: `ess_min=16.3` on `nu` parameter (degrees-of-freedom;
even slower mixing per Student-t innovations distribution).
Both well below tolerance=200 (PASS threshold per Phase 4 S9
P4-1.3 codification + BYF Phase 1 2b precedent) + half-threshold=
100 (CAVEAT band). Both classified BLOCK by `mcmc_convergence`
omnibus checker.

**S3 pre-flight investigation scope vs S3 execution-time
empirical surfacing distinction:** Pre-flight at `1fd1ad3`
established Case 0 outcome on field availability (`ess_min`
exposed at run_tsl() top level via engine audit_fields elevation
per Phase 4 S8 P4-1.2 + harness wrapper extraction). Pre-flight
did NOT audit field VALUE behavior on standard fixtures. Field
availability ≠ field value satisfaction. Execution-time
empirical verification surfaced the BLOCK pattern; pre-flight
authoritative scope (per Q-S3-exec-1=(β)) was field availability
only.

**Cross-references:** Phase 4 S9 P4-1.3 codification (ess_min on
phi as typical SV MCMC bottleneck);
B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-EXTENSION at
`s3_amendment_banking.md` (Case 0 field availability outcome);
S3 pre-flight commit `1fd1ad3` (pre-flight scope = field
availability; NOT field value satisfaction);
B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE
(proximate empirical cause for invariant-class bifurcation);
S3 Commit A1 `9ba96b9` (allowlist + tests) + Commit A2
`af07e90` (findings doc).

**Forward-looking:** Per-wrapper field-availability protocol
scope refinement: pre-flight investigation should audit field
availability AND field value behavior on standard fixtures
going forward. Per-wrapper investigation step at execution-time
authoring includes field value verification when invariant
outcome is fixture/config-dependent (MCMC class) vs deterministic
(closed-form class). Future MCMC-class wrapper integrations
expect status-variable invariant outcomes; smoke tests apply
loose assertion semantic per
B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE
banking. Wrapper config tuning for chain quality (engaging Phase
4 P4-1.3 codification revisit) deferred to future scope per
Q-S3-exec-block-2 disposition.

## B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE — Smoke test assertion semantics bifurcate by invariant class

At S3 execution, smoke test pattern bifurcation surfaced.
Closed-form deterministic invariants (kalman covariance ordering
at S2-α-1-redux + vecm cointegrating rank at S2-α-2-redux + evt
extremal index at S2-β-redux) → smoke test asserts PASS
(deterministic outcome on well-behaved fixtures because
closed-form math is deterministic). MCMC stochastic invariants
(`mcmc_convergence` for both S3 MCMC SV wrappers) → smoke test
asserts dispatch fires + invariant-required field present +
checker returns valid status (PASS / CAVEAT / BLOCK; no specific
outcome assertion; outcome depends on chain mixing quality
which is fixture/preset/seed-dependent).

**Test purpose framing:** Smoke test verifies dispatch
infrastructure verification at execution-class scope, NOT
invariant outcome verification. Assertion semantic adapted to
invariant class. S2-redux closed-form trio asserted PASS because
closed-form math is deterministic on well-behaved fixtures; S3
MCMC SV cannot assume PASS because MCMC outcome is sampling-
quality-dependent. Loose assertion semantic at S3 (per
Q-S3-exec-block-2-A=(α) Chat disposition) preserves dispatch
infrastructure verification while accommodating invariant-class
empirical reality.

**Cross-references:**
B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING (proximate empirical
cause); S2-redux smoke test pattern (closed-form PASS-
deterministic baseline at S2-α-1-redux + S2-α-2-redux + S2-β-
redux); Q-S3-exec-block-2-A=(α) Chat disposition (loose
assertion semantic adoption); Q-Overshoot-A-1=(B) cascading
split (Commit A1 docstring expansion captures invariant-class
divergence rationale inline); S3 Commit A1 `9ba96b9` (loose
assertion implementation).

**Forward-looking:** Per-wrapper smoke test semantic determined
by invariant class at execution-time authoring. Future invariant
classes (e.g., bootstrap-resampled invariants; permutation-test
invariants; conformal-coverage invariants) likely fall into
status-variable category; smoke test applies loose assertion.
Trigger drafting for future MCMC-class + status-variable
wrappers anticipates loose-assertion smoke test per established
discipline. Documentation in trigger templates: invariant-class
classification (closed-form deterministic / stochastic status-
variable) determines smoke test assertion semantic at trigger
drafting time.

## B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK — Allowlist-active dispatch on BLOCK-producing wrappers — parity-slow latent CI risk

At S3 execution investigation, structural finding surfaced.
Allowlist-active dispatch on wrappers producing BLOCK invariant
outcome on real fixtures creates latent parity-slow CI risk
if/when parity-slow workflow scope expands to push-triggered
per-commit gate. Currently out-of-scope per
B-Phase5-PARITY-SLOW-WORKFLOW-SCOPE-CONTEXT (parity-slow is
scheduled cron at `parity-slow.yml`; per-commit gate is
`parity-fast.yml` which filters slow-tier wrappers; allowlist
gating doesn't override tier filter). MCMC SV wrappers are
slow-tier (declared `tier = "slow"` on both wrapper classes);
tier filter excludes from parity-fast scope; no immediate
parity-fast CI risk from S3 allowlist additions.

**Workflow YAML mapping per investigation Category 3:** Exit
0 (PASS/SKIP) → CI green; exit 1 (BLOCK) → CI red; exit 2
(CAVEAT) → CI green via mapping at L183-185 of `parity-fast.yml`;
exit 3 (ERROR) → CI red; exit 4 (DOCUMENTED-DIVERGENCE) → CI
green via mapping at L186-188. **BLOCK propagates to CI red IF
in fast-tier execution.** Slow-tier wrappers don't run in
parity-fast.yml workflow. Local parity-fast tier verification
at S3 commit time produced exit 2 (CAVEAT; CI green) with NO
BLOCK outcomes; MCMC SV wrappers not exercised in parity-fast.

**Cross-references:**
B-Phase5-PARITY-SLOW-WORKFLOW-SCOPE-CONTEXT at
`s2_close_banking.md` (`93cc692`; parity-slow scheduled cron;
per-commit gate is parity-fast which filters slow-tier);
B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING (proximate empirical
cause: BLOCK on real fixtures); S3 pre-flight commit `1fd1ad3`;
S3 Commit A1 `9ba96b9` (allowlist 5-tuple); workflow YAML
exit-code-to-CI-status mapping per `.github/workflows/parity-
fast.yml` lines 154-192; Q-S3-exec-block-1=(α) investigation
step disposition.

**Forward-looking:** If parity-slow workflow scope expands to
push-triggered per-commit gate (currently scheduled cron only
per banking), BLOCK-producing allowlist-active wrappers
produce CI red. Allowlist additions going forward should
explicitly consider invariant-outcome behavior at parity-slow
scope, not just parity-fast. Mitigation paths if scope expands:
(a) wrapper config tuning for chain quality (engages Phase 4
P4-1.3 codification revisit); (b) tier reclassification (slow
→ fast with explicit BLOCK-tolerance); (c) invariant tolerance
adjustment (engages invariant-checker design); (d) allowlist
scope refinement (per-tier allowlist enabling tier-specific
dispatch gating). Trigger drafting for S4 onward considers
parity-slow latent risk per B-Phase5-S3-ALLOWLIST-VS-PARITY-
SLOW-LATENT-RISK at allowlist-addition decision points.

## Disposition

S3 execution banking codified. Three banking entries co-located
per Q-S3-exec-block-2-B=(B-1) + Q-S3-exec-block-2-C=(C-γ)
banking standalone + Q-Overshoot-A-1=(B) cascading split. S3
single-session COMPLETE under master plan v1.2 §15 S3 framing;
first prospective application of v1.1 standing discipline
3-criteria gate empirically validated via (γ) single-session
decomposition. S4 ahead per master plan v1.2 §15 S4 framing
(heterogeneous group per-wrapper sub-sessions; per-wrapper
default applies). S4-α trigger drafting follows S3 closure +
CI verification per established cycle-wide protocol.
