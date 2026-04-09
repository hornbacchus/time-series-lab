# SARIMA

## What It Does

SARIMA (Seasonal ARIMA) extends the ARIMA model to handle time series with seasonal patterns by adding seasonal autoregressive, differencing, and moving average terms. It captures both the short-term dynamics within a season and the patterns that repeat across seasons, making it the standard parametric model for seasonal time series forecasting.

## When to Use It

- Your data has a clear seasonal pattern (e.g., monthly data with yearly cycles)
- You need a model that captures both within-season and between-season dependencies
- The seasonal pattern is relatively stable over time
- You want a well-established statistical model with prediction intervals
- You have at least 3-4 complete seasonal cycles of data

## Key Assumptions

- The series is univariate and equally spaced
- After regular and seasonal differencing, the series is stationary
- Residuals are white noise (uncorrelated, constant variance)
- The seasonal period is known and fixed
- The seasonal pattern can be captured by a linear combination of seasonal lags

## Outputs

- **Point forecasts** with seasonal patterns projected forward
- **Prediction intervals** accounting for both regular and seasonal uncertainty
- **Estimated coefficients** for both regular and seasonal AR/MA terms
- **Residual diagnostics**: ACF/PACF plots, Ljung-Box test at seasonal lags
- **Information criteria** for model comparison (AIC, BIC)

## Technical Details

A SARIMA(p, d, q)(P, D, Q)_s model has two sets of components:

- **Non-seasonal**: AR(p), differencing d, MA(q) -- capturing short-term dynamics.
- **Seasonal**: AR(P), differencing D, MA(Q) at seasonal period s -- capturing repeating seasonal dynamics.

**Model equation**: Let `B` be the backshift operator and `B^s` the seasonal backshift. The model is:

`phi(B) * Phi(B^s) * (1-B)^d * (1-B^s)^D * Y_t = c + theta(B) * Theta(B^s) * e_t`

where:
- `phi(B) = 1 - phi_1 B - ... - phi_p B^p` (non-seasonal AR)
- `Phi(B^s) = 1 - Phi_1 B^s - ... - Phi_P B^{Ps}` (seasonal AR)
- `theta(B) = 1 + theta_1 B + ... + theta_q B^q` (non-seasonal MA)
- `Theta(B^s) = 1 + Theta_1 B^s + ... + Theta_Q B^{Qs}` (seasonal MA)
- `(1-B)^d` is regular differencing
- `(1-B^s)^D` is seasonal differencing

**Common example -- SARIMA(1,1,1)(1,1,1)_12 for monthly data**:

`(1 - phi_1 B)(1 - Phi_1 B^{12})(1-B)(1-B^{12}) Y_t = (1 + theta_1 B)(1 + Theta_1 B^{12}) e_t`

This expands to dependencies on lags 1, 2, 12, 13, 14, 24, 25, 26 of the doubly differenced series, showing how the seasonal and non-seasonal operators interact multiplicatively.

**Identification for seasonal models**:
1. **Seasonal differencing**: If the ACF at seasonal lags (s, 2s, 3s, ...) decays slowly, apply seasonal differencing `(1-B^s)`. Usually D = 0 or 1.
2. **Regular differencing**: After seasonal differencing, check if the non-seasonal ACF still decays slowly. Usually d = 0 or 1.
3. **Seasonal P, Q**: Examine ACF and PACF at lags s, 2s, 3s. ACF cutting off after lag s suggests Q=1; PACF cutting off suggests P=1. Typically P, Q in {0, 1, 2}.
4. **Non-seasonal p, q**: Examine ACF and PACF at early lags (1, 2, 3, ...). Apply standard ARMA identification rules.

**Estimation**: MLE is used, but the likelihood computation must handle the seasonal structure. For large seasonal periods, the covariance matrix becomes large, and efficient algorithms like the Kalman filter in state space form are used.

**Forecasting**: Forecasts are generated recursively, with seasonal components producing the characteristic repeating pattern in multi-step forecasts. Prediction intervals account for the multiplicative interaction between seasonal and non-seasonal error propagation.
