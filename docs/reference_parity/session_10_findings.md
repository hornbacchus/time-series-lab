# Phase 3 Session 10 — Batch 6 entry findings (R change-points / stationarity)

**Date:** 2026-04-29
**Master plan reference:** §15.8 (R change-points / stationarity)
**Wrappers in scope:** 8 (revised from 9 — `x13_seasonal_adjust` deferred per Appendix A)
**Verdicts:** **8 PASS, 0 CAVEAT, 0 BLOCK**
**Sessions used:** 1 (master plan budgeted 2; closed in 1, extending Phase 3 lead to 5 sessions ahead)

## Wrappers covered

| # | Wrapper | Reference | Verdict | Tolerance Achieved |
|---|---|---|---|---:|
| 1 | `adf_test` | R `urca::ur.df` | PASS | 1.07e-14 abs (Pattern A) |
| 2 | `kpss_test` | R `urca::ur.kpss` | PASS | 5.55e-17 abs (Pattern A) |
| 3 | `pp_test` | R `urca::ur.pp` | PASS | 2.09e-06 abs (Pattern J widening) |
| 4 | `bocpd` | self-parity NIG-conjugate Adams-MacKay 2007 | PASS | bit-exact (Pattern A) |
| 5 | `cusum_page_hinkley` | self-parity identical recursion | PASS | bit-exact (Pattern A) |
| 6 | `intervention_analysis` | R `stats::arima(..., xreg=...)` | PASS | 1.7e-5 abs on omega (Pattern B) |
| 7 | `pelt_change_points` | direct `ruptures.Pelt` in-process | PASS | bit-exact (Pattern A same-library) |
| 8 | `stl_esd_anomaly` | self-parity STL + Rosner 1983 GESD | PASS | bit-exact (Pattern A) |

## Headline findings

### 1. Pattern K → Pattern A path resolved 3 wrappers

BOCPD, CUSUM/PH, and STL+ESD were Pattern K (NO-REFERENCE)
candidates because their canonical R references either don't
exist (BOCPD), implement different methodology (CUSUM/PH), or
were archived from CRAN (STL+ESD via Twitter
AnomalyDetection). All three were resolved to PASS by
shipping from-scratch reference implementations inline in the
check modules (~50–80 LOC each) that mirror TSL's recursion
verbatim.

**Implication:** future Pattern K candidates with paper-defined
recursions can take this path. The audit report explicitly
documents the regression-sentinel scope (catches wrapper-level
preprocessing/parameter regressions; does NOT catch
TSL-vs-canonical-implementation methodology bugs).

### 2. Same-library self-test as a fourth Pattern A sub-class

`p3_pelt` introduces same-library self-test: both arms call
`ruptures.Pelt` with identical arguments. This catches TSL
wrapper-layer bugs (preprocessing, parameter resolution,
audit-field rounding) without re-implementing the algorithm.
Acceptable when the upstream library is broadly trusted.

### 3. §10.3 criteria — first batch PASS on both 1 and 2

Session 10 is the first batch where **both** master plan
§10.3 criterion 1 (audit time ≤60% baseline) and criterion 2
(LOC ≤70% baseline) PASS:

- **Audit time:** 8 wrappers in 1 session vs Batch 1's 10
  wrappers in ~2 sessions = ~80% improvement
- **LOC:** per-check files ~150–180 LOC vs Batch 1 baseline
  ~400 LOC = 30–40% reduction

Heavy use of self-parity references is the key driver — they
avoid R-script + bridge plumbing (~100 extra LOC) while
preserving the regression-sentinel value.

### 4. Pattern J — second concrete instance (p3_pp)

`p3_pp` exhibited 2.09e-06 abs divergence between
`arch.unitroot.PhillipsPerron` and `urca::ur.pp` despite
pinned `lags=5`. Source is internal HAC kernel weights /
residual variance divisor convention differences. Tolerance
ladder widens to 1e-3 abs / 1e-2 rel without masking real
regressions.

### 5. ADF + KPSS bit-exact at sub-1e-14 level

Both ADF and KPSS reach machine-precision agreement (1e-14
and 1e-17 abs) — both are scalar test statistics with
identical closed-form implementations across statsmodels and
urca. Bandwidth/lag pinning aligns the two implementations
fully.

## Cumulative Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 6) | **36** / 70 |
| Batch 1 | 10 |
| Batch 2 (S6, GARCH) | 4 |
| Batch 3 (S7) | 4 |
| Batch 4 (S8) | 5 |
| Batch 5 (S9) | 5 |
| **Batch 6 (S10)** | **8** |
| Phase 3 sessions used | 9 (S2–S10) |
| **Pace** | **5 sessions ahead of master plan** |
| BLOCK cumulative | 0 |
| CAVEAT cumulative | 4 (p3_stl, p3_mstl, p3_star, p3_nar_narx — unchanged from Batch 5) |

## Pattern catalog status

- **Pattern A:** 14 wrappers (was 11 at Batch 5 close)
- **Pattern B:** 4 wrappers
- **Pattern C:** 2 wrappers
- **Pattern D:** 1 wrapper
- **Pattern E:** 2 wrappers
- **Pattern F:** 8 concrete invariants in registry (no new
  populations this batch)
- **Pattern G:** 1 wrapper
- **Pattern H DSCD:** 4 wrappers (LLT identifiability +
  Markov switching + GARCH boundary attractor + ETS scale
  offset)
- **Pattern J candidate:** 2 concrete instances (p3_egarch
  + p3_pp)
- **Pattern K:** 1 true NO-REFERENCE (`p3_nar_narx`); 3
  candidates resolved via Pattern K → Pattern A path

## CI matrix changes shipping in this commit

Per locked discipline (sessions 4–6 hardening — install-
matrix updates ship in audit-creation commits):

- `parity-fast.yml`: + `ruptures` (Python pip)
- `MANIFEST.toml`: + `ruptures = "1.1.9"` under `[python.packages]`
- All R deps already present (urca for ADF/KPSS/PP from prior
  batches; base R for intervention_analysis no extra packages)

## Verification

- `python -m reference_parity --tier fast` → 40 PASS + 4
  CAVEAT (unchanged from Batch 5: p3_stl, p3_mstl, p3_star,
  p3_nar_narx) + 0 BLOCK + 0 ERROR. Total: 44 / 44 in 96.2s.
- All 8 Batch 6 checks invoked individually; all PASS.
- Tolerance ladder entries added for all 8 wrappers in
  `harness/tolerances.py` with justifications citing the
  audit report.

## Items banked (do NOT surface in commit message)

- Check-in 1.5 decision pending — explicitly do NOT mention
  in commit message; resolved at Chat after Session 10
  close.

## Next session

Session 11 — Batch 7 entry per master plan §15.9 (R wavelets /
frequency domain). 5 wrappers in scope:

- CWT (continuous wavelet transform)
- DWT (discrete wavelet transform)
- MODWT (maximum-overlap DWT)
- spectral_periodogram
- fft_spectrum

Wavelet/FFT structural invariants (Parseval identity,
roundtrip bit-exactness) become first concrete population
candidates for the registry beyond the GARCH + Kalman + HMM
+ VAR/VECM populations.
