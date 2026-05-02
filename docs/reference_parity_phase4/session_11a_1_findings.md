# Phase 4 Session 11a-1 — Doc patches batch 1 (3 inheritance items)

**Date:** 2026-05-02
**Scope:** First of three sub-sessions in the S11a three-way
split. Three inheritance items dispositioned via doc patches
to P-1, P-2, P-3.
**Status:** COMPLETE.

## Why this is a sub-session

Per Phase 4 retrospective Check-in #2 + S11a §13.4 spill
detection (projected 384 LOC vs 200 LOC default budget +
220 LOC trigger ceiling): user disposition Option D — three-
way split, NOT two-way bundle.

The three-way split honors §13.2 sharpened criteria
(architectural inseparability + categorical orthogonality
+ per-category LOC under threshold; ALL three required, not
"most of three"). The Option C two-way bundle would have
failed architectural inseparability (P-1 §13 and P-3
§3.4.2 are both forward-looking governance codifications
but don't depend on each other). User: "Accepting Option C
at the same session that codifies §13.2 would be the worst
possible institutional precedent."

S11a-1 takes the three small-to-medium items (each
self-contained, no cross-item dependency). S11a-2 takes
Decision A (P-1 §13 NEW). S11a-3 takes Decision 3 (P-3
§3.4.2 NEW). Each sub-session gets its own commit, CI
verification, and findings doc.

## What changed

### Item #4 — P-2 §B.6.4 bvars trigger doc patch

**Origin:** Phase 4 master plan §15 S11 catalog item.

**Insertion location:** `docs/engineering/parity_diagnostic_reference.md`
between §B.6.3 (statsmodels-x13ashtml integration deferred)
and §B.D (Platform-binary integration sub-pattern).

**Content added (~56 LOC):**
- Documents R `bvars` package install fragility on R 4.5.3
  observed across multiple Phase 3 + Phase 4 install
  attempts. Specifically: `install.packages("bvars")`
  succeeds but `library(bvars)` raises namespace-load error
  due to compiled-binary / system-library mismatch
  incompatible with R 4.5.x ABI changes.
- Operational impact: at Phase 4 S5, the BVAR-SV constant-
  volatility cross-check (BYF candidate #1) needed Pattern
  A.2 secondary reference; `bvars` was the natural
  candidate but unavailable; fell back to R `BVAR::bvar()`
  with different prior parameterization → DOCUMENTED-
  DIVERGENCE outcome.
- Recommended fallback hierarchy for future BVAR-family
  Pattern A.2 audits: bvars (if available) → BVAR (with DD
  expectation) → BMR::bvarm() → Tier-B paper-formula
  reimpl per Banbura-Giannone-Reichlin 2010.
- Pattern statement: "R-package availability is a real-
  world constraint on Pattern A.2 secondary-reference
  selection. The audit-design phase must verify package
  install AND library() load on the target R version
  BEFORE committing to a specific reference. A reference
  that's 'in CRAN' is not the same as a reference that
  'loads on R 4.5.3 today'."

### Item #9 — P-1 §6.1 tier classification clarification

**Origin:** Phase 4 master plan §15 S11 catalog item +
master-plan §15.1 amendment site catalog (~20 LOC
estimate; ~30 LOC actual).

**Insertion location:** `docs/engineering/parity_standard.md`
appended to §6.1 (Fast tier) before §6.2 (Slow tier).

**Content added (~30 LOC):**
- Explicit clarification that §6.1 / §6.2 tier
  classification refers to per-check audit RUNTIME (the
  wall-clock cost of running a single parity check end-
  to-end), NOT to:
  - Engineering work runtime needed to author a check
    (covered separately by master plan §11.13 + the
    forthcoming P-1 §13 per-session LOC budget protocol).
  - C-1 §1.2 "Standard tier" framework — which is about
    binding-vs-aspirational, NOT runtime.
- Cross-document tier-axis disambiguation table:
  | Doc | Section | Axis | Values |
  |---|---|---|---|
  | P-1 | §6.1/§6.2 | per-check audit runtime | fast / slow |
  | C-1 | §1.2 | per-requirement binding | B / A |
  | P-1 | §13 (new) | per-session LOC budget | within / spill |
- Forward-references P-1 §13 (which lands at S11a-2; this
  S11a-1 amendment intentionally pre-references it so
  S11a-2 doesn't need to retroactively patch the
  cross-reference).

### Item O-1 — P-3 §3.4.1 banking (near-unit-root VAR companion)

**Origin:** BYF Mod-2 cycle banked observation; consumed
at Phase 4 S9 via O-2 Pattern F threshold tightening
(<0.999 → <0.9995). Master plan §15 S11 catalog item.

**Insertion location:** `docs/engineering/parity_empirical_findings.md`
between §3.4 (Pattern A.1 production-locked across 4
dimensions) and §4 (Surprises and reversals) as new §3.4.1.

**Content added (~54 LOC):**
- Documents BYF Mod-2 34-maturity fixture's
  `max|λ_companion| = 0.9988` observation as institutional
  precedent.
- Pre-S9 vs post-S9 verdict comparison table (with
  threshold transitions and margin to threshold for both
  10-mat and 34-mat fixtures).
- Pattern as institutional precedent: "Banked observations
  that flag near-threshold operational margins should be
  audited at next-cycle close; the corrective action (here:
  threshold tightening to add explicit early-warning band)
  is preferable to ad-hoc relaxation of the strict-
  instability boundary."
- Two-band recommendation for future audit cycles:
  `<PASS_threshold` for PASS; `<BLOCK_threshold` for
  early-warning BLOCK; `≥BLOCK_threshold` for strict BLOCK.
- Cross-references to BYF Mod-2 findings doc (origin) and
  Phase 4 S9 findings doc (corrective action consumed).

## §13.4 spill compliance

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC (excluding findings doc) |
| Sub-session projection | ~141 LOC |
| **Sub-session actual** | **+139 net LOC** (P-2 +56 + P-3 +54 + P-1 +29) |
| Margin under default | 61 LOC (30% headroom) |

S11a-1 commits unblocked under §13.1 default; no §13.2
bundled-category exception engagement needed; no §13.4
spill protocol re-engagement.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | n/a (no engine code touched) |
| Per-wrapper test suite green | n/a (no wrappers touched) |
| `parity-fast --check-environment` clean | n/a (no MANIFEST.toml changes) |
| `parity-fast` tier outcome distribution unchanged | n/a (doc-only) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

Doc-only sub-session; verification surface is the docs
themselves plus post-push CI confirming no Markdown-side
regressions (none expected; CI does not parse Markdown).

## v1.2.0 amendment ledger update

S11a-1 contributes to the v1.2.0 ledger per master plan
§15.1:

| Doc | Section | Source | LOC |
|---|---|---|---|
| P-1 | §6.1 (clarification) | S11a-1 #9 | ~30 |
| P-2 | §B.6.4 (NEW) | S11a-1 #4 | ~56 |
| P-3 | §3.4.1 (NEW) | S11a-1 O-1 | ~54 |

**Cumulative ledger after S11a-1 (pre-S11a-2 / pre-S11a-3):**

| Doc | LOC accumulator |
|---|---|
| P-1 | ~75 (S1 §8.5) + ~30 (S11a-1 §6.1) = **~105** |
| P-2 | ~205 (S4-S9) + ~56 (S11a-1 §B.6.4) = **~261** |
| P-3 | ~70 (S5-S6 + S9) + ~54 (S11a-1 §3.4.1) = **~124** |
| C-1 | ~205 (S1 + S10) |
| **Total** | **~695 LOC** (over §11.11 ceiling 600) |

**§11.11 cumulative ledger ceiling crossed at S11a-1.** S12
v1.2.0 issuance will need to split into S12a/S12b per
§11.11 trigger semantics. S11a-2 + S11a-3 + S11b + S11c
will further increase the cumulative ledger. Confirmed
expectation; no Phase 4 in-session action required at S11a-1.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_diagnostic_reference.md` | New §B.6.4 between §B.6.3 and §B.D | +56 |
| `docs/engineering/parity_empirical_findings.md` | New §3.4.1 between §3.4 and §4 | +54 |
| `docs/engineering/parity_standard.md` | §6.1 clarification block + cross-axis disambiguation table | +29 |
| `docs/reference_parity_phase4/session_11a_1_findings.md` | NEW (this file) | ~150 |
| **Total (commit-counted; excludes findings doc)** | | **+139 LOC** |

## Disposition

| Item | Pre-S11a-1 status | Post-S11a-1 status |
|---|---|---|
| BYF candidate #4 (P-2 §B.6.4 bvars trigger) | banked | **CLOSED** — P-2 §B.6.4 NEW |
| BYF candidate #9 (P-1 §6.1 tier classification) | banked | **CLOSED** — P-1 §6.1 clarification block |
| BYF Mod-2 O-1 (near-unit-root VAR margin) | banked | **CLOSED** — P-3 §3.4.1 NEW (corrective action consumed at S9) |
| 13-item inheritance register | 4 open + 9 closed | **3 open + 10 closed** |
| Phase 4 cycle progress | 10 of 13 sessions (77%) | **(no full-session count change; S11a is sub-session series)** |

## Banked observations from S11a-1

**B-Phase4-S11a1-1 — Forward-reference discipline.** The §6.1
amendment forward-references P-1 §13 (which lands at S11a-2).
This is intentional: documenting the cross-axis
disambiguation table at S11a-1 means S11a-2 doesn't need to
retroactively patch the table after §13 lands. The cost: a
window of ~10-30 minutes where P-1 §6.1 references a §13 that
doesn't yet exist in the doc. Acceptable for sub-session
batching.

For future sub-session sequences: when a downstream sub-
session is committed-and-CI-green within an hour of an
upstream forward-reference, the discipline is acceptable. If
a downstream sub-session is delayed (Chat re-engagement,
spill discovery, etc.), update the forward-reference to flag
"pending" or remove until downstream lands.

## Next sub-session

**S11a-2 — Decision A: P-1 §13 NEW per-session cycle
discipline.** ~170 LOC. Codifies the per-session LOC budget,
bundled-category exception, test-LOC accounting, spill
protocol, and S9 precedent disclosure. Single new top-level
section in P-1 between §12 (Document Maintenance) and the
"End of P-1 v1.1.0" footer.

This is the "Phase 4 governance codification" item — high-
value institutional precedent. Trigger: ready to fire after
S11a-1 CI confirms green.
