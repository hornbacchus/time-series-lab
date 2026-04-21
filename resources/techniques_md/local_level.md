# Local Level Model

## What It Does

The local level model (also called the random walk plus noise model) is the simplest structural time series model. It assumes the observed data is a noisy version of an underlying level that evolves as a random walk. This provides a principled way to extract a smooth, slowly changing signal from noisy observations, equivalent to Simple Exponential Smoothing (SES) when cast in state space form.

## When to Use It

- You want to track a slowly changing underlying level from noisy measurements
- Your data has no trend or seasonal pattern, just a wandering level with noise
- You need a simple baseline state space model before adding complexity
- You want to understand the signal-to-noise ratio in your data
- You are introducing state space modeling concepts and need a minimal example

## Key Assumptions

- The underlying level changes slowly and randomly (random walk)
- Observations are the true level plus independent Gaussian noise
- There is no deterministic trend or seasonal pattern
- The variances of the level disturbance and observation noise are constant over time
- The signal-to-noise ratio is stable

## Outputs

- **Filtered level**: the real-time estimate of the underlying level at each time point
- **Smoothed level**: the retrospective estimate using all data (smoother than filtered)
- **Signal-to-noise ratio**: q = sigma_eta^2 / sigma_epsilon^2, indicating how much the level varies relative to observation noise
- **One-step-ahead forecasts** with prediction intervals
- **Estimated variances** for the level disturbance and observation noise

## Technical Details

**State space formulation**:

Observation equation: `y_t = mu_t + epsilon_t`, where `epsilon_t ~ N(0, sigma_epsilon^2)`

State equation: `mu_t = mu_{t-1} + eta_t`, where `eta_t ~ N(0, sigma_eta^2)`

This is a state space model with scalar state `mu_t`, transition matrix F = 1, observation matrix H = 1, state noise variance Q = `sigma_eta^2`, and observation noise variance R = `sigma_epsilon^2`.

**Kalman filter for the local level model**:

Prediction: `mu_t|t-1 = mu_{t-1|t-1}`, `P_t|t-1 = P_{t-1|t-1} + sigma_eta^2`

Update: `K_t = P_t|t-1 / (P_t|t-1 + sigma_epsilon^2)`, `mu_t|t = mu_t|t-1 + K_t (y_t - mu_t|t-1)`, `P_t|t = (1 - K_t) P_t|t-1`

As t grows, the Kalman gain converges to a steady-state value `K* = (-sigma_epsilon^2 + sqrt(sigma_epsilon^4 + 4 sigma_eta^2 sigma_epsilon^2)) / (2 sigma_epsilon^2)`.

**Equivalence to SES**: At steady state, the Kalman filter update is `mu_t|t = K* y_t + (1 - K*) mu_{t-1|t-1}`, which is exactly Simple Exponential Smoothing with smoothing parameter `alpha = K*`. The signal-to-noise ratio `q = sigma_eta^2 / sigma_epsilon^2` determines `alpha`:
- q = 0: alpha = 0, the level never changes (constant mean model)
- q -> infinity: alpha -> 1, the level tracks each observation exactly
- Intermediate q: moderate smoothing

**Parameter estimation**: The two unknown parameters `sigma_eta^2` and `sigma_epsilon^2` are estimated by maximizing the log-likelihood computed from the Kalman filter innovations:

`log L = -T/2 log(2pi) - 1/2 sum_{t=1}^{T} [log(S_t) + v_t^2 / S_t]`

where `v_t = y_t - mu_t|t-1` and `S_t = P_t|t-1 + sigma_epsilon^2`.

**Smoothed estimates**: The Kalman smoother applied to this model produces `mu_t|T`, which uses both past and future observations. The smoothed level is less variable than the filtered level and provides the best retrospective signal extraction.

**Diagnostic checking**: Examine the standardized innovations `v_t / sqrt(S_t)` for normality, independence (no autocorrelation), and homoskedasticity. Significant autocorrelation suggests the model needs additional components (trend or seasonal).

## Interpretation

local_level runs emit a two-tier Interpretation block framed around the signal-to-noise ratio q = sigma^2_eta / sigma^2_epsilon.

**Plain-Language Finding (Tier 1)** - fit RMSE vs last-value naive baseline with percentage delta, end-of-horizon trend clause, signal-to-noise ratio q with adjective band (very low / low / moderate / high / very high) and its consequence sentence. The forecast is the smoothed final level extended flat; local_level has no drift component.

**Technical Interpretation (Tier 2)** - state-space equations y_t = mu_t + epsilon_t, mu_t = mu_{t-1} + eta_t, the two variance components sigma^2_epsilon and sigma^2_eta, AIC / BIC / log-likelihood, smoothed final level. Note on smoother-vs-filter state (wrapper uses the retrospective smoother).

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= last-value naive baseline - state-space model does not beat naive; a constant-forecast baseline is competitive.
- Residual normality rejection (JB p < 0.05) - prediction intervals may be mis-calibrated.
