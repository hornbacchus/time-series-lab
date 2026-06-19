## What It Does
The Kalman smoother estimates the hidden state of a linear state-space model using the *entire* series — at each point it uses both past and future observations to produce the best possible estimate of where the state was. Where the Kalman filter is causal (each estimate uses only data up to that point), the smoother is *retrospective*: it goes back and revises every estimate with the benefit of hindsight, so its historical estimates are more accurate and less uncertain than the filter's.

## When to Use It
- You're analyzing a completed series (not streaming) and want the most accurate estimate of its past states.
- You want to reconstruct the historical level/trend/components with the full series informing each point.
- You want lower uncertainty on early estimates than real-time filtering can give.
- Use the smoother for retrospective/historical analysis; use `kalman_filter` for real-time estimation; use `particle_filter` for nonlinear models.

## How to Read the Result
The output is the smoothed state path, its standard errors, and a decomposition of the historical disturbances. The smoothed estimate uses the whole series, so it improves most on the filter early in the sample where the filter had little data: on the Nile series the average absolute difference between the smoothed and filtered estimates is 32.2 — that gap *is* the value the hindsight adds. The smoothed standard errors are never larger than the filtered ones, and the two estimates coincide at the final point (where "all data up to now" and "all data" are the same), which is why smoothed and filtered forecasts match. The disturbance smoother attributes the historical shocks to the state versus the observation noise.

## Related Techniques
- *(use after)* use the smoothed components for historical decomposition or shock attribution.
- *(alternatives)* `kalman_filter` (real-time, causal); `particle_filter` (nonlinear/non-Gaussian); `structural_ts` for a component-decomposition framing.

## Technical Detail
The smoother runs the Kalman filter forward, then a backward recursion (the Rauch-Tung-Striebel smoother) that conditions each state estimate on the full series. The smoothed state at time t conditions on all observations through time T; the smoothed standard errors are no larger than the filtered ones, and the two coincide at t = T. The same state-space templates and custom-matrix option as the filter apply. A disturbance smoother attributes the estimated shocks to the state and observation equations.
*Reference run:* nile_river.csv (100 annual observations), Balanced — smoothed final level 1,112 (standard error 63.8), mean absolute smoothed-minus-filtered difference 32.2 (the retrospective revision), disturbance smoother computed.
