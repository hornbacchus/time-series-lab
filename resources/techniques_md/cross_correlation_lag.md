# Cross-Correlation / Lag Analysis

## What It Does

Cross-correlation analysis measures the **linear association between two time series at different time lags**, identifying which lag produces the strongest relationship. The Cross-Correlation Function (CCF) computes the Pearson correlation between one series and a time-shifted version of another, revealing whether one series leads, lags, or moves simultaneously with the other, and by how many time periods.

## When to Use It

- You want to identify the time delay between a cause and its effect
- You are exploring the lead-lag relationship between two series before building a model
- You need to determine the appropriate lag for input variables in a transfer function or regression model
- You want a quick visualization of the temporal relationship between two series
- You are checking whether two series are related and at what time offset

## Key Assumptions

- Both series are stationary (or have been differenced to achieve stationarity)
- The relationship between the series is linear
- The series are measured at the same frequency and aligned in time
- The cross-correlation structure is stable over time
- Autocorrelation within each series does not spuriously inflate the cross-correlations

## Outputs

- **Cross-correlation function (CCF)**: correlation values at each lag from -max_lag to +max_lag
- **Peak lag**: the lag with the highest absolute cross-correlation
- **Peak correlation**: the strength of the relationship at the optimal lag
- **Confidence bounds**: approximate 95% significance bands under the null of no cross-correlation
- **CCF plot**: visual display of correlations across lags

## Technical Details

**Sample cross-correlation function**: For two series `x_t` and `y_t` of length T:

`r_{xy}(k) = c_{xy}(k) / (s_x * s_y)`

where the sample cross-covariance is:

`c_{xy}(k) = (1/T) sum_{t=1}^{T-k} (x_t - x_bar)(y_{t+k} - y_bar)` for k >= 0
`c_{xy}(k) = (1/T) sum_{t=1}^{T+k} (x_{t-k} - x_bar)(y_t - y_bar)` for k < 0

and `s_x`, `s_y` are the sample standard deviations.

**Lag sign convention**:
- `r_{xy}(k) > 0` for k > 0: x leads y (x at time t is correlated with y at time t+k)
- `r_{xy}(k) > 0` for k < 0: y leads x

**Approximate confidence bounds**: Under the null hypothesis that x and y are independent white noise processes, the cross-correlations are approximately:

`r_{xy}(k) ~ N(0, 1/T)`

The 95% confidence bounds are approximately `+/- 1.96 / sqrt(T)`. Cross-correlations exceeding these bounds are considered significant.

**Problem of spurious cross-correlation**: If both series are autocorrelated, the cross-correlation can be misleadingly high even when there is no true relationship. Sources of spurious cross-correlation:
- Common trends in both series (remove trends first by differencing)
- Shared seasonal patterns (deseasonalize first)
- Autocorrelation inflating the variance of cross-correlation estimates

**Prewhitening** (the recommended approach for identifying lag relationships):

1. Fit an ARIMA model to the input series x_t and compute the residuals (white noise) alpha_t.
2. Apply the exact same ARIMA filter to the output series y_t to get beta_t.
3. Compute the CCF between alpha_t and beta_t.

This removes the confounding effect of autocorrelation and produces reliable cross-correlation estimates. See the prewhitened CCF technique for details.

**Confidence intervals with autocorrelation**: When prewhitening is not used, Bartlett's formula provides adjusted standard errors:

`Var(r_{xy}(k)) approx (1/T) sum_{j=-inf}^{inf} [r_{xx}(j) r_{yy}(j) + r_{xy}(j+k) r_{yx}(j-k)]`

This is more complex than the white noise bounds and requires estimating the autocovariance functions.

**Practical guidelines**:
- Always check and handle stationarity before computing the CCF.
- Prewhitening is strongly recommended for reliable lag identification.
- The maximum lag to examine should be small relative to T (typically T/4 or less).
- Multiple significant lags may indicate a distributed lag relationship (transfer function model).
- A single dominant peak suggests a simple delay.

## Interpretation

**Plain-Language Finding (Tier 1)** - static single-window CCF. Names leader/follower, lag, peak rho with correlation-strength adjective, Bartlett-band significance, single-window vs rolling caveat.

**Technical Interpretation (Tier 2)** - static lag range, peak vs Bartlett band, pointer to prewhitening for autocorrelation-robust variant.

**Caveats (Tier 3, conditional)**:
- Insignificant peak (|rho| < band) - pair may be informationally independent.
- Boundary peak (at +/-max_lag) - optimum outside search range.
