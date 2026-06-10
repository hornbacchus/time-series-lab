# 1c BVAR IRF / FEVD — reference parity audit

**Date:** 2026-04-24

**Fixture:** 2-variable VAR(1) with fixed coefficients
and residual covariance. H=10 for IRF; FEVD computed
at horizons [1, 4, 8, 10].

A1 = [[0.5, 0.1], [0.2, 0.6]]
Sigma = [[1.0, 0.3], [0.3, 1.0]]

**Verification strategy:** Per Stage B plan, the
parity check is on IRF / FEVD math given a fitted
VAR, NOT the Bayesian posterior estimation. TSL's
`_compute_posterior_irf` is called with `n_draws=1`
and `B_post_var=0` so the single posterior draw
equals the point estimate exactly → deterministic
IRF tensor. Same closed-form math is also
implemented in pure numpy (audit-side) and in
base-R matrix algebra (via rscript_bridge), with
all three compared elementwise.

**Tolerance:** `1e-12` (bitwise) for closed-form
math. No estimation noise; pure arithmetic.

## Cholesky factor

| Pair | max abs | verdict |
|---|---|---|
| TSL vs numpy | 0.000e+00 | **PASS** |
| TSL vs R | 3.331e-16 | **PASS** |
| numpy vs R | 3.331e-16 | **PASS** |

## IRF tensor — shape (10, 2, 2)

| Pair | max abs | max rel | RMS | verdict |
|---|---|---|---|---|
| TSL vs numpy | 0.000e+00 | 0.000e+00 | 0.000e+00 | **PASS** |
| TSL vs R | 4.580e-16 | 4.158e-15 | 1.462e-16 | **PASS** |
| numpy vs R | 4.580e-16 | 4.158e-15 | 1.462e-16 | **PASS** |

## FEVD at each requested horizon

### Horizon h=1

| Pair | max abs | max rel | verdict |
|---|---|---|---|
| TSL vs numpy | 0.000e+00 | 0.000e+00 | **PASS** |
| TSL vs R | 0.000e+00 | 0.000e+00 | **PASS** |
| numpy vs R | 0.000e+00 | 0.000e+00 | **PASS** |

### Horizon h=4

| Pair | max abs | max rel | verdict |
|---|---|---|---|
| TSL vs numpy | 0.000e+00 | 0.000e+00 | **PASS** |
| TSL vs R | 1.110e-16 | 1.779e-15 | **PASS** |
| numpy vs R | 1.110e-16 | 1.779e-15 | **PASS** |

### Horizon h=8

| Pair | max abs | max rel | verdict |
|---|---|---|---|
| TSL vs numpy | 0.000e+00 | 0.000e+00 | **PASS** |
| TSL vs R | 1.388e-16 | 1.922e-15 | **PASS** |
| numpy vs R | 1.388e-16 | 1.922e-15 | **PASS** |

### Horizon h=10

| Pair | max abs | max rel | verdict |
|---|---|---|---|
| TSL vs numpy | 0.000e+00 | 0.000e+00 | **PASS** |
| TSL vs R | 2.220e-16 | 6.780e-16 | **PASS** |
| numpy vs R | 2.220e-16 | 6.780e-16 | **PASS** |

## Methodology notes

- **Audit targets the IRF/FEVD math only.** The
  Bayesian posterior-draw machinery is unrelated to
  the IRF formulas — we zero out posterior variance
  so the single draw equals the point estimate. This
  isolates the math under test from Monte-Carlo noise.

- **Cholesky orthogonalization:** TSL, numpy, and R
  all use the lower-triangular Cholesky factor P = L
  such that L L' = Σ. R's `chol()` returns U upper-
  triangular, so the R reference transposes to get L.

- **MA coefficient recursion:** identical formula
  `Phi_0 = I`, `Phi_h = Σ_{j=1..min(h,p)} A_j · Phi_{h-j}`.
  TSL's in-wrapper implementation reindexes A_list
  starting from lag-1 (A_list[0] = A_1); pure numpy
  and R do the same. Shape convention for the IRF
  tensor: `(H, k, k)` with `[h, i, j]` = response of
  variable i to shock j at horizon h.

- **FEVD definition:** share of forecast error
  variance at horizon h explained by each shock, from
  cumulative squared orthogonalized IRF. All three
  implementations follow the same formula.
