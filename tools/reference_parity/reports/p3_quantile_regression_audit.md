# Phase 3 Batch 8 — `p3_quantile_regression` Audit

**Wrapper:** `engine/techniques/quantile_regression_model.py`
**Reference:** direct `sklearn.ensemble.GradientBoostingRegressor` with `loss='quantile'` per quantile level (sklearn 1.8.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | max abs diff | status |
|---|---:|---|
| `q10_preds` | 0.0 | PASS (exact) |
| `q50_preds` | 0.0 | PASS (exact) |
| `q90_preds` | 0.0 | PASS (exact) |
| `quantile_monotonicity` | — | PASS (1/194 = 0.52% crossings; expected algorithm behavior) |

**Outcome:** byte-identical agreement on all three quantile
prediction series. The quantile_monotonicity diagnostic
shows 1 quantile-crossing position out of 194 (0.52%) —
expected behavior for independent quantile GBR (each
quantile fit separately; not constrained to monotone). PASS
threshold set to 5% crossings.

## Fixture

- DGP: AR(1), φ=0.6, σ=1.0, T=200, seed=42
- 6 lag features
- Fast preset: n_estimators=100, max_depth=3,
  learning_rate=0.1
- Quantiles: 0.10, 0.50, 0.90

## Note on master plan §15.10 reference description

The plan's idealized reference was statsmodels.regression.
quantile_regression + R quantreg (linear quantile regression).
The actual TSL wrapper uses sklearn GradientBoostingRegressor
with quantile loss — non-linear quantile regression at each
quantile level. The same-library self-test catches wrapper-
level regressions in TSL's quantile-loss-on-GBR path; a
cross-library check (statsmodels quantreg vs R quantreg on
linear quantile regression) would be a different audit and
is out of scope this batch.

## Pattern H DSCD ruled out

Original Batch 8 hypothesis: quantile_regression statsmodels
vs R quantreg likely DSCD-Identifiability due to non-smooth
quantile loss. **Empirical result:** ruled out for THIS
wrapper — TSL doesn't use statsmodels quantreg; uses sklearn
GBR with quantile loss. The DSCD-Identifiability hypothesis
applies to LINEAR quantile regression (statsmodels vs R
quantreg cross-package), which is a different wrapper not in
TSL's current scope.
