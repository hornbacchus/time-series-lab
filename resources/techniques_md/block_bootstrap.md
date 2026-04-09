# Block Bootstrap

## What It Does

The block bootstrap resamples **contiguous blocks** of observations from a time series to generate new pseudo-series that preserve the temporal dependence structure. Unlike the standard (iid) bootstrap which resamples individual observations, the block bootstrap respects the autocorrelation in the data, making it valid for constructing confidence intervals, prediction intervals, and hypothesis tests for time series statistics.

## When to Use It

- You need confidence intervals for a time series statistic but the analytical formula is unavailable or unreliable
- You want to assess the uncertainty of forecast accuracy metrics from rolling origin evaluation
- The distributional assumptions required for analytical inference (e.g., normality) are questionable
- You need to generate synthetic time series for simulation or stress testing
- You want prediction intervals that do not rely on Gaussian error assumptions

## Key Assumptions

- The time series is stationary (or locally stationary within each block)
- The block length is long enough to capture the dependence structure but short enough to allow sufficient resampling
- The statistic of interest can be meaningfully computed on the resampled series
- The resampled series is a reasonable approximation to new draws from the data-generating process
- The number of bootstrap replications is large enough for stable inference

## Outputs

- **Bootstrap distribution**: the empirical distribution of the statistic of interest across replications
- **Confidence intervals**: percentile-based or bias-corrected intervals for the statistic
- **Standard error**: the bootstrap estimate of the standard deviation of the statistic
- **Bias estimate**: the difference between the bootstrap mean and the observed statistic
- **Prediction intervals**: for forecasts, by resampling residuals or fitted errors

## Technical Details

**Non-overlapping Block Bootstrap (NBB)**:

1. Choose block length `l`.
2. Divide the series into `k = floor(n/l)` non-overlapping blocks: `B_1 = (y_1, ..., y_l)`, `B_2 = (y_{l+1}, ..., y_{2l})`, etc.
3. Resample k blocks with replacement and concatenate to form a bootstrap series of length `k * l`.
4. Compute the statistic of interest on the bootstrap series.
5. Repeat B times to build the bootstrap distribution.

**Moving Block Bootstrap (MBB)** (Kunsch, 1989; Liu and Singh, 1992):

1. Define all possible overlapping blocks of length l: `B_i = (y_i, y_{i+1}, ..., y_{i+l-1})` for i = 1, ..., n-l+1.
2. Randomly select `k = ceil(n/l)` blocks with replacement.
3. Concatenate and truncate to length n.
4. Compute the statistic; repeat B times.

MBB uses more blocks than NBB, improving efficiency.

**Stationary Bootstrap** (Politis and Romano, 1994):

Instead of a fixed block length, each block has a random length drawn from a geometric distribution with mean l:
- Start at a random time index.
- With probability `1/l`, start a new block at a random location; with probability `1 - 1/l`, extend the current block.

This ensures the resampled series is stationary (unlike MBB, which can have discontinuities at block junctions).

**Block length selection**: Critical for performance. Too short: dependence is not preserved, bootstrap is inconsistent. Too long: too few distinct blocks, high variance.

Methods for selecting l:
- **Rule of thumb**: `l = n^{1/3}` (optimal rate for many statistics).
- **Politis-White (2004) automatic selection**: Estimates the spectral density at frequency zero and uses it to determine the optimal block length.
- **Cross-validation**: Try multiple block lengths and select the one that minimizes the bootstrap variance.

**Bootstrap for prediction intervals**:

1. Fit the forecasting model to the original series.
2. Compute in-sample residuals `e_t = y_t - y_hat_t`.
3. For each bootstrap replication:
   a. Resample residuals using the block bootstrap (preserving residual autocorrelation).
   b. Generate a new series by adding resampled residuals to the fitted values.
   c. Refit the model and produce forecasts.
4. The quantiles of the bootstrap forecast distribution give prediction intervals.

**Sieve bootstrap** (alternative approach): Fit an AR(p) model (with p selected by AIC), resample the residuals using the iid bootstrap (since AR residuals are approximately iid), and generate new series from the AR model with resampled innovations. This parameterically captures the dependence and allows iid resampling of residuals.

**Number of replications B**: At least 1,000 for confidence intervals, 5,000-10,000 for accurate tail probabilities. Use the Monte Carlo error `SE_MC = s / sqrt(B)` (where s is the bootstrap standard deviation) to assess whether B is large enough.
