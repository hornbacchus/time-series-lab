## What It Does
The cross-correlation function (CCF) measures the correlation between two series across a range of leads and lags. The lag at which the absolute correlation peaks is the estimated lead-lag relationship — how many periods one series leads or follows the other. It is the most direct way to find the offset at which two series co-move most strongly.

## When to Use It
- You want the lag at which two series are most strongly correlated (the lead-lag offset).
- You want a quick, interpretable picture of the whole lead-lag structure, not just one number.
- You're exploring whether two series move together with a delay.
- Use plain CCF for a first look; use `prewhitened_ccf_lag` when both series are autocorrelated or trending (which inflates the raw CCF); use `rolling_ccf_lag` to see whether the lead-lag is stable over time.

## How to Read the Result
The output is the correlation at each lag, the peak lag, and significance bands. Positive lag means the first series leads the second. On a synthetic pair where the first series leads the second by 5 periods, the CCF peaks at +5 with a correlation of 0.96 — recovering the lead exactly. The crucial caveat is autocorrelation inflation: when each series is itself autocorrelated, the raw CCF is inflated and more lags look significant than truly are. The engine reports both a naive band and an autocorrelation-corrected (Bartlett, effective-sample-size) band — here the inflation factor is 2.8 (effective sample 107 versus 300), so read significance against the corrected band. If both series are trending or strongly autocorrelated, prefer the prewhitened version.

## Related Techniques
- *(use after)* `prewhitened_ccf_lag` to confirm a peak is not an autocorrelation artifact; `rolling_ccf_lag` to check stability over time.
- *(alternatives)* `prewhitened_ccf_lag` (removes autocorrelation inflation); `granger_causality` for a predictive test; `dtw_alignment_lag` when the relationship is a nonlinear time-warp rather than a constant lag.

## Technical Detail
The CCF is computed directly across lags up to the maximum. Positive lag = first series leads second. Correlations are normalized by default. The engine also computes an autocorrelation-corrected significance band using Bartlett's formula with an effective sample size, alongside the naive band, so you can judge whether a peak survives the autocorrelation adjustment.
*Reference run:* a synthetic AR(1) pair where the first series leads the second by 5 periods (n=300), max lag 30, Balanced — the CCF peaks at lag +5 with correlation 0.96; autocorrelation-inflation factor 2.8 (effective sample 107 of 300), with 13 lags exceeding the band (the motivation for the prewhitened variant).
