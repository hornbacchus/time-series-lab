# Phase 3 Session 16 — Documentation phase: P-2 diagnostic reference

**Date:** 2026-04-29
**Master plan reference:** §15.13 + Appendix C
**Deliverable:** `docs/engineering/parity_diagnostic_reference.md` v1.0.0
**Scope:** Single-session — completed in 1 session as planned.

## Summary

Phase 3 documentation phase Session 16 issues the **P-2
diagnostic reference** as the descriptive companion to P-1
(parity standard). P-2 captures *what we learned* across
13 batch-execution sessions; P-1 captures *what new wrappers
must do*. When directive guidance is needed, P-1 wins; P-2
explains the empirical foundation.

This session promotes the document from v0.3.0 (S14 close;
Pattern J catalog complete with 11 entries) to v1.0.0
(formalized Pattern A taxonomy + 4 banked items closed).

## Document structure (8 sections)

The S12–S14 incremental development populated Sections B
(Pattern J catalog) and Section D (Pattern F invariants
registry). Session 16 fills the deferred sections and adds
new ones for banked items.

| § | Status at S15 close | Status at S16 close |
|---|---|---|
| A — Tolerance class taxonomy | Placeholder | **LOCKED** at 11 classes; per-class bands documented; A.10/A.11 split candidate banked |
| B — Pattern J catalog | Complete (11 entries B.1-B.6) | Unchanged (already complete) |
| C — Pattern A taxonomy | Placeholder | **FORMALIZED** into A.1 same-library / A.2 cross-package / A.3 self-parity sub-patterns; selection decision tree |
| D — Pattern F invariants registry | Table only (14 entries) | **EXTENDED** with 4-step playbook for new wrappers + D.2 wavelet-mode interaction note |
| E — Pattern I sign/scale convention | (new) | **NEW** — formalizes sign canonicalization discipline; 6 empirical instances |
| F — DSCD diagnostic-axis registry | (new) | **NEW** — DSCD-MLE / DSCD-EM / DSCD-Identifiability sub-taxonomy locked at S9; 4 instances |
| G — Pattern J resolution sub-patterns | (new) | **NEW** — J.A name-mapping / J.B tolerance widening / J.C alignment-via-metric; selection decision tree |
| H — Document maintenance + change log | (new) | **NEW** — update protocol + version history |

## Banked items closed at P-2 venue (5 of 13)

| Item | Status | P-2 venue |
|---|---|---|
| #1 Pattern I formalization (sign/scale convention) | **CLOSED** | Section E |
| #4 DSCD diagnostic-axis registry | **CLOSED** | Section F |
| #11 Pattern J alignment-via-metric (3rd resolution sub-pattern) | **CLOSED** | Section G (J.C) |
| #18 Pattern F wavelet-mode interaction | **CLOSED** | Section D.2 |
| #20 Pattern A.1 vs A.2 sub-pattern formalization | **CLOSED** | Section C |

P-1 closed 5 items at S15. P-2 closes 5 more. Cumulative
**10 of 13 evidence-complete items closed** at documentation
level after S16. Remaining 3 (items #6, #7, #9) distribute
to P-3 (Session 17).

## Empirical evidence summary documented in P-2

- **Pattern A wrapper count: 46** (66% of Phase 3 in-scope)
- **Pattern A.1 same-library sub-class: 18 wrappers** (all at 0.0 abs)
- **Pattern A.2 cross-package bit-exact: ~12 wrappers**
- **Pattern A.3 self-parity / paper-formula reimpl: ~10 wrappers**
- **Pattern F concrete invariants: 14**
- **Pattern J catalog entries: 11** across 6 sub-sections
- **Pattern J resolution sub-patterns: 3** (J.A name-mapping, J.B tolerance widening, J.C alignment-via-metric)
- **Pattern I sign/scale instances: 6 wrappers**
- **DSCD instances: 4 wrappers** across 3 sub-classes
- **Tier C / NO-REFERENCE-class: 3 wrappers**

## Verification

- File extended: `docs/engineering/parity_diagnostic_reference.md`
  (v0.3.0 → v1.0.0; +650 lines net).
- All Section A class references match
  `harness/tolerances.py` ladder entries.
- All Section D invariant types match
  `harness/structural_invariants.py` populated checkers.
- All Section B Pattern J entries cross-reference to
  audit reports under `tools/reference_parity/reports/`.
- No engine code changes (docs-only commit).
- No CI workflow changes.

## Cross-document consistency

P-2 v1.0.0 cross-references:

- **P-1 §3.3** (Tier propagation rules) — referenced at
  Section D.1 Step 4 for Diagnostic-tier CAVEAT
  non-propagation.
- **P-1 §5.1** (verdict_class taxonomy) — referenced at
  Section A as the binding directive; P-2 Section A
  explains *why* each class exists and *how* to pick one.
- **P-1 §10.1** (Pattern A.1 default) — referenced at
  Section C.1 as the operational default mandate.

## Next session

Session 17 — P-3 empirical findings synthesis.
`docs/engineering/parity_empirical_findings.md` (NEW —
created at Session 17). Will synthesize:

- **Item #6** Cross-batch findings doc design refinements
- **Item #7** Broader cross-batch findings synthesis
- **Item #9** p3_var headroom 8.1 orders + p3_vecm 13
  orders — Phase 3.5 tightening candidates
- **Item #10** EM-stochastic per-metric band tightening
  (canonical bands documented at P-1 §5.1 + P-2 Section A;
  tightening discussion deferred to P-3)

P-3 is intended as a **descriptive narrative document** —
the story of Phase 3 told through cumulative cross-batch
patterns. Distinct from P-1 (directive) and P-2
(reference / playbook). Story arc: 70 wrappers, 5 sessions
ahead of plan, 0 BLOCK; what made Phase 3 work; what it
empirically tells us about audit-engineering of TSL-class
wrappers.

After Session 17: Session 18 closeout (CI workflow
finalization, P-4 status tracker finalization, Phase 3
closeout commit).
