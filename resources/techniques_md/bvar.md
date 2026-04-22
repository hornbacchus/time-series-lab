# Bayesian VAR (BVAR)

## What It Does

Bayesian VAR combines the standard Vector Autoregression framework with Bayesian prior distributions on the model parameters. This addresses the key weakness of frequentist VARs: the large number of parameters (which grows as k^2 * p for k variables and p lags) leads to overfitting and imprecise estimates. By incorporating prior beliefs about parameter values, BVAR produces shrinkage that improves forecast accuracy, especially in systems with many variables.

## When to Use It

- You are modeling a system with many variables where standard VAR overfits
- You want to include more lags or more variables than a classical VAR can support
- Forecasting accuracy is the primary goal and you want to leverage shrinkage
- You have prior economic knowledge about the likely structure (e.g., each variable is close to a random walk)
- You are working with macroeconomic data where BVAR is the standard tool at central banks

## Key Assumptions

- The VAR structure is appropriate for the system
- The prior distribution reasonably reflects beliefs or provides useful regularization
- The likelihood is well-specified (normally distributed innovations)
- The system is stable (eigenvalues of the companion matrix are inside the unit circle)
- The prior hyperparameters are set appropriately (e.g., through cross-validation or marginal likelihood)

## Outputs

- **Posterior distributions** for all VAR coefficients (point estimates and credible intervals)
- **Forecasts with full posterior predictive distributions** (naturally incorporating parameter uncertainty)
- **Impulse response functions** with credible bands reflecting parameter uncertainty
- **Marginal likelihood** for comparing different prior specifications or model sizes
- **Forecast error variance decomposition** with posterior uncertainty

## Technical Details

**The Minnesota prior (Litterman prior)**: The most widely used BVAR prior, developed at the Federal Reserve Bank of Minneapolis. It centers each variable's own first lag coefficient at 1 (random walk prior) and all other coefficients at 0, with decreasing variance for more distant lags and cross-variable effects.

For the coefficient of lag j of variable m in the equation for variable i:

- Own lag (i = m): prior mean = 1 (for j=1), 0 (for j>1)
- Cross lag (i != m): prior mean = 0

Prior variance: `V(A_{i,m,j}) = (lambda_1 / j^lambda_3)^2` for own lags, and `(lambda_1 * lambda_2 * sigma_i / (j^lambda_3 * sigma_m))^2` for cross lags.

Key hyperparameters:
- `lambda_1` (overall tightness): controls how much coefficients can deviate from the prior. Smaller = more shrinkage.
- `lambda_2` (cross-variable tightness): controls how much information other variables can contribute. Typically 0.5-1.0.
- `lambda_3` (lag decay): how quickly the prior shrinks coefficients at longer lags. Typically 1-2.
- `sigma_i / sigma_m` ratio: scales for different variable units (estimated from univariate AR models).

**Posterior computation**: With a normal prior on the VAR coefficients and a known (or inverse-Wishart) prior on the error covariance, the posterior is available in closed form (normal-inverse-Wishart conjugate family):

`vec(A) | Sigma, Y ~ N(vec(A_post), Sigma (x) V_post)`
`Sigma | Y ~ IW(S_post, v_post)`

where `A_post` and `V_post` are the posterior mean and variance of the coefficient matrix, computed by combining the prior with the OLS estimates weighted by their relative precisions.

**Sum-of-coefficients prior**: An additional prior that the sum of all lag coefficients on each variable in its own equation equals 1. This ensures that unit root behavior in the prior is consistent across lags.

**Dummy observation priors**: The Minnesota prior, sum-of-coefficients prior, and single-unit-root prior can all be implemented by adding "dummy observations" to the data matrix before running OLS. This makes BVAR estimation straightforward.

**Hyperparameter selection**: The marginal likelihood `p(Y | lambda)` is computed in closed form for the conjugate prior and maximized over the hyperparameters. This empirical Bayes approach automatically calibrates the degree of shrinkage.

## Interpretation

Every BVAR run emits a two-tier plain-language Interpretation block.

**Plain-Language Finding (Tier 1)** - inherits the var_model Tier 1 shape: names the lag order, number of variables and their names, effective observations, prior tightness (lambda1 with adjective band tight / moderate / loose), per-variable fit RMSEs, and the horizon + credible-interval coverage level. When IRF/FEVD is computed (Balanced / Thorough preset default, or user override), Tier 1 closes with a pointer to Tier 2 for the structural analysis. When skipped (Fast preset default, or explicitly disabled), Tier 1 notes that IRF/FEVD can be enabled by re-running on a Balanced / Thorough preset.

**Technical Interpretation (Tier 2)** - discloses the Minnesota prior hyperparameters (lambda1, lambda2, lambda3), the analytical Normal-Inverse-Wishart posterior, the number of Monte Carlo draws used to form the credible intervals, BIC approximation, and total parameter count. Critically, discloses that reported intervals are Bayesian credible intervals — they answer "what is the probability the parameter lies in this range given the data and prior" rather than the frequentist "what fraction of resampled intervals would contain the true parameter under repeated sampling."

**Structural analysis (Tier 2, when computed)**:
- **IRF** is computed under Cholesky identification with ordering matching the input variable order. Reported IRF is the posterior median across draws; 90% credible bands are in the Impulse Response data table.
- **FEVD** is reported at horizons [1, 4, 8, 12, 24] (subject to the IRF horizon). Tier 2 cites each variable's own-shock share at the longest horizon (one-decimal precision, e.g., "Real GDP Growth's own shocks account for 50.3% of its forecast-error variance").
- **Σ point-estimate disclosure**: credible bands reflect posterior uncertainty in VAR coefficient draws; innovation covariance Σ is held at its posterior point estimate (a simplification that keeps computational cost bounded). Fuller posterior propagation including Σ uncertainty requires MCMC-based BVAR, which is not yet available in TSL.

When IRF/FEVD is skipped, Tier 2 discloses the reason (Fast preset default, user-disabled, or computation error) and how to enable.

**Caveats (Tier 3, conditional)**:
- Prior tightness lambda1 < 0.05 - posterior is strongly shrunk toward the random-walk prior; forecasts mirror RW-forecasts.
- Prior tightness lambda1 > 0.5 - posterior is close to OLS with little shrinkage; Bayesian regularization benefits muted.
- Total parameters > 20% of effective observations - even with Minnesota shrinkage the fit is data-hungry.
- **IRF credible bands straddle zero at peak lag** (D1, Follow-up 1c) - fires when any cross-variable shock-response pair has a 90% credible band that straddles zero at its peak IRF lag AND the median effect is non-trivial (filtered by 5% of max cross-pair magnitude). These structural channels are not statistically distinguishable from no response under the posterior.
- **Cholesky ordering sensitivity** (D2, Follow-up 1c) - always-fires when IRF/FEVD was computed. Reminds the reader that the recursive identification is ordering-dependent; rearranging variables changes interpretation. Suggests comparing results across multiple plausible orderings for robustness.
