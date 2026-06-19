## What It Does
Rolling cross-correlation computes the lead-lag relationship over a moving window rather than once for the whole series, producing a *time-varying* lead-lag. It answers a question the static CCF cannot: is the lead-lag stable, or does it drift, strengthen, or flip over time? It also flags structural breaks in the relationship and windows where the estimate hits the edge of the searched lag range.

## When to Use It
- You suspect the lead-lag between two series changes over time (regime-dependent or evolving relationships).
- You want to see the stability of a lead-lag, not just its average.
- You want structural breaks in the relationship detected automatically.
- Use the rolling version to assess stability over time; use `cross_correlation_lag` for a single static estimate over the whole sample.

## How to Read the Result
The output is the lead-lag and correlation in each window, the share of windows that are significant, a stability measure, and any detected structural breaks. On the synthetic pair with a constant 5-period lead, the rolling CCF returns a median lead of +5 across 241 windows, 100% of them significant, with zero variation in the lag (perfectly stable) and no structural break — correctly showing both the lead and its stability. Watch two flags: windows whose optimal lag sits at the edge of the searched range are boundary hits and are excluded as unreliable; and the structural-break detection (conservative, requiring several criteria to agree) marks points where the lead-lag relationship shifts.

## Related Techniques
- *(use after)* nothing required — this is usually the stability check after a static estimate.
- *(alternatives)* `cross_correlation_lag` for a single static lead-lag; `prewhitened_ccf_lag` to first remove autocorrelation; `dtw_alignment_lag` for nonlinear alignment.

## Technical Detail
The CCF is computed over a rolling window, stepping through the series, with the per-window peak lag and correlation recorded. The window length and maximum lag default to the values shown (clearing them restores a preset-adaptive window). Note this does not collapse to a static CCF when the window equals the series length — for a static estimate use `cross_correlation_lag`. Boundary-hit windows (optimal lag at the edge of the searched range) are flagged and excluded, and structural breaks are detected by a conservative change-point procedure on the lag and correlation series.
*Reference run:* a synthetic AR(1) pair where the first series leads the second by 5 periods (n=300), window 60, max lag 20, Balanced — median lead +5 across 241 windows, 100% significant, lag perfectly stable (zero variation), no structural break detected, correlation 0.88.
