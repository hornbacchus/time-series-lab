# Kalman Smoother

## What It Does

The Kalman smoother refines the state estimates produced by the Kalman filter by using information from the **entire** time series, not just past observations. While the filter gives the best estimate at time t using data up to t, the smoother gives the best estimate at time t using data from the whole series (past, present, and future). This produces more accurate and smoother state trajectories.

## When to Use It

- You have collected all the data and want the best possible state estimates for historical periods
- You are extracting trend, cycle, or other components from a completed time series
- You need to impute missing values using information from both before and after the gap
- You are estimating parameters via the EM algorithm (the E-step requires smoothed states)
- You want to produce a smooth signal from noisy data for retrospective analysis

## Key Assumptions

- The same assumptions as the Kalman filter: linear Gaussian state space model
- The entire time series is available (not an online/real-time setting)
- System matrices are known or estimated (often using the filter's likelihood first)
- The model is correctly specified for both the forward and backward information to be valid

## Outputs

- **Smoothed state estimates**: optimal estimate of the state at each time given ALL observations
- **Smoothed state covariances**: reduced uncertainty compared to filtered estimates
- **Smoothed cross-covariances**: covariance between states at adjacent time steps (needed for EM)
- **Disturbance estimates**: smoothed estimates of the state and observation noise at each time

## Technical Details

**Rauch-Tung-Striebel (RTS) smoother**: The most common fixed-interval smoother. It runs the Kalman filter forward through the data, then performs a backward pass to incorporate future information.

**Forward pass**: Run the standard Kalman filter to obtain filtered estimates `x_t|t` and `P_t|t`, and predicted estimates `x_t|t-1` and `P_t|t-1` for t = 1, ..., T.

**Backward pass** (from t = T-1 down to t = 1):

- Smoother gain: `L_t = P_t|t F_{t+1}' P_{t+1|t}^{-1}`
- Smoothed state: `x_t|T = x_t|t + L_t (x_{t+1|T} - x_{t+1|t})`
- Smoothed covariance: `P_t|T = P_t|t + L_t (P_{t+1|T} - P_{t+1|t}) L_t'`

Starting condition: `x_T|T` and `P_T|T` from the last filter step.

**Interpretation**: The smoother gain `L_t` determines how much the filtered estimate at time t is adjusted by the discrepancy between the smoothed and predicted estimates at time t+1. If the future data suggests the state was different from what the filter estimated, the smoother corrects backward.

**Cross-covariance**: For the EM algorithm, the lag-one cross-covariance is needed:

`P_{t,t-1|T} = P_t|t L_{t-1}' + L_t (P_{t+1,t|T} - F_{t+1} P_t|t) L_{t-1}'`

with `P_{T,T-1|T} = (I - K_T H_T) F_T P_{T-1|T-1}`.

**Disturbance smoother** (de Jong, Koopman): Instead of smoothing the states, the disturbance smoother directly estimates the state noise `w_t` and observation noise `v_t`:

Backward recursion using auxiliary quantities `r_t` and `N_t`:
- `r_{t-1} = H_t' S_t^{-1} v_t + L_t' r_t` (where `L_t = F_t - F_t K_t H_t` here is the filter transition)
- `N_{t-1} = H_t' S_t^{-1} H_t + L_t' N_t L_t`

Smoothed disturbances: `w_hat_t = Q_t r_t` and `v_hat_t = R_t (S_t^{-1} v_t - K_t' r_t)`.

**Computational cost**: The smoother adds a backward pass with the same O(m^3) per step cost as the filter, so total cost is O(T * m^3) for both filter and smoother combined, where m is the state dimension.

**Comparison with filter**: Smoothed estimates always have lower variance than filtered estimates: `P_t|T <= P_t|t` (in the positive semidefinite sense). The improvement is largest in the middle of the series and smallest at the endpoints.
