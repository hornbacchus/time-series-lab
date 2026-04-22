# Kalman Smoother (Direct Access)

## What It Does

The Kalman smoother computes retrospective, full-sample state estimates for a linear Gaussian state-space model. At each period t, the smoother combines the Kalman filter's forward pass with a backward pass that incorporates all observations y_{1:T}, producing state estimates that are strictly more precise than the filtered counterparts (SE_smoothed ≤ SE_filtered for every state dimension).

This wrapper uses the same four named templates as `kalman_filter` (local_level, local_linear_trend, seasonal, ar1) plus a custom path with user-supplied (Z, T, R, H, Q) matrices. On Balanced and Thorough presets, it additionally emits the smoothed disturbance table (ε̂_t, η̂_t | y_{1:T}) for shock attribution and residual-based diagnostics.

Use `kalman_filter` instead when you need online estimates conditioned on past and current observations only.

## When to Use It

- Historical / retrospective analysis — the smoothed state is the best estimate at each past period using all the information the series contains.
- Shock attribution — the disturbance smoother estimates realized observation and state shocks, useful for decomposing historical movements into specific drivers.
- Early-period state estimation — the smoother materially revises the filter's early-period states once later observations reveal the true level/slope/seasonal trajectory.
- Generating smooth signal extractions for presentation (charts, reports).
- Validating a custom state-space specification by inspecting the smoothed disturbance distribution.

## Key Assumptions

Identical to `kalman_filter`:

- The state dynamics and observation equation are linear and Gaussian.
- Variance components (or the user-supplied H, Q matrices) are stable over the sample.
- Diffuse initialization is acceptable for early-period states, or you supply known initial state and covariance.
- For the template path: MLE-estimated variances are identifiable from the data.
- For the custom path: the user's Z, T, R, H, Q matrices faithfully represent the data-generating process.

## Outputs

- **Forecast** — horizon-step forecast with configurable CI coverage.
- **Smoothed State** — period-by-period smoothed state mean and SE for each state dimension.
- **Smoothed Disturbance** (Balanced / Thorough preset default, or explicit `disturbance_smoother=True`) — observation disturbance and state disturbance smoothed means and SEs at each period.
- **Model Summary** — wrapper kind, template, dimensions, likelihood, AIC, BIC, variance components, RMSE, disturbance-smoother flag.
- **Residual Diagnostics** — Jarque-Bera, Ljung-Box lag-10, Durbin-Watson, RMSE, MAE.

## Technical Details

**State-space equations (general form):**

- Observation equation: `y_t = Z_t s_t + ε_t`, `ε_t ~ N(0, H_t)`
- State equation: `s_t = T_t s_{t-1} + R_t η_t`, `η_t ~ N(0, Q_t)`

This wrapper currently assumes time-invariant Z, T, R, H, Q.

**Smoothing recursion.** After the Kalman filter runs forward through the sample, the Rauch-Tung-Striebel (RTS) smoothing recursion runs backward from t=T to t=1, combining the filtered estimate `ŝ_{t|t}` with a correction term derived from the filtered forecast for t+1. The result is `ŝ_{t|T}` — the retrospective state estimate using all observations. Smoothed state covariances are strictly smaller than the corresponding filtered covariances (pointwise in the positive-semidefinite ordering).

**Disturbance smoother.** On Balanced / Thorough presets (or when `disturbance_smoother=True`), the wrapper additionally computes `ε̂_t | y_{1:T}` and `η̂_t | y_{1:T}` — the smoothed observation and state disturbances. These are the realized shocks conditional on the full sample and are the canonical tool for shock attribution. Their covariances are emitted alongside as SE columns.

**Template path.** Identical to `kalman_filter`: one of `{local_level, local_linear_trend, seasonal, ar1}` routed through `UnobservedComponents`. Variance components estimated by MLE; smoothed states extracted via the `.smoothed_state` and related attributes.

**Custom path.** Identical custom-matrix handling as `kalman_filter` via the shared `_TSLStateSpaceModel(MLEModel)` subclass. This mode is intended for users who have already determined their state-space matrices through prior estimation (in another tool or via theoretical reasoning) and want TSL to perform the state inference. For matrix estimation, use the template path.

**Initialization.** `diffuse` (default), `known`, or `approximate_diffuse`. Same semantics as `kalman_filter`.

**Shape validation (custom path).** Identical to `kalman_filter`.

## Interpretation

kalman_smoother runs emit a two-tier Interpretation block.

**Plain-Language Finding (Tier 1)** — names the wrapper kind (Kalman smoother), series, state dimension, state labels, template name (or custom model), observation count, initialization choice, the final smoothed state value and SE at period T, whether the disturbance smoother was computed, and the horizon forecast trend clause with baseline comparison.

**Technical Interpretation (Tier 2)** — opens with the filter vs smoother disclosure (retrospective y_{1:T} vs online y_{1:t}; smoother always at least as precise as filter), then renders either the state equations (template path) or the custom-matrix disclosure with shape summary and "no free parameters" framing. Discloses initialization choice, MLE variance components (template path), log-likelihood / AIC / BIC, residual diagnostics, and (when computed) the disturbance-smoother paragraph explaining its role in shock attribution. Closes with a forecast-mechanism sentence noting that smoothed and filtered final states coincide, so out-of-sample forecasts are identical to what the filter would produce.

**Caveats (Tier 3, conditional):**
- **Convergence warning** (template path) — MLE optimizer did not fully converge.
- **Residual non-normality** (Jarque-Bera p < 0.05) — Gaussian assumption may not hold.
- **Residual autocorrelation** (Ljung-Box lag-10 p < 0.05) — model leaves structure in residuals.
- **RMSE exceeds baseline** — state-space model does not beat naive on this series.
- **Custom path no-MLE disclosure** — reported log-likelihood reflects user's matrix choices; AIC/BIC degenerate (k=0 free params) and reported for parity only.
- **Smoother-far-from-filter** — fires when mean |smoothed − filtered| exceeds 2× mean filter SE. Indicates the retrospective smoother materially revised the filtered estimates; common when early-period filtered states were noisy and later observations clarified the true trajectory.
