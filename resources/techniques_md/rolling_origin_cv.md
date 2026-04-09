# Rolling Origin Cross-Validation

## What It Does

Rolling origin cross-validation (also called time series cross-validation or walk-forward validation) evaluates forecast model performance by repeatedly **expanding or sliding the training set** and testing on the next observation(s). Unlike standard k-fold CV which randomly splits data, it respects the temporal order -- the model is always trained on past data and tested on future data, mimicking real-world forecasting conditions.

## When to Use It

- You want to evaluate forecast accuracy in a way that reflects real-world sequential prediction
- You need to compare multiple forecasting models or parameter settings on the same data
- Standard train/test splits use too little test data or are sensitive to the split point
- You want to understand how forecast accuracy varies over time (not just a single number)
- You are selecting hyperparameters (e.g., ARIMA orders, smoothing parameters) for a forecasting model

## Key Assumptions

- The temporal order of observations matters and must be preserved
- The forecasting model can be retrained or updated as the training window expands
- The series is long enough to provide multiple training/test splits
- The evaluation metric chosen is appropriate for the forecasting task
- The computational cost of refitting the model many times is acceptable

## Outputs

- **Forecast errors at each origin**: the error for each test period from each training origin
- **Average forecast accuracy**: mean error metrics (MAE, RMSE, MAPE, etc.) across all origins
- **Error trajectory**: how forecast accuracy changes as more data becomes available
- **Model ranking**: comparison of multiple models across all origins
- **Prediction interval coverage**: how often actual values fall within the predicted intervals

## Technical Details

**Expanding window procedure**: For a series `y_1, ..., y_T` with minimum training size `w` and forecast horizon `h`:

For i = 0, 1, ..., T - w - h:
1. Training set: `y_1, ..., y_{w+i}`
2. Fit the model on the training set.
3. Produce h-step-ahead forecasts: `y_hat_{w+i+1}, ..., y_hat_{w+i+h}`
4. Compute errors: `e_{w+i+j} = y_{w+i+j} - y_hat_{w+i+j}` for j = 1, ..., h.

This produces T - w - h + 1 forecast origins, each generating h forecast errors.

**Sliding window procedure**: Instead of expanding from a fixed start:
1. Training set: `y_{i+1}, ..., y_{w+i}` (fixed window of length w)
2. Everything else is the same.

Sliding windows prevent very old data from influencing the model and can better capture non-stationary behavior.

**Error metrics computed across origins**:

- **MAE**: `(1/n) sum |e_t|` -- robust to outliers, same units as data
- **RMSE**: `sqrt((1/n) sum e_t^2)` -- penalizes large errors more
- **MAPE**: `(100/n) sum |e_t / y_t|` -- percentage error, scale-independent
- **sMAPE**: `(200/n) sum |e_t| / (|y_t| + |y_hat_t|)` -- symmetric percentage error
- **MASE**: `MAE / MAE_naive` -- scaled by the naive (seasonal random walk) in-sample MAE

**Multi-step evaluation**: For h-step-ahead forecasts, errors can be evaluated at each horizon separately (MAE at h=1, h=2, etc.) or averaged across horizons. Horizon-specific accuracy reveals how quickly forecast quality degrades.

**Computational considerations**:
- Refitting complex models (ARIMA, neural networks) at each origin is expensive.
- For ARIMA: refit only if the model order might change; otherwise, update parameters incrementally.
- For ETS: full re-optimization at each origin is standard but can use warm starts.
- Gap between origins: Instead of rolling forward one observation at a time, skip every k observations to reduce computation while maintaining temporal coverage.

**Initial training size w**: Should be large enough for the model to estimate parameters reliably. For seasonal models, at least 2-3 complete seasons. For non-seasonal, at least 30-50 observations.

**Statistical comparison**: To test whether Model A is significantly better than Model B, use the Diebold-Mariano test on the forecast error differences:

`DM = d_bar / sqrt(Var(d_bar))`, where `d_t = L(e_t^A) - L(e_t^B)` and L is a loss function (e.g., squared error). Under H0 (equal accuracy), DM is approximately standard normal for large samples.

**Pitfalls**:
- Overlapping forecast horizons create correlated errors, complicating statistical comparison.
- If model selection is performed within the CV loop, it must be re-done at each origin to avoid lookahead bias.
- Very few origins (short series) give unstable accuracy estimates.
