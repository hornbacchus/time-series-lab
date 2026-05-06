# Phase 5 S3 master-plan-amendment banking — Case 0 protocol extension + v1.1 §15 S3 framing reconciliation

**Date:** 2026-05-06
**Origin:** Q-S3-α-1=(a) cycle-internal master plan amendment +
Q-S3-α-2=(a) standalone Case 0 banking + Q-S3-decomp-1=(γ)
single-session decomposition + Q-S3-decomp-3=(α) two banking
entries at amendment commit. S3 pre-flight CLOSED at commit
`1fd1ad3` (CI green via workflow run 25463934625) surfacing
major finding: engine Path A elevation ALREADY COMPLETE per
Phase 4 S8 P4-1.2 codification; master plan v1.1 §15 S3
framing premise empirically wrong. Co-located institutional
record codifying 2 institutional learnings surfaced from S3
pre-flight: per-wrapper field-availability protocol Case 0
extension + master plan amendment-design-gap pattern. Master
plan v1.1 → v1.2 amendment landed at this commit per
Q-S3-decomp-1=(γ) Chat disposition.

## B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-EXTENSION — Per-wrapper field-availability protocol Case 0 extension

At S3 pre-flight investigation (`1fd1ad3`), both
`mcmc_sv_gaussian` + `mcmc_sv_student_t` `run_tsl()` found to
ALREADY EXPOSE `ess_min` field at top level (REQUIRED by
`mcmc_convergence` checker per `_INVARIANT_REQUIRED_FIELDS`
map at `tools/reference_parity/harness/check_base.py`). No
harness wrapper expansion needed; no allowlist-only-gating
concern. This surfaces "Case 0" beyond Cases (i)/(ii)/(iii)/(iv)
established at S2-redux per-wrapper field-availability
protocol per
B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION.

**Case 0 definition:** Required field already available at
`run_tsl()` top level (typically because engine wrapper
elevates field to `audit_fields` per BYF Decision 12 pattern
+ harness wrapper extracts to top level). No work needed
beyond standard allowlist addition + per-wrapper smoke test.

**Cross-references:**
B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION (original
Case (i)/(ii)/(iii)/(iv) enumeration); S3 pre-flight commit
`1fd1ad3` (Case 0 empirical surfacing); Phase 4 S8 P4-1.2
codification (engine elevation pre-existing, enabling Case 0
outcome at MCMC SV pair); BYF Decision 12 pattern (engine
audit-field elevation framework).

**Forward-looking:** Case 0 added to per-wrapper
field-availability protocol enumeration as protocol-defined
outcome (no work needed beyond standard allowlist + smoke
test). Future Phase 5 sub-sessions + Phase 6+ inheritance
recognize Case 0 as valid empirical outcome alongside Cases
(i)/(ii)/(iii)/(iv). Per-wrapper investigation step still
REQUIRED at execution-time authoring (Case 0 is empirical
outcome per-wrapper, not assumed default — pre-flight finding
at one wrapper does not pre-determine other wrappers'
outcomes). Pattern applies to S3-α (gaussian + student-t
both Case 0 per S3 pre-flight) + future MCMC-class wrappers
where engine Path A elevation pre-exists.

## B-Phase5-MASTER-PLAN-V1.1-§15-S3-FRAMING-RECONCILIATION — Master plan v1.1 §15 S3 framing reconciliation per S3 pre-flight empirical findings

At S3 pre-flight authoring (`1fd1ad3`), engine Path A
elevation discovered ALREADY COMPLETE per Phase 4 S8 P4-1.2
codification (predates Path 34B-γ Phase 2 Consolidation v1.1
authoring at commits `021c778` + `c070c62`). Master plan v1.1
§15 S3 framing premise (engine Path A elevation as
anticipated substantive engine work + engine + harness
decomposition seam mirroring Decision 31ζ S2 pattern)
empirically wrong. Path 34B-γ Phase 2 Consolidation v1.1
authoring didn't audit empirical engine state per wrapper
before authoring §15 S3 framing — same class of design gap
as S1 [PRE-FLIGHT] field-availability audit gap that
surfaced at original S2-α-1 (B-Phase5-S2-CI-VS-LOCAL-GATES-
DIVERGENCE related root cause: dispatch fired structural
invariants without per-wrapper field-availability audit at
authoring time).

**Design-gap pattern:** Master plan amendments authored
without empirical audit of pre-existing engine + harness
state per wrapper produce framing premises that may be
empirically invalidated at execution-time pre-flight. Pre-
flight pattern (established at Path 34B-γ for design-class
calibration error) extends to execution-class scope
evaluation per S3 pre-flight precedent. Master plan v1.2
amendment reconciles framing per pre-flight findings +
Q-S3-decomp-1=(γ) single-session disposition under v1.1
standing discipline 3-criteria gate empirical satisfaction
(Criteria 1+2+3 SATISFIED via analytical-class cohesion +
Case 0 outcome + chunking discipline at staging).

**Cross-references:**
S3 pre-flight commit `1fd1ad3`; Phase 4 S8 P4-1.2
codification; Path 34B-γ Phase 2 Consolidation commits
`021c778` + `c070c62` (v1.1 authoring locus);
B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-EXTENSION (proximate
empirical finding); B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE
(related design-gap class); v1.1 standing discipline
3-criteria gate (empirically validated at S3 first
prospective application); master plan v1.2 amendment §15 S3
framing reconciliation.

**Forward-looking:** Master plan amendments going forward
audit empirical engine state per wrapper before authoring
wrapper-grouping framing. Pre-flight pattern extends to
execution-class scope evaluation as standing discipline (not
limited to design-class calibration error per v1.1
authoring). v1.1 standing discipline 3-criteria gate at v1.2
stands as authoritative gate-evaluation framework for sub-
domain (i) sessions; first prospective application at S3
empirically validated multi-wrapper grouping disposition.
Phase 6+ inheritance includes this discipline as candidate
pattern (per `trigger_templates_v1.md` §0 + §8 candidate-
pattern framing); actual disposition determined at Phase 5
cycle close S14 per remaining-cycle empirical validation.

## Disposition

S3 master-plan-amendment banking codified. Master plan v1.2
amendment landed at this commit (`plans/reference_parity_phase5_master_plan.md`
§15 S3 + §17 v1.2 entry + §18 v1.2 reflective record append).
S3-α execution trigger drafting begins per Q-S3-decomp-1=(γ)
single-session disposition; v1.1 standing discipline
3-criteria gate at v1.2 standing as authoritative gate-
evaluation framework; per-wrapper field-availability protocol
Case 0 extended to enumeration; cycle-wide parity-fast tier
verification + CI verification protocol both standing apply.
