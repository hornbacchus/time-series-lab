# Phase 3 Batch 8 — `p3_random_forest` Audit

**Wrapper:** `engine/techniques/random_forest_forecast.py`
**Reference:** direct `sklearn.ensemble.RandomForestRegressor` in-process (sklearn 1.8.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | max abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `feature_importances` | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement on predictions and
feature importances. RandomForestRegressor with `random_state=42`
+ `n_jobs=1` is fully deterministic; same-library self-test
verifies wrapper preprocessing + lag-feature engineering
round-trip the sklearn primitive without bugs.

## Fixture

- DGP: AR(1), φ=0.6, σ=1.0, T=200, seed=42 (matches Batch 8
  shared DGP in `harness/checks/p3_random_forest.py`)
- 6 lag features
- TSL Fast preset: n_estimators=100, max_depth=6,
  min_samples_leaf=5
