## What It Does
The wavelet transform decomposes a series into time-frequency components, showing not just *which* cycles are present but *when* they occur. Unlike the Fourier transform, which gives a single global spectrum, the wavelet transform localizes frequency content in time — so a cycle that appears only in part of the series, or that strengthens and fades, is visible as such. It splits the series into frequency bands plus a smooth trend.

## When to Use It
- The frequency content of your series changes over time (cycles that come and go, or shift).
- You want to know *when* a cycle is active, not just that it exists somewhere in the series.
- You want a multi-resolution view — coarse trend plus progressively finer detail bands.
- Use the wavelet transform for time-varying frequency content; use `fft_spectrum`/`periodogram_spectral_density` for a stationary global spectrum.

## How to Read the Result
The output is a set of detail bands (each covering a range of periods) plus an approximation (the trend), with the energy in each. The bands are dyadic octaves — the first detail band covers periods of about 2-4 observations, the next 4-8, the next 8-16, and so on. On a constructed period-12 signal, the energy lands in the 8-16 band (where period 12 belongs) and the trend in the approximation (95% of energy) — correctly localizing the cycle. Read which band holds the energy to identify the dominant period range, and read the band's time profile to see when that cycle is active. Note that wavelet coefficients near the start and end of the series are affected by edge artifacts within roughly a filter-length of the boundaries.

## Related Techniques
- *(use after)* `wavelet_coherence_phase_lag` to compare the time-frequency structure of two series.
- *(alternatives)* `fft_spectrum`/`periodogram_spectral_density` for a global spectrum; `emd_hht` for an adaptive (data-driven band) decomposition; `ssa` for variance-based component separation.

## Technical Detail
The transform is a discrete wavelet decomposition (PyWavelets `wavedec`) using the chosen wavelet (Daubechies-4 by default) to a chosen level (defaulting to an automatic, preset-capped depth). It produces dyadic detail bands — band D1 covers periods of roughly 2-4 observations, D2 4-8, D3 8-16, and so on — plus an approximation band holding the trend. Energy per band identifies the dominant period range; edge effects affect coefficients within about a filter length of the boundaries.
*Reference run:* a constructed period-12 signal, Daubechies-4, Balanced — the cycle's energy concentrated in the 8-16 (D3) band where period 12 belongs, with the trend in the approximation band (95% of energy).
