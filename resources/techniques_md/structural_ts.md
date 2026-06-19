## What It Does
A structural time-series model (also called an unobserved-components model) decomposes a series into interpretable parts — a level, a trend, a seasonal component, and a cycle — each estimated as its own stochastic process. Unlike a black-box forecaster, it tells you *what the series is made of*: how much is trend, how much is the seasonal pattern, how much is a longer business-style cycle. It is the structural approach to understanding and forecasting a series with several components at once.

## When to Use It
- You want to decompose a series into trend, seasonal, and cyclical components you can interpret.
- The series has several structural features at once (trend plus seasonality plus a cycle).
- You want a model-based decomposition with forecasts, not just a descriptive split.
- Use the structural model for multi-component decomposition; use `local_level`/`local_linear_trend` for simpler level/trend-only series, `stl_decompose` for a non-parametric trend-seasonal split.

## How to Read the Result
The output is the estimated components — level, trend, seasonal, cycle — with the share of variance each explains, plus a forecast. On the airline series the model decomposes into those four components with the level dominating (about 89% of the variance) and the seasonal period inferred automatically as 12. Read the variance shares to see which components drive the series, and the component series themselves to see their shapes. The model fits its standard configuration (a local-linear-trend level with seasonal and cycle components, seasonality inferred from the data frequency); the seasonal period is detected automatically when not specified.

## Related Techniques
- *(use after)* analyze the extracted seasonal or cyclical component, or forecast from the fitted model.
- *(alternatives)* `local_linear_trend` (trend only, no seasonal/cycle); `stl_decompose` (non-parametric decomposition); `sarima` for a seasonal ARIMA forecast.

## Technical Detail
Estimation is statsmodels `UnobservedComponents`, fit by maximum likelihood, decomposing the series into level, trend, seasonal, and cycle components with an optional autoregressive term. The seasonal period is inferred from the data frequency when not specified. Each component's variance share indicates its contribution; the components are the smoothed states.
*Reference run:* airline_passengers.csv (144 monthly observations), standard configuration, Balanced — decomposed into level, trend, seasonal, and cycle components with the level explaining about 89% of the variance and the seasonal period inferred as 12, RMSE 57.3.
