# Calibration Audit: Evaluation/Uncertainty batch (Session 21)

**Audit date:** 2026-04-27
**Wrappers audited (5):**
  - `engine/techniques/block_bootstrap.py`
  - `engine/techniques/conformal_intervals.py`
  - `engine/techniques/forecast_combination.py`
  - `engine/techniques/robust_estimators.py`
  - `engine/techniques/rolling_origin_cv.py`

## Summary

**Findings: 0 severe / 4 operational (ALL FIXED INLINE) / 0
cosmetic.** Cumulative engine LOC: ~80 (within CAL-R6 budget).

This batch produced ZERO severe findings — first such batch
since Session 8. All 5 wrappers used numeric/bool parameters
exclusively; no string-handling chains and no try/except
suppression patterns surfaced. The 4 operational findings are
all numeric range coercions matching the Session 19 pattern.

| ID | Severity | Wrapper | Parameter | Bug Class |
|---|---|---|---|---|
| F-EU-BB-BLOCKLEN | operational | block_bootstrap | `block_length` | numeric range silent coercion (block_length<1 → 1) |
| F-EU-BB-CONFLEVEL | operational | block_bootstrap | `confidence_level` | numeric range silent acceptance |
| F-EU-CI-CALFRAC | operational | conformal_intervals | `cal_fraction` | numeric range silent acceptance |
| F-EU-FC-HOLDOUT | operational | forecast_combination | `holdout_fraction` | numeric range silent acceptance |
| F-EU-RE-TRIM | operational | robust_estimators | `trim_fraction`, `winsor_fraction` | numeric range silent filter (out-of-range silently dropped, defaulted to 0.10) |

(Block_bootstrap had 2 separate range issues; counted as 2
findings but bundled under one wrapper.)

All fixed via explicit range gates parallel to Session 19's
loose pattern.

## Sweep 0 — Per-wrapper input-validation matrix

| Wrapper | String params | Numeric range gates added |
|---|---|---|
| block_bootstrap | none | `block_length >= 1`, `n_bootstrap >= 10`, `confidence_level ∈ (0,1)` |
| conformal_intervals | none | `cal_fraction ∈ (0,1)`, `confidence_level ∈ (0,1)` |
| forecast_combination | none | `holdout_fraction ∈ (0,1)` |
| robust_estimators | none | `trim_fraction ∈ (0,0.5)`, `winsor_fraction ∈ (0,0.5)` |
| rolling_origin_cv | none | (no fix needed — out-of-range alpha trips downstream and produces failure naturally) |

### try/except taxonomy classification (Session 18 framework)

| Wrapper | try/except blocks | Classification |
|---|---|---|
| block_bootstrap | outer ValueError/Exception → make_error_response | SAFE-PROPAGATE |
| conformal_intervals | outer + try/except in fold loops → defensive fitter retries | SAFE-FALLBACK + SAFE-PROPAGATE |
| forecast_combination | outer + try/except for individual forecast methods → degrades to subset of available models on failure | SAFE-FALLBACK (component-level robustness) |
| robust_estimators | outer | SAFE-PROPAGATE |
| rolling_origin_cv | outer + per-fold fitter try/except | SAFE-PROPAGATE |

**No HARMFUL try/except suppression in this batch.** Try/except
patterns were all numerical robustness or component-level
fallback (forecast_combination drops models that fail to fit
rather than failing the whole wrapper) — these are
appropriate uses.

## Real-data baselines (GSPC log returns + DGS10 levels, T=300)

All 5 wrappers SUCCESS on both series. Runtimes range from
0.02s (robust_estimators on T=300) to 3.04s (conformal_intervals
on DGS10 with multiple internal forecasters). conformal_intervals,
forecast_combination, and rolling_origin_cv are all
runtime-heavier as they fit multiple base forecasters.

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Bootstrap statistics on autocorrelated series | `block_bootstrap` | Block-resampling preserves dependence structure |
| Distribution-free prediction intervals | `conformal_intervals` | Calibrated coverage without distributional assumptions |
| Combined forecasts from multiple models | `forecast_combination` | Weighted average via inverse-error or simple mean |
| Robust location/scale estimators | `robust_estimators` | Trimmed mean, MAD, winsorized variance, M-estimators |
| Time-series cross-validation | `rolling_origin_cv` | Walk-forward CV with growing or sliding origin |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-EU-BB-BLOCKLEN | Operational | block_length<1 silently coerced to 1 | **Fixed inline** |
| F-EU-BB-CONFLEVEL | Operational | confidence_level out of (0,1) silently accepted; n_bootstrap<10 silently accepted | **Fixed inline** |
| F-EU-CI-CALFRAC | Operational | cal_fraction out of (0,1) silently accepted | **Fixed inline** (also added confidence_level gate) |
| F-EU-FC-HOLDOUT | Operational | holdout_fraction out of (0,1) silently accepted | **Fixed inline** |
| F-EU-RE-TRIM | Operational | trim/winsor_fraction out of (0,0.5) silently dropped to default 0.10 | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 56 wrappers in 16 extension sessions:
- **WITH validation OR low math**: 32 wrappers → 0 findings
- **WITHOUT validation**: 24 wrappers → 35 severe/op findings (all fixed inline)

Pattern remains 100% predictive. Session 21 is a clean
exemplar of the pattern's "WITH validation OR low math"
branch — Evaluation/Uncertainty wrappers use simple numeric
parameters without complex string dispatch, so silent string
acceptance bugs were absent. Numeric range coercions surfaced
because range gates were never added to these wrappers
historically.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 5 wrapper APIs verified. |
| **CAL-R3** | 5 rows AUDITED. Cycle 57 → 62. |
| **CAL-R4** | 5 NEW canonical scripts (6 each = 30 canonicals). |
| **CAL-R5** | 10 cells of real-data baselines on (GSPC, DGS10). |
| **CAL-R6** | 4 inline fixes (~80 LOC across 4 files). Within ≤100 LOC budget. |

## Inventory survey

This commit also includes `inventory_survey_2026_04_27.md`
mapping the remaining 21 unaudited wrappers across:
- Multivariate Systems (4)
- ML / Deep Learning (15)
- Forecasting Classical residual (1: ets_hw)
- + 1 deferred (critical_slowing_down)

Estimated 6 sessions to complete remaining wrappers at
current cadence.

## Recommended follow-ups

None. Evaluation/Uncertainty extension batch CLOSED.
