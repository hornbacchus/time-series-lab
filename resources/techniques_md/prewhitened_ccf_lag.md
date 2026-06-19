## What It Does
Prewhitened cross-correlation removes the autocorrelation that inflates a raw CCF before measuring lead-lag. It fits an ARIMA model to the input series, filters *both* series through that model (prewhitening), and then computes the CCF on the residuals. Because each series' own internal correlation structure has been stripped out, the remaining cross-correlation is a cleaner estimate of the genuine lead-lag relationship.

## When to Use It
- Both series are autocorrelated or trending, so a raw CCF would be inflated and over-flag significant lags.
- You want a lead-lag estimate robust to each series' own dynamics.
- You found a CCF peak and want to confirm it is not an autocorrelation artifact.
- Use this whenever the plain `cross_correlation_lag` shows high autocorrelation inflation; use the plain version for a first look or when the series are already close to white noise.

## How to Read the Result
The output is the prewhitened CCF, its peak lag, the ARIMA order used to filter, and a measure of how much autocorrelation remained after filtering. On the synthetic autocorrelated pair, prewhitening fits an ARIMA(1,0,1), and the CCF still peaks at +5 (correlation 0.93) — the same true lead — but now only 3 lags are significant versus 13 in the raw CCF, because the spurious autocorrelation-driven significance has been removed. Check the residual inflation figure: here it falls to 1.08 (from 2.8 raw), confirming the filter worked; if it stays at or above about 1.5 the engine warns that prewhitening was incomplete and the lead-lag estimate is less reliable.

## Related Techniques
- *(use after)* `rolling_ccf_lag` to check whether the cleaned lead-lag is stable over time.
- *(alternatives)* `cross_correlation_lag` (the raw version, for near-white series); `granger_causality` for a predictive test; `dtw_alignment_lag` for nonlinear time-warping.

## Technical Detail
An ARIMA model is fit to the input series (automatic order selection, exhaustive under the Thorough preset), and the same filter is applied to both series; the CCF is then computed on the two residual series. Positive lag = first series leads second. The residual autocorrelation inflation is reported as a check on filter completeness, with a warning when it remains high.
*Reference run:* a synthetic AR(1) pair where the first series leads the second by 5 periods (n=300), max lag 30, Balanced — automatic order (1,0,1); the prewhitened CCF peaks at lag +5 with correlation 0.93, residual autocorrelation inflation 1.08 (cleaned from 2.8 raw), with only 3 significant lags versus 13 in the raw CCF.
