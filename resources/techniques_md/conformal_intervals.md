# Conformal Prediction Intervals

## What It Does

Conformal prediction constructs **distribution-free prediction intervals** with guaranteed finite-sample coverage. Unlike traditional prediction intervals that rely on assumptions about the error distribution (normality, specific parametric form), conformal intervals achieve valid coverage under minimal assumptions -- primarily exchangeability of the data. Applied to time series via adaptive methods, they provide reliable prediction intervals even when the model is misspecified.

## When to Use It

- You want prediction intervals with guaranteed coverage, regardless of the underlying distribution
- Model-based prediction intervals are too narrow (undercoverage) or too wide (overcoverage)
- You are using a complex forecasting model (machine learning) that lacks built-in interval estimation
- The error distribution is non-Gaussian, skewed, or heavy-tailed
- You need robust prediction intervals that adapt to changing forecast difficulty

## Key Assumptions

- For standard conformal: the data (or residuals) are exchangeable (a weaker condition than iid)
- For time series conformal: the method accounts for temporal dependence through adaptive calibration
- A base forecaster produces point predictions (any method -- ARIMA, ML, neural nets)
- The calibration set is representative of future prediction difficulty
- The non-conformity scores (residuals) capture the model's prediction quality

## Outputs

- **Prediction intervals** at the specified confidence level (e.g., 90%, 95%) for each forecast
- **Coverage analysis**: empirical coverage rate compared to the nominal level
- **Interval widths**: showing how uncertainty varies over time
- **Adaptive adjustment factors**: how the method adjusts interval width in response to recent errors
- **Non-conformity scores**: the residuals used to calibrate the intervals

## Technical Details

**Basic split conformal prediction**:

1. Split data into training set and calibration set.
2. Fit the model on training data, producing point forecasts.
3. Compute non-conformity scores on calibration data: `R_i = |y_i - y_hat_i|` (absolute residual).
4. For a new prediction at time T+1 with coverage level `1-alpha`:
   - Take the `ceil((1-alpha)(n_cal + 1))`-th smallest calibration score as the quantile `Q`.
   - Prediction interval: `[y_hat_{T+1} - Q, y_hat_{T+1} + Q]`.

**Coverage guarantee**: If the calibration residuals and the new residual are exchangeable, then `P(y_{T+1} in interval) >= 1 - alpha`. This holds regardless of the model, the distribution, or the sample size.

**Adaptive Conformal Inference (ACI)** for time series (Gibbs and Candes, 2021):

Standard conformal assumes exchangeability, which fails for time series. ACI adapts by dynamically adjusting the significance level:

`alpha_t = alpha + gamma * (err_{t-1} - alpha)`

where `err_{t-1} = I(y_{t-1} not in interval_{t-1})` indicates whether the previous interval missed, and gamma > 0 is a learning rate. After a miss, alpha_t increases (making intervals wider); after a hit, alpha_t decreases.

The prediction interval at time t uses the adjusted alpha_t:
- Compute `Q_t = quantile_{1-alpha_t}` of recent non-conformity scores.
- Interval: `[y_hat_t - Q_t, y_hat_t + Q_t]`.

**Conformalized Quantile Regression (CQR)**:

Instead of symmetric intervals around a point forecast, use quantile regression to produce asymmetric intervals:

1. Train quantile regressors for levels `alpha/2` and `1-alpha/2`.
2. Compute non-conformity scores: `R_i = max(q_{alpha/2}(x_i) - y_i, y_i - q_{1-alpha/2}(x_i))`.
3. Find the quantile Q of the calibration scores.
4. Interval: `[q_{alpha/2}(x_{new}) - Q, q_{1-alpha/2}(x_{new}) + Q]`.

CQR produces intervals that are narrower where uncertainty is low and wider where it is high, adapting to heteroskedasticity.

**EnbPI (Ensemble Batch Prediction Intervals)**:

Designed specifically for time series:
1. Use an ensemble of models trained on different bootstrap samples.
2. Compute sequential residuals using leave-one-out-style predictions.
3. Calibrate intervals using the most recent residuals (a sliding window).
4. Intervals adapt to non-stationarity because the calibration window reflects recent prediction difficulty.

**Practical considerations**:
- Longer calibration windows produce more stable but less adaptive intervals.
- The learning rate gamma in ACI controls responsiveness: larger values adapt faster but are noisier.
- Conformal intervals are always at least as wide as the empirical quantile of recent residuals, which can be conservative if the model is very good.
- Any base forecaster can be used -- the conformal wrapper only adjusts the intervals, not the point predictions.

## Interpretation

**Plain-Language Finding (Tier 1)** - verdict-free (per Prompt C1 Decision B). Distribution-free N% prediction intervals with average width, optional comparison to parametric baseline when wrapper exposes it.

**Technical Interpretation (Tier 2)** - split-conformal with base model, train/calibration split, conformal quantile, exchangeability disclosure (time-series caveat).

**Caveats (Tier 3, conditional)**:
- Calibration-residual lag-1 ACF > 0.3 - exchangeability violated, nominal coverage overstates true.
- Interval width >= parametric baseline - conformal adds no tightness.
