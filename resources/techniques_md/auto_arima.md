## What It Does
auto_arima automatically searches for the best ARIMA (or seasonal ARIMA) order rather than requiring you to specify it. It fits many candidate orders, scores each by an information criterion, and returns the best one with its forecast. It is the convenient route to a well-specified ARIMA when you do not want to choose the orders by hand.

## When to Use It
- You want an ARIMA forecast without manually selecting the order.
- You want the order chosen by a consistent information criterion rather than by eye.
- You're forecasting many series and need an automated, repeatable specification.
- Use it to find a good order automatically; use `arima`/`sarima` when you already know the order or want full manual control.

## How to Read the Result
The output is the selected order, the forecast, and the winning model's information criterion. On the airline series, with seasonality on, the search selects ARIMA(1,1,3)(1,0,0)[12] — recovering the period of 12 — at AIC 1139.8. Read it as the *best searched* model under the chosen criterion, not a guaranteed global optimum: the search is stepwise on the faster presets (exhaustive only under Thorough), so it can skip a better order the stepwise path does not visit. And when several orders sit within a couple of AIC points, the exact winner can differ across software versions, so treat near-ties as interchangeable rather than meaningful.

## Related Techniques
- *(use after)* `arima` or `sarima` to refit the selected order manually if you want to adjust it.
- *(alternatives)* `arima`/`sarima` (manual order); `ets_hw` and `theta_forecast` as non-ARIMA forecasters worth benchmarking against.

## Technical Detail
The search uses pmdarima's `auto_arima`, scanning ranges of the AR, MA, and differencing orders (and their seasonal counterparts when seasonality is on), scoring each by the selected information criterion (default AIC; AICc, BIC, HQIC also available). The search is stepwise on Fast and Balanced and exhaustive under Thorough. The seasonal period is inferred from the data frequency when left blank. This is a *search*, not a single fit — the result is the best candidate found, not a proof of optimality.
*Reference run:* airline_passengers.csv (144 monthly observations), seasonality on, criterion AIC, horizon 12, Balanced — selected ARIMA(1,1,3)(1,0,0)[12] (period 12 auto-inferred), AIC 1139.8, RMSE 40.4, after searching at least 21 candidate specifications.
