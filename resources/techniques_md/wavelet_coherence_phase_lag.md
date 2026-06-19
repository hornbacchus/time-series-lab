## What It Does
Wavelet coherence measures how strongly two series move together at each frequency *and* at each point in time — a time-localized, frequency-resolved correlation. It also reports the phase relationship, which translates into a lead-lag at each scale. Use it to see whether two series share a cycle, where in time they share it, and which one leads.

## When to Use It
- You want to know whether two series co-move at a particular cycle (and when in time they do).
- You want a lead-lag that can vary by frequency and over time, not a single constant lag.
- The relationship between the series may be localized to certain periods or episodes.
- Use wavelet coherence for time-and-frequency-resolved co-movement; use `cross_correlation_lag` for a single constant lead-lag; use `wavelet_transform` to examine one series' time-frequency structure.

## How to Read the Result
The output is coherence (between 0 and 1) and phase across scales and time. The critical reading caution: do **not** simply take the scale of maximum coherence as the answer. Coherence at the largest scales, near the start and end of the series, is inflated by edge effects (the cone of influence), and this engine does not mask that region — so the global maximum can land on a long-period edge artifact rather than a genuine shared cycle. On two series built to share a period-12 cycle, the reported headline maximum falls at a long period (about 66) that is exactly this edge artifact; the genuine shared period-12 coherence is present in the by-scale results. Read coherence *at the scale or period you care about* from the by-scale output, not the global maximum, and interpret the phase (and the lead-lag it implies) at that scale — the phase at the inflated edge scale is similarly not the relationship you want.

## Related Techniques
- *(use after)* `cross_correlation_lag` to confirm a constant-lag reading of a shared cycle.
- *(alternatives)* `cross_correlation_lag` / `prewhitened_ccf_lag` for a single constant lead-lag; `wavelet_transform` for one series' time-frequency content.

## Technical Detail
The method is a continuous wavelet transform (PyWavelets `cwt`) of each series with a complex wavelet, from which the cross-wavelet spectrum, coherence, and phase are formed. The first series is `x`, the second `y`; a positive lag means `x` leads `y`. Scale is converted to period by an approximately one-to-one factor for the supported wavelets. The cone of influence (the edge region where coherence is unreliable) is **not** masked, and no surrogate-based significance test is applied, so coherence should be read at the scales of interest from the by-scale output rather than taken as a single global maximum.
*Reference run:* two constructed series sharing a period-12 cycle, Balanced — the scale-to-period conversion is correct (the genuine period-12 coherence appears in the by-scale results), but the reported headline maximum falls at a long period (about 66), an edge-effect artifact of the unmasked cone of influence.
