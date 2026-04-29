# Phase 3 Batch 7 — `p3_fft_spectrum` Audit

**Wrapper:** `engine/techniques/fft_spectrum.py`
**Reference:** `numpy.fft.fft` (numpy 2.4.4)
**Verdict:** **PASS** (Pattern A bit-exact, machine precision)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Component | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `fft_real` | 2.84e-14 | 3.74e-13 | PASS |
| `fft_imag` | 1.55e-14 | 1.19e-12 | PASS |
| `fft_abs` | 2.84e-14 | 2.18e-14 | PASS |

### Pattern F structural invariants

| Invariant | Status | Residual |
|---|---|---:|
| `fft_roundtrip` | PASS | 6.66e-16 |
| `fft_energy_conservation` | PASS | 0.0 (exact) |

**Outcome:** machine-precision agreement. scipy.fft and
numpy.fft both wrap pocketfft (since numpy 1.17) with
different wrapper code paths but identical computational
core. Pattern F invariants verify Parseval theorem and
inverse-roundtrip identity at machine precision.

## Fixture

- DGP: 3-tone sinusoid (f=0.05, 0.13, 0.25) + N(0, 0.04)
  noise, T=512, seed=42

## Diagnostics

- Mean-detrend applied (matches TSL's default `detrend='mean'`)
- numpy version: 2.4.4
- Pattern F invariants populated this batch (FFT roundtrip
  + energy conservation; replaces Session 5
  NotImplementedError stubs)
