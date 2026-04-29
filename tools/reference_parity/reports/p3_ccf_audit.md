# Phase 3 Batch 10 — `p3_ccf` Audit

**Wrapper:** `engine/techniques/prewhitened_ccf_lag.py`
**Reference:** R `stats::ccf` (base R 4.5.3)
**Verdict:** **PASS** (Pattern A bit-exact)
**Date:** 2026-04-29

| Metric | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `ccf_positive` | 1.33e-15 | 1.46e-15 | PASS |

CCF is closed-form Pearson cross-correlation across lags;
both implementations compute identical normalized cross-
covariance. Lag-convention reconciliation: statsmodels.ccf(x,y)[k]
= cor(x[t+k], y[t]); R ccf(x,y) at lag k = same. Both arms
use POSITIVE lags 0..MAX_LAG.

Initial run blocked at 9% abs diff due to R lag-sign
extraction error; corrected to extract POSITIVE lags from R's
symmetric output (matching statsmodels semantics).

DGP: lagged-pair series (T=200, true lag=3, seed=42).
