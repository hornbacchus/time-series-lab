# Phase 3 Session 11 — Batch 7 entry findings (Python spectral)

**Date:** 2026-04-29
**Master plan reference:** §15.9 (Python spectral)
**Wrappers in scope:** 7
**Verdicts:** **6 PASS, 1 CAVEAT, 0 BLOCK**
**Sessions used:** 1 (master plan budgeted 2; closed in 1, extending Phase 3 lead to 5–6 sessions ahead)

## Wrappers covered

| # | Wrapper | Reference | Verdict | Tolerance Achieved |
|---|---|---|---|---:|
| 1 | `fft_spectrum` | numpy.fft | PASS | 2.84e-14 abs (Pattern A) |
| 2 | `periodogram_spectral_density` | scipy.signal.periodogram | PASS | 0.0 abs (Pattern A same-library) |
| 3 | `lomb_scargle` | astropy.timeseries.LombScargle | PASS | 0.0 on peak-freq (Pattern J alignment-via-metric) |
| 4 | `wavelet_transform` | direct pywt.wavedec | PASS | 0.0 abs (Pattern A same-library) |
| 5 | `wavelet_coherence` | self-parity reference | PASS | 0.0 abs (Pattern K → Pattern A) |
| 6 | `emd_hht` | PyEMD.EMD | CAVEAT | n_imfs ±2; ρ=0.991 (Tier C) |
| 7 | `ssa_model` | from-scratch numpy SVD | PASS | 0.0 abs (Pattern K → Pattern A) |

## Headline findings

### 1. Pattern A → 20 wrappers (was 14)

Six of seven Batch 7 wrappers achieved bit-exact parity, many
at exactly 0.0 abs diff. All-Python in-process references
make this batch the most bit-exact-favorable to date.

### 2. Pattern F — first concrete population beyond GARCH/Kalman/HMM/VAR

Four new structural invariants populated, replacing Session 5
NotImplementedError stubs:

- `fft_roundtrip` (ifft(fft(x))==x) — verified at 6.66e-16
- `fft_energy_conservation` (Parseval) — verified exactly
- `wavelet_inverse_roundtrip` (waverec(wavedec(x))==x) —
  verified at 3.11e-15
- `wavelet_energy_conservation` (Parseval-like for orthogonal
  wavelets) — verified at 5e-16 relative under
  mode='periodization'

**12 concrete invariants in production** (was 8 at Batch 6 close).

### 3. Pattern J → third concrete instance + new resolution sub-pattern

`p3_lomb_scargle` introduces "alignment-via-metric" as a third
Pattern J resolution mechanism. scipy and astropy
Lomb-Scargle implementations agree on the underlying math but
differ on output normalization. Resolution: pick a metric
that's invariant under the normalization difference (peak
frequency LOCATION rather than absolute power). Cleaner than
tolerance widening when SHAPE agrees but SCALE differs.

### 4. Pattern K → Pattern A path expansion

Two additional wrappers (`wavelet_coherence`, `ssa_model`)
followed the Session 10 Pattern K → Pattern A path. **5
wrappers cumulatively** resolved this way. Empirically
locked.

### 5. Tier C / em_stochastic — second wrapper joins p3_nar_narx

`p3_emd_hht` is the second Tier C wrapper. CAVEAT verdict
with 0.991 energy-curve correlation confirms the convention
locked at S8: when TSL and reference are independent
implementations of the same iterative algorithm, comparison
via reconstruction identity + output-count tolerance +
correlation on the output-distribution curve.

### 6. PyBridge first production batch — simplification candidate

Batch 7 was the FIRST batch consuming PyBridge primitives.
Observation: all 7 checks used direct `import` + call (matching
the established p3_pca / p3_dfm precedent). PyBridge.py_invoke
shim was NOT actually invoked. Banked for check-in 1.5:
PyBridge's `isolate=False` path may be over-engineered for
Batch 7–8 needs; reserve PyBridge purely for subprocess
isolation (`isolate=True` for Batch 9 DL).

### 7. §10.3 criteria — second consecutive batch passing both 1 and 2

| Batch | Criterion 1 | Criterion 2 |
|---|---|---|
| Batch 6 (S10) | 80% improvement | 30–40% reduction |
| **Batch 7 (S11)** | 70% improvement | 35–45% reduction |

The empirical pattern is locked: distinct-wrapper batches with
mostly self-parity OR Python-in-process references achieve
both criteria. R-subprocess overhead (per Batch 3–5) drove the
earlier 10–15% reduction baseline.

## Cumulative Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 7) | **43** / 70 |
| Batch 1 | 10 |
| Batch 2 (S6) | 4 |
| Batch 3 (S7) | 4 |
| Batch 4 (S8) | 5 |
| Batch 5 (S9) | 5 |
| Batch 6 (S10) | 8 |
| **Batch 7 (S11)** | **7** |
| Phase 3 sessions used | 10 (S2–S11) |
| **Pace** | **5–6 sessions ahead of master plan** |
| BLOCK cumulative | 0 |
| CAVEAT cumulative | 5 (p3_stl, p3_mstl, p3_star, p3_nar_narx, **p3_emd_hht NEW**) |

## Pattern catalog status

- **Pattern A:** 20 wrappers (was 14)
- **Pattern B:** 4 wrappers
- **Pattern C:** 2 wrappers
- **Pattern D:** 1 wrapper
- **Pattern E:** 2 wrappers
- **Pattern F:** **12 concrete invariants** (was 8 at Batch 6
  close; +4 fft/wavelet roundtrip + energy)
- **Pattern G:** 1 wrapper
- **Pattern H DSCD:** 4 wrappers
- **Pattern J candidate:** 3 concrete instances (egarch, pp,
  lomb_scargle); 3 resolution sub-patterns
- **Pattern K:** 1 true NO-REFERENCE (`p3_nar_narx`); 5
  wrappers via Pattern K → Pattern A path
- **Tier C / em_stochastic Pattern K convention:** 2 wrappers
  (nar_narx, emd_hht)

## Item 13 budget revision — empirically locked

Master plan §11 §15 budgets 18–22 sessions for Phase 3.
Empirical evidence after Batch 7:

- 7 batches × ~1 session-each-on-average so far (S2–S11)
- 27 wrappers remaining at current pace ≈ 4–5 more sessions
- **Empirical closure horizon: 14–16 sessions total**
  (we're at 10 used; budget assumed 18–22)

Item 13 (budget revision) is now empirically locked at the
14–16 closure-horizon. Banked for check-in 1.5 disposition.

## CI matrix changes shipping in this commit

Per locked discipline (sessions 4–6 hardening):
- `parity-fast.yml`: + astropy, PyWavelets, EMD-signal, pyts
  (Python pip)
- `MANIFEST.toml`: + astropy=7.2.0, PyWavelets=1.8.0,
  EMD-signal=1.9.0, pyts=0.13.0 under [python.packages]
- R install matrix unchanged (R biwavelet rejected as reference
  for wavelet_coherence due to methodology divergence)

## Verification

- `python -m reference_parity --tier fast` → 46 PASS + 5
  CAVEAT (4 prior + p3_emd_hht new) + 0 BLOCK + 0 ERROR.
  Total: 51 / 51 in 187.4s.
- All 7 Batch 7 checks invoked individually; all PASS or
  expected-CAVEAT.
- Tolerance ladder entries added for all 7 wrappers in
  `harness/tolerances.py` with justifications.
- Pattern F invariant registry: 4 new concrete checkers
  populated (fft_roundtrip, fft_energy_conservation,
  wavelet_inverse_roundtrip, wavelet_energy_conservation)
  replacing Session 5 stubs.

## Items banked (do NOT surface in commit message)

- Check-in 1.5 disposition is following Session 11 close per
  user-locked Session 11 prompt; explicitly NOT a commit
  concern.

## Next session

Session 12 — Batch 8 entry per master plan §15.10 (Python ML).
7 wrappers in scope:

- random_forest_forecast, xgboost_forecast,
  lightgbm_forecast, gradient_boosting_forecast,
  knn_forecast, elastic_net_forecast, mapie_intervals

Likely all-PASS Pattern A (closed-form OLS-class refs for
most ML wrappers). `mapie_intervals` is the conformal
wrapper; `conformal_nominal_coverage` invariant
(currently stubbed) gets first concrete population.
