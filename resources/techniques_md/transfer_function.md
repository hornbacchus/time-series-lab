# Transfer Function Model

## What It Does

A transfer function model captures the **dynamic, lagged relationship** between an input series (cause) and an output series (effect). Unlike ARIMAX, where exogenous variables enter contemporaneously, transfer function models allow the input to affect the output through a distributed lag structure described by a rational polynomial filter. This lets you model situations where the effect of an input unfolds gradually over multiple time periods.

## When to Use It

- An input variable (e.g., advertising, policy change, price) affects the output with a delayed and distributed effect
- You need to model the shape and duration of how an impulse in one series propagates to another
- You want to separate the dynamic input effect from the noise (ARMA) structure of the output
- Intervention analysis needs to model the response pattern to a known event
- Cross-correlation analysis suggests a lagged relationship between two series

## Key Assumptions

- The input-output relationship is linear and time-invariant
- The input variable is exogenous (not influenced by the output) or at least predetermined
- The noise component of the output follows a stationary ARMA process
- Future values of the input are known or can be specified for forecasting
- The transfer function is stable (the effect of an input eventually dies out or reaches a constant)

## Outputs

- **Transfer function weights**: the impulse response showing how the output responds over time to a unit change in the input
- **Numerator (omega) and denominator (delta) polynomials** defining the transfer function shape
- **Dead time (b)**: the number of periods before the input first affects the output
- **Noise model coefficients**: ARMA parameters for the unexplained component
- **Forecasts** conditional on future input values

## Technical Details

**Model formulation**: The transfer function model for output `Y_t` and input `X_t` is:

`Y_t = c + v(B) X_{t-b} + N_t`

where:
- `v(B) = omega(B) / delta(B)` is the transfer function filter
- `omega(B) = omega_0 - omega_1 B - ... - omega_s B^s` (numerator polynomial of order s)
- `delta(B) = 1 - delta_1 B - ... - delta_r B^r` (denominator polynomial of order r)
- `b` is the dead time (delay before input affects output)
- `N_t` follows an ARIMA process: `phi(B)(1-B)^d N_t = theta(B) a_t`

**Impulse response weights**: The transfer function `v(B)` can be expanded as an infinite polynomial: `v(B) = v_0 + v_1 B + v_2 B^2 + ...`, where `v_j` represents the effect on `Y` at time `t` of a unit impulse in `X` at time `t-b-j`. The rational form `omega(B)/delta(B)` provides a parsimonious parameterization of this potentially infinite response.

**Identification (Box-Jenkins approach)**:

1. **Prewhiten the input**: Fit an ARIMA model to `X_t` and compute the residuals `alpha_t`.
2. **Apply the same filter to the output**: Filter `Y_t` through the same ARIMA model to get `beta_t`.
3. **Cross-correlate**: Compute the cross-correlation function (CCF) between `alpha_t` and `beta_t`. The pattern of significant cross-correlations reveals the dead time `b` and suggests the orders `r` and `s`.
4. **Determine transfer function orders**: The CCF pattern maps to (r, s, b):
   - CCF starting at lag b with exponential decay suggests r=1, s=0.
   - CCF with a single spike at lag b suggests r=0, s=0.
   - CCF starting at lag b with two spikes then decay suggests r=1, s=1.
5. **Identify noise model**: After estimating the transfer function, examine the residuals `N_t = Y_t - v(B) X_{t-b}` and fit an ARMA model.

**Estimation**: Joint MLE of transfer function parameters (omega, delta) and noise model parameters (phi, theta). The optimization is nonlinear due to the denominator polynomial `delta(B)`, requiring iterative algorithms (Gauss-Newton or Marquardt).

**Stability condition**: All roots of `delta(B) = 0` must lie outside the unit circle, ensuring the impulse response weights decay over time rather than explode.
