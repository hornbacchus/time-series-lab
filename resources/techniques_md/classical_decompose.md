# Classical Decomposition

## What It Does

Classical decomposition separates a time series into **trend-cycle**, **seasonal**, and **irregular** (remainder) components using moving averages. It is the simplest and oldest decomposition approach, offering either an additive model (Y = T + S + R) or a multiplicative model (Y = T * S * R).

## When to Use It

- You need a quick, interpretable decomposition as a first look at your data
- The seasonal pattern is stable and does not change over time
- You want to understand the general trend direction after removing seasonality
- Your audience prefers straightforward, easy-to-explain methods
- You are working with data that has no extreme outliers

## Key Assumptions

- The seasonal period is known and fixed
- The seasonal pattern repeats identically from one cycle to the next
- Additive model: seasonal fluctuations are constant in magnitude regardless of the level
- Multiplicative model: seasonal fluctuations scale proportionally with the level
- The series is long enough to estimate at least two full seasonal cycles

## Outputs

- **Trend-cycle component**: smoothed series showing the long-run movement
- **Seasonal indices**: one value per position in the seasonal cycle (e.g., 12 values for monthly data)
- **Remainder**: the residual after removing trend and seasonal effects
- Decomposition plot with all components

## Technical Details

**Step 1 -- Trend estimation**: Apply a centered moving average of order `m` (the seasonal period) to the original series. If `m` is even, a 2x`m` moving average is used (i.e., a moving average of order `m` followed by a moving average of order 2) to maintain symmetry. This yields the trend-cycle estimate `T_t`.

For additive decomposition:

**Step 2 -- Detrend**: Compute `Y_t - T_t` for all time points where the trend is defined.

**Step 3 -- Seasonal indices**: For each seasonal position `j` (e.g., January, February, ...), average the detrended values across all years: `S_j = mean(Y_t - T_t)` for all `t` corresponding to position `j`. Adjust the indices so they sum to zero: `S_j' = S_j - mean(S_1, ..., S_m)`.

**Step 4 -- Remainder**: `R_t = Y_t - T_t - S_t`.

For multiplicative decomposition:

**Step 2**: Compute `Y_t / T_t`.

**Step 3**: `S_j = mean(Y_t / T_t)` for position `j`, adjusted so indices average to 1.0: `S_j' = S_j * m / sum(S_1, ..., S_m)`.

**Step 4**: `R_t = Y_t / (T_t * S_t)`.

**Limitations of the classical approach**:
- The moving average loses `floor(m/2)` observations at each end of the series, so the trend cannot be estimated for the first and last few periods.
- Seasonal indices are fixed across the entire series, so the method cannot capture evolving seasonality.
- The trend estimate can be distorted by outliers since the moving average assigns equal weight to all observations in the window.
- There is no robustness mechanism; a single extreme value affects the trend and consequently the seasonal and remainder estimates.

**Choosing additive vs. multiplicative**: If the magnitude of seasonal swings grows with the level of the series, use multiplicative. If seasonal swings remain constant, use additive. Alternatively, apply a log transform and use the additive model, which is equivalent to a multiplicative decomposition on the original scale.
