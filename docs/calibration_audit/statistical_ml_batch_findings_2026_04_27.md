# Calibration Audit: Statistical ML batch (Session 26)

**Audit date:** 2026-04-27
**Wrappers audited (4):**
  - `engine/techniques/gaussian_process_forecast.py`
  - `engine/techniques/prophet_forecast.py`
  - `engine/techniques/quantile_regression_model.py`
  - `engine/techniques/svr_forecast.py`

## Summary

**Findings: 2 severe / 6 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~95 across 4 files
(within raised 150-LOC budget for multi-wrapper batches).

| ID | Severity | Wrapper | Bug Class |
|---|---|---|---|
| F-ML-GP-KERNEL | severe | gaussian_process_forecast | string fall-through `kernel` |
| F-ML-SVR-KERNEL | severe | svr_forecast | loud-and-coerced `kernel` |
| F-ML-GP-HORIZON | op | gaussian_process_forecast | numeric range `horizon` |
| F-ML-GP-CONFLEVEL | op | gaussian_process_forecast | numeric range `confidence_level` |
| F-ML-P-HORIZON | op | prophet_forecast | numeric range `horizon` |
| F-ML-QR-HORIZON | op | quantile_regression_model | numeric range `horizon` |
| F-ML-QR-NLAGS | op | quantile_regression_model | numeric range `n_lags` |
| F-ML-SVR-HORIZON | op | svr_forecast | numeric range `horizon` |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Wrapper | (1) String | (2) try/except | (3) Numeric | (4) Fall-through | (5) Multi-param |
|---|---|---|---|---|---|
| gaussian_process_forecast | ❌→✅ | SAFE | ❌→✅ × 2 | ❌→✅ same fix | OK |
| prophet_forecast | n/a (preset-driven) | SAFE-FALLBACK (seasonal naive) | ❌→✅ | n/a | OK |
| quantile_regression_model | n/a | SAFE | ❌→✅ × 2 | n/a | OK |
| svr_forecast | ❌→✅ | SAFE | ❌→✅ | ❌→✅ same fix | OK |

### try/except taxonomy

| Wrapper | Pattern | Classification |
|---|---|---|
| gaussian_process_forecast | outer | SAFE-PROPAGATE |
| prophet_forecast | outer + seasonal_naive fallback when prophet unavailable | SAFE-PROPAGATE + SAFE-FALLBACK |
| quantile_regression_model | outer | SAFE-PROPAGATE |
| svr_forecast | outer | SAFE-PROPAGATE |

No HARMFUL try/except suppression.

### Prophet multi-parameter consistency notes

Prophet's user-facing parameter surface in this wrapper is
much smaller than the underlying Prophet API: only `horizon`,
`yearly_seasonality`, `weekly_seasonality`, and
`changepoint_prior_scale` are exposed. Many Prophet
multi-parameter consistency surfaces (logistic growth + cap
column, multiplicative seasonality + non-positive data,
holidays specification) are NOT exposed at the TSL layer —
preset-driven defaults handle them. So Prophet did NOT
surface the high-finding-density that the prompt anticipated;
the wrapper-layer smoothing is effective at hiding
multi-parameter consistency violations from users.

## Real-data baselines (DGS10 + GSPC log returns, T=300)

All 4 wrappers SUCCESS on both series:

| Wrapper | DGS10 | GSPC_logret |
|---|---|---|
| gaussian_process_forecast | 0.26s | 0.35s |
| prophet_forecast | 0.32s | 0.30s |
| quantile_regression_model | 1.13s | 1.26s |
| svr_forecast | 0.04s | 0.04s |

quantile_regression_model is slowest because it fits
`n_estimators` × `len(quantiles)` separate gradient boosting
models. svr_forecast is fastest on small data.

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Uncertainty quantification with smooth kernels | `gaussian_process_forecast` | Posterior credible bands; flexible kernels |
| Business forecasting with seasonality + holidays | `prophet_forecast` | Robust to outliers; trained on industry data |
| Distributional forecasting | `quantile_regression_model` | Direct quantile outputs at multiple levels |
| Small-sample nonlinear regression | `svr_forecast` | Kernel methods generalize well in low-data |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-ML-GP-KERNEL | Severe | invalid kernel silently fell through to RBF | **Fixed inline** |
| F-ML-SVR-KERNEL | Severe | invalid kernel loud-and-coerced to rbf | **Fixed inline** |
| F-ML-GP-HORIZON | Op | horizon<1 silently coerced | **Fixed inline** |
| F-ML-GP-CONFLEVEL | Op | confidence_level out of (0,1) silently accepted | **Fixed inline** |
| F-ML-P-HORIZON | Op | horizon<1 silently coerced (prophet) | **Fixed inline** |
| F-ML-QR-HORIZON | Op | horizon<1 silently coerced (qr) | **Fixed inline** |
| F-ML-QR-NLAGS | Op | n_lags<1 silently accepted | **Fixed inline** |
| F-ML-SVR-HORIZON | Op | horizon<1 silently coerced (svr) | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 75 wrappers in 21 extension sessions:
- **WITH validation OR low math**: 36 wrappers → 0 findings
- **WITHOUT validation**: 39 wrappers → 70 severe/op findings (all fixed inline)

Pattern remains 100% predictive.

## Inventory roadmap update

After Session 26:
- 81 wrappers AUDITED (77 + 4)
- 2 wrappers UNAUDITED (1 forecasting-classical residual `ets_hw` + 1 deferred `critical_slowing_down`)
- **1 session remaining (S27: ets_hw solo)**

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 4 wrapper APIs verified. |
| **CAL-R3** | 4 rows AUDITED. Cycle 77 → 81. |
| **CAL-R4** | 4 NEW canonical scripts (6 each = 24 canonicals). |
| **CAL-R5** | 8 cells real-data baselines on (DGS10, GSPC). |
| **CAL-R6** | 8 inline fixes (~95 LOC across 4 files). Within raised 150 LOC budget. |

## Recommended follow-ups

None. Statistical ML extension batch CLOSED.
