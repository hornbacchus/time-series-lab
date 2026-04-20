# LOESS Interpolation

## What It Does

LOESS (LOcally Estimated Scatterplot Smoothing) interpolation fills missing values and produces smooth estimates of the underlying signal by fitting **local weighted polynomial regressions** at each point. At each time step, it fits a low-degree polynomial to nearby observed data, with closer observations receiving higher weights. This produces a flexible, smooth curve that adapts to local patterns in the data without assuming a global parametric form.

## When to Use It

- You need to fill scattered missing values in a time series with a smooth estimate
- You want a nonparametric approach that does not assume a specific model (like ARIMA)
- The underlying signal is smooth and continuous, but the observed data is noisy or incomplete
- You need to estimate the series at arbitrary time points (not just the original observation times)
- You want a simple, well-understood method for signal extraction and gap filling

## Key Assumptions

- The underlying signal is a smooth, continuous function of time
- Missing values are surrounded by enough observed data for local regression
- The smoothing bandwidth (span) is appropriate for the data's variability
- The data is not dominated by seasonal or periodic components (handle those separately)
- Observations are approximately equally spaced (or the local regression handles irregular spacing)

## Outputs

- **Imputed values**: estimates at each missing time point
- **Smoothed series**: the LOESS fit at all time points (observed and missing)
- **Confidence bands**: pointwise confidence intervals around the smooth
- **Residuals**: differences between observed data and the LOESS fit
- **Effective degrees of freedom**: a measure of the fit complexity

## Technical Details

**LOESS procedure**: For each target point `t_0`:

1. **Select neighbors**: Identify the `q = floor(alpha * n)` nearest observed data points to `t_0`, where `alpha` (the span) is the fraction of data used in each local fit (typically 0.25 to 0.75).

2. **Compute weights**: Assign weights using the tricube function:
   `w_i = W(|t_i - t_0| / d_q)`
   where `d_q` is the distance to the q-th nearest neighbor and `W(u) = (1 - u^3)^3` for `0 <= u < 1`, 0 otherwise.

3. **Fit local polynomial**: Fit a weighted least-squares polynomial of degree `d` (typically d = 1 for linear or d = 2 for quadratic) to the neighboring points with weights `w_i`:
   `min_beta sum_i w_i (y_i - beta_0 - beta_1(t_i - t_0) - ... - beta_d(t_i - t_0)^d)^2`

4. **Evaluate**: The LOESS estimate at `t_0` is `y_hat(t_0) = beta_hat_0`.

**Interpolation of missing values**: Apply the LOESS procedure at each missing time point `t_0`. The local regression uses only the observed data points, and the weights ensure that nearby observed values contribute most. The result is a smooth estimate that naturally interpolates through gaps.

**Span (bandwidth) selection**:
- **Small span** (e.g., alpha = 0.1): captures rapid local changes but is sensitive to noise. May overfit.
- **Large span** (e.g., alpha = 0.75): produces a very smooth estimate but may miss local features.
- **Cross-validation (LOOCV)**: Minimize `sum_i (y_i - y_hat_{-i}(t_i))^2 / n`, where `y_hat_{-i}` is the LOESS fit at `t_i` leaving observation i out. This automatically balances smoothness and fidelity.
- **GCV (Generalized Cross-Validation)**: An efficient approximation to LOOCV.

**Robust LOESS**: Iteratively downweight observations with large residuals:
1. Fit standard LOESS to get residuals `e_i`.
2. Compute robustness weights: `r_i = B(|e_i| / (6 * median(|e_i|)))`, where `B(u) = (1-u^2)^2` for `|u| < 1`, else 0.
3. Refit LOESS using combined weights `w_i * r_i`.
4. Repeat 2-3 times.

This makes the interpolation resistant to outliers in the observed data.

**Confidence intervals**: Pointwise confidence intervals at each point are:
`y_hat(t_0) +/- t_{alpha/2, df} * sigma_hat * sqrt(l_0' (X' W X)^{-1} l_0)`
where `l_0 = (1, 0, ..., 0)'` extracts the intercept, X is the local design matrix, W is the diagonal weight matrix, and `sigma_hat` is the residual standard error.

**Effective degrees of freedom**: The LOESS smoother can be written as `y_hat = S y`, where S is the smoother (hat) matrix. The trace of S gives the effective degrees of freedom, measuring the complexity of the fit.

**Limitations for time series**:
- LOESS does not model autocorrelation explicitly. For series with strong AR dynamics, Kalman-based imputation may be more appropriate.
- Seasonal patterns should be removed before LOESS interpolation (or use STL which uses LOESS internally).
- At the edges of gaps, the fit relies on one-sided information and may be less accurate than in the middle.

## Interpretation

**Plain-Language Finding (Tier 1)** - imputed count and percent, LOESS fraction, gap count, global RMSE on observed. Explicitly notes that LOESS does NOT provide per-value uncertainty; validate longer-gap fills against auxiliary data.

**Technical Interpretation (Tier 2)** - span, robustifying iterations, no-per-value-SE disclosure, recommendation of Kalman imputation for uncertainty-aware longer-gap work.

**Caveats (Tier 3, conditional)**:
- Wide span (frac > 0.5) - LOESS degenerates to global polynomial fit.
- Long gap (> 5% of series) - exceeds local-fit scale, validate visually.
