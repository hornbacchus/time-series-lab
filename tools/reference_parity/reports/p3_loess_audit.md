# Phase 3 Batch 10 — `p3_loess` Audit

**Wrapper:** `engine/techniques/loess_interpolation.py`
**Reference:** direct `statsmodels.nonparametric.smoothers_lowess.lowess` (statsmodels 0.14.6)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Date:** 2026-04-29

| Metric | max abs diff | status |
|---|---:|---|
| `smoothed_y` | 0.0 | PASS (exact, 200 points) |

statsmodels.nonparametric.lowess is deterministic given
identical inputs + frac. Same-library self-test verifies
wrapper preprocessing round-trips the smoother.

DGP: noisy sinusoid x∈[0,10], y=sin(x)+N(0,0.09) (T=200,
seed=42); frac=0.3.
