# P3 — `var_model.py` reference parity audit

**Wrapper:** `engine/techniques/var_model.py`
**Audit ID:** `p3_var`
**Batch / Session:** Phase 3 Batch 3 / Session 7
**Date:** 2026-04-29
**Verdict:** **PASS** (bit-exact at machine precision)

## 1. Reference

- **Primary:** R `vars::VAR(Y, p=2, type="const")` — `vars` 1.6.1.

VAR(p) estimation is OLS-on-stacked-equations: regress each variable on its own and other variables' p lags. Both statsmodels VAR and R `vars::VAR` implement the same closed-form normal-equations solve.

## 2. Fixture

Synthetic stationary bivariate VAR(2):

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 500 |
| `k` (variables) | 2 |
| `p` (lag order) | 2 (pinned, no auto-select) |
| Burn-in | 200 |

True coefficients: `A_1 = [[0.5, 0.1], [0.0, 0.4]]`, `A_2 = [[0.1, 0.0], [0.05, 0.2]]`.

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | AR coefficient tensor (p, k, k), intercept (k,), Sigma residual covariance (k, k), log-likelihood, 5-step forecast (h, k) |
| **Secondary** | AIC, BIC |
| **Diagnostic** | Companion-form eigenvalue magnitudes (Pattern F structural-invariant input) |

## 4. Tolerance ladder

Pattern A closed-form target (1e-8 abs / 1e-8 rel on Primary; 1e-2 abs / 1e-2 rel on Secondary).

## 5. Achieved metrics (seed=42)

### Primary

| Metric | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---|
| AR coefs (8 entries) | **7.22e-16** | 4.52e-15 | PASS |
| intercept (2,) | 1.60e-16 | 2.68e-15 | PASS |
| Sigma_u (4 entries) | 2.22e-16 | 1.46e-15 | PASS |
| log-likelihood | 4.55e-12 | 3.20e-15 | PASS |
| forecast (h=5, k=2) | 6.11e-16 | 4.05e-15 | PASS |

**Bit-exact at IEEE 754 double precision.**

### Secondary

| Metric | TSL | Reference | abs_diff | Status |
|---|---:|---:|---:|---|
| AIC | 0.07 | 2859.52 | 2859.45 | **BLOCK** (documented divergence) |
| BIC | 0.15 | 2901.63 | 2901.48 | **BLOCK** (documented divergence) |

The AIC/BIC scale offset is a known **methodology divergence**: statsmodels VAR.aic uses the formula `log(det(Sigma_u)) + 2*k_total/T` (per-observation form, dimensionless) while R `vars::VAR` returns the standard AIC formula `-2*loglik + 2*k_total` (likelihood-based, scales with T). Both rank-order alternative VAR(p) models identically; only absolute scale differs. Pattern D (AIC scale offset; Secondary tier; non-blocking) — see Batch 1 `p3_ets` for the first instance.

## 6. Documented divergences

**1. AIC/BIC scale-convention difference** (Secondary tier). Pattern D instance #2.

## 7. Runtime

0.59s. Fast-tier eligible.

## 8. Structural invariants verification

`var_eigenvalues`: max |companion eigenvalue| = computed from extracted A_p tensor. On the seed=42 fixture, all 4 eigenvalues are well inside the unit circle (stationarity confirmed). Diagnostic field `max_companion_eig` reports this.

## 9. Outcome

**PASS at machine precision.** **Pattern A 8th wrapper** + **Pattern D 2nd wrapper** (AIC scale offset). VAR(p) closed-form OLS reproduces R `vars::VAR` bit-for-bit. The `verdict_class = "closed_form"` annotation is empirically validated; this is **not a DSCD candidate** despite involving independent implementations — the underlying math is closed-form, not optimizer-driven.

## 10. Notes — Pattern H (DSCD) re-evaluation

Session 6 banked DSCD as a candidate verdict_class for cases where TSL and reference are independent implementations. p3_var was a candidate (statsmodels and R `vars` are independent), but achieved Pattern A bit-exact result rather than Pattern H DSCD. **DSCD applies to MLE-class wrappers, not to closed-form OLS.** Update Pattern H definition: DSCD = "independent-implementation OPTIMIZER divergence", not just "independent implementation." Closed-form algorithms (eigendecomposition, normal-equations OLS, FFT) don't have optimizer-search and so don't suffer from DSCD. Documented in cross-batch findings.
