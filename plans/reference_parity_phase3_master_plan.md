# TSL Reference Parity — Phase 3 Master Plan

**Date:** 2026-04-28
**Author:** Phase 3 kickoff Chat session
**Status:** **PHASE 3 CLOSED at Session 18 (2026-04-29).
PHASE 3.5 CLOSED at Session 12 (2026-04-30).** Preserved as
authoritative record of execution-phase guidance through both
cycles. Phase 3 final outcomes: 70/70 wrappers covered, 0 BLOCK,
65 PASS / 5 CAVEAT / 1 SKIP-graceful, 17 sessions used vs
original 18-22 budget. **Phase 3.5 final outcomes: 9 banked
candidates dispositioned (8 closed in-cycle; 1 partial Phase 4
deferral), P-1/P-2/P-3/P-4 all at v1.1.0, 12 sessions used vs
17-session budget (5 sessions under budget), 3 Phase 4 carry-
forward items documented.** See [P-4 status tracker](../docs/reference_parity_status.md),
[P-1 parity standard](../docs/engineering/parity_standard.md),
[P-2 diagnostic reference](../docs/engineering/parity_diagnostic_reference.md),
[P-3 empirical findings](../docs/engineering/parity_empirical_findings.md)
for the v1.1.0 closeout deliverables. Phase 3.5 per-session
findings docs preserved at [`docs/reference_parity_phase3_5/`](../docs/reference_parity_phase3_5/).
**Phase 4 launches immediately at Phase 3.5 Session 12
closeout** (this commit); Phase 4 master plan drafts in next
Chat session per established handoff-doc → master-plan
pattern (P-1/P-2/P-3/P-4 v1.1.0 serve as the handoff doc).
**Supersedes:** Open questions in `reference_parity_phase3_handoff.md` Section 8
**Companion:** `reference_parity_phase3_handoff.md` (background, scope sketch, working-agreement carry-forward)

---

## 1. Purpose

This document is the operational master plan for Phase 3 of TSL's correctness verification work: **Level 3 reference-implementation parity for the ~71 wrappers not covered by the prior Verification Initiative**. It is comprehensive enough that Claude Code can execute routine sessions against it without further Chat input.

Chat re-engagement is reserved for: (a) periodic pattern-tracking check-ins between batches, (b) escalation triggers defined in Section 11, (c) Phase 3 closeout synthesis.

---

## 2. Inheritance From CAI Phase 2

The following CAI working agreements **carry forward verbatim** unless explicitly revised in this plan:

- Auto Mode default for Code execution; Plan Mode reserved for genuinely new work patterns.
- Direct push permission via `.claude/settings.local.json`; no pre-push approval for routine commits.
- One commit per session typically; same-bug-class bundling acceptable when same-files + under budget.
- **CAL-R6 budget:** 100 LOC for solo audits, 150 LOC for multi-wrapper batches.
- Mid-audit reclassification discipline: investigate root cause before classifying severe findings.
- Status doc updated per session.
- Per-session findings doc per session.

The following authoritative references are inherited:

- `docs/engineering/wrapper_development_standard.md` (C-1)
- `docs/engineering/validation_patterns_reference.md` (C-2)
- `docs/engineering/cai_empirical_findings.md` (C-3)

CAI's three-document deliverable pattern is the template for Phase 3 closeout (Section 16).

---

## 3. Closure Criteria

### 3.1 Four-verdict closure rule

Phase 3 closes when **100% of in-scope wrappers** reach one of four verdicts:

| Verdict | Meaning | CI gate |
|---|---|---|
| `PASS` | Output matches reference within stated tolerance on stated fixtures | Yes |
| `CAVEAT` | Matches except in stated regime (boundary, near-singular, etc.) | Yes (with caveat noted) |
| `DOCUMENTED-DIVERGENCE` | Does not match; divergence is methodology-equivalent (different optimizer / prior / default), not a bug | No |
| `NO-REFERENCE` | No clean external reference; internal-consistency only (per Section 5 Tier C) | No |

No `DEFERRED` status. Deferral creates scope leakage; explicit verdict is required even if the verdict is `NO-REFERENCE`.

### 3.2 Engineering deliverables (closeout)

Phase 3 closes only when all four below are committed:

- **P-1: `docs/engineering/parity_standard.md`** — Directive standard. Defines the four-verdict rule, output-surface discipline, tolerance bands, reference-version pinning protocol, CI tier classification. Binding for new wrappers.
- **P-2: `docs/engineering/parity_diagnostic_reference.md`** — Diagnostic + fix patterns. Per-divergence-class diagnostic patterns, methodology-equivalent classification heuristics, R-subprocess vs Python-import invocation patterns, per-finding cross-reference index.
- **P-3: `docs/engineering/parity_empirical_findings.md`** — Descriptive synthesis. Cycle statistics, per-batch summaries, cross-method empirical artifacts, validated principles, lessons learned.
- **P-4: `docs/reference_parity_status.md`** — Per-wrapper status tracker (master tracker for Phase 3). Updated per session during execution; finalized at closeout.

### 3.3 CI gate

Extended `parity-fast.yml` and `parity-slow.yml` workflows must run all `PASS` and `CAVEAT` verdicts on schedule (Section 12). Green CI on the extended workflow is the pre-merge gate for any future wrapper PR.

---

## 4. Output-Surface Discipline

Each wrapper produces multiple outputs. Phase 3 audits do not test all outputs; testing all is wasteful, testing arbitrary subsets is silent-gap risk. Three-tier output policy:

| Tier | Scope | Tolerance treatment | Examples |
|---|---|---|---|
| **Primary** | Must match reference within stated tolerance | Strict (Section 7) | Coefficients, primary forecast / state series, log-likelihood |
| **Secondary** | Should match within loose tolerance | 5–10× primary tolerance | Residuals, standard errors, AIC/BIC |
| **Diagnostic** | Sanity check only, no pass/fail | N/A | Plotting outputs, summary text, derived diagnostics |

Per-wrapper output-tier assignment lives in Appendix A (wrapper inventory). Default assignment per category:

- **Estimation wrappers** (GARCH, ARIMA, VAR): Primary = parameter vector + log-likelihood; Secondary = residuals + AIC/BIC.
- **Forecast wrappers** (ETS, Theta): Primary = h-step point forecast; Secondary = forecast intervals.
- **State-space wrappers** (Kalman variants, DFM): Primary = filtered/smoothed state means; Secondary = state covariances.
- **Test statistics** (ADF, KPSS, PP, Granger): Primary = test statistic + p-value.
- **Decompositions** (STL, MSTL, EMD): Primary = component series.
- **Spectral** (FFT, periodogram, wavelet): Primary = transformed series / power spectrum.

---

## 5. Reference Availability Tiers

Three-tier policy. **Skipping is forbidden**; explicit verdict per wrapper.

### Tier A — Clean reference

Wrapper has an authoritative external reference (R package, Python alternative, published algorithm with closed-form). Standard parity audit per Section 8 protocol.

### Tier B — Partial reference

Wrapper composes multiple components, some of which have references and some bespoke. Component-level parity for matched parts; internal-consistency for bespoke parts. The audit report explicitly documents the tier-A and tier-B sub-components.

Examples expected:
- Wavelet coherence: spectral primitives (Tier A) + custom phase-lag estimator (Tier B sub-component).
- STAR with non-standard transition: linear AR component (Tier A) + transition function (Tier B sub-component).
- Some change-point detectors with bespoke cost functions: detection statistic (Tier A) + cost function (Tier B sub-component).

### Tier C — No reference

No clean external reference exists. Internal-consistency-only validation:

1. **DGP recovery:** wrapper recovers known data-generating-process parameters within stated tolerance on synthetic fixture.
2. **Closed-form spot checks:** any analytical case for which a formula exists is tested.
3. **Self-parity (regression test):** pinned reference output committed; future runs must match (drift detection).

Documented in P-4 with `NO-REFERENCE` verdict and reasoning.

---

## 6. Reference Implementation Matrix

Default policy: **R-first for statistical wrappers; Python-first for ML/DL.** Cross-check with second reference for high-stakes families (GARCH, ARIMA, VAR).

### 6.1 Reference matrix

| Category | Primary reference | Cross-check | Notes |
|---|---|---|---|
| ARIMA family (AR, MA, ARIMA, SARIMA, ARIMAX) | R `forecast::Arima`, `forecast::auto.arima` | R `fable` | Hyndman ecosystem canonical |
| ETS | R `forecast::ets` | R `fable::ETS` | |
| Theta method | R `forecast::thetaf` | — | |
| Intermittent demand (Croston, SBA, TSB) | R `forecast::croston`, R `tsintermittent` | — | |
| sGARCH, GJR-GARCH, EGARCH, IGARCH | R `rugarch::ugarchfit` | Python `arch` | rugarch has best variant coverage |
| HAR-RV | R `HARModel` | — | Same package as 3b (HAR-CJ) |
| EVT POT GPD | R `evd`, R `extRemes` | — | Distinct from 3c (extremal index) |
| VAR | R `vars::VAR` | — | |
| VECM | R `urca::ca.jo` + `vars::vec2var` | — | Already in 3d |
| BVAR estimation | R `BVAR::bvar` | — | Distinct from 1c (IRF given coefs) |
| DFM | R `MARSS::MARSS` | Python `statsmodels.tsa.DynamicFactor` | EM-fit; loose tolerance expected |
| PCA | Python `sklearn.decomposition.PCA` | R `prcomp` | Closed-form; tight tolerance |
| Forecast reconciliation OLS/WLS | R `hts::combinef` | Python `hierarchicalforecast` | 3e covered MinT, not OLS/WLS |
| State space — local level, LLT, structural | R `KFAS::KFS` | R `dlm` | Already used in 2a |
| Particle filter | R `pomp` | Python `particles` | Stochastic; loose tolerance |
| HMM | R `depmixS4` | Python `hmmlearn` | EM stochastic |
| Markov switching | R `MSwM::msmFit` | — | |
| TAR / SETAR | R `tsDyn::setar` | — | |
| STAR | R `tsDyn::star` | — | Custom transitions → Tier B/C |
| NAR / NARX | R `tsDyn::nlar` | — | |
| Critical slowing down (CSD) | Custom (paper-formula) | — | Likely Tier B |
| FFT | Python `scipy.fft` | NumPy `numpy.fft` | Closed-form; tight tolerance |
| Periodogram | Python `scipy.signal.periodogram` | — | Closed-form |
| Lomb-Scargle | Python `astropy.timeseries.LombScargle` | `scipy.signal.lombscargle` | |
| Wavelet transform (DWT, MODWT) | R `waveslim` | Python `pywt` | |
| Wavelet coherence | R `biwavelet` | — | Custom phase-lag → Tier B |
| EMD / HHT | Python `PyEMD` | — | |
| SSA | Python `pyts.decomposition.SingularSpectrumAnalysis` | R `Rssa` | |
| Granger causality | R `lmtest::grangertest` | — | |
| Cross-correlation lag, prewhitened CCF, rolling CCF | R `stats::ccf` | NumPy `correlate` | |
| GCC-PHAT | Custom (closed-form, paper) | — | Tier A via formula |
| DTW alignment | R `dtw::dtw` (Giorgino) | Python `dtaidistance` | |
| Transfer function | R `TSA::arimax` | — | |
| BOCPD | Python `bocd` | — | |
| CUSUM / Page-Hinkley | R `cpm` | Python `ruptures` | |
| Intervention analysis | R `TSA::arimax` | — | |
| PELT | R `changepoint::cpt.mean`, `cpt.var`, `cpt.meanvar` | Python `ruptures.Pelt` | |
| STL + ESD | R `stats::stl` + custom ESD | — | Combination |
| STL | R `stats::stl` | — | |
| MSTL | R `forecast::mstl` | — | |
| Classical decomposition | R `stats::decompose` | — | |
| X-13 | R `seasonal` | — | Wraps X-13ARIMA-SEATS binary |
| ADF | R `urca::ur.df` | R `tseries::adf.test` | Closed-form critical values |
| KPSS | R `urca::ur.kpss` | R `tseries::kpss.test` | |
| PP | R `urca::ur.pp` | R `tseries::pp.test` | |
| Denton-Cholette | R `tempdisagg::td` | — | |
| Kalman imputation | R `KFAS` | — | Same as state space |
| LOESS interpolation | R `stats::loess` | Python `statsmodels.nonparametric.lowess` | |
| Block bootstrap, MBB, stationary bootstrap | R `boot::tsboot`, `tseries::tsbootstrap` | — | Stochastic; distributional check |
| Conformal intervals | Python `MAPIE` | Python `nonconformist` | |
| Forecast combination | R `forecastHybrid` | — | |
| Robust estimators | R `robustbase` | — | |
| Rolling-origin CV | R `forecast::tsCV` | — | |
| Random forest | Python `sklearn.ensemble.RandomForestRegressor` | — | Direct (same library) |
| Gradient boosting | Python `sklearn.ensemble.GradientBoostingRegressor` | — | |
| XGBoost | Python `xgboost` | Direct | |
| LightGBM | Python `lightgbm` | Direct | |
| SVR | Python `sklearn.svm.SVR` | — | |
| Quantile regression | Python `statsmodels.regression.quantile_regression` | R `quantreg` | |
| LSTM / GRU | PyTorch native | — | Seed-pinning required |
| TCN | PyTorch native | — | Seed-pinning required |
| N-BEATS, N-HiTS | Python `neuralforecast` (Nixtla) | — | Seed-pinning required |
| Autoencoder | PyTorch native | — | Seed-pinning required |
| ESN | Python `reservoirpy` | — | |
| GP forecast | Python `GPyTorch` | — | |
| Prophet | Python `prophet` | — | |

### 6.2 Reference selection rationale

Selection prefers (in order): (i) widest variant coverage within one package (rugarch over fGarch); (ii) most cited in academic literature; (iii) actively maintained at time of master plan commit; (iv) compatible with existing `parity-fast.yml` R-subprocess pattern.

Cross-check pairing applied where wrapper sits in TSL's high-stakes core (GARCH, ARIMA, VAR, KPSS) — i.e., wrappers used heavily in cross-method analytical work.

### 6.3 Reference package pin manifest

See Appendix B for the version pin manifest. Pinned at master plan commit; re-pinned per Section 13 protocol.

---

## 7. Tolerance Discipline

Per-class bands; no global tolerance. Extends the CAI-observed pattern to the Phase 3 surface.

### 7.1 Tolerance classes

| Class | Abs tol | Rel tol | Examples |
|---|---|---|---|
| Closed-form analytical | 1e-10 | 1e-9 | BVAR IRF given coefs, ADF/KPSS critical values |
| Spectral / FFT primitives | 1e-10 | 1e-12 | FFT, periodogram, DWT |
| OLS / closed-form GLS | 1e-8 | 1e-7 | Reconciliation OLS/WLS, PCA, LOESS |
| MLE-fit (deterministic optimizer) | 1e-3 | 1e-2 | GARCH coef, ARIMA coef, TBATS |
| EM-stochastic | 1e-2 | 5e-2 | DFM, HMM, Markov switching |
| MCMC samplers | 5e-3 | 5e-2 | SV (existing 2b/2c) |
| ML (seed-pinned, deterministic) | 1e-3 | 1e-2 | XGB, LGB, RF (with seed + n_jobs=1) |
| DL training (seed-pinned, deterministic flag) | 1e-2 | 5e-2 | LSTM, TCN, N-BEATS |
| ML/DL (non-portable seed) | N/A | Distributional check | If hardware/version drift breaks reproducibility → Tier C |

### 7.2 Output-tier × class composition

- Primary outputs: tolerance per class above.
- Secondary outputs: 5–10× the primary tolerance band for that class.
- Diagnostic outputs: no formal tolerance.

### 7.3 Reporting convention

Audit reports state achieved tolerance, not target tolerance. Format: `abs_max=X, rel_max=Y, n_compared=N, class=<class>, verdict=<verdict>`.

---

## 8. Audit Protocol (per wrapper)

Standard audit sequence per wrapper. Generator-templated post-Session 5.

1. **Identify reference** (per Section 6.1) and pin version (per Appendix B).
2. **Build fixture set** — synthetic (DGP-recovery), canonical (from existing pool), real-macro (from existing pool). Pin via SHA256.
3. **Invoke TSL wrapper** on fixture; extract Primary + Secondary outputs.
4. **Invoke reference** on identical fixture; extract corresponding outputs.
5. **Compare** per Section 7 tolerance class; log abs_max / rel_max / n_compared.
6. **Classify** per Section 5 tier × Section 3.1 verdict.
7. **Document divergences** — methodology-equivalent vs bug-suspected vs numerical-precision artifact.
8. **Emit report** at `tools/reference_parity/reports/p3_<wrapper>_audit.md`.
9. **Update P-4 status tracker.**
10. **Commit** with one-line summary referencing audit ID.

Bug-suspected divergences trigger CAL-R6-style finding workflow: investigate root cause, classify severity, fix inline if under budget, defer to follow-up commit otherwise.

---

## 9. Batching Strategy

Hybrid: primary by reference library (amortizes subprocess setup overhead and import-side complexity), secondary by methodology (cross-wrapper findings cohere within batch).

### 9.1 Batch sequence

| Batch | Theme | Reference stack | Wrapper count | Sessions |
|---|---|---|---|---|
| 1 | R `forecast` family | R `forecast`, `tsintermittent` | ~9 | 3 (manual templates) |
| — | **Generator abstraction** | — | — | 1 |
| 2 | R volatility | R `rugarch`, `HARModel`, `evd`/`extRemes` | ~6 | 2 |
| 3 | R multivariate | R `vars`, `urca`, `BVAR`, `MARSS`, `hts` | ~6 | 2 |
| 4 | R Markov / nonlinear | R `depmixS4`, `MSwM`, `tsDyn` | ~7 | 2 |
| 5 | R state space | R `KFAS`, `dlm`, `pomp` | ~4 | 1 |
| 6 | R change-points / stationarity | R `urca`, `tseries`, `changepoint`, `cpm` | ~8 | 2 |
| 7 | Python spectral | Python `scipy`, `pywt`, `PyEMD`, `pyts` | ~7 | 2 |
| 8 | Python ML | Python `sklearn`, `xgboost`, `lightgbm` | ~7 | 2 |
| 9 | Python DL | PyTorch, `neuralforecast`, `prophet`, `GPyTorch`, `reservoirpy` | ~10 | 3 |
| 10 | Misc + Tier C consolidation | Mixed (DTW, conformal, bootstrap, GCC-PHAT, transfer fn, custom Markov, wavelet coherence) | ~7 | 2 |
| — | **Documentation: P-1, P-2, P-3** | — | — | 3 |
| — | **CI extension + closeout commit** | — | — | 1 |

Total: **26 execution sessions** + **3 Chat check-ins** (between Batches 1–2, 5–6, 10–docs).

### 9.2 Batch-level deliverables

Per batch, in addition to per-wrapper audit reports:

- `tools/reference_parity/reports/p3_batch_<N>_summary.md` — cross-wrapper findings, tolerance-band performance, reference-library issues encountered.
- P-4 status tracker updated with batch-complete entries.
- Pattern notes for Chat check-in (carried forward, not committed each session).

---

## 10. Parity-Test-Generator (Q9, Option B)

### 10.1 Sequencing

- **Sessions 2–4 (Batch 1):** manual audits using copy-paste templates derived from existing audit scripts (`audit_1a_*.py` through `audit_3f_*.py`).
- **Session 5 (Generator abstraction):** abstract Batch 1 patterns into a shared harness.
- **Sessions 6+ (Batch 2 onward):** use generator.

### 10.2 Generator scope

Shared harness at `tools/reference_parity/harness/`:

- **`harness.py`** — common audit loop: fixture load → TSL invoke → reference invoke → compare → classify → emit report.
- **`r_invoke.py`** — R subprocess wrapper utility (extends or replaces `r_bridge.py` per Session 1 inventory).
- **`py_invoke.py`** — Python-import reference invocation utility (for Batches 7–9).
- **`compare.py`** — tolerance class application + verdict assignment.
- **`report_template.py`** — standardized audit report emission.

Per-wrapper config: ~50 LOC defining wrapper signature, fixture choice, output mapping, tolerance class, reference invocation. Lives in `tools/reference_parity/configs/p3_<wrapper>.toml` or equivalent.

### 10.3 Generator success criteria

Generator passes if:

1. Batch 2 audit time per wrapper ≤ 50% of Batch 1 manual audit time.
2. Generator reproduces Batch 1 audit results bit-for-bit when re-run on Batch 1 wrappers.
3. Adding a new wrapper config requires zero modification to harness code (only config file).

If generator fails (1) or (2), revert to manual templates for remaining batches; Session 5 sunk cost is bounded.

---

## 11. Escalation Triggers (Code → Chat)

Code escalates to Chat for any of the following. Escalation = session-end commit + Chat-ready summary in batch summary doc:

1. **Tolerance band fails systematically** (>30% of wrappers in batch fail at stated tolerance) → Chat re-check tolerance class assignment for category.
2. **Novel divergence type** not in CAI taxonomy or current Phase 3 taxonomy → Chat for taxonomy extension.
3. **Reference implementation unstable** (numerical issues, version regression, R/Python upstream bug) → Chat for reference re-selection.
4. **CAL-R6 budget exceeded** with same-class-deferral pattern (≥2 consecutive sessions) → Chat for budget recalibration.
5. **≥3 wrappers in same batch land Tier C unexpectedly** → Chat for scope rebalance.
6. **CI runtime regression** >50% on `parity-fast.yml` → Chat for fast/slow tier rebalance per Section 12.
7. **Cross-wrapper finding pattern** (e.g., shared upstream dependency producing common divergence) → Chat for root-cause investigation.

Without these triggers, "minimal Chat involvement" becomes "Chat involvement at the wrong moments."

---

## 12. CI Tier Classification

### 12.1 Fast vs slow tier

| Tier | Workflow | Trigger | Runtime budget per audit | Membership rule |
|---|---|---|---|---|
| Fast | `parity-fast.yml` | Every push to master | ≤30s | Closed-form, OLS, FFT, small-fixture MLE |
| Slow | `parity-slow.yml` | Nightly schedule + manual dispatch | ≤5min | EM-stochastic, MCMC, ML/DL training, large-fixture MLE |
| Skip-CI | None (local only) | Manual run | N/A | DL training requiring GPU; long-MCMC chains |

### 12.2 Per-batch CI assignment

- Batches 1, 5, 6 (forecast, state space, change-points/stationarity): mostly fast tier.
- Batches 2, 3, 4 (volatility, multivariate, Markov): mixed; deterministic-optimizer fits go fast, EM/MCMC go slow.
- Batch 7 (spectral): all fast (closed-form primitives).
- Batch 8 (ML): mostly fast (deterministic with seed pinning).
- Batch 9 (DL): mostly slow; some skip-CI for GPU-only audits.
- Batch 10 (misc): mixed.

Default: assign to slow tier if uncertain; promote to fast after measured runtime supports it.

### 12.3 Runtime monitoring

`tools/reference_parity/scripts/measure_runtime.py` runs per-audit timing and emits a runtime ledger. CI runtime regression triggers escalation per Section 11 trigger 6.

---

## 13. Reference Version Drift Protocol

### 13.1 Pinning

R packages and Python packages pinned in **`tools/reference_parity/harness/MANIFEST.toml`** — single source of truth for both languages, loaded via `harness/manifest.py` (Python 3.11+ stdlib `tomllib`). The Phase 3 Session 1 inventory established this as the consolidated manifest, superseding the originally-proposed parallel `manifests/r_packages_p3.txt` + `py_packages_p3.txt` plain-text files (rationale in `tools/reference_parity/INVENTORY.md` §4).

The manifest exposes:
- `[r]` block: R version + `rscript_exe` + `libs_user` + `[r.packages]` (package → version).
- `[python]` block: Python version + `[python.packages]` (package → version).
- `[refresh]` block: `last_review` / `next_review` dates + notes; enforced by `Manifest.is_stale()`.
- `[tiers]` block: documentation of fast/slow tier membership.

CI workflows (`parity-fast.yml`, `parity-slow.yml`) install from `install.packages()` / `pip install` lines that should remain version-aligned with `MANIFEST.toml`. `RBridge.check_environment()` (and `python -m reference_parity --check-environment`) reports drift between the actual installed environment and the manifest. Re-pin commits update `MANIFEST.toml` + the corresponding workflow line in one edit.

### 13.2 Drift response

When upstream package update produces divergence outside stated tolerance for a previously-PASS wrapper:

1. **Investigate first** — is the upstream change a bug fix, a methodology change, or a numerical-precision improvement?
2. **Classify:**
   - Upstream bug fix → re-pin to new version, document.
   - Upstream methodology change → either (i) widen tolerance with documented rationale, (ii) maintain old pin and document, (iii) investigate whether TSL's wrapper should adopt the new methodology.
   - Numerical-precision change (e.g., LAPACK update) → typically widen tolerance.
3. **Decide and document** in P-3.

### 13.3 Quarterly re-pin window

Each quarter, re-pin manifest to current upstream stable. Re-run all `PASS` and `CAVEAT` audits; address drift per 13.2.

---

## 14. Out of Scope

Explicit non-scope to prevent leakage:

- **Level 4 production stress testing** (intraday, million-row, regime breaks) — separate future initiative.
- **New wrapper implementations.**
- **Performance benchmarking.**
- **Methodology comparison across implementations** ("is R's GARCH better than TSL's GARCH").
- **Macro fixture expansion** (multi-FX, broader rates, commodities) — flagged Phase 3.5 candidate; uses existing 5-series fixture (GSPC, DGS2, DGS10, DEXUSEU, GOLD) plus per-category synthetic DGP fixtures.
- **Bug fixes for newly-discovered parity divergences outside CAL-R6 budget** — become separate follow-up work, not blocked on Phase 3 closure.
- **Path Q DEXUSEU follow-up** — carry-forward only: at Phase 3 closeout, FX-relevant wrapper findings (GARCH/EGARCH on FX, change-point detectors on FX) reviewed for Path Q implications and documented in P-3. Path Q execution remains separate.

---

## 15. Session-by-Session Plan

### 15.1 Setup phase (Session 1)

**Session 1 — Infrastructure inventory.**

Deliverable: `tools/reference_parity/INVENTORY.md`. Code inspects:

- Actual file inventory under `tools/reference_parity/` (scripts, fixtures, reports).
- `r_bridge.py` status: planned, implemented, vestigial.
- `parity-fast.yml` content, runtime, `parity-slow.yml` if exists.
- R package install step pattern.
- Existing fixture SHA256 pin format.
- Existing audit script structural pattern (target template source for Session 2).

Output drives Session 2 design choices.

### 15.2 Batch 1 — R `forecast` family (Sessions 2–4)

In-scope wrappers (~9): ARIMA / SARIMA / ARIMAX / auto.arima dispatch, ETS, Theta, Croston / SBA / TSB, MSTL, STL, classical decomposition.

- **Session 2:** ARIMA family (3 wrappers) + manual harness pattern locked.
- **Session 3:** ETS + Theta + intermittent demand (5 wrappers).
- **Session 4:** STL + MSTL + classical decomposition + batch summary.

Deliverable per session: per-wrapper audit reports + status tracker update.
Batch close: `p3_batch_1_summary.md`.

### 15.3 Generator abstraction (Session 5)

Per Section 10. Deliverable: `tools/reference_parity/harness/` populated; Batch 1 audits re-run via generator producing bit-identical results.

**Chat check-in 1** after Session 5: pattern review, generator validation, Batch 2 readiness.

### 15.4 Batch 2 — R volatility (Sessions 6–7)

In-scope wrappers (~6): sGARCH, GJR-GARCH, EGARCH, IGARCH, HAR-RV, EVT POT GPD.

- **Session 6:** sGARCH + GJR-GARCH + EGARCH + IGARCH (4 wrappers via rugarch).
- **Session 7:** HAR-RV + EVT POT GPD + batch summary.

### 15.5 Batch 3 — R multivariate (Sessions 8–9)

In-scope wrappers (~6): VAR, BVAR estimation, DFM, PCA, reconciliation OLS, reconciliation WLS.

- **Session 8:** VAR + BVAR estimation + reconciliation OLS/WLS.
- **Session 9:** DFM + PCA + batch summary.

(VECM is partially covered by 3d Johansen; Phase 3 confirms the post-cointegration VECM fit, not the cointegration test.)

### 15.6 Batch 4 — R Markov / nonlinear (Sessions 10–11)

In-scope wrappers (~7): HMM, Markov switching, TAR, SETAR, STAR, NAR/NARX, critical slowing down (CSD).

- **Session 10:** HMM + Markov switching + TAR + SETAR.
- **Session 11:** STAR (Tier B/C likely) + NAR/NARX + CSD (Tier B likely) + batch summary.

### 15.7 Batch 5 — R state space (Session 12)

In-scope wrappers (~4): local level, local linear trend, structural TS, particle filter.

- **Session 12:** all four + batch summary.

### 15.8 Batch 6 — R change-points / stationarity (Sessions 13–14)

In-scope wrappers (~8): ADF, KPSS, PP, BOCPD, CUSUM/Page-Hinkley, intervention analysis, PELT, STL+ESD.

- **Session 13:** ADF + KPSS + PP (closed-form, Tier A, fast tier).
- **Session 14:** BOCPD + CUSUM/PH + intervention + PELT + STL+ESD + batch summary.

**Chat check-in 2** after Session 14: midpoint pattern review (~50% of in-scope wrappers complete).

### 15.9 Batch 7 — Python spectral (Sessions 15–16)

In-scope wrappers (~7): FFT, periodogram, Lomb-Scargle, wavelet transform, wavelet coherence (Tier B), EMD/HHT, SSA.

- **Session 15:** FFT + periodogram + Lomb-Scargle + wavelet transform.
- **Session 16:** wavelet coherence + EMD/HHT + SSA + batch summary.

### 15.10 Batch 8 — Python ML (Sessions 17–18)

In-scope wrappers (~7): random forest, gradient boosting, XGBoost, LightGBM, SVR, quantile regression, robust estimators.

- **Session 17:** RF + GB + XGB + LGB.
- **Session 18:** SVR + quantile regression + robust estimators + batch summary.

### 15.11 Batch 9 — Python DL (Sessions 19–21)

In-scope wrappers (~10): LSTM, GRU, TCN, N-BEATS, N-HiTS, autoencoder, ESN, GP forecast, Prophet, conformal intervals.

Pre-budget assumption: ≥30% Tier C verdicts due to DL non-determinism.

- **Session 19:** LSTM + GRU + TCN.
- **Session 20:** N-BEATS + N-HiTS + autoencoder + ESN.
- **Session 21:** GP forecast + Prophet + conformal intervals + batch summary.

### 15.12 Batch 10 — Misc + Tier C consolidation (Sessions 22–23)

In-scope wrappers (~7): DTW, Granger, CCF (incl. prewhitened, rolling), GCC-PHAT, transfer function, block bootstrap (and family), forecast combination, rolling-origin CV, Denton-Cholette, Kalman imputation, LOESS interpolation.

(Counts cluster slightly differently here; final wrapper assignment finalized at Session 21 close based on running total.)

- **Session 22:** Granger + CCF family + GCC-PHAT + DTW + transfer function.
- **Session 23:** bootstrap family + forecast combination + rolling-origin CV + Denton-Cholette + Kalman imputation + LOESS + Tier C consolidation + batch summary.

**Chat check-in 3** after Session 23: closeout readiness, P-1/P-2/P-3 outline review.

### 15.13 Documentation phase (Sessions 24–26)

- **Session 24:** P-1 (`docs/engineering/parity_standard.md`) drafted and committed.
- **Session 25:** P-2 (`docs/engineering/parity_diagnostic_reference.md`) drafted and committed.
- **Session 26:** P-3 (`docs/engineering/parity_empirical_findings.md`) drafted and committed.

### 15.14 Closeout (Session 27)

- CI workflow extension finalized: `parity-fast.yml` and `parity-slow.yml` covering all PASS + CAVEAT verdicts.
- P-4 status tracker finalized.
- `docs/calibration_audit_status.md` cross-reference updated to point to P-1/P-2/P-3.
- Phase 3 closeout commit.

### 15.15 Total

**27 execution sessions + 3 Chat check-ins.** Within handoff estimate (25–30); generator (Session 5) anticipated to compress total vs CAI Phase 2's 28-session arc despite higher per-wrapper complexity.

Scope-evolution acceptance: master plan accommodates growth to 35 sessions if mid-cycle findings warrant. Per-session-evolution decisions made at Chat check-ins.

---

## 16. Naming Conventions

### 16.1 Findings

- **Phase 3 findings:** `P-{CATEGORY}-{IDENTIFIER}` (e.g., `P-GARCH-EGARCH-COEF-DIVERGE`, `P-DFM-EM-CONVERGENCE`).
- **Categories** match wrapper-category prefix used in CAI (extended where new categories appear).
- Findings cross-referenced in P-2 Appendix A (parallel to CAI's C-2 Appendix A).

### 16.2 Audit scripts

- **Phase 3 audit scripts:** `tools/reference_parity/scripts/audit_p3_<wrapper>.py`.
- Distinguishes from existing `audit_1a_*.py` through `audit_3f_*.py` Verification Initiative scripts.

### 16.3 Audit reports

- **Per-wrapper:** `tools/reference_parity/reports/p3_<wrapper>_audit.md`.
- **Per-batch:** `tools/reference_parity/reports/p3_batch_<N>_summary.md`.

### 16.4 Fixtures

- **DGP-recovery fixtures:** `tools/reference_parity/fixtures/p3_dgp_<wrapper>.npz` (SHA256 pinned).
- **Existing fixtures reused:** referenced by name; not duplicated.

### 16.5 Configs (post-Session 5)

- **Generator configs:** `tools/reference_parity/configs/p3_<wrapper>.toml`.

---

## 17. Risks and Scope Evolution

### 17.1 Risks

1. **R-subprocess pattern doesn't scale to ML/DL.** Existing infra is R-bridge oriented; Batches 7–9 are Python-native. Session 1 inventory must surface whether existing pattern handles Python-reference audits or a parallel pattern is needed. If parallel: Session 5 generator scope expands accordingly.
2. **DL parity is fragile.** Hardware (CUDA vs CPU, cuDNN version) and PyTorch version drift cause non-deterministic outputs even with seed pinning. Pre-budgeted as ≥30% Tier C verdicts in Batch 9. If actual >50%, escalation per Section 11 trigger 5.
3. **Per-wrapper complexity exceeds CAI baseline.** Reference parity is per-wrapper more expensive than input validation. 35–40 sessions is the upside scope. Master plan accepts this; Chat check-ins gate scope expansion.
4. **Reference-implementation regressions.** Upstream R/Python packages may regress between master plan commit and Phase 3 closeout. Section 13 protocol applies.
5. **Wrapper inventory uncertainty.** Handoff cites "~71 remaining wrappers" but enumeration in Appendix A may differ ±3 once Session 1 inventory finalizes the actual wrapper-coverage delta vs existing 12 audits.

### 17.2 Scope evolution protocol

Scope changes at Chat check-ins, not within sessions. Within-session scope drift is forbidden; out-of-scope discoveries are documented in batch summary and queued for next Chat check-in.

---

## 18. Communication Style (Carry-Forward)

User preferences (carried from CAI):

- Direct, quantitative, honest uncertainty bounds.
- No hedging unless materially uncertain.
- Structured framing for strategic decisions (diagnose → frame → advance → stress-test → synthesize).
- Avoid generic disclaimers and corporate filler.

Memory / editor instructions (carried from CAI):

- Never use the name "Molly" or "Molly Nickolin" in any output. Refer to the desk-head editor of the Global Macro Commentary product as "the desk-head editor" or "the primary editorial reviewer".
- When drafting prompts intended for Claude Code, prepend "Plan mode: on" or "Plan mode: off" line at the top.

---

## Appendix A: In-Scope Wrapper Inventory

**FINALIZED at Phase 3 Session 1** against actual `engine/techniques/*.py` filesystem inventory.
See `tools/reference_parity/INVENTORY.md` §6 for the reconciliation method and adjustment ledger.

Total in-scope: **70 audit deliverables** = 69 unaudited wrappers + 1 harness promotion (`tbats_forecast.py` — Phase 1 audit-script exists but never promoted to harness).

### Batch 1 — R `forecast` family (10)
1. `arima.py`
2. `arimax_sarimax.py`
3. `sarima.py`
4. `ets_hw.py` (= "ets_forecast" in master plan §6.1)
5. `theta_forecast.py`
6. `intermittent_demand.py` (covers Croston / SBA / TSB variants)
7. `mstl_decompose.py`
8. `classical_decompose.py`
9. `stl_decompose.py`
10. `tbats_forecast.py` (harness promotion — Phase 1 audit-script `audit_1b_tbats.py` produced tolerance ladder; Phase 3 writes `harness/checks/tbats_forecast.py` from scratch using that ladder as baseline)

### Batch 2 — R volatility (2)
1. `garch_model.py` (single wrapper covers sGARCH / GJR-GARCH / EGARCH / IGARCH via `vol` param dispatch — verified per CAI Session 6 finding)
2. `har_rv.py`

(`evt_pot_gpd.py` already covered by Verification Initiative 3c; not in Phase 3 scope.)

### Batch 3 — R multivariate (4)
1. `var_model.py`
2. `vecm_model.py` (post-cointegration fit; cointegration test already covered by 3d)
3. `dynamic_factor_model.py`
4. `pca_analysis.py`

(`bvar.py` already covered by 1c; `forecast_reconciliation.py` already covered by 3e for ALL 4 methods including ols/wls_variance — not in Phase 3 scope.)

### Batch 4 — R Markov / nonlinear (5)
1. `hmm_model.py`
2. `markov_switching.py`
3. `tar_setar.py`
4. `star_model.py` (Tier B/C — STAR with custom transitions)
5. `nar_narx.py`

(`critical_slowing_down.py` already covered by harness check from Phase 2 cleanup.)

### Batch 5 — R state space (5)
1. `local_level.py`
2. `local_linear_trend.py`
3. `structural_ts.py`
4. `particle_filter.py` (reference may need to be Python `particles` rather than R `pomp` due to Windows CI install constraints — decide at Batch 5 start)
5. `kalman_imputation.py` (moved from Batch 10 — uses same KFAS reference as 2a)

### Batch 6 — R change-points / stationarity (9)
1. `adf_test.py`
2. `kpss_test.py`
3. `pp_test.py`
4. `bocpd.py`
5. `cusum_page_hinkley.py`
6. `intervention_analysis.py`
7. `pelt_change_points.py`
8. `stl_esd_anomaly.py`
9. `x13_seasonal_adjust.py` (R `seasonal` package — wraps X-13ARIMA-SEATS binary)

### Batch 7 — Python spectral (7)
1. `fft_spectrum.py`
2. `periodogram_spectral_density.py`
3. `lomb_scargle.py`
4. `wavelet_transform.py` (DWT + MODWT)
5. `wavelet_coherence.py` (Tier B — custom phase-lag)
6. `emd_hht.py`
7. `ssa_model.py`

### Batch 8 — Python ML (7)
1. `random_forest_forecast.py`
2. `gradient_boosting_forecast.py`
3. `xgboost_forecast.py`
4. `lightgbm_forecast.py`
5. `svr_forecast.py`
6. `quantile_regression_model.py`
7. `robust_estimators.py`

### Batch 9 — Python DL (9)
1. `lstm_gru_forecast.py` (single wrapper, 2 variants — LSTM and GRU)
2. `tcn_forecast.py`
3. `nbeats_forecast.py`
4. `nhits_forecast.py`
5. `autoencoder_anomaly.py`
6. `echo_state_network.py` (= "esn_forecast" in master plan §6.1)
7. `gaussian_process_forecast.py` (= "gp_forecast" in master plan §6.1)
8. `prophet_forecast.py`
9. `conformal_intervals.py`

(`transformer_forecast.py` attention-capture path already covered by 3f; the forecast-output path is uncovered but treated as a derivative of the LSTM/GRU/TCN audit-pattern — slot under Batch 9 if scope-bandwidth permits, else defer to Phase 3.5.)

### Batch 10 — Misc + Tier C consolidation (12)
1. `granger_causality.py`
2. `cross_correlation_lag.py` (CCF family)
3. `prewhitened_ccf_lag.py` (CCF family)
4. `rolling_ccf_lag.py` (CCF family)
5. `gcc_phat_delay.py`
6. `dtw_alignment_lag.py`
7. `transfer_function.py`
8. `block_bootstrap.py` (covers block / MBB / stationary variants via params)
9. `forecast_combination.py`
10. `rolling_origin_cv.py`
11. `denton_chowlin_disaggregation.py`
12. `loess_interpolation.py`

### Inventory total
**70 audit deliverables** finalized at Session 1 (69 unaudited wrappers + 1 harness promotion of tbats_forecast).

---

## Appendix B: Reference Package Pin Manifest

**Manifest source of truth:** `tools/reference_parity/harness/MANIFEST.toml` (TOML, loaded via `harness/manifest.py`). The non-existent paths originally referenced by Section 13.1 (`tools/reference_parity/manifests/r_packages_p3.txt` and `py_packages_p3.txt`) are **superseded by `harness/MANIFEST.toml`** — single source of truth, typed loader, runtime divergence report, quarterly cadence enforcement. See `tools/reference_parity/INVENTORY.md` §4 for rationale.

Update protocol per Section 13. Quarterly review next due **2026-07-25** (`refresh.next_review` field of `MANIFEST.toml`).

### Pin classification

- **PINNED** — version verified installed locally as of Session 1 (2026-04-28); already in or being added to `harness/MANIFEST.toml`.
- **TBD-batch-N** — not yet installed; recommended action is to install at start of batch N before first audit, pin to whatever CRAN/PyPI serves, and append to `MANIFEST.toml` `[r.packages]` / `[python.packages]` table at the same time. Quarterly re-pin then reconciles to canonical version.

### R packages — R 4.5.3 (rscript_exe `C:/Program Files/R/R-4.5.3/bin/Rscript.exe`)

| Package | Pinned version | Used by batch | Status |
|---|---|---|---|
| `forecast` | 9.0.2 | 1, 10 | PINNED |
| `fable` | 0.5.0 | 1 (cross-check) | PINNED |
| `fabletools` | 0.6.1 | 1 (cross-check) | PINNED |
| `tsintermittent` | TBD-batch-1 | 1 | TBD-batch-1 |
| `rugarch` | 1.5.5 | 2 | PINNED |
| `HARModel` | TBD-batch-2 | 2 (har_rv); see INVENTORY §8 — Windows-CI install non-trivial; may use from-scratch reimpl per existing `har_cj.py` check | TBD-batch-2 |
| `evd` | TBD-batch-2 | 2 | TBD-batch-2 |
| `extRemes` | 2.2.1 | 2 (same as 3c) | PINNED |
| `vars` | 1.6.1 | 3 | PINNED |
| `urca` | 1.3.4 | 3, 6 (same as 3d) | PINNED |
| `BVAR` | TBD-batch-3 | 3 (BVAR estimation — distinct from 1c which audits IRF/FEVD given coefs) | TBD-batch-3 |
| `MARSS` | TBD-batch-3 | 3 (DFM) | TBD-batch-3 |
| `hts` | 6.0.3 | 3 (same as 3e; already covered for OLS/WLS) | PINNED |
| `KFAS` | 1.6.0 | 5 (same as 2a) | PINNED |
| `dlm` | 1.1.6.1 | 5 (same as 2a) | PINNED |
| `pomp` | TBD-batch-5 | 5 (particle filter); see INVENTORY §8 — install non-trivial; may swap to Python `particles` | TBD-batch-5 |
| `depmixS4` | TBD-batch-4 | 4 (HMM) | TBD-batch-4 |
| `MSwM` | TBD-batch-4 | 4 (Markov switching) | TBD-batch-4 |
| `tsDyn` | TBD-batch-4 | 4 (TAR / SETAR / STAR / NAR-NARX) | TBD-batch-4 |
| `tseries` | 0.10.61 | 6 (ADF / KPSS / PP cross-check) | PINNED |
| `changepoint` | TBD-batch-6 | 6 (PELT) | TBD-batch-6 |
| `cpm` | TBD-batch-6 | 6 (CUSUM / Page-Hinkley) | TBD-batch-6 |
| `TSA` | TBD-batch-6 | 6, 10 (intervention / transfer function) | TBD-batch-6 |
| `seasonal` | TBD-batch-6 | 6 (X-13ARIMA-SEATS binary wrapper) | TBD-batch-6 |
| `lmtest` | 0.9.40 | 10 (Granger) | PINNED |
| `dtw` | TBD-batch-10 | 10 (DTW Giorgino) | TBD-batch-10 |
| `boot` | 1.3.32 | 10 (block bootstrap) | PINNED |
| `forecastHybrid` | TBD-batch-10 | 10 (forecast combination) | TBD-batch-10 |
| `robustbase` | TBD-batch-8 | 8 (robust estimators) | TBD-batch-8 |
| `tempdisagg` | TBD-batch-10 | 10 (Denton-Cholette) | TBD-batch-10 |
| `quantreg` | 6.1 | 8 (cross-check) | PINNED |
| `waveslim` | TBD-batch-7 | 7 (DWT / MODWT R-side; Python `pywt` is primary) | TBD-batch-7 |
| `biwavelet` | TBD-batch-7 | 7 (wavelet coherence; Tier B custom phase-lag → audit may settle without R reference) | TBD-batch-7 |
| `Rssa` | TBD-batch-7 | 7 (SSA cross-check; Python `pyts` is primary) | TBD-batch-7 |
| `evir` | 1.7.4 | (already covered by 3c; not in Phase 3 scope but pinned as inheritance) | PINNED |
| `POT` | 1.1.11 | (already covered by 3c) | PINNED |
| `stochvol` | 3.2.9 | (already covered by 2b/2c) | PINNED |

### Python packages — Python 3.14

| Package | Pinned version | Used by batch | Status |
|---|---|---|---|
| `numpy` | 2.4.4 | universal | PINNED |
| `scipy` | 1.17.1 | 7 (FFT / Lomb-Scargle / periodogram) | PINNED |
| `pandas` | 2.3.3 | universal | PINNED |
| `arch` | 8.0.0 | 2 (cross-check) | PINNED |
| `statsmodels` | 0.14.6 | 3 (DFM cross-check), 8 (quantile regression cross-check) | PINNED |
| `pmdarima` | 2.1.1 | 1 (auto.arima cross-check if used) | PINNED |
| `tbats` | 1.1.3 | 1 (same library TSL wraps; sanity-only cross-check) | PINNED |
| `pyextremes` | 2.5.0 | 2 (already inherited from 3c) | PINNED |
| `hierarchicalforecast` | 1.5.1 | 3 (already inherited from 3e) | PINNED |
| `pymc` | 5.28.4 | (inherited from 2b/2c) | PINNED |
| `arviz` | 0.23.4 | (inherited from 2b/2c) | PINNED |
| `torch` | 2.11.0+cpu | 9 (DL); inherited from 3f | PINNED |
| `ewstools` | 2.1.2 | (inherited from CSD harness check) | PINNED |
| `scikit-learn` | 1.8.0 | 8 (RF / GB / SVR primary) | PINNED |
| `xgboost` | 3.2.0 | 8 (XGBoost primary) | PINNED |
| `lightgbm` | TBD-batch-8 | 8 (LightGBM primary) | TBD-batch-8 |
| `prophet` | 1.3.0 | 9 (Prophet primary) | PINNED |
| `reservoirpy` | 0.4.1 | 9 (ESN primary) | PINNED |
| `hmmlearn` | 0.3.3 | 4 (HMM cross-check) | PINNED |
| `ruptures` | 1.1.9 | 6 (PELT cross-check; CUSUM cross-check) | PINNED |
| `EMD-signal` | 1.9.0 | 7 (EMD/HHT primary; PyPI name `EMD-signal`, import name `PyEMD`) | PINNED |
| `PyWavelets` | 1.9.0 | 7 (DWT/MODWT primary; PyPI name `PyWavelets`, import name `pywt`) | PINNED |
| `astropy` | TBD-batch-7 | 7 (Lomb-Scargle primary if scipy doesn't suffice) | TBD-batch-7 |
| `pyts` | TBD-batch-7 | 7 (SSA primary) | TBD-batch-7 |
| `bocd` | TBD-batch-6 | 6 (BOCPD primary) | TBD-batch-6 |
| `dtaidistance` | TBD-batch-10 | 10 (DTW cross-check) | TBD-batch-10 |
| `MAPIE` | TBD-batch-9 | 9 (conformal intervals primary; PyPI name `mapie`) | TBD-batch-9 |
| `nonconformist` | TBD-batch-9 | 9 (conformal cross-check) | TBD-batch-9 |
| `neuralforecast` | TBD-batch-9 | 9 (N-BEATS / N-HiTS primary) | TBD-batch-9 |
| `gpytorch` | TBD-batch-9 | 9 (GP forecast primary) | TBD-batch-9 |
| `particles` | TBD-batch-5 | 5 (particle filter cross-check or primary if `pomp` not installed) | TBD-batch-5 |

**Summary:** 28 packages PINNED at Session 1 (all installed and verified); 23 packages flagged TBD with batch-targeted install rationale. Each TBD entry resolves at the batch's first session, when `pip install <pkg>` / `install.packages("<pkg>")` runs against the local + CI environment and the resulting version is appended to `harness/MANIFEST.toml`.

**Quarterly cadence:** when `refresh.next_review` (currently 2026-07-25) elapses, all PINNED versions are re-checked; any drift is reconciled per Section 13.2. TBD entries remain TBD until their batch begins.

---

## Appendix C: Phase 3 Closeout Deliverables Specification

### P-1 — `docs/engineering/parity_standard.md`

Structure:
1. Purpose and scope.
2. Four-verdict closure rule (binding).
3. Output-surface discipline (binding).
4. Reference availability tier policy (binding).
5. Tolerance bands per class (binding).
6. CI tier classification (binding).
7. Reference-version pinning protocol (binding).
8. Pre-merge checklist for new wrappers — parity dimension (binding).
9. Cross-reference to wrapper development standard (C-1).

### P-2 — `docs/engineering/parity_diagnostic_reference.md`

Structure:
1. Purpose.
2. Per-divergence-class diagnostic patterns.
3. Methodology-equivalent vs bug-suspected vs numerical-precision-artifact heuristics.
4. R-subprocess invocation patterns (with examples).
5. Python-import invocation patterns (with examples).
6. Generator usage guide (post-Session 5 harness).
7. Tolerance class assignment heuristics.
8. Empirical examples per finding.
9. **Appendix A:** per-finding cross-reference index of all Phase 3 findings (`P-*` IDs).

### P-3 — `docs/engineering/parity_empirical_findings.md`

Structure:
1. Cycle statistics (sessions, wrappers, findings, distribution).
2. Methodology evolution narrative.
3. Per-batch summaries.
4. Cross-method empirical artifacts (cross-batch findings, shared-dependency divergences).
5. Validated principles (parallel to CAI's 10 engineering principles).
6. Path Q implications for FX-relevant wrappers (carry-forward note).
7. Lessons learned for any Phase 4 (production stress) work.
8. Recommendations for Phase 3.5 (fixture expansion) if scope warrants.

### P-4 — `docs/reference_parity_status.md`

Per-wrapper status tracker. Columns: wrapper, batch, reference primary, reference cross-check, tolerance class, output tier mapping, fixtures used, verdict, audit report path, audit script path, finding IDs.

---

**End of Phase 3 master plan.**
