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

## Interpretation

Every Stochastic Volatility run emits a two-tier plain-language Interpretation block. Tier 1 inherits the GARCH persistence-band narrative (shared with `garch_model`) with adaptations for SV's latent-state framing.

**Plain-Language Finding (Tier 1)** - names the persistence φ with its adjective band (low / moderate / high / very high, shared with GARCH via the 4-band convention), the volatility shock half-life, and the filtered-volatility dynamic range across the sample. Tier 1 cites the *filtered* volatility path as the forward-causal analog of GARCH's σ_t for cross-spec comparability.

**Technical Interpretation (Tier 2)** - discloses the SV AR(1) log-variance model equations, the quasi-maximum likelihood Kalman-filter inference path, the innovation-distribution choice (Gaussian default or Student-t opt-in), AIC/BIC on the adjusted parameter count (k=3 Gaussian, k=4 Student-t), and three honest-disclosure sentences:
1. **Transformation-bias (D13):** back-transforming filtered/smoothed log-volatility to volatility scale introduces Jensen-inequality bias (E[exp(X)] ≠ exp(E[X])); reported values carry this systematic bias. This applies on both Gaussian and Student-t paths — Student-t does NOT fix this limitation (future follow-up 2b addresses via MCMC).
2. **Innovation distribution (D12):** the wrapper defaults to Gaussian innovations; set `innovations='student_t'` to use Student-t_ν innovations with ν jointly estimated via quasi-ML (Follow-up 2c). On the Student-t path, Tier 2 renders the digamma/trigamma-based observation offset and variance and a "what Student-t fixes / what it does NOT fix" scope frame.
3. **No forecast path (D4):** the wrapper does not emit a forecast; historical filtered/smoothed volatility is the deliverable, paralleling the BVAR wrapper's IRF/FEVD absence.

### Innovation distribution (Follow-up 2c)

The `innovations` parameter toggles the return-innovation distribution:

- **`gaussian`** (default) — ε_t ~ N(0, 1). Fast, 3 free parameters (μ, φ, σ_η). Appropriate when return kurtosis is near 3.
- **`student_t`** — ε_t ~ t_ν(0, 1) with ν jointly estimated. 4 free parameters (μ, φ, σ_η, ν). ν is constrained to (2.01, 200) via a sigmoid reparameterization and initialized at ν₀ = 10. Captures heavy tails explicitly; for typical daily equity returns ν lands in the 5–10 range ("heavy tails").

On the Student-t path, the Kalman-filter quasi-ML framework is retained but the observation-equation offset and variance shift to:

  `offset(ν)  = ψ(1/2) − ψ(ν/2) + log(ν)`
  `obs_var(ν) = ψ'(1/2) + ψ'(ν/2)`

where ψ and ψ' are digamma and trigamma (scipy.special). As ν → ∞ these recover the Gaussian constants (−1.2704, π²/2).

**Graceful degradation (D13):** if Student-t optimization fails to converge on all restarts, the wrapper automatically falls back to Gaussian fit. The fallback is visible — audit fields record `requested_innovations='student_t'` vs `fitted_innovations='gaussian'`, and Tier 2 / Tier 3 disclose the event with three possible causes (genuinely-Gaussian data, too-short series, destabilizing outliers) and their specific remediations.

**Caveats (Tier 3, conditional)**:
- φ > 0.98 (near-integrated volatility) - shocks decay extremely slowly; forward-looking use beyond a few weeks carries substantial uncertainty. Threshold inherited from GARCH for cross-spec consistency.
- φ < 0.3 (low persistence) - volatility is essentially iid; SV framing adds little over sample-mean-volatility. Verify the input is returns (not levels) and that the series has volatility clustering.
- Sample kurtosis > 6 AND `innovations='gaussian'` - input is heavy-tailed and user is on the Gaussian path. Rerun with `innovations='student_t'` to capture tails directly. Suppressed on the Student-t path (user is already handling tails).
- **Student-t ν < 5** (Follow-up 2c D1) - very heavy tails; even Student-t may struggle with extreme moves. Consider checking for structural breaks, outliers, or mean dynamics beyond the SV model's scope.
- **Student-t ν ≥ 30** (Follow-up 2c D2) - essentially Gaussian; series does not exhibit heavy tails at the sampling frequency. Consider `innovations='gaussian'` on the next fit (faster, fewer free parameters).
- **Student-t optimization failed, fell back to Gaussian** (Follow-up 2c D3) - user requested Student-t but the wrapper converged only under Gaussian. Reported parameters are from the Gaussian fit. See Tier 2 for specific remediations.

