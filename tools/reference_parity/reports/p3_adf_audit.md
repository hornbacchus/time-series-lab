# Phase 3 Batch 6 — `p3_adf` Audit

**Wrapper:** `engine/techniques/adf_test.py`
**Reference:** R `urca::ur.df` (urca 1.3.4)
**Verdict:** **PASS** (Pattern A bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | abs diff | rel diff | status |
|---|---:|---:|---:|---:|---|
| `test_statistic` (tau) | -9.46555379266110 | -9.46555379266109 | 1.07e-14 | 1.13e-15 | PASS |

**Outcome:** machine-precision agreement. ADF test statistic
is closed-form OLS on the differenced series; statsmodels
``adfuller(maxlag=1, autolag=None, regression="c")`` and R
``urca::ur.df(type="drift", lags=1)`` compute identical
values given identical lag specification.

## Fixture

- DGP: stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42
- Burn-in 100 to discard transient

## Diagnostics

- TSL p-value: 4.04e-16
- Reference 5% critical value: -2.87
- Lag pinned to 1 on both sides
- urca version: 1.3.4
