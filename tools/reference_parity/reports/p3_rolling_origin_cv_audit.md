# Phase 3 Batch 10 — `p3_rolling_origin_cv` Audit

**Wrapper:** `engine/techniques/rolling_origin_cv.py`
**Reference:** from-scratch self-parity (expanding-window CV with naive last-value forecast)
**Verdict:** **PASS** (Pattern A bit-exact)
**Date:** 2026-04-29

| Metric | max abs diff | status |
|---|---:|---|
| `per_fold_mae` | 0.0 | PASS (exact, 96 folds) |

Rolling-origin CV with naive last-value base forecaster is
deterministic loop over folds; each fold's MAE is closed-form.
Self-parity bit-exact across all 96 folds.

DGP: AR(1) (T=200, seed=42); initial_train=100, horizon=5,
step=1.
