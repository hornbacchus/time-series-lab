## What It Does
PELT (Pruned Exact Linear Time) finds the points where a series' statistical regime shifts — a change in mean, variance, or distribution — by partitioning the whole series into segments that minimize a penalized cost. It is an *offline* method: it sees the complete series and returns the optimal segmentation. A penalty term governs how many change points it finds, trading fit against parsimony.

## When to Use It
- You have a complete series (not a live stream) and want the optimal set of structural breaks.
- You want to locate shifts in level or volatility — regime boundaries in a historical series.
- You want the number of breaks chosen by the data (via a penalty) rather than fixed in advance — or, alternatively, you want to force an exact count.
- Use PELT for offline segmentation; use `bocpd` for online/streaming detection; use `cusum_page_hinkley` for a sequential single-mean-shift alarm.

## How to Read the Result
The output is the set of change-point locations and the resulting segments. On a synthetic series with a single mean shift at position 120, PELT places one change point at 121 (essentially exact), splitting the series into two segments with a mean shift of +3.83. The penalty is the dial that matters most: a higher penalty yields fewer change points, a lower one more. The default auto penalty computes a BIC-family value from the data; if you get too many or too few breaks, raise or lower the penalty, or set an explicit count to force a specific number.

## Related Techniques
- *(use after)* `bocpd` for an online cross-check of the same breaks; `intervention_analysis` to quantify the effect of a located break.
- *(alternatives)* `bocpd` (online/streaming detection); `cusum_page_hinkley` (sequential single-shift alarm); `stl_esd_anomaly` for point anomalies rather than regime shifts.

## Technical Detail
Estimation uses the `ruptures` library's PELT (`rpt.Pelt(model=…, min_size=…).fit(X).predict(pen=…)`). The cost model is selectable: rbf (a kernel cost that detects general distributional changes, the dialog default), l2 (mean shifts), l1 (robust to outliers), normal, or clinear. The minimum segment length bounds how close two change points may be. The penalty defaults blank to a preset criterion (BIC, or MBIC under Thorough), which resolves to a data-computed value of order `log(n) · variance`; an explicit penalty value or a fixed number of breakpoints overrides it. A higher penalty selects fewer change points.
*Reference run:* a synthetic mean-shift series (shift 0→4 at position 120, n=240), l2 cost, BIC penalty, Balanced, seed 42 — one change point at position 121 (true break 120), mean shift +3.83, two segments.
