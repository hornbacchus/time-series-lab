# Phase 3 Batch 7 — `p3_ssa` Audit

**Wrapper:** `engine/techniques/ssa_model.py`
**Reference:** from-scratch numpy SVD reference inline in
`harness/checks/p3_ssa.py` (numpy 2.4.4)
**Verdict:** **PASS** (Pattern A bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Component | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `singular_values` | 0.0 | 0.0 | PASS (exact) |
| `eigenvalues` | 0.0 | 0.0 | PASS (exact) |
| `U_first_col` | 0.0 | 0.0 | PASS (exact) |
| `Vt_first_row` | 0.0 | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement on singular values,
eigenvalues (singular values squared), and the first
left/right singular vectors after sign canonicalization.
SSA is closed-form: build Hankel trajectory matrix from
the time series, apply SVD, group eigentriples, diagonal-
average back to the time series. Both arms call
`numpy.linalg.svd` on identical Hankel matrix; output is
unique up to singular-vector sign, which the
`_sign_canonicalize` step removes.

## Fixture

- DGP: trend (0.02·t) + 12-period sinusoid + N(0, 0.09)
  noise, T=200, seed=42
- Window length L = N // 2 = 100
- n_components = 10

## Diagnostics

- numpy version: 2.4.4
- Sign convention: sklearn `svd_flip` style (max-absolute-
  entry of U positive, Vt sign-locked to U)

## Why self-parity vs `pyts.decomposition.SingularSpectrumAnalysis`

pyts provides an SSA estimator but its sklearn-style API
expects (n_samples, n_features) input shape and applies
SSA per-row, not per-time-series. Translating to a 1-D
series parity test is awkward; the from-scratch reference
follows Golyandina-Zhigljavsky 2013 directly, mirroring
TSL's numpy SVD implementation.
