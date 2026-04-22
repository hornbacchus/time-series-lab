# Quantile Regression Forecast

## What It Does

Quantile regression estimates **conditional quantiles** of the response variable rather than the conditional mean. By forecasting at multiple quantile levels (e.g., 10th, 25th, 50th, 75th, 90th percentiles), it produces a full picture of forecast uncertainty without assuming any particular error distribution. This makes it a powerful tool for probabilistic forecasting where the distribution of outcomes may be asymmetric, heavy-tailed, or heteroskedastic.

## When to Use It

- You need prediction intervals that do not assume Gaussian errors
- The distribution of forecast errors is asymmetric (upside and downside risks differ)
- You want to understand how uncertainty changes with the level or features of the series
- Risk management requires quantile-specific forecasts (e.g., 1% VaR, 95th percentile demand)
- Inventory planning needs different percentiles for safety stock calculations

## Key Assumptions

- The conditional quantile function is correctly specified (linear or via the chosen nonlinear model)
- Sufficient data exists for stable estimation, especially at extreme quantiles
- The relationship between features and quantiles is stable over time
- Each quantile is estimated independently (potential for quantile crossing)
- The chosen features (lags, exogenous variables) are relevant for predicting the target quantiles

## Outputs

- **Quantile forecasts**: predictions at each specified quantile level
- **Prediction intervals**: formed by pairing lower and upper quantile forecasts (e.g., 5th and 95th)
- **Median forecast**: the 50th percentile as a robust point forecast
- **Quantile coefficient estimates**: showing how features affect different parts of the distribution
- **Interval coverage analysis**: how often actual values fall within the predicted intervals

## Technical Details

**Linear quantile regression** (Koenker and Bassett, 1978): For quantile level tau, estimate:

`Q_tau(Y | X) = X' beta(tau)`

by minimizing the **check function (pinball loss)**:

`min_beta sum_{i=1}^{n} rho_tau(y_i - x_i' beta)`

where `rho_tau(u) = u * (tau - I(u < 0))`. This gives:
- For `u > 0` (underprediction): loss = `tau * u`
- For `u < 0` (overprediction): loss = `(1 - tau) * |u|`

At tau = 0.5 (median regression), this is equivalent to minimizing absolute deviations (LAD).

**Why check function works**: The population minimizer of `E[rho_tau(Y - q)]` over q is exactly the tau-th quantile of Y. The check function asymmetrically penalizes under- and over-prediction, tilting the optimal prediction toward the desired quantile.

**Estimation**: The minimization problem is a linear program and can be solved efficiently by the simplex method or interior point methods. Standard errors are obtained via:
- **Direct density estimation**: `Var(beta_hat(tau)) = tau(1-tau) / (n * f(Q_tau)^2) * (X'X)^{-1}`, where `f(Q_tau)` is the error density at the quantile, estimated by kernel methods.
- **Bootstrap**: Resample observations and re-estimate the quantile regression.

**Nonlinear quantile regression**: For nonlinear relationships, gradient boosting with quantile loss is widely used:

`L_tau(y, F(x)) = tau * max(y - F(x), 0) + (1-tau) * max(F(x) - y, 0)`

XGBoost, LightGBM, and similar methods support quantile loss natively, allowing complex feature interactions while targeting specific quantiles.

**Quantile crossing**: Since each quantile is estimated independently, it is possible that `Q_{tau1}(x) > Q_{tau2}(x)` for `tau1 < tau2` at some x values. Solutions include:
- **Sorting**: Simply reorder quantile forecasts to enforce monotonicity.
- **Joint estimation**: Methods like the non-crossing quantile regression add constraints to prevent crossing.
- **Isotonic regression**: Post-process quantile forecasts to enforce monotonicity.

**Application to time series**: Lag features `(y_{t-1}, ..., y_{t-p})`, rolling statistics, and calendar features serve as predictors X. The quantile regression produces conditional quantile forecasts at each horizon, naturally accommodating heteroskedastic forecast uncertainty (wider intervals during volatile periods, narrower during calm periods).

**Comparison with parametric intervals**: Gaussian prediction intervals assume `Y_t | X ~ N(mu, sigma^2)` and compute `mu +/- z * sigma`. Quantile regression imposes no distributional assumption and can produce asymmetric intervals that better reflect the true conditional distribution.


## Interpretation

Every Quantile Regression run emits a two-tier Interpretation block. **Stands alone** per D7 - distinct from CAViaR (which is autoregressive on the quantile state).

**Tier 1** - names the quantile levels (integer-when-whole rendering per Convention A), median-model RMSE, and any quantile-crossing violations. Discloses the median-rollover coupling risk up-front.

**Tier 2** - explains sklearn GradientBoostingRegressor with `loss='quantile'` fitted independently per quantile level (distribution-free check / pinball loss - no distributional assumption). Contrasts with CAViaR: no backtest suite (Kupiec/DQ/Christoffersen); only quantile-crossing count as a monotonicity sanity check. Cites top-3 feature importances per quantile.

**Caveats (Tier 3, conditional)**:
- Quantile crossings detected -> suggest isotonic post-processing or joint-quantile model.
- Median rollover coupling (always fires for horizon > 1) - quantile uncertainty at long horizons reflects median uncertainty rather than quantile-specific dynamics.
