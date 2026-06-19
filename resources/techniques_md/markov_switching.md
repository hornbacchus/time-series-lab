## What It Does
A Markov-Switching model is a regime-switching regression or autoregression: like a hidden Markov model the regime is unobserved and follows a Markov chain, but each regime carries its own *regression or AR coefficients* (and optionally its own variance), not just a mean. It captures a series whose dynamics — not merely its average level — change with the regime. Outputs are the smoothed probability of each regime at each point, the transition matrix, expected regime durations, and a regime-aware forecast.

## When to Use It
- You want regime-dependent *dynamics* (AR coefficients, regression slopes), not just a regime-dependent mean and variance.
- You want smoothed regime probabilities (the probability the system was in each regime at each date) and expected regime durations.
- You're modeling a series whose persistence or response structure shifts between states (expansion versus recession dynamics).
- Use it over `hmm` when the regimes differ in their dynamics; use `hmm` for a lighter mean/variance segmentation; use `tar_setar` / `star` when the regime is driven by an observed variable.

## How to Read the Result
Each regime's mean and the expected durations characterize the states: on the SP500 reference a two-regime AR(1) model finds Regime 0 (positive mean +0.122, 1,777 observations) expected to last about 49 days and Regime 1 (negative mean −0.131, 734 observations) about 21 days — a long calm regime punctuated by shorter stress spells. The smoothed probabilities show when each regime was active. The decisive check is the benchmark comparison: the engine reports the RMSE improvement over a plain AR of the same order — here only +0.86%, meaning the regime structure barely earns its added complexity on this data. As with any EM fit, confirm convergence and that restarts agreed, and read regimes by their means (labels are arbitrary and relabeled). Note that the multi-step forecast is formed by iterating a regime-probability-weighted prediction and becomes less reliable at long horizons.

## Related Techniques
- *(use after)* compare against `hmm` (does the extra dynamic structure change the segmentation?) and a plain AR (the RMSE-lift check).
- *(alternatives)* `hmm` for hidden-state mean/variance segmentation; `tar_setar` / `star` for observed-threshold regimes; a single AR when the RMSE-lift is negligible.

## Technical Detail
Estimation is statsmodels `MarkovRegression` (order 0) or `MarkovAutoregression` (order 1 or higher), fit with multiple search repetitions, with regimes deterministically relabeled to defeat label-switching. Because statsmodels does not implement forecasting for these models, the multi-step forecast is built in-house by iterating a regime-probability-weighted one-step prediction, with its interval assumptions disclosed in the audit. The engine also computes the RMSE improvement over an AR benchmark of the same order. You set the number of regimes, the AR order, and whether the variance switches; the forecast horizon and the switching-trend option default internally.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), 2 regimes, order 1, Balanced, seed 42 — Regime 0 mean +0.122 (1,777 observations), Regime 1 mean −0.131 (734 observations); log-likelihood −3283.74, AIC 6583.5, expected durations 49.1 and 20.6 days; RMSE improvement over AR(1) +0.86%.
