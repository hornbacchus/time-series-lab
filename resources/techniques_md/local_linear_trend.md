# Local Linear Trend Model

## What It Does

The local linear trend model extends the local level model by adding a stochastic slope component. Both the level and the slope evolve as random walks, allowing the model to capture time-varying trends where the growth rate itself changes over time. It is equivalent to Holt's linear exponential smoothing when cast in state space form.

## When to Use It

- Your data has a trend that changes direction or speed over time
- You need to separate the current level from the current growth rate
- You want to forecast a trending series with proper uncertainty quantification
- Simple exponential smoothing underfits because it ignores the trend
- You need a building block for more complex structural time series models

## Key Assumptions

- The level and slope each evolve as independent random walks
- Observations are the true level plus Gaussian noise
- There are no seasonal patterns (add a seasonal component for that)
- The disturbance variances are constant over time
- The trend is stochastic, not deterministic (for a fixed slope, set the slope variance to zero)

## Outputs

- **Filtered and smoothed level**: the evolving baseline of the series
- **Filtered and smoothed slope**: the evolving growth rate at each time point
- **Forecasts**: linear extrapolation from the current level and slope, with widening prediction intervals
- **Estimated variances**: for the level disturbance, slope disturbance, and observation noise
- **Decomposition**: separate plots of the level and slope components over time

## Technical Details

**State space formulation**:

State vector: `alpha_t = (mu_t, nu_t)'` where `mu_t` is the level and `nu_t` is the slope.

Observation equation: `y_t = (1, 0) alpha_t + epsilon_t = mu_t + epsilon_t`, where `epsilon_t ~ N(0, sigma_epsilon^2)`

State equation:
```
(mu_t)   (1  1) (mu_{t-1})   (eta_t  )
(nu_t) = (0  1) (nu_{t-1}) + (zeta_t )
```

where `eta_t ~ N(0, sigma_eta^2)` (level disturbance) and `zeta_t ~ N(0, sigma_zeta^2)` (slope disturbance), mutually independent.

So F = [[1,1],[0,1]], H = [1,0], Q = diag(sigma_eta^2, sigma_zeta^2), R = sigma_epsilon^2.

**Special cases**:
- `sigma_zeta^2 = 0`: The slope is constant (deterministic linear trend). Equivalent to Holt's method with damping at the limit.
- `sigma_eta^2 = 0`: The level is driven entirely by the slope; the level disturbance is zero. This is the integrated random walk or smooth trend model.
- `sigma_eta^2 = 0` and `sigma_zeta^2 = 0`: Deterministic linear trend with noise.

**Smooth trend model** (`sigma_eta^2 = 0`): The state equation becomes `mu_t = mu_{t-1} + nu_{t-1}` and `nu_t = nu_{t-1} + zeta_t`. This forces the level to change smoothly (no jumps), producing a very smooth extracted trend. It is equivalent to the Hodrick-Prescott filter when the ratio of observation to slope variance takes a specific value.

**Equivalence to Holt's method**: At steady state, the Kalman filter for the local linear trend model produces updates:
- `mu_t|t = alpha * y_t + (1 - alpha)(mu_{t-1|t-1} + nu_{t-1|t-1})`
- `nu_t|t = beta * (mu_t|t - mu_{t-1|t-1}) + (1 - beta) nu_{t-1|t-1}`

which is exactly Holt's linear method with smoothing parameters `alpha` and `beta` determined by the variance ratios.

**Forecasting**: The h-step-ahead forecast is `y_hat_{T+h|T} = mu_T|T + h * nu_T|T`. The prediction variance grows cubically with h: `Var(y_{T+h} - y_hat_{T+h|T}) = sigma_epsilon^2 + h * sigma_eta^2 + h^2 * sigma_zeta^2 / 3 + higher order terms`. This widening reflects the increasing uncertainty about both the level and the slope at distant horizons.

**Parameter estimation**: Three variance parameters (sigma_epsilon^2, sigma_eta^2, sigma_zeta^2) are estimated by maximizing the log-likelihood from the Kalman filter. Initial state can be estimated or set using diffuse initialization.

## Interpretation

local_linear_trend runs emit a two-tier Interpretation block framed around the three variance components and the slope-adaptivity ratio sigma^2_zeta / sigma^2_eta.

**Plain-Language Finding (Tier 1)** - fit RMSE vs naive baseline, end-of-horizon trend clause, slope-adaptivity adjective band (near-linear / moderately adaptive / highly adaptive) with its consequence sentence and smoothed final slope.

**Technical Interpretation (Tier 2)** - state-space equations with level and slope disturbances, three variance components sigma^2_epsilon / sigma^2_eta / sigma^2_zeta, AIC / RMSE, smoothed final level and slope. Long-horizon forecast variance amplifies cubically with h under the integrated-slope structure.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= naive baseline.
- Slope variance sigma^2_zeta at optimizer floor - the trend is effectively a fixed (non-stochastic) slope; the fitted model behaves as local_level with linear drift.
- Residual normality rejection (JB p < 0.05).
- Residual Ljung-Box rejection - the model leaves structure in the residuals.

The wrapper accepts a `damped` parameter that is not currently wired into the fit; Tier 2 honest-disclosure flags this when the parameter was supplied.
