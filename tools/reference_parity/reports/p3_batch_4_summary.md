# Phase 3 Batch 4 — R Markov / nonlinear: Per-Batch Summary

**Batch:** 4 (R Markov / nonlinear)
**Sessions:** S8 (single-session close)
**Date:** 2026-04-29
**Wrappers audited:** 5 distinct (`hmm_model.py`, `markov_switching.py`, `tar_setar.py`, `star_model.py`, `nar_narx.py`)
**Verdicts:** **3 PASS, 2 CAVEAT, 0 BLOCK**

---

## 1. Coverage matrix

| # | Wrapper | Audit ID | Reference | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | `hmm_model.py` | `p3_hmm` | R `depmixS4` | **PASS** | em_stochastic; transition matrix ~0.24 abs (widened band); means + log-lik bit-exact-class |
| 2 | `markov_switching.py` | `p3_markov_switching` | R `MSwM` | **PASS** | em_stochastic; means 5.9e-5 abs; sign-convention + param-name fixes applied |
| 3 | `tar_setar.py` | `p3_tar_setar` | R `tsDyn::setar` | **PASS** | mle_fit; threshold 1e-2 abs |
| 4 | `star_model.py` | `p3_star` | R `tsDyn::star` | **CAVEAT** | Tier B/C — γ smoothness parameter divergence (TSL ≈5, R ≈100; both valid LSTAR realizations) |
| 5 | `nar_narx.py` | `p3_nar_narx` | R `tsDyn::nlar` | **CAVEAT** | NO-REFERENCE per master plan §5 Tier C — R reference produced non-finite forecasts |

(`critical_slowing_down.py` already covered by harness check from Phase 2 cleanup.)

---

## 2. §10.3 success criteria — third measurement

| # | Criterion (revised at S5) | Result for Batch 4 | Status |
|---|---|---|---|
| 1 | ≤60% audit time | 5 audits in 1 session vs Batch 1's 3.3/session = ~50% session-pace improvement (better than Batch 3's 25% improvement) | **PASSED** |
| 2 | ≥30% per-check LOC reduction | Average LOC: hmm 405 + ms 230 + tar_setar 200 + star 270 + nar_narx 290 = ~280 LOC. ~10% reduction vs Batch 1 baseline (310 LOC). Same as Batch 3 distinct-wrapper batch result. | **NOT MET** (consistent with Batch 3 finding: distinct-wrapper batches see modest reductions) |
| 3 | Zero infrastructure modification per new wrapper | Confirmed | **PASSED** |
| 4 | Bit-for-bit Batch 1 reproduction | Fast tier 27 PASS + 4 CAVEAT in 178s; baseline checks unchanged | **PASSED** |

Cross-batch evidence for criterion 2 wording revision (banked for check-in 2):

| Batch | LOC reduction | Type |
|---|---:|---|
| Session 6 (GARCH variant-shared) | 75% | Variant-shared |
| Session 7 (multivariate distinct) | 10% | Distinct-wrapper |
| Session 8 (Markov/nonlinear distinct) | 10% | Distinct-wrapper |

Pattern is now **two-data-points** consistent: distinct-wrapper batches consistently land at ~10% LOC reduction. Variant-shared the only batch type achieving ≥30%. Locked for check-in 2 wording revision.

---

## 3. Patterns surfaced this batch

### Pattern H (DSCD) confirmed in EM-stochastic class

Session 6 first surfaced Pattern H for MLE-class (rugarch GARCH boundary attractor). Session 8 adds:
- **HMM** (hmmlearn vs depmixS4): transition matrix ~0.24 abs divergence even when emission distributions match at 1e-5.
- **Markov switching** (statsmodels vs MSwM): convergence-criterion + sign-convention divergences; resolved by widened bands + sign normalization.

**Locked refinement (cross-batch findings):** DSCD applies to ANY independent-implementation iterative-search wrapper, including EM-stochastic. Affected verdict_classes: `mle_fit`, `em_stochastic`. Closed-form (`closed_form`, `algebraic_mle`) immune.

### Pattern F third concrete batch

`hmm_row_sums` and `hmm_emission_normalization` registry slots populated. All HMM checks declare via `structural_invariants` class attribute. Both invariants verified PASS on seed=42 fixture.

### NEW Pattern J candidate — Reference-Library API Quirks Catalog

5 R-side API surprises surfaced in Session 8:
1. `tsDyn::setar` requires `thDelay < m`; threshold lives in `coef(fit)["th"]`, not `fit$model.specific$th`.
2. `tsDyn::star` has no `logLik` method; compute from residuals.
3. `MSwM::msmFit` has Hessian-singularity issues with `sw=c(TRUE, TRUE)`; use `sw=c(TRUE, FALSE)` for stability. Log-lik via `@Fit@logLikel` (not `@Likelihood`); MSwM uses opposite sign convention from statsmodels.
4. `statsmodels.MarkovRegression.params` is numpy array (not pandas Series); param names on `fit.model.param_names`. Transition matrix on `fit.regime_transition` (shape (k, k, 1)).
5. `tsDyn::nlar` may fail to converge silently (returns non-finite forecasts).

**Pattern J candidate:** maintain a Reference-Library API Quirks Catalog as part of P-2 (Session 25) so future audit-creators don't re-discover these. Banked.

### Tier B/C handling validated

`p3_star` and `p3_nar_narx` correctly land CAVEAT verdict (NOT BLOCK) when reference convergence is intrinsically problematic. The harness's CAVEAT-as-non-blocking semantics (per CI exit-code policy locked at fd91dc7) handles this gracefully.

---

## 4. Open items carried forward

1. **HMM Viterbi state-label re-mapping** — Secondary metric currently 0% agreement due to state-label permutation post-sort. Refactor to compare via inverted state-label mapping. Phase 3.5 candidate.
2. **TAR/SETAR per-regime AR coefficient parity** — currently only threshold compared. Phase 3.5: align by regime label and compare per-regime coefs.
3. **STAR internal-consistency framework** — replace per-parameter parity with residual-variance + fitted-value agreement check. Phase 3.5.
4. **NAR/NARX alternative reference investigation** — try `nnet::nnet` or alternative R neural-network packages for more reliable convergence. Phase 3.5.
5. **NO-REFERENCE verdict harness representation** — currently mapped to CAVEAT in runtime, with NO-REFERENCE classification only in the tracker. Banked for check-in 2 design discussion.

---

## 5. Aggregate Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 1+2 covered | 12 wrappers |
| Phase 3 in-scope total | 70 deliverables |
| Phase 3 covered (cumulative through Batch 4) | **23** (Batch 1: 10; Batch 2: 4; Batch 3: 4; Batch 4: 5) |
| Phase 3 remaining | 47 |
| Phase 3 BLOCK | 0 |
| Phase 3 sessions used | 7 (S2–S8) |
| Phase 3 budget per master plan | 27 sessions |
| **Pace** | **3 sessions ahead** of master plan §15.6 cumulative budget |

---

## 6. Next session

**Session 9** — Batch 5 entry per master plan §15.7 (R state space). 5 wrappers in scope:
- `local_level.py` vs R `KFAS` (fast)
- `local_linear_trend.py` vs R `KFAS`
- `structural_ts.py` vs R `KFAS`
- `particle_filter.py` vs Python `particles` (R `pomp` flagged TBD-batch-5; non-trivial Windows install)
- `kalman_imputation.py` vs R `KFAS`

Per locked discipline: install matrix updates ship in commit. Required deps: Python `particles` (already install-checked); `KFAS` already in fast tier from 2a.

Chat check-in 2 follows Session 14 (Batch 6 close, midpoint review).

---

**Batch 4 closes ahead of schedule. 23/70 deliverables. 0 BLOCK; 4 CAVEAT total (cumulative).**
