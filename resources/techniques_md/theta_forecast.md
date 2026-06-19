## What It Does
The Theta method is a simple, remarkably robust forecasting technique that won the M3 forecasting competition. It decomposes the series into "theta lines" — versions of the series with the local curvature scaled up or down — forecasts each, and recombines them. In practice it amounts to combining a long-run trend (drift) with short-run exponential smoothing, optionally after removing seasonality. Its strength is that it is hard to beat: a standard benchmark that more complex models must outperform to justify themselves.

## When to Use It
- You want a strong, simple baseline forecast to benchmark more complex models against.
- You have limited data or want a method that is hard to overfit.
- You want a fast, robust forecaster with minimal specification.
- Use Theta as the benchmark in any forecasting comparison; reach for ARIMA/ETS only if they actually beat it on your data.

## How to Read the Result
The output is the forecast and its fit error. The value of Theta is comparative: on the airline series it achieves a fit RMSE of 8.95 — about 75% better than a seasonal-naive benchmark — the kind of strong, hard-to-beat performance that makes it the standard reference. When you fit ARIMA, ETS, or an ML forecaster, compare against Theta: if they do not clearly beat it, the simpler method is the better choice.

## Related Techniques
- *(use after)* nothing required — Theta is usually the baseline others are measured against.
- *(alternatives)* `ets_hw` (exponential smoothing); `arima`/`auto_arima` (Box-Jenkins); any ML forecaster — all worth comparing to Theta.

## Technical Detail
Estimation is statsmodels `ThetaModel` (the Hyndman-Billah state-space reformulation). The series is optionally deseasonalized, then decomposed into theta lines — the `θ = 0` line (a linear trend / drift) and the `θ = 2` line (simple exponential smoothing on the curvature-doubled series) — which are forecast and recombined, with the seasonal component re-applied at the end. The seasonal period is inferred from the data frequency.
*Reference run:* airline_passengers.csv (144 monthly observations), horizon 12, Balanced — period 12 inferred, fit RMSE 8.95 (about 75% better than a seasonal-naive benchmark), a strong benchmark forecast.
