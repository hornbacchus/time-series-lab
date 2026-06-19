## What It Does
ARIMA (AutoRegressive Integrated Moving Average) is the classical Box-Jenkins forecasting model. It combines three pieces: autoregression (the series regressed on its own recent values), differencing (to remove trends and make the series stationary), and a moving-average term (modeling dependence in the forecast errors). You specify the three orders — `p` (AR), `d` (differencing), `q` (MA) — and the model fits by maximum likelihood, returning forecasts, fit diagnostics, and prediction intervals.

## When to Use It
- You have a single non-seasonal series and want a well-understood, diagnostic-rich forecast.
- You want explicit control over the model order (the AR, differencing, and MA terms).
- You want residual diagnostics (Ljung-Box) to confirm the model captured the serial correlation.
- Use ARIMA when you know or want to choose the order; use `auto_arima` to search the order automatically; use `sarima` when the series has a seasonal cycle.

## How to Read the Result
The output is the forecast, the fitted coefficients, the AIC, and a Ljung-Box residual test. The AIC compares models on the same data (lower is better). The Ljung-Box p-value is the adequacy check: a high p-value (no leftover residual autocorrelation) means the model captured the structure — on the airline series a (1,1,1) ARIMA returns Ljung-Box p = 0.30, so the ARMA part is adequate. But note what the reference exposes: a *non-seasonal* ARIMA on a strongly seasonal series underperforms even a seasonal-naive benchmark (RMSE 47.6 versus a naive 33.7), not because the fit is poor but because it ignores the seasonal cycle. That gap is exactly why the seasonal variant exists.

## Related Techniques
- *(use after)* check the residuals; if seasonality remains, move to `sarima`.
- *(alternatives)* `auto_arima` (searches the order for you); `sarima` (seasonal cycle); `arimax_sarimax` (add exogenous drivers); `ets_hw` and `theta_forecast` as alternative forecasters.

## Technical Detail
Estimation is statsmodels `ARIMA` by maximum likelihood. The order `(p, d, q)` is specified directly; `d` differences the series to stationarity before fitting the ARMA part. An optional seasonal order field exists, but for a genuine seasonal model `sarima` is the natural choice. Outputs include AIC and BIC, the coefficient estimates, the Ljung-Box residual autocorrelation test, and forecasts with prediction intervals.
*Reference run:* airline_passengers.csv (144 monthly observations), order (1,1,1), horizon 12, Balanced — AIC 1394.7, forecast RMSE 47.6, Ljung-Box(10) p = 0.30 (the ARMA part is adequate); the non-seasonal model underperforms a seasonal-naive benchmark on this seasonal series, motivating `sarima`.
