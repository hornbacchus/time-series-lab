# Phase 3 Batch 8 — `p3_lightgbm` Audit

**Wrapper:** `engine/techniques/lightgbm_forecast.py`
**Reference:** direct `lightgbm.LGBMRegressor` in-process (lightgbm 4.6.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | max abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `feature_importances` | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement. LGBMRegressor with
`deterministic=True` + `force_col_wise=True` + `n_jobs=1`
is deterministic; same-library self-test verifies wrapper.

## Fixture

- DGP: AR(1), φ=0.6, σ=1.0, T=200, seed=42
- 6 lag features
- Fast preset: n_estimators=100, max_depth=4,
  learning_rate=0.1, num_leaves=15
- lightgbm version: 4.6.0

## Pattern J catalog entry

lightgbm parameter case sensitivity: legacy LightGBM C-API
parameter names use camelCase (`numLeaves`, `maxDepth`); the
sklearn-API wrapper (`LGBMRegressor`) uses snake_case
(`num_leaves`, `max_depth`). Mixing conventions in a single
call is silently accepted but only some parameters are
recognized — invisible bug surface. Always use snake_case
via the sklearn API. Documented in Appendix B.
