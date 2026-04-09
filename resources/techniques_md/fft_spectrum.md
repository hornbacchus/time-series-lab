# FFT Spectrum Analysis

## What It Does

FFT (Fast Fourier Transform) spectrum analysis decomposes a time series into its constituent **frequency components**, revealing the periodic oscillations that make up the signal. It transforms data from the time domain to the frequency domain, showing how much of the series' variance is concentrated at each frequency. This identifies dominant cycles, periodicities, and the overall spectral shape of the data.

## When to Use It

- You want to identify the dominant periodicities (cycles) in your data
- You need to determine whether seasonal patterns exist and at what frequencies
- You are analyzing signals that are composed of multiple oscillating components
- You want to filter out specific frequency bands (e.g., remove high-frequency noise)
- You need a fast computational tool for frequency analysis of large datasets

## Key Assumptions

- The time series is regularly spaced (equal intervals between observations)
- The series length is ideally a power of 2 for computational efficiency (zero-padding is used otherwise)
- The signal can be meaningfully represented as a sum of sinusoidal components
- The series is stationary or at least approximately so (trends should be removed first)
- The frequency content is relatively stable over the duration of the series

## Outputs

- **Power spectrum**: the distribution of variance across frequencies, showing dominant periodicities
- **Frequency axis**: from 0 (DC component / mean) to the Nyquist frequency (1/(2*dt))
- **Phase spectrum**: the phase angle of each frequency component
- **Dominant frequencies and corresponding periods**: the strongest cyclical components
- **Amplitude spectrum**: the magnitude of each frequency component

## Technical Details

**Discrete Fourier Transform (DFT)**: For a series `y_0, y_1, ..., y_{N-1}`, the DFT is:

`Y_k = sum_{n=0}^{N-1} y_n * exp(-2*pi*i*k*n/N)` for k = 0, 1, ..., N-1

where `i = sqrt(-1)`. Each `Y_k` is a complex number representing the amplitude and phase of the sinusoidal component at frequency `f_k = k / (N * dt)`, where dt is the sampling interval.

**FFT algorithm**: The FFT computes the DFT in O(N log N) operations instead of O(N^2), using the Cooley-Tukey divide-and-conquer approach. The series is recursively split into even- and odd-indexed subsequences, their DFTs computed, and the results combined using "twiddle factors" `W_N^k = exp(-2*pi*i*k/N)`.

**Power spectral density (PSD)**:

`S(f_k) = (2 * dt / N) * |Y_k|^2` for k = 1, ..., N/2 - 1

The factor of 2 accounts for the symmetry of the DFT for real-valued signals. The power at frequency `f_k` represents the variance contributed by oscillations at that frequency.

**Frequency resolution**: `Delta_f = 1 / (N * dt)`. Longer series provide finer frequency resolution. Two sinusoidal components can only be distinguished if their frequencies differ by at least `Delta_f`.

**Nyquist frequency**: `f_{Nyquist} = 1 / (2 * dt)`. Frequencies above this are aliased (they appear as lower frequencies in the DFT). The sampling interval must be small enough that the highest frequency of interest is below Nyquist.

**Spectral leakage**: A finite-length series acts as if the signal is multiplied by a rectangular window. This causes energy from a single frequency to spread ("leak") into neighboring frequency bins. The side lobes of the rectangular window's frequency response are responsible.

**Windowing**: Multiply the time series by a tapering window function before computing the FFT to reduce leakage:
- **Hann window**: `w_n = 0.5 (1 - cos(2*pi*n/(N-1)))`. Good general-purpose choice.
- **Hamming window**: `w_n = 0.54 - 0.46 cos(2*pi*n/(N-1))`. Slightly narrower main lobe.
- **Blackman window**: `w_n = 0.42 - 0.5 cos(2*pi*n/(N-1)) + 0.08 cos(4*pi*n/(N-1))`. Better sidelobe suppression.

Windows reduce leakage at the cost of widening the main lobe (reducing frequency resolution).

**Zero padding**: Appending zeros to the series before the FFT interpolates the spectrum (finer frequency grid) but does not improve true frequency resolution. Useful for visualization.

**Preprocessing**: Remove the mean (and any linear trend) before computing the FFT. The DC component (k=0) reflects the mean; a trend creates a large low-frequency contribution that can obscure other features.
