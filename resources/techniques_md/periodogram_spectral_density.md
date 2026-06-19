## What It Does
The periodogram estimates a series' spectral density — how its variance is distributed across frequencies — to reveal the dominant cycles. A peak at a given frequency means the series has a strong cyclical component at that period. It is the classical first tool for finding periodicities: feed in a series, read off the frequencies (and corresponding periods) where the energy concentrates.

## When to Use It
- You want to find the dominant cycle(s) in a series (a weekly pattern, an annual cycle, a business-cycle frequency).
- You want the whole frequency picture, not just whether one specific period is present.
- The series is regularly sampled (evenly spaced observations).
- Use the periodogram for evenly-sampled data; use `lomb_scargle` for irregular timestamps or gaps; use `wavelet_transform` when the cycles change over time.

## How to Read the Result
The output is the spectral density across frequencies, the dominant frequency, and its period. Frequency is in cycles per observation (the maximum meaningful value is 0.5, the Nyquist frequency), and the period is its reciprocal. On a constructed signal with a period-12 cycle, the periodogram returns a dominant frequency of 0.084 — a period of 11.9, recovering the true cycle — carrying 44% of the power. The spectral entropy (0.33 here) measures how concentrated the spectrum is: low means a few sharp cycles dominate, high means broadband noise with no clear periodicity. One caveat: the raw periodogram is an unbiased but high-variance estimate, so a noisy-looking spectrum is expected — a smoothed (Welch) estimate trades resolution for lower variance.

## Related Techniques
- *(use after)* `wavelet_transform` to see whether a dominant cycle is stable over time or localized.
- *(alternatives)* `fft_spectrum` (the raw amplitude spectrum); `lomb_scargle` (uneven sampling); `ssa` to extract the cyclical component as a series.

## Technical Detail
Estimation is scipy's periodogram (the squared magnitude of the Fourier transform, optionally windowed). Frequency is in cycles per observation; the period is the reciprocal of frequency. A window (Hann by default) reduces spectral leakage. The series is detrended before transforming, and the dominant frequencies are reported with their power shares and the spectral entropy.
*Reference run:* a constructed signal with a period-12 cycle plus mild noise (n≈256), Balanced — dominant frequency 0.084 (period 11.9, recovering the true cycle), 44% of the power, spectral entropy 0.33.
