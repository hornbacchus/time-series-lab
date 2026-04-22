# XGBoost Forecast

## What It Does

XGBoost (Extreme Gradient Boosting) Forecast applies the XGBoost algorithm to time series forecasting by training on auto-generated lag features. Unlike Random Forest which builds trees independently, XGBoost builds trees sequentially, with each new tree correcting the errors of the ensemble so far. This sequential refinement often produces more accurate forecasts than bagging-based ensembles, especially with proper regularization.

## When to Use It

- You want state-of-the-art tree-based forecasting with high accuracy
- The relationship between past and future values is complex and potentially nonlinear
- You need feature importance scores to understand predictive lag structure
- You have sufficient data to tune hyperparameters (learning rate, tree depth, regularization)
- You want a model that handles missing values natively
- Tabular prediction competitions consistently show XGBoost as a top performer

## Key Assumptions

- Past values of the series contain predictive information for future values
- The lag features adequately capture temporal dependencies
- The series does not require extreme extrapolation beyond training range
- Sufficient training data exists for the sequential boosting to converge
- The data generating process is relatively stable (no extreme distributional shifts)

## Outputs

- **Point forecasts** for the specified horizon
- **Prediction intervals** via quantile regression or residual bootstrap
- **Feature importance**: gain-based and SHAP-based importance of lag features
- **Model summary**: number of boosting rounds, learning rate, tree depth, training loss

## Technical Details

**Feature engineering**: Same lag-based approach as other tree methods. Features include `[y_{t-1}, ..., y_{t-L}]`, rolling statistics (mean, std), and calendar features (day of week, month) when datetime index is available.

**Gradient boosting**: XGBoost minimizes a regularized objective: `L = sum_i l(y_i, y_hat_i) + sum_k Omega(f_k)` where `l` is the loss function (MSE for regression), `f_k` is the k-th tree, and `Omega(f) = gamma*T + 0.5*lambda*||w||^2` penalizes tree complexity (T = number of leaves, w = leaf weights).

**Sequential tree building**: At each round `m`, a new tree `f_m` is fitted to the negative gradient (residuals for MSE loss): `y_hat_i^{(m)} = y_hat_i^{(m-1)} + eta * f_m(x_i)` where `eta` is the learning rate (shrinkage). Smaller learning rates require more rounds but typically generalize better.

**Split finding**: XGBoost uses an approximate algorithm based on weighted quantile sketches for efficient split finding. The gain for a split is: `Gain = 0.5 * [G_L^2/(H_L+lambda) + G_R^2/(H_R+lambda) - (G_L+G_R)^2/(H_L+H_R+lambda)] - gamma` where `G` and `H` are sums of first and second derivatives of the loss.

**Regularization**: L1 (`alpha`) and L2 (`lambda`) regularization on leaf weights, plus tree complexity penalty (`gamma`), prevent overfitting. Column subsampling and row subsampling add further regularization.

**Multi-step forecasting**: Recursive strategy (same as Random Forest) or direct strategy where a separate model is trained for each horizon step.

**Fallback**: When the xgboost package is not installed, the implementation falls back to scikit-learn's GradientBoostingRegressor, which uses the same algorithmic principles but with a pure Python implementation.

**Comparison**: XGBoost typically outperforms Random Forest on structured/tabular data due to its sequential error correction. It requires more careful tuning but rewards it with better accuracy. Like all tree methods, it struggles with extrapolation beyond the training data range.

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


## Interpretation

Every XGBoost run emits a two-tier Interpretation block with tree-cohort Tier 1 template + XGBoost-specific Tier 2.

**Plain-Language Finding (Tier 1)** - same shape as Random Forest with backend disclosure (xgboost preferred; falls back to sklearn.GradientBoostingRegressor when unavailable).

**Technical Interpretation (Tier 2)** - discloses gradient-boosted ensemble structure with subsample / learning_rate regularization. When the xgboost library is not installed, explicitly discloses the sklearn.GBR fallback as a semantic drift (not equivalent to true XGBoost defaults).

**Caveats (Tier 3, conditional)**:
- Backend fallback (xgboost -> sklearn_gbr) - results are approximate.
- Overfitting, insufficient training, tree extrapolation, time-index dominance triggers (shared with RF).
