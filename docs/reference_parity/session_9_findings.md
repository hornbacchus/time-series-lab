# Phase 3 Session 9 — Findings (Batch 5 close)

**Date:** 2026-04-29
**Batch:** 5 (R state space) — **CLOSED in single session** (master plan §15.7 budgeted S12)
**Wrappers audited:** 5 distinct
**Verdicts:** **5 PASS, 0 CAVEAT, 0 BLOCK**

## Verdicts

| Audit ID | Verdict | Notes |
|---|---|---|
| `p3_local_level` | **PASS** | mle_fit Kalman; smoothed state at MLE-class precision |
| `p3_local_linear_trend` | **PASS** (widened band) | LLT 3-variance identifiability — Pattern H DSCD instance for state-space class |
| `p3_structural_ts` | **PASS** | 4-variance multi-component model |
| `p3_particle_filter` | **PASS** | em_stochastic; SMC filtered-mean correlation |
| `p3_kalman_imputation` | **PASS** | KFAS smoother imputation at NA positions |

## Highlights

### Pattern A growing — 11 wrappers

`p3_local_level` and `p3_kalman_imputation` join Pattern A bit-exact regime when KFAS+statsmodels variance estimates align. Pattern A = 11 confirmed wrappers across 5 batches.

### Pattern H DSCD extends to LLT identifiability

`p3_local_linear_trend` is a fundamentally weak identifiability case — statsmodels drives `sigma_eta → 0.51` while KFAS drives `sigma_eta → 1e-4` (with corresponding flip in `sigma_zeta`). Both are valid local optima of the same 3-variance Kalman likelihood.

**Refined Pattern H taxonomy (locked S9):**
- DSCD-MLE (rugarch GARCH boundary attractor — S6)
- DSCD-EM (HMM/MS state-distribution divergence — S8)
- DSCD-Identifiability (LLT variance flips — S9; new sub-pattern)

Banked: formalize DSCD sub-pattern taxonomy at check-in 2.

### Pattern F fourth concrete batch

`kalman_covariance_ordering` + `kalman_innovation_positivity` slots populated. **Eight concrete invariants** in production cumulative through S9.

### Particle filter SMC parity

`p3_particle_filter` is the **second SMC-class wrapper** (first was 2c MCMC SV in Phase 2). em_stochastic class; filtered-mean Pearson correlation comparison via Python `particles` package. PASS at corr ≥ 0.85 threshold.

## §10.3 measurement (fourth)

| # | Criterion | Result |
|---|---|---|
| 1 | Audit time | 5 audits/session = 50% improvement vs Batch 1 baseline | **PASSED** |
| 2 | LOC reduction | ~10% (distinct-wrapper batch with shared `_kalman_helpers.py`) | **NOT MET** (consistent w/ Batches 3, 4) |
| 3 | Zero infrastructure modification | **PASSED** |
| 4 | Bit-for-bit Batch 1 reproduction | **PASSED** — fast tier 32 PASS + 4 CAVEAT in 118s |

## Aggregate Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered | **28 / 70** |
| Phase 3 sessions used | 8 (S2–S9) — **4 sessions ahead of master plan** |
| BLOCK | 0 |
| CAVEAT cumulative | 4 |
| Patterns | A (11 wrappers) + B–H confirmed; I/J/K candidates |
| Concrete invariants | 8 (cumulative) |

## Banked items (cumulative through S9)

Inheriting all from S8; new at S9:
- **Item 14:** DSCD sub-pattern taxonomy (DSCD-MLE / DSCD-EM / DSCD-Identifiability)
- **Item 15:** LLT identifiability documentation candidate for P-3 (Session 26) — methodological note that 3-variance LLT is fundamentally non-identifiable on small T

Plus master plan §15 session-count budget revision (Item 13) gains weight: pace is now consistently 4-5 audits/session vs master plan's ~3/session assumption. At this pace Phase 3 closes in ~14-16 sessions vs budget 27.

## Next session

**Session 10** — Batch 6 entry per master plan §15.8 (R change-points / stationarity). 9 wrappers in scope:
- `adf_test.py`, `kpss_test.py`, `pp_test.py` (closed-form critical values)
- `bocpd.py` (Bayesian online change-point)
- `cusum_page_hinkley.py`, `pelt_change_points.py` (change-point methods)
- `intervention_analysis.py` (TSA package)
- `stl_esd_anomaly.py` (STL + Generalized ESD)
- `x13_seasonal_adjust.py` (R seasonal package — X-13ARIMA-SEATS binary wrapper)

Required deps: `tseries`, `changepoint`, `cpm`, `TSA`, `seasonal` (R); `bocd`, `ruptures` (Python). Per discipline lock: install matrix updates ship in commit.
