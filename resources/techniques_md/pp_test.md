# Phillips-Perron Test

## What It Does

The Phillips-Perron (PP) test is a unit root test that checks whether a time series is non-stationary. Like the ADF test, its null hypothesis is that the series has a unit root. However, instead of adding lagged differences to handle autocorrelation (as ADF does), the PP test applies a non-parametric correction to the Dickey-Fuller test statistic, making it robust to general forms of heteroskedasticity and autocorrelation in the error term.

**See also**: the **Stationarity Triage** (invoked from the ADF ribbon button) runs ADF + KPSS + PP together and emits a joint verdict. PP serves as a tie-breaker on the unit-root side when ADF and KPSS disagree. Standalone PP is useful for programmatic drill-down; the triage path is the recommended workflow for most macro users.

**Summary language**: PP shares ADF's null (unit root), so the summary says "unit root rejected" / "unit root not rejected" — it does not affirm "is stationary" on its own, because that conclusion requires agreement from a complementary-null test like KPSS. Critical values appear in ascending 1% / 5% / 10% order.

## When to Use It

- You want a unit root test that is robust to heteroskedasticity (changing variance)
- You suspect the error process has forms of autocorrelation not well captured by adding lags
- You want an alternative to the ADF test that does not require selecting a lag order
- The residuals from the Dickey-Fuller regression may exhibit both serial correlation and heteroskedasticity
- You are performing a battery of unit root tests for robustness

## Key Assumptions

- The series follows a process that can be tested for a unit root using the Dickey-Fuller regression framework
- The error process is weakly dependent and can have heteroskedasticity
- The non-parametric variance correction (Newey-West or similar) uses an appropriate bandwidth
- The sample size is large enough for the non-parametric correction to work well

## Outputs

- **Test statistic**: the modified t-statistic (Z_t) or normalized coefficient (Z_alpha)
- **p-value**: based on the Dickey-Fuller distribution (same as ADF)
- **Critical values** at standard significance levels
- **Decision**: reject or fail to reject the unit root null hypothesis
- **Bandwidth** used for the spectral density estimation

## Technical Details

**Basic regression**: Like the ADF test, the PP test starts with the Dickey-Fuller regression (without augmentation lags):

`Y_t = alpha + rho * Y_{t-1} + e_t` (with constant)

or

`Y_t = alpha + beta*t + rho * Y_{t-1} + e_t` (with constant and trend)

The OLS estimates of `rho` and its t-statistic `t_rho` are computed, but they are then corrected non-parametrically.

**Non-parametric correction**: The PP test modifies the DF test statistic to account for serial correlation and heteroskedasticity. Two key quantities are estimated:

1. **Short-run variance**: `sigma^2 = (1/n) * sum_{t=1}^{n} e_hat_t^2` (the usual OLS residual variance)

2. **Long-run variance**: `lambda^2 = sigma^2 + 2 * sum_{j=1}^{l} w(j,l) * gamma_hat(j)`, where `gamma_hat(j) = (1/n) * sum_{t=j+1}^{n} e_hat_t * e_hat_{t-j}` is the sample autocovariance at lag j, and `w(j,l)` are kernel weights (typically Bartlett: `w(j,l) = 1 - j/(l+1)`).

**Modified test statistics**:

The Z_t statistic (modified t-statistic):

`Z_t = (sigma / lambda) * t_rho - (lambda^2 - sigma^2) / (2 * lambda * s_rho)`

where `s_rho` is the standard error of `rho_hat` and `t_rho = (rho_hat - 1) / s_rho`.

The Z_alpha statistic (modified coefficient):

`Z_alpha = n * (rho_hat - 1) - (n^2 * s_rho^2 / (2 * sigma^2)) * (lambda^2 - sigma^2)`

Both statistics follow the same asymptotic distributions as their Dickey-Fuller counterparts, so the same critical values apply.

**Bandwidth selection**: As with the KPSS test, the truncation lag `l` for the long-run variance estimator affects the test properties. Common choices include the Newey-West automatic bandwidth selector or Schwert's rule `l = floor(12 * (n/100)^{1/4})`.

**Comparison with ADF**:
- **Advantage**: PP does not require specifying a lag order. It handles arbitrary autocorrelation and heteroskedasticity non-parametrically.
- **Disadvantage**: In finite samples, the non-parametric correction can be imprecise, leading to size distortions (especially over-rejection) when the error process has strong negative MA components. The ADF test with proper lag selection often has better finite-sample properties.
- **Recommendation**: Use both tests. If they agree, the conclusion is robust. If they disagree, investigate further with the KPSS test or examine the data for structural breaks.

**Practical note**: The PP test is particularly useful for financial time series, where heteroskedasticity (volatility clustering) is common and the non-parametric correction provides robustness without requiring a specific volatility model.

## Interpretation

**Plain-Language Finding (Tier 1)** - Phillips-Perron verdict (null = unit root, mirrors ADF). Z(t) statistic, p-value, critical value, Newey-West correction note.

**Technical Interpretation (Tier 2)** - regression type, Newey-West bandwidth, sample size. Contrasts with ADF (lag augmentation) and KPSS (flipped null).

**Caveats (Tier 3, conditional)**:
- Borderline verdict (Z(t) within 10% of critical).
- Trending series with regression='c' - try regression='ct'.
