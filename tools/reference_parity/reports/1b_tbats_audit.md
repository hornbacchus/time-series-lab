# 1b TBATS — reference parity audit

**Date:** 2026-04-24

**Fixture:** Seasonal AR(1) with 12-period sinusoidal seasonal + AR(1) noise. T=240, seasonal_period=12, seed=42.

**Implementations compared:**
- **TSL `tbats_forecast`** (wraps Python `tbats` 1.1.3)
- **Python tbats package** directly (same library TSL
  wraps; verifies wrapper does not introduce noise)
- **R forecast::tbats** (De Livera-Hyndman-Snyder 2011
  reference implementation)

**Tolerance:** smoothing params 1e-4 abs / 1e-3 rel; Box-Cox lambda same; forecasts 1e-2 abs / 1e-3 rel.

## Smoothing parameters

| Parameter | TSL | py-tbats | R::forecast | TSL vs py-tbats | TSL vs R |
|---|---|---|---|---|---|
| `alpha` | 0.920866 | 0.920866 | 0.897176 | 2.317e-07 (PASS) | 2.369e-02 (DIVERGE) |
| `beta` | -0.155817 | -0.155817 | 0.001287 | 4.726e-07 (PASS) | 1.571e-01 (DIVERGE) |
| `box_cox_lambda` | 0.999148 | 0.999148 | 0.999999 | 1.725e-07 (PASS) | 8.512e-04 (PASS) |

## Seasonal Fourier coefficients (gamma)

- TSL vs py-tbats gamma vector: max_abs=0.000e+00, max_rel=0.000e+00 → **PASS**
- TSL vs R::forecast gamma vector: max_abs=3.757e-03, max_rel=1.001e+00 → **DIVERGE**

## Point forecasts at h=1, 6, 12, 24

| h | TSL | py-tbats | R::forecast |
|---|---|---|---|
| h=1 | 20.4083 | 20.4083 | 20.2261 |
| h=6 | 23.2675 | 23.2675 | 23.4775 |
| h=12 | 18.3386 | 18.3386 | 19.1388 |
| h=24 | 18.3607 | 18.3607 | 20.2573 |

**Forecast vector comparison (full h=24):**

- TSL vs py-tbats: max_abs=4.922e-07, max_rel=2.377e-08, RMS=3.005e-07 → **PASS**
- TSL vs R::forecast: max_abs=1.897e+00, max_rel=9.684e-02, RMS=1.010e+00 → **DIVERGE**

## Methodology notes

- **TSL vs py-tbats** is expected to be bit-identical
  (or near-bitwise) since TSL wraps the same package.
  Any divergence here would indicate a wrapper-
  introduced numerical artifact.

- **TSL vs R::forecast** is a true cross-implementation
  parity check. Both implement the same TBATS framework
  (De Livera-Hyndman-Snyder 2011) but differ in:
  - Optimization initialization (random restarts vs
    deterministic AIC-grid).
  - Box-Cox lambda search range.
  - ARMA error order selection.
  - Damped-trend handling.
  Modest divergence on smoothing parameters is expected;
  forecasts should align since both optimize the same
  log-likelihood.

- **Gamma vector ordering:** Python tbats stores gamma
  parameters as [gamma1_period1, gamma2_period1,
  gamma1_period2, ...] (interleaved) while R::forecast
  exposes them as separate `gamma.one.values` and
  `gamma.two.values` vectors. The audit concatenates
  R's two vectors; element-wise comparison may show
  ordering-induced divergence even if values agree as
  a set. Treat ordering-mismatch divergence as audit
  artifact, not bug.
