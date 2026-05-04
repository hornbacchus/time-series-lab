# Phase 5 Session 0 (S0-MASTERPLAN-1-A) — Master plan §1-§3 (Decision 28 cascading split, 1 of 3)

**Date:** 2026-05-03
**Scope:** First of three sub-sub-sessions in S0-MASTERPLAN
cascading split per Decision 28. Lands the Phase 5 master plan
at `plans/reference_parity_phase5_master_plan.md` in initial
state with header + framing + §1 cycle context + §2 cycle
objective + §3 inheritance register. S0-MASTERPLAN-1-B (next)
appends §4 institutional discipline standing application + §5
cycle-scope expansion expectation; S0-MASTERPLAN-2 (final)
appends §15 session enumeration + §16 Phase 6 inheritance
handoff anticipation + §17 master plan version history.
**Status:** COMPLETE.

## Why this is a sub-sub-sub-session (Decision 28 four-level cascading split)

S0-MASTERPLAN-1 unsplit attempt produced master plan §1-§5 at
+264 LOC — **44 LOC over §13.4 hard threshold (220)** per
B-Phase4-S12b-1-1 hard-threshold precedent. Decision 21
operational test on the artifact: each section serves distinct
reader populations (Phase 5 cycle authors + future cycle
archaeologists); §13.4 marginal-tolerance band (200-220) cannot
absorb the 44-LOC overshoot; principled content density NOT
measurement-variance.

§13.2 bundled-category exception failed per-category LOC
criterion: master plan §1+§2+§3+§4+§5 single artifact > 220
hard threshold. Per Decision 17 / B-Phase4-S12c-4 / B-Phase4-
S12c-3 precedents, content-density spill at hard threshold
triggers split, not band absorption.

Decision 28 confirmed Option B four-level cascading split per
trigger pre-planned natural seam:
- S0-MASTERPLAN-1-A: §1-§3 (~155 LOC; cycle context + objective
  + inheritance register)
- S0-MASTERPLAN-1-B: §4-§5 + footer (~115 LOC; standing
  discipline + expansion expectation)
- S0-MASTERPLAN-2: §15-§17 (~210 LOC; session enumeration +
  Phase 6 anticipation + version history; pre-planned
  secondary split if exceeds 220 LOC)

The recursion is appropriate, not redundant: Phase 5 master
plan v1 — the cycle's first commit — applies the very §13
discipline that Phase 4 codified, through cascading split. The
Phase 5 cycle inherits Phase 4's institutional discipline
framework cradle-to-grave: from the cycle's first commit
(this one) through every subsequent session.

Bank as institutional precedent (B-Phase5-S0-2; lands at
S0-MASTERPLAN-1-B findings doc per sequencing discipline).

## What changed

### `plans/reference_parity_phase5_master_plan.md` NEW (~156 LOC)

Master plan v1 lands in initial state with the following
content:

**Header + framing** (~15 LOC): file-purpose framing per
master plan v1 convention (status block; cycle naming; audience
identification; origin citation to Phase 4 cycle-close artifact
commit `3ac8c0e` + P-4 v1.2.0 inheritance register commit
`64ade89`).

**§1 Cycle context** (~50 LOC):
- §1.1 Phase 4 closure framing + naming evolution: cycle's
  institutional record summary (5 docs at target versions; 13
  inheritance items resolved; 19/19 touchpoints + 15/15
  codifications LANDED at v1.2.0 doc-set; 9 §13 application
  instances; 2 forward-banked items). Naming evolution Phase
  4.5+ → Phase 5: full-cycle-class scope (engine-side
  architectural work beyond bounded amendments) is correct
  framing. Phase 4.5+ references in v1.2.0 doc-set remain
  unchanged via reader convention; future patch-version
  P-4 update can substitute at convenient occasion.
- §1.2 Institutional discipline inheritance summary: Phase 5
  inherits the full §13 discipline framework codified at Phase
  4 (binding rules + retrospective examples + marginal-
  tolerance amendment + Decision 21 principled-content-density
  distinction). Specific standing-application provisions
  documented at §4 (lands at S0-MASTERPLAN-1-B).

**§2 Cycle objective** (~25 LOC):
- Primary: runner integration of structural-invariants
  framework. Wire `check_invariants` lifecycle method into
  harness runner so that 9 wrapper declarations landed dormant
  at Phase 4 S9 (P4-1.3) become empirically active.
- Secondary: B-Phase4-S7-1 (None-handling bug in 6 concrete
  invariant checkers) + B-Phase4-S10-3 (smoke-test n_draws
  insufficiency) + surface-during-integration scope.
- Out of scope: new wrapper additions beyond Phase 4 baseline
  (84 wrappers); v1.3.0 doc-set issuance (deferred to Phase 6
  unless cycle-internal accumulation triggers); ad-hoc engine
  modifications outside structural-invariants + smoke-test
  scope.

**§3 Inheritance register** (~60 LOC):
- §3.1 Forward-banked items (concrete + explicit at Phase 4
  S7+S10): B-Phase4-S7-1 + B-Phase4-S10-3 with closure-path
  framing.
- §3.2 Dormant declarations table (10 wrappers): per-row
  audit-script + invariant + tolerance + Phase 5 sub-domain
  classification per P-2 §D.1.5 audit-side declaration table;
  per Phase 4 Check-in #2 deep-verification probe.
- §3.3 Phase 5 cycle-internal scope additions: sub-domain (iv)
  catch-all reserved for items surfacing during Phase 5
  runner-integration empirical work. Anticipated category
  types: runner-side architectural concerns; new invariant
  types beyond Phase 4 baseline; tolerance-value calibration
  adjustments.

**Footer** (~6 LOC): explicit notice that §4-§5 land at
S0-MASTERPLAN-1-B per Decision 28; §15-§17 land at
S0-MASTERPLAN-2.

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection (S0-MASTERPLAN-1-A split) | ~155 LOC |
| Phase 4 empirical 1.0-1.3× pattern (content-density-bounded) | ~155-200 LOC predicted |
| **S0-MASTERPLAN-1-A actual** | **+156 net LOC** (single new file) |
| Position vs default | UNDER by 44 LOC (~22% headroom) |
| Position vs marginal-tolerance band | not engaged (well under default) |
| Position vs predicted range | matches lower-bound projection (~155) very closely |

Clean commit. Per Decision 21 operational test (applied at
staging time): each block (§1.1-§1.2 cycle context + §2
objective + §3.1-§3.3 inheritance register) serves the Phase 5
cycle author / future cycle archaeologist reader populations;
no removable redundancy. Content density well within §13.1
default — no §13.4 marginal-tolerance band engagement needed.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 30.33s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit (R 4.5.3 match; all R + Python packages match; manifest stale=False) |
| Validation script live state | ✅ exit 0 (MANIFEST: 23 Python + 21 R packages; install matrix consistent) |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## Cross-reference verification

| Cross-reference | Target | Status |
|---|---|---|
| §1.1 → Phase 4 cycle-close artifact | S13b-2 commit `3ac8c0e` | ✅ resolves |
| §1.1 → P-4 v1.2.0 inheritance register | S13a commit `64ade89` | ✅ resolves |
| §1.2 → §13 framework codification | P-1 §13 + P-1 §13.5 + P-1 §13.6 | ✅ resolve |
| §3.1 → B-Phase4-S7-1 + B-Phase4-S10-3 | per-session findings docs | ✅ resolve |
| §3.2 → P-2 §D.1.5 audit-side declaration table | P-2 v1.2.0 commit `cfc6e54` | ✅ resolves |
| §3.2 → Phase 4 Check-in #2 deep-verification | Check-in #2 minutes | ✅ documented |

## Disposition

| Item | Pre-S0-MASTERPLAN-1-A status | Post-S0-MASTERPLAN-1-A status |
|---|---|---|
| Master plan §1-§3 | banked (S0-MASTERPLAN-1-A scope) | **LANDED** |
| Master plan §4-§5 | banked (S0-MASTERPLAN-1-B scope) | deferred to S0-MASTERPLAN-1-B |
| Master plan §15-§17 | banked (S0-MASTERPLAN-2 scope) | deferred to S0-MASTERPLAN-2 |
| Phase 5 cycle progress | new cycle (0 of ~14 nominal) | **(no full-session count change; sub-sub-session)** |

## Banked observations from S0-MASTERPLAN-1-A

(Per Decision 27 / 28 sequencing discipline: institutional
precedent banking entries land in the sequence's final
findings doc once all sub-sub-sessions are complete. S0-
MASTERPLAN-1-A findings doc documents only execution +
verification + disposition for this sub-sub-session. B-Phase5-
S0-1 and B-Phase5-S0-2 banking entries land in S0-MASTERPLAN-
1-B or S0-MASTERPLAN-2 findings doc per sequencing.)

## Next sub-sub-session

**S0-MASTERPLAN-1-B — Master plan §4 + §5 + footer append** (~115 LOC projected).

Per Decision 28 split:
- §4 Institutional discipline standing application (~95 LOC):
  - §4.1 §13 budget standing application (200 default; 200-220
    marginal band; 220 hard threshold; cascading-split
    discipline)
  - §4.2 Trigger-drafting standing language (B-Phase4-S12c-3
    precedent verbatim citation)
  - §4.3 Pre-flight enumeration discipline (S12 Phase 1 pattern)
  - §4.4 Correction patterns (revert-and-re-commit per
    Decision 17; revert-and-re-split per Decision 23B)
  - §4.5 LOC estimate calibration awareness (1.5-2× pattern
    for codification-density-bounded; 1.1-1.3× pattern for
    content-density-bounded)
- §5 Cycle-scope expansion expectation (~15 LOC):
  - ~14 nominal sessions → ~21-28 expected actual (Phase 4
    pattern: 13 nominal → 26+ actual)
  - Honest framing of cycle expansion via §13 discipline
    application not scope creep
- Footer (~5 LOC): explicit notice that §15-§17 land at
  S0-MASTERPLAN-2 per Decision 28
- B-Phase5-S0-1 (NEW; master plan codification-density-class
  observation) + B-Phase5-S0-2 (NEW; cycle cradle-to-grave §13
  application pattern) banking entries land in S0-MASTERPLAN-
  1-B findings doc per sequencing

S0-MASTERPLAN-1-B trigger: ready to fire after S0-MASTERPLAN-
1-A CI confirms green.

After S0-MASTERPLAN-2 commit + CI green:
- Phase 5 master plan v1 fully landed
- §1-§5 + §15-§17 sections collectively serve as cycle's
  institutional planning artifact
- Phase 5 cycle execution sessions (S1, S2, ...) begin per
  master plan §15 enumeration
