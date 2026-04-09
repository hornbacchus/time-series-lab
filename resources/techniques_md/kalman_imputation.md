# Kalman Imputation

## What It Does

Kalman imputation uses the **state space framework** to fill in missing values in a time series by treating each missing observation as an unobserved state. The Kalman filter propagates forward through gaps using the model dynamics, and the Kalman smoother refines estimates using data from both sides of the gap. This produces optimal (minimum variance) estimates of missing values along with their uncertainty, fully accounting for the temporal structure of the data.

## When to Use It

- Your time series has missing values (gaps, dropouts, sensor failures) and you need a complete series
- You want imputed values that respect the autocorrelation, trend, and seasonal structure of the data
- You need uncertainty estimates for the imputed values (not just point estimates)
- The missingness pattern is irregular (scattered missing values, varying gap lengths)
- You are working with multivariate data where cross-series correlations help fill gaps

## Key Assumptions

- A suitable state space model can be specified for the data (e.g., local level, structural time series, ARIMA in state space form)
- The data is missing at random or missing completely at random (the missingness does not depend on the unobserved values)
- The state space model parameters are known or can be estimated from the available data
- The model is correctly specified (trend, seasonal, and noise components are appropriate)
- Gaps are not so long that the model cannot maintain meaningful state estimates

## Outputs

- **Imputed values**: point estimates for each missing observation
- **Imputation uncertainty**: the variance (or confidence interval) for each imputed value
- **Complete series**: the original data with missing values filled in
- **State estimates**: the full smoothed state trajectory, including through gaps
- **Model diagnostics**: residual analysis on the observed portions to validate the model

## Technical Details

**How the Kalman filter handles missing data**: In the standard Kalman filter, when an observation `y_t` is missing:

1. **Predict step**: Same as usual. Propagate the state: `x_t|t-1 = F x_{t-1|t-1}` and `P_t|t-1 = F P_{t-1|t-1} F' + Q`.
2. **Update step**: Skip the measurement update entirely. Set `x_t|t = x_t|t-1` and `P_t|t = P_t|t-1`. The state estimate remains at its predicted value, and uncertainty grows because no information was received.

For the smoother, the backward pass proceeds as usual, incorporating information from future observed values to improve the estimate during the gap.

**Effect on uncertainty**: During a gap, the filtered state covariance `P_t|t` grows with each missing observation because no new information is incorporated. The smoother reduces this uncertainty by using data after the gap. The imputation variance is smallest at the edges of a gap and largest in the middle.

**State space formulation for common models**:

**Local level model**: `y_t = mu_t + e_t`, `mu_t = mu_{t-1} + eta_t`. Missing y_t means the level `mu_t` drifts as a random walk through the gap, with increasing uncertainty.

**ARIMA as state space**: Any ARIMA(p,d,q) model can be written in state space form, and the Kalman filter/smoother automatically handles missing data. For ARIMA(1,1,1) with missing data, the state includes the differenced and undifferenced levels, and the smoother interpolates through gaps using the AR and MA dynamics.

**Structural time series (BSM)**: With trend, seasonal, and irregular components, the Kalman smoother imputes missing values using both the local trend extrapolation and the seasonal pattern. If a value is missing for a particular month, the seasonal component from previous years provides information.

**EM algorithm for parameter estimation with missing data**:

When model parameters are unknown, the EM algorithm iterates:
- **E-step**: Run the Kalman smoother to compute expected sufficient statistics, treating missing data as latent variables.
- **M-step**: Update model parameters (variances, AR coefficients) using the smoothed estimates.

This jointly estimates the parameters and imputes the missing values.

**Multivariate imputation**: For a vector of time series, the state space model can be multivariate. If series A has an observation at time t but series B does not, the Kalman filter uses the observation from A (and the cross-series correlations in the model) to improve the estimate of B's missing value.

**Practical considerations**:
- Very long gaps (relative to the autocorrelation time) produce imputed values that revert to the unconditional mean with wide uncertainty bands.
- Model misspecification (e.g., wrong seasonal period) leads to biased imputations.
- Validate by artificially removing known observations and comparing imputed vs. true values.
- For data with many missing values, the EM algorithm may converge slowly. Good initial parameter estimates help.
