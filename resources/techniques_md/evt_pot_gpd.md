# EVT / POT / GPD (Extreme Value Theory)

## What It Does

Extreme Value Theory (EVT) with the Peaks Over Threshold (POT) method models the **tail behavior** of a distribution -- the probability and magnitude of rare, extreme events. By fitting a Generalized Pareto Distribution (GPD) to observations exceeding a high threshold, it provides rigorous estimates of tail risk measures like Value-at-Risk (VaR) and Expected Shortfall (ES) at extreme quantile levels where historical data is scarce.

## When to Use It

- You need to estimate the probability of rare, extreme losses (beyond what the historical sample shows)
- Standard VaR models (normal or t-distribution) underestimate tail risk
- You are computing regulatory capital requirements that focus on extreme quantiles (99.5%, 99.9%)
- Stress testing and scenario analysis require extrapolation into the tails
- You are modeling natural disaster losses, insurance claims, or operational risk events

## Key Assumptions

- A sufficiently high threshold can be chosen above which the GPD approximation is valid
- Exceedances above the threshold are approximately independent (decluster if needed)
- The threshold is high enough for the asymptotic GPD result to hold but low enough to retain sufficient data
- The tail behavior is stationary (or can be made so with conditional models)
- The series does not have infinite variance issues that violate the GPD assumptions

## Outputs

- **GPD parameter estimates**: shape (xi) and scale (sigma) with confidence intervals
- **Tail risk measures**: VaR and Expected Shortfall at extreme quantile levels
- **Return level estimates**: the level expected to be exceeded once in N periods
- **Diagnostic plots**: threshold stability plot, QQ plot, return level plot
- **Threshold selection analysis**: mean residual life plot

## Technical Details

**Theoretical foundation**: The Pickands-Balkema-de Haan theorem states that for a wide class of distributions, the distribution of exceedances over a high threshold u converges to the Generalized Pareto Distribution as u increases:

`P(Y - u <= y | Y > u) -> GPD(y; xi, sigma_u)` as u -> u_F (upper endpoint)

**Generalized Pareto Distribution**:

`G(y; xi, sigma) = 1 - (1 + xi y / sigma)^{-1/xi}` for xi != 0
`G(y; xi, sigma) = 1 - exp(-y / sigma)` for xi = 0

Defined for `y > 0` and `(1 + xi y / sigma) > 0`.

**Shape parameter xi**:
- `xi > 0`: heavy tail (Pareto-type), unbounded. Includes Pareto, Cauchy-like tails. Common for financial losses.
- `xi = 0`: exponential tail (thin tail). Normal, exponential distributions.
- `xi < 0`: bounded tail (short tail). Uniform, beta distributions. The distribution has a finite upper endpoint at `u + sigma / |xi|`.

**POT procedure**:

1. **Threshold selection**: Choose u using:
   - **Mean residual life plot**: Plot `E[Y - u | Y > u]` vs. u. The GPD implies this should be approximately linear above the correct threshold.
   - **Parameter stability plot**: Fit GPD for a range of u values and check where xi and modified scale `sigma - xi*u` stabilize.
   - Rule of thumb: use the top 5-10% of data.

2. **Decluster extremes**: If the data is serially dependent (e.g., financial returns with GARCH effects), cluster consecutive exceedances and take the cluster maximum to ensure approximate independence. Alternatively, fit a GARCH model first and apply EVT to the standardized residuals.

3. **Fit GPD**: MLE for the GPD parameters given exceedances `y_i = Y_i - u`:
   `log L(xi, sigma) = -n_u log(sigma) - (1 + 1/xi) sum_{i=1}^{n_u} log(1 + xi y_i / sigma)`
   where `n_u` is the number of exceedances.

4. **Compute tail risk measures**: For probability level p with `p > P(Y > u) = n_u / n`:
   - **VaR_p**: `u + (sigma / xi) * ((n/(n_u) * (1-p))^{-xi} - 1)`
   - **ES_p**: `VaR_p / (1 - xi) + (sigma - xi * u) / (1 - xi)` (valid for xi < 1)

**Return levels**: The level exceeded on average once every m periods: `z_m = u + (sigma/xi) * ((m * n_u/n)^xi - 1)`.

**Conditional EVT**: Fit a GARCH model to capture time-varying volatility, then apply GPD to the standardized residuals. VaR and ES are then `sigma_t * VaR_{standardized}`, combining dynamic volatility with extreme tail estimation.
