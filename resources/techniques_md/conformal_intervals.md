## What It Does
Conformal prediction produces forecast intervals with a distribution-free coverage guarantee — it does not assume the forecast errors are normal or follow any particular distribution. The default method (split conformal) sets aside a calibration set, measures how large the forecast errors actually are on it, and uses the appropriate error quantile to build intervals around new forecasts. The result is intervals whose coverage is guaranteed on average, derived from the data's own error distribution rather than a parametric assumption.

## When to Use It
- You want prediction intervals without assuming a particular error distribution.
- The parametric model's intervals look too narrow or too wide and you want an empirically-calibrated alternative.
- You want a coverage guarantee grounded in the data rather than in distributional assumptions.
- Use conformal intervals when the error distribution is unknown or non-normal; use a model's parametric intervals when its distributional assumptions genuinely hold.

## How to Read the Result
The output is the forecast with conformal lower and upper bounds. The headline property — and its precise limit — is the coverage guarantee: conformal coverage is *marginal*, meaning it holds on average across the calibration distribution, **not** conditional, meaning it is not guaranteed for any individual point, region, or sub-period. On the airline series at 90% coverage, the conformal half-width is 23.65 (a constant-width interval), about 57% narrower than the parametric ARIMA interval — tighter because it reflects the actual error sizes rather than an inflated model assumption. The critical caveat for time series: the guarantee assumes the calibration errors are exchangeable, which autocorrelation violates. The engine flags this when the calibration residuals are autocorrelated, and you should treat the coverage as approximate in that case (an adaptive conformal method is the remedy when it matters).

## Related Techniques
- *(use after)* report conformal intervals alongside a point forecast from any model.
- *(alternatives)* a model's parametric intervals when its assumptions hold; `block_bootstrap` for uncertainty on a statistic; `rolling_origin_cv` to check realized coverage out-of-sample.

## Technical Detail
The default is split conformal: the data are split into a training set (which fits a rolling one-step ARIMA) and a calibration set, the nonconformity scores are the absolute residuals on the calibration set, and the interval half-width is the residual quantile at `ceil((n_cal+1)(1-alpha))/n_cal` for target coverage `1-alpha`, giving constant-width intervals `forecast ± q`. Two further methods are available — CQR (conformalized quantile regression, which yields varying-width intervals) and EnbPI (an ensemble method for time series) — selectable via the method parameter. Coverage is marginal and assumes exchangeable residuals; the engine warns when calibration-residual autocorrelation suggests that assumption is violated.
*Reference run:* airline_passengers.csv (144 monthly observations), 90% coverage, split conformal — an ARIMA(2,1,2) base with a 75/25 train/calibration split (36 calibration residuals), conformal half-width 23.65 (constant width 47.3), about 57% narrower than the parametric ARIMA interval; the engine flagged the exchangeability caveat.
