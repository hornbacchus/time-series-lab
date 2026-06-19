## What It Does
Classical decomposition splits a time series into three components — trend, seasonal, and residual — using the ratio-to-moving-average method. It estimates the trend with a centered moving average, extracts a fixed seasonal pattern that repeats each cycle, and leaves the remainder as the residual. It is the simplest, most transparent decomposition, and a good first look at a series' structure.

## When to Use It
- You want a quick, interpretable breakdown of a series into trend, seasonal, and residual.
- The seasonal pattern is roughly constant over time (a fixed shape each cycle).
- You want a transparent baseline before reaching for more flexible methods.
- Use classical decomposition for a fixed seasonal pattern; use `stl_decompose` when the seasonality evolves or the series has outliers; use `mstl_decompose` for multiple seasonal cycles.

## How to Read the Result
The output is the three component series plus strength measures for the seasonal and trend components (each between 0 and 1, higher meaning that component explains more of the variation). On the airline series, an additive decomposition returns a seasonal strength of 0.76 and a trend strength of 0.97 — a strong trend with clear, moderately strong seasonality. Choose the model to match the series: additive when the seasonal swings are a roughly constant size, multiplicative when they grow with the level (as airline passengers do). Note that if you request a multiplicative model on a series with zero or negative values, the engine falls back to additive and warns, since multiplicative decomposition requires strictly positive data.

## Related Techniques
- *(use after)* `stl_decompose` for a more flexible, outlier-robust decomposition of the same series.
- *(alternatives)* `stl_decompose` (evolving seasonality, robust); `mstl_decompose` (multiple seasonal periods); `x13_seasonal_adjust` for official-statistics-grade seasonal adjustment.

## Technical Detail
Estimation is statsmodels `seasonal_decompose` (ratio-to-moving-average). The trend is a centered moving average; the seasonal component is the average detrended value for each position in the cycle, held fixed across cycles. The seasonal period is inferred from the data frequency when left blank. The trend endpoints are filled by extrapolation rather than dropped, so the trend and residual series cover the full sample. The additive/multiplicative choice is set by the model parameter, with an automatic fallback to additive (and a warning) if a multiplicative model is requested on non-positive data.
*Reference run:* airline_passengers.csv (144 monthly observations), additive model, Balanced — period 12 inferred, seasonal strength 0.76, trend strength 0.97.
