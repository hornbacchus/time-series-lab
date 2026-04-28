# P3 — `arimax_sarimax.py` reference parity audit

**Wrapper:** `engine/techniques/arimax_sarimax.py`
**Audit ID:** `p3_arimax_sarimax`
**Batch / Session:** Phase 3 Batch 1 / Session 2
**Date:** 2026-04-28
**Verdict:** **PASS**

## 1. Reference

- **Primary:** R `forecast::Arima(y, order=c(p,d,q), xreg=X, method="ML")` — `forecast` 9.0.2.
- **Cross-check:** None at this iteration.

Both implementations fit Gaussian-innovation MLE on the regression-with-ARIMA-errors representation: `y_t = X_t β + u_t` where `u_t ∼ ARMA(p, q)`. Coefficient vector includes the regression coefs (β) plus the AR/MA coefs.

## 2. Fixture

Synthetic ARIMAX(1,0,1) DGP with one exogenous AR(1) regressor, runtime-generated:

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 300 |
| `phi` (AR1 of u_t) | 0.6 |
| `theta` (MA1 of u_t) | 0.4 |
| `beta` (exog coef) | 1.5 |
| `rho_x` (AR1 of x_t) | 0.7 |
| `sigma` | 1.0 |
| Burn-in | 100 |

Fit order: `(1, 0, 1)` non-seasonal + 1 exog regressor.

Future-x for forecast horizon: deterministic AR(1) continuation (zero noise) so the parity audit isolates the wrapper's forecast math from stochastic future-x estimation.

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | AR + MA coefs, exog regression coefficient, log-likelihood, 5-step forecast |
| **Secondary** | sigma², AIC, BIC |
| **Diagnostic** | in-sample fitted Pearson correlation |

## 4. Tolerance ladder

Same `p3_arima_manual` MLE-fit band (master plan §7.1).

## 5. Achieved metrics (seed=42)

### Primary

| Metric | TSL | Reference | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---:|---:|---|
| ar.L1 | 0.5401783 | 0.5401783 | 3.30e-08 | 6.12e-08 | PASS |
| ma.L1 | 0.5244840 | 0.5244863 | 2.28e-06 | 4.34e-06 | PASS |
| exog (β̂) | 1.5148831 | 1.5148886 | 5.52e-06 | 3.64e-06 | PASS |
| log-likelihood | −432.0837 | −432.0837 | 3.87e-08 | 8.95e-11 | PASS |
| forecast (h=5, max) | — | — | 2.14e-06 | 2.36e-06 | PASS |

True DGP β = 1.5; both implementations recover β̂ ≈ 1.5149 (within sampling noise of the truth at T=300 with σ=1).

### Secondary

| Metric | TSL | Reference | abs_diff | rel_diff | Status |
|---|---:|---:|---:|---:|---|
| sigma² | 1.0395412 | 1.0500586 | 1.05e-02 | 1.00e-02 | PASS |
| AIC | 872.1674 | 872.1674 | 7.74e-08 | 8.87e-11 | PASS |
| BIC | 886.9826 | 886.9826 | 7.74e-08 | 8.72e-11 | PASS |

## 6. Documented divergences

**None.** All Primary outputs PASS at the §7.1 MLE-fit band.

`sigma²` ~1% divergence: same MLE-vs-unbiased divisor convention as the prior two audits. Methodology-equivalent.

## 7. Runtime

2–3 seconds locally. Fast tier eligible.

## 8. Reference version snapshot

- R: 4.5.3
- `forecast`: 9.0.2
- statsmodels: 0.14.6

## 9. Outcome

**PASS.** ARIMAX/SARIMAX (with exog regressor) reproduces R `forecast::Arima(xreg=...)` outputs within the master plan §7.1 MLE-fit band on the seeded ARIMAX(1,0,1) DGP-recovery fixture. Exog coefficient parity verified to 5e-6 absolute (deep in PASS band).

## 10. Notes

R `forecast::Arima` names exogenous regressor coefs by the column names of `xreg` (or `xreg`/`xreg1` if no names). statsmodels names them `x1`, `x2`, ... by default (or by exog_names if supplied). The check extracts whichever-side names are non-AR/MA/intercept/drift/seasonal and treats them as the exog set; works for arbitrary number of exogenous regressors as long as the column ordering matches.

Future-x supply convention: both wrappers accept a future_x array of length horizon; the parity audit deterministically continues the AR(1) of x with zero noise to keep the comparison wrapper-side-only (not subject to RNG path differences in stochastic exog forecasting).
