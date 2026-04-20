# ARIMA

## What It Does

ARIMA (AutoRegressive Integrated Moving Average) models a time series as a combination of its own past values (autoregressive terms), past forecast errors (moving average terms), and differencing to achieve stationarity. It is the foundational model for univariate time series analysis and forecasting, capable of capturing a wide range of temporal dynamics in non-seasonal data.

## When to Use It

- Your data shows autocorrelation structure but no strong seasonal pattern
- You need a principled statistical model with well-understood properties
- You want to produce forecasts with proper prediction intervals based on likelihood theory
- The series can be made stationary through differencing (it is not inherently explosive)
- You have at least 30-50 observations for reliable parameter estimation

## Key Assumptions

- The series is univariate and equally spaced
- After differencing `d` times, the series is stationary (constant mean and variance over time)
- The residuals (innovations) are uncorrelated white noise with constant variance
- The model is correctly specified (right orders of p and q)
- No structural breaks or regime changes occur during the sample period

## Outputs

- **Point forecasts** for the specified horizon
- **Prediction intervals** at chosen confidence levels
- **Estimated coefficients** for AR and MA terms with standard errors and significance tests
- **Residual diagnostics**: ACF/PACF of residuals, Ljung-Box test for remaining autocorrelation
- **Information criteria**: AIC, BIC for model comparison

## Technical Details

An ARIMA(p, d, q) model has three components:

- **AR(p)** -- autoregressive of order p: the current value depends linearly on the previous `p` values.
- **I(d)** -- integrated of order d: the series is differenced `d` times to achieve stationarity.
- **MA(q)** -- moving average of order q: the current value depends linearly on the previous `q` forecast errors.

**Model equation**: Let `W_t = (1-B)^d Y_t` be the d-th difference of the original series, where `B` is the backshift operator (`B Y_t = Y_{t-1}`). Then:

`W_t = c + phi_1 W_{t-1} + ... + phi_p W_{t-p} + e_t + theta_1 e_{t-1} + ... + theta_q e_{t-q}`

Or in operator notation: `phi(B) W_t = c + theta(B) e_t`, where `phi(B) = 1 - phi_1 B - ... - phi_p B^p` and `theta(B) = 1 + theta_1 B + ... + theta_q B^q`.

**Stationarity and invertibility conditions**: All roots of `phi(B) = 0` must lie outside the unit circle (stationarity of the differenced series). All roots of `theta(B) = 0` must lie outside the unit circle (invertibility, ensuring unique representation).

**Model identification (Box-Jenkins methodology)**:
1. **Determine d**: Use unit root tests (ADF, KPSS) or visual inspection to decide the differencing order.
2. **Identify p and q**: Examine the ACF and PACF of the differenced series. AR(p) shows PACF cutting off at lag p; MA(q) shows ACF cutting off at lag q. Mixed ARMA patterns show gradual decay in both.
3. **Estimate parameters**: Maximum likelihood estimation (MLE) or conditional least squares. The log-likelihood is: `log L = -n/2 * log(2*pi*sigma^2) - 1/(2*sigma^2) * sum(e_t^2)`, where the innovations `e_t` are computed recursively.
4. **Diagnose**: Check residuals for white noise using ACF plots and the Ljung-Box test: `Q = n(n+2) * sum_{k=1}^{h} r_k^2 / (n-k) ~ chi^2(h-p-q)`.

**Forecasting**: Forecasts are computed recursively. For `h` steps ahead, future errors are set to zero (their expected value), and future observations are replaced by their forecasts. Prediction intervals widen with the horizon: `Var(e_t(h)) = sigma^2 * sum_{j=0}^{h-1} psi_j^2`, where `psi_j` are the coefficients of the infinite MA representation.

## Interpretation

Every manual-order ARIMA run emits a two-tier plain-language Interpretation block.

**Plain-Language Finding (Tier 1)** - names the fitted order (p,d,q), observations, horizon, fit RMSE vs the last-value naive baseline with percentage delta, and the end-of-horizon forecast level. Uses the three-rule ``horizon_trend_pct`` fallback: when the latest observation is near-zero relative to the series' scale (common for growth-rate series), the clause reads "forecast ends at X, starting from Y" rather than a percentage.

**Technical Interpretation (Tier 2)** - discloses the user-chosen (p,d,q), the differencing level applied, AIC / BIC / in-sample RMSE, and residual Ljung-Box at lag 10. Flags that manual ARIMA does not search alternatives; recommends auto_arima to validate the order choice.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= naive baseline - the model does not beat naive.
- Ljung-Box rejects white-noise - ARMA structure is inadequate.
- (p+q) > sqrt(n_obs) - order may be overfitted.
- d >= 2 - verify non-stationarity of the once-differenced series.
