## What It Does
Intervention analysis quantifies the effect of a known event on a series. It fits an ARIMA model augmented with dummy regressors that mark the event — a step, a pulse, or a ramp at a specified date — and reports the estimated effect size and its statistical significance. Because the ARIMA component absorbs the series' own dynamics, the estimated effect is the event's impact net of normal persistence.

## When to Use It
- You have a known intervention (a policy change, a structural break, a one-off shock) and want its measured effect.
- You want to test whether an event had a statistically significant impact on the series.
- You want the effect estimated net of the series' autocorrelation, not a raw before/after difference.
- Use it when you know the event date; use `pelt_change_points` or `bocpd` to *locate* unknown breaks first.

## How to Read the Result
The output is the estimated intervention coefficient(s) and their significance. The intervention type sets the shape of the effect: a step is a permanent level shift, a pulse a one-time spike, a ramp a linear post-event trend. On a synthetic mean-shift series, a step intervention at position 120 in an ARIMA(1,0,0) is significant with a coefficient of 0.99 (p < 0.0001). Read the coefficient carefully: it is expressed in the regression-with-ARIMA-errors parameterization, so the autoregressive term absorbs part of the raw level change and the coefficient reflects the effect *net of* the modeled dynamics, not the full raw jump. The significance test assumes the fitted ARIMA has captured the serial correlation in the residuals.

## Related Techniques
- *(use after)* nothing required — this is usually the destination once an event is known.
- *(alternatives)* `pelt_change_points` / `bocpd` to find unknown breaks; the regime models (`markov_switching`) for recurring rather than one-off shifts.
- *(use before)* run a change-point detector first if you need to identify the event date.

## Technical Detail
Estimation is a statsmodels ARIMA with exogenous intervention regressors. The caller specifies the event date(s) and the intervention type (step, pulse, or ramp); if no event is supplied, the engine auto-detects a single break via a CUSUM scan. The ARIMA order defaults to an automatic AIC-based selection, falling back to a default order if needed. The reported coefficient is the intervention effect in the ARIMA-errors parameterization, and its t-test relies on the fitted ARIMA structure to account for serial correlation (it is not otherwise autocorrelation-robust).
*Reference run:* a synthetic mean-shift series (shift 0→4 at position 120, n=240), a step intervention at position 120, ARIMA(1,0,0), Balanced — the step is significant with coefficient 0.99 (p < 0.0001).
