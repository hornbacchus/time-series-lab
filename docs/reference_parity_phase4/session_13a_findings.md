# Phase 4 Session 13a — P-4 status tracker v1.2.0 ISSUED

**Date:** 2026-05-03
**Scope:** First of two sub-sessions in S13 cycle-close
split per Decision 24. Lands P-4 v1.2.0 issuance: 13
inheritance-item status updates + BYF row secondary verdict
lines + per-wrapper status updates + Phase 4.5+ deferred-
items section + v1.2.0 doc-set cross-references + version
bump. Closes the v1.2.0 doc-set issuance event for P-1 +
P-2 + P-3 + P-4 (all 4 docs at Phase 4 target versions).
S13b (next) lands the cycle-close artifact at
`docs/reference_parity_phase4/phase_4_cycle_close.md`.
**Status:** COMPLETE.

## What changed

### Header version bump + companion-doc cross-references (~12 LOC)

P-4 header status block updated:
- Version bumped v1.1.1 → v1.2.0 with Phase 4 cycle close
  framing (engine baseline frozen at S11c-2 commit `8c45de7`;
  doc-set baseline frozen at S12c-2 commit `bcbf243`)
- Companion doc references bumped: P-1 v1.1.0 → v1.2.0;
  P-2 v1.1.0 → v1.2.0; P-3 v1.1.0 → v1.2.0; C-1 v2.0.0
  added (Phase 4 S10 issuance)

### DD legend update (~5 LOC)

Status legend `DOCUMENTED-DIVERGENCE` entry updated: post-
Phase-4 empirical note adds first runtime instances at
Phase 4 S5 (`p3_byf_bvar_constant_vol`) + S6
(`p3_byf_stochvol_partial`) with cross-references to P-3
§3.4.3/§3.4.4 cycle-close documentation, P-2 §C.2 audit
entries, P-2 §C.2.x/§C.2.y auto-DD pattern + audit-design
discipline codifications.

### Phase 4 secondary verdict lines on BYF row (~30 LOC)

Three new entries appended after the BYF wrapper row:
- **BYF #1** secondary verdict: PASS-A.2 (DOCUMENTED-
  DIVERGENCE) at Phase 4 S5; sampler-correction at S12b-1-1.
  Cross-references P-2 §C.2 + P-3 §3.4.3 + §3.4.2.
- **BYF #2** Pattern A.3 verdict: PASS bit-exact 1318/1318
  cells at Phase 4 S4. Cross-reference P-2 §C.3.
- **BYF #3** secondary verdict: PASS-A.2 (DOCUMENTED-
  DIVERGENCE) at Phase 4 S6. Cross-references P-2 §C.2 +
  P-3 §3.4.4.

### Phase 4 carry-forward closure annotations (~20 LOC)

Existing §"Phase 4 carry-forward (NOT actioned in Phase
3.5)" section header amended: "ALL CLOSED at Phase 4".
Three carry-forward items receive closure annotations
in-table:
- P4-1: CLOSED at S7+S8+S9 (commits `ac91cb0` + `bcd162b`
  + `ff403dd`)
- P4-2: CLOSED at S2 (commits `050647e` + `6fb9590`)
- P4-3: CLOSED at S3 (commit `3bd5f61`)

Closing paragraph updated to reference Phase 4 cycle-close
section below.

### NEW Phase 4 cycle-close disposition table + per-wrapper updates + Phase 4.5+ deferred items + doc-set table (~85 LOC)

NEW top-level section "Phase 4 cycle close — disposition
table (S13a v1.2.0 issuance)" with five blocks:

1. **13-item inheritance register final disposition table**:
   one row per inheritance item with closure session + commit
   hash. All 13 items show CLOSED status.

2. **Per-wrapper Phase 4 amendments**:
   - 9 wrappers received `structural_invariants` declarations
     at S9 (P4-1.3); declarations dormant pending runner
     integration per B-Phase4-S9-2; cross-reference to P-2
     §D.1.5 audit-side declaration table.
   - 10 wrappers received docstring backfill at S11c (P-1
     §3.4 application); all comply with two-block convention
     per B-Phase4-S11c-1-2.

3. **Phase 4.5+ explicit forward-banking table**:
   - B-Phase4-S7-1 None-handling bug in 6 concrete checkers
     (Phase 4.5+ runner-integration concern)
   - B-Phase4-S10-3 smoke-test n_draws insufficiency
     (runner-integration concern)
   Framed as explicit-deferral, NOT silent-slippage. Cycle-
   planning discipline validated per B-Phase4-S11c-2-1
   institutional precedent.

4. **v1.2.0 doc-set issuance event table**:
   P-1 v1.2.0 (commit `c66af23` at S12a) + P-2 v1.2.0
   (commit `cfc6e54` at S12b-2) + P-3 v1.2.0 (commit
   `bcbf243` at S12c-2) + C-1 v2.0.0 (commit `193f4e7` at
   Phase 4 S10). 19/19 touchpoints + 15/15 codifications
   LANDED. References to P-1 §13.6 (Decision 21) + §12.2
   (B-Phase4-S10-1) for newly-codified principles.

5. **Documentation set (Phase 4 v1.2.0) table**:
   Updated docs table reflecting all 5 docs (P-1/P-2/P-3/
   P-4/C-1) at their Phase 4 target versions with issuance
   commits.

### Last-updated block update (~12 LOC)

P-4 "Last updated" block updated to reflect 2026-05-03
Phase 4 S13a P-4 v1.2.0 ISSUED status; prior 2026-05-01
BYF Mod-2 entry preserved as "Prior update" for historical
record.

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~140-220 LOC |
| Phase 4 empirical 1.5-2× pattern | ~210-440 LOC predicted (codification-density-mixed scope) |
| **S13a actual** | **+141 net LOC** (163 insertions, 22 deletions) |
| Position vs default | UNDER by 59 LOC (~30% headroom) |
| Position vs marginal-tolerance band | not engaged (well under default) |
| Position vs trigger projection | matches lower-bound projection (~140 LOC); below empirical 1.5-2× pattern range |

Clean commit. The actual landed substantially below the
empirical 1.5-2× pattern prediction — the work was content-
density-bounded (factual table updates + closure annotations
+ existing-section status amendments) rather than
codification-density-bounded (multiple new doctrinal
sections). The new "Phase 4 cycle close — disposition table"
section is a single new top-level section but its contents
are 4 tables + brief framing rather than expanded narrative.

This pattern matches B-Phase4-S12b-2-1 banking: content-
density-bounded sub-sessions land at 1.0-1.3× trigger
projection (closer to lower estimate), while codification-
density-bounded sub-sessions land at 1.5-2× (closer to upper
estimate or beyond). S13a is content-density-bounded.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 34.82s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## Cross-reference verification

| Cross-reference | Target | Status |
|---|---|---|
| Companion doc references | P-1/P-2/P-3 v1.2.0 + C-1 v2.0.0 | ✅ all resolve |
| BYF #1 secondary verdict line | P-2 §C.2 + P-3 §3.4.3 + §3.4.2 | ✅ resolves |
| BYF #2 verdict | P-2 §C.3 | ✅ resolves |
| BYF #3 secondary verdict line | P-2 §C.2 + P-3 §3.4.4 | ✅ resolves |
| P4-1/P4-2/P4-3 closure annotations | Phase 4 commits | ✅ all hash-verified |
| 13-item inheritance disposition table | All Phase 4 commits | ✅ all hash-verified |
| Per-wrapper amendments | S9 + S11c-1 + S11c-2 commits | ✅ resolve |
| v1.2.0 doc-set issuance table | S12a/S12b-2/S12c-2 commits | ✅ resolve |
| Phase 4.5+ deferred-items | B-Phase4-S7-1 + B-Phase4-S10-3 banking | ✅ documented |

## Disposition

| Item | Pre-S13a status | Post-S13a status |
|---|---|---|
| P-4 v1.2.0 issuance | banked (S13a scope) | **ISSUED** |
| **v1.2.0 doc-set + P-4 alignment** | partial (P-4 lagging at v1.1.1) | **CLOSED** (5 of 5 docs at Phase 4 target versions) |
| 13-item inheritance register P-4 reflection | not yet documented | **fully documented** in cycle-close section |
| BYF row Phase 4 secondary verdict lines | not yet added | **3 of 3 added** (BYF #1, #2, #3) |
| Per-wrapper Phase 4 amendments | not yet documented | **9 S9 declarations + 10 S11c docstring backfills documented** |
| Phase 4.5+ explicit forward-banking | banked in findings docs only | **codified in P-4 cycle-close section** |
| Phase 4 cycle progress | 12 of 13 sessions (92%) | **(no full-session count change; sub-session)** |

## Banked observations from S13a

**B-Phase4-S13a-1 — P-4 v1.2.0 issuance closed in single
sub-session.** S13a was projected at 140-220 LOC with
empirical 1.5-2× suggesting 210-440 LOC actual; landed at
+141 LOC (lower-bound match). Content-density-bounded scope
(factual table updates + closure annotations + status
amendments) routinely lands closer to lower-bound projection
than codification-density-bounded scope. Bank as institutional
precedent for trigger projection calibration: distinguish
content-density-bounded vs codification-density-bounded
scopes in trigger drafting; the empirical pattern differs
markedly between them (B-Phase4-S12b-2-1 + B-Phase4-S12a-2
parallel observations).

**B-Phase4-S13a-2 — Phase 4 v1.2.0 doc-set + P-4 alignment
complete.** All 5 Phase 4 docs at target versions (P-1
v1.2.0 + P-2 v1.2.0 + P-3 v1.2.0 + P-4 v1.2.0 + C-1
v2.0.0). 19/19 touchpoints + 15/15 codifications LANDED
across the v1.2.0 doc-set. S13b (next sub-session) lands
the Phase 4 cycle-close artifact (cycle-close summary +
carry-forward register seeding + engineering retrospective)
at `docs/reference_parity_phase4/phase_4_cycle_close.md`.

## Next sub-session

**S13b — Phase 4 cycle-close artifact** (~150-250 LOC
projected per Decision 24 framing).

Per master plan §15 S13 + Decision 24 split:
- Cycle-close summary (Phase 4 outcomes synthesis; aggregate
  numbers; major institutional precedents established)
- Carry-forward register seeding for Phase 4.5+ (B-Phase4-
  S7-1 + B-Phase4-S10-3 + any meta-banked items from S13a
  retrospective)
- Engineering retrospective on Phase 4 process (S11/S12
  cascading-split discipline empirical validation; trigger
  drafting calibration insights from B-Phase4-S12c-3 +
  B-Phase4-S13a-1; doc-set issuance event execution
  retrospective)

S13b is the FINAL Phase 4 session. After S13b commit + CI
green, Phase 4 cycle CLOSES.

Trigger: ready to fire after S13a CI confirms green.
