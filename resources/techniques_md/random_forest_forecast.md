# Random Forest Forecast

## What It Does

Random Forest Forecast uses an ensemble of decision trees trained on auto-generated lag features to produce time series forecasts. Each tree in the ensemble is trained on a bootstrap sample of the data with a random subset of features, and the final prediction is the average across all trees. The lag-based feature engineering transforms the time series forecasting problem into a supervised regression problem where past values predict future values.

## When to Use It

- You want a robust, non-parametric forecasting approach that requires minimal tuning
- The relationship between past and future values may be nonlinear
- You want feature importance scores to understand which lags drive the forecast
- The series does not have strong assumptions about its generating process
- You need a model that is resistant to overfitting (due to bagging and feature subsetting)
- You want prediction intervals via the distribution of individual tree predictions

## Key Assumptions

- Past values of the series contain predictive information for future values
- The lag structure adequately captures temporal dependencies
- The series values are numeric and bounded (extreme extrapolation is limited by the tree structure)
- Training data is representative of the patterns expected in the forecast period
- The relationship between lags and future values is relatively stable over time

## Outputs

- **Point forecasts** for the specified horizon
- **Prediction intervals** based on the distribution of individual tree predictions
- **Feature importance**: which lag features contribute most to the forecast
- **Model summary**: number of trees, max depth, out-of-bag score

## Technical Details

**Feature engineering**: The time series is transformed into a tabular dataset. For each time step `t`, the features are `[y_{t-1}, y_{t-2}, ..., y_{t-L}]` and the target is `y_t`, where `L` is the maximum lag. Additional features include rolling means and rolling standard deviations at multiple windows.

**Random Forest algorithm**: An ensemble of `B` decision trees, where each tree:
1. Draws a bootstrap sample (with replacement) of the training rows.
2. At each split, considers only `sqrt(p)` randomly selected features (where `p` is total features).
3. Splits on the feature and threshold that maximizes variance reduction.
4. Grows until a stopping criterion is met (max depth, min samples per leaf).

The final prediction is the mean of all tree predictions: `y_hat = (1/B) * sum_{b=1}^{B} T_b(x)`.

**Out-of-bag estimation**: Each tree's out-of-bag (OOB) samples provide an unbiased estimate of generalization error without needing a separate validation set.

**Multi-step forecasting**: Uses recursive (iterated) strategy: forecast `t+1`, feed it back as a lag feature, then forecast `t+2`, and so on. This can accumulate errors but preserves temporal coherence.

**Prediction intervals**: Computed from the empirical distribution of individual tree predictions. The interval `[q_{alpha/2}, q_{1-alpha/2}]` across tree outputs provides a non-parametric uncertainty estimate.

**Comparison**: Random Forest is more robust to overfitting than a single decision tree and requires less tuning than gradient boosting. However, it cannot extrapolate beyond the range of training data (tree-based limitation). For strongly trending series, detrending before modeling is recommended.

## Prediction Intervals — important caveat

Machine-learning forecasters do **not** come with native prediction-
interval machinery the way classical models (ARIMA, ETS, state-space)
do. When this technique returns a prediction interval, it is derived
empirically from in-sample residuals using a normal or t approximation —
NOT from a probabilistic forecast distribution.

Consequences:

- The interval width does **not** reflect model uncertainty
  (epistemic uncertainty about the learned parameters) — only
  aleatoric noise captured by the residual distribution.
- Coverage is not guaranteed. On out-of-sample data with regime
  shifts or distribution drift, empirical intervals typically
  under-cover.
- The interval is **symmetric** around the point forecast, which
  mis-represents asymmetric error distributions that ML models
  often produce.

For calibrated intervals on an ML forecast, wrap this technique with
**Conformal Prediction Intervals** — it takes a point-forecast model
and produces distribution-free intervals via a held-out calibration
set. See also **Quantile Regression Forecast** for directly
modeling conditional quantiles.
