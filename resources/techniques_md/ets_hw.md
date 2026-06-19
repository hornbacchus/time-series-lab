## What It Does
ETS / Holt-Winters is exponential smoothing for series with trend and seasonality. It models the series as evolving level, trend, and seasonal components, each updated by a smoothing parameter that weights recent observations more heavily than distant ones. You specify the component structure — additive or multiplicative trend and seasonality, optionally damped — and the model fits by maximum likelihood, returning forecasts and prediction intervals. It is a robust, widely-used alternative to ARIMA for trended or seasonal data.

## When to Use It
- You have a series with trend and/or seasonality and want a smoothing-based forecast.
- You want a robust, fast forecaster that is hard to overfit.
- You prefer the interpretable level/trend/seasonal decomposition over ARIMA's order specification.
- Use ETS/Holt-Winters as an alternative or complement to `sarima`; benchmark both against `theta_forecast`.

## How to Read the Result
The output is the forecast, the fitted smoothing parameters, the AIC, and prediction intervals. The smoothing parameters tell you how reactive each component is: near 1 tracks recent data closely, near 0 holds the component nearly fixed. On the airline series, an additive-trend, additive-seasonal fit returns RMSE 12.24 (about 66% better than a seasonal-naive benchmark) with `α = 0.25` (level), `β = 0.00003`, and `γ = 0.75` (seasonal). Note the trend smoothing `β`: at 0.00003 it has hit the optimizer's lower bound, which means the trend is effectively *frozen* at its initial value — the model is essentially level-plus-seasonal with a static trend slope. A smoothing parameter pinned at its bound is driven by initialization rather than learned from the data, so do not over-interpret it; this is a known weak-identification feature of these models, not an error.

## Related Techniques
- *(use after)* benchmark against `theta_forecast` (often the one to beat) and `sarima`.
- *(alternatives)* `sarima` (the ARIMA route to seasonal forecasting); `theta_forecast` (a simpler benchmark); `arima` for non-seasonal series.

## Technical Detail
Estimation is statsmodels `ETSModel` — a state-space exponential-smoothing model fit by maximum likelihood (this replaced an earlier sum-of-squares implementation). You specify the trend type (additive, multiplicative, or none), the seasonal type, and whether the trend is damped; the seasonal component is auto-detected as additive or none when not specified. The model fits the *single specified structure* — it does not search across the full ETS family. Smoothing parameters are bounded to `[1e-4, 1-1e-4]` to prevent degenerate corner solutions, and prediction intervals are analytic, taken from the state-space forecast-error variance.
*Reference run:* airline_passengers.csv (144 monthly observations), additive trend, additive seasonal, horizon 12, Balanced — Holt-Winters(additive, additive, period 12), AIC 1166.0, RMSE 12.24 (about 66% better than seasonal-naive); smoothing parameters `α = 0.25`, `β = 0.00003` (at the optimizer floor — trend effectively frozen), `γ = 0.75`.
