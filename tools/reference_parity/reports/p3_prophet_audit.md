# Phase 3 Batch 9 — `p3_prophet` Audit

**Wrapper:** `engine/techniques/prophet_forecast.py`
**Reference:** direct `prophet.Prophet` in-process (prophet 1.3.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** dl_seed_pinned (slow tier)
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `yhat` | 0.0 | PASS (exact) |
| `trend` | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement on yhat and trend
forecasts. Prophet configured with `uncertainty_samples=0` to
disable MCMC sampling and run pure MAP estimation
(deterministic given fixed Stan optimization). Same-library
self-test verifies wrapper preprocessing round-trips the
prophet primitive.

## Fixture
- DGP: 120 monthly observations with linear trend + 12-period
  sinusoidal seasonal + N(0, 0.09) noise, seed=42
- Forecast horizon: 12 months
- Total predicted: 132 points (120 fitted + 12 forecast)

## Diagnostics
- Tier: slow (Prophet's cmdstanpy backend takes ~2s per fit;
  master plan §12.2 routing rule applied)
- prophet version: 1.3.0
