# ARIMAX / SARIMAX

## What It Does

ARIMAX (ARIMA with eXogenous variables) and SARIMAX (Seasonal ARIMA with eXogenous variables) extend the ARIMA/SARIMA framework by including external predictor variables (regressors) alongside the time series' own lagged values. This allows the model to capture relationships between the target series and other variables (e.g., temperature affecting energy demand, advertising spend affecting sales) while still modeling the temporal dynamics of the residuals.

## When to Use It

- You believe external factors drive or influence your target variable
- You have reliable exogenous variables available both in-sample and for the forecast horizon
- Pure ARIMA residuals show patterns correlated with known external variables
- You need to produce scenario-based forecasts (e.g., "what if advertising doubles?")
- You want a regression model that properly accounts for autocorrelated errors

## Key Assumptions

- Exogenous variables are available for the entire forecast horizon (you must supply future values)
- The relationship between exogenous variables and the target is contemporaneous and linear
- After accounting for exogenous effects and differencing, residuals follow a stationary ARMA process
- Exogenous variables are not caused by the target variable (no reverse causality)
- No perfect multicollinearity among the regressors

## Outputs

- **Point forecasts** conditional on provided future exogenous values
- **Prediction intervals** reflecting both regression and ARMA uncertainty
- **Regression coefficients** for each exogenous variable with standard errors
- **ARMA coefficients** for the error process
- **Residual diagnostics** confirming white noise errors after modeling

## Technical Details

**Model specification**: A SARIMAX(p,d,q)(P,D,Q)_s model with k exogenous regressors is:

`Y_t = beta_1 X_{1,t} + beta_2 X_{2,t} + ... + beta_k X_{k,t} + eta_t`

where `eta_t` follows a SARIMA(p,d,q)(P,D,Q)_s process:

`phi(B) Phi(B^s) (1-B)^d (1-B^s)^D eta_t = c + theta(B) Theta(B^s) e_t`

This is a **regression with ARIMA errors** formulation. The regression captures the systematic effect of exogenous variables, and the ARIMA component models the remaining temporal structure.

**Important distinction -- transfer function vs. regression with ARIMA errors**:

In the ARIMAX formulation above, the exogenous variables affect `Y_t` contemporaneously (at the same time period). The differencing operator applies to the error process `eta_t`, not to the exogenous variables. This differs from a transfer function model where the exogenous inputs can have lagged effects through rational polynomial filters.

Some software implementations differ: statsmodels in Python applies differencing to the entire model (including regressors), while the R `forecast::Arima` function treats regressors as entering the undifferenced equation. Be aware of which convention your software uses.

**Estimation**:

1. An initial regression of `Y_t` on `X_{1,t}, ..., X_{k,t}` is computed (possibly with differencing).
2. The residuals from this regression are examined for ARMA structure.
3. The full model (regression + ARIMA errors) is estimated jointly via MLE, iterating between regression parameter updates and ARMA parameter updates until convergence.

The log-likelihood depends on the innovations `e_t`, computed via the Kalman filter in state space form, which handles the interaction between regression and ARMA components correctly.

**Forecasting**:

For h-step-ahead forecasts, you need future values of all exogenous variables `X_{1,t+h}, ..., X_{k,t+h}`. The forecast is:

`Y_hat_{t+h} = beta_1 X_{1,t+h} + ... + beta_k X_{k,t+h} + eta_hat_{t+h}`

where `eta_hat_{t+h}` is the ARIMA forecast of the error component. Prediction intervals combine the uncertainty from the ARIMA error forecasts with the regression estimation uncertainty.

**Model selection**: Use AICc or BIC to compare models with different exogenous variable subsets and ARIMA orders. Stepwise procedures can be applied to both the ARIMA order and the regressor selection.

## Interpretation

Every ARIMAX / SARIMAX run emits a two-tier plain-language Interpretation block. The spec variant (arimax vs sarimax) is chosen from the fitted seasonal order: runs with a non-trivial seasonal specification route to the sarimax spec; runs without seasonal route to arimax.

**Plain-Language Finding (Tier 1)** - names the fitted order (and seasonal order for sarimax), observations, count of exogenous regressors, horizon, fit RMSE vs the naive baseline (last-value for arimax, seasonal-naive for sarimax) with percentage delta, and the end-of-horizon forecast level. The horizon-trend phrasing uses the four-rule fallback hierarchy (near-zero observation, near-zero-scale, extreme percentage, returns-class mean) for robustness on economic series.

**Technical Interpretation (Tier 2)** - discloses the user-chosen (p,d,q) and (P,D,Q)[m], the differencing levels applied, AIC / BIC / in-sample RMSE, residual Ljung-Box at lag 10, and — when exogenous regressors are present — each exogenous coefficient with its p-value and significance verdict at 5% / 10%. Also explicitly discloses the exog-carry-forward convention: the naive baseline uses last-value-carried-forward for both the endogenous series and exogenous regressors, making the RMSE comparison apples-to-apples on identical exogenous paths.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= naive baseline - the model does not beat naive.
- Residuals reject normality (Jarque-Bera) - prediction intervals assume Gaussian errors and may be mis-calibrated.
- Maximum-likelihood optimization did not fully converge - coefficient standard errors are approximate.
- (arimax) None of the exogenous regressors reach the 5% significance threshold - refit without exog and compare AIC.
- (sarimax) Combined ARMA+SARMA order (p+q+P+Q) is high and exceeds 10% of sample size - model may be overparameterized (composite threshold: order > 6 AND > 0.1 * n_obs).
