# GCC-PHAT Delay Estimation

## What It Does

GCC-PHAT (Generalized Cross-Correlation with Phase Transform) estimates the **time delay** between two signals by computing a sharpened cross-correlation in the frequency domain. The PHAT weighting normalizes the cross-spectrum by its magnitude, retaining only the phase information. This produces a much sharper correlation peak than standard cross-correlation, enabling more precise delay estimation, especially in the presence of noise and reverberation.

## When to Use It

- You need precise time delay estimation between two versions of a related signal
- Standard cross-correlation produces broad or ambiguous peaks due to signal autocorrelation
- The signals are noisy and you want a method robust to spectral coloring
- You are working with acoustic signals (speaker localization, echo detection)
- You need sub-sample delay accuracy through interpolation of the GCC peak

## Key Assumptions

- One signal is a delayed (and possibly noisy) version of the other
- The delay is constant over the analysis window (or slowly varying for windowed analysis)
- The signals share sufficient spectral overlap for the phase information to be meaningful
- The noise is not so severe that the phase information is destroyed at all frequencies
- The sampling rate is high enough to resolve the delay of interest (or interpolation is used)

## Outputs

- **Estimated time delay**: the lag producing the maximum GCC-PHAT value
- **GCC-PHAT function**: the sharpened cross-correlation across all candidate delays
- **Peak sharpness**: indicating the reliability of the delay estimate
- **Confidence measure**: the peak-to-sidelobe ratio or peak prominence
- **Sub-sample delay**: when interpolation is applied around the peak

## Technical Details

**Standard Generalized Cross-Correlation**: For two signals `x(t)` and `y(t)` with Fourier transforms `X(f)` and `Y(f)`:

The cross-power spectral density is: `G_{xy}(f) = X(f) * Y*(f)` (where * denotes conjugate).

The GCC with weighting function `W(f)` is:

`R_{xy}(tau) = integral W(f) G_{xy}(f) exp(j*2*pi*f*tau) df`

The delay estimate is: `tau_hat = argmax_tau R_{xy}(tau)`

**PHAT weighting**: The Phase Transform weighting normalizes by the cross-spectrum magnitude:

`W_{PHAT}(f) = 1 / |G_{xy}(f)| = 1 / |X(f) Y*(f)|`

This gives: `R_{xy}^{PHAT}(tau) = integral [G_{xy}(f) / |G_{xy}(f)|] exp(j*2*pi*f*tau) df`

The weighted cross-spectrum `G_{xy}(f) / |G_{xy}(f)|` has unit magnitude at all frequencies and retains only the phase `angle(X(f) Y*(f))`. The inverse Fourier transform of this "whitened" cross-spectrum produces a very sharp peak at the true delay.

**Why PHAT works**: Standard cross-correlation is dominated by frequencies with high power. If the signal has a colored spectrum (e.g., strong low-frequency content), the cross-correlation peak is broadened by the autocorrelation of the signal. PHAT equalizes all frequencies, so the peak is determined purely by the phase alignment, producing a much sharper (ideally a delta function) peak.

**Discrete implementation**:
1. Compute DFTs: `X_k` and `Y_k` for k = 0, ..., N-1.
2. Cross-spectrum: `G_k = X_k * conj(Y_k)`.
3. PHAT weighting: `G_k^{PHAT} = G_k / (|G_k| + epsilon)`, where epsilon is a small regularization constant to avoid division by zero.
4. Inverse DFT: `R_{xy}^{PHAT}(m) = IFFT(G_k^{PHAT})`.
5. Find peak: `tau_hat = argmax_m |R_{xy}^{PHAT}(m)|`.

**Regularization**: At frequencies where `|G_k|` is very small (low SNR), the PHAT normalization amplifies noise. Adding a regularization `epsilon` (typically 1e-6 times the maximum `|G_k|`) stabilizes the estimate. Alternatively, use a frequency-weighted PHAT that blends between PHAT and standard GCC based on the local SNR.

**Sub-sample interpolation**: The discrete GCC-PHAT has resolution limited to one sample. For finer resolution:
- **Parabolic interpolation**: Fit a parabola to the peak and its two neighbors.
- **Zero-padding**: Pad the weighted cross-spectrum with zeros before IFFT to interpolate the peak.
- **Sinc interpolation**: Use the sinc function to interpolate between samples.

**Comparison with other GCC weightings**:
- **Unweighted (GCC)**: `W(f) = 1`. Same as standard cross-correlation. Broad peaks.
- **SCOT (Smoothed Coherence Transform)**: `W(f) = 1/sqrt(G_xx * G_yy)`. Intermediate sharpness.
- **ML (Maximum Likelihood)**: `W(f) = |gamma_{xy}|^2 / (|G_xy|(1 - |gamma_{xy}|^2))`. Optimal in Gaussian noise but requires coherence estimation.

**Windowed analysis**: For signals where the delay changes over time, apply GCC-PHAT to overlapping short windows (similar to STFT). This produces a delay trajectory over time.

## Interpretation

**Plain-Language Finding (Tier 1)** - estimated delay in time units via GCC-PHAT, SNR with confidence descriptor (low/moderate/high), 95% bootstrap CI.

**Technical Interpretation (Tier 2)** - PHAT weighting mechanics, peak at lag in samples, SNR definition (peak vs median-around-peak), bootstrap CI construction.

**Caveats (Tier 3, conditional)**:
- Low SNR (< 3) - delay-estimate confidence low.
- Wide CI (> 20% of point estimate) - uncertainty large relative to magnitude.
