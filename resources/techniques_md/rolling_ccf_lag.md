# Rolling CCF / Time-Varying Lag Analysis

## What It Does

Rolling CCF computes the cross-correlation function over a **sliding window**, revealing how the relationship and lead-lag structure between two time series **changes over time**. Instead of a single, global cross-correlation, you get a time-varying view of correlation strength and optimal lag. This is essential when the coupling between series is non-stationary -- strengthening during some periods, weakening during others, or shifting in timing.

## When to Use It

- The lead-lag relationship between two series is not constant over time
- You want to track how quickly one series responds to another, and whether that response time changes
- Economic or financial relationships evolve due to policy changes, market regime shifts, or structural breaks
- You need to identify periods when two series decouple (lose their typical correlation)
- You are monitoring the stability of a known lead-lag relationship for early warning of changes

## Key Assumptions

- The window length is long enough to produce reliable cross-correlation estimates (at least 30-50 observations per window)
- The relationship changes slowly relative to the window length
- Both series are locally stationary within each window (or have been detrended/differenced)
- The linear cross-correlation captures the relevant relationship (nonlinear dependencies are missed)
- The chosen maximum lag is appropriate for the expected delay

## Outputs

- **Time-varying CCF heatmap**: correlation as a function of both time (window center) and lag
- **Optimal lag over time**: the lag with maximum correlation at each window, with a `Boundary_Hit` flag marking windows that landed at or near ±max_lag and were excluded from summary statistics
- **Maximum correlation over time**: the strength of the peak relationship at each time point
- **Lag stability analysis**: how much the optimal lag varies over time (on the boundary-excluded subset)
- **Structural-break flag**: whether the rolling series exhibits a confirmed regime shift, with a pre-break / post-break split in the summary when confirmed
- **Summary statistics**: mean, median, and std of optimal lag (ex-boundary); AC-corrected vs naive pct_significant for comparison

## Conventions Enforced By This Technique

Rolling CCF is the reference implementation for two platform-wide conventions. Every pairwise technique in Time Series Lab follows the same rules.

**Pairwise-summary convention (F2)**: the primary plain-English sentence always pairs a sign indicator, a correlation magnitude, and a direction word. You will never see a summary that reports a lag without the associated ρ, or a ρ without the associated direction. When a structural break is confirmed, the sentence splits into pre-break and post-break clauses with the same sign+magnitude+direction triplet in each.

**Significance-disclosure convention (F3)**: the audit sheet always exposes `test_name`, `critical_value_formula`, `ac_corrected`, and (when AC-corrected) `effective_n`. You can always trace exactly which test was applied, what critical value was used, and whether autocorrelation in the inputs was accounted for.

## Boundary-lag flagging

When the optimal lag in a window sits at or near the search boundary (|lag| ≥ 0.8 × max_lag), the reported lag is not reliable — the optimizer wanted a lag outside the search range and got clipped. Such windows are flagged in the `Boundary_Hit` column, **excluded from mean/median/std summary statistics**, and their count disclosed in both the Summary Statistics table and the audit sheet (`n_windows_boundary_excluded`). Raise `boundary_threshold` toward 1.0 if your data legitimately uses lags at the edge of the range; lower it below 0.8 if you want to be more conservative.

## Autocorrelation-corrected significance

The naive Bartlett band ±z / √window assumes white-noise inputs. For autocorrelated macro/financial series (the common case) it systematically overstates significance. This technique applies the **Bartlett effective-n correction** on the two input series:

`n_eff = n / (1 + 2 · Σ_k ρ_x(k) · ρ_y(k))`

then uses ±z / √n_eff for the critical band. Both naive and AC-corrected significance percentages are reported side-by-side so the materiality of the correction is explicit. On highly persistent data (AR(ρ)=0.9), effective-n can collapse to ~1/8 of nominal n, yielding a significance-rate drop from 90%+ (naive) to under 25% (corrected) — a dramatic qualitative change in the finding.

## Structural-break detection

After computing the rolling CCF, this technique invokes [ruptures](https://github.com/deepcharles/ruptures)' PELT algorithm on two derived series: the CCF-at-optimal-lag magnitude series and the sign-of-CCF series. A break is **confirmed** only if four criteria all hold:

1. Each segment is ≥ max(8, n_windows/8) windows long.
2. Each segment has >2/3 modal-sign consistency (not 50/50 random wandering).
3. Pre- and post-break modal signs differ (true regime change, not persistence).
4. |median_pre_ρ − median_post_ρ| > 0.25 (the mean shift is not a marginal wobble).

This conservative rule deliberately misses borderline breaks rather than splitting the summary on noise. When confirmed, the summary emits a split-regime template with the break date, pre-break (N, sign, magnitude, lag, direction), and post-break triplet.

## Multi-series disclosure

Rolling CCF is a pairwise technique. If you supply more than two columns, the wrapper uses the first two in order and emits a warning naming both the pair used and the columns ignored. Re-run with a different column order to analyze a different pair.

## Default window

The Balanced preset auto-selects `window = max(40, min(80, n // 3))`. For n=286 quarterly observations this gives window=80 (a 20-year window), economically coherent for macro data. Override via the `window` parameter; the wrapper will warn if you request `window > n/2`.

## Technical Details

**Basic rolling CCF procedure**:

For each window centered at time t (or ending at time t for causal windows):

1. Extract the sub-series `x_{t-W/2}, ..., x_{t+W/2}` and `y_{t-W/2}, ..., y_{t+W/2}` (window of length W).
2. Optionally detrend each window (remove local mean and/or linear trend).
3. Compute the CCF between the windowed x and y for lags `k = -k_max, ..., k_max`:
   `r_{xy}^{(t)}(k) = sum_{i} (x_i - x_bar)(y_{i+k} - y_bar) / sqrt(sum(x_i - x_bar)^2 * sum(y_{i+k} - y_bar)^2)`
4. Record the optimal lag: `k_hat(t) = argmax_k |r_{xy}^{(t)}(k)|`
5. Record the peak correlation: `r_max(t) = r_{xy}^{(t)}(k_hat(t))`

**Window parameters**:
- **Window length W**: Larger windows give more stable CCF estimates but less sensitivity to temporal changes. Typical range: 2-5 times the maximum lag of interest.
- **Step size**: How much the window advances between consecutive CCF computations. Step = 1 gives the finest temporal resolution; larger steps reduce computation.
- **Window type**: Rectangular (simple truncation) or tapered (Gaussian, Hann) to reduce edge effects.

**Significance testing in rolling windows**: The standard `+/- 1.96/sqrt(W)` bounds apply within each window under the null of independent white noise. However, multiple testing across many windows and lags inflates the false positive rate. Corrections include:
- Bonferroni adjustment for the number of windows * lags tested
- False Discovery Rate (FDR) control
- Bootstrapping: shuffle the time alignment between the two series to generate a null distribution

**Visualization**: The most informative display is a heatmap with time on the x-axis, lag on the y-axis, and color representing the cross-correlation value. This reveals:
- Horizontal bands at specific lags: stable lead-lag relationship
- Shifting bands: changing lag over time
- Patches of high color: episodic coupling
- Uniform low color: no relationship during that period

**Rolling prewhitened CCF**: For more reliable results, apply prewhitening within each window:
1. Fit a local ARIMA to x within the window.
2. Filter both x and y with the fitted model.
3. Compute the CCF of the filtered series.

This is more computationally intensive but removes the distortion caused by autocorrelation.

**Exponentially weighted CCF**: An alternative to fixed windows that gives more weight to recent observations:
`r_{xy}^{EW}(k, t) = sum_{i<=t} lambda^{t-i} (x_i - x_bar)(y_{i+k} - y_bar) / ...`
where `lambda` (0 < lambda < 1) is the decay factor. Smaller lambda emphasizes more recent data.

**Practical considerations**:
- Very short windows produce noisy CCF estimates; very long windows average over structural changes.
- If both series have strong seasonality, deseasonalize before computing rolling CCF or the seasonal correlation will dominate.
- The maximum lag should be less than W/4 to ensure reliable estimation at the edges of the lag range.
