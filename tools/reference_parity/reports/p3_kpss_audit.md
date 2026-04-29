# Phase 3 Batch 6 — `p3_kpss` Audit

**Wrapper:** `engine/techniques/kpss_test.py`
**Reference:** R `urca::ur.kpss` (urca 1.3.4)
**Verdict:** **PASS** (Pattern A bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | abs diff | rel diff | status |
|---|---:|---:|---:|---:|---|
| `test_statistic` (η) | 0.09170600105152636 | 0.0917060010515263 | 5.55e-17 | 6.05e-16 | PASS |

**Outcome:** machine-precision agreement. KPSS statistic is
closed-form: ratio of partial-sum-of-residuals to a
Newey-West-style long-run variance estimator. statsmodels
``kpss(regression="c", nlags=5)`` and R
``urca::ur.kpss(type="mu", use.lag=5)`` compute the
identical statistic given identical bandwidth.

## Fixture

- DGP: stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42
- Same generator as `p3_adf` and `p3_pp`

## Diagnostics

- TSL p-value: 0.10 (table boundary)
- 5% critical value: 0.463 (both sides)
- Bandwidth pinned to 5 on both sides (Schwert "short" rule
  for n=500: int(4*(5)^0.25) = 5)
- urca version: 1.3.4
