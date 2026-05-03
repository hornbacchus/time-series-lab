# Phase 4 Cycle Close — Institutional-Learning Artifact

**Status:** Phase 4 CLOSED at Phase 4 Session 13b, 2026-05-03.
**Audience:** Phase 4.5+ cycle planners; future cycle authors;
TSL maintainers reviewing Phase 4 outcomes for forward
planning.
**Origin:** Distinct from operational status tracker P-4
(`docs/reference_parity_status.md`); historical-narrative
artifact summarizing cycle-level outcomes + banked-
observations reconciliation + Phase 4.5+ handoff.

---

## 1. Cycle-level outcomes

Phase 4 ran 13 nominal sessions across 2026-05-01 to
2026-05-03 (~26 sub-sessions accounting for cascading
splits + 1 revert pair). Engine work CLOSED at S11c-2
commit `8c45de7`; v1.2.0 doc-set issuance event CLOSED at
S12c-2 commit `bcbf243`; cycle officially CLOSES at this
S13b commit.

### 1.1 Engine work delivered (S1-S11c)

- **13 inheritance items resolved** (P4-1 + P4-2 + P4-3 +
  BYF #1-#10); see P-4 Phase 4 cycle-close section for
  per-item closure table.
- **9 wrapper structural-invariants declarations** at S9
  (P4-1.3) covering kalman_filter, kalman_smoother,
  johansen_bartlett, mcmc_sv_gaussian/student_t,
  evt_ferro_segers, mint_family, transformer_attention,
  caviar_sav, p3_bond_yield_forecast. Declarations dormant
  pending runner integration (Phase 4.5+ scope per
  B-Phase4-S9-2).
- **10 wrapper docstring backfills** at S11c (P-1 §3.4
  application; two-block References + Audit-fields
  convention per B-Phase4-S11c-1-2).
- **§8.5 install-matrix gate operationally enforced** at
  S11b (3-layer belt-and-suspenders: validation script +
  CI step + pre-commit hook installer); operationally
  validated at S11b-2 by surfacing latent dtw violation
  introduced during prior cycle.
- **2 first-runtime DOCUMENTED-DIVERGENCE outcomes**:
  BYF #1 at S5 (`p3_byf_bvar_constant_vol`) + BYF #3 at S6
  (`p3_byf_stochvol_partial`); first DD instances in TSL
  parity history.

### 1.2 v1.2.0 doc-set issuance (S12 + S13a)

5 docs at Phase 4 target versions:
- **P-1 v1.2.0** (S12a; commit `c66af23`)
- **P-2 v1.2.0** (S12b-2; commit `cfc6e54`)
- **P-3 v1.2.0** (S12c-2; commit `bcbf243`)
- **P-4 v1.2.0** (S13a; commit `64ade89`)
- **C-1 v2.0.0** (Phase 4 S10; commit `193f4e7`; major
  version bump per B-Phase4-S10-1 binding-section criterion)

19/19 touchpoints + 15/15 codifications LANDED across the
doc-set per S12 Phase 1 enumeration.

### 1.3 Discipline framework codification

- **P-1 §13 NEW** (S11a-2-1 + S11a-2-2): per-session cycle
  discipline binding rules (§13.1 LOC budget; §13.2
  bundled-category exception with three sharpened criteria;
  §13.3 test-LOC accounting; §13.4 spill protocol with
  marginal-tolerance amendment); §13.5 retrospective
  examples (4 case studies); §13.6 Decision 21 principled
  content density vs measurement-variance distinction.
- **P-1 §3.4 NEW** (S11c-1): engine wrapper docstring
  convention with two-block pattern.
- **P-1 §6.1** (S11a-1): tier classification clarification.
- **P-1 §8.5** (S1 codification + S11b operational
  enforcement): install-matrix 4-surface gate.
- **P-1 §12.2 NEW** (S12a; B-Phase4-S10-1): version-bump
  criteria mirroring C-1 v2.0.0 precedent.
- **P-2 §C.2.x + §C.2.y NEW** (S12b-1-2): auto-DD pattern
  + audit-design discipline.
- **P-2 §C.6 NEW** (S12b-1-2): Pattern A.2 vs A.3
  expectation differentiation.
- **P-2 §C.7 NEW** (S12b-1-2; Decision 20): convention-
  with-application landing pattern.
- **C-1 §6 NEW** (Phase 4 S10): three wrapper structural
  patterns (module-vs-package layout; bundled-workbook
  input; layered validation).

### 1.4 §8.5 operational enforcement validated against latent violation

S11b-2 pre-flight validation script run discovered a real
gap: R `dtw` package pinned in MANIFEST.toml (Phase 3 S14
Batch 10) but missing from both slow-tier R install lines.
Per B-Phase4-S11b-2-2 banking, the §8.5 gate operationally
caught a discipline violation introduced during a prior
cycle that prose-only enforcement at S1 would not have
prevented. Belt-and-suspenders pattern empirically validated
end-to-end via synthetic gap test at S11b-3 per
B-Phase4-S11b-3-1.

### 1.5 §13 application instances empirically validating discipline

Phase 4 produced 8+ §13 application cases across the cycle:

| Case | Disposition | Reference |
|---|---|---|
| S9 311-LOC bundled cluster | commit-and-document per §13.2 all-three-criteria met | P-1 §13.5.1 |
| S11a 384-LOC scope | three-way split per §13.4 | P-1 §13.5.2 |
| S11a-2 289-LOC §13 codification | two-way cascading split per §13.4 (level 2) | P-1 §13.5.3 |
| S11a-2-2 218-LOC marginal-tolerance amendment | within-band absorption per Decision 16C | (S11a-2-2 commit `c765917`) |
| S11b-1 ORIGINAL 274-LOC scope spill | revert-and-re-commit per Decision 17 / B-Phase4-S11b-1-3 | (revert `3b04bf9` + re-commit `715e06a`) |
| S11c 251-LOC scope | two-way split per Decision 19A | (S11c-1 + S11c-2) |
| S12b-1 223-LOC borderline overshoot | two-way split per Decision 22 (3 LOC over hard threshold) | B-Phase4-S12b-1-1 |
| S12c original 207-LOC marginal-band | revert-and-re-split per Decision 23B (institutional-inconsistency) | B-Phase4-S12c-4 |

Discipline held at every level including meta-level
applications (§13 fired on §13's own codification at S11a-2;
§8.5 fired on §8.5 codification author at S5; §13.4 hard
threshold preserved against goalpost-moving at Decision 23B).

---

## 2. Banked observations register reconciliation

Final count: **~63 entries** across the Phase 4 cycle (delta
+10 from S12 Phase 1 enumeration's 53 entries reflects S12c
+ S13a-2 cycle-internal additions). Categorized:

### 2.1 Codified at Phase 4 (15 entries)

Per S12 Phase 1 enumeration (no change from initial
projection):
- **6 P-1 codifications**: Decisions 18, 21; B-Phase4-S10-1,
  S10-2, S11b-3-2, S11c-1-2 → all LANDED at S12a (commit
  `c66af23`).
- **8 P-2 codifications**: B-Phase4-S5-3, S6-1, S6-4, S6-5,
  S7-4, S8-1, S9-3; Decision 20 → all LANDED at S12b-1
  series + S12b-2 (commits `5e0c93c` + `be2c323` + `cfc6e54`).
- **1 P-3 cross-doc reuse**: B-Phase4-S6-1 → LANDED at
  S12c-1 (commit `59102bb`).

### 2.2 Closed at Phase 4 (~26 entries)

- **13 inheritance items**: P4-1, P4-2, P4-3, BYF #1-#10
  → all CLOSED in-cycle (see P-4 cycle-close section).
- **2 BYF Mod-2 banked observations**: O-1 (near-unit-root
  VAR companion), O-2 (Pattern F threshold-tightening) →
  both CLOSED in-cycle (S11a-1 P-3 §3.4.1 + S9 corrective
  action).
- **11 Phase 4 institutional decisions**: Decisions 3, A,
  14, 15, 16C, 17, 19A, 22, 23B, 24, 25, 26 (post-S12
  Phase 1 enumeration adds Decisions 22-26 to count).

### 2.3 Deferred to Phase 4.5+ (2 entries; explicit forward-banking)

- **B-Phase4-S7-1**: None-handling bug in 6 concrete
  invariant checkers (`np.asarray(tsl.get(field), dtype=
  np.float64)` raises TypeError on None instead of returning
  empty array). Surfaced at S7 P4-1.1 registry expansion;
  per §11.8 blast-radius discipline NOT fixed within S7.
- **B-Phase4-S10-3**: Smoke-test n_draws insufficiency
  surfaces as omnibus BLOCK once runner-integration lands.

Both items documented at P-4 Phase 4.5+ deferred-items
section + cross-referenced from this cycle-close artifact.

### 2.4 Cycle-internal operational (~22 entries)

S11a-* / S11b-* / S11c-* / S12-* / S13-* internal banking
entries (no codification needed; documented in respective
per-session findings docs at `docs/reference_parity_phase4/`).
Final per-series count:
- S11a-* (6 entries): B-Phase4-S11a1-1, S11a21-1, S11a21-2,
  S11a-2-2-1, S11a-2-2-2, S11a-3-1
- S11b-* (5 entries): B-Phase4-S11b-1-1 (corrected),
  S11b-1-2, S11b-1-3, S11b-2-2, S11b-3-1
- S11c-* (3 entries): B-Phase4-S11c-1-1, S11c-2-1, S11c-2-2
- S12-* (~12 entries): B-Phase4-S12a-1, S12a-2, S12-Phase1-1,
  S12b-1-1, S12b-1-2-A, S12b-1-2-B, S12b-2-1, S12b-2-2,
  S12c-3, S12c-4, S12c-5
- S13-* (2 entries): B-Phase4-S13a-1, S13a-2

---

## 3. Phase 4.5+ handoff + cycle-close retrospective

### 3.1 Phase 4.5+ deferred items

Two items explicit-deferred to Phase 4.5+ per cycle close:

- **B-Phase4-S7-1** — None-handling bug in 6 concrete
  invariant checkers (`np.asarray(tsl.get(field), dtype=
  np.float64)` raises TypeError on None instead of returning
  empty array). Surfaced at S7 P4-1.1 registry expansion;
  per §11.8 blast-radius discipline NOT fixed within S7.
  Phase 4.5+ runner-integration concern.
- **B-Phase4-S10-3** — Smoke-test n_draws insufficiency
  surfaces as omnibus BLOCK once runner-integration lands.
  Phase 4.5+ runner-integration concern.

Cross-reference: P-4 Phase 4.5+ deferred-items section
landed at S13a commit `64ade89`. Forward-banking is
**explicit deferral**, NOT silent slippage. Both items
scoped concretely with rationale + closure path documented
per B-Phase4-S11c-2-1 institutional precedent.

### 3.2 Master plan §15 estimate-vs-actual comparison

| Aspect | Master plan §15 estimate | Phase 4 actual |
|---|---|---|
| Sessions | ~13 | ~26+ sub-sessions (S1-S13 with S11/S12/S13 cascading splits + 1 revert pair at S12c) |
| Cycle duration | (open) | 2026-05-01 to 2026-05-03 (~3 days) |
| Inheritance items | 13 | 13 (all closed) |
| Cascading splits | 0 (planned linear sequence) | 8+ application-driven splits at sub-session level |

The session-count expansion was driven by **§13 discipline
application**, NOT scope creep. Each split honored §13.2
criteria check at split-level; each revert preserved audit
trail integrity (S11b-1 ORIGINAL per Decision 17 Path B;
S12c original per Decision 23B). The cycle expanded honestly
to fit institutional discipline rather than compressing
dishonestly to fit master plan estimates.

### 3.3 Institutional-grade discipline framework empirical validation

§13 fired correctly on routine work AND on its own
codification (P-1 §13.5.3 S11a-2 cascading split case).
§13.4 marginal-tolerance band empirically calibrated at
S11a-2-2 from theoretical 5% to empirical 5-10% per
codified amendment + S11a-2-2 acknowledgment-banking. §13.4
hard threshold preserved at borderline edge case (S12b-1
3-LOC overshoot at 223 vs 220 upper bound; honestly
disposed as split per Decision 22 / B-Phase4-S12b-1-1).

§8.5 operational enforcement caught real Phase 3 latent
violation at S11b-2 (R `dtw` package pinned in MANIFEST
since Phase 3 S14 but missing from both slow-tier R install
lines; latent ~8 cycles before §8.5 operational enforcement
exposed it). Belt-and-suspenders pattern empirically
validated end-to-end via synthetic gap test at S11b-3 per
B-Phase4-S11b-3-1.

Two correction patterns established:
- **Revert-and-re-commit** (S11b-1 ORIGINAL → Decision 17
  Path B): substantive-content-violation correction.
- **Revert-and-re-split** (S12c original → Decision 23B):
  institutional-inconsistency correction.

Audit trail integrity preserved across all correction
patterns (master history shows: original commit + revert +
corrected re-commit/re-split; mistakes documented as
institutional learning, not erased per B-Phase4-S11b-1-3
discipline).

### 3.4 Forward-looking lessons for Phase 4.5+ cycle planning

1. **Trigger-drafting discipline** (B-Phase4-S12c-3):
   marginal-tolerance applications must explicitly preserve
   content-vs-measurement distinction. Permissive trigger
   language at S12c trigger permitted institutional-
   inconsistency disposition; corrected via revert + re-split
   per Decision 23B. Future trigger drafts must specify the
   Decision 21 operational test as a precondition for
   marginal-tolerance band absorption.
2. **Pre-flight enumeration discipline** (S12 Phase 1
   bounded-coherence framing pattern): for issuance-class
   sessions spanning multiple companion docs, run a Phase 1
   read-only touchpoint enumeration + dispositions +
   recommended split structure BEFORE the write phase.
   Phase 4.5+ should adopt this pattern for multi-doc
   issuance work.
3. **Institutional self-application validates discipline**:
   cycles that apply codified discipline to themselves
   (Phase 4's §13 framework codified at S11a + applied to
   itself across 9 application instances) produce stronger
   institutional grounding than aspirational specification
   followed by deferred application.
4. **Master-plan LOC estimates run 1.5-2× under empirical
   actuals** for codification-density work (per
   B-Phase4-S12a-2). Future master plans should treat per-
   session LOC estimates as lower bound; sub-session splits
   driven by §13.4 discipline are expected, not exceptional.

---

## 4. Cycle close confirmation

Phase 4 cycle CLOSES at this S13b-2 commit.

- **Engine baseline frozen at S11c-2 commit `8c45de7`** (2026-05-02)
- **Doc-set issuance baseline frozen at S13a commit `64ade89`** (2026-05-03)
- **Cycle-close artifact frozen at this commit**
- **Phase 4.5+ work inherits from**: this cycle-close artifact
  (institutional learning + deferred items) + P-4's Phase 4.5+
  deferred-items section (operational inheritance register)

**End of Phase 4.**
