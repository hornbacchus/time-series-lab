# TSL Reference Parity — Phase 4 Master Plan

**Drafted:** 2026-05-01 (plan-mode session)
**Cycle type:** Closure cycle (no new wrappers; finalises v1.2.0 doc set; consumes 13 inherited work items)
**Precedents:** Phase 3.5 master plan (12 sessions; v1.0.0 → v1.1.0 doc-set bump); Phase 3 master plan §1-§18 structure; BYF integration plan + BYF-Mod-1/Mod-2 cycle (precedent for modification cycles)

---

## Context

Phase 3 (Sessions 2–18, closed 2026-04-29) verified 70 wrappers
and issued P-1/P-2/P-3/P-4 v1.0.0 — 65 PASS + 5 CAVEAT + 1
SKIP-graceful, 0 BLOCK. Phase 3.5 (Sessions 1–12, closed
2026-04-30) ran a closure cycle, dispositioned 9 banked
candidates (8 closed in-cycle, 1 partial Phase 4 deferral),
expanded coverage to 83 wrappers, and bumped the doc set to
v1.1.0. Bond Yield Forecast integration cycle (S1–S6 +
modification cycle Mod-1/Mod-2, closed 2026-05-01) added
wrapper #84 and bumped P-4 to v1.1.1. The two-fixture audit
extension at BYF-Mod-2 surfaced two empirical observations
(O-1 near-unit-root VAR companion margin; O-2 Pattern F
invariant tightness) that need banking decisions.

**Phase 4 is a closure cycle, not a discovery cycle.** It
inherits 13 work items: 3 carry-forward from Phase 3.5 + 10
v1.2.0 amendment candidates from BYF. The cycle's goal is to
disposition all 13, issue P-1/P-2/P-3/P-4 v1.2.0, and bank
anything that doesn't fit into a Phase 4.5 / Phase 5 register.
After Phase 4 closes, the parity infrastructure should be
stable for several quarters of routine use without
master-plan-level work.

---

## §1 Purpose

Phase 4 closes the loop on items deferred from Phase 3.5 + BYF
cycles. Operational guidance dense enough that Claude Code can
execute routine sessions without further Chat input; Chat
re-engagement reserved for escalation triggers (§11) and cycle
closeout synthesis.

---

## §2 Inheritance from Prior Cycles

**Working agreements** carried forward verbatim from Phase
3.5 + BYF cycles:

- Auto Mode default for execution; Plan Mode reserved for
  genuinely new work patterns.
- Direct push to master via `.claude/settings.local.json`.
- One commit per session; same-bug-class bundling acceptable
  when same-files + under CAL-R6 budget (100 LOC solo / 150
  LOC multi-wrapper batches).
- Per-session findings doc at
  `docs/reference_parity_phase4/session_<N>_findings.md`.
- P-4 status doc updated per session.
- Pre-merge gate: existing tests preserved + `parity-fast`
  green + `--check-environment` clean + (if engine touches)
  numerical-array preservation vs pre-session baseline.

**Inherited authoritative references:**

- `docs/engineering/parity_standard.md` (P-1 v1.1.0)
- `docs/engineering/parity_diagnostic_reference.md` (P-2 v1.1.0)
- `docs/engineering/parity_empirical_findings.md` (P-3 v1.1.0)
- `docs/reference_parity_status.md` (P-4 v1.1.1)
- `docs/engineering/wrapper_development_standard.md` (C-1)
- `docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md`
- `docs/reference_parity_status.md` §"Phase 4 carry-forward"
  (P4-1, P4-2, P4-3 origin docs)

**Inherited 13-item inheritance register:**

| Source | ID | Description | Class |
|---|---|---|---|
| P3.5 | P4-1 | structural_invariants on 12 inherited wrappers | engine LARGE |
| P3.5 | P4-2 | statsmodels-x13ashtml integration | engine MED |
| P3.5 | P4-3 | CSD wrapper memory scaling | engine SMALL |
| BYF | #1 | R `BVAR` constant-vol Pattern A.2 cross-check | audit MED |
| BYF | #2 | Minnesota dummy-obs Pattern A.3 fragment | audit MED |
| BYF | #3 | stochvol rpy2 partial Pattern A.2 (SV component) | audit MED |
| BYF | #4 | P-2 §B.6.4 bvars-availability trigger entry | doc-only S |
| BYF | #5 | P-1 v1.2.0 docstring-convention amendment | doc + engine MED |
| BYF | #6 | C-1 v2 §"Wrapper module-vs-package layout" | doc-only S |
| BYF | #7 | C-1 v2 §"Bundled-workbook input wrappers" recipe | doc-only S |
| BYF | #8 | C-1 v2 §"Layered validation" | doc-only S |
| BYF | #9 | P-1 v1.2.0 §6.1 tier-classification clarification | doc-only S |
| BYF | #10 | P-1 §pre-merge install-matrix gate (HIGH priority) | doc + CI S |
| BYF Mod-2 | O-1 | Near-unit-root VAR companion eigenvalue (banked observation) | finding |
| BYF Mod-2 | O-2 | Pattern F invariant tightness (banked observation) | finding |

---

## §3 Closure Criteria

Phase 4 closes when:

1. All 13 inheritance items are dispositioned (closed in-cycle
   OR explicitly banked to Phase 4.5+ with reasoning).
2. P-1, P-2, P-3 issued at v1.2.0; P-4 at v1.2.0; C-1 at v2.0.0.
3. CI green on `parity-fast.yml` + `parity-slow.yml`
   (Windows + Linux jobs).
4. Phase 4.5 / Phase 5 carry-forward register exists (even if
   empty).
5. All per-session findings docs landed.

---

## §11 Escalation Triggers

**Carry forward Phase 3 §11.1–§11.7 verbatim:**
empirical divergence > 1 order; reference-version drift;
CI tier reclassification; fixture-pool expansion; Pattern J
catalog growth; single-impl-MLE band-widening; R-bridge
platform regression.

**Phase 4 additions:**

- **§11.8** P4-1 audit-field expansion blast radius. If S8
  Kalman/VECM engine touches require schema-breaking
  `P3ParityCheck` changes, escalate; becomes Phase 5
  prerequisite.
- **§11.9** Pattern A audit reveals actual divergence (not
  methodology-equivalent) on #1, #2, or #3. Do not silently
  bank-and-fix mid-session.
- **§11.10** O-1 boundary breach. If any subsequent fixture
  pushes VAR companion eigenvalue past 0.9999, escalate
  before tightening Pattern F.
- **§11.11** v1.2.0 amendment-site-count overrun. If
  accumulated amendment LOC at S11 close exceeds 600,
  escalate; split S12 into S12a/S12b before issuance.
- **§11.12** Carry-forward churn. If more than 2 new items
  bank to Phase 4.5 during execution, Phase 4 may be
  undersized; escalate.
- **§11.13** P4-2 pathway (c) spill. Pathway (c) is estimated
  at ~150–250 LOC (BYF Session 4 audit-script work landed
  at ~280 LOC for similar empirical-investigation scope, so
  the upper end of this range is realistic, not inflated).
  Spill threshold set at **200 LOC** — the median of the
  estimate range. If S2 commits exceed 200 LOC, S2 splits
  into S2a (direct x13ashtml invocation) + S2b (TSL output
  parsing). The 200-LOC threshold is intentionally above
  the standard CAL-R6 150-LOC batch budget for this
  specific session because the work is meaningfully larger
  than a typical multi-wrapper batch; the trigger fires only
  when S2 actually overruns rather than as a structural
  default.

---

## §14 Out of Scope

Phase 4 explicitly does NOT cover:

1. **New wrapper additions.** 84-wrapper baseline frozen.
   Banks to Phase 5.
2. **Calibration audit re-runs.** No re-validating prior
   PASS verdicts.
3. **Quarterly manifest re-pin window.** P-1 §7.3 cadence
   runs independently.
4. **Phase 5 prerequisites / scaffolding.**
5. **Full BVAR-SV from-scratch reimpl.** Pattern A.3
   for the Minnesota component only (#2); banked otherwise.
6. **CSD chunking pathway (c).** Auto-cap pathway (b)
   commits in S3; pathway (c) banks to Phase 4.5+ if (b)
   proves insufficient on a future fixture.
7. **Pattern J / DSCD widenings unrelated to the 13 items.**
   Discovered drifts during Phase 4 audits bank to Phase 4.5.

---

## §15 Session-by-Session Plan (13 sessions)

Locked decisions from plan-mode review:
- **P4-2 pathway (c)** — bypass statsmodels.x13_arima_analysis
  entirely; direct x13ashtml invocation + TSL output parsing
  (~150–250 LOC).
- **P4-3 pathway (b)** — auto-cap by series length (~20–40
  LOC).
- **Pattern A audits** — 3 separate sessions (S4=#2, S5=#1,
  S6=#3); shared scaffold introduced at S4.
- **Doc closeout** — 2 sessions (S12 = P-1/P-2/P-3 v1.2.0;
  S13 = P-4 v1.2.0 + cycle close).

| Sess | Theme | Items | Risk | Class |
|---|---|---|---|---|
| **S1** | Pre-merge install-matrix gate | #10 | LOW | doc + CI |
| **S2** | P4-2 pathway (c) — bypass statsmodels | P4-2 | LOW-MED | engine |
| **S3** | P4-3 pathway (b) — auto-cap by series length | P4-3 | LOW | engine |
| **S4** | Pattern A audit scaffold + Pattern A.3 #2 | #2 + scaffold | MED | audit |
| **S5** | R `BVAR` constant-vol Pattern A.2 audit | #1 | MED | audit |
| **S6** | stochvol rpy2 partial Pattern A.2 (SV component) | #3 | MED | audit |
| **S7** | P4-1.1 — registry expansion (5 new invariant types) | P4-1a | MED | engine |
| **S8** | P4-1.2 — Kalman/VECM engine audit-field expansion | P4-1b | MED-HIGH | engine |
| **S9** | P4-1.3 — wire 12 inherited wrappers + O-2 Pattern F tightening | P4-1c + O-2 | MED | engine |
| **S10** | C-1 v2 doc bundle | #6, #7, #8 | LOW | doc-only |
| **S11** | P-1/P-2 doc patches + #5 docstring backfill + O-1 banking | #4, #5, #9, O-1 | LOW | doc + engine |
| **S12** | v1.2.0 doc-set issuance — P-1, P-2, P-3 | accumulator | LOW | doc closeout |
| **S13** | P-4 v1.2.0 + cycle close | accumulator + carry-fwd register | LOW | doc closeout |

### Per-session detail

- **S1 — install-matrix gate (#10):** Add P-1 §8.5 pre-merge
  checklist item: "If wrapper introduces new runtime
  dependencies, verify install lines updated across 4
  surfaces: `engine/requirements.txt`,
  `tools/reference_parity/harness/MANIFEST.toml`,
  `parity-fast.yml`, `parity-slow.yml` × Windows + Linux
  jobs." Cite BYF S4-S5 + Phase 3.5 S6 retrospectives. Add
  C-1 cross-reference. ~50 LOC. Front-loaded because
  subsequent engine sessions benefit from the codified gate.

- **S2 — P4-2 pathway (c) bypass statsmodels:** Direct
  x13ashtml invocation from
  `engine/techniques/x13_seasonal_adjust.py`; TSL-side parser
  for x13ashtml output. Abandons
  `statsmodels.x13_arima_analysis`. Expected ~150–250 LOC
  (BYF S4 audit-script precedent for empirical-
  investigation scope of similar shape landed at ~280 LOC).
  Linux runner now PASSes p3_x13 (was SKIP-graceful). Update
  `parity-slow.yml` Linux job to expect PASS; remove
  X13PATH-not-exported clause. **§11.13 spill protocol:**
  if S2 commits exceed **200 LOC** (median of estimate
  range), splits S2a (invocation) + S2b (parser).

- **S3 — P4-3 pathway (b) auto-cap by series length:** Modify
  `engine/techniques/critical_slowing_down.py` (and
  `_csd_helpers.py` if present) to compute n_surrogates per
  series length: `n_surrogates_effective = max(100,
  min(default_per_preset, T // 10))`. Update preset config
  notes to document the cap. Re-run T10Y2Y / DGS5 / WTI
  fixtures to confirm OOM-free + statistically equivalent
  to the n_surrogates=100 workaround. ~20–40 LOC.

- **S4 — Pattern A audit scaffold + #2 Minnesota Pattern
  A.3:** Scaffold reusable Pattern A audit helpers (R env
  verification, fixture loader, tolerance harness; promote
  shared utilities into
  `tools/reference_parity/harness/checks/_pattern_a_helpers.py`
  if they fit the existing harness shape). Apply to #2
  (Minnesota dummy-Y/X reimpl per Doan-Litterman-Sims 1984
  §3 verbatim; ~50 LOC audit). File new audit script at
  `tools/reference_parity/harness/checks/p3_byf_minnesota_dummies.py`
  (or extension of existing `p3_bond_yield_forecast.py`
  per BYF-Mod-2 Option A precedent). Bumps P-2 §C.3/§C.4
  amendment ledger.

- **S5 — #1 R `BVAR` constant-vol Pattern A.2:** Reuse S4
  scaffold. Fit TSL BVAR-SV with stochastic-volatility OFF;
  R `BVAR::bvar()` (Kuschnig & Vashold 2021, JSS) at same
  prior config; compare Minnesota-prior coefficient
  posteriors. Tolerance band: mcmc 5e-3 abs / 5e-2 rel.
  ~250 LOC R audit harness. Bumps P-2 §C.2 amendment
  ledger + P-4 BYF row gains secondary verdict line.
  **§11.9 trigger:** if divergence > 1 order beyond
  tolerance, escalate (real wrapper bug, not methodology-
  equivalent).

- **S6 — #3 stochvol rpy2 partial Pattern A.2:** Per-equation
  log-volatility extraction from TSL BVAR-SV; run
  `stochvol::svsample` on residuals separately; cross-check
  posterior means at the 2b audit's tolerance band (5% mu /
  10% phi / sigma_eta record-only). ~150 LOC audit + 60 doc.
  Bumps P-2 §C.2 + P-3 §3.4 amendment ledger.

- **S7 — P4-1.1 registry expansion:** Populate 5 new
  invariant types in
  `tools/reference_parity/harness/structural_invariants.py`
  per the inventory across the 12 inherited wrappers. **No
  engine touches yet.** Each new type gets a checker stub +
  concrete implementation + unit test under harness/tests/.
  Estimated 10 of 12 wrappers lack registry fit (per Phase
  3.5 S9 audit) so 5 new types covers ~5 wrapper families
  (MCMC convergence, EVT extremal-index, MinT coherence,
  attention normalization, intervals-test). ~200–400 LOC.

- **S8 — P4-1.2 Kalman/VECM engine audit-field expansion:**
  `engine/techniques/kalman_filter.py` exposes
  `filtered_state_cov`, `predicted_state_cov`,
  `smoothed_state_cov` as new audit fields (Kalman covariance
  ordering invariant precondition).
  `engine/techniques/johansen_cointegration.py` exposes
  `determined_rank_trace` (VECM rank invariance precondition).
  Both via `audit_fields` schema extension; T14 fixture
  + T15 allowlist updates in `engine/tests/test_interpretation_contract.py`.
  ~80–120 LOC engine + ~30 LOC test. **§11.8 trigger:**
  if schema-breaking `P3ParityCheck` changes surface, halt
  and escalate.

- **S9 — P4-1.3 wire wrappers + O-2 tightening:** Apply 5
  new invariant types from S7 to corresponding inherited
  wrappers; activate Kalman covariance + VECM rank checks
  from S8's new audit fields. Bundle O-2 Pattern F
  tightening: companion max|eig| PASS threshold from
  <0.999 to <0.9995 (early-warning band; <1.0 still BLOCK).
  Run `parity-fast` + `parity-slow` to confirm no
  regressions on existing 84 wrappers. ~150 LOC + tests.

- **S10 — C-1 v2 doc bundle (#6, #7, #8):** Three new
  sections in `docs/engineering/wrapper_development_standard.md`:
  - §"Wrapper module-vs-package layout" (#6) — single-
    file → `<id>.py`; subpackage → `<id>/__init__.py` +
    `_dispatch.py` + re-export. NEVER co-locate. Cite BYF
    S2 retrospective.
  - §"Bundled-workbook input wrappers" (#7) — recipe:
    prefix sheet names with catalog ID; auto-detect helper
    pattern (cite BYF S3 `_resolve_workbook_sheet_config`).
  - §"Layered validation" (#8) — request-local config copy
    discipline (cite BYF S3 re-entrancy regression test).
  Single commit; ~80 LOC across 3 sections.

- **S11 — Standalone doc patches + #5 docstring backfill +
  O-1 banking:**
  - #4 P-2 §B.6.4 bvars-availability trigger entry (~25 LOC).
  - #5 docstring-convention amendment: P-1 §3.4 ~40 LOC +
    engine docstring backfill on ~10 wrappers (PCA-using:
    `dynamic_factor_model.py`, `pca_analysis.py`,
    `bond_yield_forecast/data.py`; design-matrix:
    `arima.py`, `var_model.py`, `vecm.py`, `johansen_cointegration.py`,
    `bvar.py`; truncated decompositions: `bond_yield_forecast`).
    ~10–15 LOC per wrapper docstring; ~140 LOC total engine.
  - #9 P-1 §6.1 tier-classification clarification (~20 LOC).
  - O-1 banking: P-3 §3.4 NEW finding entry "near-unit-root
    VAR companion margin observation (BYF-Mod-2 34-mat;
    informational, not Pattern)." (~25 LOC).
  Engine docstring touches require running BYF + impacted
  wrapper test suites for sanity.

- **S12 — v1.2.0 doc-set issuance — P-1, P-2, P-3:**
  Consolidate per-session amendment ledger from S1–S11.
  Bump P-1 → v1.2.0; P-2 → v1.2.0; P-3 → v1.2.0. Single
  commit per Phase 3.5 S11 precedent. **§11.11 trigger:**
  if accumulated amendment LOC exceeds 600, split S12 into
  S12a/S12b. Verify all cross-references resolve (P-1 ↔
  P-2; P-2 ↔ P-3; P-1 ↔ C-1).

- **S13 — P-4 v1.2.0 + cycle close:** Bump P-4 → v1.2.0
  reflecting all session outcomes; document Phase 4.5+
  carry-forward register (likely empty if cycle ran
  clean); update the cycle-close summary banner per Phase
  3 / Phase 3.5 precedent. Single commit.

---

## §15.1 v1.2.0 Amendment Site Catalog (S12 input)

The per-session amendment ledger that S12/S13 consolidate.
**Provisional**; sessions append rows.

**P-1 `parity_standard.md` v1.1.x → v1.2.0:**

- §3.4 docstring-convention amendment (S11 source) — ~40 LOC
- §6.1 tier-classification clarification (S11 source) — ~20 LOC
- §8.5 pre-merge install-matrix gate (S1 source) — ~20 LOC
- §12 changelog v1.2.0 entry — ~5 LOC

**P-2 `parity_diagnostic_reference.md` v1.1.x → v1.2.0:**

- §B.6.4 NEW bvars-availability trigger (S11 #4) — <25 LOC
- §C.2 NEW R `BVAR` constant-vol entry (S5 #1) — ~30 LOC
- §C.2 NEW stochvol SV-component entry (S6 #3) — ~25 LOC
- §C.3/§C.4 NEW Minnesota dummy-obs entry (S4 #2) — ~40 LOC
- Pattern F invariant-tightness rule (S9 O-2) — ~20 LOC

**P-3 `parity_empirical_findings.md` v1.1.x → v1.2.0:**

- §3.4 NEW BYF-cycle stochvol partial A.2 finding (S6) — ~40 LOC
- §3.x NEW O-1 near-unit-root margin observation (S11) — ~25 LOC
- §6 closure rows for #1, #2, #3 dispositions — ~20 LOC

**P-4 `reference_parity_status.md` v1.1.x → v1.2.0 (S13 only):**

- BYF rows: #1 + #3 secondary verdict lines — ~10 LOC
- Phase 4 cycle-close subsection — ~30 LOC
- Phase 4.5+ carry-forward register — ~20 LOC

**C-1 `wrapper_development_standard.md` v2.x (S10):**

- §"Wrapper module-vs-package layout" (#6) — ~25 LOC
- §"Bundled-workbook input wrappers" recipe (#7) — ~30 LOC
- §"Layered validation" (#8) — ~25 LOC
- Cross-ref to P-1 §8.5 install-matrix gate (#10) — ~10 LOC

**Estimated total amendment LOC across 5 docs:** ~535. Under
the §11.11 trigger ceiling of 600.

---

## §17 Risks and Scope Evolution

**Most likely derailment vectors and absorption strategy:**

1. **P4-1 underestimate (highest probability).** S7/S8/S9
   decomposition is intentional; if S8 spills, S9 absorbs;
   if S9 spills, bank "wire 3 of 12" to Phase 4.5 rather
   than extending Phase 4. **Hard rule:** P4-1 does not
   get a fourth session in Phase 4.

2. **R `BVAR` env install failure (medium).** Phase 3 hit
   this with `bvars`; Phase 4 may hit it with `BVAR`.
   Pattern A.1+F fallback discipline carries forward; #1
   verdict downgrades to PASS-A.1+F + DOCUMENTED-DIVERGENCE
   if R env unavailable; bank to Phase 4.5.

3. **P4-2 pathway (c) ~250-LOC ceiling (medium-high).**
   Direct x13ashtml invocation + TSL parser is ambitious
   for a single session. **§11.13 spill protocol** splits
   S2 into S2a/S2b. Schedule absorbs from the 2-session
   under-budget margin (target 13; budget 13–15).

4. **CSD pathway (b) auto-cap formula tunable (low-medium).**
   S3 includes a fixture re-run gate; if cap+1 fixtures
   still OOM, escalate per §11.

5. **Doc-set bump scope creep (medium).** §11.11 trigger;
   pre-emptively design S12 around section-by-section
   commits within a single session, falling back to
   S12a/S12b split.

6. **O-1 escalation (low probability, high impact).** A
   new fixture pushes companion eigenvalue past 0.9999.
   §11.10 trigger; if hit, pause Phase 4 mainline, run a
   focused mini-cycle (~1 session), resume.

**Scope-evolution philosophy:** Phase 4 is a **closure
cycle**, not a discovery cycle. Anything not in the
13-item inheritance is banked, not absorbed. The §14
out-of-scope list is the contract that lets the schedule
hold.

**Session count budget:** target **13** (best case 11 if
P4-1 collapses to 2 sessions; ceiling **16** if scope
expands per any of the §11 triggers above).

---

## §18 Critical Files

**Engine touch surface:**
- `engine/techniques/x13_seasonal_adjust.py` (S2; pathway c rewrite)
- `engine/techniques/critical_slowing_down.py` (S3)
- `engine/techniques/_csd_helpers.py` if present (S3)
- `engine/techniques/kalman_filter.py` (S8)
- `engine/techniques/johansen_cointegration.py` (S8)
- `engine/techniques/dynamic_factor_model.py`,
  `pca_analysis.py`, `arima.py`, `var_model.py`,
  `vecm.py`, `bvar.py`,
  `bond_yield_forecast/data.py` (S11 #5 docstring backfill)
- `engine/tests/test_interpretation_contract.py` (S8 T14/T15)

**Harness:**
- `tools/reference_parity/harness/structural_invariants.py` (S7, S9)
- `tools/reference_parity/harness/checks/_pattern_a_helpers.py`
  (S4 NEW; reused S5, S6)
- `tools/reference_parity/harness/checks/p3_byf_minnesota_dummies.py`
  (S4 NEW) OR extension of `p3_bond_yield_forecast.py`
- `tools/reference_parity/harness/checks/p3_byf_bvar_constant_vol.py`
  (S5 NEW)
- `tools/reference_parity/harness/checks/p3_byf_stochvol_partial.py`
  (S6 NEW)
- `tools/reference_parity/harness/checks/p3_x13.py` (S2 update)

**Docs:**
- `docs/engineering/parity_standard.md` (P-1) — S1, S11, S12
- `docs/engineering/parity_diagnostic_reference.md` (P-2) —
  S4, S5, S6, S9, S11, S12
- `docs/engineering/parity_empirical_findings.md` (P-3) —
  S6, S11, S12
- `docs/reference_parity_status.md` (P-4) — every session;
  S13 v1.2.0 issuance
- `docs/engineering/wrapper_development_standard.md` (C-1) —
  S1, S10
- `docs/reference_parity_phase4/session_<N>_findings.md` —
  every session

**CI:**
- `.github/workflows/parity-fast.yml` — S1 install matrix
- `.github/workflows/parity-slow.yml` — S1 install matrix;
  S2 Linux job p3_x13 PASS expectation update

---

## §19 Verification (per-session)

Per-session pre-commit gates (carry forward Phase 3.5 + BYF
discipline):

1. `engine/tests/` pytest 96/96 PASS preserved (no engine
   tests added/removed without explicit cycle-level
   approval).
2. Per-wrapper test suite green (e.g., `bond_yield_forecast/tests/`
   on any session touching BYF; `kalman_filter` tests on S8;
   etc.).
3. `parity-fast` tier `--check-environment` clean.
4. `parity-fast` tier full sweep: count + outcome distribution
   unchanged from previous-session baseline (audit-runtime
   sessions S4–S6 may add new metric keys; numerical-array
   counts must not regress).
5. (Engine sessions only) Pre/post numerical-array
   byte-identical equivalence on the wrapper's canonical
   fixture, excluding clock fields per Session 0 Refinement
   3 pattern.
6. CI green on `parity-fast.yml` post-push; engine sessions
   also gated on `parity-slow.yml`.

**End-of-cycle verification (S13):**

- All P-x docs at v1.2.0; cross-references resolve.
- 13-item inheritance register fully dispositioned (closed
  or banked).
- Phase 4.5+ register exists in P-4.
- Cycle-close commit summary surfaces session count, doc
  bump, banked items.

---

## §20 Communication / Carry-forward

Per Phase 3.5 + BYF cycle precedent: Chat re-engagement at
- §11 escalation triggers
- Mid-cycle check-ins after S6 (Pattern A audits done) and
  S9 (P4-1 done) for pattern-tracking
- S13 cycle close

**Carry-forward to Phase 4.5 / Phase 5 (post-S13 register
seeded):**

- Whatever fails to close in-cycle.
- BVAR-SV full Pattern A.3 reimpl (BYF candidate #2 deeper
  scope).
- CSD chunking pathway (c) if pathway (b) proves
  insufficient.
- Phase 5 prerequisites (TBD).

End of Phase 4 master plan.
