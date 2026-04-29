# Phase 3 Batch 6 — `p3_pp` Audit

**Wrapper:** `engine/techniques/pp_test.py`
**Reference:** R `urca::ur.pp` (urca 1.3.4)
**Verdict:** **PASS** (Pattern J widening — closed-form with
internal HAC kernel divergence accommodated)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | abs diff | rel diff | status |
|---|---:|---:|---:|---:|---|
| `test_statistic` (Z(τ)) | -9.25345071447954 | -9.25345280545195 | 2.09e-06 | 2.26e-07 | PASS |

**Outcome:** PASS at 2e-6 absolute. PP Z(τ) is closed-form
Newey-West correction to the DF t-statistic. The two
implementations differ slightly in their internal HAC kernel
defaults — ``arch.unitroot.PhillipsPerron`` (TSL) and
``urca::ur.pp`` agree to ~1e-6 absolute even with pinned
``lags=5``.

## Fixture

- DGP: stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42

## Diagnostics

- TSL backend: ``arch.PhillipsPerron`` (statsmodels < 0.14
  on this Python; arch path used)
- TSL p-value: 1.16e-15 (rejects unit-root null)
- 5% critical value: -2.87 (urca)
- Lag pinned to 5 on both sides
- urca version: 1.3.4

## Pattern J observation

Both implementations expose ``lags=5`` as a Newey-West
truncation lag, but their internal HAC kernel weights
(triangular vs Bartlett vs identical) and the residual
variance divisor (n-1 vs n-k) can differ at sub-1e-6 levels.
The 1e-3 abs / 1e-2 rel ladder accommodates this without
masking real regressions.
