# KPSS Test

## What It Does

The KPSS (Kwiatkowski-Phillips-Schmidt-Shin) test checks whether a time series is **stationary** around a deterministic level or trend. Unlike the ADF test, the KPSS null hypothesis is that the series IS stationary, and rejection indicates non-stationarity. This reversal of hypotheses makes it a useful complement to the ADF test for confirming the stationarity status of a series.

**See also**: the **Stationarity Triage** (invoked from the ADF ribbon button) runs ADF + KPSS + PP together and emits a joint verdict. KPSS as a standalone technique is useful for programmatic drill-down; the triage path is the recommended workflow for most macro users.

**Summary language**: because the KPSS null IS stationarity, "null not rejected" legitimately supports the phrasing "series appears stationary" — in contrast to ADF/PP, whose nulls are the unit root and which therefore can only say "unit root rejected" (not the same thing as affirming stationarity). Critical values in the Results sheet appear in ascending 1% / 5% / 10% order.

## When to Use It

- You want to confirm results from the ADF test (use both together for robustness)
- You need to distinguish between trend-stationarity and difference-stationarity
- You want a test where stationarity is the null hypothesis (to be conservative about declaring non-stationarity)
- As part of determining the differencing order for ARIMA modeling
- When the ADF test gives ambiguous results (p-value near 0.05)

## Key Assumptions

- The series can be decomposed into a deterministic trend, a random walk, and a stationary error
- The error process has a well-defined long-run variance
- The bandwidth parameter for the long-run variance estimator is chosen appropriately
- There are no structural breaks in the series (which can cause spurious rejections)

## Outputs

- **Test statistic**: the KPSS statistic (always positive)
- **Critical values** at 10%, 5%, 2.5%, and 1% significance levels
- **p-value**: often reported as bounds (e.g., "< 0.01" or "> 0.10") since exact p-values require interpolation
- **Decision**: reject stationarity or fail to reject
- **Bandwidth** used for long-run variance estimation

## Technical Details

**Model**: The KPSS test decomposes the series as:

`Y_t = xi*t + r_t + e_t`

where:
- `xi*t` is a deterministic trend (set `xi = 0` for the level-stationary version)
- `r_t = r_{t-1} + u_t` is a random walk with `u_t ~ iid(0, sigma_u^2)`
- `e_t` is a stationary error process

**Hypotheses**:
- **H0 (stationarity)**: `sigma_u^2 = 0`, meaning the random walk component has zero variance and the series is stationary (around a level or trend).
- **H1 (unit root)**: `sigma_u^2 > 0`, meaning the random walk component contributes non-stationary behavior.

**Two variants**:
1. **Level stationarity** (`mu` test): Tests stationarity around a constant mean. Regression: `Y_t = mu + e_t`.
2. **Trend stationarity** (`tau` test): Tests stationarity around a linear trend. Regression: `Y_t = mu + beta*t + e_t`.

**Test statistic**:

1. Regress `Y_t` on a constant (level test) or constant + trend (trend test) to obtain residuals `e_hat_t`.
2. Compute partial sums: `S_t = sum_{i=1}^{t} e_hat_i`.
3. Compute the test statistic: `KPSS = (1/n^2) * sum_{t=1}^{n} S_t^2 / s^2(l)`.

where `s^2(l)` is the Newey-West long-run variance estimator of `e_t`:

`s^2(l) = (1/n) * sum_{t=1}^{n} e_hat_t^2 + (2/n) * sum_{j=1}^{l} w(j,l) * sum_{t=j+1}^{n} e_hat_t * e_hat_{t-j}`

with Bartlett kernel weights `w(j,l) = 1 - j/(l+1)`.

**Bandwidth selection**: The truncation lag `l` for the long-run variance estimator is critical. Common choices:
- Schwert's rule: `l = floor(12 * (n/100)^{1/4})`
- Andrews' data-dependent bandwidth using an AR(1) approximation
- Too small `l` causes size distortion (over-rejection); too large `l` reduces power.

**Critical values** (asymptotic, from KPSS 1992):

| Significance | Level test | Trend test |
|---|---|---|
| 10% | 0.347 | 0.119 |
| 5% | 0.463 | 0.146 |
| 1% | 0.739 | 0.216 |

**Joint use with ADF**: Four outcomes are possible: (1) ADF rejects, KPSS does not reject: series is stationary. (2) ADF does not reject, KPSS rejects: series has a unit root. (3) Both reject: inconclusive, possibly fractional integration. (4) Neither rejects: inconclusive, low power in both tests.

## Interpretation

**Plain-Language Finding (Tier 1)** - KPSS verdict (null = stationarity, inverts ADF/PP direction). Names the rejection/fail-to-reject verb, stat value, critical value, series consequence.

**Technical Interpretation (Tier 2)** - regression type (constant/trend), Newey-West bandwidth, sample size. Emphasizes null-direction flip (rejection means non-stationarity). Pairs with ADF for joint triage.

**Caveats (Tier 3, conditional)**:
- Borderline verdict (LM within 10% of critical) - joint triage advisable.
- Trending series with regression='c' - try regression='ct'.
