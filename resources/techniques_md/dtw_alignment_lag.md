## What It Does
Dynamic Time Warping (DTW) aligns two series by stretching and compressing the time axis to match their shapes, then reads a lead-lag from that alignment. Unlike cross-correlation, which assumes a single constant offset, DTW handles relationships where the timing varies — one series may lead by a little in some stretches and more in others. It is the tool for a *nonlinear* time-warped relationship rather than a fixed shift.

## When to Use It
- The lead-lag between two series is not constant — the relationship stretches or compresses over time.
- The series have similar shapes but are misaligned in a time-varying way.
- A constant-offset method (CCF) does not fit because the timing drifts.
- Use DTW for nonlinear/time-varying alignment; use `cross_correlation_lag` when a single constant lag is the right model and you also want a significance test (DTW provides a distortion measure, not a p-value).

## How to Read the Result
The output is a median lead-lag, its variation over the alignment, and a distortion ratio (how much warping was needed). On a synthetic pair with a constant 5-period offset, DTW recovers the magnitude correctly — a median lag of 5 with low variation and a distortion ratio of 1.06. One important caveat on direction: the sign convention DTW currently reports for lead-lag direction is *inverted* relative to the cross-correlation techniques — on this pair, where CCF correctly reports the first series leading the second, DTW labels it the opposite way. Read the *magnitude* from DTW, and cross-check the *direction* against `cross_correlation_lag` rather than relying on DTW's sign. Because DTW is distance-based it produces no significance test — the distortion ratio (near 1 means little warping was needed) indicates alignment quality instead.

## Related Techniques
- *(use after)* `cross_correlation_lag` to confirm the lead-lag direction (and get a significance test).
- *(alternatives)* `cross_correlation_lag` / `prewhitened_ccf_lag` for a constant-offset lead-lag with significance; `rolling_ccf_lag` for a time-varying lag under the constant-offset-per-window assumption.

## Technical Detail
A custom DTW computes the optimal alignment path between the two series under a Sakoe-Chiba band (the band width is set by preset), with the series normalized by default. The local lead-lag is read from the alignment path and summarized as a median with its variation; a distortion ratio measures the total warping. Note the lead-lag direction sign is currently inverted relative to the CCF techniques, so direction should be cross-checked; the magnitude is reliable. DTW provides no p-value (it is a distance-based alignment, not a hypothesis test).
*Reference run:* a synthetic AR(1) pair where the first series leads the second by 5 periods (n=300), Balanced — DTW recovers a median lag magnitude of 5 (low variation, distortion ratio 1.06), though it reports the direction inverted relative to the CCF techniques (which correctly show the first series leading); normalized DTW distance 0.0155.
