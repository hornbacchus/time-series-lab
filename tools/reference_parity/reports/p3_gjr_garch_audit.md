# P3 — `garch_model.py` (GJR-GARCH variant) reference parity audit

**Wrapper:** `engine/techniques/garch_model.py` (vol="GJR-GARCH" path → arch package vol="GARCH" + o=1)
**Audit ID:** `p3_gjr_garch`
**Batch / Session:** Phase 3 Batch 2 / Session 6
**Date:** 2026-04-28
**Verdict:** **PASS**

## 1. Reference

- **Primary:** R `rugarch::ugarchspec(model='gjrGARCH', garchOrder=c(1,1))` + `ugarchfit(solver='gosolnp', n.restarts=10, n.sim=2000, rseed=20260428)` — `rugarch` 1.5.5.

GJR adds asymmetric response to negative shocks via the gamma term:

    sigma2_t = omega + alpha * eps_{t-1}^2
                     + gamma * I(eps_{t-1} < 0) * eps_{t-1}^2
                     + beta * sigma2_{t-1}

Persistence formula: `alpha + beta + 0.5*gamma`. The 0.5 weight reflects that the asymmetric term applies to negative shocks only ~50% of the time under symmetric innovations.

## 2. Fixture

Same fixture as `p3_sgarch` (T=1000 GARCH(1,1) realization, seed=42). Note: the fixture is symmetric GARCH; gamma should converge near zero (no asymmetry in the DGP). Both implementations recover gamma ≈ 0.0034 (small + non-zero, near identifiability noise floor).

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | omega, alpha, beta, gamma, log-likelihood, 5-step forecast variance |
| **Secondary** | AIC, BIC, conditional variance series |

## 4. Tolerance ladder

Same band as `p3_sgarch`.

## 5. Achieved metrics (seed=42)

### Primary

| Metric | TSL | Reference | abs_diff | rel_diff | Status |
|---|---:|---:|---:|---:|---|
| omega | 0.5135935 | 0.5128143 | 7.79e-04 | 1.52e-03 | PASS |
| alpha | 0.0851029 | 0.0850928 | 1.01e-05 | 1.19e-04 | PASS |
| beta | 0.6533804 | 0.6537518 | 3.71e-04 | 5.68e-04 | PASS |
| gamma | 0.0034046 | 0.0035000 | 9.54e-05 | 2.73e-02 | PASS via abs_tol |
| log-likelihood | −1751.6907 | −1751.7061 | 1.54e-02 | 8.82e-06 | PASS |
| forecast_variance (max) | — | — | 6.74e-04 | 2.96e-04 | PASS |

The gamma `rel_diff` of 0.027 is high relative to other params because gamma is identified near zero on this symmetric fixture (denominator inflates rel_diff). The `abs_diff` of 9.5e-5 is well within band.

### Secondary

| Metric | TSL | Reference | abs_diff | rel_diff | Status |
|---|---:|---:|---:|---:|---|
| AIC | 3511.381 | 3511.412 | 3.09e-02 | 8.80e-06 | PASS |
| BIC | 3531.012 | 3531.043 | 3.09e-02 | 8.75e-06 | PASS |
| conditional_variance (max) | — | — | 1.44e-01 | 7.33e-02 | PASS via abs_tol |

## 6. Documented divergences

**Same DSCD pattern as p3_sgarch.** First-attempt with rugarch's default `hybrid` solver may land at boundary local optima; `gosolnp` with seeded restarts resolved it.

## 7. Runtime

5.1–24 seconds locally. Fast-tier eligible.

## 8. Reference version snapshot

- R: 4.5.3
- `rugarch`: 1.5.5
- Python `arch`: 8.0.0

## 9. Outcome

**PASS.** GJR-GARCH(1,1,1) parameters reproduce R rugarch outputs within the §7.1 MLE-fit band. The asymmetry coefficient `gamma` is small (near identifiability noise floor on the symmetric fixture) but matches rugarch at 9.5e-5 abs.

## 10. Notes

A GJR audit on an **asymmetric** DGP (e.g., Session 6 follow-up Phase 3.5 candidate) would identify gamma at a more substantive level (~0.05–0.15 typical for financial returns) and tighten the gamma rel_diff. Logged.
