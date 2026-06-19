## What It Does
A Threshold Autoregression (SETAR — Self-Exciting Threshold AR) fits a different linear AR model in each of two or more regimes, switching between them when a lagged value of the series crosses an estimated threshold. It captures discrete regime behavior — a market that behaves differently above and below a return or volatility level — with a hard switch rather than a smooth blend. Outputs are the per-regime AR coefficients, the estimated threshold(s), a test of whether the threshold structure is warranted at all, and forecasts.

## When to Use It
- You suspect the series follows different dynamics in distinct regimes, with an abrupt switch at a level, not a gradual transition.
- You want the regime boundary estimated from the data rather than imposed.
- You want a formal test of whether the nonlinearity (the threshold) is even justified versus a single linear AR.
- Use SETAR for a hard threshold; use `star` when the regime change is smooth, or `markov_switching` / `hmm` when the regime is unobserved (a hidden state, not an observed lagged value).

## How to Read the Result
The threshold is the estimated switch level: on the SP500 reference, a two-regime SETAR places it at 0.336 (on the once-lagged series), splitting the sample into 1,628 observations below and 880 above, each fit with its own AR(4). Compare the per-regime residual scales (σ 1.143 versus 1.043 here) to see whether one regime is noisier. The crucial diagnostic is the linearity test: it tells you whether the two-regime structure actually beats a single linear AR — if it does not reject linearity, a plain AR is the more honest model and the threshold is spurious. The AR order is selected automatically from the data; you choose the number of regimes and the delay (which lag triggers the switch).

## Related Techniques
- *(use after)* compare the regime split against `markov_switching` or `hmm`, which infer an unobserved regime rather than keying off an observed threshold.
- *(alternatives)* `star` for a smooth rather than hard transition; `markov_switching` / `hmm` for hidden-state regimes; a plain AR if the linearity test does not reject.

## Technical Detail
Estimation is OLS within each regime (numpy), with the threshold chosen by grid search over candidate values — the sorted observations of the threshold variable, trimmed 15% at each tail — minimizing the summed within-regime residual sum of squares (a coarse pass of up to 50 candidates, then a fine pass of up to 200). A regime with fewer than `AR order + 2` observations is penalized, enforcing a minimum regime size. A Hansen-style linearity F-test assesses the two-regime specification against a linear AR. The AR order defaults to a data-dependent automatic choice; the delay (the lag whose value triggers the switch) defaults to 1. Table outputs carry a 6-decimal rounding floor.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), 2 regimes, delay 1, Balanced, seed 42 — SETAR(2) with threshold 0.336 (delay 1); Regime 0 AR(4), 1,628 observations, σ 1.143; Regime 1 AR(4), 880 observations, σ 1.043; RMSE 1.107, AIC 531 (the AR order was auto-selected to 4).
