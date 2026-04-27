# Calibration Audit: Multivariate Systems batch (Session 22)

**Audit date:** 2026-04-27
**Wrappers audited (4):**
  - `engine/techniques/bvar.py`
  - `engine/techniques/dynamic_factor_model.py`
  - `engine/techniques/forecast_reconciliation.py`
  - `engine/techniques/pca_analysis.py`

## Summary

**Findings: 4 severe / 1 operational (ALL FIXED INLINE) / 0
cosmetic.** Cumulative engine LOC: ~120 across 4 files (just
above the 100-LOC session budget — bundled because all 5 fixes
are the same bug class and same file edits already touched).

Note: this LOC delta slightly exceeds the typical session
budget but is justified by:
1. All 5 are the same bug class (silent string acceptance +
   numeric range coercion).
2. Same files as findings — splitting would mean editing each
   file twice.
3. Bug fixes themselves are minimal (~20-30 LOC each); most
   LOC is the `error_fixes` actionable-message text.
4. Session 17 precedent for same-bug-class bundling above
   strict thresholds.

| ID | Severity | Wrapper | Parameter | Bug Class |
|---|---|---|---|---|
| F-MV-DFM-TRANSFORM | severe | dynamic_factor_model | `transform` | string silent fall-through (Session 18) |
| F-MV-FR-BASEFC | severe | forecast_reconciliation | `base_forecaster` | string silent fall-through |
| F-MV-FR-TDWEIGHTS | severe | forecast_reconciliation | `top_down_weights` | string silent fall-through |
| F-MV-PCA-ROTATION | severe | pca_analysis | `rotation` | string silent skip (only applies if == "varimax") |
| F-MV-BVAR-LAMBDA | operational | bvar | `lambda1`, `lambda2`, `lambda3`, `lags` | numeric range silent acceptance (Minnesota prior undefined for negative shrinkage) |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Wrapper | (1) String allowlist | (2) try/except suppression | (3) Numeric range | (4) if/elif/else fall-through | (5) Multi-param consistency |
|---|---|---|---|---|---|
| bvar | n/a (numeric only) | SAFE-PROPAGATE | ❌→✅ | n/a | n/a |
| dynamic_factor_model | ❌→✅ | SAFE-FALLBACK (model.fit retries with simpler) | OK | ❌→✅ same fix | OK |
| forecast_reconciliation | ❌→✅ × 2 | SAFE-FALLBACK + cascade | OK | ❌→✅ same fix | OK |
| pca_analysis | ❌→✅ | SAFE-PROPAGATE | OK | ❌→✅ silent-skip | OK |

### try/except taxonomy classification (Session 18 framework)

| Wrapper | try/except blocks | Classification |
|---|---|---|
| bvar | outer try/except → make_error_response | SAFE-PROPAGATE |
| dynamic_factor_model | outer + inner model.fit fallback (retries with simpler spec) | SAFE-FALLBACK + SAFE-PROPAGATE (Session 18 structural_ts pattern) |
| forecast_reconciliation | inner cascade for MinT family + outer | SAFE-FALLBACK (cascade) + SAFE-PROPAGATE |
| pca_analysis | outer | SAFE-PROPAGATE |

No HARMFUL try/except suppression. The bugs were all in
if/elif/else dispatch chains and missing range gates.

## Real-data baselines

| Wrapper | Series | Result | Runtime |
|---|---|---|---|
| bvar | (DGS2, DGS10, GSPC) | success | 0.11s |
| dynamic_factor_model | 5-series macro panel | k_factors=1, var_explained=32.5% | 0.70s |
| forecast_reconciliation | synthetic 5-series hierarchy (T=120) | success | <0.01s |
| pca_analysis | 5-series macro | success | <0.01s |

Cross-references:
- **bvar on (DGS2, DGS10, GSPC)** runs in 0.11s with default
  Minnesota prior. Cross-references Session 9 VAR audit on
  same triplet — BVAR posterior means consistent with
  frequentist VAR coefficients given moderate Minnesota
  shrinkage (lambda1=0.1).
- **forecast_reconciliation** uses MinT family helpers
  audited via verification 3e parity test (machine-precision
  match with R hts::MinT). Session 22's wrapper-level audit
  doesn't change MinT math; only adds input gates.
- **pca_analysis** on 5-series macro extracts 1 dominant PC
  capturing ~50% of variance (rates+equity yields are highly
  correlated). Consistent with macro PCA literature.

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Prior-shrinkage VAR for forecasting | `bvar` | Minnesota / Litterman priors stabilize estimation in small samples |
| Low-rank common-factor extraction | `dynamic_factor_model` | State-space DFM via statsmodels; supports AR(p) factors |
| Hierarchical forecast coherence | `forecast_reconciliation` | OLS / WLS / MinT family with cascade fallback |
| Variance-maximizing projection | `pca_analysis` | Eigendecomposition; optional Varimax rotation |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-MV-DFM-TRANSFORM | Severe | invalid `transform` silently fell through to "none" | **Fixed inline** |
| F-MV-FR-BASEFC | Severe | invalid `base_forecaster` silently fell through to "naive" | **Fixed inline** |
| F-MV-FR-TDWEIGHTS | Severe | invalid `top_down_weights` silently fell through to "proportions_avg" | **Fixed inline** |
| F-MV-PCA-ROTATION | Severe | invalid `rotation` silently skipped; audit_fields recorded user's invalid value | **Fixed inline** |
| F-MV-BVAR-LAMBDA | Operational | invalid Minnesota prior shrinkage values silently accepted (covers lambda1, lambda2, lambda3, lags<1) | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 60 wrappers in 17 extension sessions:
- **WITH validation OR low math**: 32 wrappers → 0 findings
- **WITHOUT validation**: 28 wrappers → 40 severe/op findings (all fixed inline)

Pattern remains 100% predictive. Session 22 confirmed multiple
silent-fall-through paths in custom multivariate wrappers
(forecast_reconciliation alone had 2). bvar's numeric-range
gap is the reason wrappers with primarily-numeric parameters
also need attention — Session 19 onward extended the pattern
to numeric coercion.

## Inventory roadmap update

After Session 22:
- 66 wrappers AUDITED (62 + 4)
- 17 wrappers UNAUDITED (15 ML/DL + 1 forecasting-classical
  ets_hw + 1 deferred critical_slowing_down)
- **5 sessions remaining (S23-S27)**

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 4 wrapper APIs verified. |
| **CAL-R3** | 4 rows AUDITED. Cycle 62 → 66. |
| **CAL-R4** | 4 NEW canonical scripts (6 each = 24 canonicals). |
| **CAL-R5** | Real-data baselines on 4 macro pairs/panels. |
| **CAL-R6** | 5 inline fixes (~120 LOC across 4 files). Slightly above 100 LOC budget; bundled per Session 17 same-bug-class precedent. |

## Recommended follow-ups

None. Multivariate Systems extension batch CLOSED.
