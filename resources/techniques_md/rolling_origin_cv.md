## What It Does
Rolling-origin cross-validation evaluates a forecasting model the way it will actually be used: it trains on data up to a point, forecasts forward, then rolls the origin ahead and repeats, so every test is a genuine out-of-sample forecast made without seeing the future. It is the correct way to estimate forecast accuracy for time series, where ordinary k-fold cross-validation is invalid because it would let the model train on future data to predict the past.

## When to Use It
- You want an honest out-of-sample estimate of forecast accuracy for a time series.
- You're comparing forecasting approaches and need a leakage-free evaluation.
- You want accuracy and interval-coverage metrics, not just an in-sample fit.
- Use rolling-origin CV for any time-series forecast evaluation; never use ordinary k-fold cross-validation on time-ordered data — it leaks future information.

## How to Read the Result
The output is per-fold and average accuracy metrics plus interval coverage. The key metrics: MASE (mean absolute scaled error) below 1 means the model beats a naive forecast — on the airline series it is 0.91, so the model is modestly better than naive; sMAPE expresses error as a percentage (13.9% here). The interval coverage (97.2% against a 95% target here) tells you whether the prediction intervals are honest — close to nominal is good, far below means the intervals are too narrow. One thing to know about the procedure: it uses an *expanding* training window (the training set grows as the origin rolls forward) and always fits an automatic ARIMA as the base model — the evaluation measures that model's walk-forward accuracy, not a model you select.

## Related Techniques
- *(use after)* `forecast_combination` or any forecaster you want to evaluate honestly; `conformal_intervals` for distribution-free prediction intervals.
- *(alternatives)* a single holdout split for a quick check; `block_bootstrap` for uncertainty on a statistic rather than forecast accuracy.

## Technical Detail
The procedure walks an expanding origin forward across the series: for each fold it trains on all data up to the origin, forecasts the horizon, scores against the actuals, then advances. The base model is pmdarima's automatic ARIMA (this is fixed — the evaluation is of that model, not a selectable one). Reported metrics are MAE, sMAPE, and MASE, plus prediction-interval coverage. The number of folds and the horizon are set by preset and the dialog.
*Reference run:* airline_passengers.csv (144 monthly observations), horizon 12, Balanced — 3 folds, mean MAE 32.6, sMAPE 13.9%, MASE 0.91 (beats naive), interval coverage 97.2% against a 95% target.
