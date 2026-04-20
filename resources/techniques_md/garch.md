# GARCH Model

## What It Does

GARCH (Generalized Autoregressive Conditional Heteroskedasticity) models the time-varying **volatility** (conditional variance) of a time series. Financial returns and many other series exhibit volatility clustering -- periods of high volatility tend to be followed by high volatility, and calm periods by calm periods. GARCH captures this by making the current variance depend on past squared returns and past variances.

## When to Use It

- Financial return series exhibit volatility clustering (large moves followed by large moves)
- You need to estimate time-varying risk for portfolio management or Value-at-Risk
- Residuals from a mean model (ARMA) show ARCH effects (autocorrelation in squared residuals)
- You want to produce prediction intervals that widen during volatile periods
- You need to price options or other derivatives that depend on volatility

## Key Assumptions

- The conditional mean is correctly specified (often a constant or ARMA)
- Volatility is a function of past squared innovations and past conditional variances
- The GARCH process is covariance stationary (the persistence is less than 1)
- The innovation distribution is correctly specified (normal, t, or skewed-t)
- No structural breaks in the volatility process

## Outputs

- **Conditional variance series**: the estimated volatility at each time point
- **Conditional standard deviation**: the time-varying risk measure
- **GARCH parameters**: omega (constant), alpha (ARCH effect), beta (GARCH persistence)
- **Standardized residuals**: for diagnostic checking (should be iid if model is correct)
- **Volatility forecasts** for future periods

## Technical Details

**GARCH(p, q) model**:

Mean equation: `Y_t = mu + e_t`, where `e_t = sigma_t * z_t` and `z_t ~ iid(0, 1)`

Variance equation:
`sigma_t^2 = omega + alpha_1 e_{t-1}^2 + ... + alpha_q e_{t-q}^2 + beta_1 sigma_{t-1}^2 + ... + beta_p sigma_{t-p}^2`

Or: `sigma_t^2 = omega + sum_{i=1}^{q} alpha_i e_{t-i}^2 + sum_{j=1}^{p} beta_j sigma_{t-j}^2`

**GARCH(1,1)** (the workhorse model):
`sigma_t^2 = omega + alpha e_{t-1}^2 + beta sigma_{t-1}^2`

Constraints: `omega > 0`, `alpha >= 0`, `beta >= 0`, `alpha + beta < 1` (stationarity).

**Key properties**:
- **Unconditional variance**: `sigma^2 = omega / (1 - alpha - beta)`
- **Persistence**: `alpha + beta` measures how slowly volatility shocks decay. Values close to 1 indicate high persistence (near IGARCH).
- **Half-life of volatility shocks**: `log(0.5) / log(alpha + beta)`
- **Kurtosis**: GARCH(1,1) generates excess kurtosis even with normal innovations. The unconditional kurtosis is `3 * (1 - (alpha+beta)^2) / (1 - (alpha+beta)^2 - 2*alpha^2)` (when this exists).

**Estimation**: MLE with the conditional log-likelihood:

`log L = sum_t [-0.5 log(2*pi) - 0.5 log(sigma_t^2) - 0.5 e_t^2 / sigma_t^2]`

for Gaussian innovations. For Student-t innovations with nu degrees of freedom:

`log L = sum_t [log(Gamma((nu+1)/2)) - log(Gamma(nu/2)) - 0.5 log((nu-2)*pi) - 0.5 log(sigma_t^2) - (nu+1)/2 * log(1 + e_t^2 / ((nu-2)*sigma_t^2))]`

The variance recursion is initialized with `sigma_1^2 = omega / (1 - alpha - beta)` (unconditional variance) or the sample variance.

**Volatility forecasting**: The h-step-ahead forecast is:

`E[sigma_{t+h}^2 | I_t] = omega / (1 - alpha - beta) + (alpha + beta)^{h-1} (sigma_{t+1|t}^2 - omega / (1 - alpha - beta))`

Forecasts revert to the unconditional variance exponentially with rate `(alpha + beta)`.

**Testing for ARCH effects**: Before fitting GARCH, test for conditional heteroskedasticity:
- **Engle's ARCH-LM test**: Regress squared residuals on their lags and test for joint significance via an F-test or chi-squared test.
- **Ljung-Box test on squared residuals**: Tests for autocorrelation in squared residuals.

## Interpretation

Every GARCH run emits a two-tier plain-language Interpretation block between the one-line Summary and the Warnings section.

**Plain-Language Finding (Tier 1)** - 2-4 sentences. Since GARCH is descriptive rather than a hypothesis test, the actionable is persistence-keyed: high persistence (alpha+beta close to 1) supports short-horizon volatility forecasts but converges slowly to unconditional variance; low persistence supports short-horizon forecasts and converges quickly.

**Technical Interpretation (Tier 2)** - cites the ARCH coefficient alpha, GARCH coefficient beta, their persistence sum, and the derived shock half-life `ln(0.5)/ln(alpha+beta)`. Reports the Ljung-Box test on squared standardized residuals as a model-adequacy check.

**Caveats (Tier 3, conditional)**:
- **Near-IGARCH** (alpha+beta > 0.98) - volatility shocks effectively don't decay; unconditional-variance approximation breaks down.
- **Ljung-Box on squared residuals rejects** - remaining ARCH effects; specification may be under-parameterized.
- **Very low persistence** (alpha+beta < 0.3) - series behaves closer to iid than typical returns; verify residuals.
