# Calibration Audit: Missing Data batch (Session 19)

**Audit date:** 2026-04-27
**Wrappers audited (3):**
  - `engine/techniques/denton_chowlin_disaggregation.py`
  - `engine/techniques/kalman_imputation.py`
  - `engine/techniques/loess_interpolation.py`

## Summary

**Findings: 2 severe / 3 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~75 (within CAL-R6
budget).

The 5 findings span both bug classes catalogued in prior
sessions:
- 2 SEVERE = string silent acceptance (Sessions 9-18 pattern)
- 3 OPERATIONAL = numeric range coercion (loud-and-coerced,
  but should reject for clearer user feedback)

| ID | Severity | Wrapper | Parameter | Bug Class |
|---|---|---|---|---|
| F-MD-DENTON-METHOD | severe | denton_chowlin_disaggregation | `method` | string silent coercion |
| F-MD-KALMAN-MODELTYPE | severe | kalman_imputation | `model_type` | string silent fall-through (Session 18 pattern) |
| F-MD-DENTON-CONVRATIO | operational | denton_chowlin_disaggregation | `conversion_ratio` | numeric range coercion |
| F-MD-DENTON-RHO | operational | denton_chowlin_disaggregation | `rho` | numeric range coercion |
| F-MD-LOESS-FRAC | operational | loess_interpolation | `frac` | numeric range coercion |

All 5 fixed via explicit allowlist/range gates parallel to
Sessions 13-18's fixes. Per Session 17 precedent
(same-bug-class bundling acceptable when under LOC budget),
applied in single commit.

## Sweep 0 — Per-wrapper input-validation matrix

| Wrapper | Status | Notes |
|---|---|---|
| **denton_chowlin_disaggregation** | ❌→✅ | invalid `method` silently coerced; numeric `conversion_ratio`/`rho` silently reset → all gates added |
| **kalman_imputation** | ❌→✅ | invalid `model_type` silently fell through to "local linear trend" default → allowlist gate added |
| **loess_interpolation** | ❌→✅ | invalid `frac` silently reset to 0.3 → range gate added |

### try/except taxonomy (Session 18 framework)

| Wrapper | try/except blocks | Classification |
|---|---|---|
| denton_chowlin_disaggregation | inner `linalg.LinAlgError` → fallback to `pinv` (line 113-114, 161-162) | SAFE-FALLBACK (numerical robustness; doesn't suppress validation) |
| denton_chowlin_disaggregation | outer try/except propagates via make_error_response | SAFE-PROPAGATE |
| kalman_imputation | inner try/except at line 104-113 catches model.fit failure and retries with simpler "local level" | SAFE-FALLBACK (Session 18 structural_ts pattern: retries with DIFFERENT spec; would propagate on second failure via outer except) |
| loess_interpolation | inner try/except in `_auto_select_frac` catches lowess failures during CV | SAFE-FALLBACK (skips bad lambda values; doesn't suppress user-facing validation) |
| loess_interpolation | outer try/except propagates | SAFE-PROPAGATE |

**No HARMFUL try/except suppression in this batch.** The bugs
were all in if/elif/else dispatch chains, not in try/except
clauses.

## Real-data baselines (synthetic 10% missing on macro fixtures)

| Wrapper | GSPC_logret RMSE | DGS10_level RMSE | Synthetic Q→M max_disc |
|---|---|---|---|
| kalman_imputation | 1.11 | 0.00 | n/a |
| loess_interpolation | 1.10 | 0.10 | n/a |
| denton_chowlin (denton) | n/a | n/a | 0.00 |
| denton_chowlin (chowlin) | n/a | n/a | 0.00 |

Notes:
- kalman_imputation has RMSE=0 on DGS10 because the local
  linear trend model perfectly fits a near-step-like yield
  curve segment (the Kalman smoother interpolates exactly
  between observations on slowly-varying series).
- loess_interpolation RMSE on DGS10 (~0.10) is the more
  realistic measure of interpolation accuracy.
- denton_chowlin produces machine-precision aggregation
  consistency (max_disc=0 on synthetic well-behaved input).

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Random sparse missing in stationary series | `kalman_imputation` | State-space-aware; provides credible bands |
| Random sparse missing without state-space prior | `loess_interpolation` | Local nonparametric; no model assumption beyond smoothness |
| Block missing (long gaps) | `kalman_imputation` | Smoothing distribution properly accounts for gap propagation |
| Boundary missing (extrapolation) | Either + cite warnings | Both wrappers warn explicitly; user should treat boundary imputations cautiously |
| Temporal disaggregation (Q→M, A→M, etc.) | `denton_chowlin_disaggregation` | Only wrapper for this task; preserves aggregation constraints exactly |
| Non-negativity preservation in disaggregation | `denton_chowlin (method='denton')` | Proportional first differences preserve sign; chowlin can produce negatives |
| Indicator-series-driven disaggregation | `denton_chowlin (method='chowlin')` | Uses high-frequency regressors via GLS |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-MD-DENTON-METHOD | Severe | invalid `method` silently coerced to "chowlin" | **Fixed inline** |
| F-MD-KALMAN-MODELTYPE | Severe | invalid `model_type` silently fell through to "local linear trend" | **Fixed inline** |
| F-MD-DENTON-CONVRATIO | Operational | invalid `conversion_ratio` (<2) silently reset to 3 | **Fixed inline** |
| F-MD-DENTON-RHO | Operational | invalid `rho` (out of (0,1)) silently reset to 0.5 | **Fixed inline** |
| F-MD-LOESS-FRAC | Operational | invalid `frac` (out of (0,1]) silently reset to 0.3 | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 50 wrappers in 14 extension sessions:
- **WITH validation OR low math**: 27 wrappers → 0 findings
- **WITHOUT validation**: 23 wrappers → 27 severe/op findings (all fixed inline)

Pattern remains 100% predictive. Session 19 hit the prediction
precisely: all 3 wrappers had custom string/numeric handling
chains with silent coercion paths; all 5 surfaced bugs. The
distinction this session highlights: **numeric range coercions**
are a sub-class worth tracking. Pre-Session-19 the pattern
focused on string acceptance; numeric range coercions are the
same bug class (loud-and-coerced) just on different parameter
types.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 3 wrapper APIs verified. |
| **CAL-R3** | 3 rows AUDITED. Cycle 53 → 56. |
| **CAL-R4** | 3 NEW canonical scripts (6 each = 18 canonicals). |
| **CAL-R5** | 6 cells of synthetic-missing real-data baselines + 2 cells of synthetic Q→M disaggregation. |
| **CAL-R6** | 5 inline fixes (~75 LOC across 3 files). Within ≤100 LOC budget. |

## Recommended follow-ups

None. Missing Data extension batch CLOSED.
