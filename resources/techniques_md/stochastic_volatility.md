## What It Does
Stochastic volatility models treat log-variance as its own latent AR(1) random process driven by separate shocks, rather than a deterministic function of past returns as GARCH does. This is the academically preferred volatility model: it captures the same clustering but with a genuinely random volatility component. The default fits quickly via quasi-maximum-likelihood; an optional MCMC path delivers an unbiased fit by sampling the return likelihood directly.

## When to Use It
- You want a volatility model where volatility itself is stochastic (the canonical SV specification used across the volatility literature).
- You need persistence and vol-of-vol estimates — how persistent the latent vol is and how much it moves.
- For a fast first look, the default quasi-ML is fine; for a publication-grade unbiased estimate, switch inference to MCMC (Balanced/Thorough presets).
- Choose SV over GARCH when you specifically want the latent-process interpretation or plan to extend toward multivariate or factor SV.

## How to Read the Result
The headline parameters are φ (persistence of latent log-vol) and σ_η (vol-of-vol). On the SP500 reference, φ=0.980 — a half-life of about 35 days, so shocks to volatility take over a month to decay — and σ_η=0.217. The smoothed volatility path ranges from 0.24% to 4.77% (a ~19.5× span), tracking the calm-versus-turbulent regimes in the data. Read the default fit as a fast approximation: quasi-ML fits log of squared returns, which carries a known observation-error bias; the MCMC path removes it. If you requested Student-t innovations, the estimated degrees-of-freedom (bounded 2.01–200) reports tail-heaviness.

## Related Techniques
- *(use after)* `evt_pot_gpd` and `caviar_quantile_dynamics` for tail risk on top of the vol estimate.
- *(alternatives)* `garch` / `gjr_garch` / `egarch` (deterministic-vol family — faster, no latent sampling); `particle_filter` and the state-space techniques for related latent-state estimation.

## Technical Detail
Default inference is quasi-ML: `scipy.optimize.minimize` (Nelder-Mead) on a Kalman quasi-likelihood of log squared returns, with 3 restarts. The optional MCMC path uses PyMC NUTS or a Kim-Shephard-Chib Gibbs sampler. The engine runs a fallback cascade and the audit distinguishes requested from fitted: (a) the Fast preset with MCMC auto-downgrades to quasi-ML; (b) an MCMC runtime failure falls back to quasi-ML; (c) a Student-t MLE failure falls back to Gaussian — each with a warning, so a requested option can silently downgrade. The MCMC backend default tries NUTS and downgrades to Gibbs when no C++ compiler is present (NUTS without a compiler runs roughly 100× slower); the Gibbs option needs no compiler. The posterior-predictive-check option defaults blank to on under the Thorough preset, off otherwise.
*Reference run:* sp500_returns.csv, quasi-ML / Gaussian default, Balanced — `φ=0.980` (half-life 34.7 days), `σ_η=0.217`, `μ=−0.588`; mean smoothed vol 0.854%, range 0.244–4.77% (19.5× ratio); negative log-likelihood 3428.6; input excess kurtosis 19.8.
