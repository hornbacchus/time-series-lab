# Robust Estimators

## What It Does

Robust estimators provide reliable statistical summaries and model fits when the data contains **outliers, heavy-tailed distributions, or other departures from ideal assumptions**. They limit the influence of any single observation on the result, ensuring that a few contaminated data points do not distort the analysis. For time series, this includes robust trend estimation, robust autocovariance, and robust regression for forecasting models.

## When to Use It

- Your data contains outliers or extreme values that distort standard methods
- You suspect the error distribution is heavy-tailed (common in financial data)
- Standard least-squares estimates are unreliable because a few observations have excessive influence
- You want estimates that degrade gracefully when data quality is poor
- You need a preprocessing step to identify and handle outliers before applying standard methods

## Key Assumptions

- The majority of observations follow the assumed model (the "bulk" of the data is well-behaved)
- The proportion of outliers is below the estimator's breakdown point
- Outliers are not systematic (they do not represent a separate, important process)
- The data is informative enough that the robust estimator has sufficient efficiency
- The loss of statistical efficiency from using robust methods is acceptable

## Outputs

- **Robust parameter estimates**: model coefficients with reduced outlier influence
- **Robust standard errors**: reflecting the true precision after downweighting outliers
- **Outlier identification**: observations with low robustness weights (flagged as potential outliers)
- **Robustness weights**: showing how much each observation contributes to the estimate
- **Comparison with standard estimates**: highlighting the impact of outliers on non-robust methods

## Technical Details

**Robust location estimators** (replacing the mean):

- **Median**: The simplest robust estimator. Breakdown point = 50% (up to half the data can be outliers).
- **Trimmed mean**: Remove the largest and smallest k% of observations, average the rest. Breakdown point = k%.
- **Winsorized mean**: Replace extreme observations with the nearest non-extreme value, then average.
- **Huber estimator**: Minimize `sum rho_H(r_i)` where `rho_H(r) = r^2/2` for `|r| <= c` and `c|r| - c^2/2` for `|r| > c`. The tuning constant c (typically 1.345) controls the efficiency-robustness tradeoff.

**Robust scale estimators** (replacing the standard deviation):

- **MAD (Median Absolute Deviation)**: `MAD = 1.4826 * median(|y_i - median(y)|)`. The factor 1.4826 makes it consistent for the Gaussian distribution. Breakdown point = 50%.
- **Qn estimator**: Based on pairwise differences. More efficient than MAD.
- **Sn estimator**: `Sn = 1.1926 * median_i(median_j(|y_i - y_j|))`. High breakdown and good efficiency.

**M-estimators** (robust regression):

Replace OLS minimization of `sum e_i^2` with `min_beta sum rho(e_i / sigma_hat)`, where `rho` is a bounded loss function.

Common choices:
- **Huber**: `rho(r) = r^2/2` for `|r| <= c`, else `c|r| - c^2/2`. Linear growth in tails.
- **Tukey bisquare (biweight)**: `rho(r) = (c^2/6)(1 - (1-(r/c)^2)^3)` for `|r| <= c`, else `c^2/6`. Completely rejects observations beyond c (zero influence).

The M-estimator solves `sum psi(e_i / sigma_hat) x_i = 0`, where `psi = rho'` is the influence function. Iteratively Reweighted Least Squares (IRLS):
1. Start with OLS or median regression.
2. Compute residuals `e_i` and weights `w_i = psi(e_i / sigma_hat) / (e_i / sigma_hat)`.
3. Run weighted least squares with weights `w_i`.
4. Repeat until convergence.

**MM-estimators**: Combine a high-breakdown initial estimator (S-estimator, breakdown = 50%) with an efficient M-estimator started at the S-estimate. This achieves both high breakdown point (resistant to many outliers) and high efficiency (close to OLS when no outliers are present).

**Robust autocovariance**: Replace the standard autocovariance `gamma(h) = (1/n) sum (y_t - y_bar)(y_{t+h} - y_bar)` with a robust version using robust scale estimators:

`gamma_{rob}(h) = (1/4)[Q_n(y_t + y_{t+h})^2 - Q_n(y_t - y_{t+h})^2]`

This produces an ACF that is not distorted by outliers, enabling correct ARIMA order identification.

**Influence function**: Measures the sensitivity of an estimator to an infinitesimal contamination at value y: `IF(y; T, F) = lim_{epsilon->0} (T((1-epsilon)F + epsilon delta_y) - T(F)) / epsilon`. Bounded influence functions characterize robust estimators.

**Breakdown point**: The maximum fraction of contaminated observations that the estimator can handle before giving an arbitrary result. The median has breakdown 50% (highest possible); OLS has breakdown 1/n (a single outlier can destroy it).

**Efficiency**: The relative precision of the robust estimator compared to OLS under ideal (Gaussian) conditions. Huber with c=1.345: 95% efficiency. Tukey bisquare with c=4.685: 95% efficiency. The small efficiency loss is the "insurance premium" for robustness.

## Interpretation

**Plain-Language Finding (Tier 1)** - univariate location/scale summary. Median vs mean (gap indicates skew/outliers), std vs MAD-based scale with ratio band (well-behaved / mild / heavy / very heavy).

**Technical Interpretation (Tier 2)** - four location estimators (mean, median, trimmed, Huber/winsorized) and four scale estimators (std, MAD, IQR, Qn). Ratio-based interpretation framing.

**Caveats (Tier 3, conditional)**:
- Very heavy tails (Std/MAD > 3) - classical methods unreliable.
- Well-behaved (ratio < 1.3, small mean-median gap) - robust and classical agree.
