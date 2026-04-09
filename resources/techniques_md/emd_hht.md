# EMD / Hilbert-Huang Transform

Empirical Mode Decomposition (EMD) with the Hilbert-Huang Transform (HHT) is a fully adaptive, data-driven method for analyzing nonlinear and non-stationary time series. Unlike Fourier analysis (which assumes stationarity) or wavelet transforms (which require choosing a basis), EMD derives its basis functions directly from the data.

## How It Works

EMD decomposes a signal into a set of Intrinsic Mode Functions (IMFs) through an iterative sifting process. Each IMF represents an oscillatory mode embedded in the data, ordered from highest to lowest frequency. The Hilbert transform is then applied to each IMF to compute instantaneous amplitude and instantaneous frequency, producing a time-frequency-energy representation called the Hilbert-Huang spectrum.

**Ensemble EMD (EEMD)** adds white noise to the signal before decomposition, averaging over many trials. This reduces the mode-mixing problem where different oscillatory modes bleed into the same IMF.

## When to Use

- **Nonlinear and non-stationary signals** where Fourier analysis gives misleading results
- **Time-varying frequency content** — unlike FFT, EMD captures how frequencies change over time
- **Exploratory decomposition** to understand the oscillatory structure of a signal
- **Pre-processing** before applying other techniques (e.g., detrending via residual removal)
- **Geophysical, financial, and biomedical signals** that exhibit complex multi-scale dynamics

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_imfs` | 8 | Maximum number of IMFs to extract |
| `method` | emd | "emd" (standard) or "eemd" (ensemble) |
| `ensemble_size` | 100 | Number of noise-added trials for EEMD |
| `noise_width` | 0.05 | Noise amplitude as fraction of signal standard deviation |

## Output Tables

- **IMF Summary**: Variance, variance %, mean frequency, mean period, and mean amplitude for each IMF and the residual
- **IMF Components**: Time series values for each extracted IMF and the residual
- **Instantaneous Frequency**: Time-varying frequency for each IMF (from Hilbert transform)
- **Configuration**: Method, backend, and parameter settings used

## Dependencies

Uses the `emd` package (Andrew Quinn, Oxford) when available for optimized sifting, EEMD, and CEEMDAN. Falls back to a numpy-based sifting implementation if `emd` is not installed. Install with `pip install emd`. The Hilbert transform always uses `scipy.signal.hilbert`.

## Presets

- **Fast**: Standard EMD, up to 4 IMFs, 50 sift iterations
- **Balanced**: Standard EMD, up to 8 IMFs, 200 sift iterations
- **Thorough**: Ensemble EMD (100 trials), up to 12 IMFs, 500 sift iterations
