# Stochastic Volatility Model

## What It Does

Stochastic volatility (SV) models treat the log-variance as a **latent stochastic process** rather than a deterministic function of past observations (as in GARCH). The volatility evolves according to its own random innovation, separate from the return innovation. This provides a more flexible and theoretically appealing model of time-varying volatility, closely aligned with the continuous-time models used in option pricing.

**Inference options**: Fast quasi-maximum likelihood via Kalman filter on log-squared returns (default), or opt-in full MCMC posterior sampling on the returns likelihood directly (Balanced or Thorough preset; removes the log-squared transformation bias). Both options support Gaussian and Student-t innovations.

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

**Technical Interpretation (Tier 2)** - discloses the SV AR(1) log-variance model equations, the inference method (quasi-ML default or MCMC opt-in), the innovation-distribution choice (Gaussian default or Student-t opt-in), AIC/BIC on the adjusted parameter count (k=3 Gaussian, k=4 Student-t), and three honest-disclosure sentences:
1. **Transformation-bias (D13):** on the quasi-ML path, back-transforming filtered/smoothed log-volatility to volatility scale introduces Jensen-inequality bias (E[exp(X)] ≠ exp(E[X])); reported values carry this systematic bias. **Follow-up 2b closes this gap**: set `inference_method='mcmc'` (Balanced or Thorough preset) to sample directly on the returns likelihood, avoiding the log-squared transformation entirely.
2. **Innovation distribution (D12):** the wrapper defaults to Gaussian innovations; set `innovations='student_t'` to use Student-t_ν innovations with ν jointly estimated (Follow-up 2c). On the Student-t path, Tier 2 renders the digamma/trigamma-based observation offset and variance and a "what Student-t fixes / what it does NOT fix" scope frame.
3. **No forecast path (D4):** the wrapper does not emit a forecast; historical filtered/smoothed volatility is the deliverable, paralleling the BVAR wrapper's IRF/FEVD absence.

### Inference method (Follow-up 2b)

The `inference_method` parameter toggles the inference backend:

- **`quasi_ml`** (default) — quasi-maximum likelihood via Kalman filter on log-squared returns. Fast (sub-second on n=2500). Works on any preset. Produces point estimates with standard errors; inference is approximate because of the log-squared transformation and its Jensen-inequality bias.
- **`mcmc`** — full Bayesian posterior sampling directly on the returns likelihood. Supports Balanced (2 chains × 2000 draws, ~30–120 s) and Thorough (4 chains × 4000 draws, ~2–10 min) presets. Removes the transformation bias by construction; produces genuine posterior distributions with 95% HDIs on every parameter. Fast preset + `inference_method='mcmc'` triggers graceful auto-downgrade (D9) — MCMC's compute cost is incompatible with Fast's latency budget.

Both innovation distributions (`gaussian` and `student_t`) are supported on both inference methods (4 combinations total).

**MCMC backends** — the wrapper supports two samplers, chosen automatically:

1. **pymc NUTS** (preferred) — No-U-Turn Sampler via `pymc`/`pytensor`. Best convergence on SV's awkward geometry; produces WAIC and LOO via `arviz`; tracks divergent transitions as a first-class diagnostic. Used when `pymc` and `arviz` are installed.
2. **Kim-Shephard-Chib Gibbs** (fallback) — classical mixture-of-normals Gibbs sampler, pure `numpy`/`scipy`. Used when `pymc` is unavailable. SV-specialized: FFBS for the latent log-volatility path, conjugate Gibbs for μ and σ_η², Metropolis for φ, and for Student-t innovations a scale-mixture augmentation with per-observation λ_t Gibbs and Metropolis ν slice sampler. No external MCMC dependency. Citation: Kim, S., Shephard, N., & Chib, S. (1998). *Stochastic volatility: likelihood inference and comparison with ARCH models*. Review of Economic Studies, 65(3), 361–393.

Tier 2 always discloses which backend ran for replicability.

**Graceful degradation (D7)**: if MCMC sampling fails (gross convergence failure, library error, compile failure), the wrapper falls back to quasi-ML. Audit fields `requested_inference_method` vs `fitted_inference_method` capture the divergence; Tier 2 renders a 3-cause / 3-remediation diagnostic block; Tier 3 D7 trigger fires.

**Posterior predictive check (PPC)**: on Thorough + MCMC, the wrapper computes `ppc_coverage_90pct` (fraction of observations within the posterior 90% predictive band). Balanced users can opt in via `compute_ppc=True`. D8 trigger fires if coverage falls below 0.80 (model misses important features).

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
- **Student-t ν < 5** (2c D1) - very heavy tails; even Student-t may struggle with extreme moves. Consider checking for structural breaks, outliers, or mean dynamics beyond the SV model's scope.
- **Student-t ν ≥ 30** (2c D2) - essentially Gaussian; series does not exhibit heavy tails at the sampling frequency. Consider `innovations='gaussian'` on the next fit (faster, fewer free parameters).
- **Student-t optimization failed, fell back to Gaussian** (2c D3) - user requested Student-t but the wrapper converged only under Gaussian. Reported parameters are from the Gaussian fit. See Tier 2 for specific remediations.
- **R-hat > 1.01** on any MCMC parameter (2b D4) - chain mixing imperfect (warn at 1.01, fail at 1.05). Posterior summaries should be interpreted with caution; switch to Thorough preset.
- **Bulk ESS < 400 × chains** on any MCMC parameter (2b D5) - low effective sample size, Monte Carlo error on that parameter is high. Run Thorough preset.
- **Divergent transitions > 5% of draws** (2b D6, pymc NUTS only) - NUTS struggling with posterior geometry. Switch to Thorough (tighter target-accept) or use the Kim-Shephard-Chib Gibbs backend.
- **MCMC failed, fell back to quasi-ML** (2b D7) - user requested MCMC but the wrapper fell back. Reported parameters are from the quasi-ML fit and carry the Jensen-inequality transformation bias.
- **PPC 90% coverage < 0.80** (2b D8, Thorough + MCMC) - model misses features of the data; typically extreme moves on heavy-tailed returns. Switch to Student-t or inspect for structural breaks.
- **MCMC requested on Fast preset, auto-downgraded** (2b D9) - Fast cannot run MCMC. Reported parameters reflect the quasi-ML approximation. Re-run on Balanced or Thorough for MCMC inference.
- **MCMC backend auto-downgraded — no C++ compiler** (B6 D10) - the PyMC NUTS path requires a C++ compiler that is not available on this machine; the wrapper auto-downgraded to the Kim-Shephard-Chib Gibbs sampler. NUTS and Gibbs are mathematically equivalent for SV inference. To enable NUTS specifically, install gxx (see "Backend Selection and C-Compiler Detection" below).

## Backend Selection and C-Compiler Detection (Follow-up B6)

The MCMC inference path supports two backends, controlled via the `mcmc_backend` parameter:

- **PyMC NUTS** — preferred when available. Uses pytensor's JIT compilation to generate fast compiled samplers. Requires a C++ compiler (g++, clang++, or MSVC) on the machine.
- **Kim-Shephard-Chib (KSC) Gibbs** — pure numpy/scipy implementation. No compilation needed; runs on any Python install. Mathematically equivalent for SV inference; mixing characteristics differ marginally.

### Auto-detection (default `mcmc_backend="auto"`)

The wrapper inspects `pytensor.config.cxx` at MCMC dispatch to determine whether a C++ compiler is available:

| Compiler available? | Action |
|---|---|
| Yes | Use PyMC NUTS at full compiled speed |
| No | Auto-downgrade to KSC Gibbs; fire D10 Tier 3 trigger |

**Why auto-downgrade matters.** Without a compiler, pytensor falls back to pure-Python execution which is ~100× slower than compiled NUTS. On T=500 SV (a typical daily-returns sample), this means 25+ minutes of unfinished sampling vs ~10 seconds compiled. The auto-downgrade prevents users from waiting on what looks like a hung wrapper.

### Explicit backend requests

- `mcmc_backend="pymc"` — explicitly request NUTS. If no compiler is found, the wrapper still downgrades to Gibbs but emits a loud progress-callback warning explaining why. The workflow continues; no error is raised.
- `mcmc_backend="gibbs"` — skip the probe entirely and run KSC Gibbs directly. Predictable performance; no compiler dependency.

### Installing a C++ compiler for NUTS

If you specifically need NUTS sampling (e.g., for divergent-transition diagnostics or WAIC/LOO information criteria — neither is computed on the Gibbs backend), install a compiler matching your platform:

| Platform | Command |
|---|---|
| Windows (conda) | `conda install -c conda-forge gxx` |
| Windows (system) | Install MSVC Build Tools, or RTools / MSYS2 mingw-w64 for the toolchain pytensor expects |
| macOS | `xcode-select --install` |
| Linux (Debian/Ubuntu) | `apt install build-essential` |

After installation, restart Python so pytensor re-detects the compiler at its next import.

### Audit-trail fields

The wrapper exposes four fields tracking the backend cascade:

- `mcmc_backend_requested` — the user's pinned choice (`"pymc"` / `"gibbs"`) or `"auto"` when unspecified.
- `mcmc_backend_applied` — what actually ran (`"pymc"` or `"gibbs"`).
- `mcmc_backend_fallback_reason` — `None` on the requested path; `"c_compiler_unavailable"` on the B6 D10 cascade; `"pymc_not_installed"` when the existing ImportError fallback fires.
- `c_backend_available` — the probe's bool result (read from `pytensor.config.cxx`).

## Latent Posterior Summary (Follow-up B7)

In addition to the population-parameter posteriors (μ, φ, σ_η, ν), the MCMC inference path now exposes the **latent log-volatility posterior summary**:

- `h_posterior_mean` — list of T floats. The posterior mean of `h_t` at each timepoint, computed via Welford online accumulators across all chains × post-tune draws (Gibbs backend) or extracted from `idata.posterior["h"]` (PyMC NUTS backend).
- `h_posterior_std` — list of T floats. The posterior standard deviation of `h_t` at each timepoint, suitable for ±2σ confidence-band visualization.

To convert to volatility scale, practitioners typically apply `σ_t = exp(h_t / 2)`. The transformation is monotonic but introduces Jensen-inequality bias on the mean (`E[exp(h/2)] ≠ exp(E[h]/2)`); for unbiased volatility estimates use the per-draw transformation `exp(h_draw[t] / 2)` followed by averaging — but this requires full draw retention beyond what audit_fields exposes.

Both fields are `None` on the quasi-ML inference path (`inference_method='quasi_ml'`).

### Storage strategy

The Gibbs backend uses **Welford online accumulators** (Welford 1962 / Knuth Vol 2 §4.2.2) per chain, with parallel-Welford pooling (Chan, Golub & LeVeque 1979) across chains. Memory cost is **O(T)** per chain regardless of draw count — 16 KB on T=10000, vs 1.28 GB for naive full-draw retention on Thorough × T=10000. The PyMC NUTS backend retains draws in `idata.posterior["h"]` natively (NUTS samples h as a first-class variable), so no Welford storage is needed there.

