# P3 — `classical_decompose.py` reference parity audit

**Wrapper:** `engine/techniques/classical_decompose.py`
**Audit ID:** `p3_classical_decompose`
**Batch / Session:** Phase 3 Batch 1 / Session 4
**Date:** 2026-04-28
**Verdict:** **PASS** (bit-exact at machine precision)

## 1. Reference

- **Primary:** R `stats::decompose(y, type="additive")` — base R 4.5.3.

Methodology equivalence note: both implementations follow the classical decomposition algorithm:
1. Centered moving average of length m → trend.
2. Detrended series (y − trend) → group seasonal averages by index-mod-m.
3. Replicated seasonal pattern → seasonal component.
4. Residual = y − trend − seasonal.

Closed-form arithmetic; bit-exact parity expected.

## 2. Fixture

Synthetic seasonal AR(1) with linear trend + sin seasonality (reused from `p3_theta` DGP):

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 120 |
| `phi` (AR1) | 0.7 |
| `sigma` | 1.0 |
| `m` | 12 |

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | trend, seasonal, residual component vectors |

## 4. Tolerance ladder

| Tier | abs_tol | rel_tol | block_abs_tol | block_rel_tol |
|---|---:|---:|---:|---:|
| Primary | 1e-10 | 1e-10 | 1e-6 | 1e-6 |

## 5. Achieved metrics (seed=42)

| Component | n_finite | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---:|---|
| trend | 108 | **7.11e-14** | 1.33e-15 | PASS |
| seasonal | 120 | **5.33e-15** | 1.72e-14 | PASS |
| residual | 108 | **1.73e-14** | 2.13e-12 | PASS |

**Bit-exact at IEEE 754 double precision.** Confirms Session 3 Observation 1: closed-form recursion → machine-precision parity.

## 6. Documented divergences

**None.** All three components agree at <1e-13 absolute, well below the 1e-10 PASS threshold.

## 7. Runtime

0.4–2.2 seconds locally. Fast tier eligible.

## 8. Reference version snapshot

- R: 4.5.3 (base `stats` package; no separate version pin)
- statsmodels: 0.14.6

## 9. Outcome

**PASS.** Classical decomposition (additive) is bit-exact between TSL (statsmodels `seasonal_decompose`) and R `stats::decompose`. Both implement the same closed-form algorithm.

## 10. Notes

The trend vector has 108 finite values out of 120 (NaN at edges where the centered MA window cannot be computed); the seasonal vector has all 120 (broadcast from the m=12 group means); the residual vector has 108 finite values (NaN where trend is NaN). The `_compare_vector` helper masks non-finite indices on both sides, so the comparison only operates on the 108 (or 120) jointly-finite positions.

**Multiplicative model not audited this session.** R `stats::decompose` supports `type="multiplicative"` and TSL's wrapper does too; same-class closed-form parity expected. Phase 3.5 candidate or follow-up if a fixture surfaces unexpected divergence.
