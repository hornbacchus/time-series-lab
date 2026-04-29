# Phase 3 Batch 9 — `p3_conformal` Audit

**Wrapper:** `engine/techniques/conformal_intervals.py`
**Reference:** from-scratch split-conformal self-parity reference (~30 LOC inline)
**Verdict:** **PASS** (Pattern A self-parity bit-exact + Pattern F invariant PASS)
**Tolerance class:** conformal_coverage
**Date:** 2026-04-29

## Result

### Bit-exact parity metrics

| Metric | abs diff | status |
|---|---:|---|
| `lower` | 0.0 | PASS (exact) |
| `upper` | 0.0 | PASS (exact) |
| `qhat` | 0.0 | PASS (exact) |

### Pattern F structural invariants

| Invariant | Status | Detail |
|---|---|---|
| `conformal_nominal_coverage` | PASS | empirical coverage 0.8625 vs nominal 0.9 (alpha=0.1; n_test=80; within finite-sample slack) |

**Outcome:** byte-identical agreement on bounds + qhat;
empirical coverage within finite-sample slack of nominal
guarantee.

## Fixture

- DGP: AR(1), φ=0.6, T=400, seed=42 (n=400 chosen for stable
  empirical coverage estimate; n_test=80 → binomial σ_p ~3%)
- alpha = 0.1 (target 90% coverage)
- calib_frac = 0.3 (50% train / 30% calib / 20% test split)

## Diagnostics

- Reference rationale: MAPIE's TimeSeriesRegressor expects
  sklearn-API base estimators which don't match TSL's
  pmdarima ARIMA backbone. Inline self-parity reference
  mirrors TSL's quantile-of-absolute-residuals method
  verbatim.
- Pattern F first conformal invariant population (replaces
  Session 5 NotImplementedError stub).

## Pattern A self-parity rationale

Split-conformal prediction is closed-form: take (1-alpha)
quantile of calibration absolute residuals; interval =
y_pred ± qhat. Both arms compute identical quantile on
identical residuals; bit-exact qhat + lower/upper arrays
expected. Coverage validity (Vovk 2005 finite-sample
guarantee) verified as Pattern F invariant.
