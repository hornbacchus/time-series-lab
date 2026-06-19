## What It Does
SARIMA (Seasonal ARIMA) extends ARIMA with a seasonal component, modeling both the short-term dynamics and a repeating seasonal cycle. Alongside the non-seasonal `(p, d, q)` orders it adds seasonal orders `(P, D, Q)` at a seasonal period `m` (12 for monthly data with an annual cycle). It is the standard tool for forecasting series with a clear seasonal pattern.

## When to Use It
- Your series has a seasonal cycle (monthly with annual seasonality, quarterly, weekly patterns).
- You want explicit control over both the non-seasonal and seasonal model orders.
- A non-seasonal ARIMA leaves seasonal structure in the residuals.
- Use SARIMA when the seasonality is known; use `auto_arima` (seasonality on) to search the seasonal order automatically.

## How to Read the Result
The output is the forecast, the seasonal and non-seasonal coefficients, the AIC, and prediction intervals. On the airline series a (1,1,1)(1,1,1) SARIMA with the period inferred as 12 returns AIC 1022.3 and RMSE 44.9 — a clear improvement over the non-seasonal ARIMA (AIC 1394.7) on the same data, because it now captures the annual cycle. The seasonal period is the key specification: leave the seasonal order blank and the engine infers the period from the data frequency and fits a default seasonal structure, or set it explicitly.

## Related Techniques
- *(use after)* compare against `auto_arima` to confirm the chosen order is competitive.
- *(alternatives)* `arima` (non-seasonal); `auto_arima` (automatic seasonal order); `ets_hw` (an exponential-smoothing route to seasonal forecasting); `arimax_sarimax` to add exogenous regressors.

## Technical Detail
Estimation is statsmodels `SARIMAX` by maximum likelihood. The non-seasonal order `(p, d, q)` and seasonal order `(P, D, Q, m)` are specified; leaving the seasonal order blank resolves to a default seasonal structure at the frequency-inferred period `m`. Stationarity and invertibility constraints are enforced by default. Outputs include AIC/BIC, coefficients, and forecasts with prediction intervals.
*Reference run:* airline_passengers.csv (144 monthly observations), order (1,1,1), seasonal order left blank, horizon 12, Balanced — the blank seasonal order resolved to (1,1,1,12) at the inferred period, AIC 1022.3, RMSE 44.9 (an improvement over the non-seasonal ARIMA's 1394.7 on the same data).
