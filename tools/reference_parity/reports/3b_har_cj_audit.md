# 3b HAR-CJ — reference parity audit

**Date:** 2026-04-24

**Fixture:** Synthetic RV / BV / TQ series mimicking ABD 2007 structure. T=1500, seed=42, M=78. Underlying continuous component is an AR(1) on log(C) with persistence 0.95; jumps injected on ~5% of days as Exp(0.5)·C; BV simulated as C + 5% log-normal noise; TQ ≈ BV² + noise.

**Verification strategy (Refinement R1):**
1. Build from-scratch Python reimplementation of HAR-CJ
   following ABD 2007 + Huang-Tauchen 2005 BNS test.
2. R1 paper-validation: check that reimpl produces
   sensible coefficients on the synthetic fixture
   (continuous components positive, R² > 0.3,
   continuous persistence sum in 0.5-0.95 range).
3. Audit step: TSL `har_cj` vs validated reimpl on
   identical fixture. OLS coefficients should agree
   to machine precision since both implementations
   apply identical preprocessing and identical OLS.

**Tolerance:** `abs_tol=1e-6, rel_tol=1e-6` on OLS
coefficients. The underlying OLS via `np.linalg.lstsq`
is bitwise-identical between TSL and reimpl (same
inputs, same LAPACK gelsd routine), but TSL's audit
fields and output table apply `round(coef, 6)` when
serializing back to user-visible format. The audit
therefore reads TSL coefficients via the `Estimate`
column of the `HAR-CJ Coefficients` output table and
compares at the 1e-6 floor TSL exposes.

## R1 paper validation — reimpl sanity

| Check | Value | Threshold | Verdict |
|---|---|---|---|
| Continuous components positive | β_cd=0.4721, β_cw=0.2674, β_cm=0.0850 | all > 0 | PASS |
| Continuous persistence sum | 0.8246 | in [0.5, 0.95] | PASS |
| R² | 0.3341 | > 0.3 | PASS |

**R1 paper validation:** PASS

Other reimpl diagnostics: jump fraction = 0.0360, jump persistence sum = 0.1969, T_effective = 1478

## TSL vs reimpl — coefficient parity

| Coefficient | reimpl | TSL | abs_diff | rel_diff | Verdict |
|---|---|---|---|---|---|
| `Intercept` | 0.0000086179 | 0.0000090000 | 3.821e-07 | 4.246e-02 | **PASS** |
| `beta_cd` | 0.4721147947 | 0.4721150000 | 2.053e-07 | 4.349e-07 | **PASS** |
| `beta_cw` | 0.2674330816 | 0.2674330000 | 8.157e-08 | 3.050e-07 | **PASS** |
| `beta_cm` | 0.0850302344 | 0.0850300000 | 2.344e-07 | 2.757e-06 | **PASS** |
| `beta_jd` | -0.0752439683 | -0.0752440000 | 3.167e-08 | 4.209e-07 | **PASS** |
| `beta_jw` | 0.2886080748 | 0.2886080000 | 7.475e-08 | 2.590e-07 | **PASS** |
| `beta_jm` | -0.0165045641 | -0.0165050000 | 4.359e-07 | 2.641e-05 | **PASS** |

**Coefficient vector max abs diff:** 4.359e-07
**Coefficient vector max rel diff:** 4.246e-02

## R² and persistence-sum cross-check

| Metric | reimpl | TSL | abs_diff |
|---|---|---|---|
| R² | 0.334059 | 0.334059 | 2.437e-07 |
| Continuous persistence sum | 0.824578 | 0.824600 | 2.189e-05 |
| Jump persistence sum | 0.196860 | 0.196900 | 4.046e-05 |

## Jump detection cross-check

- reimpl jump fraction: 0.0360
- TSL jump fraction:    0.036
- True jump fraction (fixture): 0.0473

## Methodology notes

- **R1 paper validation passed** above means the
  reimplementation produces ABD-2007-consistent
  coefficients on a synthetic-but-paper-shaped
  fixture. It does not validate against the paper's
  Table 5 SPY estimates directly (data unavailable);
  validation is structural / sign / persistence.

- **OLS bitwise parity** between TSL and reimpl is
  expected because both implementations apply the
  same:
    1. BNS z-statistic with theta = (pi/2)² + pi − 5,
    2. max(TQ, BV²) variance flooring,
    3. Forward-Phi(1−alpha) z threshold,
    4. J = max(RV − BV, 0) on jump days, else 0,
    5. C = RV − J,
    6. Lagged-window regressors (1 / 5 / 22),
    7. OLS via lstsq.

- **Floating-point reproducibility:** numpy's lstsq
  uses SVD (LAPACK gelsd) by default; on identical
  inputs, results are bitwise reproducible across
  runs and processes on the same machine. The audit's
  1e-8 tolerance is a strict-but-realistic floor.
