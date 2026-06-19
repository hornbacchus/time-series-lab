## What It Does
The block bootstrap estimates the uncertainty of a statistic computed on a dependent (autocorrelated) series. Ordinary bootstrap resampling shuffles individual observations, which destroys the series' time dependence and gives wrong uncertainty estimates; the block bootstrap instead resamples *overlapping blocks* of consecutive observations, preserving the short-range correlation structure within each block. It returns confidence intervals for the series' mean, variance, and first-order autocorrelation.

## When to Use It
- You need a confidence interval for a statistic of an autocorrelated series (returns, rates, any time-dependent data).
- Ordinary bootstrap or analytic standard errors would be wrong because they assume independence.
- You want a distribution-free uncertainty estimate that respects the time dependence.
- Use the block bootstrap whenever the data are autocorrelated; ordinary bootstrap is fine only for independent observations.

## How to Read the Result
The output is the estimate and a confidence interval for each of the mean, the variance, and the first-order autocorrelation. On the SP500 daily returns, the mean's 95% interval is [0.002, 0.087] with a standard error of 0.022 — the interval accounts for the autocorrelation that an ordinary bootstrap would ignore (and which would otherwise understate the uncertainty). The block length is chosen automatically to match the series' persistence; a longer block preserves more dependence at the cost of fewer distinct resamples. The intervals for variance and autocorrelation are reported alongside the mean.

## Related Techniques
- *(use after)* report the interval alongside the point statistic in any analysis of dependent data.
- *(alternatives)* analytic standard errors for independent data; `rolling_origin_cv` for forecast-accuracy uncertainty rather than statistic uncertainty.

## Technical Detail
The method is the moving block bootstrap (numpy): overlapping blocks of consecutive observations are resampled with replacement and concatenated to form each bootstrap series, preserving short-range dependence. The block length defaults to an automatic choice of order `n^(1/3)` inflated for the series' persistence (capped at half the series length); the number of bootstrap replications is set by preset. The statistics computed are the mean, variance, and first-order autocorrelation — these are fixed, not selectable. Confidence intervals are the bootstrap percentiles.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), Balanced — automatic block length 15 (persistence-inflated), 1,000 replications; the mean's 95% confidence interval is [0.002, 0.087], standard error 0.022 (variance and first-order autocorrelation intervals are also reported).
