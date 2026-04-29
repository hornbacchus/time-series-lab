# Phase 3 Batch 10 — `p3_granger` Audit

**Wrapper:** `engine/techniques/granger_causality.py`
**Reference:** R `lmtest::grangertest` (lmtest 0.9.40)
**Verdict:** **PASS** (Pattern A bit-exact)
**Date:** 2026-04-29

| Metric | abs diff | rel diff | status |
|---|---:|---:|---|
| `f_stat` | 8.53e-14 | 3.00e-15 | PASS |
| `p_value` | 5.20e-25 | 3.34e-14 | PASS |

Granger F-test is closed-form OLS-on-nested-models;
statsmodels.grangercausalitytests and R lmtest::grangertest
implement identical procedure. Bit-exact at machine precision.

DGP: bivariate AR(1) with X granger-causing Y (T=200, lag=2,
seed=42).
