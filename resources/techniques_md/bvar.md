## What It Does
A Bayesian VAR estimates the same joint dynamics as a standard VAR but applies a Minnesota (Litterman) prior that shrinks the system toward a set of independent random walks. The shrinkage tames the parameter proliferation that makes large VARs overfit, producing more stable forecasts and impulse responses with credible bands. The posterior is available analytically (no MCMC), so it is fast. Outputs are regularized forecasts, posterior impulse responses and variance decompositions, and credible intervals.

## When to Use It
- Your system has many variables and/or many lags relative to the sample, where an unrestricted VAR overfits.
- You want more stable out-of-sample forecasts than OLS VAR gives.
- You want credible bands on impulse responses from a coherent Bayesian posterior.
- Use BVAR over plain `var` whenever the system is large; the shrinkage strength is tunable, so it nests a near-OLS fit (loose prior) and a near-random-walk fit (tight prior).

## How to Read the Result
The shrinkage hyperparameters control the prior. λ1 (overall tightness) is the main dial: smaller pulls the system harder toward the random-walk prior, larger lets the data speak — it is monotone, so reducing it always tightens toward the prior. On the Treasury reference (λ1 0.1), forecast RMSEs are 0.054–0.061 across maturities. The variance decomposition shows own-shock dominance that varies by maturity (at horizon 24, the 2Y's own share is 0.68 versus the 30Y's 0.037). The credible bands come from posterior draws of the coefficients; note that the residual covariance is held at its point estimate, so the bands reflect coefficient uncertainty, not full covariance-parameter uncertainty.

## Related Techniques
- *(use after)* `vecm` if cointegration is present; compare against plain `var` to see the shrinkage effect.
- *(alternatives)* `var` (no shrinkage); `dynamic_factor_model` for a factor-based reduction of a large panel. `bond_yield_forecast` is the flagship BVAR with stochastic volatility for the full yield curve, conditioned on macro projections.

## Technical Detail
The posterior is the analytical Normal-Inverse-Wishart conjugate result under a Minnesota prior — no MCMC. The hyperparameters are λ1 (overall tightness), λ2 (cross-equation shrinkage), and λ3 (lag-decay exponent: 1 harmonic, 2 quadratic). Impulse responses and variance decompositions are formed from Monte-Carlo posterior draws of the coefficients, with the residual covariance held at its point estimate (the audit flags this honestly — coefficient-draw precision, not full covariance propagation). Lag length, draw count, and IRF horizon default to the preset configuration.
*Reference run:* treasury_yields.csv (2Y/5Y/10Y/30Y, 6,146 obs), 4 lags, λ1 0.1, Balanced — BVAR(4) Minnesota with λ1 0.1 / λ2 1.0 / λ3 1.0, 1,000 posterior draws; forecast RMSE 2Y 0.054 / 5Y 0.061 / 10Y 0.058 / 30Y 0.054; 12-step forecast with 90% credible bands; FEVD own-shock share at horizon 24: 2Y 0.68, 30Y 0.037.
