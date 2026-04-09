# Wavelet Coherence and Phase Lag

## What It Does

Wavelet coherence measures the **time-varying correlation between two time series in the time-frequency domain**. For each combination of time and frequency (scale), it quantifies how strongly the two series co-move, analogous to a localized, frequency-specific correlation coefficient. The associated phase information reveals the **lead-lag relationship** -- which series leads and by how much at each frequency and time.

## When to Use It

- You want to understand how the relationship between two series varies across frequencies and over time
- You need to identify lead-lag relationships that differ at different time scales
- The co-movement between series is non-stationary (the correlation changes over time)
- You are studying economic or financial contagion, spillovers, or synchronization
- You want a richer picture than a single correlation coefficient or a fixed-frequency coherence

## Key Assumptions

- Both time series are regularly sampled at the same frequency
- The chosen mother wavelet (typically Morlet) is appropriate for the analysis
- Sufficient data exists to resolve the scales of interest (at least a few cycles at the lowest frequency)
- The smoothing applied to compute coherence is appropriate (not too much, not too little)
- Phase relationships are meaningful (the series have a genuine, not spurious, connection)

## Outputs

- **Wavelet coherence map**: a 2D plot (time vs. scale) with coherence values from 0 to 1
- **Phase arrows**: overlaid on the coherence map, showing the lead-lag relationship at each significant point
- **Significant coherence regions**: areas where coherence exceeds the significance level against a null of no relationship
- **Phase difference time series**: the phase lag at selected scales, converted to time units
- **Cone of influence**: the boundary of reliable estimates

## Technical Details

**Cross-wavelet transform**: For two series `x(t)` and `y(t)` with wavelet transforms `W^x(a,b)` and `W^y(a,b)`:

`W^{xy}(a,b) = W^x(a,b) * conj(W^y(a,b))`

The cross-wavelet power `|W^{xy}|` identifies regions where both series have high power simultaneously. The cross-wavelet phase `arg(W^{xy})` gives the local phase difference.

**Wavelet coherence** (analogous to squared coherency in Fourier analysis):

`R^2(a,b) = |S(a^{-1} W^{xy}(a,b))|^2 / [S(a^{-1} |W^x(a,b)|^2) * S(a^{-1} |W^y(a,b)|^2)]`

where `S` is a smoothing operator applied in both time and scale. Without smoothing, coherence would always equal 1 (just like correlation equals 1 for a single pair of observations).

**Smoothing**: The smoothing operator S typically combines:
- Time smoothing: convolution with a Gaussian or boxcar filter along the time axis at each scale
- Scale smoothing: a moving average along the scale axis at each time point

The time smoothing window width is proportional to the scale (larger windows at larger scales), matching the wavelet's inherent resolution.

**Phase interpretation** (for the Morlet wavelet):
- Phase difference `phi = arg(W^{xy})` gives the angular offset between the two series at that time-frequency point.
- Converting to time lag: `lag = phi / (2*pi*f)`, where f is the frequency corresponding to the scale.
- Arrow conventions in coherence plots:
  - Right-pointing (0 degrees): in-phase (positive correlation, no lag)
  - Left-pointing (180 degrees): anti-phase (negative correlation)
  - Down-pointing (90 degrees): x leads y by a quarter cycle
  - Up-pointing (-90 degrees): y leads x by a quarter cycle

**Significance testing**: Monte Carlo approach:
1. Generate many pairs of surrogate series with the same spectral properties as the originals (e.g., AR(1) processes with matched lag-1 autocorrelation).
2. Compute wavelet coherence for each surrogate pair.
3. The 95% significance level at each time-frequency point is the 95th percentile of surrogate coherence values.

Typical significance thresholds range from 0.5 to 0.8, depending on the smoothing and effective degrees of freedom.

**Partial wavelet coherence**: Analogous to partial correlation, this measures the coherence between two series after removing the influence of a third series. Useful for identifying direct vs. indirect relationships in multivariate systems.

**Scale-averaged coherence**: Average the coherence over a band of scales to produce a time series of coherence at a specific frequency band. This simplifies interpretation when the relationship is consistent across nearby scales.
