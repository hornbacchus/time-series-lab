# Prewhitened CCF / Lag Analysis

## What It Does

Prewhitened cross-correlation applies a filtering step before computing the cross-correlation function (CCF) to produce **reliable lag estimates** between two series. By first removing the autocorrelation structure from the input series and applying the same filter to the output, the resulting CCF directly reveals the impulse response function of the relationship, free from the distortions caused by serial correlation in the original data.

## When to Use It

- You need to identify the true lag structure between an input and output series
- Standard CCF is unreliable because both series have strong autocorrelation
- You are preparing to build a transfer function model and need to identify the delay (b), numerator order (s), and denominator order (r)
- You want to separate the effect of the input from the noise dynamics in the output
- Cross-correlation analysis shows many significant lags and you cannot determine the true relationship

## Key Assumptions

- An adequate ARIMA model can be fit to the input series (to whiten it)
- The same ARIMA filter is appropriate for both the input and output (linearity assumption)
- The input is exogenous (not influenced by the output)
- The true relationship is linear and time-invariant
- Residuals after prewhitening are approximately white noise

## Outputs

- **Prewhitened CCF**: clean cross-correlations showing the true impulse response pattern
- **Estimated delay (dead time b)**: when the first significant cross-correlation appears
- **Transfer function order suggestions**: patterns in the CCF indicate (r, s, b) orders
- **Impulse response weights**: the estimated response of the output to a unit impulse in the input
- **Confidence bounds**: reliable significance thresholds for the prewhitened CCF

## Technical Details

**Why standard CCF is unreliable**: If x_t follows an AR(1) process and y_t responds to x_t with a one-period delay, the standard CCF will show significant correlations at many lags (not just lag 1) because each observation of x_t is correlated with its neighbors. The autocorrelation in x_t "smears" the cross-correlation across multiple lags, making it impossible to identify the true lag.

**Prewhitening procedure** (Box-Jenkins method):

1. **Model the input**: Fit an ARIMA model to the input series x_t:
   `phi_x(B)(1-B)^d x_t = theta_x(B) alpha_t`
   where `alpha_t` are white noise residuals.

2. **Apply the same filter to the output**: Transform y_t using the same ARIMA filter:
   `beta_t = phi_x(B)(1-B)^d y_t / theta_x(B)`
   This is NOT fitting an ARIMA model to y_t; it is applying x's filter to y.

3. **Compute the CCF**: Calculate the cross-correlation between `alpha_t` and `beta_t`. Since `alpha_t` is white noise, the CCF `r_{alpha,beta}(k)` is proportional to the impulse response weights `v_k` of the transfer function from x to y:
   `r_{alpha,beta}(k) = (sigma_alpha / sigma_beta) * v_k` for k >= 0

**Interpreting the prewhitened CCF**: The pattern of significant cross-correlations maps directly to the transfer function orders:

| CCF pattern (starting at lag b) | Transfer function |
|---|---|
| Single spike at lag b | v(B) = omega_0 B^b (r=0, s=0) |
| Two spikes then zero | v(B) = (omega_0 - omega_1 B) B^b (r=0, s=1) |
| Exponential decay from lag b | v(B) = omega_0 / (1 - delta_1 B) B^b (r=1, s=0) |
| Spike then exponential decay | v(B) = (omega_0 - omega_1 B) / (1 - delta_1 B) B^b (r=1, s=1) |

**Important details**:
- Only positive lags (k >= 0) in the CCF between alpha and beta are relevant for the transfer function (input leads output).
- Significant negative lags would suggest reverse causality (output leading input) or feedback.
- The scaling factor `sigma_alpha / sigma_beta` converts cross-correlations to impulse response weights.

**After identifying the transfer function**:
1. Estimate the transfer function model: `y_t = v(B) x_{t-b} + N_t`.
2. Compute the residuals `N_t = y_t - v_hat(B) x_{t-b}`.
3. Identify an ARIMA model for N_t using standard Box-Jenkins methodology.
4. Estimate the full model jointly by MLE.

**Practical considerations**:
- The ARIMA model for x_t should produce white noise residuals (check with Ljung-Box).
- If x_t cannot be adequately modeled by ARIMA (e.g., it contains outliers), the prewhitening will be imperfect.
- For multiple inputs, prewhiten each input separately and examine the CCF with the output.
- The method assumes linearity; nonlinear relationships will not be captured.
