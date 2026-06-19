## What It Does
The Lomb-Scargle periodogram finds periodicities in *unevenly-sampled* data — series with gaps, irregular timestamps, or missing observations, where an ordinary FFT cannot be applied. It is the standard frequency-analysis tool when the sampling is not regular: it fits sinusoids of varying frequency directly to the observed time points, so the spacing need not be uniform.

## When to Use It
- Your data are irregularly sampled — gaps, missing values, or non-uniform timestamps.
- You want the dominant cycle of a series an FFT cannot handle because of uneven spacing.
- You have an evenly-sampled series too, but want a method robust to later-introduced gaps.
- Use Lomb-Scargle for irregular sampling; use `fft_spectrum` or `periodogram_spectral_density` for evenly-sampled data (faster and simpler there).

## How to Read the Result
The output is the periodogram power across periods, the dominant period, and a false-alarm probability. On a constructed period-12 signal it returns a period of 12.0 when regularly sampled — and, importantly, 12.0 again when 20% of the observations are randomly dropped, confirming it handles the irregular case where an FFT would fail. The false-alarm probability gauges significance, but note it is conservative here: a clean sinusoid can be flagged as "not significant" even when the period is recovered correctly, so trust the recovered period and treat the false-alarm probability as a strict lower bar rather than a verdict.

## Related Techniques
- *(use after)* `wavelet_transform` to check stability of a cycle over time.
- *(alternatives)* `fft_spectrum` / `periodogram_spectral_density` for evenly-sampled data; `ssa` to extract the component.

## Technical Detail
The method is scipy's Lomb-Scargle implementation, which fits sinusoids across a frequency grid directly to the (possibly irregular) sample times. The frequency search range and oversampling are set internally; the false-alarm probability follows the Baluev approximation. On regularly-sampled data it reduces to an ordinary periodogram. The dominant period is the reciprocal of the peak frequency.
*Reference run:* a constructed period-12 signal (n≈256), Balanced — period 12.0 when regularly sampled, and period 12.0 again with 20% of observations randomly dropped (an irregularity measure of 0.44), confirming the uneven-sampling capability.
