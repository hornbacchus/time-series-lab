# Phase 3 Batch 7 — `p3_wavelet_coherence` Audit

**Wrapper:** `engine/techniques/wavelet_coherence.py`
**Reference:** from-scratch reference mirroring TSL recursion
verbatim (pywt 1.8.0 + scipy 1.17.1)
**Verdict:** **PASS** (Pattern A self-parity bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Component | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `mean_coherence` | 0.0 | 0.0 | PASS (exact) |
| `mean_phase` | 0.0 | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement on scale-averaged
coherence and phase. Both arms invoke `pywt.cwt` with
identical Morlet wavelet ('morl'), identical
`scipy.ndimage.uniform_filter1d` smoothing kernel
(width=5), and identical scale grid (n_scales=64,
log-spaced over [2, N/4]).

## Fixture

- DGP: two coherent sinusoids with lead-lag relationship.
  Series x(t) = sin(2π t/32) + 0.3·N(0,1); y(t) = x(t)
  shifted forward by 4 samples + 0.3·N(0,1). T=256, seed=42
- Wavelet: morl (Morlet)
- 64 scales, smoothing width 5

## Diagnostics

- True period: 32 samples
- True lag: 4 samples (y leads x)
- pywt version: 1.8.0

## Pattern K → Pattern A path (Tier B sub-component)

Original Pattern K candidate: R `biwavelet` package implements
a different coherence estimator (Liu-Liang-Weisberg 2007 with
Monte Carlo significance) — not directly comparable. The
custom phase-lag estimator (scale-averaged circular mean of
phase angle) has no canonical reference at all. Resolution:
self-parity reference inline in `harness/checks/p3_wavelet_coherence.py`
(~50 LOC) mirrors TSL's CWT-based coherence + smoothing
formula verbatim. Catches wrapper-level regressions in CWT
invocation, smoothing application, or coherence-formula
arithmetic.
