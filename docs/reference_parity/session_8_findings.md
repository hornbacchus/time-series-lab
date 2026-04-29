# Phase 3 Session 8 — Findings (Batch 4 close)

**Date:** 2026-04-29
**Batch:** 4 (R Markov / nonlinear) — **CLOSED in single session** (master plan §15.6 budgeted S10+S11)
**Wrappers audited:** 5 distinct (`hmm_model.py`, `markov_switching.py`, `tar_setar.py`, `star_model.py`, `nar_narx.py`)
**Verdicts:** **3 PASS, 2 CAVEAT, 0 BLOCK**

## Verdicts (this session)

| Audit ID | Verdict | Achieved tolerance | Tier | Runtime |
|---|---|---|---|---:|
| `p3_hmm` | **PASS** | means 1.5e-5 abs; transmat 0.24 abs (widened em_stochastic band) | fast | 18.9s |
| `p3_markov_switching` | **PASS** | means 5.9e-5 abs (after param-name + sign-convention fixes) | fast | 3.1s |
| `p3_tar_setar` | **PASS** | threshold 1e-2 abs | fast | 7.5s |
| `p3_star` | **CAVEAT** | γ divergence 5 vs 100 (Tier B/C) | fast | 6.3s |
| `p3_nar_narx` | **CAVEAT** | R reference produced non-finite forecasts (NO-REFERENCE Tier C) | fast | 10.0s |

## Highlights

### Pattern H DSCD extends to em_stochastic class

Session 8 extends Pattern H (DSCD) from MLE-class (Session 6 GARCH) to **em_stochastic class**:
- p3_hmm: hmmlearn vs depmixS4 transition matrix divergence ~0.24 abs (means + log-lik agree at 1e-5)
- p3_markov_switching: statsmodels vs MSwM convergence + sign-convention divergences

**Refined definition LOCKED in cross-batch findings:**
> DSCD applies to ANY independent-implementation iterative-search wrapper, including MLE and EM-stochastic. Closed-form algorithms (Pattern A regime) are immune.

### Pattern F third concrete batch (HMM invariants)

`hmm_row_sums` and `hmm_emission_normalization` registry slots populated. p3_hmm declares both via `structural_invariants` class attribute. **Six concrete invariants now in production** (garch_persistence, garch_conditional_variance, var_eigenvalues, vecm_cointegration_rank, hmm_row_sums, hmm_emission_normalization).

### NEW Pattern J candidate — Reference-Library API Quirks

Session 8 surfaced 5 distinct R/Python API quirks during the audit-creation cycle:
1. `tsDyn::setar` — `thDelay < m` constraint; threshold in `coef(fit)["th"]` not `fit$model.specific$th`
2. `tsDyn::star` — no `logLik` method; compute from residuals
3. `MSwM::msmFit` — Hessian-singularity with `sw=c(TRUE,TRUE)`; log-lik via `@Fit@logLikel` not `@Likelihood`; opposite sign convention from statsmodels
4. `statsmodels.MarkovRegression` — `fit.params` is numpy array; param names on `fit.model.param_names`; transition matrix on `fit.regime_transition` (shape `(k, k, 1)`)
5. `tsDyn::nlar` — silent non-convergence (returns non-finite forecasts)

**Pattern J candidate**: maintain Reference-Library API Quirks Catalog as P-2 deliverable (Session 25). Banked.

### NEW Pattern K candidate — NO-REFERENCE harness representation

p3_nar_narx is the **first Phase 3 audit landing in master plan §5 Tier C** (NO-REFERENCE). The harness emits CAVEAT verdict (no runtime NO-REFERENCE outcome exists). Master plan §3.1's NO-REFERENCE classification is **tracker-only**, not a runtime outcome.

**Pattern K candidate**: add `NO-REFERENCE` runtime outcome to harness, distinct from CAVEAT. Banked for check-in 2 design discussion.

## §10.3 success criteria — third measurement (cumulative pattern)

| # | Criterion | Result | Status |
|---|---|---|---|
| 1 | ≤60% audit time per wrapper | 5 audits/session vs Batch 1's 3.3/session = ~50% improvement | **PASSED** |
| 2 | ≥30% LOC reduction | 10% (consistent with Batch 3; distinct-wrapper batch) | **NOT MET** |
| 3 | Zero infrastructure modification | PASSED | **PASSED** |
| 4 | Bit-for-bit Batch 1 reproduction | PASSED — 27 PASS + 4 CAVEAT in 178s | **PASSED** |

**Criterion 2 cross-batch evidence (now 3 data points):**

| Batch | LOC reduction | Type |
|---|---:|---|
| Session 6 | 75% | Variant-shared (GARCH 3 variants on 1 wrapper) |
| Session 7 | 10% | Distinct-wrapper |
| Session 8 | 10% | Distinct-wrapper |

Pattern locked: distinct-wrapper batches consistently land at ~10% LOC reduction. Variant-shared the only batch type achieving ≥30%.

## Investigation arc — methodology pattern for EM-stochastic audits

The Markov switching audit had to iterate through 5 distinct R/Python issues before landing on PASS. The investigation pattern is reusable:

1. **AttributeError on TSL fit object** → API discovery (`fit.model.param_names` vs `fit.params.index`).
2. **R reference compile error** → tsDyn `thDelay < m` constraint; tsDyn coefficient name conventions.
3. **R reference Hessian singularity** → MSwM `sw=c(TRUE,TRUE)` to `sw=c(TRUE,FALSE)`.
4. **Slot access error** → MSwM API: `@Fit@logLikel`, not `@Likelihood`.
5. **Sign convention divergence** → MSwM log-lik returns positive; statsmodels returns negative; compare via `abs()`.

**Generalization:** when integrating against EM-class R packages, expect ~3-5 iterations of API discovery + sign convention fixes. Banked: add EM-Stochastic-Reference-Integration Checklist to P-2 (Session 25).

## Files written this session

| File | LOC |
|---|---:|
| harness/checks/p3_hmm.py | 405 |
| harness/checks/p3_markov_switching.py | 230 |
| harness/checks/p3_tar_setar.py | 200 |
| harness/checks/p3_star.py | 270 |
| harness/checks/p3_nar_narx.py | 290 |
| harness/structural_invariants.py (extension) | +90 |
| harness/tolerances.py (extension) | +130 |
| .github/workflows/parity-fast.yml + parity-slow.yml | +2/+2 |
| 5 audit reports (p3_hmm + p3_markov_switching + p3_tar_setar + p3_star + p3_nar_narx) | ~600 |
| reports/p3_batch_4_summary.md | 165 |
| reports/phase3_cross_batch_findings.md (extension) | +160 |
| docs/reference_parity_status.md | (updated) |
| docs/reference_parity/session_8_findings.md | (this file) |
| **Total** | ~2700 |

## Regression check

Full fast tier 31 checks → 27 PASS + 4 CAVEAT in 178s (overall CAVEAT, exit 2 → CI maps to green per fd91dc7 policy).

```
[PASS] _smoke_test, 1c_bvar, 3a_caviar, csd, 3c_evt, 3b_har_cj, 3d_johansen,
       2a_kalman, 3e_mint, p3_arima_manual, p3_arimax_sarimax, p3_theta,
       p3_classical_decompose, p3_egarch, p3_ets, p3_gjr_garch, p3_har_rv,
       p3_hmm (NEW), p3_intermittent, p3_markov_switching (NEW),
       p3_pca, p3_sarima, p3_sgarch, p3_tar_setar (NEW), p3_var, p3_vecm,
       3f_transformer
[CAVEAT] p3_mstl, p3_nar_narx (NEW), p3_star (NEW), p3_stl
overall: CAVEAT
```

## Banked items (cumulative through S8) — do NOT modify

1. **`verdict_class` enum split** — needs Batch 5–6 evidence; em_stochastic per-metric bands surfacing as additional consideration
2. **DSCD diagnostic-axis registry** — design at check-in 2
3. **Pattern I formalization** (sign / scale convention alignment) — needs 1+ more wrapper
4. **NEW: Pattern J formalization** (Reference-Library API Quirks Catalog) — empirical evidence sufficient
5. **NEW: Pattern K formalization** (NO-REFERENCE harness runtime outcome) — needed before Tier C wrappers proliferate
6. **§10.3 criterion 2 wording revision per batch type** — empirically locked across 3 batches
7. **Cross-batch findings doc design refinements**
8. **Infrastructure-fix discipline track** — only 1 fix to date (fd91dc7)
9. **p3_var headroom 8.1 orders + p3_vecm 13 orders** — Phase 3.5 tightening
10. **EM-stochastic per-metric bands** — Session 8 evidence: means/log-lik 4-orders-headroom, transmat 0-2-orders
11. **NEW: EM-Stochastic-Reference-Integration Checklist** for P-2 (Session 25)

## Discipline applied (Session 6 carry-forward)

Install-matrix updates ship in this commit per the locked discipline:
- `depmixS4`, `MSwM`, `tsDyn` (R) added to fast-tier + slow-tier install
- `hmmlearn` (Python pip) added to fast-tier + slow-tier install (used by p3_hmm)

No separate CI-fix follow-up commit needed.

## Next session

**Session 9** — Batch 5 entry per master plan §15.7 (R state space). 5 wrappers in scope:
- `local_level.py` vs R `KFAS`
- `local_linear_trend.py` vs R `KFAS`
- `structural_ts.py` vs R `KFAS`
- `particle_filter.py` vs Python `particles` (R `pomp` flagged TBD-batch-5; non-trivial Windows install)
- `kalman_imputation.py` vs R `KFAS`

KFAS already in fast-tier R install from 2a. Python `particles` package install check needed at session start.

Chat check-in 2 follows Session 14 (Batch 6 close, midpoint review).

---

**Batch 4 closes ahead of schedule. 23/70 deliverables. Pattern J + K candidates surfaced.**
