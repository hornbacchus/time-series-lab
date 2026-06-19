## What It Does
BOCPD (Bayesian Online Change-Point Detection, Adams-MacKay 2007) processes a series one observation at a time, maintaining a posterior distribution over the *run length* — the time elapsed since the last change point — and updating it at each step. It is an *online/streaming* detector: it does not need the whole series in advance. When incoming data stop fitting the current run, the posterior mass collapses back to a short run length — and that reset is a detected change point.

## When to Use It
- You want sequential, real-time detection as observations arrive, rather than an offline pass over a finished series.
- You want a probabilistic view of how long the current regime has persisted (the run-length posterior).
- You're monitoring a live series for regime changes.
- Use BOCPD for online detection; use `pelt_change_points` for offline optimal segmentation of a complete series; use `cusum_page_hinkley` for a lightweight sequential mean-shift alarm.

## How to Read the Result
The output is the set of detected change-point locations together with the run-length posterior. A change point is flagged where the most-probable (MAP) run length drops sharply — the posterior abandoning the current run for a fresh one. On a synthetic series with a single mean shift at position 120, BOCPD fires once, at index 122, detecting a shift of +3.78. On a pure-noise series with no genuine change point, it correctly stays silent (zero detections). One important caveat on the output: the per-point change *probability* series is a diagnostic by-product and is *not* the detection signal — the run-length reset is what marks a change point, so read the detected locations, not the probability trace.

## Related Techniques
- *(use after)* `pelt_change_points` for an offline cross-check of the located breaks; `intervention_analysis` to quantify a break's effect.
- *(alternatives)* `pelt_change_points` (offline optimal segmentation); `cusum_page_hinkley` (sequential single-shift alarm).

## Technical Detail
Implementation is the Adams-MacKay recursion (numpy/scipy) with a Normal-inverse-Gamma observation model and a constant hazard. Each step updates the run-length distribution through the posterior predictive likelihood; a change point is recorded where the MAP run length falls by more than a minimum gap, indicating the posterior has reset to a fresh run. The hazard parameter — the prior expected run length between changes — governs sensitivity: a longer expected run length yields fewer change points. The minimum gap (set by preset) prevents immediate re-triggering after a detection.
*Reference run:* a synthetic mean-shift series (shift 0→4 at position 120, n=240), Balanced, seed 42 — fires once, change point at index 122 (true break 120), detected shift +3.78, by MAP run-length reset; on a separate pure-noise series (n=240) it stays silent with zero detections.
