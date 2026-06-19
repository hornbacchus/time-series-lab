## What It Does
The Kalman filter estimates the hidden state of a linear state-space model in real time — at each point it combines the previous state estimate with the new observation to produce the best current estimate, using only data up to that point. It is the foundational recursive estimator for state-space models: exact and optimal when the model is linear with Gaussian noise. The defining feature is that it is *causal* — each estimate uses only the past and present, never the future.

## When to Use It
- You want a real-time (online) estimate of a series' underlying state as data arrives.
- Your model is linear with Gaussian noise (the filter is exact and efficient there).
- You want filtered estimates and one-step-ahead forecasts that only use information available at each point.
- Use the Kalman filter for causal/real-time estimation; use `kalman_smoother` when you can use the whole series to revise past estimates; use `particle_filter` for nonlinear or non-Gaussian models.

## How to Read the Result
The output is the filtered state path, its standard errors, and forecasts. The filtered estimate at each point reflects all data *up to* that point — it is what you would have known in real time. On the Nile series the filtered final level is 1,112 with a standard error of 63.8. Because the filter is causal, its early estimates are necessarily less certain (less data has accumulated), and its forecast simply propagates the final state forward. Choose a state-space template to match the series (local level, local linear trend, seasonal, AR), or supply custom matrices for a bespoke model.

## Related Techniques
- *(use after)* `kalman_smoother` to revise the filtered estimates using the full series (it will reduce the early uncertainty).
- *(alternatives)* `kalman_smoother` (retrospective, uses all data); `particle_filter` (nonlinear/non-Gaussian); `local_level`/`structural_ts` for the specific structural models.

## Technical Detail
The filter is the standard recursive linear-Gaussian state-space filter (statsmodels state space). State-space templates are provided (local level, local linear trend, seasonal, AR(1)), or custom system matrices can be supplied. Estimation uses a diffuse initialization by default. The filtered state at time t conditions on observations through time t; forecasts propagate the final filtered state with horizon-widening intervals.
*Reference run:* nile_river.csv (100 annual observations), Balanced — filtered final level 1,112 (standard error 63.8), converged, local-level template, RMSE 161.
