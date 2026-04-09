# Gradient Boosting Forecast

## What It Does

Gradient boosting builds a powerful forecasting model by **sequentially combining many weak learners** (typically decision trees), where each new tree corrects the errors of the ensemble so far. Applied to time series, it treats forecasting as a supervised learning problem: lagged values, calendar features, and other engineered features serve as inputs, and the target is the future value. Methods like XGBoost, LightGBM, and CatBoost are widely used for this purpose.

## When to Use It

- You have rich feature information (calendar variables, holidays, external regressors) alongside the time series
- The relationship between features and the target is complex and potentially nonlinear
- You need a flexible model that can capture interactions between features automatically
- You are competing in forecasting competitions (gradient boosting is consistently among top methods)
- You have enough data to train a feature-based model (hundreds to thousands of observations)

## Key Assumptions

- The forecasting problem can be framed as a supervised regression (features -> target)
- Relevant features (lags, rolling statistics, calendar variables) can be engineered from the data
- The relationship between features and target is stable enough over time to learn from history
- The training data is representative of the patterns in the forecast period
- Overfitting is controlled through regularization, early stopping, or cross-validation

## Outputs

- **Point forecasts** for the specified horizon
- **Feature importance scores**: which features contribute most to the predictions
- **Prediction intervals**: via quantile regression, conformal prediction, or bootstrapping
- **Partial dependence plots**: showing the marginal effect of individual features
- **Out-of-sample accuracy metrics** from time series cross-validation

## Technical Details

**Gradient boosting algorithm**: Given training data `{(x_i, y_i)}`, the model builds an additive ensemble:

`F_M(x) = F_0(x) + sum_{m=1}^{M} nu * h_m(x)`

where `F_0` is an initial estimate (e.g., the mean), `h_m` are weak learners (shallow decision trees), `nu` is the learning rate (shrinkage), and M is the number of boosting iterations.

At each iteration m:
1. Compute pseudo-residuals: `r_{i,m} = -dL(y_i, F_{m-1}(x_i))/dF` (the negative gradient of the loss function).
2. Fit a decision tree `h_m` to the pseudo-residuals.
3. Update: `F_m(x) = F_{m-1}(x) + nu * h_m(x)`.

For squared error loss: `r_{i,m} = y_i - F_{m-1}(x_i)` (the actual residuals).

**Feature engineering for time series**:

- **Lag features**: `y_{t-1}, y_{t-2}, ..., y_{t-p}` (autoregressive inputs)
- **Rolling statistics**: rolling mean, std, min, max over windows of different sizes
- **Calendar features**: day of week, month, quarter, year, day of year, week of year
- **Holiday indicators**: binary flags for known holidays
- **Fourier features**: `sin(2*pi*k*t/period)`, `cos(2*pi*k*t/period)` for k = 1, ..., K to capture seasonality
- **Trend features**: time index, time^2, or other trend proxies
- **External regressors**: temperature, price, marketing spend, etc.

**Multi-step forecasting strategies**:
- **Recursive**: Train a one-step-ahead model. For multi-step, feed predictions back as lag features. Risk: error accumulation.
- **Direct**: Train separate models for each horizon h. No error accumulation but requires M*h models.
- **Multi-output**: Train a single model that predicts all h steps simultaneously.
- **Rectified**: Combine recursive and direct by using recursive predictions as features in a direct model.

**Key hyperparameters**:
- `max_depth` (tree depth): controls tree complexity. Typically 3-8.
- `n_estimators` (M): number of boosting rounds. Selected by early stopping.
- `learning_rate` (nu): shrinkage factor. Smaller values (0.01-0.1) with more trees improve generalization.
- `min_child_weight`: minimum data in each leaf, prevents overfitting to small subgroups.
- `subsample` and `colsample_bytree`: stochastic gradient boosting using random subsets of data and features.
- `reg_alpha` (L1) and `reg_lambda` (L2): regularization penalties on leaf weights.

**Quantile regression for prediction intervals**: Use the pinball (quantile) loss function instead of squared error:

`L_tau(y, F) = tau * max(y - F, 0) + (1-tau) * max(F - y, 0)`

Train separate models for the lower (e.g., tau = 0.025) and upper (tau = 0.975) quantiles to get a 95% prediction interval.

**Global models**: Train a single gradient boosting model across multiple related time series (using series identifiers as features). This "global" approach often outperforms individual models because the algorithm can learn shared patterns across series, effectively increasing the training data size.
