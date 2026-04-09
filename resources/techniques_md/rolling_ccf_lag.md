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
- **Optimal lag over time**: the lag with maximum correlation at each time point
- **Maximum correlation over time**: the strength of the peak relationship at each time point
- **Lag stability analysis**: how much the optimal lag varies over time
- **Regime identification**: periods where the relationship is strong, weak, or has shifted lag

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
