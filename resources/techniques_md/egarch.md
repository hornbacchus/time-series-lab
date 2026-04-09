# EGARCH Model

## What It Does

EGARCH (Exponential GARCH) models time-varying volatility using the **logarithm** of the conditional variance. This provides two key advantages over standard GARCH: it naturally ensures the variance is always positive without requiring parameter constraints, and it captures the leverage effect through an asymmetric response to the sign and magnitude of shocks. Negative returns increase log-volatility more than positive returns.

## When to Use It

- You need an asymmetric volatility model with no positivity constraints on parameters
- The leverage effect is prominent and you want a flexible parameterization
- Standard GARCH imposes parameter constraints that are binding during estimation
- You want to allow the volatility response to differ in both sign and magnitude of shocks
- Financial return series show strong asymmetric volatility behavior

## Key Assumptions

- The conditional mean is correctly specified
- The log-variance follows a linear ARMA-type process in terms of standardized residuals
- The leverage effect can be captured by separate coefficients on the sign and magnitude of standardized shocks
- The model is stationary (persistence parameter less than 1 in absolute value)
- The innovation distribution is correctly specified

## Outputs

- **Log conditional variance series** and the corresponding conditional variance
- **EGARCH parameters**: omega (constant in log-variance), alpha (magnitude effect), gamma (sign/leverage effect), beta (persistence)
- **Asymmetry analysis**: quantifying the differential impact of positive vs. negative shocks
- **News impact curve**: showing the exponential asymmetric response
- **Volatility forecasts** with the characteristic multiplicative structure

## Technical Details

**EGARCH(1,1) model** (Nelson, 1991):

Mean equation: `Y_t = mu + e_t`, where `e_t = sigma_t * z_t` and `z_t ~ iid(0,1)`

Log-variance equation:
`log(sigma_t^2) = omega + alpha (|z_{t-1}| - E[|z_{t-1}|]) + gamma z_{t-1} + beta log(sigma_{t-1}^2)`

**Interpretation of parameters**:
- `omega`: the long-run level of log-variance (when beta < 1)
- `alpha`: captures the magnitude effect -- how the absolute size of the standardized shock affects log-volatility
- `gamma`: captures the sign (leverage) effect -- negative when bad news increases volatility more than good news
- `beta`: persistence of log-volatility shocks

**Effect of shocks on log-variance**:
- After a positive shock `z_{t-1} > 0`: impact = `alpha * z_{t-1} + gamma * z_{t-1}` (net coefficient: `alpha + gamma`)
- After a negative shock `z_{t-1} < 0`: impact = `-alpha * z_{t-1} + gamma * z_{t-1}` (net coefficient: `-alpha + gamma`, but applied to negative z, so the effect is `alpha - gamma` in magnitude)

Since the model is in log-variance, the impact on variance itself is multiplicative: `sigma_t^2 = sigma_{t-1}^{2*beta} * exp(omega + ...)`, which guarantees `sigma_t^2 > 0` for any parameter values.

**Advantages over GARCH/GJR-GARCH**:
1. **No positivity constraints**: Since the model is in log-variance, parameters can take any value.
2. **Multiplicative shocks**: The exponential structure means volatility responds multiplicatively to shocks, which may be more realistic.
3. **Standardized residuals**: The model uses `z_t` (standardized) rather than `e_t` (raw), making coefficients scale-free.

**Stationarity**: The process is stationary when `|beta| < 1`. The unconditional log-variance is `E[log(sigma^2)] = omega / (1 - beta)` (under some regularity conditions).

**Estimation**: MLE using the conditional log-likelihood. For Gaussian innovations:

`log L = -0.5 sum_t [log(2*pi) + log(sigma_t^2) + z_t^2]`

where `log(sigma_t^2)` is computed recursively from the EGARCH equation. `E[|z_t|] = sqrt(2/pi)` for Gaussian z_t, or `sqrt(2) * Gamma((nu+1)/2) / (sqrt(nu-2) * Gamma(nu/2))` for Student-t with nu degrees of freedom.

**Forecasting**: Direct multi-step forecasts for EGARCH are complicated because `E[log(sigma_{t+h}^2)]` does not directly give `E[sigma_{t+h}^2]` (Jensen's inequality). Simulation-based forecasts are typically used: generate many paths of `z_{t+1}, z_{t+2}, ...`, compute the log-variance path for each, and average the resulting `sigma^2` values.

**General EGARCH(p,q)**:
`log(sigma_t^2) = omega + sum_{i=1}^{q} [alpha_i |z_{t-i}| + gamma_i z_{t-i}] + sum_{j=1}^{p} beta_j log(sigma_{t-j}^2)` minus the centering term for `E[|z|]`.
