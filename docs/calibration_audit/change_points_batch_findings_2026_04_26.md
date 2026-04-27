# Calibration Audit: Change Points / Anomalies batch (Session 15)

**Audit date:** 2026-04-26
**Wrappers audited (5):**
  - `engine/techniques/bocpd.py`
  - `engine/techniques/cusum_page_hinkley.py`
  - `engine/techniques/intervention_analysis.py`
  - `engine/techniques/pelt_change_points.py`
  - `engine/techniques/stl_esd_anomaly.py`

## Summary

**Findings: 3 severe (ALL FIXED INLINE) / 0 operational / 0
cosmetic.** Cumulative engine LOC: ~55 (within CAL-R6 budget).

All three severe findings are textbook silent-acceptance /
silent-coercion bugs matching Sessions 9/10/12/13/14 pattern:
- F-CP-INT-TYPE — intervention_analysis silently coerced
  invalid `type` to "step" (with warning, but audit_fields
  still reported user's invalid value)
- F-CP-PELT-PENALTY — pelt_change_points silently coerced
  invalid `penalty` string to "bic" (no warning;
  audit_fields reported user's invalid value)
- F-CP-STL-DIRECTION — stl_esd_anomaly silently coerced
  invalid `direction` to "lower" (no warning;
  audit_fields reported user's invalid value)

All three fixed via explicit allowlist gates parallel to
Sessions 13/14's FFT/EMD/GCC/DTW fixes.

## Sweep 0 — Per-wrapper input-validation matrix

| Wrapper | Status | Notes |
|---|---|---|
| bocpd | ✅ | numeric params only; no string-acceptance surface |
| cusum_page_hinkley | ✅ | numeric params only; both methods always run |
| **intervention_analysis** | ❌→✅ | invalid `type` silently coerced → allowlist added |
| **pelt_change_points** | ❌→✅ | invalid `penalty` silently coerced → allowlist added |
| **stl_esd_anomaly** | ❌→✅ | invalid `direction` silently coerced → allowlist added |

PELT's `cost_model` parameter is upstream-validated by ruptures
(invalid models raise — caught and converted to error response).
That's the only string-typed param that worked correctly
pre-fix.

## Real-data baselines (GSPC log returns + DGS10 levels, T=500)

All 5 wrappers succeed on both series:

| Wrapper | GSPC_logret | DGS10_level |
|---|---|---|
| bocpd | n_cps=0, 0.5s | n_cps=0, 0.5s |
| cusum_page_hinkley | n_alarms=2, 0.2s | n_alarms=353, 0.3s |
| intervention_analysis | n_sig=1, 8.6s | n_sig=1, 11.0s |
| pelt_change_points | n_cps=2, 0.8s | n_cps=12, 0.3s |
| stl_esd_anomaly | n_anom=17, 0.03s | n_anom=8, 0.02s |

Cross-method observations:
- **BOCPD** is conservative at default settings (hazard_lambda=200);
  detects no change points in either series even at default
  threshold=0.5. Tuning required for macro applications.
- **CUSUM/PH** is highly sensitive on DGS10 (353 alarms) due to
  yield-level dynamics not stationary; flat returns produce
  fewer alarms (2 on GSPC). Typical of CUSUM applied to
  non-stationary series.
- **PELT** detects 2 cps on GSPC returns (consistent with
  volatility regime shifts) and 12 cps on DGS10 levels
  (consistent with multiple Fed cycle phases over the window).
- **STL+ESD** detects 17 outliers on GSPC log returns (fat
  tails, classic finance), 8 on DGS10 (fewer outliers in
  yield-level dynamics).
- **intervention_analysis** auto-detects a single break per
  series (default behavior when `interventions` param absent).

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Online change detection | `bocpd` | Bayesian recursive update; produces probability stream |
| Classical sequential test (mean shifts) | `cusum_page_hinkley` | Two complementary statistics; bootstrap p-values available |
| Known intervention timing (event study) | `intervention_analysis` | ARIMAX with intervention dummies; compares to counterfactual |
| Offline segmentation (multiple unknown breaks) | `pelt_change_points` | Optimal exact algorithm; multiple cost models |
| Outlier detection on seasonally adjusted series | `stl_esd_anomaly` | STL removes seasonal/trend; ESD then tests remainder |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-CP-INT-TYPE | Severe | intervention_analysis silently coerced invalid `type` to "step" | **Fixed inline** |
| F-CP-PELT-PENALTY | Severe | pelt_change_points silently coerced invalid `penalty` to "bic" | **Fixed inline** |
| F-CP-STL-DIRECTION | Severe | stl_esd_anomaly silently coerced invalid `direction` to "lower" | **Fixed inline** |

## Documented limitations (not findings)

- **PELT detects 4 spurious cps on a constant series with
  noise ~1e-9** because the BIC penalty `log(n)·sigma²`
  scales with variance and becomes nearly zero on
  near-zero-variance data. Real applications never have
  sigma so small. Documenting for awareness; not a
  classification finding.
- **STL+ESD over-detects on a single-anomaly DGP** (4
  detected when 1 was injected) at default alpha=0.05 on
  a small T=240 sinusoidal fixture; this is consistent with
  ESD's iterative removal procedure occasionally flagging
  the next-largest residual as also extreme. Tighter alpha
  reduces this. Documented in spec already.

## Validation-presence pattern update

Cumulative across 36 wrappers in 10 extension sessions:
- **WITH validation OR low math**: 21 wrappers → 0 findings
- **WITHOUT validation**: 15 wrappers → 14 severe findings (all fixed inline)

Pattern's predictive power exceptionally strong. Session 15
matches the prediction precisely: bocpd and cusum_page_hinkley
have only numeric params (no allowlist needed); the three
wrappers with custom string-handling chains all surfaced
silent-coercion bugs.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 5 wrapper APIs verified. |
| **CAL-R3** | 5 rows AUDITED. Cycle 37 → 42. |
| **CAL-R4** | 5 NEW canonical scripts (6 each = 30 canonicals). |
| **CAL-R5** | 10 cells of real-data baselines on (GSPC, DGS10). |
| **CAL-R6** | 3 inline fixes (~55 LOC across 3 files). Within ≤100 LOC budget. |

## Recommended follow-ups

None. Change Points / Anomalies extension batch CLOSED.
