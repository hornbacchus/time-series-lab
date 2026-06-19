## What It Does
A Smooth Transition Autoregression (STAR) blends two AR regimes *continuously* through a transition function rather than switching abruptly at a threshold. As a transition variable (a lagged value) moves, the model shifts gradually from one regime's dynamics to the other's — logistic (LSTAR) for a directional, monotone transition, or exponential (ESTAR) for a symmetric one. Outputs are the AR coefficients of each regime, the transition location `c`, the transition smoothness `γ` (gamma), and forecasts.

## When to Use It
- You believe the regime change is gradual rather than a hard switch (a smooth blend between dynamics).
- You want a directional transition (LSTAR — behaves differently as the variable rises versus falls) or a symmetric one (ESTAR — behaves differently in the middle versus the extremes).
- You want a continuous nonlinear model that nests a linear AR as a limiting case.
- Use STAR for smooth transitions; use `tar_setar` for a hard threshold; use `markov_switching` / `hmm` when the regime is hidden rather than a function of an observed variable.

## How to Read the Result
Read the transition location `c` (where the regime switch is centered) and the per-regime AR coefficients (the two sets of dynamics being blended) — these are the interpretable, well-identified quantities. **Do not over-interpret the transition smoothness `γ`.** In STAR models `γ` is *weakly identified*: the likelihood is nearly flat in `γ` over a wide range, so its point estimate is unstable and the engine does not report a standard error or confidence interval for it. This is a known statistical property of STAR models, not a defect. On the SP500 reference the instability is visible directly — changing the AR order from 2 to 4 swings `γ` from 0.061 to 0.097 and the transition location `c` from −0.53 to +2.74, for a trivial 2.7-point change in AIC; both fits describe a `γ` so small the transition is nearly linear (the two regimes are barely distinguishable on this data). Treat a fitted `γ` as indicative of *whether* the transition is sharp or gradual, never as a precise number.

## Related Techniques
- *(use after)* compare against `tar_setar` (is a hard threshold a better description?) and a linear AR (when `γ` is near zero, the regimes barely differ).
- *(alternatives)* `tar_setar` (hard transition); `markov_switching` / `hmm` (hidden regimes); a plain AR when the transition is negligible.

## Technical Detail
Estimation is nonlinear least squares (`scipy.optimize.minimize`, L-BFGS-B) minimizing the residual sum of squares, with the transition function `G(s) = 1 / (1 + exp(-gamma*(s - c)))` for LSTAR or `G(s) = 1 - exp(-gamma*(s - c)^2)` for ESTAR; the "both" option fits each and selects by AIC. To make the weakly-identified `γ` and location `c` as robust as the data allow, the optimizer is started from multiple points — a spread of quantiles of the transition variable for `c` plus several random starts — and the best fit by residual sum of squares is kept. The AR order defaults to a data-dependent automatic choice. No standard error or confidence interval is computed for `γ` (no Hessian is inverted), and that absence is itself the honest signal that `γ` is not point-identified.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), LSTAR, Balanced, seed 42 — across AR orders 2 and 4 the smoothness `γ` ranged 0.061 to 0.097 and the transition location `c` from −0.53 to +2.74 for an AIC change of just 432.98 to 430.28, both reporting a very gradual (nearly linear) transition — the flat-likelihood signature of weak `γ` identification.
