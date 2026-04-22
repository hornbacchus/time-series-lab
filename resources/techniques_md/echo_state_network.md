# Echo State Network

## What It Does

Echo State Networks (ESN) are a type of reservoir computing model for time series forecasting. Unlike traditional recurrent neural networks, the ESN uses a large, fixed, randomly initialized recurrent reservoir and only trains the output weights. The input signal is fed into the reservoir, which transforms it into a high-dimensional dynamical representation. A simple linear readout is then trained to map reservoir states to predictions. This architecture avoids the vanishing gradient problem and trains extremely fast via linear regression.

## When to Use It

- You want a recurrent model that trains in seconds (no backpropagation through time)
- The series has complex nonlinear dynamics that benefit from a high-dimensional representation
- You need a computationally efficient alternative to LSTM/GRU
- The series exhibits chaotic or complex temporal patterns
- You want fast experimentation with different reservoir configurations
- Memory and temporal dependencies matter but full gradient-based RNN training is too slow

## Key Assumptions

- The echo state property holds: the reservoir's internal dynamics are stable and the influence of initial conditions fades over time (requires spectral radius < 1 in practice)
- The reservoir is rich enough (enough neurons) to capture the relevant dynamics
- The input scaling and spectral radius are set appropriately for the signal's dynamic range
- A linear readout from reservoir states is sufficient to approximate the target function
- The series has temporal structure that benefits from recurrent processing

## Outputs

- **Point forecasts** for the specified horizon
- **Reservoir states**: internal activations over time (useful for analysis)
- **Model summary**: reservoir size, spectral radius, leak rate, input scaling, training R-squared

## Technical Details

**Reservoir dynamics**: At each time step `t`, the reservoir state is updated as: `r(t) = (1-alpha) * r(t-1) + alpha * tanh(W_in * u(t) + W * r(t-1))` where `u(t)` is the input, `W_in` is the input weight matrix, `W` is the reservoir weight matrix, and `alpha` is the leak rate. The leak rate controls how quickly the reservoir integrates new information versus retaining past state.

**Echo state property**: The spectral radius `rho(W)` (largest absolute eigenvalue) must be less than 1 for the network to be stable. In practice, `W` is initialized randomly and then scaled: `W = (rho_desired / rho(W_random)) * W_random`. Typical spectral radius values are 0.8-0.99.

**Input weight matrix**: `W_in` is randomly initialized from a uniform distribution and scaled by an input scaling factor. The input scaling controls the nonlinearity regime: small values keep the reservoir in the linear regime of tanh, while large values push it into the saturating regime.

**Readout training**: The output weights `W_out` are trained via ridge regression (regularized least squares): `W_out = Y * R^T * (R * R^T + beta * I)^{-1}` where `R` is the matrix of collected reservoir states, `Y` is the target matrix, and `beta` is the regularization parameter. This is a one-shot computation (no iterative optimization).

**Sparsity**: The reservoir matrix `W` is typically sparse (only 10-20% of connections are non-zero), which improves both computational efficiency and dynamical richness.

**Warm-up**: The first `n_washout` time steps are discarded to allow the reservoir state to wash out the effect of the arbitrary initial state `r(0) = 0`.

**Multi-step forecasting**: Uses teacher forcing during training (actual values fed as input) and free-running (recursive) mode during forecasting where predictions are fed back as inputs.

**Fallback implementation**: When reservoirpy is not installed, a pure numpy implementation creates the reservoir, runs the dynamics, and trains the readout using ridge regression. This fallback is fully functional but may be slower for very large reservoirs.

**Comparison**: ESNs train orders of magnitude faster than LSTMs/GRUs because only the output layer is trained. They perform well on chaotic time series and short-to-medium term forecasting. However, they may underperform deep learning models on very long series where the fixed reservoir lacks sufficient capacity. The randomness of the reservoir means results can vary across initializations (mitigated by the seed parameter).

## Prediction Intervals — important caveat

Machine-learning forecasters do **not** come with native prediction-
interval machinery the way classical models (ARIMA, ETS, state-space)
do. When this technique returns a prediction interval, it is derived
empirically from in-sample residuals using a normal or t approximation —
NOT from a probabilistic forecast distribution.

Consequences:

- The interval width does **not** reflect model uncertainty
  (epistemic uncertainty about the learned parameters) — only
  aleatoric noise captured by the residual distribution.
- Coverage is not guaranteed. On out-of-sample data with regime
  shifts or distribution drift, empirical intervals typically
  under-cover.
- The interval is **symmetric** around the point forecast, which
  mis-represents asymmetric error distributions that ML models
  often produce.

For calibrated intervals on an ML forecast, wrap this technique with
**Conformal Prediction Intervals** — it takes a point-forecast model
and produces distribution-free intervals via a held-out calibration
set. See also **Quantile Regression Forecast** for directly
modeling conditional quantiles.


## Interpretation

Every Echo State Network run emits a two-tier Interpretation block. Inherits C2 forecaster Tier 1; Tier 2 highlights closed-form readout and non-interpretability.

**Tier 1** - names reservoir size, spectral radius rho, leak rate alpha, sparsity, ridge readout regularization. Backend (reservoirpy preferred; numpy fallback).

**Tier 2** - explains closed-form ridge-regression readout (**no loss curve** - unlike other C7 neural specs). Spectral radius < 1.0 satisfies the echo state property. **D9 non-interpretability disclosure**: "Reservoir is a random sparse projection - no feature semantics are learned. Readout coefficients operate on random high-dimensional coordinates rather than original time-series features." Parallels C5 BVAR IRF/FEVD absence.

**Caveats (Tier 3, conditional)**:
- Backend fallback (reservoirpy -> numpy).
- Spectral radius >= 1.0 - echo state property violated.
- n_train < 5 x reservoir_size - readout ridge poorly constrained.
