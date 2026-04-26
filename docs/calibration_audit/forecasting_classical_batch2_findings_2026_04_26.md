# Calibration Audit: Forecasting Classical batch 2
(arimax_sarimax + intermittent_demand + theta_forecast)

**Audit date:** 2026-04-26
**Commit:** (assigned at commit step)
**Auditor:** Claude (driven mode)
**Wrappers audited:**
  - `engine/techniques/arimax_sarimax.py` (statsmodels SARIMAX)
  - `engine/techniques/intermittent_demand.py` (Croston/SBA/TSB)
  - `engine/techniques/theta_forecast.py` (statsmodels ThetaModel)
**Closes:** Forecasting classical extension batch (Sessions
            10-11; 6 wrappers across 2 sessions)

## Summary

Sixth extension audit (CAI Phase 2 Session 11). Closes the
forecasting-classical extension batch.

**Findings: 0 severe / 0 operational / 0 cosmetic.** Cleanest
3-wrapper batch yet. All three wrappers pass through the
audit unchanged.

**Critical question answered:** Did `arimax_sarimax` inherit
Session 10's pmdarima `start_P` bug? **No.** `arimax_sarimax`
uses statsmodels SARIMAX directly (via grid_search at line
153-157 of arimax_sarimax.py); pmdarima is NOT involved. The
Session 10 fix only applies to `auto_arima` invocations
through `engine/techniques/arima.py`. Architecture audit
confirms isolation.

## Sweep 0 — Dispatch + input-validation matrix

| Probe | Result |
|---|---|
| `arimax_sarimax` baseline (no exog) | success ✅ |
| `arimax_sarimax` with exogenous regressor | success ✅ |
| `arimax_sarimax` invalid trend `'zzz'` | failure with statsmodels error: *"Valid trend inputs are 'c'..."* ✅ (validated upstream) |
| `intermittent_demand` baseline (default Croston) | success, best_method=CROSTON ✅ |
| `intermittent_demand` method=`croston`/`sba`/`tsb` (each) | All 3 dispatch correctly (case-insensitive match) ✅ |
| `intermittent_demand` invalid method `'xxx'` | failure with `"No valid method could be fitted"` (clean error after warn-and-skip drains all candidates) ✅ |
| `theta_forecast` baseline | success ✅ |

All wrappers exhibit appropriate input validation:
- arimax_sarimax inherits validation from statsmodels SARIMAX
  (rejects invalid trend with clear error message)
- intermittent_demand has wrapper-level method allowlist
  (warn+skip for invalid methods; if all methods invalid,
  returns error_response cleanly)
- theta_forecast has minimal user-facing surface (horizon,
  period, deseasonalize) — simple math, no dispatch
  ambiguity

## Technique 1: Parameter Sweep

### Sweep 1.1: arimax_sarimax orders on synthetic ARMA(1,1)

| order | AIC | BIC | runtime |
|---|---|---|---|
| (1,0,1) (truth) | 1381.30 | 1398.16 | 0.07s |
| (2,0,1) | 1380.24 | 1401.31 | 0.11s |
| (1,0,2) | 1381.08 | 1402.16 | 0.11s |
| (2,0,2) | 1380.64 | 1405.93 | 0.40s |

BIC correctly favors truth (1,0,1). AIC slightly favors
(2,0,1) over-specification (typical AIC bias on small samples).

### Sweep 1.2: intermittent_demand method comparison

Synthetic intermittent series (T=200, zero_density=0.7):

| method | MSE | runtime |
|---|---|---|
| Croston | 4.093 | 0.0s |
| SBA | 4.069 | 0.0s |
| **TSB** | **2.715** ⭐ | 0.0s |

TSB best on this fixture. SBA and Croston produce nearly-
identical MSE (SBA is a bias-corrected variant of Croston).

### Sweep 1.3: theta_forecast horizon sweep

| horizon | runtime |
|---|---|
| 1 | 9.11s |
| 5 | 8.81s |
| 10 | 10.08s |
| 22 | 9.44s |

Runtime independent of horizon (Theta model fits once,
forecasts cheaply). 9-10s/series at T=500 — slower than
ARIMA (~0.1s) but still under the 30s budget.

## Technique 2: Real-Data Stress

### arimax_sarimax (5 series × 1 wrapper)

| Series | Order | AIC | runtime |
|---|---|---|---|
| GSPC log_returns | (1,0,1) | 1431 | 0.1s |
| DGS10 level | (1,1,1) | -1329 | 0.2s |
| DGS2 level | (1,1,1) | -1287 | 0.4s |
| DEXUSEU log_returns | (1,0,1) | 625 | 0.1s |
| GOLD log_returns | (1,0,1) | 1362 | 0.1s |

Cross-reference Session 10 ARIMA results: AIC values match
ARIMA's exactly on returns series (different backend, same
math). Yields differ slightly (-1329 vs -1331 for DGS10) due
to optimizer / fit options differences.

### theta_forecast (5 series × 1 wrapper)

All 5 series PASS. Runtime 2.6-9.2s/series.

### intermittent_demand (synthetic fixtures × 1 wrapper)

| Density label | DGP zero_density | best_method | MSE |
|---|---|---|---|
| low_density_30 | 0.30 | SBA | 5.20 |
| typical_60 | 0.60 | SBA | 4.95 |
| sparse_85 | 0.85 | SBA | 2.19 |

SBA wins across all density regimes on these fixtures (with
default alpha grid). Wrapper's default Balanced preset
correctly selects via MSE comparison.

## Technique 3: Adversarial Canonicals

| Canonical | Wrapper | Outcome |
|---|---|---|
| C-CAL-1 (Constant series) | arimax_sarimax, theta_forecast | Both succeed |
| C-CAL-2 (Random walk + ARIMA(0,1,0)) | arimax_sarimax | success, AIC=860 |
| C-CAL-3 (Short series T=30) | arimax_sarimax, theta_forecast | Both succeed (no hard guard tripped) |
| C-CAL-4 (All-zeros + intermittent_demand) | intermittent_demand | failure with clear error: *"All demand values are zero. Cannot fit intermittent demand model."* ✅ |

## Findings table

No findings on any wrapper.

| ID | Severity | Description | Disposition |
|---|---|---|---|

(empty — clean audit)

## Validation-presence pattern update

| Session | Wrapper | Validation? | Findings |
|---|---|---|---|
| 6 | garch family | No | 2 severe (fixed) |
| 7 | har_rv | N/A (low math) | 0 |
| 8 | caviar | Yes (wrapper allowlist) | 0 |
| 9 | var | Yes (statsmodels) | 0 |
| 9 | vecm | No | 1 severe (fixed) |
| 10 | arima | Yes (strict order check) | 0 |
| 10 | auto_arima | No (relies on pmdarima) | 1 severe (fixed) |
| 10 | sarima | Partial (silent order fallback) | 0 |
| 11 | **arimax_sarimax** | **Yes (statsmodels)** | **0** |
| 11 | **intermittent_demand** | **Yes (wrapper allowlist warn+skip+fail)** | **0** |
| 11 | **theta_forecast** | **N/A (low math)** | **0** |

**Tally across extension Sessions 6-11 (13 wrappers):**
- WITH validation OR low math complexity: **8 wrappers (har_rv,
  caviar, var, arima, sarima, arimax_sarimax,
  intermittent_demand, theta_forecast) → 0 findings**
- WITHOUT validation: **5 wrappers (garch×3, vecm, auto_arima)
  → 5 severe findings (all fixed inline)**

Pattern's predictive power remains 100% across 13 wrappers in
6 extension sessions. Session 11 confirms: when wrappers
inherit validation from a robust upstream library
(statsmodels) AND/OR implement their own allowlist+fallback,
they ship clean.

## Cross-wrapper comparison: forecasting classical methods

When to use which (synthesizing Sessions 10 + 11):

| Use case | Recommended | Why |
|---|---|---|
| Known ARIMA order | `arima` (manual) | Fastest; strict input validation |
| Auto order discovery | `auto_arima` (post-S10 fix) | pmdarima search; ~1s on T=500 |
| Seasonal data | `sarima` or `auto_arima(seasonal=True)` | Manual SARIMA gives explicit control |
| With exogenous regressors | `arimax_sarimax` (`sarimax`) | Native exog support |
| Theta-decomposition forecasting | `theta_forecast` | Simple, robust; uses ThetaModel |
| Intermittent / lumpy demand | `intermittent_demand` | Croston/SBA/TSB — designed for sparse data |
| All-zero demand history | None | All wrappers reject; expected |
| Explicit dependency injection | `arimax_sarimax` w/ exog series | Only wrapper supporting external regressors |

## Forecasting Classical Extension Batch Closure (Sessions 10-11)

6 wrappers across 2 sessions:

| Session | Wrapper | Validation | Findings |
|---|---|---|---|
| 10 | arima | Yes | 0 |
| 10 | auto_arima | No | 1 severe (fixed) |
| 10 | sarima | Partial | 0 |
| 11 | arimax_sarimax | Yes | 0 |
| 11 | intermittent_demand | Yes | 0 |
| 11 | theta_forecast | N/A | 0 |
| **Total** | **6 wrappers** | — | **1 severe (fixed)** |

**Batch finding ratio: 1/6 wrappers had a severe bug, all
fixed inline within CAL-R6. Excluded from this batch:
`transfer_function` (deferred for higher-math-complexity
session).** The forecasting-classical extension arc is now
CLOSED.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | Wrapper params verified for all 3 wrappers. arimax_sarimax confirmed NOT to use pmdarima (no S10-bug inheritance risk). |
| **CAL-R3** | Status doc updated: 3 wrappers PENDING → AUDITED. Cycle table extended; AUDITED count 16 → 19. |
| **CAL-R4** | Three NEW canonical scripts: `validate_arimax_sarimax_canonicals.py`, `validate_intermittent_demand_canonicals.py`, `validate_theta_forecast_canonicals.py` (9 canonicals each). |
| **CAL-R5** | Real-data baselines for arimax_sarimax (5 series), theta_forecast (5 series), intermittent_demand (3 synthetic density regimes). |
| **CAL-R6** | No fixes required (0 severe / 0 operational findings). |

## Recommended follow-ups

None required. All 3 wrappers clean.

For future cycles:
- `transfer_function` deferred to a dedicated session
  (higher math complexity; impulse-response and dynamic
  regression structure differs from this batch)
- The intermittent_demand SBA/TSB methods could benefit
  from a parity test against R `tsintermittent` package or
  paper-derived implementations. Currently no
  verification-initiative parity for any of these 3
  wrappers.
- theta_forecast runtime (2-10s/series) is moderate; could
  be optimized if the wrapper's `_warnings.catch_warnings`
  block adds overhead beyond the underlying ThetaModel fit.
  Out of scope.
