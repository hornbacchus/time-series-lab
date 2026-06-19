## What It Does
A Vector Error Correction Model is a VAR for series that are individually non-stationary but share one or more long-run equilibrium relationships (cointegration). It separates the long-run structure — the equilibrium relationships (β) and the speed each series adjusts back toward them (α) — from the short-run dynamics. For yields, this captures that maturities wander individually but the curve's spreads are mean-reverting. Outputs are the cointegrating vectors, adjustment speeds, forecasts, impulse responses, and variance decompositions.

## When to Use It
- Your series are non-stationary in levels but move together in the long run (cointegrated) — typical of a yield curve or a set of arbitrage-linked prices.
- You want the long-run equilibrium relationships and how fast deviations correct.
- You've run a cointegration test (`johansen_cointegration`) and found rank at least 1.
- Use VECM over differencing-then-VAR when you care about the level relationships; use plain `var` when the series are not cointegrated.

## How to Read the Result
The cointegrating rank is how many long-run relationships exist (selected here by the trace test: rank 2). Each cointegrating vector β is reported Phillips-normalized — its pivot entry set to 1 — so the entries read as equilibrium spread coefficients; on the reference, V1 is `[1, 0, −4.15, 3.33]` across the four maturities. The adjustment coefficient α measures correction speed: near zero (here α on 2Y is about −0.0041) means very slow reversion, giving a long half-life (170 periods here). A half-life reported as undefined means the estimated adjustment fell outside the stable correction range and the closed-form half-life does not apply. The trace statistic against its critical value (70.68 vs 47.85 at 5%) is the evidence for the chosen rank.

## Related Techniques
- *(use after)* nothing required — VECM is usually the destination after a cointegration finding.
- *(alternatives)* `johansen_cointegration` to determine the rank first; `var` on differences when the series are not cointegrated; `bvar` for a shrinkage approach to the same system.

## Technical Detail
Estimation is statsmodels `VECM` with the cointegrating rank and lag order selectable or auto-selected (`VECM(data, k_ar_diff=…, coint_rank=…, deterministic='ci').fit()`); blank rank auto-selects by the trace test and blank lags by information criterion. β and α are Phillips-normalized (the product `α·β'` is scale-invariant, so normalization only pins the reporting scale). Impulse responses are Cholesky-orthogonalized; the variance decomposition is built in-house (statsmodels provides no `VECM.fevd()`) using the same cumulative squared orthogonalized-MA formula as the VAR. The half-life is returned only when the adjustment coefficient lies strictly in (−1, 0); outside that range the closed form is undefined and the field is left empty rather than reporting a spurious value.
*Reference run:* treasury_yields.csv (2Y/5Y/10Y/30Y, 6,146 obs), rank and lags auto-selected, deterministic 'ci', Balanced — rank 2, 4 lagged differences; β V1 `[1, 0, −4.15, 3.33]` (Phillips-normalized), α (2Y, eq 1) −0.0041, half-life 170.1 periods, trace statistic 70.68 vs 47.85 critical value (5%).
