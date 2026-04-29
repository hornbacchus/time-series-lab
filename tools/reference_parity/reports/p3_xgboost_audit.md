# Phase 3 Batch 8 — `p3_xgboost` Audit

**Wrapper:** `engine/techniques/xgboost_forecast.py`
**Reference:** direct `xgboost.XGBRegressor` in-process (xgboost 3.2.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | max abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `feature_importances` | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement. XGBRegressor with
`tree_method='hist'` + `random_state=42` + `n_jobs=1` is
deterministic; same-library self-test verifies wrapper math.

## Fixture

- DGP: AR(1), φ=0.6, σ=1.0, T=200, seed=42
- 6 lag features
- Fast preset: n_estimators=100, max_depth=4, learning_rate=0.1
- xgboost version: 3.2.0

## Pattern J catalog entry

xgboost `tree_method` default has flipped across major
versions:
- xgboost < 1.0: default `'exact'`
- xgboost 1.0+: default `'auto'` (resolves to `'hist'` on
  most platforms)
- xgboost 2.0+: default `'hist'` explicit

To preserve reproducibility across version drift, pin
`tree_method='hist'` explicitly. Documented in Appendix B
of `docs/engineering/parity_diagnostic_reference.md`.
