## What It Does
ARIMAX/SARIMAX extends ARIMA (or SARIMA) with exogenous regressors — external driver series that help explain the target. The model captures the target's own ARIMA dynamics *and* its response to the drivers at once: a dynamic regression with ARIMA errors. Use it when you have explanatory variables whose values inform the forecast, not just the target's own past.

## When to Use It
- You have one or more external driver series (exogenous regressors) that explain the target.
- You want the driver effects estimated jointly with the target's ARIMA dynamics.
- You're doing scenario analysis (forecasting the target under assumed driver paths).
- Use it when you have explanatory series; use plain `arima`/`sarima` when only the target's own history is available; use `transfer_function` for an interpretable distributed-lag view of an input-output relationship.

## How to Read the Result
The first series is the target (endogenous); the second and subsequent series are the exogenous regressors. The output is the forecast, the ARIMA coefficients, the exogenous regression coefficients (the estimated driver effects), and the AIC. On a synthetic series built as `y = 1.5·x + ARMA(1,1)` noise, an automatic-order ARIMAX recovers the structure with AIC 861.7 and RMSE 0.99 (about 48% better than naive), the exogenous regressor entering significantly. One practical caveat: to forecast forward you need future values of the exogenous series — if they are not supplied the engine carries the last value forward and warns, so a forecast that depends on assumed driver paths is only as good as those assumptions.

## Related Techniques
- *(use after)* `transfer_function` for a complementary distributed-lag view of the same input-output relationship.
- *(alternatives)* `arima`/`sarima` (no exogenous drivers); `transfer_function` (distributed-lag OLS with a long-run multiplier); the VAR family when drivers and target are mutually endogenous.

## Technical Detail
Estimation is statsmodels `SARIMAX` with exogenous regressors by maximum likelihood. The first series is the endogenous target; remaining series are the exogenous regressors. A non-zero seasonal order routes through the seasonal branch. The order can be set explicitly or searched automatically. Stationarity and invertibility constraints are enforced by default. Forecasting requires future exogenous values; absent them, the last observed value is carried forward with a warning.
*Reference run:* a synthetic series `y = 1.5·x + ARMA(1,1)` with `x` an AR(0.7) process (n=300), automatic order, Balanced — selected ARIMAX(3,0,3) with the exogenous regressor, AIC 861.7, RMSE 0.99 (about 48% better than naive).
