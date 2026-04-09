# Wavelet Transform

## What It Does

The wavelet transform analyzes a time series simultaneously in **time and frequency** (or time and scale), revealing how the frequency content changes over time. Unlike the Fourier transform which gives a global frequency decomposition, wavelets provide a local analysis: they detect when periodic components appear, disappear, or change character. This makes wavelets ideal for non-stationary signals with transient features, regime changes, or evolving periodicities.

## When to Use It

- The frequency content of your series changes over time (non-stationary spectral properties)
- You want to identify when specific periodicities are active or dominant
- You need to analyze transient events, structural breaks, or localized oscillations
- Your data has features at multiple scales that appear at different times
- Standard Fourier analysis loses temporal information that is important for your analysis

## Key Assumptions

- The time series is regularly sampled (for the standard discrete wavelet transform)
- The chosen wavelet (mother wavelet) is appropriate for the features you want to detect
- The series is long enough to resolve the scales of interest (at least a few cycles at the lowest frequency)
- Edge effects near the boundaries of the series are acknowledged (the cone of influence)
- The signal-to-noise ratio is sufficient for meaningful time-frequency analysis

## Outputs

- **Wavelet power spectrum**: a 2D map of power as a function of time and scale/frequency
- **Scale-averaged power**: power summed over selected scales, as a function of time
- **Global wavelet spectrum**: power averaged over time, comparable to a Fourier spectrum
- **Cone of influence**: the region where edge effects are not significant
- **Significant power regions**: areas exceeding the background noise level at a given confidence

## Technical Details

**Continuous Wavelet Transform (CWT)**: For a time series `y(t)` and mother wavelet `psi(t)`:

`W(a, b) = (1/sqrt(a)) integral y(t) psi*((t-b)/a) dt`

where `a > 0` is the scale (inversely related to frequency), `b` is the time location, and `psi*` is the complex conjugate of the wavelet. In practice, computed for discretized time and a set of scales.

**Morlet wavelet**: The most common choice for time series analysis:

`psi(t) = pi^{-1/4} exp(i*omega_0*t) exp(-t^2/2)`

A complex sinusoid modulated by a Gaussian envelope. The parameter `omega_0` (typically 6) controls the time-frequency tradeoff. For `omega_0 = 6`, the relationship between scale and Fourier period is: `period = 1.03 * a`.

**Wavelet power spectrum**: `|W(a,b)|^2` gives the local power at scale a and time b. Plotted as a heatmap with time on the x-axis and scale (or equivalent period) on the y-axis.

**Significance testing**: Under a null hypothesis of red noise (AR(1) process), the wavelet power at each point follows a chi-squared distribution:

`|W(a,b)|^2 / sigma^2 ~ (1/2) P_k chi^2_2`

where `P_k` is the theoretical Fourier spectrum of the AR(1) process at the frequency corresponding to scale a, and `chi^2_2` is a chi-squared with 2 degrees of freedom (for complex wavelets). The 95% significance level is `P_k * chi^2_2(0.95) / 2`.

**Cone of influence (COI)**: Near the edges of the time series, the wavelet overlaps with regions outside the data. The COI marks the boundary where edge effects become important. For the Morlet wavelet, the e-folding time is `sqrt(2) * a`, and the COI follows this contour from each edge.

**Discrete Wavelet Transform (DWT)**: Samples the CWT at dyadic scales `a = 2^j` and positions `b = k * 2^j`:

`d_{j,k} = sum_t y(t) psi_{j,k}(t)`

The DWT uses a cascade of high-pass and low-pass filters (quadrature mirror filters) to decompose the signal into detail coefficients `d_{j,k}` at each scale and approximation coefficients at the coarsest scale. Common wavelet families: Daubechies, Symlets, Coiflets.

**Maximal Overlap DWT (MODWT)**: A shift-invariant version that does not downsample, producing the same number of coefficients as the original series at each scale. Better for time series analysis than the standard DWT because it is not sensitive to the starting point.

**Scale-to-frequency conversion**: For the Morlet wavelet with `omega_0 = 6`: `frequency = 1 / (1.03 * scale)`. For Daubechies wavelets at level j with sampling interval dt: the frequency band is approximately `[1/(2^{j+1} dt), 1/(2^j dt)]`.
