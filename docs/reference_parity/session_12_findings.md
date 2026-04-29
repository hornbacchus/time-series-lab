# Phase 3 Session 12 — Batch 8 entry findings (Python ML)

**Date:** 2026-04-29
**Master plan reference:** §15.10 (Python ML)
**Wrappers in scope:** 7
**Verdicts:** **7 PASS, 0 CAVEAT, 0 BLOCK** — first all-PASS batch since Batch 1
**Sessions used:** 1 (master plan budgeted 1; on-budget)

## Wrappers covered

| # | Wrapper | Reference | Verdict | Tolerance |
|---|---|---|---|---:|
| 1 | `random_forest_forecast` | sklearn RandomForestRegressor | PASS | 0.0 abs (Pattern A same-library) |
| 2 | `gradient_boosting_forecast` | sklearn GradientBoostingRegressor | PASS | 0.0 abs (Pattern A same-library) |
| 3 | `xgboost_forecast` | xgboost.XGBRegressor direct | PASS | 0.0 abs (Pattern A same-library) |
| 4 | `lightgbm_forecast` | lightgbm.LGBMRegressor direct | PASS | 0.0 abs (Pattern A same-library) |
| 5 | `svr_forecast` | sklearn.svm.SVR direct | PASS | 0.0 abs (Pattern A same-library) |
| 6 | `quantile_regression_model` | sklearn GBR with quantile loss | PASS | 0.0 abs (Pattern A same-library) |
| 7 | `robust_estimators` | R stats::mad + robustbase::Qn | PASS | 4.22e-15 abs (Pattern A cross-package) |

## Headline findings

### 1. Pattern A → 27 wrappers (was 20)

ALL 7 Batch 8 wrappers achieved bit-exact parity. First all-PASS
batch since Batch 1. Same-library self-test pattern dominant: 6
wrappers used direct sklearn/xgboost/lightgbm imports; 1 used R
robustbase cross-package and reached machine precision.

### 2. Check-in 1.5 act-now decisions all delivered

- **#1 Pattern J catalog launched** —
  `docs/engineering/parity_diagnostic_reference.md` Appendix B
  with 6 entries. Sessions 13-15 will append.
- **#2 §10.3 criterion 2 split locked** — sub-criterion 2c
  (distinct-wrapper Python in-process / self-parity ≥30%)
  reported in batch summary. Batch 8 PASSES at 55-70% reduction.
- **#3 PyBridge isolate=False shim retire** — investigated:
  0/14 wrappers used the shim across Batches 7+8. Decision
  locked: Session 13 commit retires shim; subprocess-isolation
  path preserved for Batch 9.

### 3. Pattern H DSCD hypotheses ruled out

S12 prompt hypothesized SVR (DSCD-MLE) and quantile_regression
(DSCD-Identifiability) might exhibit DSCD. Empirical result:
both wrappers use same-library refs (sklearn primitives), so no
cross-library optimizer divergence surfaces. Pattern H DSCD
remains 4 wrappers cumulatively.

### 4. Pattern J — two new catalog entries

- **B.4.1 xgboost tree_method default flip** — pin
  `tree_method='hist'` explicit on both arms.
- **B.4.2 lightgbm parameter case sensitivity** — use sklearn-
  API snake_case; mixing camelCase silently ignores parameters.

### 5. §10.3 criteria — third consecutive batch passing both

| Batch | Criterion 1 | Criterion 2 sub-criterion |
|---|---|---|
| Batch 6 (S10) | 80% improvement | 30-40% (criterion 2c) |
| Batch 7 (S11) | 70% improvement | 35-45% (criterion 2c) |
| **Batch 8 (S12)** | 7 wrappers/session | **55-70% (criterion 2c)** |

### 6. Item 13 budget revision empirically locked at 17-18

11 sessions used (S2-S12) + ~6 remaining at current pace ≈ 17
total. Per check-in 1.5 locked decision: closure horizon at
17-18 sessions; Phase 3 buffer absorbs savings (no Phase 3.5
pull-forward).

## Cumulative Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 8) | **50** / 70 |
| Phase 3 remaining | 20 |
| Phase 3 sessions used | 11 (S2–S12) |
| **Pace** | **5–6 sessions ahead; closure at 17–18 (locked)** |
| BLOCK cumulative | 0 |
| CAVEAT cumulative | 5 (unchanged) |
| Pattern A wrappers | **27** (was 20) |
| Pattern F concrete invariants | 12 |
| Pattern J catalog entries | **6** (Appendix B launched) |

## CI matrix changes shipping in this commit

- `parity-fast.yml`: + lightgbm, xgboost (Python pip);
  robustbase (R)
- `MANIFEST.toml`: + lightgbm=4.6.0, xgboost=3.2.0,
  robustbase=0.99-7

## Verification

- `python -m reference_parity --tier fast` → 53 PASS + 5
  CAVEAT (unchanged from Batch 7) + 0 BLOCK + 0 ERROR.
  Total: 58 / 58 in 194.8s.
- All 7 Batch 8 checks invoked individually; all PASS.
- Tolerance ladder entries added for all 7 wrappers.

## Items banked (do NOT surface in commit message)

- Check-in 2 disposition follows Session 14 close per locked
  schedule.

## Next session

Session 13 — Batch 9 entry per master plan §15.11 (Python DL).
~9 wrappers in scope. **First batch using PyBridge.isolate=True
subprocess path** for PyTorch state isolation. Session 13 also
retires PyBridge isolate=False shim per locked decision #3.
