## What It Does
The local-level model (also called the random-walk-plus-noise model) is the simplest structural time-series model. It treats the series as a slowly-drifting underlying level that you observe with noise — the level itself follows a random walk, and each observation is that level plus measurement error. It separates the true signal (the level) from the noise, giving a smoothed estimate of where the series really is at each point.

## When to Use It
- You want to extract a smooth underlying level from a noisy series.
- The series has no strong trend or seasonality — just a level that wanders over time.
- You want a principled signal-versus-noise separation rather than an arbitrary moving average.
- Use the local-level model for a drifting level; use `local_linear_trend` when there is a trend, `structural_ts` when there is seasonality or a cycle.

## How to Read the Result
The output is the smoothed level, the variance estimates, and a forecast. The key quantity is the signal-to-noise ratio — the level variance divided by the observation variance — which tells you how much of the series' movement is real signal versus noise. On the Nile river series, the ratio is 0.10: the observation variance (15,009) is about ten times the level variance (1,518), so the series is noisy relative to how fast the level moves, and the smoothed level is a substantially cleaned-up version of the raw data. The forecast is flat (the level model has no trend), extending the last estimated level forward — appropriate only when there is genuinely no trend.

## Related Techniques
- *(use after)* `local_linear_trend` if the forecast should carry a trend rather than stay flat.
- *(alternatives)* `local_linear_trend` (adds a slope); `structural_ts` (adds seasonality and cycles); `kalman_filter`/`kalman_smoother` for the general state-space treatment.

## Technical Detail
Estimation is statsmodels `UnobservedComponents` with a local-level specification, fit by maximum likelihood; the reported level is the smoothed state (using the full series). The signal-to-noise ratio is the ratio of the level (state) variance to the observation variance. Multi-step forecasts are flat at the final level, with intervals that widen with the horizon.
*Reference run:* nile_river.csv (100 annual observations), Balanced — signal-to-noise ratio 0.10 (observation variance 15,009 versus level variance 1,518), smoothed final level 1,112, RMSE 161.
