# Kalman Filter

## What It Does

The Kalman filter is a recursive algorithm that estimates the hidden state of a dynamic system from noisy observations. At each time step, it makes a prediction based on the system model, then updates that prediction when a new observation arrives. The result is the optimal (minimum variance) estimate of the state given all observations up to the current time, along with a measure of estimation uncertainty.

## When to Use It

- You need real-time estimation of an unobserved quantity (e.g., true GDP, signal in noise)
- Your system evolves over time and you receive noisy measurements sequentially
- You want to track a changing parameter or state as new data arrives
- You are implementing online forecasting where the model updates with each observation
- You need to compute the likelihood of a state space model for parameter estimation

## Key Assumptions

- The system dynamics and observation process are linear
- The state and observation noise are Gaussian and white (uncorrelated over time)
- The system matrices (transition, observation, noise covariances) are known or have been estimated
- The initial state distribution is known or can be specified (diffuse initialization for unknown initial conditions)

## Outputs

- **Filtered state estimates**: optimal estimate of the state at each time given observations up to that time
- **Filtered state covariances**: uncertainty in the state estimates
- **One-step-ahead forecast** and its variance at each time step
- **Innovation sequence**: the forecast errors (used for model diagnostics and likelihood computation)
- **Log-likelihood**: computed as a byproduct, used for parameter estimation via MLE

## Technical Details

**Linear Gaussian state space model**:

State equation: `x_t = F_t x_{t-1} + B_t u_t + w_t`, where `w_t ~ N(0, Q_t)`

Observation equation: `y_t = H_t x_t + v_t`, where `v_t ~ N(0, R_t)`

where `x_t` is the m-dimensional state vector, `y_t` is the p-dimensional observation, `F_t` is the state transition matrix, `H_t` is the observation matrix, `Q_t` is the state noise covariance, and `R_t` is the observation noise covariance.

**Algorithm** (two steps per time period):

**Predict step** (time update):
- Predicted state: `x_t|t-1 = F_t x_{t-1|t-1} + B_t u_t`
- Predicted covariance: `P_t|t-1 = F_t P_{t-1|t-1} F_t' + Q_t`

**Update step** (measurement update):
- Innovation: `v_t = y_t - H_t x_t|t-1`
- Innovation covariance: `S_t = H_t P_t|t-1 H_t' + R_t`
- Kalman gain: `K_t = P_t|t-1 H_t' S_t^{-1}`
- Updated state: `x_t|t = x_t|t-1 + K_t v_t`
- Updated covariance: `P_t|t = (I - K_t H_t) P_t|t-1`

The Kalman gain `K_t` determines how much the prediction is adjusted by the new observation. When the prediction is very uncertain (large `P_t|t-1`), the gain is high and the observation has a large influence. When the observation is very noisy (large `R_t`), the gain is low and the prediction dominates.

**Log-likelihood computation**: The innovation form of the log-likelihood is:

`log L = -nT/2 * log(2*pi) - 1/2 * sum_{t=1}^{T} [log|S_t| + v_t' S_t^{-1} v_t]`

This is used to estimate unknown parameters (elements of F, H, Q, R) by maximizing `log L` numerically.

**Initialization**: For stationary systems, the initial state can be set to the unconditional mean and covariance: `x_0 = 0` and `P_0 = solution of P = F P F' + Q`. For non-stationary systems, diffuse initialization sets `P_0 = kappa * I` with `kappa -> infinity`, handled by exact diffuse initialization algorithms.

**Numerical stability**: The Joseph form of the covariance update `P_t|t = (I - K_t H_t) P_t|t-1 (I - K_t H_t)' + K_t R_t K_t'` is more numerically stable than the standard form. Square-root filters (UD decomposition) provide additional stability for ill-conditioned problems.
