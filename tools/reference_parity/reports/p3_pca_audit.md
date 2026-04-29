# P3 — `pca_analysis.py` reference parity audit

**Wrapper:** `engine/techniques/pca_analysis.py`
**Audit ID:** `p3_pca`
**Batch / Session:** Phase 3 Batch 3 / Session 7 (Batch 3 entry)
**Date:** 2026-04-29
**Verdict:** **PASS** (bit-exact at machine precision)

## 1. Reference

- **Primary:** Python `sklearn.decomposition.PCA` (1.8.0). Internally uses `np.linalg.svd`. PCA is closed-form eigendecomposition of the covariance matrix; both implementations should agree at machine precision modulo eigenvector sign convention.

## 2. Fixture

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` (observations) | 200 |
| `p` (features) | 5 |
| `k_factors` (latent in DGP) | 2 |
| `n_components` (extracted) | 5 (all) |

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | eigenvalues (5,), loadings (p, k), scores (n, k) |
| **Secondary** | total variance |

## 4. Tolerance ladder

Pattern A bit-exact target (1e-10 abs / 1e-10 rel on Primary).

## 5. Achieved metrics (seed=42)

### Primary

| Metric | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---|
| eigenvalues | **7.99e-15** | 1.13e-14 | PASS |
| loadings (sign-canonicalized) | **4.37e-14** | 3.84e-13 | PASS |
| scores (sign-canonicalized) | **7.64e-14** | 4.96e-11 | PASS |

### Secondary

| Metric | abs_diff | Status |
|---|---:|---|
| total_variance | 7.99e-15 | PASS |

**Bit-exact.** All metrics ≤ 1e-13 abs.

## 6. Documented divergences

**None.** Eigenvector sign-convention divergence (sklearn's `svd_flip` rule vs TSL's two-part rule) handled by sign-canonicalization in compare(). Post-canonicalization both implementations produce identical loadings to machine precision.

## 7. Runtime

0.08s. Fast-tier eligible.

## 8. Outcome

**PASS** at machine precision. **Pattern A 7th wrapper** (closed-form recursion → bit-exact parity). PCA wrapper bypasses TSL's 6-decimal output rounding by replicating the `np.linalg.eigh` math directly (mirror of `p3_arima` / `p3_har_rv` pattern).
