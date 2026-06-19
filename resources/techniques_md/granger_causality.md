## What It Does
Granger causality tests whether one series' past values help predict another series, beyond what the second series' own past already explains. If adding the history of series A improves the forecast of series B, A is said to "Granger-cause" B. It is a test of *predictive precedence*, run as an F-test on whether the lagged terms of the candidate driver are jointly significant in a regression for the target.

## When to Use It
- You want to know whether one series leads another in a predictive sense (does A's past forecast B).
- You're screening which of several variables carry predictive information about a target.
- You want a formal significance test, not just a correlation.
- Use it for predictive lead-lag; use `cross_correlation_lag` for the lag at which two series co-move most strongly, or the regime/structural models when you need the actual mechanism.

## How to Read the Result
The output is the test direction, the optimal lag, the F-statistic, and the p-value. Series order matters and is not obvious: the *second* series is the hypothesized cause and the *first* is the effect — the test asks whether series 2 Granger-causes series 1. On a synthetic pair where one series genuinely leads another by 5 periods, the test (with the leader as the second series) returns a significant result at lag 5 (F = 611.5, p < 0.0001), correctly recovering both the direction and the lag. The decisive caveat: *Granger causality is predictive, not structural.* "A Granger-causes B" means A's past helps predict B — it does **not** establish that A causes B; a common third driver or a lead-lag artifact can produce the same signal. Treat it as evidence of predictive precedence, not proof of a causal mechanism.

## Related Techniques
- *(use after)* `cross_correlation_lag` to see the lag structure of the relationship; the regime or VAR models for the joint dynamics.
- *(alternatives)* `cross_correlation_lag` / `prewhitened_ccf_lag` for correlation-based lead-lag; a structural model when you need genuine causality, which no purely statistical test can establish.

## Technical Detail
Estimation is statsmodels `grangercausalitytests` — for each lag up to the maximum, an F-test compares a regression of the target on its own lags against one that adds the candidate driver's lags. The reported optimal lag is the one with the smallest p-value across the search (not an information-criterion choice). Inputs must be stationary (difference them first if not), or the test can spuriously reject. The series order convention is that the second series is the hypothesized cause; the reverse-direction test is also run under the Thorough preset.
*Reference run:* a synthetic AR(1) pair where one series leads another by 5 periods (n=300), max lag 12, Balanced, with the leader as the second series — the leader Granger-causes the follower at optimal lag 5 (F = 611.5, p < 0.0001), recovering the true lag.
