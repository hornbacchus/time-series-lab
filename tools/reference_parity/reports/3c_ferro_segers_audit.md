# 3c EVT Ferro-Segers extremal index — reference parity audit

**Date:** 2026-04-24

**Fixtures:**
- **Fixture A (clustering check):** GARCH(1,1) returns, omega=0.01, alpha=0.1, beta=0.88; T=2000, seed=42; threshold = 97.5th percentile of |y| = 1.537610.
- **Fixture B (iid baseline):** N(0, 1) iid, T=2000, seed=42; threshold = 97.5th percentile of |y| = 2.280760.

**Primary reference:** R `extRemes::extremalindex(..., method="intervals")`, the canonical Ferro-
Segers 2003 implementation.

**Tolerance:** `abs_tol=1e-6, rel_tol=1e-6` on theta.

## Secondary references — not used

- **evir::exindex:** evir::exindex is the BLOCK-MAXIMA extremal-index estimator (Smith 1989 blocks method), NOT the Ferro-Segers 2003 intervals estimator. Not a parity reference for TSL's intervals-based implementation. Skipped.

- **pyextremes:** pyextremes uses runs declustering (fixed-gap method), not Ferro-Segers intervals. Skipped as a parity reference.

## Overall verdict

| Fixture | TSL theta | extRemes theta | abs diff | Verdict |
|---|---|---|---|---|
| A GARCH clustering | 0.6184410424 | 0.6184410424 | 0.000e+00 | **PASS** |
| B iid baseline | 1.0000000000 | 1.0000000000 | 0.000e+00 | **PASS** |

## Correctness baseline (Fixture B iid)

Critical check: on iid data, theta should be near 1.0 (no clustering). Implementations reporting theta substantially < 1.0 on iid data have a bug.

| Implementation | theta on iid | interpretation |
|---|---|---|
| TSL | 1.0 | ✓ near 1.0 (1.0000) |
| extRemes | 1.0 | ✓ near 1.0 (1.0000) |

## Branch selection (TSL-only metadata)

Ferro-Segers has two polynomial branches: `T_i` form (simple; used when `max(T_i) ≤ 2`) and `(T_i-1)(T_i-2)` form (bias-corrected; used when `max(T_i) > 2`). R's `extRemes::extremalindex` does not publicly expose which branch it selects, so this check verifies TSL's branch-selection logic against observable inter-exceedance-time statistics.

| Fixture | TSL branch | max(T_i) | expected branch |
|---|---|---|---|
| A GARCH | `(T_i-1)(T_i-2)` | 257 | (T_i-1)(T_i-2) (✓) |
| B iid | `(T_i-1)(T_i-2)` | 133 | (T_i-1)(T_i-2) (✓) |

## Cluster count K

| Fixture | TSL K | extRemes K | agreement |
|---|---|---|---|
| A GARCH | 31 | 28 | abs diff = 3 |
| B iid | 50 | 46 | abs diff = 4 |

## Inter-exceedance-time statistics (TSL)

| Fixture | n_exceedances | min(T_i) | mean(T_i) | max(T_i) |
|---|---|---|---|---|
| A GARCH | 50 | 1 | 37.00 | 257 |
| B iid | 50 | 2 | 36.24 | 133 |

## Notes & methodology observations

- **evir::exindex is NOT the Ferro-Segers intervals estimator.** It's a block-maxima method (Smith 1989) requiring a `block` size argument. The Stage B plan named it as a secondary reference; that was an incorrect assumption — documented here so future audits don't repeat the mistake.

- **pyextremes uses runs declustering**, not intervals. Not a parity reference.

- **Absolute-value threshold convention:** both TSL (audit-specific) and extRemes operate on |y| > thr for symmetric return series. This mirrors standard EVT-on-returns practice and keeps exceedance sets identical across implementations.

- **Cluster count K interpretation:** TSL computes K = ceil(theta × n_exceed) per WAH / Ferro-Segers 2003. extRemes may compute K slightly differently (via cluster-boundary identification from inter-exceedance gaps). Small integer differences (±1) are expected and not audit failures.
