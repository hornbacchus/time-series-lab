# LightGBM Forecast

LightGBM (Light Gradient Boosting Machine) is a high-performance gradient boosting framework developed by Microsoft. It uses histogram-based splitting and leaf-wise tree growth, making it significantly faster than traditional boosting methods while often achieving comparable or better accuracy.

## How It Works

The technique constructs a supervised learning problem from the time series by creating lag features (past values), rolling statistics (moving averages and standard deviations), difference features, and a normalized time index. LightGBM then learns a mapping from these features to the next value. Forecasts are produced recursively: each predicted value is fed back as input for the next step.

LightGBM differs from XGBoost in its tree-building strategy: it grows trees leaf-wise (choosing the leaf with the maximum delta loss) rather than level-wise. This often produces deeper, more accurate trees with fewer nodes. The `num_leaves` parameter controls complexity directly.

## When to Use

- **Forecasting with nonlinear patterns** that linear models (ARIMA, ETS) struggle to capture
- **Large datasets** where training speed matters — LightGBM is typically 2-10x faster than XGBoost
- **Feature-rich settings** where lag structure and rolling statistics are informative
- **Quick benchmarking** against classical and deep learning methods

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `horizon` | 12 | Number of steps to forecast ahead |
| `max_lag` | 24 | Number of lag features to create |
| `n_estimators` | 300 | Number of boosting rounds |
| `learning_rate` | 0.05 | Step size shrinkage to prevent overfitting |
| `max_depth` | 6 | Maximum tree depth |
| `num_leaves` | 31 | Maximum leaves per tree (LightGBM-specific) |

## Output Tables

- **Forecast**: Step-ahead predictions for the specified horizon
- **Feature Importance**: Top features ranked by contribution to predictions
- **Model Summary**: Training/CV metrics, hyperparameters, and backend used

## Dependencies

Uses the `lightgbm` library when available. Falls back to scikit-learn's `GradientBoostingRegressor` if LightGBM is not installed. Install with `pip install lightgbm`.

## Presets

- **Fast**: 100 trees, 6 lags, depth 4, 15 leaves
- **Balanced**: 300 trees, 12 lags, depth 6, 31 leaves
- **Thorough**: 600 trees, 24 lags, depth 8, 63 leaves

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
