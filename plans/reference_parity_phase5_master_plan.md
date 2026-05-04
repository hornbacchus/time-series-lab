# Phase 5 Master Plan — Runner Integration Cycle

**Status:** v1 (drafted at S0-MASTERPLAN, 2026-05-03;
Phase 4 cycle CLOSED at commit `3ac8c0e`)
**Cycle name:** Phase 5 (formerly forward-banked as "Phase
4.5+"; promoted to Phase 5 per cycle-naming evolution
documented in §1.1 below)
**Audience:** Phase 5 cycle authors (Code + Chat); future
cycle archaeologists reviewing Phase 5 planning artifact
**Origin:** Drafted at S0-MASTERPLAN per Phase 4 cycle-
close artifact handoff (commit `3ac8c0e`) + P-4 v1.2.0
inheritance register (commit `64ade89`)

---

## 1. Cycle context

### 1.1 Phase 4 closure framing + naming evolution

Phase 4 closed at S13b-2 commit `3ac8c0e` (2026-05-03).
The cycle's institutional record summary (per Phase 4
cycle-close artifact §4):
- 5 docs at target versions (P-1/P-2/P-3/P-4 v1.2.0; C-1
  v2.0.0)
- 13/13 inheritance items resolved
- 19/19 touchpoints + 15/15 codifications LANDED at v1.2.0
  doc-set
- 9 §13 application instances empirically validating
  discipline framework
- 2 forward-banked items explicit-deferred to "Phase 4.5+"
  (B-Phase4-S7-1; B-Phase4-S10-3)

**Naming evolution: Phase 4.5+ → Phase 5.** Phase 4's
forward-banking framing used "Phase 4.5+" as placeholder
for the next cycle (carried from Phase 3.5's intermediate-
cycle convention). At cycle-planning time, the "Phase 4.5"
intermediate framing was reconsidered: the runner-
integration cycle's scope (engine-side architectural work
beyond bounded amendments) is full-cycle-class, not
intermediate-cycle-class. Promotion to Phase 5 is the
correct framing.

Phase 4.5+ references in v1.2.0 doc-set (P-4 deferred-
items section + Phase 4 cycle-close artifact §3.1) remain
unchanged; the naming substitution "Phase 4.5+ ↔ Phase 5"
holds via reader convention. Future doc-set revisions can
update the references at convenient occasion (e.g., a
patch-version P-4 update during Phase 5 cycle-internal
work); not Phase 5 S0-MASTERPLAN scope.

### 1.2 Institutional discipline inheritance summary

Phase 5 inherits the full §13 discipline framework codified
at Phase 4 (P-1 §13 binding rules + retrospective examples
+ marginal-tolerance amendment + Decision 21 principled-
content-density distinction). Phase 5 cycle planning
applies these standing disciplines without re-codification.

Specific standing-application provisions documented at §4
below.

---

## 2. Cycle objective

**Primary objective:** runner integration of structural-
invariants framework. Wire the `check_invariants` lifecycle
method into the harness runner so that the 9 wrapper
declarations landed dormant at Phase 4 S9 (P4-1.3) become
empirically active.

**Secondary objectives:**
- Resolve B-Phase4-S7-1 (None-handling bug in 6 concrete
  invariant checkers; surfaces as runner-integration
  TypeError without fix)
- Resolve B-Phase4-S10-3 (smoke-test n_draws insufficiency
  surfaces as omnibus BLOCK once runner-integration lands)
- Surface-during-integration scope for new banked items
  emerging from runner-integration empirical work

**Out of scope:**
- New wrapper additions beyond Phase 4 baseline (84
  wrappers per Phase 4 cycle close)
- v1.3.0 doc-set issuance (deferred to Phase 6 unless
  cycle-internal accumulation triggers; see §16 cycle-
  close handoff anticipation)
- Ad-hoc engine modifications outside structural-invariants
  + smoke-test infrastructure scope

---

## 3. Inheritance register

### 3.1 Forward-banked items (concrete + explicit at Phase 4 S7+S10)

- **B-Phase4-S7-1** — None-handling bug in 6 concrete
  invariant checkers: `np.asarray(tsl.get(field), dtype=
  np.float64)` raises TypeError on None instead of
  returning empty array. Surfaced at S7 P4-1.1 registry
  expansion; per §11.8 blast-radius discipline NOT fixed
  within S7. Phase 5 sub-domain (i) integration cleanup;
  closure path: defensive None-handling at checker entry
  with empty-array fallback.

- **B-Phase4-S10-3** — Smoke-test n_draws insufficiency:
  BYF smoke runs at n_draws=1000 will surface as omnibus
  BLOCK on `mcmc_convergence` invariant once runner-
  integration lands. Phase 5 sub-domain (ii) closure;
  closure path: smoke-fixture n_draws calibration vs
  invariant tolerance band reconciliation.

### 3.2 Dormant declarations table (10 wrappers)

| # | Wrapper audit-script | Invariant declared | Tolerance | Phase 5 sub-domain |
|---|---|---|---|---|
| 1 | `kalman_filter.py` | `kalman_covariance_ordering` | 1e-6 abs | (i) closed-form-numerical |
| 2 | `kalman_smoother.py` | `kalman_covariance_ordering` | 1e-6 abs | (i) closed-form-numerical |
| 3 | `johansen_bartlett.py` | `vecm_cointegration_rank` | 0 abs (strict) | (i) closed-form-numerical |
| 4 | `mcmc_sv_gaussian.py` | `mcmc_convergence` (omnibus) | 200 ESS_min | (ii) MCMC-convergence |
| 5 | `mcmc_sv_student_t.py` | `mcmc_convergence` (omnibus) | 200 ESS_min | (ii) MCMC-convergence |
| 6 | `evt_ferro_segers.py` | `evt_extremal_index` | 0.01 abs slack | (i) closed-form-numerical |
| 7 | `mint_family.py` | `mint_coherence` | 1e-10 abs | (i) closed-form-numerical |
| 8 | `transformer_attention.py` | `attention_normalization` | 1e-6 abs | (i) closed-form-numerical |
| 9 | `caviar_sav.py` | `intervals_test` (INVERTED) | 0.05 p-value floor | (iii) inverted-semantics |
| 10 | `p3_bond_yield_forecast.py` | `mcmc_convergence` (omnibus) | 200 ESS_min | (ii) MCMC-convergence |

Per P-2 §D.1.5 audit-side declaration table; per Phase 4
Check-in #2 deep-verification probe confirming tolerance-
value semantic correctness across all 10 declarations.

### 3.3 Phase 5 cycle-internal scope additions

Sub-domain (iv) catch-all reserved for items surfacing
during Phase 5 runner-integration empirical work. Items
banked here at cycle-internal sessions land as scope-
internal additions per §13 discipline (split protocol
applies if scope expansion produces §13.4 spill at session-
trigger time).

Anticipated category types for sub-domain (iv):
- Runner-side architectural concerns surfaced by integration
- New invariant types beyond Phase 4 baseline (5 P4-1.1
  types; 2 Phase 3 stub types) needed for previously-
  unaddressed wrapper classes
- Tolerance-value calibration adjustments based on
  empirical runner-integration data

---

## 4. Institutional discipline standing application

### 4.1 §13 per-session cycle discipline

Phase 5 inherits P-1 v1.2.0 §13.1-§13.4 binding rules verbatim:
- Default budget **200 LOC** per §13.1
- Marginal-tolerance band **200-220 LOC** per S11a-2-2
  amendment (P-1 v1.2.0 §13.4)
- Hard threshold **220 LOC** per B-Phase4-S12b-1-1
  institutional precedent
- Decision 21 principled-content-density test required for
  marginal-tolerance band classification per B-Phase4-S12c-3
- Test-LOC accounting per P-1 v1.2.0 §13.3 clarifying
  sentence (Decision 18)

Cross-reference: P-1 v1.2.0 §13 + Phase 4 cycle-close artifact
§3.3 (institutional-grade discipline framework empirical
validation, 9 application instances).

### 4.2 Trigger-drafting discipline (B-Phase4-S12c-3 standing language)

Every Phase 5 trigger anticipating LOC above ~150 includes
this language verbatim:

> "If actual lands at 200-220 LOC band: run Decision 21
> principled-content-density test BEFORE classifying as
> marginal-tolerance band absorption. Content-density
> classification → split per Decision 17 + B-Phase4-S12b-1-1
> hard-threshold precedent. Measurement-variance classification
> → band absorption with explicit findings-doc banking."

This is institutional precedent from Phase 4 S12c revert +
re-split (Decision 23B); not ceremony. The standing language
prevents Phase 4 S12c-class trigger-drafting omissions where
absorbing-into-band became default disposition without
Decision 21 application.

### 4.3 Pre-flight enumeration discipline (S12 Phase 1 pattern)

Pre-flight enumeration applies to:
- **Issuance-class sessions** (sessions producing version
  bumps to multi-doc artifacts)
- **Multi-touchpoint-coherence sessions** (sessions touching
  multiple existing artifacts requiring cross-amendment
  coherence verification)

Pre-flight enumeration does NOT apply to:
- Engine-implementation sessions (Phase 5 S1-S9 style)
- Single-doc bounded amendments
- Cycle-close artifact authoring

Phase 5 sessions warranting pre-flight enumeration are marked
**[PRE-FLIGHT]** in §15 (lands at S0-MASTERPLAN-2).

### 4.4 Correction patterns

Phase 4 codified two empirically-validated correction patterns:

- **Revert-and-re-commit** (Decision 17 Path B; S11b-1
  ORIGINAL precedent at commit `28f6983` revert + corrected
  re-commit at `712397f`): for substantive-content violations
  caught mid-session before disposition lock-in.
- **Revert-and-re-split** (Decision 23B; S12c original
  precedent at commit `f0833c8` revert + re-split at
  `59102bb` + `bcbf243`): for institutional-inconsistency
  dispositions corrected post-commit when CI-green has
  confirmed clean execution but disposition contradicts
  institutional framework.

Audit trail integrity preserved through both: original commit
+ revert + corrected re-commit/re-split documented in master
history.

### 4.5 LOC estimate calibration awareness

Phase 4 empirical pattern (B-Phase4-S12a-2 + B-Phase4-S12b-2-1
+ B-Phase4-S13a-1):
- **Codification-density-bounded scope**: 1.5-2× projection-
  to-actual multiplier (e.g., S12a 165 LOC vs ~86 projected =
  1.92×; S11a Decision A 170 LOC vs ~30-50 projected ≈ 3-4×)
- **Content-density-bounded scope**: 1.1-1.3× multiplier
  (e.g., S12b-2 100 LOC vs ~78 projected = 1.28×; S12b-1-1
  84 LOC vs ~75 projected = 1.12×; S13a 141 LOC vs ~140
  projected = 1.01×)

Master plan §15 session estimates are skeleton-class;
empirical multipliers applied at trigger drafting and Chat-
side review.

## 5. Cycle-scope expansion expectation

Per Phase 4 empirical pattern (master plan estimated ~13
sessions; actual ~26+ sub-sessions; expansion driven by §13
discipline application not scope creep), Phase 5 master plan
§15 represents **nominal session count**.

**Empirical expansion of 1.5-2× nominal-to-actual sub-session
count expected.** Phase 5's ~14 nominal §15 sessions
anticipate ~21-28 actual sub-sessions. This is calibration-
awareness for stakeholders reading the master plan, not
pre-splitting commitment (Disposition 4 from Phase 4 S12
prohibits pre-splitting for hypothetical overshoot per §13.2
sharpened criteria).

Cycle expands honestly to fit institutional discipline;
nominal session estimates are skeleton-class.

---

**End of Phase 5 master plan §1-§5 (S0-MASTERPLAN-1-B
appending per Decision 28 cascading split, 2 of 3).** §15
session enumeration + §16 Phase 6 inheritance handoff
anticipation + §17 master plan version history land at
S0-MASTERPLAN-2 per pre-planned natural seam.
