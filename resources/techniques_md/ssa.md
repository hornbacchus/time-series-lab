## What It Does
Singular Spectrum Analysis (SSA) decomposes a series into interpretable components — trend, oscillatory cycles, and noise — without assuming a model. It embeds the series into a trajectory matrix of lagged copies, applies a singular value decomposition, and groups the resulting components by similarity. It is a flexible, model-free way to separate a series into its underlying structure, useful for smoothing, trend extraction, or isolating a cycle.

## When to Use It
- You want to separate a series into trend, cyclical, and noise components without specifying a model.
- You want to extract or remove a trend or a specific oscillation as a reconstructed series.
- You want a data-driven decomposition robust to non-stationarity.
- Use SSA to decompose and reconstruct components; use `fft_spectrum`/`periodogram_spectral_density` when you only need the frequencies, not the separated series.

## How to Read the Result
The output is the decomposed components, ranked by how much variance each explains, grouped into trend, oscillatory, and noise. On a constructed trend-plus-period-12 signal, SSA separates a trend component (72% of variance, the leading group) from an oscillatory pair (18%, capturing the cycle) — recovering the structure. Read the components by their variance share and shape: the leading components are the trend and dominant cycles, the trailing ones are noise. One framing point: SSA orders components by *variance*, not by frequency — it does not label a component with a frequency. You identify what each component is (trend versus a particular cycle) by inspecting its shape, which is why a cyclical pair appears as two adjacent components of similar variance.

## Related Techniques
- *(use after)* `fft_spectrum` or `periodogram_spectral_density` on an extracted oscillatory component to pin its frequency.
- *(alternatives)* `emd_hht` (a different model-free decomposition); `stl_decompose` when the structure is explicitly trend-plus-seasonal.

## Technical Detail
The series is embedded into a trajectory matrix with a chosen window length (defaulting to half the series length), decomposed by singular value decomposition, and the components reconstructed by diagonal averaging. Components are grouped — by default through their weighted correlation — into trend, oscillatory, and noise. Components are ordered by variance (singular value), not frequency; semantic identity (trend versus a specific cycle) comes from inspecting the reconstructed shapes.
*Reference run:* a constructed trend-plus-period-12 signal, window length 128, Balanced — a trend component (72% of variance, leading group) separated from an oscillatory pair (18%), recovering the structure.
