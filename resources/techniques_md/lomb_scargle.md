# Lomb-Scargle Periodogram

## What It Does

The Lomb-Scargle periodogram estimates the power spectrum of a time series that is **irregularly sampled** -- where observations are not equally spaced in time. Standard FFT-based methods require regular spacing, but Lomb-Scargle handles arbitrary observation times by fitting sinusoidal models at each candidate frequency using least squares. It is the standard tool for spectral analysis when data has gaps, uneven sampling, or missing observations.

## When to Use It

- Your time series has irregular or uneven time spacing
- Data has gaps or missing observations that prevent standard FFT analysis
- You are working with astronomical, geophysical, or environmental data with irregular sampling
- Clinical or event-driven data arrives at non-uniform intervals
- You want to detect periodicities in data that cannot be resampled to a regular grid without information loss

## Key Assumptions

- The signal can be represented as a combination of sinusoidal components
- The noise is Gaussian and independent across observations (for significance testing)
- The irregular sampling is not itself periodic (which could create aliasing artifacts)
- The candidate frequencies are chosen to cover the range of interest with adequate density
- The data has been detrended (the mean should be removed)

## Outputs

- **Lomb-Scargle power spectrum**: power at each candidate frequency
- **Dominant frequencies and periods**: peaks in the power spectrum
- **Significance levels**: false alarm probabilities for each peak (the probability of observing such a peak by chance)
- **Spectral window function**: showing how the irregular sampling affects the spectral response
- **Phase estimates** at significant frequencies

## Technical Details

**Standard periodogram limitation**: The DFT requires equal spacing. With irregular sampling, the standard periodogram loses its statistical properties (it is no longer related to the sample autocovariance in a simple way).

**Lomb-Scargle formulation**: For observations `(t_j, y_j)` at irregular times, the Lomb-Scargle power at frequency `f` is:

`P(f) = (1 / (2 sigma^2)) * { [sum_j (y_j - y_bar) cos(2*pi*f*(t_j - tau))]^2 / sum_j cos^2(2*pi*f*(t_j - tau)) + [sum_j (y_j - y_bar) sin(2*pi*f*(t_j - tau))]^2 / sum_j sin^2(2*pi*f*(t_j - tau)) }`

where `sigma^2` is the variance of the data, `y_bar` is the mean, and `tau` is a time offset defined by:

`tan(4*pi*f*tau) = sum_j sin(4*pi*f*t_j) / sum_j cos(4*pi*f*t_j)`

The offset `tau` makes the power invariant to time shifts and ensures the sine and cosine components are orthogonal.

**Equivalence to least-squares fitting**: P(f) is equivalent to the reduction in chi-squared when fitting a sinusoidal model `a cos(2*pi*f*t) + b sin(2*pi*f*t)` to the data, normalized by the total variance. This makes the method equivalent to a sequence of least-squares harmonic regressions.

**Frequency grid**: Unlike the FFT which uses Fourier frequencies `k/N`, Lomb-Scargle evaluates power at arbitrary frequencies. Common choices:
- Uniform grid from 0 to the pseudo-Nyquist frequency `1 / (2 * median(dt))` with step `1 / (T_total * oversampling_factor)`.
- The oversampling factor (typically 4-10) interpolates between natural frequencies for smoother spectra.

**Significance testing**: Under the null hypothesis of pure Gaussian white noise, each `P(f)` follows an exponential distribution. The false alarm probability (FAP) for a peak height z is:

`FAP = 1 - (1 - exp(-z))^M`

where M is the number of independent frequencies tested (approximately `N/2` for N observations, but the effective number depends on the frequency grid density). Baluev's analytical approximation provides more accurate FAP estimates.

**Generalized Lomb-Scargle**: Extensions include:
- **Floating mean**: Fit an offset along with the sinusoid, important when the mean is uncertain.
- **Weighted LS**: Assign weights `w_j` to each observation to handle heteroskedastic errors.
- **Multi-harmonic**: Fit multiple harmonics simultaneously for non-sinusoidal periodic signals.

**Spectral window**: The irregular sampling creates a non-trivial spectral window function. Compute it by applying Lomb-Scargle to a synthetic unit-amplitude sinusoid sampled at the actual observation times. Sidelobes in the window function can create spurious peaks in the data's spectrum.

**Aliasing**: Unlike regular sampling where aliasing is well-defined, irregular sampling can partially suppress aliasing. However, clusters of observations at regular intervals can create aliasing at unexpected frequencies.
