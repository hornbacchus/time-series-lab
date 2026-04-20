# ETS / Holt-Winters Exponential Smoothing

## What It Does

ETS (Error-Trend-Seasonal) is a family of exponential smoothing methods that forecast by applying exponentially decreasing weights to past observations. The Holt-Winters variant adds explicit trend and seasonal components. ETS provides a unified framework covering 30 model variants based on the combination of error type (additive/multiplicative), trend type (none/additive/damped), and seasonal type (none/additive/multiplicative).

## When to Use It

- You need a reliable baseline forecast for univariate time series
- The data shows trend, seasonality, or both
- You want automatic model selection from the ETS family
- You prefer a method that produces well-calibrated prediction intervals
- Your data is too short for complex models but long enough to estimate smoothing parameters (at least two seasonal cycles for seasonal variants)

## Key Assumptions

- The series is univariate and regularly spaced
- Future patterns resemble recent past patterns (exponential smoothing emphasizes recent data)
- For multiplicative error/seasonal models, the data must be strictly positive
- The chosen error structure (additive or multiplicative) matches the data characteristics

## Outputs

- **Point forecasts** for the specified horizon
- **Prediction intervals** at chosen confidence levels (e.g., 80% and 95%)
- **Fitted values** and residuals for the in-sample period
- **Smoothing parameters** (alpha, beta, gamma, phi) and their estimated values
- **Selected model** specification (e.g., ETS(M,Ad,M) for multiplicative error, additive damped trend, multiplicative seasonal)

## Technical Details

The ETS framework uses a state space formulation. Each model is defined by its component types:

- **Error (E)**: Additive (A) or Multiplicative (M)
- **Trend (T)**: None (N), Additive (A), or Additive Damped (Ad)
- **Seasonal (S)**: None (N), Additive (A), or Multiplicative (M)

**Example: ETS(A,A,A) -- additive error, additive trend, additive seasonal**:

Measurement equation: `Y_t = l_{t-1} + b_{t-1} + s_{t-m} + e_t`

State update equations:
- Level: `l_t = l_{t-1} + b_{t-1} + alpha * e_t`
- Trend: `b_t = b_{t-1} + beta * e_t`
- Seasonal: `s_t = s_{t-m} + gamma * e_t`

where `e_t ~ N(0, sigma^2)`, `m` is the seasonal period, `alpha` is the level smoothing parameter, `beta` is the trend smoothing parameter, and `gamma` is the seasonal smoothing parameter.

**Damped trend**: replaces `b_{t-1}` with `phi * b_{t-1}` where `0 < phi < 1`. This causes the trend to flatten over longer horizons, often improving forecast accuracy.

**Model selection**: The information criterion approach fits all admissible models and selects the one with the lowest AICc (corrected Akaike Information Criterion):

`AICc = -2 * log(L) + 2k + 2k(k+1)/(n-k-1)`

where `L` is the maximized likelihood, `k` is the number of parameters, and `n` is the series length.

**Parameter estimation**: Parameters (alpha, beta, gamma, phi) and initial states (l_0, b_0, s_{1-m}, ..., s_0) are estimated by maximizing the likelihood function, which for additive errors is based on the Gaussian density of the one-step-ahead forecast errors. Constraints ensure stationarity and invertibility: `0 < alpha < 1`, `0 < beta < alpha`, `0 < gamma < 1 - alpha`, `0.8 < phi < 0.98`.

**Prediction intervals**: Generated analytically for additive error models using the accumulated effect of future errors on forecasts. For multiplicative error models, simulation-based intervals are used since the forecast distribution is non-Gaussian.

## Interpretation

The wrapper services two user-facing technique IDs — `ets` and `holt_winters` — via distinct Interpretation specs that read the same fitted output but frame it differently.

### ETS framing (`ets` technique_id)

**Plain-Language Finding (Tier 1)** - component code "ETS(trend,seasonal)" composed from wrapper output (error component not separately exposed by the statsmodels ExponentialSmoothing path). Fit RMSE vs seasonal-naive baseline. Rationale sentence grounds the multiplicative-seasonal choice on strictly-positive series.

**Technical Interpretation (Tier 2)** - smoothing parameters (level alpha, trend beta, seasonal gamma, damping phi), damping flag, AIC / RMSE, and the state-space vs Holt-Winters equivalence note.

### Holt-Winters framing (`holt_winters` technique_id)

**Plain-Language Finding (Tier 1)** - trend type (additive / multiplicative / none), seasonal type, seasonal period, damping flag. Fit RMSE vs seasonal-naive baseline.

**Technical Interpretation (Tier 2)** - updating equations in citation form (multiplicative or additive per seasonal type), smoothing parameters, AIC / RMSE. Undamped long-horizon runs include explicit trend-amplification risk advice.

**Caveats shared across both framings (Tier 3, conditional)**:
- Fit RMSE >= naive baseline.
- Multiplicative seasonal on non-positive data.
- Trend smoothing beta ~ 0 (trend frozen at initialization; includes actionable refit advice).
- Holt-Winters only: undamped trend over horizon > 2x seasonal period.
- ETS only: level smoothing alpha > 0.9 (random-walk level).
