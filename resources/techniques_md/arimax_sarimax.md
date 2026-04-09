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
