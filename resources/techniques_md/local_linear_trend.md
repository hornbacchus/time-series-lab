## What It Does
The local linear trend model extends the local-level model with a slope, so the series has both a drifting level and a drifting trend — both evolving stochastically over time. Where the local-level model forecasts flat, this one carries the estimated trend forward, and because the slope itself can change, the trend adapts rather than staying a fixed straight line. It is the structural model for a series with an evolving trend but no seasonality.

## When to Use It
- The series has a trend that may change direction or steepness over time.
- You want a forecast that carries the trend forward, not a flat projection.
- You want the level and trend separated as interpretable components.
- Use the local linear trend for an evolving trend; use `local_level` when there is no trend, `structural_ts` when there is seasonality.

## How to Read the Result
The output is the smoothed level and slope, the variance estimates, and a trend-carrying forecast. The informative quantity is how much the slope is allowed to move — the ratio of the slope variance to the level variance. When the slope variance is near zero (at the optimizer's floor), the trend is effectively a fixed linear drift; when it is larger, the trend bends to follow the data. On the airline series the slope variance sits at the floor, so the model fits a near-linear trend — telling you the trend in that series is well-described by a constant slope rather than a curving one. Read the level and slope components to see the decomposition, and note the forecast extends the current slope.

## Related Techniques
- *(use after)* `structural_ts` if the series also has a seasonal or cyclical component the trend model leaves in the residual.
- *(alternatives)* `local_level` (no trend); `structural_ts` (trend plus seasonality and cycles); `ets_hw` for an exponential-smoothing route to trended forecasting.

## Technical Detail
Estimation is statsmodels `UnobservedComponents` with a local-linear-trend specification, fit by maximum likelihood; the level and slope are the smoothed states. The slope-adaptivity is the ratio of the slope (trend) variance to the level variance — at zero the trend is a fixed linear drift, larger values let it curve. Forecasts carry the final slope forward with horizon-widening intervals.
*Reference run:* airline_passengers.csv (144 monthly observations), Balanced — extracts a level plus a near-linear slope (the slope variance at the optimizer floor, indicating a constant-slope trend), smoothed final level 112.
