## What It Does
A particle filter estimates the hidden state of a *nonlinear or non-Gaussian* state-space model using sequential Monte Carlo — it represents the distribution of the state with a swarm of weighted samples ("particles") that are propagated and reweighted as each observation arrives. Where the Kalman filter is exact but assumes linear-Gaussian dynamics, the particle filter handles models where that assumption fails, at the cost of being a simulation-based approximation.

## When to Use It
- Your state-space model is nonlinear or has non-Gaussian noise, so the Kalman filter does not apply.
- You want a flexible filtering approach for models like stochastic volatility or nonlinear growth.
- You accept a Monte Carlo approximation in exchange for handling models the Kalman filter cannot.
- Use the particle filter for nonlinear/non-Gaussian models; use `kalman_filter` when the model is linear-Gaussian (it is exact and faster there).

## How to Read the Result
The output is the estimated state path, the effective sample size, and the number of resampling steps. The effective sample size (ESS) is the diagnostic to watch: it measures how many particles are meaningfully contributing, and a low ESS signals particle degeneracy (a few particles carrying all the weight, which degrades the estimate). On the Nile series with the local-level model, the average ESS is 977 out of 2,000 (about 49%) with 54 resampling steps — healthy. Because the method is simulation-based it is stochastic, but it is seeded, so a given run reproduces. Choose the model to match your problem from the four available; more particles improve accuracy at proportional cost.

## Related Techniques
- *(use after)* compare against `kalman_filter` if a linear-Gaussian approximation of the model is plausible.
- *(alternatives)* `kalman_filter`/`kalman_smoother` (exact for linear-Gaussian models); `stochastic_volatility` for the specific SV case with a dedicated sampler.

## Technical Detail
The method is a bootstrap particle filter (sequential importance resampling, numpy). Particles are propagated through the state equation, weighted by the observation likelihood, and resampled when the effective sample size falls below a threshold. Four model templates are available — local level, local level with stochastic volatility, nonlinear growth, and random-walk stochastic volatility. The state and observation noise are estimated automatically by default. The procedure is stochastic but seeded for reproducibility.
*Reference run:* nile_river.csv (100 annual observations), local-level model, seed 42, Balanced — 2,000 particles, average effective sample size 977 (49%), 54 resampling steps, automatically-estimated noise scale 84, log-likelihood −868.
