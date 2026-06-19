## What It Does
NAR (Nonlinear AutoRegression) and its exogenous-input variant NARX forecast a series with a neural network — a multilayer perceptron — that learns nonlinear dependence on the series' own lags (and, for NARX, on lagged external inputs). It captures nonlinear patterns a linear AR would miss. Outputs are forecasts with bootstrap intervals, a cross-validated RMSE, and a permutation-based ranking of which lags matter most.

## When to Use It
- You suspect nonlinear lag dependence that a linear AR or ARIMA cannot capture.
- You want a flexible nonlinear forecaster and are willing to validate it carefully (neural nets overfit easily).
- For NARX, you have exogenous drivers whose lagged values should inform the forecast.
- Use it when nonlinearity is the point and you have enough data; prefer a linear AR/ARIMA when the relationship is approximately linear or data is scarce (the network will overfit).

## How to Read the Result
The honest headline is the cross-validated RMSE, not the in-sample fit. On the SP500 reference the in-sample RMSE is 1.069 (R² 0.124) but the cross-validated RMSE is higher at 1.260 — the gap is the overfit the cross-validation correctly exposes, and the CV number is the one to trust. The permutation importance ranks the lags (lag-1 dominates here). The most important thing to understand about validation: **there is no external gold-standard package to check this implementation against.** Unlike ARIMA (validated against statsmodels) or HMM (against hmmlearn), this engine *is* the reference implementation for NAR/NARX — its results are validated by cross-validated error and a linear-AR baseline, *not* by cross-package agreement. Results are made reproducible by seeding: two runs with the same seed produce bit-identical outputs (verified — only the wall-clock timestamp differs). Read the model as a carefully-reproducible nonlinear forecaster, not an externally-certified one.

## Related Techniques
- *(use after)* benchmark against a linear `arima` or AR to confirm the nonlinearity earns its complexity.
- *(alternatives)* the classical forecasters (`arima`, `theta_forecast`) when the relationship is near-linear; other ML forecasters for a different nonlinear family.

## Technical Detail
The model is a multilayer-perceptron regressor (scikit-learn `MLPRegressor`, not a deep-learning/torch model) fit on standardized autoregressive-lag features, with early stopping; cross-validation uses a time-series split, multi-step forecasts iterate the one-step model (carrying exogenous values forward for NARX), prediction intervals come from a 200-replication bootstrap, and feature importance is by permutation. The number of lags, the hidden-layer architecture, and the training settings default by preset. Validation is cross-validated RMSE against a linear-AR baseline — there is no independent reference implementation to cross-check against, so results are seed-pinned for reproducibility and table outputs carry a 6-decimal rounding floor.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), NAR, 5 lags, a (20, 10) hidden architecture, Balanced, seed 42 — in-sample RMSE 1.069 (R² 0.124), cross-validated RMSE 1.260 (the gap the CV catches as mild overfit), top feature lag-1, 341 parameters; two same-seed runs verified bit-identical (only the timestamp differs).
