# Phase 3 Batch 8 — Python ML: Per-Batch Summary

**Batch:** 8 (Python ML)
**Sessions:** S12 (single-session close — master plan §15.10 budgeted 1 session; on-budget)
**Date:** 2026-04-29
**Wrappers audited:** 7 distinct
**Verdicts:** **7 PASS, 0 CAVEAT, 0 BLOCK**

## Coverage matrix

| # | Wrapper | Audit ID | Reference | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | `random_forest_forecast.py` | `p3_random_forest` | `sklearn.ensemble.RandomForestRegressor` | **PASS** | Pattern A bit-exact (0.0); same-library |
| 2 | `gradient_boosting_forecast.py` | `p3_gradient_boosting` | `sklearn.ensemble.GradientBoostingRegressor` | **PASS** | Pattern A bit-exact (0.0); same-library |
| 3 | `xgboost_forecast.py` | `p3_xgboost` | `xgboost.XGBRegressor` direct | **PASS** | Pattern A bit-exact (0.0); same-library; tree_method='hist' pinned |
| 4 | `lightgbm_forecast.py` | `p3_lightgbm` | `lightgbm.LGBMRegressor` direct | **PASS** | Pattern A bit-exact (0.0); same-library; deterministic=True pinned |
| 5 | `svr_forecast.py` | `p3_svr` | `sklearn.svm.SVR` direct | **PASS** | Pattern A bit-exact (0.0); same-library; libsvm SMO deterministic |
| 6 | `quantile_regression_model.py` | `p3_quantile_regression` | sklearn GBR with quantile loss per level | **PASS** | Pattern A bit-exact on q10/q50/q90 (0.0); same-library; 0.52% monotonicity crossings (within 5% PASS threshold) |
| 7 | `robust_estimators.py` | `p3_robust_estimators` | R `stats::mad` + `robustbase::Qn` | **PASS** | Pattern A cross-package machine precision (4.44e-16 mad; 4.22e-15 qn) |

## Patterns

### Pattern A — closed-form expansion to **27 wrappers**

ALL 7 Batch 8 wrappers achieved bit-exact parity (6 at exactly
0.0 abs diff via same-library; 1 at machine precision
cross-package). Pattern A wrapper count is now **27** (was 20
at Batch 7 close):

- 14 from Batches 1–6
- 6 from Batch 7 (FFT/periodogram/lomb-scargle peak/wavelets/SSA)
- **NEW Session 12 (7):** random_forest, gradient_boosting,
  xgboost, lightgbm, svr, quantile_regression,
  robust_estimators

This is the **first all-PASS Batch since Batch 1** (Batches 4,
5, 7 had CAVEATs; Batch 6 was all-PASS but smaller).

### Pattern A same-library precedent locked at scale for P-2

Six of seven Batch 8 wrappers used same-library self-test
(direct sklearn / xgboost / lightgbm in-process). All 6
achieved 0.0 abs diff (byte-identical predictions and
feature importances). Cumulative same-library precedent:

| Batch | Wrappers | Pattern |
|---|---|---|
| Batch 6 | p3_pelt | ruptures self-test |
| Batch 7 | p3_periodogram, p3_wavelet_transform | scipy/pywt self-test |
| **Batch 8** | **6 wrappers** | **sklearn/xgboost/lightgbm self-test** |

**9 wrappers cumulatively** establish the same-library
self-test pattern. P-2 should formalize this as Pattern A
sub-class "same-library reproducibility verification" —
catches wrapper-level preprocessing / parameter-resolution
regressions without requiring an independent reference
implementation.

### Pattern H DSCD candidates ruled out

Two Batch 8 hypotheses (per S12 prompt) were ruled out:

1. **SVR vs sklearn DSCD-MLE** — ruled out. Same library
   (libsvm SMO via sklearn) means same optimizer; bit-exact
   parity, no cross-library divergence to surface.
2. **quantile_regression statsmodels vs R quantreg
   DSCD-Identifiability** — partially ruled out. TSL's
   wrapper uses sklearn GBR with quantile loss (NOT
   statsmodels QR). Cross-package linear-QR comparison would
   be a different audit; out of scope.

Pattern H DSCD remains 4 wrappers cumulatively.

### Pattern J catalog launch

Per check-in 1.5 act-now decision #1, this commit creates
**`docs/engineering/parity_diagnostic_reference.md`**
**Appendix B** documenting Pattern J quirks. Sessions 8/10/11
quirks captured plus 2 new from Batch 8:

| Source | Quirk | Resolution |
|---|---|---|
| MSwM (S8) | log-likelihood sign convention | abs() comparison |
| tsDyn::setar (S8) | th access via coef() not slot | extract via coef[\"th\"] |
| arch / urca (S10) | HAC kernel default mismatch | tolerance widening 1e-3 abs |
| scipy / astropy (S11) | LS normalization convention | alignment-via-metric (peak freq) |
| **NEW xgboost (S12)** | tree_method default flips across versions | pin tree_method='hist' explicit |
| **NEW lightgbm (S12)** | parameter case-sensitivity (camelCase vs snake_case) | use sklearn-API snake_case only |

Sessions 13–15 will append additional entries.

### §10.3 criterion 2 split lock — Batch 8 reports 2c

Per check-in 1.5 act-now decision #2, the revised criterion 2
wording locks at:

| Sub-criterion | Threshold | Batch 8 result |
|---|---|---|
| (2a) variant-shared | ≥50% LOC reduction | N/A (no variant-shared this batch) |
| (2b) distinct-wrapper R-subprocess | ≥10% LOC reduction | N/A (only 1 of 7 is R-subprocess) |
| (2c) distinct-wrapper Python in-process / self-parity | ≥30% LOC reduction | **PASSED** (per-check files ~120–180 LOC vs Batch 1 ~400 LOC = 55–70% reduction) |

Batch 8 reports against **sub-criterion 2c** since 6/7 of
the wrappers used Python in-process refs and 1/7 used
R-subprocess (robust_estimators).

### PyBridge isolate=False shim usage — Batch 8 evidence

Per check-in 1.5 act-now decision #3, this batch tracks shim
mode usage:

| Wrapper | PyBridge.py_invoke called? | Mode |
|---|---|---|
| p3_random_forest | NO | direct sklearn import |
| p3_gradient_boosting | NO | direct sklearn import |
| p3_xgboost | NO | direct xgboost import |
| p3_lightgbm | NO | direct lightgbm import |
| p3_svr | NO | direct sklearn import |
| p3_quantile_regression | NO | direct sklearn import |
| p3_robust_estimators | NO | direct scipy import + R subprocess for Qn |

**0/7 wrappers used the PyBridge.py_invoke shim** — same
result as Batch 7 (0/7 used it). Cumulative PyBridge.py_invoke
usage in production: **0 wrappers across 14 checks** (Batches
7+8 combined).

**Decision per locked discipline:** Session 13 commit retires
the `isolate=False` shim from PyBridge. The `isolate=True`
subprocess path is preserved (Batch 9 DL needs it). The
`PyBridge` class will become subprocess-isolation-only;
in-process Python references continue using the established
direct-import pattern (p3_pca / p3_dfm precedent).

## Aggregate Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 8) | **50** (Batch 1: 10; Batch 2: 4; Batch 3: 4; Batch 4: 5; Batch 5: 5; Batch 6: 8; Batch 7: 7; Batch 8: 7) |
| Phase 3 remaining | 20 |
| Phase 3 sessions used | 11 (S2–S12) |
| **Pace** | **5–6 sessions ahead of master plan; closure horizon at 17–18 sessions per locked Item 13** |
| BLOCK | 0 |
| CAVEAT cumulative | 5 (p3_stl, p3_mstl, p3_star, p3_nar_narx, p3_emd_hht — unchanged from Batch 7) |
| Pattern A wrappers | **27** (was 20 at Batch 7 close) |
| Pattern F concrete invariants | 12 (no change this batch) |
| Pattern J catalog entries | **6** (Appendix B launched this batch) |

## CI install matrix update

Batch 8 install additions in this commit:
- Python: `lightgbm` (4.6.0); xgboost already in matrix
  from prior session
- R: `robustbase` (0.99-7); quantreg already pinned

## Next session

Session 13 — Batch 8 second half OR Batch 9 entry per master
plan §15.11 (Python DL). Master plan §15.10 budgeted Batch 8
at 1 session; closed in 1 session — proceed to Batch 9 in S13.

Session 13 also retires PyBridge `isolate=False` shim per
locked check-in 1.5 decision #3 (evidence: 0/14 wrappers
used the shim across Batches 7+8).

Chat check-in 2 follows Session 14 close per locked schedule.
