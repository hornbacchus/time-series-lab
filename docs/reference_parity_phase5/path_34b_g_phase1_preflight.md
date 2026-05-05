# Path 34B-γ Pre-flight Phase 1 — Framework Refinement Touchpoints

**Date:** 2026-05-04
**Status:** PRE-FLIGHT PHASE 1 (read-only enumeration; framework-refinement scope only; restructuring touchpoints at Phase 2)

## §1 Pre-flight Phase 1 context

Decision 34B-γ broad-scope framework + restructuring
consolidation per Phase 5 sub-domain (i) calibration-error
pattern. Q1=a sequencing (framework first, restructuring
second); Q2 codification venue: framework refinement →
`trigger_templates_v1.md` (this Phase 1's consolidation
output); restructuring → master plan v1.1 (Phase 2 scope).
Recursive-pattern protection per Path 30E pre-flight gap (c)
empirical confirmation: findings doc explicitly counted in
trigger projection.

## §2 Framework refinement touchpoints

**(a) Per-class LOC budget accounting.** §13.1 default 200
LOC budget is per-commit total; doesn't distinguish content
classes. Phase 5 commits have structurally distinct classes
(implementation/test code + findings doc + banking entries +
trigger-template references); each has natural LOC
distribution. Empirical instances: S2-α ORIGINAL (~99 LOC
findings doc + impl); S2-α-1 (~75 LOC findings + ~72 LOC
test boilerplate); Path 30E pre-flight (167 deliverable + 40
findings). **Touchpoint:** trigger-template doc specifies
per-class LOC accounting at trigger drafting + at staging.

**(b) Authoring-overshoot disposition.** Original CONSTRAINT
4 (S2-α trigger) had no pre-specification of disposition for
findings-doc authoring exceeding spec; UPDATED CONSTRAINT 4
(Decision 32B trigger) pre-specifies surface-to-Chat-not-trim
disposition. **Touchpoint:** trigger-template doc codifies
UPDATED CONSTRAINT 4 authoring-overshoot language as standing
trigger discipline; applies across all content classes.

**(c) Test boilerplate accounting.** Test files include
docstring + `main()` + setup overhead (~20-25 LOC)
systematically across sub-domain (i) sessions. Trigger
projections under-estimate test-file size by ~20-25 LOC.
Specific instance: S2-α-1 test 72 LOC vs ~40-50 trigger spec.
**Touchpoint:** trigger-template doc specifies per-test-file
boilerplate baseline ~20-25 LOC + per-test-content LOC
~15-25 LOC.

**(d) Banking-entry-as-principled-content.** Banking entries
explicitly required by trigger (~15-20 LOC each) not counted
in CONSTRAINT 4 overhead spec; multiple banking entries push
findings doc above ~30-50 spec. Specific instance: S2-α-1
findings 75 LOC with 2 banking entries. **Touchpoint:**
trigger-template doc specifies banking-entry-LOC-budget
separate from findings-doc-overhead-LOC-budget.

**(e) Within-band content-density classification.** Original
Decision 21 language at master plan §4.2 didn't pre-specify
content-density vs measurement-variance split-vs-absorb
mapping for within-band landing; UPDATED Decision 21 at
Decision 30B trigger explicitly maps content-density → split,
measurement-variance → absorption. Empirical instances:
S1-A-1 + S1-A-1-a both produced band-absorption institutional-
inconsistencies via different framings (reverted at Decision
30B + 30D). **Touchpoint:** trigger-template doc codifies
UPDATED Decision 21 within-band classification language.

**(f) Execution-class projection multiplier guidance.**
Skeleton triggers at sub-domain (i): 1.5-2.8× multipliers.
Constraint-specified design-class triggers: 0.84-1.07×
multipliers (S1 sequence). Constraint-specified execution-
class trigger: 1.55× upper-bound (S2-α-1) — calibration error
specifically at execution-class scope despite constraint
specification. **Touchpoint:** trigger-template doc specifies
execution-class projection multiplier distinct from design-
class; per-class empirical-calibration ranges documented.

**(g) Recursive-pattern protection.** Path 30E pre-flight
itself produced same calibration-error pattern (uncounted
findings doc); pattern is required-but-non-trigger-enumerable
artifacts (findings doc; banking entries; test boilerplate)
systematically uncounted. **Touchpoint:** trigger-template
doc includes required-artifact enumeration as standard at
every trigger; applies recursively to consolidation-class
sessions.

## §3 Framework refinement deliverable scope

Phase 1 consolidation write phase produces
`docs/reference_parity_phase5/trigger_templates_v1.md`
covering:
- Standing UPDATED CONSTRAINT 4 authoring-overshoot
  disposition language (gap (b))
- Per-class LOC budget specification with quantitative
  ranges per class — implementation + tests + findings doc +
  banking entries + trigger-template references (gaps (a) +
  (c) + (d))
- UPDATED Decision 21 within-band classification language
  (gap (e))
- Execution-class projection multiplier guidance (gap (f))
- Required-artifact enumeration template per trigger (gap
  (g))
- Cross-references to Phase 4 institutional discipline
  framework + Phase 5 banking entries informing each
  refinement

## §4 Out-of-scope for Phase 1 (per Q1=a sequencing)

- Master plan §15 sub-domain (i) restructuring (Phase 2
  scope)
- Master plan §4.5 cycle-internal amendment (Phase 2 scope
  per master plan v1.1 unified amendment)
- S2-α-1 / Path 30E pre-flight commit dispositions (post-
  consolidation per Q5=b-2)
- Phase 4 framework re-architecture (Phase 5-specific
  refinement only; Phase 4 framework remains baseline)

## §5 Pre-flight closure + Phase 1 consolidation anticipation

After Pre-flight Phase 1 CI green, Chat reviews touchpoint
enumeration. Phase 1 consolidation write phase scope
estimate: ~80-130 LOC (7 gap-codifications + cross-references
+ scope language). Per validated constraint-specification
pattern: single sub-session feasible.

If consolidation scope > ~150 LOC at trigger drafting, pre-
planned natural seam:
- Phase 1 consolidation part 1: per-class LOC budget +
  authoring-overshoot disposition + within-band
  classification (gaps (a) + (b) + (e); ~80 LOC)
- Phase 1 consolidation part 2: execution-class multiplier +
  test boilerplate + banking-entry budget + required-
  artifact enumeration (gaps (c) + (d) + (f) + (g); ~80 LOC)

After Phase 1 consolidation lands `trigger_templates_v1.md`,
Pre-flight Phase 2 (cycle scope restructuring) begins.

**§13.4 compliance:** Pre-flight Phase 1 commit delta
verified at staging time (deliverable + findings doc combined
per recursive-pattern protection); clean per §13.1 default
expected.

## Disposition

Framework refinement touchpoint enumeration LANDED.
Awaiting Chat review of gap analysis (a)-(g) before Phase 1
consolidation write phase trigger ships. S2-α-1 staging +
Path 30E pre-flight files preserved untouched per Q5=b-2.
