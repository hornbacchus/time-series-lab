# Particle Filter

## What It Does

The particle filter (Sequential Monte Carlo) estimates the hidden state of a dynamic system when the standard Kalman filter cannot be used -- typically because the system is **nonlinear**, the noise is **non-Gaussian**, or both. It represents the state probability distribution using a set of weighted random samples (particles) and updates them as new observations arrive, providing a flexible approach to sequential Bayesian inference.

## When to Use It

- The state space model is nonlinear (e.g., the state evolves via a nonlinear function)
- The noise distributions are non-Gaussian (e.g., heavy-tailed, skewed, or multimodal)
- The Kalman filter assumptions are violated and the Extended/Unscented Kalman filters are insufficient
- You need to estimate states in regime-switching models, stochastic volatility models, or other complex dynamic systems
- You want a general-purpose sequential Bayesian estimation method

## Key Assumptions

- A generative model is available: you can simulate the state forward and evaluate the likelihood of observations given the state
- The state dimension is moderate (particle filters struggle in high dimensions, typically above 10-20)
- Enough particles are used to adequately represent the posterior distribution
- The proposal distribution is reasonably close to the true posterior (for efficiency)

## Outputs

- **Weighted particle cloud**: a set of state samples and weights representing the posterior at each time
- **Filtered state estimate**: weighted mean (or median) of the particles at each time
- **Posterior uncertainty**: captured by the spread of particles (variance, quantiles, full distribution)
- **Marginal likelihood estimate**: useful for model comparison and parameter estimation
- **Effective sample size (ESS)**: a diagnostic measuring how evenly weights are distributed

## Technical Details

**Generic particle filter (Sequential Importance Resampling, SIR)**:

Setup: N particles `{x_0^{(i)}}_{i=1}^{N}` drawn from the prior `p(x_0)`, each with weight `w_0^{(i)} = 1/N`.

For each time step t = 1, 2, ...:

1. **Predict (propagate)**: For each particle i, sample `x_t^{(i)} ~ q(x_t | x_{t-1}^{(i)}, y_t)`, where `q` is the proposal distribution. The simplest choice (bootstrap filter) uses the state transition prior: `x_t^{(i)} ~ p(x_t | x_{t-1}^{(i)})`.

2. **Update (weight)**: Compute importance weights. For the bootstrap filter:
   `w_t^{(i)} = p(y_t | x_t^{(i)})`
   Normalize: `W_t^{(i)} = w_t^{(i)} / sum_j w_t^{(j)}`

3. **Resample**: If the effective sample size `ESS = 1 / sum_i (W_t^{(i)})^2` falls below a threshold (e.g., N/2), resample N particles from the current set with probabilities proportional to their weights. This eliminates particles with negligible weights and duplicates high-weight particles.

**Filtered estimate**: `E[x_t | y_{1:t}] approx sum_i W_t^{(i)} x_t^{(i)}`

**Resampling schemes**:
- **Multinomial**: simple random sampling with replacement. High variance.
- **Systematic**: a single random number determines all selections. Lower variance.
- **Stratified**: divide [0,1] into N strata, one random number per stratum. Good balance.
- **Residual**: deterministically replicate particles with weights > 1/N, then sample the remainder.

**Weight degeneracy**: A fundamental problem where after a few steps, one particle accumulates nearly all the weight. Resampling mitigates this but causes **sample impoverishment** (many identical particles). The auxiliary particle filter and optimal proposal distributions help address these issues.

**Marginal likelihood**: The product of mean likelihoods across time steps gives an unbiased estimate: `p(y_{1:T}) approx prod_{t=1}^{T} (1/N sum_i w_t^{(i)})`. This is used for parameter estimation via Particle MCMC (PMCMC).

**Computational cost**: O(N) per time step (times the cost of simulating one state transition and evaluating one likelihood). Typically N = 100 to 10,000 particles depending on the state dimension and model complexity.

**Rao-Blackwellization**: If part of the state is conditionally linear-Gaussian, use a Kalman filter for that part and particles only for the nonlinear part. This dramatically reduces the number of particles needed.

## Interpretation

particle_filter runs emit a two-tier Interpretation block with a distinct SMC-centric Tier 1 - framed around particle count, ESS utilization, and resampling diagnostics rather than forecast-trajectory or variance-component citations (which the Kalman-family state-space wrappers use).

**Plain-Language Finding (Tier 1)** - model type (local_level / local_level_sv / nonlinear_growth / random_walk_sv), particle count, average effective sample size with adjective band (degenerate / moderate / efficient), resampling event rate, log-likelihood approximation. When minimum ESS drops below 10, Tier 1 flags the weight-collapse tail behavior.

**Technical Interpretation (Tier 2)** - SIR bootstrap algorithm, systematic resampling threshold, per-step sigma_state and sigma_obs, stochastic nature of the log-likelihood approximation, and disclosure that user-supplied nonlinear transitions are not injected (four built-in model types only). Forecast is a posterior-predictive sample path; 90% credible bands are empirical Q5/Q95 quantiles.

**Caveats (Tier 3, conditional)**:
- ESS degeneracy (min_ess < 10) - SMC approximation is unreliable for the affected steps.
- Average ESS/N ratio in 'degenerate' band (< 0.1) - filter is persistently weight-degenerate.
- High resampling rate (> 50% of steps) - the filter spends most of its budget on resampling rather than sequential update.
