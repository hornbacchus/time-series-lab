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

**Phase 5 sub-domain (i) opening empirical observations**
(v1.1 amendment per Decision 34B-γ Phase 2 Consolidation):
- **Skeleton triggers** (sub-domain (i) opening):
  1.5-2.8× multipliers (S0-MASTERPLAN-1 unsplit 1.7×; S1
  unsplit 2.8×; S1-A-1 ORIGINAL 1.5×; S1-A-1-a 2.7×) —
  pattern is genuine codification-density at cycle-
  establishment scope, not measurement noise
- **Constraint-specified triggers (design-class):**
  0.84-1.07× multipliers (S1 sequence: S1-A-1-a-CORRECTED
  1.07×; S1-A-1-b 1.02×; S1-A-1-c 0.88×; S1-A-2 0.84×;
  S1-B 1.05×; S1-C 0.92×)
- **Constraint-specified triggers (execution-class):**
  empirical data thin; S2-α ORIGINAL 1.23× post-trim
  (institutionally inconsistent disposition; reverted at
  Decision 32B); S2-α-1 1.55× upper-bound calibration error
  (within marginal-tolerance band); NO clean execution-class
  validation point yet
- **Recursive-pattern protection** (design-class read-only
  + write-phase consolidation): Pre-flight Phase 1 0.99×
  upper-bound (read-only enumeration); Phase 1 Consolidation
  1.10× deliverable + within-band combined (write-phase
  consolidation); both distinct from execution-class scope

Trigger specificity as moderation lever empirically validated
(B-Phase5-S0-3 + B-Phase5-S0-6 + B-Phase5-S1-A-1-c-
GENERALIZATION-VALIDATION); skeleton triggers prohibited at
Phase 5 sub-domain (i) opening per empirical record.

Master plan §15 session estimates are skeleton-class;
empirical multipliers applied at trigger drafting and Chat-
side review.

**Cross-reference:** see `docs/reference_parity_phase5/trigger_templates_v1.md`
for application discipline (per-class LOC budgets +
authoring-overshoot disposition + within-band classification
+ trigger-drafting protocols + per-section empirical
baselines). §4.5 captures empirical observations (what was
observed across Phase 4 + Phase 5 cycles); trigger-template
doc captures application discipline (how to apply at trigger
drafting) per Decision 40-I1 Q2=Principle 2 jurisdictional
split.

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

**Sub-domain (i) session structure standing discipline** (v1.1
amendment per Decision 40-I1 Q1=Option α per-wrapper default):

Per-wrapper sessions are the **default** at sub-domain (i)
opening. Multi-wrapper sessions retained as **exception**
ONLY where ALL three criteria met:
1. Analytical-class cohesion (per wrapper grouping principles
   below)
2. Pre-planned natural seam enumerated at trigger drafting
   per Decision 31ζ pattern + `trigger_templates_v1.md` §7
3. Empirical-validation-envelope assessment at trigger drafting

**Wrapper grouping (authoritative for all 9 sub-domain (i)
wrappers + p3_bond_yield_forecast)** per Decision 40-I1 +
S1-C §3 grouping principles:
- **Closed-form-numerical:** kalman_filter, johansen_bartlett,
  evt_ferro_segers
- **MCMC-stochastic-vol:** mcmc_sv_gaussian, mcmc_sv_student_t
- **Heterogeneous (per-wrapper analytical class):**
  mint_family (closed-form structural-decomposition),
  transformer_attention (matrix-attention),
  caviar_sav (INVERTED quantile-statistic)
- **Acceptance + cycle-baseline wrapper:**
  p3_bond_yield_forecast (separate session per master plan
  v1 §15 S5)

B-Phase5-S1-1 master-plan-locus correction (v1.1 codified):
audit-side `structural_invariants` declarations live at
`tools/reference_parity/harness/checks/*.py` per Phase 4 S9
commit `ff403dd`, NOT engine `_dispatch.py` as v1
hypothesised. S1 below references the authoritative locus.

**S1 — Runner harness architecture review + design** [PRE-FLIGHT]
- Read-only enumeration of current runner-harness state.
- Design decisions: how runner fires structural-invariants
  checks against engine output; how dormant declarations
  elevate to active; integration points with audit-side
  declarations at
  `tools/reference_parity/harness/checks/*.py` + audit
  registry in P-2 §D.1.5 + tolerance values per audit-side
  declarations.
- Output: design touchpoint enumeration + recommended sub-
  session structure for S2-S5.
- LOC estimate: ~100-150 (design doc; content-density);
  empirical projection ~110-195 actual.

**S2 — Closed-form-numerical trio** (multi-wrapper grouping
pre-dating v1.1 standing discipline; per-wrapper natural seam
Decision 31ζ pre-split applied)
- Wrappers: kalman_filter + johansen_bartlett +
  evt_ferro_segers (Decision 31ζ pre-split S2-α + S2-β
  empirically established as natural seam).
- Engine touch + smoke test for each integrated wrapper;
  shared lifecycle method + dispatch infrastructure landed
  per S2-α (B-Phase5-S2-α-INFRASTRUCTURE-COLOCATION pattern).
- **Note on standing discipline application:** S2 multi-
  wrapper structure pre-dates the v1.1 standing discipline
  3-criteria gate. The 3-criteria gate applies prospectively
  to S3 + S4 trigger drafting. S2 multi-wrapper structure is
  in-flight under empirical test (S2-α-1 1.55× upper-bound
  calibration error) and may surface envelope-related
  concerns during S2-α-1 + S2-α-2 + S2-β execution; resume
  sequence per Q5=b-2 surfaces these empirically.

**S3 — MCMC-stochastic-vol pair** (multi-wrapper single-
session grouping per v1.1 standing discipline 3-criteria gate
empirical satisfaction; v1.2 framing per S3 pre-flight
empirical findings at commit `1fd1ad3`)
- Wrappers: mcmc_sv_gaussian + mcmc_sv_student_t (2 wrappers
  in MCMC-stochastic-vol analytical class).
- **Engine state finding (S3 pre-flight `1fd1ad3`):** Engine
  Path A audit-field elevation in `_sv_mcmc.py` ALREADY
  COMPLETE per Phase 4 S8 P4-1.2 codification (predates
  Path 34B-γ Phase 2 Consolidation v1.1 authoring).
  `_sv_mcmc.py` result dict (lines 311-321) exposes
  `rhat_max` / `ess_min`; `stochastic_volatility.py` engine
  wrapper (lines 647-650) elevates these to `audit_fields`
  per BYF Decision 12 pattern. Both `mcmc_sv_gaussian` +
  `mcmc_sv_student_t` `run_tsl()` expose `ess_min` (REQUIRED
  for `mcmc_convergence` checker) at top level. Per-wrapper
  field-availability protocol Case 0 outcome (no harness
  expansion needed beyond allowlist + smoke test).
- **3-criteria gate evaluation (per Q-S3-decomp-1=(γ)
  disposition):**
  1. Analytical-class cohesion: SATISFIED (both wrappers
     MCMC-stochastic-vol; shared engine module + analytical
     pattern)
  2. Pre-planned natural seam: SATISFIED (analytical-class
     cohesion as seam under no-engine-work scope; both
     wrappers Case 0 outcome empirically established at
     pre-flight; cross-wrapper acceptance test natural fit
     in same sub-session)
  3. Empirical-validation envelope: SATISFIED via chunking
     discipline at staging time (combined envelope ~165-250
     LOC engages §13.1 marginal-tolerance band at upper
     bound; chunking judgment per Phase 5 standing pattern +
     Code's §13.4 chunking judgment at staging time)
- **Single-session decomposition declared.** Both wrappers
  integrate at single S3 sub-session including cross-wrapper
  acceptance test; chunking discipline applied at staging
  time per §13.4 + Phase 5 standing pattern.
- **Empirical finding (v1.2 amendment):** v1.1 §15 S3 framing
  premise (engine Path A elevation as anticipated substantive
  engine work + engine + harness decomposition seam)
  empirically wrong. Path 34B-γ Phase 2 Consolidation v1.1
  authoring at commits `021c778` + `c070c62` didn't audit
  empirical engine state per wrapper before authoring. v1.2
  reconciles framing per S3 pre-flight findings; banking
  entry B-Phase5-MASTER-PLAN-V1.1-§15-S3-FRAMING-
  RECONCILIATION codifies the design-gap pattern.
- **Forward-looking:** v1.1 standing discipline 3-criteria
  gate empirically validated at first prospective
  application (S3); gate-evaluation framework stands as
  authoritative at v1.2. Master plan amendments going
  forward audit empirical engine state per wrapper before
  authoring wrapper-grouping framing.

**S4 — Heterogeneous group: per-wrapper sessions** (Q1=Option
α per-wrapper default; v1.1 standing discipline 3-criteria
gate applied):
- Wrappers: mint_family + transformer_attention + caviar_sav
  (INVERTED) span 3 distinct analytical classes (closed-form
  structural-decomposition / matrix-attention / quantile-
  statistic INVERTED per B-Phase4-S9-3 codification).
- **3-criteria gate application:**
  1. Analytical-class cohesion: NOT MET (3 distinct
     analytical classes; no shared engine module or
     analytical pattern)
  2. Pre-planned natural seam: not assessed (criterion 1
     failure terminates gate evaluation per logical AND
     structure)
  3. Empirical-validation envelope: not assessed (per
     criterion 2)
- Multi-wrapper exception not warranted; per-wrapper default
  per Q1=Option α applies.
- Sub-sessions at trigger drafting:
  - S4-α: mint_family (closed-form structural-decomposition)
  - S4-β: transformer_attention (matrix-attention)
  - S4-γ: caviar_sav (INVERTED quantile-statistic per
    B-Phase4-S9-3 codification)
- Decision 31ζ pre-split pattern applied per-wrapper if
  natural seam surfaces during S4-α / S4-β / S4-γ trigger
  drafting.

**S5 — Runner integration acceptance testing + p3_bond_yield_forecast**
- Cross-wrapper acceptance testing across the 9 sub-domain (i)
  integrations; p3_bond_yield_forecast wrapper integration
  (single wrapper; separate from prior batch per Decision
  40-I1 wrapper grouping).
- LOC estimate: ~100-150; empirical projection ~110-195
  actual.

**Cross-reference:** trigger drafting at S2-S5 references
`docs/reference_parity_phase5/trigger_templates_v1.md` §6
(execution-class projection multiplier guidance) + §1 (per-
class LOC budget specification) + §7 (recursive-pattern
protection); Decision 40-I1 Q2=Principle 2 jurisdictional
split applies.

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
  S0-MASTERPLAN-2 (§15-§17, commit `4056bf6`).
- **v1.1 (2026-05-05):** Cycle-internal amendment per Decision
  34B-γ broad-scope consolidation; Q1=Option α per-wrapper
  default + Q2=Principle 2 jurisdictional split locked at
  Decision 40-I1. Amendments: §4.5 Phase 5 sub-domain (i)
  opening empirical observations + cross-reference to
  `trigger_templates_v1.md`; §15 sub-domain (i) session
  structure standing discipline (per-wrapper default + multi-
  wrapper exception criteria); §15 sub-domain (i) wrapper
  grouping authoritative mapping for all 9 wrappers +
  p3_bond_yield_forecast; §15 S1 locus correction per
  B-Phase5-S1-1; §15 S2-S5 restructured (S2 closed-form-
  numerical multi-wrapper exception; S3 MCMC pair multi-
  wrapper exception; S4 per-wrapper sub-sessions; S5
  unchanged); §18 Phase 5 reflective record. Inheritance to
  Phase 6+ candidate pattern; actual disposition at S14 per
  trigger_templates_v1.md §0 + §8 framing.
- **v1.2 (2026-05-06):** Cycle-internal amendment per S3
  pre-flight empirical findings at commit `1fd1ad3` +
  Q-S3-decomp-1=(γ) Chat disposition. Amendment: §15 S3
  framing reconciliation under no-engine-work scope (engine
  Path A elevation finding ALREADY COMPLETE per Phase 4 S8
  P4-1.2 codification predating v1.1 authoring); v1.1
  premise (engine + harness decomposition seam) empirically
  wrong; (γ) single-session decomposition declared per
  v1.1 standing discipline 3-criteria gate empirical
  satisfaction (Criteria 1+2+3 SATISFIED via analytical-
  class cohesion + Case 0 outcome + chunking discipline at
  staging). First prospective application of v1.1 standing
  discipline 3-criteria gate empirically validated at S3.
  Banking entries B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-
  EXTENSION + B-Phase5-MASTER-PLAN-V1.1-§15-S3-FRAMING-
  RECONCILIATION codify Case 0 protocol extension +
  amendment-design-gap pattern at separate findings doc
  `docs/reference_parity_phase5/s3_amendment_banking.md`.
- **Phase 5 close (2026-05-08; no version increment per
  Q-Phase5-close-3=(γ)):** Phase 5 cycle CLOSED at close arc
  step 6. Sub-domain (i) closed-form-numerical + MCMC
  stochastic + INVERTED tolerance heterogeneous group
  COMPLETE — 8-wrapper allowlist + 14 dispatch tests + 3
  invariant class coverage + per-class cross-wrapper
  acceptance dispatch framework. Framework reference doc LIVE
  at `docs/reference_parity_phase5/framework_reference.md`
  (473 LOC across 5 successor-utility sections; PASSES Phase
  6+ inheritance test per Chat F1 review). Reserve sub-
  domains (ii) + (iii) + (iv) deferred entirely to Phase 6+
  per Q-S5-3=(δ) + Q-Phase5-forward=(γ) explicit transfer.
  Master plan v1.2 remains authoritative through Phase 5
  close; v1.3 increment deferred to Phase 6+ if cycle-
  architecture recalibration produces structural amendment
  per Code's banked findings + closeout banking
  (B-Phase5-CLOSE-ARC-INSTITUTIONAL-PATTERN-CLOSEOUT at
  `docs/reference_parity_phase5/phase_5_closeout_banking.md`).

## 18. Phase 5 reflective record (v1.1 amendment)

Phase 5 cycle-internal amendment pattern as **candidate
institutional precedent** for Phase 6+ (final inheritance
disposition determined at Phase 5 cycle close S14 per
remaining-cycle empirical validation; per
`trigger_templates_v1.md` §0 + §8 candidate-pattern framing):

When sub-domain-opening calibration errors exceed framework-
amendment threshold, cycle-internal artifacts produced
(`trigger_templates_v1.md` cycle-internal v1 + master plan
v1.1 amendment) rather than deferring to S13 doc-set
issuance per v1 standing pattern. Path 30E disposition +
Decision 33C constructive Path 30E + Decision 34B-γ broad-
scope cycle-internal amendment as empirical institutional
learning sequence. The deferral-to-S13 default was
provisional per cycle-establishment phase reasoning, not
principled; Phase 5 cycle-internal amendment surfaces
calibration-error pattern early enough to apply refinement
mid-cycle rather than retrospectively at cycle close.

Empirical sequence:
- 3 institutional-inconsistency cases at Phase 5 sub-domain
  (i) (S1-A-1 ORIGINAL band-absorption misclassification;
  S1-A-1-a saturation-framing band-absorption repeat; S2-α
  trim-disposition) reverted via Decisions 30B + 30D + 32B
- Trigger-projection calibration errors persist despite
  constraint-specification (S2-α-1 1.55× upper-bound;
  Path 30E pre-flight required-artifact-uncounted recursion)
- Constructive Path 30E pause (Decision 33C) → broad-scope
  consolidation (Decision 34B-γ) producing 2 cycle-internal
  artifacts: trigger_templates_v1.md (Phase 1 Consolidation
  framework refinement) + master plan v1.1 (Phase 2
  Consolidation cycle scope restructuring)

Forward-looking: Phase 5 execution resumes per Q5=b-2
sequence (Path 30E pre-flight commits + S2-α-1 commits +
S2-α-2 onward) under refined framework + restructured master
plan. Future Phase 5 sessions reference `trigger_templates_v1.md`
for application discipline + master plan v1.1 §4.5 for
empirical observations + master plan v1.1 §15 for sub-domain
(i) session structure standing discipline.

**v1.2 amendment record append (2026-05-06):** Second cycle-
internal amendment per S3 pre-flight empirical findings.
Distinct from v1.1 calibration-error class: v1.2 reconciles
master plan framing premise (engine Path A elevation
anticipated work) against empirical engine state (already
complete per Phase 4 S8 P4-1.2). Pre-flight pattern
established at Path 34B-γ for design-class extends to
execution-class scope evaluation per S3 pre-flight
precedent. v1.1 standing discipline 3-criteria gate
empirically validated at first prospective application (S3
single-session disposition under Criteria 1+2+3 satisfaction);
gate-evaluation framework stands as authoritative going
forward. Forward-looking: master plan amendments going
forward audit empirical engine state per wrapper before
authoring wrapper-grouping framing (per
B-Phase5-MASTER-PLAN-V1.1-§15-S3-FRAMING-RECONCILIATION
banking entry).

---

**End of Phase 5 master plan v1.2 (S3 pre-flight framing
reconciliation amendment).** Master plan v1 baseline + v1.1
+ v1.2 amendments fully landed; Phase 5 cycle execution
sessions resume per §15 v1.2 enumeration under refined framework +
restructured grouping.

---

**Phase 5 cycle close reflection (2026-05-08; appended at
close arc step 6 per Q-Phase5-close-3=(γ) §17 + §18 closure
note WITHOUT v1.3 increment):**

Phase 5 sub-domain (i) heterogeneous group integration
COMPLETE: 8-wrapper allowlist active across 3 invariant
classes (closed-form deterministic 5 wrappers + MCMC
stochastic 2 wrappers + INVERTED tolerance 1 wrapper); 14
dispatch tests + per-class cross-wrapper acceptance framework
operational; framework reference doc LIVE as Phase 6+
successor inheritance asset.

Institutional learning codified across cycle:
- Per-wrapper field-availability protocol with Cases
  0/(i)/(iii) empirically observed (Cases (ii)+(iv) reserved)
- Smoke test semantic bifurcation by invariant class (closed-
  form deterministic / MCMC stochastic loose-assertion /
  INVERTED orthogonality)
- INVERTED tolerance handling at checker level (architectural
  separation of comparison direction from dispatch + lifecycle
  infrastructure)
- Mitigation activation framework (mit-i)+(mit-ii)+(mit-iii)+
  (mit-iv) with drift-evidence-driven activation discipline
- Chat-instance-seam recalibration as institutionally-
  legitimate disposition reversal pattern (informed by Code's
  empirical recalibration response across Chat-instance
  transition seam)
- Q-Overshoot recalibration framework V1+V2 + execution-class
  baseline + close findings class baseline empirically
  emerging across cycle

Forward-looking — Phase 6+ inheritance: reserve sub-domain
activation + cycle-architecture recalibration handled at Phase
6+ inheritance preparation sub-session per close arc step 7;
Code's banked findings (chat-instance-seam recalibration
banking) + Phase 5 closeout banking serve as agenda inputs
for Phase 6+ kickoff cycle-architecture recalibration if
warranted (compression candidates 1-4 + Q-disposition
tightening + pre-flight class proportionality + recalibration
runaway consolidation).
