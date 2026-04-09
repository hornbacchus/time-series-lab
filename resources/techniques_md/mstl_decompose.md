# MSTL Decomposition

## What It Does

MSTL (Multiple Seasonal-Trend decomposition using Loess) extends STL to handle time series with **multiple seasonal periods**. For example, hourly electricity data may exhibit both a daily pattern (period 24) and a weekly pattern (period 168). MSTL iteratively extracts each seasonal component from shortest to longest period, producing a single trend and one seasonal component per period.

## When to Use It

- Your data has more than one seasonal cycle (e.g., daily and weekly, or weekly and yearly)
- You are working with high-frequency data such as hourly, sub-daily, or daily observations
- You want to isolate individual seasonal effects to understand their relative importance
- STL is insufficient because it only handles a single seasonal period
- You need a decomposition that feeds into multi-seasonal forecasting models

## Key Assumptions

- The series is regularly spaced with no missing values
- Multiple seasonal periods are known in advance (e.g., 24 and 168 for hourly data)
- Seasonal components are additive (apply log transform for multiplicative behavior)
- Sufficient data spans at least two full cycles of the longest seasonal period

## Outputs

- **Trend component**: the long-term movement after all seasonal effects are removed
- **Multiple seasonal components**: one for each specified period, showing the repeating pattern at that frequency
- **Remainder**: the residual after removing trend and all seasonal components
- Summary of seasonal strength for each period

## Technical Details

MSTL works by iterating STL decompositions, extracting one seasonal component at a time while treating previously extracted components as known.

**Algorithm**:

1. Initialize: set all seasonal components to zero. The working series is `Y_t`.
2. For iteration `k = 1, 2, ..., K`:
   - For each seasonal period `m_i` (ordered from smallest to largest):
     a. Compute the partial series: `Y_t^{(i)} = Y_t - sum of all other seasonal components S_j (j != i) - T_t`.
     b. Apply STL to `Y_t^{(i)}` with period `m_i` to extract an updated seasonal component `S_i` and a trend.
   - After processing all seasonal periods, update the trend by applying STL (or Loess smoothing) to `Y_t - S_1 - S_2 - ... - S_p`.
3. Repeat until the components converge (changes between iterations fall below a threshold) or `K` iterations are reached.
4. Compute the remainder: `R_t = Y_t - T_t - S_1(t) - S_2(t) - ... - S_p(t)`.

**Parameter choices**:

- Each seasonal period `m_i` requires its own STL seasonal smoothing window `n_s^{(i)}`. Larger windows produce smoother, more stable seasonal patterns; smaller windows allow the seasonal shape to evolve over time.
- The trend smoother window `n_t` is typically set based on the longest seasonal period.
- Iteration count `K` is usually 2-5. Convergence is fast in practice.

**Ordering of periods**: Processing from shortest to longest period is standard. The shortest cycle is extracted first because it has the most observations per cycle, making it the most precisely estimated. Each subsequent extraction operates on a series that has already had shorter cycles removed.

**Seasonal strength measure**: For each component `S_i`, the relative strength can be quantified as `1 - Var(R) / Var(S_i + R)`, where values close to 1 indicate a strong seasonal pattern and values near 0 indicate weak or negligible seasonality at that period.

**Comparison with STL**: STL handles one period; MSTL handles multiple. If you only have one seasonal period, MSTL reduces to STL. MSTL is particularly valuable for sub-daily data where multiple overlapping cycles are common.
