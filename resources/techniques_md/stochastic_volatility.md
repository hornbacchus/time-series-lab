# Stochastic Volatility Model

## What It Does

Stochastic volatility (SV) models treat the log-variance as a **latent stochastic process** rather than a deterministic function of past observations (as in GARCH). The volatility evolves according to its own random innovation, separate from the return innovation. This provides a more flexible and theoretically appealing model of time-varying volatility, closely aligned with the continuous-time models used in option pricing.

## When to Use It

- You want a volatility model that is more flexible than GARCH and allows independent volatility shocks
- You are connecting discrete-time models to continuous-time diffusion processes for derivatives pricing
- The GARCH assumption that volatility is a deterministic function of past returns seems too restrictive
- You need a model where the correlation between return shocks and volatility shocks can be estimated (leverage)
- Bayesian inference for volatility modeling is preferred

## Key Assumptions

- Log-volatility follows an AR(1) or more general autoregressive process
- The volatility shock is separate from and possibly correlated with the return shock
- The latent volatility process is stationary
- The innovation distributions are correctly specified (typically Gaussian for log-volatility)
- The model can be estimated despite the intractable likelihood (requires simulation-based methods)

## Outputs

- **Smoothed log-volatility series**: the estimated latent volatility path
- **Persistence parameter (phi)**: how strongly current log-volatility depends on past log-volatility
- **Volatility of volatility (sigma_eta)**: how much the volatility itself fluctuates
- **Leverage correlation (rho)**: the correlation between return and volatility innovations
- **Posterior distributions** of all parameters (in Bayesian estimation)

## Technical Details

**Basic SV model**:

Return equation: `Y_t = exp(h_t / 2) * e_t`, where `e_t ~ N(0, 1)`

Log-volatility equation: `h_t = mu + phi * (h_{t-1} - mu) + eta_t`, where `eta_t ~ N(0, sigma_eta^2)`

Here `h_t = log(sigma_t^2)` is the log-variance, `mu` is the long-run mean of log-volatility, `phi` is the persistence (|phi| < 1 for stationarity), and `sigma_eta` is the volatility of volatility.

**Key difference from GARCH**: In GARCH, `sigma_t^2` is a function of observable past returns. In SV, `h_t` has its own independent shock `eta_t`, making it a true latent variable. The likelihood `p(Y_1, ..., Y_T | mu, phi, sigma_eta)` requires integrating over all possible paths of `h_1, ..., h_T`, which is intractable analytically.

**Estimation methods**:

1. **MCMC (Bayesian)**: The most common approach. Uses Gibbs sampling with:
   - Sample `h_1, ..., h_T | Y, mu, phi, sigma_eta` using single-site or multi-move samplers.
   - Kim-Shephard-Chib (1998) approach: Transform `log(Y_t^2) = h_t + log(e_t^2)`. Since `log(e_t^2)` follows a log-chi-squared distribution, approximate it as a mixture of 7-10 normals. Then the model becomes conditionally linear-Gaussian, and the FFBS (Forward Filtering Backward Sampling) algorithm applies.
   - Sample parameters from their conditional posteriors.

2. **Particle filter methods**: Sequential Monte Carlo for online estimation. Particle MCMC (PMCMC) uses particle filters within MCMC to sample parameters.

3. **Quasi-maximum likelihood**: Use the linearized model `log(Y_t^2) = h_t + log(e_t^2)` and treat it as a linear state space model, applying the Kalman filter. Consistent but inefficient.

**SV with leverage**: Allow correlation between return and volatility shocks:
`Corr(e_t, eta_t) = rho`

Negative rho (typically -0.5 to -0.8 for equities) captures the leverage effect: negative returns are associated with increases in volatility.

**Comparison with GARCH**:
- SV is more flexible: volatility has its own independent source of randomness.
- SV connects naturally to continuous-time models (discretization of geometric Brownian motion for volatility).
- GARCH is easier to estimate (closed-form likelihood). SV requires simulation-based methods.
- In forecasting competitions, GARCH and SV often perform similarly for conditional variance prediction.

**Unconditional distribution**: The unconditional variance of `h_t` is `sigma_eta^2 / (1 - phi^2)`. The unconditional distribution of returns is a scale mixture of normals, which produces fat tails.
