# Theta Method

## What It Does

The Theta method is a simple yet surprisingly effective forecasting approach that decomposes a time series into two "theta lines" -- one that amplifies the local curvature of the data and one that dampens it. By extrapolating and combining these lines, the method produces forecasts that often rival more complex approaches. It gained prominence after winning the M3 forecasting competition.

## When to Use It

- You need a quick, competitive baseline forecast
- The series has a trend but limited or no seasonal pattern (deseasonalize first if seasonal)
- You want a method that is computationally cheap and requires minimal tuning
- You are benchmarking other forecasting models and need a strong simple comparator
- The series is too short for ARIMA model identification

## Key Assumptions

- The series is univariate and regularly spaced
- Any seasonal pattern has been removed prior to applying the method (standard practice)
- The underlying data-generating process can be reasonably approximated by a combination of linear extrapolation and exponential smoothing
- The series is not purely random noise (some signal must be present for extrapolation to be meaningful)

## Outputs

- **Point forecasts** for the specified horizon
- **Prediction intervals** based on the underlying SES model's error variance
- **Theta lines**: the decomposed components showing amplified and dampened curvature
- **Fitted values** for the in-sample period

## Technical Details

**Theta decomposition**: Given a time series `Y_t`, the theta method applies a "theta transformation" that modifies the second differences (curvature) of the series. For a parameter theta, the theta-line `Z_t(theta)` satisfies:

`Z_t''(theta) = theta * Y_t''`

where `Z_t'' = Z_t - 2*Z_{t-1} + Z_{t-2}` denotes the second difference. When `theta = 0`, the theta-line is a straight line (all curvature removed). When `theta = 2`, the curvature is doubled.

**Standard Theta method** (as used in the M3 competition):

1. **Deseasonalize**: If the series is seasonal, estimate seasonal indices (e.g., via classical decomposition) and divide them out.

2. **Create two theta lines**:
   - `Z_t(0)`: the linear regression line fit to the deseasonalized series (theta = 0). This extrapolates the global linear trend.
   - `Z_t(2)`: the series with doubled curvature (theta = 2). This amplifies short-term dynamics.

3. **Forecast each theta line**:
   - `Z_t(0)` is forecast by extending the fitted regression line.
   - `Z_t(2)` is forecast using Simple Exponential Smoothing (SES) with `alpha` estimated to minimize in-sample MSE.

4. **Combine**: The final forecast is the simple average of the two theta-line forecasts: `F_t = 0.5 * F_t(0) + 0.5 * F_t(2)`.

5. **Reseasonalize**: Multiply the combined forecast by the seasonal indices.

**Why it works**: The combination of a linear trend extrapolation (which captures the long-run direction) with SES (which adapts to recent levels) creates a balanced forecast. The method is equivalent to SES applied to the original data with a drift term equal to half the slope of the linear trend. This gives it the adaptability of exponential smoothing plus the directionality of trend extrapolation.

**Optimized Theta method**: Generalizations allow optimizing the theta parameter and the number of theta lines. The Dynamic Optimized Theta method fits multiple theta lines with optimized weights, improving accuracy at the cost of additional complexity.

**Prediction intervals**: Since the standard Theta method reduces to SES with drift, prediction intervals are computed as for SES: `F_t+h +/- z * sigma * sqrt(1 + (h-1)*alpha^2)`, where `sigma` is the residual standard error and `z` is the normal quantile for the desired confidence level.

## Interpretation

Theta method runs emit a two-tier Interpretation block with qualitative component disclosure.

**Plain-Language Finding (Tier 1)** - fit RMSE vs seasonal-naive baseline with percentage delta, end-of-horizon trend, seasonal pre-adjustment flag. Fit RMSE uses one-step-ahead expanding-window reconstruction when the statsmodels `fittedvalues` attribute is unavailable; a `fit_rmse_source` audit flag discloses the reconstruction method.

**Technical Interpretation (Tier 2)** - Theta decomposition math (theta=0 linear drift + theta=2 SES) qualitatively; seasonal pre-adjustment detail; honest-disclosure note that short-horizon M3 benchmark strength does not extend to longer horizons or non-seasonal series; statsmodels' ThetaModel does not expose individual theta-line coefficients numerically.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= naive baseline.
- Forecast horizon > 2x seasonal period - treat longer-horizon forecasts cautiously.
- Seasonal pre-adjustment disabled but a seasonal period is supplied.
