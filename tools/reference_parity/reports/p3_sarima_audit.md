# P3 — `sarima.py` reference parity audit

**Wrapper:** `engine/techniques/sarima.py`
**Audit ID:** `p3_sarima`
**Batch / Session:** Phase 3 Batch 1 / Session 2
**Date:** 2026-04-28
**Verdict:** **PASS**

## 1. Reference

- **Primary:** R `forecast::Arima(y, order=c(p,d,q), seasonal=list(order=c(P,D,Q), period=m), method="ML")` — `forecast` 9.0.2.
- **Cross-check:** None at this iteration.

statsmodels SARIMAX and R forecast::Arima both fit Gaussian-innovation MLE on the multiplicative seasonal-ARMA state-space representation. We use `method="ML"` on the R side for an apples-to-apples comparison vs SARIMAX's MLE.

## 2. Fixture

Synthetic SARIMA(1,0,1)x(1,0,1)[12] DGP-recovery, runtime-generated:

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 240 |
| `phi` (AR1) | 0.6 |
| `theta` (MA1) | 0.4 |
| `Phi` (seasonal AR1) | 0.5 |
| `Theta` (seasonal MA1) | 0.3 |
| `sigma` | 1.0 |
| `m` (seasonal period) | 12 |
| Burn-in | 200 |

Fit order: `(1, 0, 1)` x `(1, 0, 1, 12)`.

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | non-seasonal AR + MA coefs, seasonal AR + MA coefs, log-likelihood, 12-step forecast |
| **Secondary** | sigma², AIC, BIC |
| **Diagnostic** | in-sample fitted Pearson correlation |

## 4. Tolerance ladder

Same `p3_arima_manual` MLE-fit band (master plan §7.1).

## 5. Achieved metrics (seed=42)

### Primary

| Metric | TSL | Reference | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---:|---:|---|
| ar (non-seasonal) | 0.5666164 | 0.5666221 | 5.77e-06 | 1.02e-05 | PASS |
| ma (non-seasonal) | 0.4983481 | 0.4983542 | 6.10e-06 | 1.22e-05 | PASS |
| sar (seasonal) | 0.5385684 | 0.5385623 | 6.14e-06 | 1.14e-05 | PASS |
| sma (seasonal) | 0.2601862 | 0.2601964 | 1.02e-05 | 3.92e-05 | PASS |
| log-likelihood | −347.7663 | −347.7663 | 5.80e-08 | 1.67e-10 | PASS |
| forecast (h=12, max) | — | — | 2.22e-05 | 3.44e-04 | PASS |

### Secondary

| Metric | TSL | Reference | abs_diff | rel_diff | Status |
|---|---:|---:|---:|---:|---|
| sigma² | 1.0217616 | 1.0390986 | 1.73e-02 | 1.67e-02 | PASS |
| AIC | 705.5326 | 705.5326 | 1.16e-07 | 1.64e-10 | PASS |
| BIC | 722.9358 | 722.9358 | 1.16e-07 | 1.60e-10 | PASS |

## 6. Documented divergences

**None.** All Primary outputs PASS at the §7.1 MLE-fit band; achieved tolerances 4–6 orders of magnitude tighter.

The `sigma²` ~1.7% divergence reflects the same MLE-vs-unbiased divisor convention difference as in `p3_arima_manual` — methodology-equivalent. Within Secondary tolerance.

## 7. Runtime

2–4 seconds locally. Fast tier eligible.

## 8. Reference version snapshot

- R: 4.5.3
- `forecast`: 9.0.2
- statsmodels: 0.14.6

## 9. Outcome

**PASS.** SARIMA reproduces R `forecast::Arima` (with seasonal arg, method="ML") outputs within the master plan §7.1 MLE-fit band on the seeded SARIMA(1,0,1)x(1,0,1)[12] DGP-recovery fixture.

## 10. Notes

The seasonal AR/MA naming convention required care: statsmodels names them `ar.S.L12` / `ma.S.L12` (seasonal-lag k means lag = k * period_m, indexed 1..P), while R `forecast::Arima` names them `sar1` / `sma1` (1-indexed seasonal lag). The check extracts the right names on each side then compares the resulting coefficient vector. Documented for Sessions 3–4 reuse.
