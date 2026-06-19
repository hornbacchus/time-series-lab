## What It Does
Forecast combination fits several forecasting models to a series and blends their forecasts into one, on the principle that a combination is often more accurate and more stable than any single model. It fits three members — ARIMA, ETS, and Theta — measures each one's accuracy on a holdout, and combines them, by default weighting each inversely to its error so that weaker models contribute less.

## When to Use It
- You're unsure which single model is best and want to hedge across several.
- You want a more stable forecast that does not depend on one model being right.
- You want the weak models automatically down-weighted rather than chosen out by hand.
- Use combination when no single model clearly dominates; use a single model when you have strong reason to prefer it (and benchmark the combination against it).

## How to Read the Result
The output is the combined forecast and the weight each member received. With inverse-MSE weighting, the weights reveal which models fit best: on the airline series the weights are ETS 0.55, Theta 0.37, ARIMA 0.07 — ARIMA's large holdout error drove its weight almost to zero, exactly the auto-down-weighting the method is for. One honest caveat: combination is not guaranteed to beat the single best member. On this run the ensemble's holdout MSE (360.6) was slightly worse than ETS alone (310) — combination reduces the risk of picking a bad model, but when one model is clearly best, blending in weaker ones can dilute it. Read the weights to see whether one model dominates; if it does, consider using it directly.

## Related Techniques
- *(use after)* `rolling_origin_cv` to evaluate the combined forecast honestly out-of-sample.
- *(alternatives)* any single forecaster (`arima`, `ets_hw`, `theta_forecast`) when one clearly dominates; the ML forecasters for a different model family in the mix.

## Technical Detail
Three members are fit — ARIMA, ETS, and Theta — and evaluated on a holdout fraction of the series. The combination method governs how they are weighted: simple_average (equal weights), inverse_mse (the default — weight proportional to the inverse of each member's holdout mean-squared error, so weaker models contribute less), or ols (regression-determined weights). At least two members must fit successfully. The forecast horizon and holdout fraction are set by the dialog and preset.
*Reference run:* airline_passengers.csv (144 monthly observations), inverse-MSE weighting, Balanced — members ARIMA / ETS / Theta with holdout MSE 2370 / 310 / 458, giving inverse-MSE weights 0.07 / 0.55 / 0.37; the ensemble's holdout MSE (360.6) did not beat ETS alone (310) on this series.
