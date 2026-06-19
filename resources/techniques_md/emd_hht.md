## What It Does
Empirical Mode Decomposition (EMD) with the Hilbert-Huang Transform decomposes a series into a handful of data-driven oscillatory components called intrinsic mode functions (IMFs), plus a residual trend. Unlike Fourier or wavelet methods, which use fixed basis functions, EMD derives the components *from the data itself*, so it adapts to non-stationary and nonlinear series. The Hilbert transform then gives each IMF an instantaneous frequency and amplitude over time.

## When to Use It
- You want a fully data-driven decomposition with no fixed basis or pre-specified frequencies.
- Your series is non-stationary or nonlinear and fixed-frequency methods struggle.
- You want instantaneous (time-varying) frequency and amplitude for each component.
- Use EMD/HHT for adaptive decomposition of nonlinear/non-stationary series; use `wavelet_transform` for a fixed multi-resolution view; use `ssa` for a variance-based decomposition.

## How to Read the Result
The output is the set of IMFs (ordered from highest to lowest frequency), a residual trend, and per-IMF mean period and energy. On a constructed period-12 signal, the dominant IMF has a mean period of 12.1 — recovering the cycle. Read the IMFs from fast to slow: the early ones capture high-frequency detail, the later ones slower cycles, and the residual the trend. Two important caveats. First, the IMF energy shares do *not* sum to 100% — the IMFs are not orthogonal, so unlike SSA or PCA this is not an additive variance decomposition; treat the shares as relative importance, not partitioned variance. Second, EMD can suffer mode mixing, where a single cycle is split across IMFs or two cycles blend into one — so an IMF is not guaranteed to be a single clean oscillation, and an instantaneous frequency is only meaningful for an IMF that is genuinely mono-component.

## Related Techniques
- *(use after)* analyze a dominant IMF's instantaneous frequency, or `fft_spectrum` on an IMF to confirm its period.
- *(alternatives)* `wavelet_transform` (fixed bands, orthogonal); `ssa` (variance-ordered, additive); `stl_decompose` for explicit trend-plus-seasonal.

## Technical Detail
The decomposition is empirical mode decomposition (PyEMD): iterative sifting extracts intrinsic mode functions until a residual remains, then the Hilbert transform yields each IMF's instantaneous frequency and amplitude. The number of IMFs is capped by a parameter; the EEMD variant (noise-assisted ensemble, used under the Thorough preset) mitigates mode mixing by averaging decompositions of noise-perturbed copies. Because the sifting is iterative and (for EEMD) noise-driven, the procedure is stochastic; IMFs are non-orthogonal so their energy shares are not an additive variance partition.
*Reference run:* a constructed period-12 signal, standard EMD, Balanced — 8 IMFs extracted, the dominant IMF (IMF 2) with a mean period of 12.1, recovering the cycle.
