# NAR / NARX Models

## What It Does

NAR (Nonlinear AutoRegressive) and NARX (Nonlinear AutoRegressive with eXogenous inputs) models use neural networks or other nonlinear function approximators to capture complex, nonlinear relationships between a time series and its own lagged values (NAR) or additional input variables (NARX). They provide a flexible, data-driven approach to nonlinear time series modeling when parametric nonlinear models like STAR or TAR are too restrictive.

## When to Use It

- The relationship between the series and its lags is complex and nonlinear in ways not captured by STAR/TAR/threshold models
- You have external variables with nonlinear effects on the target series
- You want to leverage neural network flexibility while maintaining the time series regression structure
- The data is abundant enough to train a nonlinear model without severe overfitting
- You need a nonlinear forecasting model that can incorporate exogenous inputs

## Key Assumptions

- The current value depends on a finite number of lagged values and/or exogenous inputs
- The functional relationship, while nonlinear, is smooth enough to be learned from data
- Enough training data is available to estimate the nonlinear function without overfitting
- The input-output relationship is time-invariant (or changes slowly enough to be captured)
- The noise is additive and independent of the inputs

## Outputs

- **Nonlinear fitted values**: the model's estimate of the series at each time point
- **Multi-step forecasts** (recursive or direct)
- **Variable importance**: relative contribution of each lagged input
- **Residual diagnostics**: checking for remaining nonlinearity and autocorrelation
- **Network architecture details**: hidden layer sizes, activation functions, weights

## Technical Details

**NAR model**:
`Y_t = f(Y_{t-1}, Y_{t-2}, ..., Y_{t-p}) + e_t`

where `f` is a nonlinear function (typically a feedforward neural network) and `e_t` is white noise.

**NARX model**:
`Y_t = f(Y_{t-1}, ..., Y_{t-p}, X_{t-1}, ..., X_{t-q}) + e_t`

where `X_t` is a vector of exogenous inputs with lags up to q.

**Neural network implementation**: A single-hidden-layer feedforward network:

`f(z) = beta_0 + sum_{j=1}^{H} beta_j * g(alpha_{0j} + sum_i alpha_{ij} z_i)`

where `z = (Y_{t-1}, ..., Y_{t-p}, X_{t-1}, ..., X_{t-q})`, `g` is an activation function (sigmoid, tanh, or ReLU), H is the number of hidden neurons, `alpha` are input-to-hidden weights, and `beta` are hidden-to-output weights.

**Universal approximation**: A single hidden layer with enough neurons can approximate any continuous function to arbitrary accuracy (Cybenko's theorem). In practice, the number of hidden neurons H is chosen via cross-validation, typically between 3 and 20.

**Training**:
1. **Lag selection**: Choose p (and q for NARX) using AIC, BIC, or cross-validation. Mutual information or partial autocorrelation can guide initial choices.
2. **Network architecture**: Select H. Too few neurons underfits; too many overfits.
3. **Optimization**: Minimize the sum of squared errors using backpropagation with gradient descent variants (Adam, L-BFGS). Multiple random initializations are used to avoid local minima.
4. **Regularization**: Weight decay (L2 penalty), early stopping based on validation error, or dropout to prevent overfitting. Bayesian regularization (evidence framework) automatically determines the effective complexity.

**Forecasting strategies**:
- **Recursive (iterated)**: Feed predicted values back as inputs for multi-step forecasts. Error accumulates.
- **Direct**: Train separate models for each forecast horizon h. Avoids error accumulation but requires more models.
- **MIMO (Multi-Input Multi-Output)**: A single model outputs all horizons simultaneously.

**Testing for nonlinearity**: Before fitting NAR/NARX, test whether nonlinearity is needed:
- **BDS test**: Tests for residual nonlinear dependence after fitting a linear AR model.
- **Terasvirta neural network test**: Tests whether adding hidden-layer terms significantly improves fit over the linear model.
- **White's test**: Uses neural network auxiliary regressions.

**Comparison with linear models**: NAR/NARX should outperform linear ARIMA when genuine nonlinearity exists. If the true process is linear, the extra flexibility can lead to worse forecasts due to overfitting. Always compare against linear benchmarks using out-of-sample evaluation.
