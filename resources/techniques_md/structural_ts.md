# Structural Time Series (Basic Structural Model)

## What It Does

The Basic Structural Model (BSM) decomposes a time series into interpretable unobserved components -- **trend**, **seasonal**, **cycle**, and **irregular** -- using a state space framework. Unlike classical decomposition, each component is modeled as a stochastic process, allowing the trend and seasonal patterns to evolve over time. The Kalman filter and smoother extract these components optimally.

## When to Use It

- You want a model-based decomposition where components can change over time
- You need to combine decomposition with forecasting in a single coherent framework
- You want proper uncertainty quantification for each component
- Your seasonal pattern evolves gradually (strengthening, weakening, or shifting phase)
- You need to handle missing data naturally (the Kalman filter skips missing observations)

## Key Assumptions

- The series can be meaningfully decomposed into additive trend, seasonal, cycle, and irregular components
- Each component follows a specified stochastic process (random walk, trigonometric seasonal, etc.)
- Disturbances across components are mutually independent
- The disturbance variances are constant over time
- The seasonal period is known in advance

## Outputs

- **Smoothed components**: trend, seasonal, cycle, and irregular, each with confidence bands
- **Forecasts** with prediction intervals, built from extrapolating each component
- **Estimated hyperparameters**: the variance of each component's disturbance
- **Diagnostic statistics**: residual tests for normality, independence, and homoskedasticity
- **Signal extraction**: the best estimate of each component given all data

## Technical Details

**Full BSM formulation**: The observation is `y_t = mu_t + gamma_t + psi_t + epsilon_t`, where:

- `mu_t` is the trend (local linear trend model)
- `gamma_t` is the seasonal component
- `psi_t` is the cycle component (optional)
- `epsilon_t ~ N(0, sigma_epsilon^2)` is the irregular

**Trend component** (local linear trend):
- `mu_t = mu_{t-1} + nu_{t-1} + eta_t`, `eta_t ~ N(0, sigma_eta^2)`
- `nu_t = nu_{t-1} + zeta_t`, `zeta_t ~ N(0, sigma_zeta^2)`

**Seasonal component** (trigonometric form for period s):

For each harmonic frequency `j = 1, ..., floor(s/2)`:
```
(gamma_j,t   )   (cos(lambda_j)   sin(lambda_j)) (gamma_j,t-1   )   (omega_j,t  )
(gamma_j,t^* ) = (-sin(lambda_j)  cos(lambda_j)) (gamma_j,t-1^* ) + (omega_j,t^*)
```

where `lambda_j = 2*pi*j/s` and `omega_j,t, omega_j,t^* ~ N(0, sigma_omega^2)`.

The total seasonal effect is `gamma_t = sum_{j=1}^{floor(s/2)} gamma_j,t`.

This representation allows each harmonic component of the seasonal pattern to evolve independently. When `sigma_omega^2 = 0`, the seasonal pattern is fixed (deterministic). When `sigma_omega^2 > 0`, it evolves slowly.

**Cycle component** (stochastic cycle):
```
(psi_t   )       (cos(lambda_c)   sin(lambda_c)) (psi_{t-1}   )   (kappa_t  )
(psi_t^* ) = rho (-sin(lambda_c)  cos(lambda_c)) (psi_{t-1}^* ) + (kappa_t^*)
```

where `rho` is the damping factor (0 < rho < 1), `lambda_c` is the cycle frequency (determining the cycle period as `2*pi/lambda_c`), and `kappa_t, kappa_t^* ~ N(0, sigma_kappa^2)`.

**State space form**: All components are stacked into a single state vector. The state dimension is 2 (trend) + s-1 (seasonal) + 2 (cycle, if included). The Kalman filter and smoother operate on this combined system.

**Parameter estimation**: The hyperparameters (sigma_epsilon^2, sigma_eta^2, sigma_zeta^2, sigma_omega^2, rho, lambda_c, sigma_kappa^2) are estimated by maximizing the log-likelihood via numerical optimization. Some parameters may be set to zero to simplify the model (e.g., fixed seasonal, deterministic trend).

**Advantages over classical decomposition**: (1) Components can evolve. (2) Missing data is handled automatically. (3) Proper prediction intervals. (4) Model selection via information criteria. (5) Diagnostic tests for model adequacy.

## Interpretation

structural_ts runs emit a two-tier Interpretation block with a single parameterized Tier 1 template that dynamically cites the active components.

**Plain-Language Finding (Tier 1)** - active-components list (level, trend, seasonal, cycle, AR) rendered in prose form, fit RMSE vs seasonal-naive baseline, end-of-horizon trend clause, dominant component by variance share with its percentage.

**Technical Interpretation (Tier 2)** - UCM component-by-component disclosure, per-component variance shares, AIC / BIC / log-likelihood, Durbin-Watson residual autocorrelation diagnostic. When level dominates (> 80%) and trend variance is near-zero, the Tier 2 notes the UCM collapses to a simpler local_level specification with seasonal-plus-cycle refinement.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= seasonal-naive baseline.
- Component variance collapsed (< 1e-8 x max_variance) - names the specific component that collapsed and recommends refitting without it.
- Residual normality rejection (JB p < 0.05).
- Residual Ljung-Box rejection - consider enabling additional components (AR, cycle) or extending the seasonal specification.
