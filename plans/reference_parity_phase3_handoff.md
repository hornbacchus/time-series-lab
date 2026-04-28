# TSL Reference Parity — Phase 3 Handoff Document

**Date:** 2026-04-28
**Author:** Produced by Claude Code at conclusion of CAI Phase 2 work
**Audience:** Future Chat session producing Phase 3 master plan; future TSL engineers

---

## 1. Purpose of This Document

This document bootstraps a fresh Chat session for **Phase 3 master
plan production**. It is NOT itself the master plan; it provides
the context and scope so a new Chat can produce the master plan
without depending on this conversation's history.

**What this document is:**
- A consolidated context dump on what came before Phase 3
- A scope sketch of what Phase 3 should cover
- A working-agreements record carried forward from CAI Phase 2
- A list of open questions the new Chat must resolve

**What this document is NOT:**
- The Phase 3 master plan (deliverable of the new Chat session)
- A continuation of CAI Phase 2 (CAI is closed at 100% wrapper coverage)
- A continuation of Path Q (DEXUSEU investigation is a one-off)
- An execution plan that Claude Code can run against directly

**Read this first** if starting a new Chat session for Phase 3.
Then read the three CAI engineering documents (Section 2 below)
for full context on what TSL has already established.

---

## 2. CAI Phase 2 Background

### What CAI was

The Calibration Audit Initiative (CAI) Phase 2 systematically
audited every TSL technique wrapper for input-validation defects
and audit-field discipline. The cycle ran 2026-04-25 → 2026-04-28
across 28 sessions and closed at **100% wrapper coverage (83/83)**
with 88 findings (40 severe + 42 operational + 6 cosmetic), all
fixed inline.

### What CAI established

**Five failure modes** were characterized across the cycle:

1. **String acceptance via if/elif/else default** — silent
   fall-through to a default branch when the user passes an
   unrecognized string.
2. **HARMFUL try/except suppression** — wrapper catches
   ValueError from upstream library and returns
   `status="success"` with the user's invalid input recorded
   in audit_fields.
3. **Numeric range silent coercion** — wrapper silently changes
   user's value (e.g., `horizon = max(1, horizon)`) without
   surfacing actionable error.
4. **String-handling chain fall-through** — same as Mode 1 but
   the if/elif/else lives in a helper module rather than the
   wrapper itself.
5. **Multi-parameter consistency violation** — wrapper silently
   modifies one parameter when a combination is inconsistent
   (e.g., `damped_trend=True` + `trend=None`).

**Validation-presence pattern (100% predictive across 77 extension wrappers):**
A wrapper produces zero CAI findings if and only if (1) it has
explicit wrapper-layer validation, OR (2) it has a low-string-
surface parameter set, AND (3) it does not short-circuit upstream
validation via try/except suppression.

**try/except taxonomy:** SAFE-PROPAGATE, SAFE-FALLBACK,
SAFE-RERAISE are valid; HARMFUL is forbidden post-Session 17.

### Durable artifacts produced

These three engineering documents synthesize CAI's institutional
knowledge into operational reference material:

- **`docs/engineering/wrapper_development_standard.md`** (C-1):
  Directive standard ("must"); binding for new wrapper PRs.
  Pre-merge checklist (B-1 through B-13 binding + A-1 through
  A-3 aspirational), validation requirements, audit field
  discipline, canonical test suite requirement.

- **`docs/engineering/validation_patterns_reference.md`** (C-2):
  Diagnostic + fix patterns. Per-failure-mode test patterns,
  fix patterns, empirical examples (with F-* IDs), try/except
  taxonomy with examples, audit methodology. Appendix A:
  per-finding cross-reference index of all 88 CAI findings.

- **`docs/engineering/cai_empirical_findings.md`** (C-3):
  Descriptive synthesis. Cycle statistics, methodology
  evolution narrative, 12 cross-method empirical artifacts
  (GARCH variant ranking, HAR-RV vs HAR-CJ relationship, rates
  pair cointegration loss, ARIMA suitability conclusions, etc.),
  10 validated engineering principles.

- **`docs/calibration_audit_status.md`**: Per-wrapper status
  tracker (master tracker for the cycle). Now updated to point
  to the three engineering docs as authoritative reference.

- **`docs/calibration_audit/*_findings_*.md`**: 28 per-session
  findings docs as audit trail. Retained for re-investigation
  but no longer the primary reference.

### Why this matters for Phase 3

CAI Phase 2 was a **Level 1 + partial Level 2** correctness
verification cycle (see Section 3). It did NOT systematically
verify that wrapper outputs match reference implementations —
that's Phase 3's job. CAI's institutional knowledge feeds Phase 3
in two ways: (a) all 83 wrappers now have validated input
discipline (so parity tests don't trip on input-handling bugs),
and (b) the three engineering documents establish the working
agreements and discipline that Phase 3 should inherit.

---

## 3. The Four Levels of Correctness Verification

TSL's correctness verification work decomposes into four levels:

### Level 1 — Wrapper input validation
Does the wrapper reject invalid input with actionable errors?
Do silent string acceptance, numeric range coercion, or
multi-parameter consistency violations exist?

**Status: HIGH confidence post-CAI.** All 83 wrappers audited;
88 findings fixed; validation-presence pattern empirically
verified across 77 extension wrappers.

### Level 2 — Wrapper math correct on canonical inputs
Does the wrapper produce mathematically correct output on
synthetic fixtures with known properties (recovers known DGP
parameters, produces expected behavior on canonical adversarial
inputs)?

**Status: MODERATE confidence post-CAI.** Each wrapper has 6-9
canonical test cases verifying expected behavior on synthetic
fixtures. Coverage is broad but not deep — canonicals are
correctness sanity checks, not formal proofs.

### Level 3 — Wrapper outputs match reference implementations
Does the wrapper produce numerical output matching established
external references (R packages, Python alternatives, published
algorithms)? Within what tolerance?

**Status: ~10/83 wrappers covered by prior Verification Initiative.**
The remaining ~73 wrappers have no systematic reference parity
testing.

**Phase 3 = Level 3 systematically.**

### Level 4 — Production stress
Does the wrapper handle production data quirks (missing values,
extreme outliers, regime breaks, computational scale) without
silent failures or numerical instability?

**Status: LOW-MODERATE confidence.** Macro-fixture testing during
CAI Phase 2 covered some Level 4 surface, but not comprehensively
(e.g., no testing on intraday tick data, no million-row
benchmarks).

### Why Level 3 matters

1. **Institutional use cases require numerical agreement** with
   established references. When TSL is used for a publishable
   analysis, peer reviewers will compare TSL's outputs to
   reference implementations. Disagreements without explanation
   are reputational risk.
2. **Cross-method analytical work is more trustworthy** when each
   method has independent validation. The Path Q DEXUSEU
   investigation (Session 30) cross-referenced 6 wrappers; the
   strength of its conclusions depends on each wrapper producing
   correct output. Reference parity establishes that.
3. **External scrutiny** — publication, peer review, institutional
   approval — requires reference parity documentation.

---

## 4. Existing Verification Initiative Coverage

A prior Verification Initiative produced ~12 reference-parity
audit scripts under `tools/reference_parity/scripts/`. These
ARE NOT in Phase 3 scope; they're done.

### Existing parity audits

| ID | Wrapper / area | Reference |
|---|---|---|
| 1a | regression | (regression test infrastructure) |
| 1b | tbats_forecast | R `forecast::tbats` |
| 1c | bvar IRF | R `vars::irf` (closed-form given coefficient matrix) |
| 2a | kalman_filter / kalman_smoother | R `dlm`, R `KFAS` |
| 2b | stochastic_volatility (MCMC SV) | R `stochvol::svsample` |
| 2c | stochastic_volatility (Student-t SV) | R `stochvol::svtsample` |
| 3a | caviar_quantile_dynamics | Engle-Manganelli 2004 reimplementation |
| 3b | har_cj | R `HARModel` |
| 3c | evt_pot_gpd (Ferro-Segers extremal index) | R `extRemes::extremalindex` |
| 3d | johansen_cointegration | R `urca::ca.jo` |
| 3e | forecast_reconciliation (MinT family) | R `hts::MinT`, Python `hierarchicalforecast` |
| 3f | transformer_forecast (attention exposure) | PyTorch native MultiheadAttention |

These are listed in the Verification Initiative reports under
`tools/reference_parity/reports/` and have working CI on the
`parity-fast.yml` workflow.

### Existing parity infrastructure

The Verification Initiative built and shipped:

- **`tools/reference_parity/scripts/audit_*.py`** (12 audit scripts)
- **`tools/reference_parity/fixtures/*.npz`** (synthetic fixtures
  with SHA256 pinning for reproducibility)
- **`tools/reference_parity/reports/*_audit.md`** (per-audit
  reports documenting tolerance achieved)
- **`.github/workflows/parity-fast.yml`** (CI workflow running
  the 10/10 fast-tier parity checks on every push to master).
  Passing this CI is the established pre-merge gate.
- **R subprocess invocation pattern** for Rscript-based reference
  comparisons (the existing audits invoke R via subprocess on
  Windows runner; `r_bridge.py` was a planned utility but the
  current implementation may use simpler patterns).
- **`MANIFEST.toml`-equivalent** version pinning for R packages
  and Python dependencies (encoded in `parity-fast.yml`'s
  `Install fast-tier R packages` step; see `parity-slow.yml` for
  the full slow-tier dependency manifest if it exists).

### Tolerance discipline observed

Existing parity audits use category-specific tolerance bands:

- **Closed-form math** (e.g., 1c BVAR IRF given coefficients):
  abs_tol ≈ 1e-10 (essentially bitwise)
- **Spectral / FFT primitives**: abs_tol ≈ 1e-10 to 1e-12
- **Iterative MLE-fit models** (e.g., 1b TBATS, 3a CAViaR):
  abs_tol ≈ 1e-3 (optimizer initialization sensitivity)
- **MCMC samplers** (2b/2c SV): abs_tol ≈ 5e-3, rel_tol ≈ 5e-2
  (Monte Carlo error)

Phase 3 should adopt and extend this category-specific tolerance
discipline.

### Phase 3 builds on, doesn't duplicate

Phase 3 should reuse the existing infrastructure:
- Same fixture pattern (`tools/reference_parity/fixtures/*.npz`
  with SHA256 pinning)
- Same audit script pattern (`tools/reference_parity/scripts/
  audit_*.py`)
- Same report pattern (`tools/reference_parity/reports/*.md`)
- Same CI workflow extended to cover new audits
- Same R subprocess invocation pattern

---

## 5. Phase 3 Proposed Scope

### Goal

Reference parity testing for the ~73 wrappers not covered by
the prior Verification Initiative. Brings TSL to comprehensive
Level 3 verification status across all 83 wrappers (pending
no-reference exclusions; see below).

### Proposed structure (parallel to CAI but adapted)

Per wrapper:
1. Identify primary reference implementation (R package or Python
   alternative or published algorithm).
2. Build common test fixtures (synthetic with known DGP +
   real macro from existing fixture pool).
3. Run TSL wrapper + reference on identical input.
4. Compare numerical outputs to specified tolerance.
5. Document divergences with explanations (methodology-equivalent
   vs bug vs numerical-precision artifact).
6. Classify findings by severity and disposition.

Per category batch:
- Build category-specific tolerance discipline document.
- Aggregate cross-wrapper findings into batch findings doc.
- Update master parity-status tracker.

### Realistic scope estimate

**25-30 Phase 3 sessions** to complete, comparable in scope to
CAI Phase 2's 28-session arc.

Distribution may differ from CAI:
- Some categories have abundant reference choices (forecasting,
  volatility) — quick batches.
- Some categories have limited references (custom Markov
  variants, certain wavelet primitives) — slower per-wrapper.
- Some wrappers have no clean reference and require alternative
  validation (internal consistency, paper formulas).

### Honest scope acknowledgments

**No-reference wrappers exist.** Some custom implementations
have no clean external reference. Phase 3 cannot achieve parity
for them. Expected categories:
- Parts of wavelet coherence (custom phase-lag estimators)
- Certain Markov regime variants (custom transition probability
  parameterizations)
- Possibly STAR with non-standard transition functions
- Possibly some change-point detectors with bespoke cost
  functions

These should be flagged early in Phase 3 master plan and treated
as documented "no-reference" wrappers with internal-consistency-
only validation, not bug-quality findings.

**Methodology-equivalent divergences are not bugs.** Different
optimizer initialization, different MCMC seed handling, different
default tolerances will produce different outputs even when both
implementations are mathematically correct. Phase 3 must
distinguish these from genuine bugs.

**Tolerance bands need per-category definition.** A single
global tolerance won't work. Volatility model coefficients may
need 1e-3 due to optimizer sensitivity; spectral primitives may
justify 1e-10. The framework needs to be defined upfront.

### What's IN scope

- Numerical agreement with R / Python references on common
  fixtures, within specified tolerance bands.
- Tolerance band definition per wrapper category.
- Divergence interpretation and classification.
- Documentation of no-reference wrappers with reasoning.
- Extension of existing parity infrastructure (CI workflow,
  fixture pool, R subprocess patterns).

### What's OUT of scope

- **Production stress testing (Level 4)** — separate future
  initiative.
- **New wrapper implementations** — Phase 3 audits existing
  wrappers; doesn't add new ones.
- **Performance benchmarking** — different question.
- **Methodology comparison across implementations** ("is R's
  GARCH BETTER than TSL's GARCH") — different question.
- **Bug fixes for newly-discovered reference parity divergences
  that fall outside CAL-R6-style budget** — those become
  separate follow-up work, not blocked on Phase 3 closure.

---

## 6. Working Agreements From CAI Phase 2

Carry-forward agreements (binding for Phase 3 unless explicitly
revised in the master plan):

### Workflow

- **Auto Mode default** for Code execution.
- **Plan Mode reserved** for genuinely new work patterns or
  novel design decisions.
- **Direct push permission established** in
  `.claude/settings.local.json`; no pre-push approval needed
  for routine commits.
- **One commit per session typically;** same-bug-class
  bundling acceptable when same-files + under budget (Session
  17 / Session 22 precedent).

### Audit discipline

- **CAL-R6 budget:** 100 LOC for solo audits, 150 LOC for
  multi-wrapper batches (Session 22 protocol update).
- **Mid-audit reclassification discipline:** when an initial
  finding looks severe, investigate root cause before
  classifying. Specifically check: wrapper bug vs methodology
  artifact vs documented limitation vs audit-script bug. Do
  NOT default to downgrade; investigate.
- **Defer 4th+ severe finding** to follow-up commits UNLESS
  same-bug-class + bounded scope + under budget.
- **Status doc updated per session** (master tracker).
- **Per-session findings doc** in
  `docs/reference_parity/` (or equivalent — different from
  `docs/calibration_audit/` to keep cycles separate).

### Documentation

- Per-session findings doc per session (parallel to CAI).
- Status doc updated per session.
- Final consolidation document at cycle close (parallel to
  CAI's C-1/C-2/C-3 pattern). Phase 3's deliverables should
  produce engineering-grade reference documentation similar in
  quality to CAI's.

### Communication style

The user (Matt) prefers:
- Direct, quantitative, honest uncertainty bounds.
- No hedging unless materially uncertain.
- Structured framing for strategic decisions (diagnose →
  frame → advance → stress-test → synthesize).
- Avoid generic disclaimers and corporate filler.

### Naming convention

- **CAI findings:** `F-{CATEGORY}-{IDENTIFIER}` format
  (e.g., F-G-DISPATCH, F-CSD-COMPOSITE).
- **Phase 3 findings:** suggested prefix `P-{CATEGORY}-{IDENTIFIER}`
  to distinguish from CAI findings.
- **Phase 3 audit scripts:** `audit_p3_<wrapper>.py` or
  similar to distinguish from existing
  Verification Initiative scripts (`audit_1a_*.py` through
  `audit_3f_*.py`).

### Memory / editor instructions

- Per Matt's stated rules: never use the name "Molly" or "Molly
  Nickolin" in output; refer to the desk-head editor of the
  Global Macro Commentary product as "the desk-head editor" or
  "the primary editorial reviewer".
- When drafting prompts intended for Claude Code, prepend "Plan
  mode: on" or "Plan mode: off" line at the top.

---

## 7. Recommended Workflow for Phase 3

A hybrid Chat + Code pattern, derived from end-of-CAI
discussions:

### Phase 3 kickoff (single fresh Chat session)

- New Chat reads this handoff document.
- Resolves the eight open questions in Section 8 with the user.
- Produces the Phase 3 master plan (similar in structure to
  `plans/calibration_audit_phase1_2026_04_25.md`).
- Master plan committed to TSL at
  `plans/reference_parity_phase3_master_plan.md`.
- Output: a comprehensive plan that Code can execute against
  autonomously for routine sessions.

### Phase 3 execution (primarily Code, minimal Chat)

- Code reads master plan, executes per session.
- Sessions ship as commits to TSL.
- User interacts with Code directly (not via Chat) for routine
  audits.
- Most sessions need NO Chat involvement.

### Phase 3 periodic check-ins (Chat, every 5-10 sessions)

- Bring batched Code reports into a fresh Chat session.
- Pattern tracking across sessions (are findings concentrating
  in any wrapper category? Are tolerance bands holding?).
- Protocol calibration if methodology gaps emerge.
- Strategic adjustments if patterns require it.

### Phase 3 closeout (single Chat session)

- Synthesis of Phase 3 findings.
- Documentation parallel to CAI's C-1/C-2/C-3 deliverables
  (parity standard + diagnostic reference + empirical findings).
- Lessons learned for any Phase 4+ correctness work
  (production stress).

### Compaction discipline

The master plan document is the durable strategic artifact, NOT
Chat conversation history. Chat sessions should remain focused
and bounded; if a Chat session runs long enough to risk
compaction, that's a signal to wrap up and commit interim
findings.

CAI Phase 2's working arc spanned multiple Chat conversations
including a compaction event. The handoff pattern (this
document) is the recovery mechanism: a fresh Chat reading a
durable handoff doc retains all strategic context without
needing the full conversation history.

---

## 8. Open Questions for the New Chat to Resolve

The new Chat producing the Phase 3 master plan must resolve
these. NOT pre-decided in this handoff document.

**Q1. Reference implementation choices per wrapper category.**
Which R packages? Which Python alternatives? Some wrappers have
multiple candidates (`rugarch` vs `fGarch` for GARCH; `forecast`
vs `fable` vs `nixtla` for ARIMA family). Define authoritative
reference per category, with rationale for choice.

**Q2. Tolerance discipline.** Single global tolerance (e.g.,
1e-6) vs per-category tolerances (volatility model coefficients
may need 1e-3 due to optimizer initialization sensitivity, while
spectral analysis primitives may justify 1e-10). What's the
framework? CAI's audits demonstrated category-specific tolerance
works; Phase 3 needs a formal definition.

**Q3. Wrappers with no clean reference.** Some custom
implementations (parts of wavelet coherence, certain Markov
regime variants, possibly STAR with specific transitions) may
have no clean external reference. How to handle: skip?
Internal-consistency-only validation? Document as no-reference?
A standard policy is needed.

**Q4. Batching strategy.** CAI batched by category. Phase 3
might batch differently — e.g., by reference-library
availability (R-backed batch, Python-backed batch,
no-clean-reference batch). What's the right structure for
Phase 3?

**Q5. Existing parity infrastructure status.** The 12 existing
audit scripts under `tools/reference_parity/scripts/` work; CI
workflow `parity-fast.yml` is green. What's the current status
of the planned `r_bridge.py` utility? Does the existing R
subprocess pattern need refactoring before Phase 3 extends it?
The new Chat should inspect actual file inventory and document
what's working vs what needs extension vs what needs replacement.

**Q6. Path Q follow-up integration.** The DEXUSEU investigation
(Session 30, `docs/investigations/dexuseu_ews_investigation_2026_04_28.md`)
surfaced specific operational follow-ups (current data pull,
GBP/USD/JPY comparison, dominant-moment investigation). These
are out of Phase 3 scope strictly, but Phase 3's parity work on
FX-relevant wrappers (CSD, EGARCH, change-point detectors) could
make better future investigations possible. Worth coordinating
or keep separate?

**Q7. Macro fixture expansion.** Current fixture is 5 series
(GSPC, DGS2, DGS10, DEXUSEU, GOLD). Phase 3 may benefit from
richer fixtures (multiple FX pairs, more global rates,
commodity baskets). Define scope for fixture work as part of
master plan, or treat as a separate workstream? If Phase 3
includes fixture expansion, that adds session count.

**Q8. Phase 3 success criteria.** CAI Phase 2 had clear closure
criteria: 100% audited, all findings fixed, documentation
produced. Phase 3's equivalent — what is it?
- "X% of wrappers with documented parity status" (binary
  pass/fail)?
- "X% of wrappers passing parity tolerance" (with no-reference
  exclusions stated)?
- "All in-scope wrappers reach a parity verdict (PASS / CAVEAT /
  DOCUMENTED-DIVERGENCE / NO-REFERENCE)"?
- Combination of the above?

The success criterion shapes what "done" means for Phase 3.

---

## 9. New Chat Session Bootstrap Instructions

The new Chat session opening this handoff document should:

1. **Read this entire document.**
2. **Read the three engineering docs (C-1, C-2, C-3)** for full
   CAI context:
   - `docs/engineering/wrapper_development_standard.md`
   - `docs/engineering/validation_patterns_reference.md`
   - `docs/engineering/cai_empirical_findings.md`
3. **Read the original CAI scope** at
   `plans/calibration_audit_phase1_2026_04_25.md` as a
   structural template for what the Phase 3 master plan should
   look like.
4. **Inspect existing parity infrastructure** at
   `tools/reference_parity/` to ground Q5 in actual file
   inventory.
5. **Resolve the eight open questions in Section 8** through
   discussion with the user.
6. **Produce the Phase 3 master plan** at
   `plans/reference_parity_phase3_master_plan.md`.
7. **Verify the master plan is comprehensive** enough that Code
   can execute against it without further Chat input for routine
   sessions (this is the leverage of the upfront planning work —
   minimize per-session Chat involvement during execution).
8. **Commit the master plan.** Phase 3 begins after that commit.

### Recommended new-Chat opening message format

```
[Attach this handoff document]

I want to scope Phase 3 of TSL's correctness verification work
— reference-implementation parity for the ~73 wrappers not
covered by prior verification work.

Background, scope, and working agreements are in the attached
handoff doc.

This conversation should produce the Phase 3 master plan.
Subsequent execution will run primarily in Code with periodic
Chat check-ins for pattern tracking — not the per-session
Chat-drafts-prompts pattern that CAI Phase 2 used.

Read the handoff doc, then let's work through the open
questions and produce the master plan.
```

---

## 10. Final Notes

CAI Phase 2 was originally scoped for 5 sessions (the "core
cycle" plan) and expanded to 28 because the work justified it.
Phase 3 estimates assume similar potential for scope evolution.
The master plan should accommodate scope growth rather than
over-constrain.

This handoff document supersedes any verbal context in prior
Chat conversations. If the new Chat session encounters apparent
contradictions between Chat memory and this document, this
document is authoritative.

The CAI Phase 2 working arc spanned 2026-04-25 to 2026-04-28
across two Chat conversations (with a compaction event between).
The conversation closing with this handoff produced Sessions
16-31:

- Sessions 16-29: Extension cycle (Decomposition through ets_hw
  + CSD deferred-wrapper closure + (C) documentation
  consolidation).
- Session 30: Path Q DEXUSEU investigation.
- Session 31: This handoff document.

**Phase 3 is forward-looking work. CAI Phase 2 is closed.**

---

## Appendix A: Quick-reference inventory

### CAI Phase 2 numerical summary

| Metric | Value |
|---|---|
| Sessions | 28 |
| Wrappers AUDITED | 83 / 83 (100%) |
| Severe findings | 40 (all fixed) |
| Operational findings | 42 (all fixed) |
| Cosmetic findings | 6 |
| Cumulative engine LOC delta | ~1700 |
| Validation-presence pattern accuracy | 100% across 77 extension wrappers |
| Canonical scripts | 86 |
| Final regression suite | 85/85 PASS |
| pytest engine/tests/ | 96/96 PASS |
| CI parity-fast.yml | PASS |

### Existing parity coverage (out of scope for Phase 3)

12 audit scripts under `tools/reference_parity/scripts/`
covering: regression infrastructure (1a), TBATS (1b), BVAR IRF
(1c), Kalman filter/smoother (2a), MCMC SV (2b), Student-t SV
(2c), CAViaR (3a), HAR-CJ (3b), Ferro-Segers extremal index
(3c), Johansen cointegration (3d), MinT reconciliation family
(3e), Transformer attention exposure (3f).

### Phase 3 scope (in scope)

~71 remaining wrappers without prior parity testing. Distributed
across categories: forecasting (ARIMA, ETS, Theta, intermittent
demand, etc.), volatility/risk (GARCH variants, HAR-RV, EVT POT
GPD), multivariate (VAR, VECM, BVAR estimation, DFM, PCA,
forecast reconciliation OLS/WLS — note 3e covered MinT but not
OLS/WLS), state space (local level, local linear trend,
structural TS, particle filter), Markov/regime (HMM, Markov
switching, TAR/SETAR, STAR, NAR/NARX, critical slowing down),
frequency domain (FFT, periodogram, Lomb-Scargle, wavelet
transform, wavelet coherence, EMD/HHT, SSA), causality
(Granger, cross-correlation lag, GCC-PHAT, prewhitened CCF,
rolling CCF, DTW alignment, transfer function), change
points/anomalies (BOCPD, CUSUM/Page-Hinkley, intervention
analysis, PELT, STL+ESD), decomposition (STL, MSTL, classical,
X-13), stationarity tests (ADF, KPSS, PP), missing data
(Denton-Cholette, Kalman imputation, LOESS interpolation),
evaluation/uncertainty (block bootstrap, conformal intervals,
forecast combination, robust estimators, rolling origin CV),
ML/DL (gradient boosting, lightgbm, random forest, xgboost,
LSTM/GRU, TCN, NBEATS, NHiTS, autoencoder, ESN, GP forecast,
Prophet, quantile regression, SVR — note 3f covered transformer
attention but not full transformer parity).

The master plan should produce an exhaustive in-scope wrapper
list with proposed reference per wrapper. This handoff doc
gives a category-level sketch only.

### Key file paths

| Area | Path |
|---|---|
| CAI status doc | `docs/calibration_audit_status.md` |
| CAI engineering docs | `docs/engineering/` |
| CAI per-session findings | `docs/calibration_audit/` |
| CAI audit scripts | `tools/calibration_audit/audit_*.py` |
| CAI canonical tests | `tools/validate_*_canonicals.py` |
| Existing parity audits | `tools/reference_parity/scripts/` |
| Existing parity fixtures | `tools/reference_parity/fixtures/` |
| Existing parity reports | `tools/reference_parity/reports/` |
| Parity CI workflow | `.github/workflows/parity-fast.yml` |
| Engine wrappers | `engine/techniques/*.py` (83 wrappers) |
| Original CAI scope | `plans/calibration_audit_phase1_2026_04_25.md` |
| Path Q investigation | `docs/investigations/dexuseu_ews_investigation_2026_04_28.md` |
| Path Q script | `tools/investigations/dexuseu_ews_investigation_2026_04_28.py` |

---

**End of Phase 3 handoff document.**
