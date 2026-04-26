# Calibration Audit: Causality / Lead-Lag batch (Session 14)

**Audit date:** 2026-04-26
**Wrappers audited (6):**
  - `engine/techniques/granger_causality.py`
  - `engine/techniques/cross_correlation_lag.py`
  - `engine/techniques/gcc_phat_delay.py`
  - `engine/techniques/prewhitened_ccf_lag.py`
  - `engine/techniques/rolling_ccf_lag.py`
  - `engine/techniques/dtw_alignment_lag.py`

## Summary

**Findings: 2 severe (ALL FIXED INLINE) / 0 operational / 0
cosmetic.** Cumulative engine LOC: ~40 (within CAL-R6 budget).

Both severe findings are textbook silent-acceptance bugs
matching Sessions 9/10/12/13 pattern:
- F-CL-GCC-WEIGHTING — gcc_phat_delay accepted invalid
  `weighting` silently (if/elif/else fall-through to
  unfiltered W=ones)
- F-CL-DTW-STEP — dtw_alignment_lag accepted invalid
  `step_pattern` silently (if/else fall-through to
  symmetric2)

Both fixed via explicit allowlist gates parallel to Session
13's FFT/EMD fixes.

**Critical question answered:** Did `prewhitened_ccf_lag`
inherit Session 10's pmdarima `start_P` bug? **No.** The
wrapper calls `pm.auto_arima(x, max_p=5, max_q=5, max_d=2)`
without explicitly setting max_P/max_Q/max_D, so pmdarima
uses its defaults which satisfy the `start_P <= max_P`
constraint. Baseline succeeded (1.6s).

## Sweep 0 — Per-wrapper input-validation matrix

| Wrapper | Status | Notes |
|---|---|---|
| granger_causality | ✅ | numeric params only; statsmodels validates |
| cross_correlation_lag | ✅ | numeric params; numpy validates |
| **gcc_phat_delay** | ❌→✅ | invalid `weighting` silent → allowlist added |
| prewhitened_ccf_lag | ✅ | numeric+optional list params |
| rolling_ccf_lag | ✅ | numeric params |
| **dtw_alignment_lag** | ❌→✅ | invalid `step_pattern` silent → allowlist added |

## Real-data baselines (rates pair, T=500)

All 6 wrappers succeed on (DGS2, DGS10) yield-diffs:

| Wrapper | Runtime |
|---|---|
| granger_causality | <0.1s |
| cross_correlation_lag | <0.1s |
| gcc_phat_delay | 0.1s |
| prewhitened_ccf_lag | 1.1s |
| rolling_ccf_lag | 0.2s |
| dtw_alignment_lag | 0.1s |

Cross-reference Sessions 4/9: rates pair found rank=0 (no cointegration on this 10-year window). Causality wrappers can still find directional or contemporaneous relationships independent of cointegration; results documented but not interpreted in this audit.

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Directional causality (X causes Y?) | `granger_causality` | Statistical test for predictive content |
| Unsigned lag detection | `cross_correlation_lag` | Standard CCF; signed correlation at each lag |
| Delay estimation in noisy signals | `gcc_phat_delay` | PHAT weighting whitens cross-spectrum |
| Lag detection accounting for serial autocorrelation | `prewhitened_ccf_lag` | ARIMA-prewhiten before CCF |
| Time-varying lag (regime-aware) | `rolling_ccf_lag` | Sliding-window CCF |
| Nonlinear temporal alignment | `dtw_alignment_lag` | Dynamic time warping |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-CL-GCC-WEIGHTING | Severe | gcc_phat_delay accepted invalid `weighting` silently | **Fixed inline** |
| F-CL-DTW-STEP | Severe | dtw_alignment_lag accepted invalid `step_pattern` silently | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 31 wrappers in 9 extension sessions:
- **WITH validation OR low math**: 19 wrappers → 0 findings
- **WITHOUT validation**: 12 wrappers → 11 severe findings (all fixed inline)

Pattern's predictive power exceptionally strong. Session 14
matches the prediction precisely: GCC-PHAT and DTW had
custom string-handling chains without allowlist gates;
both surfaced bugs.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 6 wrapper APIs verified. |
| **CAL-R3** | 6 rows AUDITED. Cycle 31 → 37. |
| **CAL-R4** | 6 NEW canonical scripts (6 each = 36 canonicals). |
| **CAL-R5** | 6 cells of real-data baselines on (DGS2, DGS10). |
| **CAL-R6** | 2 inline fixes (~40 LOC across 2 files). Within ≤100 LOC budget. |

## Recommended follow-ups

None. Causality/lead-lag extension batch CLOSED.
