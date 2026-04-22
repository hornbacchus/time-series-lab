# SVR Forecast

## What It Does

Support Vector Regression (SVR) Forecast applies kernel-based Support Vector Machines to time series forecasting using auto-generated lag features. SVR finds a function that deviates from the actual values by at most epsilon for each training point, while being as flat as possible. The RBF (Radial Basis Function) kernel maps the lag features into a high-dimensional space where nonlinear relationships become linear, enabling the model to capture complex temporal patterns.

## When to Use It

- You want a kernel-based model that can capture nonlinear lag relationships
- Your series has moderate length (SVR scales quadratically with sample size)
- You need a model with strong theoretical foundations (convex optimization, unique solution)
- The series contains complex nonlinear patterns that linear models miss
- You want robust predictions that are less sensitive to outliers (epsilon-insensitive loss)

## Key Assumptions

- Past values contain predictive information for future values
- The lag structure captures the relevant temporal dependencies
- The data fits within a moderate size (SVR becomes slow for very large datasets)
- An appropriate kernel can capture the underlying nonlinear relationship
- The data is scaled appropriately (SVR is sensitive to feature scaling)

## Outputs

- **Point forecasts** for the specified horizon
- **Model summary**: kernel type, C parameter, epsilon, number of support vectors, training R-squared
- **Support vector count**: indicates model complexity (fewer = simpler model)

## Technical Details

**Epsilon-insensitive loss**: SVR uses the epsilon-tube loss: `L = max(0, |y - f(x)| - epsilon)`. Points within the epsilon-tube incur zero loss. Only points outside the tube (support vectors) contribute to the model, making SVR sparse and robust.

**Optimization problem**: SVR solves: `min 0.5 * ||w||^2 + C * sum_i (xi_i + xi_i*)` subject to `y_i - <w, phi(x_i)> - b <= epsilon + xi_i` and `<w, phi(x_i)> + b - y_i <= epsilon + xi_i*`, where `xi_i, xi_i* >= 0` are slack variables and `C` controls the trade-off between model flatness and tolerance of deviations.

**RBF kernel**: `K(x_i, x_j) = exp(-gamma * ||x_i - x_j||^2)` where `gamma = 1/(n_features * variance)` by default. The RBF kernel maps input into an infinite-dimensional feature space, enabling approximation of any continuous function.

**Feature scaling**: All lag features are standardized (zero mean, unit variance) before fitting, as SVR is sensitive to feature scales. The scaler parameters are saved for inverse-transforming predictions.

**Multi-step forecasting**: Uses recursive strategy: predict one step ahead, append to lag features, predict the next step, and so on.

**Hyperparameter sensitivity**: `C` (regularization), `epsilon` (tube width), and `gamma` (kernel bandwidth) jointly control model complexity. Grid search with cross-validation is used in Thorough preset.

**Comparison**: SVR excels when the training set is small to moderate (hundreds to a few thousand observations). For larger datasets, tree-based methods or neural networks are more computationally efficient. SVR provides a unique global optimum (convex problem) unlike neural networks.

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

Every SVR run emits a two-tier Interpretation block. Inherits C2 forecaster Tier 1 structure; Tier 2 substitutes support-vector structure for tree-style feature importances.

**Tier 1** - names kernel (default RBF), train vs CV RMSE with overfitting ratio, support-vector count with SV ratio health indicator (healthy / elevated / overfitting-by-memorization), hyperparameters (C, epsilon, gamma).

**Tier 2** - discloses C (regularization), epsilon (insensitive-tube half-width), gamma fixed at "scale" (the #1 SVR sensitivity, NOT user-configurable). Explicit feature-scaling disclosure (StandardScaler applied to X and y) with double-scaling warning. RBF extrapolation caveat (predictions collapse to global mean at long horizons). Honest-disclosure of limited interpretability: no native feature importance on non-linear kernels.

**Caveats (Tier 3, conditional)**:
- Overfitting (CV/train RMSE > 2).
- **Overfitting by memorization** (D11 refined label): support vectors > 80% of training set.
- RBF + horizon > 3 - extrapolation collapse warning.
