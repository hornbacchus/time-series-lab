# Phase 4 Session 12c — P-3 v1.2.0 ISSUED + v1.2.0 doc-set issuance event closes (Option C, 4 of 4)

**Date:** 2026-05-03
**Scope:** Fourth and final sub-session in S12 Option C
four-way split. Lands P-3 v1.2.0 issuance: 6 touchpoints
(P3-T1 through P3-T6 including §8 numbering fix per
Disposition 1) + 1 cross-doc codification (B-Phase4-S6-1
P-3 side per Disposition 3) + version-history block + change
log v1.2.0 entry. **Closes the v1.2.0 doc-set issuance
event** for P-1 + P-2 + P-3.
**Status:** COMPLETE.

## What changed

### P3-T6 — §8 numbering fix per Disposition 1 (~3 LOC)

Pre-existing Phase 3.5 v1.1.0 amendment artifact: §8
heading "What Phase 3 tells us about audit-engineering"
had subsections mislabeled `### 7.1`, `### 7.2`, `### 7.3`.
Renumbered to `### 8.1`, `### 8.2`, `### 8.3` per Disposition
1 (elevated from "out of scope" to declared touchpoint).

### P3-T1 — §3.4.3 NEW Phase 4 BVAR DD finding (~50 LOC)

NEW subsection §3.4.3 documenting Phase 4 S5 BYF #1 audit
(`p3_byf_bvar_constant_vol`) — the **first DOCUMENTED-
DIVERGENCE outcome in TSL parity history**:
- Origin: Phase 4 S5 (commit `2b54acb`)
- Empirical outcome: max_rel_diff=1.76 on Minnesota-prior
  coefficient posterior means
- Methodology gap analysis: prior-parameterization
  differences between TSL CCM-2019 Minnesota and R BVAR
  hierarchical Litterman; not a TSL bug
- Cross-references: P-2 §C.2 (audit entry + B-Phase4-S5-3
  sampler correction); P-2 §B.6.4 (R bvars install
  fragility); P-3 §3.4.2 (forward-provisioning interval)

### P3-T2 — §3.4.4 NEW Phase 4 stochvol partial DD finding (~30 LOC)

NEW subsection §3.4.4 documenting Phase 4 S6 BYF #3 audit
(`p3_byf_stochvol_partial`) — the **second DD outcome**:
- Origin: Phase 4 S6 (commit `8ab6b6e`)
- Empirical outcome: per-equation log-volatility posterior
  means at mu rel_diff < 5% (PASS); phi rel_diff in 5-10%
  (CAVEAT band); sigma_eta record-only (prior-driven)
- Methodology gap analysis: TSL CCM-KSC joint sampler vs
  R stochvol standalone univariate SV
- Cross-references: P-2 §C.2 (audit entry); P-3 §3.4.3
  (parallel BVAR DD finding)

### B-Phase4-S6-1 P-3 cross-doc — §3.4.5 NEW auto-DD pattern empirical-findings-side (~40 LOC)

NEW subsection §3.4.5 codifying the auto-DD pattern from
the P-3 empirical-findings-side perspective per Disposition
3 (cross-doc dual placement; P-2 §C.2.x is registry-side
framing; this is empirical-findings-side framing):
- Two empirical instances at Phase 4 (table)
- Pattern as institutional precedent (auto-DD outcomes are
  explicit acknowledgments of methodologically-known-a-
  priori framework gaps; preserves operator awareness +
  numerical-fidelity reporting)
- Cycle empirical evidence (2 of 70+ Pattern A audits = ~3%
  fraction; auto-DD is the safety net for cases with only
  methodologically-divergent references available)

### P3-T3 — §6.6 DD verdict reservation update (~10 LOC)

§6.6 stale framing updated:
- Title amended: "CLOSED — forward-provisioned at S1" →
  "CLOSED — forward-provisioned at S1; FIRST RUNTIME at
  Phase 4 S5"
- Update paragraph added: first concrete DD instance landed
  at Phase 4 S5 BYF #1; second at Phase 4 S6 BYF #3;
  cross-references to P-3 §3.4.3 + §3.4.4 + §3.4.2

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

Original deferral text preserved for institutional
record.

### P3-T5 — §6.10 NEW Phase 4 cycle close consolidation (~50 LOC)

NEW subsection §6.10 with cycle-disposition table for all
13 inheritance items + Phase 4.5+ explicit forward-banking
list (B-Phase4-S7-1 None-handling bug; B-Phase4-S10-3
smoke-test n_draws insufficiency). Closes with cycle-
planning-discipline-validated framing per B-Phase4-S11c-2-1
institutional precedent.

### Change log v1.2.0 entry + version header bump (~25 LOC)

P-3 header bumped v1.1.0 → v1.2.0 (cites Phase 4 Session
12c issuance date, closes v1.2.0 doc-set issuance event).
Comprehensive §10.1 change log entry covering all Phase 4
P-3 amendments organized by section (S5/S6/S9 §3.4
existing + S11a-1 §3.4.1 + S11a-3 §3.4.2 + S12c additions).
End-of-doc footer updated to v1.2.0 with explicit closing
of v1.2.0 doc-set issuance event.

## §13.4 marginal-overshoot acknowledgment

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~113 LOC |
| Phase 4 empirical 1.5-2× pattern | ~125-155 LOC predicted |
| **S12c actual** | **+207 net LOC** (225 insertions, 18 deletions) |
| Position vs default | +7 LOC over (~3.5%) |
| Position vs marginal-tolerance band (200-220) | within (3.5% over default) |
| §13.4 hard threshold (220 LOC; B-Phase4-S12b-1-1) | NOT BREACHED (207 < 220) |

§13.4-marginal-overshoot acknowledged: actual +207 net LOC
vs threshold 200 LOC; 3.5% over default; **WITHIN codified
marginal-tolerance band 200-220**. Per trigger explicit
directive ("If total lands at 200-220 LOC, marginal-
tolerance band applies; bank explicitly in findings doc"),
banking + commit per Decision 16C / S11a-2-2 marginal-
tolerance amendment precedent.

**Decision 21 operational test (recapping principled-
content-density vs measurement-variance):** the +94 LOC
overshoot vs trigger projection (~113) reflects expanded
content-density in §3.4.3 + §3.4.5 (each landed at ~2-4×
trigger sub-estimate). Per Decision 21: this is principled
content-density (each block serves the cycle-author /
future-cycle-planner / v1.2.0 doc-set reader populations
without removable redundancy). Within the 200-220 marginal-
tolerance band per S11a-2-2 amendment + per trigger
explicit acceptance.

**B-Phase4-S12c-1 banking:** marginal-tolerance band
correctly absorbed the principled content-density overshoot
when the trigger explicitly accepted the band. Future
cycle authors should distinguish:
- **Within marginal band (200-220) + content-density:**
  bank per acknowledgment + commit per trigger directive
  (this S12c case).
- **Within marginal band (200-220) + content-density +
  trigger absent or restrictive:** apply Decision 21
  operational test; if substantive content-density,
  consider split per Decision 17.
- **Above hard threshold (220+) + any content type:**
  surface to Chat per B-Phase4-S12b-1-1 hard-threshold
  precedent.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 36.15s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## Cross-reference verification

| Cross-reference | Target | Status |
|---|---|---|
| §3.4.3 → P-2 §C.2 BVAR DD entry | P-2 §C.2 Phase 4 additions (commit `5e0c93c`) | ✅ resolves |
| §3.4.3 → P-2 §B.6.4 | Cross-references resolve cleanly post-S11a-1 | ✅ resolves |
| §3.4.4 → P-2 §C.2 stochvol partial entry | P-2 §C.2 Phase 4 additions (commit `5e0c93c`) | ✅ resolves |
| §3.4.5 → P-2 §C.2.x + §C.2.y | P-2 codifications (commit `be2c323`) | ✅ resolves |
| §6.6 → P-3 §3.4.3 + §3.4.4 + §3.4.2 | All resolve internally | ✅ resolves |
| §6.10 cycle-disposition table | Phase 4 session commits | ✅ resolves |
| §7.1/§7.2/§7.3 closure refs | Phase 4 sessions S7/S8/S9, S2, S3 | ✅ resolves |
| §8 numbering fix | §8.1, §8.2, §8.3 anchor consistency | ✅ resolves |

## v1.2.0 doc-set issuance event — CLOSED

| Doc | Status | Issuance commit |
|---|---|---|
| **P-1** | **v1.2.0 ISSUED** ✅ | `c66af23` (S12a) |
| **P-2** | **v1.2.0 ISSUED** ✅ | `cfc6e54` (S12b-2) |
| **P-3** | **v1.2.0 ISSUED** ✅ | (this commit; S12c) |
| C-1 | v2.0.0 ISSUED ✅ | Phase 4 S10 (`193f4e7`) |

The Phase 4 v1.2.0 doc-set issuance event closes at this
S12c commit. All P-1/P-2/P-3/C-1 docs at their Phase 4
target versions. Only S13 (P-4 v1.2.0 + Phase 4 cycle close)
remains.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_empirical_findings.md` | Header bump v1.1.0 → v1.2.0; §3.4.3/§3.4.4/§3.4.5 NEW (BVAR DD + stochvol partial DD + auto-DD empirical-findings-side); §6.6 stale-framing update; §6.10 NEW Phase 4 cycle close consolidation; §7.1/§7.2/§7.3 closure dispositions; §8 numbering fix; §10.1 change log v1.2.0 entry; end-of-doc footer | +207 net |
| `docs/reference_parity_phase4/session_12c_findings.md` | NEW (this file) | ~165 |
| **Total (commit-counted)** | | **+207 LOC** |

## Disposition

| Item | Pre-S12c status | Post-S12c status |
|---|---|---|
| P-3 v1.2.0 issuance | banked (S12c scope) | **ISSUED** |
| 19 touchpoints across v1.2.0 doc-set | 13 of 19 LANDED | **19 of 19 LANDED** ✅ |
| 15 new codifications across v1.2.0 doc-set | 14 of 15 LANDED | **15 of 15 LANDED** ✅ |
| **v1.2.0 doc-set issuance event** | PARTIAL (3 of 4 docs) | **CLOSED** (4 of 4 docs at target version) |
| Phase 4 cycle progress | 12 of 13 sessions | **(no full-session count change; sub-session)** |

## Banked observations from S12c

**B-Phase4-S12c-1 — Marginal-tolerance band absorbs
principled content-density when trigger explicit.** S12c
landed at +207 LOC = 7 LOC over §13.1 default, well within
§13.4 marginal-tolerance band (200-220) but above the
hard-threshold-absent baseline. Per trigger explicit
directive, banking + commit. Bank as institutional
precedent for when within-band content-density + trigger-
explicit-acceptance combine: marginal-tolerance band can
absorb borderline content-density at user discretion via
trigger framing. Distinct from B-Phase4-S12b-1-1 hard-
threshold precedent (220+ surface-to-Chat absolute).

**B-Phase4-S12c-2 — v1.2.0 doc-set issuance event closed
on schedule.** Phase 4 cycle's v1.2.0 doc-set issuance
event (P-1 + P-2 + P-3 + C-1) closes at S12c. All 4
docs at Phase 4 target versions. The 4-phase S12 split
(Phase 1 + S12a + S12b-1 + S12b-2 + S12c) executed across
2 days (2026-05-02 to 2026-05-03) with 1 cascading sub-
split (Decision 22 S12b-1 → S12b-1-1 / S12b-1-2). Bank
as institutional precedent: doc-set issuance events spanning
multiple companion docs benefit from Phase-1 enumeration +
per-doc sub-session split + cascading discipline at
sub-session level when individual doc accumulator exceeds
§13.4 thresholds.

## Next session

**S13 — P-4 v1.2.0 + Phase 4 cycle close.**

Final Phase 4 session. Lands P-4 v1.2.0 (status tracker
update reflecting Phase 4 cycle outcomes) + Phase 4 cycle
close artifacts (cycle-close summary; carry-forward
register seeding for Phase 4.5+; engineering retrospective
on Phase 4 process). Engine baseline frozen at S11c-2 commit
`8c45de7` since 2026-05-02; doc-set baseline frozen at this
S12c commit. S13 is doc-only / cycle-close.

Trigger: ready to fire after S12c CI confirms green.
