# Phase 4 Session 12c-2 — P-3 v1.2.0 ISSUED + v1.2.0 doc-set issuance event CLOSED (Decision 23B re-split, 2 of 2)

**Date:** 2026-05-03
**Scope:** Second of two sub-sub-sessions in S12c re-split per
Decision 23B. Lands P-3 §6 + §7 + §8 amendments + P-3
v1.2.0 issuance close (header bump + comprehensive change-
log entry). **Closes the v1.2.0 doc-set issuance event** for
P-1 + P-2 + P-3.
**Status:** COMPLETE.

## What changed

### P3-T6 — §8 numbering fix per Disposition 1 (~3 LOC)

Pre-existing Phase 3.5 v1.1.0 amendment artifact: §8
heading "What Phase 3 tells us about audit-engineering"
had subsections mislabeled `### 7.1`, `### 7.2`, `### 7.3`.
Renumbered to `### 8.1`, `### 8.2`, `### 8.3` per
Disposition 1 (elevated from "out of scope" to declared
touchpoint).

### P3-T3 — §6.6 DD verdict reservation update (~10 LOC)

§6.6 stale framing updated:
- Title amended: "CLOSED — forward-provisioned at S1" →
  "CLOSED — forward-provisioned at S1; FIRST RUNTIME at
  Phase 4 S5"
- Update paragraph: first concrete DD instance landed at
  Phase 4 S5 BYF #1; second at Phase 4 S6 BYF #3; cross-
  references to P-3 §3.4.3 + §3.4.4 + §3.4.2

### P3-T4 — §7 carry-forward closure dispositions (~25 LOC)

All three §7 carry-forward items closed at Phase 4:
- §7.1 P4-1 CLOSED at S7+S8+S9 (registry expansion + engine
  audit-field + wrapper wiring + O-2 threshold tightening +
  B-Phase4-S8-2 elevation)
- §7.2 P4-2 CLOSED at S2 (pathway c bypass; TSL_X13_BINARY_PATH
  + direct x13ashtml invocation; p3_x13 PASSes Linux post-
  Phase-4)
- §7.3 P4-3 CLOSED at S3 (pathway b auto-cap;
  n_surrogates_effective = max(100, min(default, T // 10)))

Original deferral text preserved for institutional record.

### P3-T5 — §6.10 NEW Phase 4 cycle close consolidation (~50 LOC)

NEW subsection §6.10 with cycle-disposition table for all
13 inheritance items + Phase 4.5+ explicit forward-banking
list (B-Phase4-S7-1 None-handling bug; B-Phase4-S10-3
smoke-test n_draws insufficiency). Closes with cycle-
planning-discipline-validated framing per B-Phase4-S11c-2-1
institutional precedent.

### Change log v1.2.0 entry + version header bump (~15 LOC)

P-3 header bumped v1.1.0 → v1.2.0 (cites Phase 4 Session
12c-2 issuance date; closes v1.2.0 doc-set issuance event).
Comprehensive §10.1 change log entry covering all Phase 4
P-3 amendments organized by section: §3.4.1 (S11a-1) +
§3.4.2 (S11a-3) + §3.4.3/§3.4.4/§3.4.5 (S12c-1) + §6.6
update + §6.10 NEW + §7.1/§7.2/§7.3 closure dispositions +
§8 numbering fix (S12c-2).

End-of-doc footer updated to v1.2.0 with explicit closing
of v1.2.0 doc-set issuance event for P-1 + P-2 + P-3.

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~58 LOC |
| Phase 4 empirical pattern (per B-Phase4-S12c-3 calibration) | ~75-116 LOC predicted (content-density-dominant) |
| **S12c-2 actual** | **+94 net LOC** (112 insertions, 18 deletions) |
| Position vs default | UNDER by 106 LOC (~53% headroom) |
| Position vs predicted range | within (94 LOC mid-range of 75-116 prediction) |
| Position vs marginal-tolerance band | not engaged |

Clean commit. Per Decision 21 operational test: §6.10 NEW
13-row inheritance-disposition table is principled content
density (each row documents specific item closure for
cycle-author / future-cycle-planner readers); §6.6 update
+ §7 closure dispositions + §8 numbering fix all serve
cycle-close operational documentation needs. All blocks
earn their LOC.

## Cross-reference verification

| Cross-reference | Target | Status |
|---|---|---|
| §6.6 → P-3 §3.4.3 + §3.4.4 + §3.4.2 | All resolve internally | ✅ resolves |
| §6.10 cycle-disposition table | Phase 4 session commits referenced | ✅ resolves |
| §7.1/§7.2/§7.3 closure refs | Phase 4 sessions S7/S8/S9, S2, S3 | ✅ resolves |
| §8 numbering fix | §8.1, §8.2, §8.3 anchor consistency | ✅ resolves |
| §10.1 change log v1.2.0 entry | All Phase 4 P-3 amendment sources | ✅ resolves |

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 29.40s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 doc-set issuance event — CLOSED

| Doc | Status | Issuance commit |
|---|---|---|
| **P-1** | **v1.2.0 ISSUED** ✅ | `c66af23` (S12a) |
| **P-2** | **v1.2.0 ISSUED** ✅ | `cfc6e54` (S12b-2) |
| **P-3** | **v1.2.0 ISSUED** ✅ | (this commit; S12c-2) |
| **C-1** | **v2.0.0 ISSUED** ✅ | Phase 4 S10 (`193f4e7`) |

The Phase 4 v1.2.0 doc-set issuance event closes at this
S12c-2 commit. All P-1 / P-2 / P-3 / C-1 docs at their
Phase 4 target versions. Only S13 (P-4 v1.2.0 + Phase 4
cycle close) remains.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_empirical_findings.md` | Header bump v1.1.0 → v1.2.0; §6.6 stale-framing update; §6.10 NEW Phase 4 cycle close consolidation; §7.1/§7.2/§7.3 closure dispositions; §8 numbering fix; §10.1 change log v1.2.0 entry; end-of-doc footer | +94 net |
| `docs/reference_parity_phase4/session_12c_2_findings.md` | NEW (this file) | ~155 |
| **Total (commit-counted)** | | **+94 LOC** |

## Disposition

| Item | Pre-S12c-2 status | Post-S12c-2 status |
|---|---|---|
| P-3 §6 + §7 + §8 amendments | banked (S12c-2 scope) | **4 of 4 LANDED** (P3-T3, T4, T5, T6) |
| **P-3 v1.2.0 issuance** | PARTIAL (§3.4 amendments at S12c-1) | **ISSUED** |
| 19 touchpoints across v1.2.0 doc-set | 15 of 19 LANDED | **19 of 19 LANDED** ✅ |
| 15 new codifications across v1.2.0 doc-set | 15 of 15 LANDED | **15 of 15 LANDED** ✅ (no codifications in S12c-2 scope) |
| **v1.2.0 doc-set issuance event** | PARTIAL (P-1 + P-2 + P-3 §3.4 done) | **CLOSED** ✅ (4 of 4 docs at target version) |
| Phase 4 cycle progress | 12 of 13 sessions | **(no full-session count change; sub-sub-session)** |

## Banked observations from S12c-2

**B-Phase4-S12c-4 (NEW per Decision 23B) — Revert-and-re-
split pattern as institutional-inconsistency correction
discipline.** Decision 23B applied revert-and-re-split to
S12c original (commit `f0833c8`) when the disposition was
institutional-inconsistency under Decision 17 + B-Phase4-
S12b-1-1 hard-threshold precedent + B-Phase4-S12b-1-2-C
extension, despite clean execution per trigger as written.
The revert (commit `73351d7`) preserves audit trail per
B-Phase4-S11b-1-3 discipline; re-split into S12c-1 + S12c-2
produces institutional consistency.

This extends B-Phase4-S11b-1-3's revert-and-re-commit
discipline to a different scope:
- **B-Phase4-S11b-1-3 case (S11b-1):** original commit was
  substantive-content-violation (inline-rationale bloat
  classified as measurement-variance); revert + re-commit
  with tightened content corrected the violation.
- **B-Phase4-S12c-4 case (S12c-2):** original commit was
  institutional-inconsistency (marginal-tolerance band
  absorbed content-density at trigger explicit acceptance,
  contradicting Decision 17 / B-Phase4-S12b-1-1 hard-
  threshold precedent); revert + re-split corrected the
  inconsistency.

Bank as institutional precedent: when trigger drafting
produces institutional-inconsistency disposition even with
clean execution, revert-and-re-split is the appropriate
correction discipline. The audit trail value of preserving
the revert outweighs the noise of the two-commit
correction footprint.

**B-Phase4-S12c-5 (NEW) — v1.2.0 doc-set issuance event
CLOSED on schedule (with one cascading sub-split + one
revert).** The Phase 4 v1.2.0 doc-set issuance event spanned
S12 Phase 1 + S12a + S12b-1 (split into S12b-1-1 +
S12b-1-2 per Decision 22) + S12b-2 + S12c (split into
S12c-1 + S12c-2 per Decision 23B revert + re-split). Total:
6 successful sub-session commits + 1 reverted commit +
1 revert commit = 8 commits across 2 days (2026-05-02 to
2026-05-03). All 4 docs at Phase 4 target versions; 19/19
touchpoints + 15/15 codifications LANDED.

Bank as institutional precedent: doc-set issuance events
spanning multiple companion docs benefit from Phase-1
enumeration + per-doc sub-session split + cascading
discipline at sub-session level when individual doc
accumulator exceeds §13.4 thresholds OR when trigger-
drafting produces institutional-inconsistency disposition.

## Next session

**S13 — P-4 v1.2.0 + Phase 4 cycle close.**

Final Phase 4 session. Lands P-4 v1.2.0 (status tracker
update reflecting Phase 4 cycle outcomes) + Phase 4 cycle
close artifacts (cycle-close summary; carry-forward
register seeding for Phase 4.5+; engineering retrospective
on Phase 4 process).

Engine baseline frozen at S11c-2 commit `8c45de7` since
2026-05-02; doc-set baseline frozen at this S12c-2 commit.
S13 is doc-only / cycle-close.

Trigger: ready to fire after S12c-2 CI confirms green.
