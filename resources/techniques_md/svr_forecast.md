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
