# STL-ESD Anomaly Detection

## What It Does

STL-ESD combines STL decomposition with the Generalized ESD (Extreme Studentized Deviate) test to detect **anomalies in seasonal time series**. First, STL removes the trend and seasonal components, isolating the remainder. Then, the ESD test identifies observations in the remainder that are statistically extreme, flagging them as anomalies. This approach is robust because it accounts for seasonal patterns that might otherwise be mistaken for anomalies.

## When to Use It

- You need to detect anomalies in time series with seasonal patterns
- Simple threshold-based methods flag seasonal peaks or troughs as false anomalies
- You want a statistical test for outliers rather than an arbitrary cutoff
- Your data has a known seasonal period (daily, weekly, monthly)
- You are monitoring metrics like web traffic, sales, or sensor data where seasonality is expected

## Key Assumptions

- The seasonal pattern is well captured by STL (regular period, at least two full cycles)
- After removing trend and seasonality, the remainder is approximately normally distributed
- Anomalies are point anomalies (individual unusual values) rather than sustained level shifts
- The maximum number of anomalies is a small fraction of the total observations
- The STL decomposition is not unduly influenced by the anomalies (robust STL helps here)

## Outputs

- **Anomaly flags**: which observations are detected as anomalous
- **Anomaly scores**: how extreme each flagged observation is (the ESD statistic value)
- **Remainder series**: the STL remainder with anomalies highlighted
- **Decomposition components**: trend, seasonal, and remainder from STL
- **Critical values**: the ESD test thresholds at the chosen significance level

## Technical Details

**Step 1 -- STL Decomposition**: Apply STL to decompose the series `Y_t = T_t + S_t + R_t` into trend, seasonal, and remainder components. Use the robust version of STL (with outer loop iterations) to minimize the influence of outliers on the trend and seasonal estimates.

**Step 2 -- Median Adjustment**: Compute the median of the remainder: `R_t' = R_t - median(R_t)`. This centers the remainder at zero and is more robust than using the mean.

**Step 3 -- Generalized ESD Test**: The Generalized ESD test (Rosner, 1983) detects up to k outliers in a sample, handling the masking problem where multiple outliers can prevent detection of each other.

**ESD algorithm** for testing up to k_max outliers:

For i = 1, 2, ..., k_max:
1. Compute the test statistic: `G_i = max|R_j' - R_bar| / s`, where `R_bar` and `s` are the mean and standard deviation of the current data.
2. Remove the observation with the largest `|R_j' - R_bar|` from the data.
3. Compute the critical value: `lambda_i = t_{p, n-i-1} * (n-i) / sqrt((n-i-1+t^2_{p,n-i-1}) * (n-i+1))`, where `t_{p,m}` is the t-distribution quantile with `p = 1 - alpha / (2*(n-i+1))` and m degrees of freedom.

The number of anomalies is the largest i such that `G_i > lambda_i`.

**Choosing k_max**: The maximum number of anomalies to test for. Typically set to a percentage of the total observations (e.g., 5-10% for hourly data). Setting k_max too low may miss anomalies; too high does not cause harm but increases computation.

**Direction**: The test can be configured to detect:
- **Both directions**: unusually high and unusually low values
- **Upper only**: only unusually high values (e.g., spike detection)
- **Lower only**: only unusually low values (e.g., dropout detection)

For one-sided tests, modify the ESD statistic to `G_i = max(R_j' - R_bar) / s` (upper) or `G_i = max(R_bar - R_j') / s` (lower).

**Significance level alpha**: Controls the false positive rate. At alpha = 0.05, approximately 5% of non-anomalous observations will be incorrectly flagged. More conservative choices (alpha = 0.01) reduce false positives at the cost of missed anomalies.

**Handling multiple seasonalities**: For data with multiple seasonal periods (e.g., hourly data with daily and weekly patterns), use MSTL instead of STL in the first step, then apply ESD to the remainder.

**Practical considerations**:
- The ESD test assumes approximate normality of the remainder. For highly skewed data, apply a Box-Cox transformation before STL.
- Very long seasonal periods (e.g., 365 for daily data with yearly seasonality) require correspondingly long series.
- For real-time monitoring, apply STL-ESD to a rolling window.

## Interpretation

**Plain-Language Finding (Tier 1)** - anomaly count, rate (%), alpha threshold, upward/downward split, most extreme anomaly with z-score on STL-adjusted remainders.

**Technical Interpretation (Tier 2)** - STL-decomposed series with generalized-ESD test on the remainder, per-iteration test statistics in data tables, alpha trade-off framing.

**Caveats (Tier 3, conditional)**:
- High anomaly rate (> 15%) - threshold too loose or regime shift being misclassified.
- All anomalies in one direction - series may have heteroscedasticity, not discrete outliers.
