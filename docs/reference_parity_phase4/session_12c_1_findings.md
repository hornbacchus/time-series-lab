# Phase 4 Session 12c-1 — P-3 §3.4 amendments (Decision 23B revert + re-split, 1 of 2)

**Date:** 2026-05-03
**Scope:** First of two sub-sub-sessions in S12c re-split per
Decision 23B (revert original f0833c8; re-split into S12c-1
+ S12c-2). Lands 2 P-3 §3.4 touchpoint amendments + 1
cross-doc codification (B-Phase4-S6-1 P-3 side per
Disposition 3). S12c-2 lands the §6 + §7 + §8 amendments
+ P-3 v1.2.0 issuance close.
**Status:** COMPLETE.

## Why this is a sub-sub-session (Decision 23B re-split)

S12c original (commit `f0833c8`, 2026-05-03) landed at +207
LOC — within §13.4 marginal-tolerance band (200-220) per
trigger explicit acceptance language ("If total lands at
200-220 LOC, marginal-tolerance band applies"). Per
Decision 17 + B-Phase4-S12b-1-1 hard-threshold precedent +
B-Phase4-S12b-1-2-C extension, this disposition was
institutionally inconsistent: §13.4 marginal-tolerance band
is for **measurement-variance** overshoot (formatting /
edit-vs-replace LOC accounting), NOT content-density
overshoot. The Decision 21 operational test was not
applied at S12c original commit time; the trigger language
permitted band absorption without the test.

User Decision 23B disposition: revert + re-split per
pre-planned natural seam from S12c trigger. Master history
preserves the audit trail: original S12c → revert (commit
`73351d7`) → S12c-1 → S12c-2.

The trigger drafting error is acknowledged at
B-Phase4-S12c-3 banking (S12c-2 findings doc); Code's
execution applied trigger as written, so the correction is
institutional consistency rather than execution issue.

## What changed

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

### B-Phase4-S6-1 P-3 cross-doc — §3.4.5 NEW auto-DD pattern empirical-findings-side (~22 LOC)

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

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~55 LOC |
| Phase 4 empirical 1.5-2× pattern | ~85-110 LOC predicted |
| **S12c-1 actual** | **+102 net LOC** (102 insertions, 0 deletions) |
| Position vs default | UNDER by 98 LOC (~49% headroom) |
| Position vs marginal-tolerance band | not engaged (well under default) |
| Position vs predicted range | within (102 LOC at upper end of 85-110 prediction) |

Clean commit. Per Decision 21 operational test: each block
(§3.4.3 + §3.4.4 + §3.4.5) serves the cycle-author /
future-cycle-planner / v1.2.0 doc-set reader populations.
No removable redundancy. Principled content density well
within §13.1 default — no §13.4 marginal-tolerance band
engagement needed.

## Cross-reference verification

| Cross-reference | Target | Status |
|---|---|---|
| §3.4.3 → P-2 §C.2 BVAR DD entry | P-2 §C.2 Phase 4 additions (commit `5e0c93c`) | ✅ resolves |
| §3.4.3 → P-2 §B.6.4 | P-2 (commit `1d8b0ff` + S12b-1-1) | ✅ resolves |
| §3.4.3 → P-3 §3.4.2 | Forward-provisioning interval (commit `5131e39`) | ✅ resolves |
| §3.4.4 → P-2 §C.2 stochvol partial entry | P-2 §C.2 Phase 4 additions (commit `5e0c93c`) | ✅ resolves |
| §3.4.4 → P-3 §3.4.3 | Internal sibling | ✅ resolves |
| §3.4.5 → P-2 §C.2.x + §C.2.y | P-2 codifications (commit `be2c323`) | ✅ resolves |

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 36.59s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S12c-1 contributes touchpoint amendments + cross-doc
codification to P-3 v1.2.0 issuance. The full v1.2.0
issuance event for P-3 closes at S12c-2 (which lands §6 +
§7 + §8 amendments + change-log entry + version bump).

**Cumulative state after S12c-1:**

| Doc | Status |
|---|---|
| **P-1** | **v1.2.0 ISSUED** (commit `c66af23`) ✅ |
| **P-2** | **v1.2.0 ISSUED** (commit `cfc6e54`) ✅ |
| P-3 | v1.2.0 PARTIAL (S12c-1 §3.4 amendments LANDED; §6 + §7 + §8 + issuance close at S12c-2) |
| C-1 | v2.0.0 (Phase 4 S10) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_empirical_findings.md` | §3.4.3 NEW (BVAR DD finding); §3.4.4 NEW (stochvol partial DD finding); §3.4.5 NEW (auto-DD empirical-findings-side codification) | +102 net |
| `docs/reference_parity_phase4/session_12c_1_findings.md` | NEW (this file) | ~145 |
| **Total (commit-counted)** | | **+102 LOC** |

## Disposition

| Item | Pre-S12c-1 status | Post-S12c-1 status |
|---|---|---|
| P-3 §3.4 amendments (P3-T1 + P3-T2 + B-Phase4-S6-1) | banked (S12c-1 scope) | **3 of 3 LANDED** |
| P-3 §6/§7/§8 amendments + issuance close | banked (S12c-2 scope) | **deferred to S12c-2** |
| 19 touchpoints across v1.2.0 doc-set | 13 of 19 LANDED post-S12b-2 | **15 of 19 LANDED** (P3-T1 + P3-T2 added) |
| 15 new codifications across v1.2.0 doc-set | 14 of 15 LANDED post-S12b-2 | **15 of 15 LANDED** (B-Phase4-S6-1 P-3 cross-doc landed) |

## Banked observations from S12c-1

**B-Phase4-S12c-3 (NEW) — Trigger language must explicitly
preserve content-vs-measurement distinction for marginal-
tolerance applications.** Permissive trigger language at
S12c original ("If total lands at 200-220 LOC, marginal-
tolerance band applies; bank explicitly in findings doc")
permitted institutional-inconsistency disposition: §13.4
marginal-tolerance band absorbed +207 LOC content-density
overshoot without applying Decision 21 principled-content-
density operational test. The disposition violated
B-Phase4-S12b-1-1 hard-threshold precedent +
B-Phase4-S12b-1-2-C extension. Trigger drafts henceforth
must specify: "If total lands in 200-220 LOC band, apply
Decision 21 principled-content-density test before deciding
marginal-tolerance vs split. Content-density classification
→ split per Decision 17 + B-Phase4-S12b-1-1. Measurement-
variance classification → band absorption with explicit
findings-doc banking." Bank as institutional precedent for
trigger-drafting discipline.

## Next sub-sub-session

**S12c-2 — P-3 §6/§7/§8 amendments + P-3 v1.2.0 issuance
close (~58 LOC projected).**

Per Decision 23B re-split + S12c trigger pre-planned seam:
- P3-T3 — §6.6 DD verdict reservation update (~5 LOC)
- P3-T4 — §7 Phase 4 carry-forward closure dispositions
  (~15 LOC)
- P3-T5 — §6.10 NEW BYF cycle close consolidation (~20 LOC)
- P3-T6 — §8 section numbering fix (~3 LOC; Disposition 1)
- P-3 v1.2.0 issuance close mechanics: change log v1.2.0
  entry + version-history block + version bump (~15 LOC)
- B-Phase4-S12c-4 (NEW) banking entry — Revert-and-re-split
  pattern (Decision 23B application as extension of
  B-Phase4-S11b-1-3 revert-and-re-commit discipline)

Phase 4 empirical 1.5-2× pattern suggests ~85-115 LOC
actual for content-density-mixed-with-issuance-mechanics
scope. Comfortably under §13.4 default 200 LOC.

S12c-2 closes P-3 v1.2.0 transition AND the v1.2.0 doc-set
issuance event for P-1 + P-2 + P-3.

Trigger: ready to fire after S12c-1 CI confirms green.
