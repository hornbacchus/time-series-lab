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

## 15. Session enumeration

### Sub-domain (i) — Runner harness elevation

**S1 — Runner harness architecture review + design** [PRE-FLIGHT]
- Read-only enumeration of current runner-harness state.
- Design decisions: how runner fires structural-invariants
  checks against engine output; how dormant declarations
  elevate to active; integration points with engine
  `_dispatch.py` + audit registry in P-2 §D.1.5 + tolerance
  values per audit-side declarations.
- Output: design touchpoint enumeration + recommended sub-
  session structure for S2-S5.
- LOC estimate: ~100-150 (design doc; content-density);
  empirical projection ~110-195 actual.

**S2 — Runner harness implementation Phase 1**
- Core dispatch implementation; first 3 wrapper integrations:
  kalman_filter, kalman_smoother, johansen_bartlett.
- Engine touch + smoke test for each integrated wrapper.
- LOC estimate: ~150-200 (engine + tests); empirical
  projection ~180-300 actual; §13.4 spill possible; pre-
  planned split natural seam: per-wrapper if needed.

**S3 — Runner harness implementation Phase 2**
- Next 3 wrapper integrations: mcmc_sv_gaussian,
  mcmc_sv_student_t, evt_ferro_segers; same engine touch +
  smoke test pattern as S2.
- LOC estimate: ~150-200; empirical projection ~180-300
  actual; §13.4 spill possible.

**S4 — Runner harness implementation Phase 3**
- Final 3 wrapper integrations: mint_family,
  transformer_attention, caviar_sav (INVERTED semantics per
  B-Phase4-S9-3 codification); same engine touch + smoke
  test pattern.
- LOC estimate: ~150-200; empirical projection ~180-300
  actual; §13.4 spill possible.

**S5 — Runner integration acceptance testing + p3_bond_yield_forecast**
- Cross-wrapper acceptance testing across the 9 sub-domain (i)
  integrations; p3_bond_yield_forecast wrapper integration
  (single wrapper; separate from prior batch).
- LOC estimate: ~100-150; empirical projection ~110-195 actual.

### Sub-domain (ii) — Smoke-test infrastructure upgrade

**S6 — Smoke-test infrastructure design**
- n_draws calibration; sample-size requirements; tolerance
  band review across the 9 wrappers; B-Phase4-S10-3 specific
  concern addressed.
- LOC estimate: ~80-120 (design doc + calibration analysis;
  content-density); empirical projection ~90-155 actual.

**S7 — Smoke-test infrastructure implementation + validation**
- Implementation of upgraded smoke-test infrastructure;
  validation across all 9 wrappers from sub-domain (i).
- LOC estimate: ~120-180 (engine + tests); empirical
  projection ~145-270 actual; §13.4 spill possible.

### Sub-domain (iii) — None-handling robustness

**S8 — None-handling fix for 6 concrete checkers + audit**
- B-Phase4-S7-1 specific concern: 6 concrete checkers None-
  handling bug; audit of additional None-handling surface
  area across runner harness post-integration.
- LOC estimate: ~80-120; empirical projection ~90-155 actual.

**S9 — None-handling robustness extension** (conditional)
- Triggered only if S8 audit surfaces additional concerns
  warranting separate session.
- LOC estimate: ~50-100 (conditional); empirical projection
  ~55-130 actual.

### Sub-domain (iv) — Surface-during-integration concerns (engine-touch reserved)

**S10-S12 — Reserve allocation for surface-during-integration scope**
- Specific session content determined as integration
  progresses; engine-touch class per Domain 5 disposition.
- LOC estimate per session: skeleton ~100-150; empirical
  projection per session ~110-225 actual; §13.4 spill per
  session possible.

If integration surfaces purely doc-side learnings, those
fold into S13 issuance scope rather than consuming sub-
domain (iv) reserve.

### Cycle-close sessions

**S13 — Phase 5 v1.x.0 doc-set issuance** [PRE-FLIGHT]
- Phase-1-style enumeration prepended (issuance-class
  session per §4.3); v1.x.0 amendments to P-1 / P-2 / P-3 /
  P-4 reflecting Phase 5 runner integration outcomes.
- C-1 amendment scope deferred to integration findings:
  ~5-10 LOC C-1 amendments fold into S13; ~30+ LOC C-1
  amendments warrant standalone sub-session.
- Mirrors Phase 4 S12 four-phase topology (Phase 1 + per-doc
  sub-sessions); cascading splits expected per Phase 4
  empirical pattern.
- LOC estimate: skeleton ~400-600 across full S13 sub-session
  series (empirical projection ~600-1200 actual across
  cascading splits; nominal "session" represents the doc-set
  issuance event not single commit).

**S14 — Phase 5 cycle close**
- P-4 v1.x.0 issuance + cycle-close artifact authoring;
  mirrors Phase 4 S13a + S13b structure.
- LOC estimate: skeleton ~250-350 across S14a + S14b;
  empirical projection ~280-700 actual across cascading splits.

## 16. Cycle-close handoff anticipation

Phase 5 closure produces:
- Engine baseline frozen at last engine-touch sub-session
- Doc-set issuance baseline frozen at S13 final commit
- Cycle-close artifact frozen at S14 final commit
- Phase 6 inheritance register seeded (forward-banked items
  + any sub-domain (iv) deferrals + cycle-close institutional
  learning)

Phase 5 cycle-close artifact lands at
`docs/reference_parity_phase5/phase_5_cycle_close.md` per
Phase 4 S13b precedent (Decision 25).

Per-session findings docs at
`docs/reference_parity_phase5/session_*_findings.md` per
Phase 4 pattern.

## 17. Master plan version history

- **v1 (2026-05-03):** Initial draft. Phase 5 cycle definition
  with 4-sub-domain runner integration scope; ~14 nominal
  sessions; empirical 1.5-2× expansion expectation; full
  institutional-discipline standing application from Phase 4
  v1.2.0 doc-set. Landed via Decision 28 four-level cascading
  split: S0-MASTERPLAN-1-A (§1-§3, commit `9721852`) +
  S0-MASTERPLAN-1-B (§4-§5, commit `716421c`) +
  S0-MASTERPLAN-2 (§15-§17, this commit).

---

**End of Phase 5 master plan v1 (S0-MASTERPLAN-2 appending
per Decision 28 cascading split, 3 of 3).** Master plan
fully landed; Phase 5 cycle execution sessions begin per §15
enumeration.
