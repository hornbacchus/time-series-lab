## What It Does
The FFT spectrum computes the fast Fourier transform of a series and reports its amplitude (and power) at each frequency, identifying the dominant periodic components. It is the most direct frequency-domain view of a series: which cycles are present and how strong each is. Where the periodogram emphasizes the spectral density, this emphasizes the amplitude spectrum and the ranked list of dominant periods.

## When to Use It
- You want the amplitude or power at each frequency and a ranked list of the strongest cycles.
- You want a direct, fast decomposition of a regularly-sampled series into its frequency components.
- The series is evenly sampled and roughly stationary over the window.
- Use the FFT for evenly-sampled stationary data; use `lomb_scargle` for irregular sampling; use `wavelet_transform` when the frequency content changes over time.

## How to Read the Result
The output is the amplitude/power at each frequency and the top dominant periods. On a constructed two-cycle signal (a period-12 and a period-4 component), the FFT correctly returns a dominant period of 11.9 and a second period of 4.0 — recovering both. Frequency is in cycles per observation, period is its reciprocal. Two caveats: with no window applied by default, spectral leakage can spread a sharp cycle's energy into neighboring frequencies (apply a window if peaks look smeared); and the FFT assumes the frequency content is constant over the whole series — if cycles strengthen, fade, or shift over time, the global spectrum blurs them together and a wavelet transform is the better tool.

## Related Techniques
- *(use after)* `wavelet_transform` to check whether a dominant cycle is stable across the sample.
- *(alternatives)* `periodogram_spectral_density` (spectral density estimate); `lomb_scargle` (uneven sampling); `ssa` to extract a component as a reconstructed series.

## Technical Detail
The transform is scipy's FFT. The series is mean-detrended by default; an optional window reduces leakage. Frequency is in cycles per observation and the period is its reciprocal; the dominant periods are reported by descending power, subject to a minimum-period cutoff. The amplitude spectrum is the magnitude of the transform.
*Reference run:* a constructed signal combining a period-12 and a period-4 cycle (n≈256), Balanced — dominant period 11.9 (frequency 0.084) and a second period of 4.0, recovering both components.
