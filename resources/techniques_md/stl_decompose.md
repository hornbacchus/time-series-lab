# STL Decomposition

## What It Does

STL (Seasonal and Trend decomposition using Loess) breaks a time series into three components: **trend**, **seasonal**, and **remainder**. It uses locally weighted regression (Loess) to iteratively extract each component, making it robust to outliers and flexible enough to handle changing seasonal patterns over time.

## When to Use It

- You want to understand the underlying trend after removing seasonal effects
- You need to check whether seasonal patterns are stable or evolving
- You suspect outliers are distorting simpler decomposition methods
- Your data has a single, known seasonal period (e.g., monthly data with yearly seasonality)
- You want a preprocessing step before forecasting or anomaly detection

## Key Assumptions

- The time series is regularly spaced (no missing timestamps)
- There is a single dominant seasonal period that you can specify
- The seasonal component is additive (for multiplicative patterns, apply a log transform first)
- Enough data exists to estimate the seasonal pattern (at least two full cycles recommended)

## Outputs

- **Trend component**: the long-term movement after removing seasonality
- **Seasonal component**: the repeating pattern at the specified period
- **Remainder component**: what is left after removing trend and seasonal effects; useful for spotting anomalies
- Diagnostic plots showing all three components aligned with the original series

## Technical Details

STL operates through an inner loop and an outer loop. The inner loop alternates between estimating the seasonal and trend components using Loess smoothing. The outer loop assigns robustness weights to reduce the influence of outliers in the remainder.

**Inner loop steps** (repeated `n_inner` times):

1. **Detrend**: subtract the current trend estimate from the series to isolate seasonality.
2. **Cycle-subseries smoothing**: for each position within the seasonal cycle (e.g., each month), apply Loess smoothing across years. The smoothing window `n_s` controls seasonal smoothness.
3. **Low-pass filter**: apply a moving average filter of length equal to the seasonal period, followed by Loess smoothing with window `n_l`, to extract a low-frequency component from the seasonal estimate.
4. **Remove low-pass**: subtract the low-pass result from the cycle-subseries smooth to get the final seasonal component.
5. **Deseason**: subtract the seasonal component from the original series.
6. **Trend smoothing**: apply Loess with window `n_t` to the deseasoned series to update the trend estimate.

**Outer loop** (repeated `n_outer` times): compute the remainder as `R = Y - T - S`, then assign robustness weights using a bisquare function on `|R| / (6 * median(|R|))`. These weights downweight large residuals in subsequent inner loop Loess fits.

**Key parameters**:
- `n_s` (seasonal smoother span): must be odd, larger values produce smoother seasonal components. Minimum recommended value is 7.
- `n_t` (trend smoother span): controls trend flexibility. Recommended default is the smallest odd integer >= `1.5 * period / (1 - 1.5/n_s)`.
- `n_l` (low-pass smoother span): recommended as the smallest odd integer >= period.
- `n_inner`: typically 1-2 for non-robust, 1 for robust fitting.
- `n_outer`: 0 for non-robust decomposition, 15 for robust decomposition with outlier resistance.

The Loess smoother at each point fits a weighted least-squares polynomial (degree 1 or 2) using a tricube weight function `W(u) = (1 - u^3)^3` based on the distance to neighboring points within the smoothing window.
