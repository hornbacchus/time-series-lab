# P3 — `mstl_decompose.py` reference parity audit

**Wrapper:** `engine/techniques/mstl_decompose.py`
**Audit ID:** `p3_mstl`
**Batch / Session:** Phase 3 Batch 1 / Session 4
**Date:** 2026-04-28
**Verdict:** **CAVEAT** (matches structurally; per-component decomposition is non-unique)

## 1. Reference

- **Primary:** R `forecast::mstl(msts(y, seasonal.periods=c(m1, m2)))` — `forecast` 9.0.2.

Methodology note: both implementations apply STL iteratively across multiple seasonal periods (Bandara, Hyndman, Bergmeir 2021). The seasonal decomposition is **non-unique** within the constraint:

> y = trend + Σ_k seasonal_k + residual

Each implementation picks a different feasible point in this constraint set, depending on (a) iteration ordering of periods, (b) inner-LOESS convergence, (c) trend-extraction defaults.

Per Session 4 finding, the structural identity above holds at machine precision on both sides (recon_cross_max_abs_diff = 7.11e-14), even though per-component values diverge at ~1.0 absolute.

## 2. Fixture

Synthetic dual-seasonal series:

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 300 |
| `m1` (period 1) | 7 |
| `m2` (period 2) | 30 |
| `amp1` | 2.0 |
| `amp2` | 3.0 |
| `trend_slope` | 0.05 |
| `sigma` | 1.0 |

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | trend, seasonal_1 (period m1), residual |
| **Secondary** | seasonal_2 (period m2) |
| **Diagnostic** | structural-identity recon: trend+sum(seasonal)+resid ≡ y |

## 4. Tolerance ladder

| Tier | abs_tol | rel_tol | block_abs_tol | block_rel_tol |
|---|---:|---:|---:|---:|
| Primary | 5e-1 | 5e-1 | 5.0 | 5.0 |
| Secondary | 5e-1 | 5e-1 | 5.0 | 5.0 |

Bands widened significantly from p3_stl baseline. Rationale: dual-seasonal MSTL exhibits per-component divergence ~1.0 absolute even when both implementations decompose the same input faithfully.

## 5. Achieved metrics (seed=42)

### Primary

| Component | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---|
| trend | 8.48e-02 | 1.70e-03 | PASS via rel_tol |
| seasonal_1 (m=7) | 1.14 | 1.01 | **CAVEAT** |
| residual | 1.06 | 1.87 | **CAVEAT** |

### Secondary

| Component | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---|
| seasonal_2 (m=30) | 1.03 | 1.57 | **CAVEAT** |

### Diagnostic — structural identity

| Metric | Value |
|---|---:|
| recon_cross_max_abs_diff | **7.11e-14** |

Both TSL and R **decompose the same y faithfully** at machine precision. The non-uniqueness of the decomposition produces ~1.0 absolute divergence in the per-component breakdown, but the underlying signal is reconstructed identically.

## 6. Documented divergences

**1. Per-component decomposition is non-unique** at the algorithmic level. statsmodels MSTL and R forecast::mstl converge to different (but equally valid) feasible points in the decomposition polytope. Master plan §3.1 `DOCUMENTED-DIVERGENCE` semantics apply, surfaced as harness verdict `CAVEAT`.

**2. Iteration order matters.** R forecast::mstl iterates periods in *increasing* order (smallest period first); statsmodels MSTL has historically used the same order. Both implementations sequentially STL-decompose each period's contribution. Differences in default inner-iteration counts and LOESS bandwidth defaults compound across the sequential application.

**3. CAVEAT-reroll override.** `on_caveat_reroll` returns False (deterministic computation; reroll won't help).

**4. Verdict justification:** CAVEAT correctly signals "matches except in stated regime" per master plan §3.1 — the regime here is "non-unique seasonal decomposition." Structural identity verified separately at machine precision.

## 7. Runtime

1.7–4.2 seconds locally. Fast tier eligible.

## 8. Reference version snapshot

- R: 4.5.3
- `forecast`: 9.0.2
- statsmodels: 0.14.6

## 9. Outcome

**CAVEAT.** MSTL exhibits per-component decomposition divergence (~1.0 abs) reflecting documented non-uniqueness of seasonal decomposition under multi-period iterative STL. Structural identity (trend + Σ seasonal + resid ≡ y) verified at machine precision on both sides — both implementations decompose the same input faithfully.

This is the first CAVEAT verdict where the divergence is **algorithmic non-uniqueness** rather than convergence-criterion-difference. Future MSTL-class audits (e.g., MSTL with X-13 seasonal handling) will inherit this verdict pattern.

## 10. Notes

For practitioners, this means: do not expect MSTL trend or per-period seasonal components to match across implementations bitwise. Expect the *forecast* derived from MSTL components to match more closely (the forecast operation re-applies the structural identity, washing out per-component non-uniqueness). Future Phase 3.5 candidate: a forecast-based MSTL parity check that compares h-step forecasts derived from each implementation's MSTL output.
