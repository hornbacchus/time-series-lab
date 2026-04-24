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

## Declustering (Ferro-Segers 2003, opt-in)

Financial-returns POT wrappers violate the independence assumption because volatility clustering produces runs of consecutive exceedances belonging to a single event. Standard GPD MLE on clustered exceedances treats dependent observations as though they carried fresh information and therefore underestimates tail risk.

Set `decluster=True` to apply the **Ferro-Segers (2003) intervals** method. The estimator is parameter-free (no fixed run-gap choice) and proceeds in three steps:

1. **Extremal-index estimation**. Given inter-exceedance times `T_i = t_{i+1} - t_i`, Ferro-Segers estimate the extremal index theta via a branching formula:
   - If `max(T_i) <= 2`: `theta_hat = 2 * (sum T_i)^2 / ((N_u - 1) * sum T_i^2)`
   - Else: `theta_hat = 2 * (sum (T_i - 1))^2 / ((N_u - 1) * sum (T_i - 1) * (T_i - 2))`
   The estimator is clamped to the interval `[1e-6, 1.0]`. An extremal index of 1.0 indicates independent exceedances; values near zero indicate severe clustering.

2. **Cluster identification**. The number of independent clusters is `K = ceil(theta_hat * N_u)`, capped at `N_u`. The `K - 1` largest inter-exceedance gaps partition the exceedance sequence into `K` segments; the **cluster peak** is the maximum exceedance within each segment.

3. **Re-fit GPD on cluster peaks**. The `K` peak excesses (cluster_peak - u) are treated as independent observations and passed to `scipy.stats.genpareto.fit`. Post-declustering VaR / ES use the cluster-peak rate `zeta_u = K / n` (Coles 2001 standard) in place of the pre-declustering exceedance rate.

The wrapper emits both the pre- and post-declustering fits in a dedicated **Declustering Summary** output table, along with the 99% VaR bias correction (post minus pre, both absolute and percent). The Tier 2 rendering contrasts the two fits and names the severity of clustering (mild / notable / severe). Five Tier 3 triggers cover severe clustering (`theta < 0.3`), extreme reduction ratio (`K / N_u < 0.3`), few cluster peaks for reliable MLE (`K < 30`), material VaR bias correction (`|delta| > 20%` at 99%), and graceful fallback when declustering is requested but insufficient exceedances or a runtime error forces the pre-declustering fit.

Additionally, the wrapper always renders a **Mean Residual Life (MRL) diagnostic** comparing the empirical mean excess at the threshold against the GPD-implied value `(sigma + xi * u) / (1 - xi)`. A notable mismatch flags possible threshold or model mis-specification independent of the declustering path.

When `decluster=False` (default), the legacy time-series honest-disclosure fires with updated actionable text pointing at `decluster=True` as the remedy.

## Interpretation

Every EVT-POT-GPD run emits a two-tier plain-language Interpretation block with a distribution-fit-with-tail-parameters Tier 1 shape.

**Plain-Language Finding (Tier 1)** - leads with the tail (left or right), threshold quantile and its value in series units, the exceedance count, the GPD shape parameter ξ with its tail-domain label (heavy-tailed Frechet, bounded Weibull, or approximately exponential), the scale parameter σ, and canonical VaR / Expected Shortfall quantiles (99% and 99.9% when available). Confidence levels render integer-when-whole per the platform convention.

**Technical Interpretation (Tier 2)** - discloses the POT methodology, explicitly names the Generalized Pareto Distribution (GPD) by name (Convention C), cites the maximum-likelihood fit via scipy.stats.genpareto, reports the Kolmogorov-Smirnov goodness-of-fit p-value, notes the GPD moment-finiteness rule (finite moments only of order less than 1/ξ when ξ > 0), and flags the POT independence assumption as an idealization for time-series data with volatility clustering. Honest-discloses the absence of backtest metrics at the wrapper level.

**Caveats (Tier 3, conditional)**:
- ξ > 0 (heavy tail) - moments of order ≥ 1/ξ are infinite; higher-moment estimates from finite samples are unreliable.
- 10 ≤ n_exceedances < 30 - above the wrapper's hard minimum but below the reliable-fit rule of thumb; tail-parameter standard errors are wide.
- Time-indexed input with `decluster=False` - POT assumes independent exceedances; volatility clustering can produce runs that violate independence. Points at the `decluster=True` opt-in or a block-maxima (GEV) fit.
- Kolmogorov-Smirnov rejects the GPD fit - threshold may be too low; try raising the threshold quantile or inspecting the mean excess function for a stable-linear region.

**Follow-up 3c triggers (fire only when `decluster=True`)**:
- Extremal index θ < 0.3 - severe clustering; pre-declustering tail estimates substantially underestimate true tail risk. Use the post-declustering VaR / ES from the Declustering Summary table.
- Reduction ratio K / N_u < 0.3 - more than 70% of exceedances were redundant cluster members; declustered sample is small. Consider lowering `threshold_quantile`.
- K < 30 cluster peaks - below the 30-observation rule of thumb for reliable GPD MLE; consider lowering `threshold_quantile` or a GEV fit.
- |99% VaR bias correction| > 20% - material bias. Users reporting regulatory or risk-management VaR should use the post-declustering estimate.
- Declustering requested but fell back - either N_u < 10 (Ferro-Segers unreliable) or a runtime error occurred; wrapper reverts to the pre-declustering fit and discloses the cause.

