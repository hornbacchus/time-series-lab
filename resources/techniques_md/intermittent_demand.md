## What It Does
Intermittent-demand forecasting handles series that are mostly zero with occasional non-zero values — sporadic sales, spare-parts demand, lumpy order flow. Standard forecasters (ARIMA, exponential smoothing) smooth across the zeros and mislead; intermittent methods instead model the demand sizes and the intervals between them separately. The engine offers Croston's method and its variants (SBA, TSB), plus a classification of the demand pattern.

## When to Use It
- Your series is sparse — many zeros with intermittent non-zero observations.
- You're forecasting spare parts, slow-moving inventory, or any lumpy/sporadic demand.
- A continuous forecaster would average over the zeros and produce a misleadingly smooth path.
- Use intermittent methods for zero-heavy series; use `arima`/`ets_hw`/`theta_forecast` for continuous series. If the series is not actually intermittent, those are the better tools.

## How to Read the Result
The output is a per-period demand-rate forecast, the demand-pattern classification, and fit statistics. The classification uses the Syntetos-Boylan scheme, which sorts a series by its average inter-demand interval (ADI — how far apart non-zero observations fall) and its demand-size variability (CV²) into four categories — smooth, intermittent, erratic, and lumpy — telling you which method suits the series. On a series that is 71.5% zeros, the classifier labels it Intermittent (ADI 3.5, CV² 0.33) and SBA forecasts a steady rate of about 1.5 per period. One important caveat: these methods do not produce calibrated prediction intervals — the forecast is a demand-rate estimate, and the usual interval-coverage guarantees do not apply.

## Related Techniques
- *(use after)* feed the demand-rate forecast into inventory / safety-stock logic.
- *(alternatives)* `arima`, `ets_hw`, `theta_forecast` for continuous (non-intermittent) series — the right choice when the series is not sparse.

## Technical Detail
The methods are Croston's method (separate exponential smoothing of demand sizes and inter-demand intervals), SBA (the Syntetos-Boylan approximation, a bias correction to Croston), and TSB (Teunter-Syntetos-Babai, which updates the demand probability each period). The demand pattern is classified by the Syntetos-Boylan ADI/CV² scheme. A smoothing parameter controls the responsiveness of the underlying exponential smoothing. The methods estimate a demand rate and do not provide calibrated prediction intervals.
*Reference run:* intermittent_demand.csv (200 monthly observations, 71.5% zeros), method SBA, smoothing 0.1, Balanced — classified Intermittent (ADI 3.5, CV² 0.33), SBA demand-rate forecast about 1.5 per period, RMSE 3.46.
