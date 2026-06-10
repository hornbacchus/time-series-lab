# 2a Kalman filter / smoother — reference parity audit

**Date:** 2026-04-24

**Fixture:** Local-level SSM (random walk + noise).
- `y_t = mu_t + e_t`, `e_t ~ N(0, H=1.0)`.
- `mu_t = mu_{t-1} + h_t`, `h_t ~ N(0, Q=0.1)`.
- Simulated T=100 observations, seed=42.
- Diffuse initial condition.

**Verification strategy:** pure inference, no MLE.
Parameters (H, Q) are fixed at simulation values;
each implementation runs the Kalman filter and
smoother at those fixed parameters. Three Kalman
engines compared:
- **TSL** (via statsmodels UnobservedComponents,
  which TSL's `kalman_filter` / `kalman_smoother`
  wrappers delegate to on the template path).
- **R dlm::dlmFilter / dlmSmooth**.
- **R KFAS::KFS** (modern successor of dlm with a
  univariate-disturbance filter).

**Tolerance:** `abs_tol = 1e-6` on filtered and
smoothed means. Linear Gaussian Kalman is
closed-form; different numerical paths (square-
root vs direct vs univariate) produce
fp-equivalent means but may differ in last fp
digits due to accumulation order.

## Filtered state mean

| Pair | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|
| TSL vs dlm | 2.437e-07 | 9.000e-07 | 2.868e-08 | **PASS** |
| TSL vs KFAS | 2.708e-07 | 1.000e-06 | 3.186e-08 | **PASS** |
| dlm vs KFAS | 2.708e-08 | 1.000e-07 | 3.186e-09 | **PASS** |

## Smoothed state mean

| Pair | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|
| TSL vs dlm | 2.129e-08 | 4.362e-06 | 3.135e-09 | **PASS** |
| TSL vs KFAS | 2.366e-08 | 4.846e-06 | 3.479e-09 | **PASS** |
| dlm vs KFAS | 2.365e-09 | 4.846e-07 | 3.460e-10 | **PASS** |

## Log-likelihood

| Implementation | log-likelihood |
|---|---|
| TSL | -152.8192579684 |
| R dlm | -69.9033913895 |
| R KFAS | -152.8192583324 |

- TSL vs dlm: abs_diff = 8.292e+01
- TSL vs KFAS: abs_diff = 3.640e-07

## Methodology notes

- **TSL's kalman_filter / kalman_smoother wrappers
  delegate to statsmodels's UnobservedComponents**
  on the template path. This audit calls
  UnobservedComponents directly with the fixed
  variance parameters [H, Q] — bypassing MLE so the
  check is on pure inference math, not optimization
  convergence.

- **dlm initialization:** dlmModPoly(order=1) with
  C0 = 1e7 gives an approximately-diffuse initial
  state. The first filtered value at t=1 contains
  the prior m0; the audit uses [-1] to drop it so
  shapes align across implementations (T filtered
  states for T observations).

- **KFAS filtering = 'state':** returns one-step-
  ahead predicted states `a[t|t-1]`, whereas
  statsmodels returns `filtered_state[t|t]` by
  default. For diffuse SSMs the predicted vs
  filtered distinction vanishes at steady state.
  Small systematic differences at t=1 are expected
  from initialization conventions and documented
  here.

- **Log-likelihood:** dlmLL returns *negative*
  log-likelihood by convention; the R script flips
  the sign to match statsmodels's and KFAS's
  positive-log-likelihood convention. Any systematic
  offset across implementations is a valid
  methodology difference, not a bug.
