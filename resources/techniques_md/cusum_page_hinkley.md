## What It Does
This technique runs two classic sequential detectors for a shift in the mean: CUSUM (the cumulative sum of deviations from a target, which alarms when the running sum crosses a threshold) and Page-Hinkley (a related cumulative test). Both flag the indices where a running statistic signals a sustained change in level. They are lightweight and designed for monitoring as data arrive.

## When to Use It
- You want a fast sequential alarm for a mean shift, suitable for monitoring.
- You want to detect drift away from a known target level.
- You're processing observations sequentially and want an early warning rather than a full segmentation.
- Use CUSUM / Page-Hinkley for a quick single-mean-shift alarm; use `pelt_change_points` or `bocpd` for full change-point segmentation.

## How to Read the Result
The output is the alarm indices for each detector. The key tunable is the CUSUM threshold: left blank it defaults to 5× the series standard deviation, a data-dependent automatic choice. On a synthetic mean-shift series, that auto threshold is 10.81 (5 × σ, with σ ≈ 2.16); CUSUM raises 16 alarms (8 upward, 8 downward) and Page-Hinkley 112 upward alarms. Page-Hinkley keeps alarming for as long as the level stays shifted, so a dense cluster of Page-Hinkley alarms should be read as one sustained shift, not many separate events. A higher threshold produces fewer, later alarms.

## Related Techniques
- *(use after)* `pelt_change_points` or `bocpd` to pin the exact break and segment the series; `intervention_analysis` to quantify it.
- *(alternatives)* `pelt_change_points` (offline optimal segmentation); `bocpd` (online run-length detection).

## Technical Detail
The detectors are implemented in numpy. CUSUM accumulates deviations from a target level beyond an allowance (a reference slack) and alarms when the cumulative sum exceeds the threshold. The blank defaults are data-dependent: the target defaults to the series mean, the allowance to about half the series standard deviation, the threshold to 5× the standard deviation, and the Page-Hinkley magnitude to about 0.005× the standard deviation. For multivariate input, the thresholds are calibrated by bootstrap.
*Reference run:* a synthetic mean-shift series (shift 0→4 at position 120, n=240), Balanced, seed 42 — auto threshold 10.81 (5 × σ, σ ≈ 2.16), allowance 1.08 (0.5σ), target 2.05 (the series mean); CUSUM 16 alarms (8 up / 8 down), Page-Hinkley 112 upward alarms.
