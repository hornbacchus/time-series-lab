# Path 34B-γ Pre-flight Phase 2 — Cycle Scope Restructuring Touchpoints

**Date:** 2026-05-05
**Status:** PRE-FLIGHT PHASE 2 (read-only enumeration; cycle scope restructuring; framework refinement out-of-scope per `trigger_templates_v1.md`)

## §1 Pre-flight Phase 2 context

Decision 34B-γ broad-scope consolidation Phase 2 per Q1=a
sequencing (framework first, restructuring second). Phase 1
Consolidation CLOSED at commit `1206350` (G1 revision);
`trigger_templates_v1.md` cycle-internal v1 authoritative for
framework refinement. Q2 codification: cycle scope
restructuring → master plan v1.1 amendment covering both
§4.5 calibration awareness + §15 sub-domain (i) restructuring.
Recursive-pattern protection applied per `trigger_templates_v1.md`
§7 (required findings doc counted in trigger projection).

## §2 Cycle scope restructuring touchpoints

**(a) Master plan §15 sub-domain (i) wrapper grouping
refinements.** Master plan v1 lists groupings: S2-S4 (3
wrappers each) + S5 (acceptance + p3_bond_yield_forecast).
S1-C §3 empirically refined groupings (closed-form-numerical
trio at S2; MCMC-stochastic-vol pair at S3) informed by
S1-A architecture review + S1-B design decisions.

Specific instances:
- `evt_ferro_segers` belongs at S2-β per Decision 31ζ pre-
  split, NOT at S3 per master plan v1 §15
- S1-C §3 confirmed only 2 MCMC wrappers (mcmc_sv_gaussian +
  mcmc_sv_student_t); S3's third wrapper requires
  re-specification under restructured grouping
- S4 + S5 wrapper groupings under master plan v1 §15
  (mint_family + transformer_attention + caviar_sav INVERTED
  at S4; acceptance + p3_bond_yield_forecast at S5) require
  verification against S1-C §3 grouping principles
- Sub-domain (i) total: 9 wrappers + p3_bond_yield_forecast;
  redistribution under restructured grouping enumerates
  placement per principled grouping (closed-form-numerical /
  MCMC / structural-decomposition / quantile-statistic)

**Touchpoint:** master plan v1.1 amendment specifies
authoritative wrapper-to-session mapping for all 9 sub-
domain (i) wrappers + p3_bond_yield_forecast under
restructured grouping principles; reconciles
evt_ferro_segers + S3 third-wrapper + S4 / S5 verification.

**(b) Master plan §15 sub-domain (i) session structure
restructuring.** Master plan v1 specifies S2-S4 each as
3-wrappers-per-session. S2-α / S2-α-1 empirical evidence
indicates 3-wrappers may exceed framework empirical-
validation envelope at sub-domain (i) opening: Decision 31ζ
pre-split S2 into S2-α + S2-β per per-wrapper natural seam
(S1-C §3.c spill anticipation); S2-α ORIGINAL trim
disposition + S2-α-1 1.55× upper-bound + Decision 32B revert
sequence empirical evidence basis.

Decision space for Phase 2 Consolidation authoring:
- **Option α — per-wrapper default.** Sub-domain (i) S2-S4
  restructured to per-wrapper sessions; multi-wrapper
  sessions permitted only when natural seam architectural
  justification surfaces at trigger drafting. Empirical
  evidence supports this option (Decision 31ζ + S2-α revert
  + S2-α-1 upper-bound).
- **Option β — multi-wrapper with mandatory pre-planned
  natural seam.** S2-S4 retain multi-wrapper sessions but
  master plan §15 mandates pre-planned natural seam
  enumeration at trigger drafting time. Codifies Decision
  31ζ pattern as standing discipline without changing
  default session granularity.
- **Option γ — no structural change.** Master plan v1
  session structure retained; framework refinement at
  `trigger_templates_v1.md` sufficient. Risks repeated
  calibration errors at S3 / S4 sub-domain (i) opening.

**Touchpoint:** Phase 2 Consolidation authoring chooses
among Options α / β / γ per empirical evidence weight +
master plan architectural cohesion. Pre-flight Phase 2
enumeration does NOT pre-commit; commitment lands at Phase 2
Consolidation trigger drafting.

**(c) Master plan §4.5 calibration awareness amendment.**
Master plan §4.5 v1 captures Phase 4 empirical multiplier
baselines (1.5-2× codification; 1.1-1.3× content). Phase 5
sub-domain (i) opening produced additional empirical data
(skeleton 1.5-2.8×; constraint-specified design-class
0.84-1.07×; constraint-specified execution-class 1.55×
upper-bound calibration error). Trigger specificity as
moderation lever empirically validated (B-Phase5-S0-3 +
S0-6 + S1-A-1-c-GENERALIZATION-VALIDATION). **Touchpoint:**
master plan §4.5 amendment incorporates Phase 5 empirical
observations + cross-references `trigger_templates_v1.md`
for detailed application; §4.5 is summary-level
architectural doc; trigger_templates_v1.md is detailed
application companion.

**(d) B-Phase5-S1-1 master-plan-locus correction
codification.** B-Phase5-S1-1 surfaced at S1-A-1-a-CORRECTED:
audit-side declarations live in
`tools/reference_parity/harness/checks/*.py` NOT engine
`_dispatch.py`. Master plan §15 v1 references `_dispatch.py`
per original hypothesis; correction deferred to S13 doc-set
issuance per v1 standing pattern. Path 34B-γ Q1=a + Q2
(master plan v1.1 covering both §4.5 + §15) reverses
deferral disposition cycle-internal — locus correction
naturally incorporates with restructuring; deferral to S13
was provisional per cycle-establishment phase reasoning,
not principled. **Touchpoint:** master plan v1.1 amendment
codifies B-Phase5-S1-1 correction.

**(e) Cross-references to `trigger_templates_v1.md`.**
Master plan §4.5 amendment + §15 amendment reference
`trigger_templates_v1.md` for detailed framework
application; master plan summary-level vs trigger-template
detailed application. **Touchpoint:** cross-reference
structure between master plan v1.1 and
`trigger_templates_v1.md` established at amendment time;
avoid re-codification of trigger-template content in master
plan.

**(f) Phase 5 reflective record.** Path 30E disposition +
Decision 33C constructive Path 30E + Decision 34B-γ broad-
scope cycle-internal amendment as empirical institutional
learning. Pattern: when sub-domain-opening calibration
errors exceed framework-amendment threshold, cycle-internal
artifacts produced (`trigger_templates_v1.md` + master plan
v1.1) rather than deferring to S13 per v1 standing pattern.
**Touchpoint:** master plan v1.1 amendment notes Phase 5
reflective pattern as candidate institutional precedent for
Phase 6+ (per `trigger_templates_v1.md` §0 + §8 candidate-
pattern framing); actual Phase 6+ inheritance disposition at
S14.

## §3 Master plan v1.1 amendment scope

Phase 2 Consolidation produces master plan v1.1 amendment
covering:
- §4.5 calibration awareness amendment incorporating Phase 5
  empirical observations + cross-reference to
  `trigger_templates_v1.md`
- §15 sub-domain (i) wrapper grouping authoritative
  (incorporating S1-C §3 refinements; reconciling
  evt_ferro_segers + S3 third-wrapper + S4 / S5 verification
  per touchpoint (a))
- §15 sub-domain (i) session structure (decision per
  touchpoint (b) Option α / β / γ)
- B-Phase5-S1-1 master-plan-locus correction codified
- Cross-reference structure between master plan v1.1 and
  `trigger_templates_v1.md`
- Phase 5 reflective record (Path 30E + Decision 34B-γ as
  candidate institutional precedent for Phase 6+)

**§4.5 vs `trigger_templates_v1.md` jurisdictional question
(deferred to Phase 2 Consolidation authoring):**
- Master plan §4.5 is summary-level architectural doc;
  `trigger_templates_v1.md` is detailed application
  companion. Content jurisdictional split during §4.5
  amendment authoring requires explicit decision.
- Candidate jurisdictional principles for Phase 2
  Consolidation to apply:
  - **Principle 1 — multiplier ranges in §4.5; per-class
    budgets in `trigger_templates_v1.md`.** §4.5 captures
    architectural multiplier observations (Phase 4 + Phase 5
    ranges + trigger-specificity-as-moderation-lever);
    `trigger_templates_v1.md` retains per-class LOC budgets +
    verbatim standing language + per-section empirical
    baselines.
  - **Principle 2 — empirical observations in §4.5;
    application discipline in `trigger_templates_v1.md`.**
    §4.5 captures empirical record (what was observed);
    `trigger_templates_v1.md` captures application
    discipline (how to apply at trigger drafting).
    Multiplier ranges could appear in both with §4.5
    referencing `trigger_templates_v1.md` for detail.
  - Phase 2 Consolidation authoring chooses Principle per
    architectural cohesion + cross-reference clarity.

Status: master plan v1.1 cycle-internal; future versioning
at Phase 5 cycle close (S14) per v1.1 inheritance
disposition determination.

## §4 Out-of-scope (per Decision 34B-γ + Q1=a sequencing)

- Framework refinement touchpoints (Phase 1 Consolidation
  scope; `trigger_templates_v1.md` authoritative)
- Sub-domain (ii)-(iv) restructuring (Phase 5 cycle's sub-
  domain (i) opening empirical evidence does not generalize;
  restructuring scope limited to sub-domain (i))
- Phase 4 framework re-architecture (Phase 4 framework
  remains baseline; Phase 5 amendments are cycle-internal
  additions)
- Engine implementation re-scope (engine baseline at Phase 4
  S11c-2 `8c45de7` unchanged)
- v1.x.0 doc-set amendments (P-1 + P-2 + P-3 + P-4 + C-1
  amendments remain S13 doc-set issuance scope; cycle-
  internal master plan amendment does NOT precedent doc-set
  amendment cycle-internal)

## §5 Pre-flight closure + Phase 2 Consolidation anticipation

After Pre-flight Phase 2 CI green, Chat reviews touchpoint
enumeration via F1 surface protocol. Phase 2 Consolidation
write phase scope estimate: ~120-180 LOC (6 touchpoint
amendments + cross-references + Phase 5 reflective record).
Per validated constraint-specification + recursive-pattern
protection: single sub-session feasible.

If consolidation scope > ~180 LOC at trigger drafting, pre-
planned natural seam:
- Phase 2 Consolidation Part 1: §4.5 amendment + cross-
  reference structure to `trigger_templates_v1.md` (~80-100
  LOC)
- Phase 2 Consolidation Part 2: §15 restructuring +
  B-Phase5-S1-1 codification + Phase 5 reflective record
  (~80-100 LOC)

After Phase 2 Consolidation lands master plan v1.1, Phase 5
execution resumes per Q5=b-2 sequence: Path 30E pre-flight
commits + S2-α-1 commits (under refined framework +
restructured master plan) + S2-α-2 onward.

**§13.4 compliance:** Pre-flight Phase 2 commit delta
verified at staging time per recursive-pattern protection
(deliverable + findings doc combined); clean per §13.1
default expected.

## Disposition

Cycle scope restructuring touchpoint enumeration LANDED.
Awaiting Chat review of 6 touchpoints (a)-(f) + amendment
implications before Phase 2 Consolidation write phase
trigger ships. S2-α-1 staging + Path 30E pre-flight files
preserved untouched per Q5=b-2.
