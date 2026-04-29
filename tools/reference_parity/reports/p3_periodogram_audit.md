# Phase 3 Batch 7 — `p3_periodogram` Audit

**Wrapper:** `engine/techniques/periodogram_spectral_density.py`
**Reference:** `scipy.signal.periodogram` (scipy 1.17.1)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Component | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `freqs` | 0.0 | 0.0 | PASS (exact) |
| `psd` | 0.0 | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement. Same-library
self-test: TSL and reference both invoke
`scipy.signal.periodogram` with identical arguments
(`window="hann", detrend="linear", scaling="density"`,
fs=1.0). The audit verifies wrapper preprocessing +
parameter resolution round-trips the scipy primitive
without wrapper-introduced bugs.

## Fixture

- DGP: 3-tone sinusoid (f=0.05, 0.13, 0.25) + N(0, 0.04)
  noise, T=512, seed=42

## Diagnostics

- Balanced preset config: window='hann', detrend='linear',
  scaling='density'
- 257 frequency bins (Nyquist + DC; T=512 / 2 + 1)
- scipy version: 1.17.1
