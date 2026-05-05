# Phase 5 Trigger Templates v1 — Standing Reference for Trigger Drafting

## §0 Document framing

Phase 5 cycle-internal standing reference for trigger
drafting. Decision 34B-γ Phase 1 Consolidation origin per
Pre-flight Phase 1 (commit `9ad5ac6`) gap enumeration.
Detailed application companion to master plan §4 (institutional
discipline standing application).

**Status:** cycle-internal v1. Inheritance to Phase 6+ is
candidate pattern — actual inheritance disposition determined
at Phase 5 cycle close (S14) based on whether
`trigger_templates_v1.md` proves valuable across remaining
Phase 5 sessions.

## §1 Per-class LOC budget specification

Phase 5 commit content classes:
- **Implementation/test code:** wrapper integration +
  lifecycle methods + dispatch logic + per-wrapper smoke
  tests
- **Findings doc:** institutional record artifact
- **Banking entries:** institutional codification
- **Trigger-template references:** cross-references to
  standing language

Trigger drafting protocol:
- Trigger projection MUST enumerate per-class LOC budget
  separately
- Combined budget MUST sum to within §13.1 default 200 LOC
- Per-class budgets serve as authoring guidance; staging-time
  accounting verifies compliance

Empirical baselines (Phase 5 sub-domain (i)):
- Implementation: ~50-70 LOC per wrapper + ~30-50 LOC
  shared infrastructure
- Tests: ~40-50 LOC per test file (including ~20-25 LOC
  boilerplate per §3)
- Findings doc: ~30-50 LOC per session (excluding banking)
- Banking entries: ~15-20 LOC per entry

## §2 Authoring-overshoot disposition (UPDATED CONSTRAINT 4)

Standing language verbatim from Decision 32B trigger:

> "Findings doc / banking entries / test files overhead
> targets per CONSTRAINT 1. Specific disposition for
> authoring-overshoot:
>
> - DURING AUTHORING: aim for spec from the start.
> - IF AUTHORING NATURALLY EXCEEDS spec at first draft
>   (without trim attempt): SURFACE TO CHAT for trigger
>   refinement.
> - IF FIRST DRAFT LANDS WITHIN SPEC: proceed; constraint
>   compliance honored during authoring.
> - DO NOT trim post-hoc to fit constraint after exceeding
>   spec. Trim-to-fit-post-hoc is goalpost-moving in trim-
>   disposition form per Decision 32B precedent."

Apply across all content classes (findings doc + banking +
test boilerplate + implementation).

## §3 Test boilerplate accounting

Per-test-file boilerplate: ~20-25 LOC (docstring + `main()`
+ setup overhead). Per-test-LOC content: ~15-25 LOC per test
scenario. Trigger projection MUST account for boilerplate +
content separately.

Empirical baseline: S2-α-1 test file 72 LOC = ~25 boilerplate
+ ~47 content (2 tests × ~23 LOC each).

**Single empirical instance.** Baseline generalizability
validated at S2-β + S3 + S4 test file pattern observations
across remaining Phase 5 sub-domain (i) sessions. Refine §3
baseline as additional test files land.

## §4 Banking-entry-as-principled-content budget

Banking-entry-LOC-budget separate from findings-doc-overhead-
LOC-budget:
- Findings doc overhead: ~30-50 LOC (header + framing + §1
  implementation summary + §2 test summary + §13.4 +
  disposition footer)
- Banking entries: ~15-20 LOC per entry; counted SEPARATELY
  in trigger projection

Banking entry format (per S1-A-1-c validated):
- 1-2 line title statement
- 3-5 line description
- 2-4 line cross-references to precedents
- 1-2 line forward-looking discipline implication

DO NOT expand banking entries beyond ~20 LOC. Events
warranting more institutional record warrant separate
findings-doc section, not banking-entry expansion.

## §5 Within-band content-density classification (UPDATED Decision 21)

Standing language verbatim from Decision 30B trigger:

> "If actual lands at 200-220 band: apply Decision 21
> principled-content-density test.
>   - If content serves distinct reader populations whose
>     information would be degraded by removal → CONTENT-
>     DENSITY classification → SPLIT per Decision 17 +
>     B-Phase4-S12b-1-1 precedent (within-band split, NOT
>     band absorption).
>   - If overshoot is from formatting noise / edit-vs-
>     replace LOC accounting / Markdown rendering width →
>     MEASUREMENT-VARIANCE classification → BAND ABSORPTION
>     with explicit findings-doc banking.
>   - DO NOT trim principled content to achieve within-band
>     classification (goalpost-moving in micro-form per
>     Decision 30B precedent).
>   - DO NOT apply novel exception paths (saturation framing,
>     cascade-depth framing, etc.) to permit band absorption."

## §6 Execution-class projection multiplier guidance

Phase 5 sub-domain (i) empirical multiplier observations:
- **Skeleton triggers** (Phase 5 sub-domain (i) opening):
  1.5-2.8× multipliers — DO NOT use for sub-domain (i) opening
- **Constraint-specified triggers (design-class):** 0.84-1.07×
  multipliers (S1 sequence empirical record)
- **Constraint-specified triggers (execution-class):** S2-α
  ORIGINAL 1.23× post-trim (institutionally inconsistent
  disposition; reverted); S2-α-1 1.55× upper-bound
  (calibration error). **NO execution-class clean validation
  point exists yet.**
- **Recursive-pattern protection (design-class read-only +
  write-phase consolidation):** Pre-flight Phase 1 0.99×
  upper-bound (read-only enumeration); Phase 1 Consolidation
  1.10× deliverable + within-band combined (write-phase
  consolidation). Both distinct from execution-class scope.

Trigger drafting at sub-domain (i) opening MUST use
constraint-specification + recursive-pattern protection per
§1 + §2 + §3 + §4. Empirical observations updated as Phase 5
cycle progresses (cycle-internal versioning). Execution-class
calibration awaits empirically clean S2-α-1 + S2-α-2 + S2-β
validation under refined framework.

## §7 Recursive-pattern protection

Required artifacts at every Phase 5 trigger:
- Per-session findings doc (institutional record)
- Banking entries (institutional codification, when
  applicable)
- Implementation/test code (when applicable)
- Cross-references to master plan + Phase 4 + prior Phase 5
  banking entries

Trigger drafting protocol:
- ENUMERATE required artifacts at trigger drafting
- COUNT each artifact's LOC budget in projection (NOT just
  primary deliverable)
- VERIFY at staging: actual artifacts match enumerated

Empirical evidence: Path 30E pre-flight projected ~100-150
deliverable; required findings doc (40 LOC) uncounted;
recursive-pattern landed at 207 LOC (within marginal band).
Pre-flight Phase 1 applied protection: combined target ~130-
190; landed 188 LOC = 0.99× upper-bound.

## §8 Cross-references + version

- Master plan §4 — institutional discipline standing
  application; this doc is detailed application companion
- Phase 4 institutional precedents (inherited unchanged):
  Decision 17, B-Phase4-S12b-1-1, B-Phase4-S12c-3,
  B-Phase4-S11b-1-3
- Phase 5 banking entries (per-section empirical basis):
  B-Phase5-S0-3, S0-6, S1-A-1-CLASSIFICATION-ERROR,
  S1-A-1-TRIGGER-LANGUAGE, S1-A-1-a-OVERHEAD-EXPANSION,
  S2-α-TRIGGER-OVERHEAD-DISPOSITION, S2-α-TRIM-AS-GOALPOST-
  MOVING

**Status:** `trigger_templates_v1.md` cycle-internal v1.
Inheritance to Phase 6+ is candidate pattern — actual
inheritance disposition determined at Phase 5 cycle close
(S14) based on whether `trigger_templates_v1.md` proves
valuable across remaining Phase 5 sessions.
