# Phase 3 Batch 7 — `p3_lomb_scargle` Audit

**Wrapper:** `engine/techniques/lomb_scargle.py`
**Reference:** `astropy.timeseries.LombScargle` (astropy 7.2.0)
**Verdict:** **PASS** (Pattern J — alignment via metric selection)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | abs diff | status |
|---|---:|---:|---:|---|
| `peak_freq` | 0.12992 | 0.12992 | 0.0 | PASS (exact) |

### Diagnostic (report-only)

| Metric | TSL (scipy) | Reference (astropy) |
|---|---:|---:|
| `peak_power` | 0.9382 | 0.9386 |

**Outcome:** byte-identical peak-frequency location.
**Pattern J classic:** scipy.signal.lombscargle and
astropy.timeseries.LombScargle use DIFFERENT normalization
conventions:

- scipy `normalize=True`: returns power in [0, 1] range
  using Lomb 1976 / Scargle 1982 inverse-variance scaling.
- astropy `normalization="standard"`: Townsend 2010
  generalized LS with mean-subtraction.

Absolute power values differ expectedly (~4e-4 here).
**Peak frequency LOCATION is normalization-invariant** —
both implementations identify the same dominant frequency
bin against the same frequency grid. Comparison aligned by
metric selection (peak frequency, not absolute power).

## Fixture

- DGP: irregularly-sampled sinusoid (true_freq=0.13,
  amplitude=1.0, σ=0.2, ~30% missingness via random
  subsampling), T=200 originally, kept ~140 samples,
  seed=42

## Diagnostics

- Both arms use SAME frequency grid:
  freq_min=1/T, freq_max=0.5, n_freqs=5*N
- TSL: scipy.signal.lombscargle(t, y_demean, omegas,
  normalize=True)
- Reference: astropy.LombScargle(t, y, normalization='standard',
  fit_mean=True, center_data=True).power(freqs)
- astropy version: 7.2.0
