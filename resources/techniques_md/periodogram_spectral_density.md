# Periodogram / Spectral Density Estimation

## What It Does

The periodogram estimates the **spectral density** of a time series -- how the total variance is distributed across different frequencies. While the raw periodogram (based on the FFT) is a noisy, inconsistent estimator, smoothed versions provide reliable estimates of the true power spectral density. This is the foundation of frequency-domain time series analysis, connecting the autocovariance structure to the frequency content.

## When to Use It

- You want to estimate the power spectral density function for a stationary time series
- You need to identify dominant periodicities and their relative importance
- You are checking for hidden periodicities or quasi-periodic behavior
- You want to compare the frequency content of different time series
- You need spectral density estimates for Whittle likelihood estimation or frequency-domain modeling

## Key Assumptions

- The time series is weakly stationary (constant mean and covariance structure)
- The series is regularly sampled
- Trends and other non-stationary components have been removed
- The spectral density is a smooth function of frequency (for smoothed estimates)
- The series is long enough for the desired frequency resolution

## Outputs

- **Raw periodogram**: variance at each Fourier frequency (noisy but unbiased)
- **Smoothed spectral density estimate**: a consistent estimate using kernel smoothing or tapering
- **Confidence intervals** for the spectral density at each frequency
- **Dominant frequencies and periods**: peaks in the spectral density
- **Bandwidth and resolution** of the spectral estimate

## Technical Details

**Raw periodogram**: For the DFT `Y_k` of series `y_1, ..., y_N`:

`I(f_k) = (1/N) |Y_k|^2 = (1/N) |sum_{t=1}^{N} y_t exp(-2*pi*i*f_k*t)|^2`

at Fourier frequencies `f_k = k/N` for k = 0, 1, ..., floor(N/2).

**Relationship to autocovariance**: The periodogram is the Fourier transform of the sample autocovariance function:

`I(f) = sum_{h=-(N-1)}^{N-1} gamma_hat(h) exp(-2*pi*i*f*h)`

This is the sample analog of the spectral density `S(f) = sum_{h=-inf}^{inf} gamma(h) exp(-2*pi*i*f*h)`.

**Inconsistency of the raw periodogram**: Despite being an unbiased estimator of `S(f)`, the raw periodogram is NOT consistent: its variance does not decrease as N increases. For a Gaussian process, `Var(I(f_k)) approx S(f_k)^2`, regardless of N. The periodogram values are approximately independent exponential random variables.

**Smoothed periodogram (Daniell kernel)**: Average the raw periodogram over a window of frequencies:

`S_hat(f) = sum_{j=-m}^{m} w_j I(f + j/N)`

where `w_j` are kernel weights summing to 1. The window width 2m+1 controls the bias-variance tradeoff: wider windows reduce variance but smooth out narrow peaks.

**Welch's method**: Divide the series into overlapping segments, compute the periodogram of each (with a window function applied), and average. For K segments of length L with 50% overlap:

`S_hat(f) = (1/K) sum_{k=1}^{K} I_k(f)`

This reduces variance by a factor of approximately K. The tradeoff is reduced frequency resolution (Delta_f = 1/(L*dt) instead of 1/(N*dt)).

**Multitaper method** (Thomson): Apply K orthogonal DPSS (Discrete Prolate Spheroidal Sequence) tapers to the data, compute a periodogram for each, and average:

`S_hat(f) = (1/K) sum_{k=1}^{K} |sum_t h_k(t) y_t exp(-2*pi*i*f*t)|^2`

The tapers are optimally concentrated in a frequency band of width W = (K+1)/(N*dt). This provides a principled bias-variance tradeoff with excellent leakage properties.

**Confidence intervals**: For the smoothed periodogram with effective degrees of freedom nu (approximately 2 times the number of independent periodogram ordinates averaged):

`[nu * S_hat(f) / chi^2_{nu, alpha/2}, nu * S_hat(f) / chi^2_{nu, 1-alpha/2}]`

provides a (1-alpha) confidence interval on the log scale. Intervals are wide for small nu and narrow for large nu.

**Bandwidth**: The spectral window bandwidth `B = sum w_j^2 / (sum w_j)^2 * (1/dt)` determines the effective frequency resolution of the smoothed estimate. Wider bandwidth means more smoothing (lower variance, less resolution).
