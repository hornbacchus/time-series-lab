# CAI Phase 2 — Inventory Survey of Remaining Unaudited Wrappers

**Survey date:** 2026-04-27 (CAI Session 21)
**Purpose:** Roadmap for Sessions 22+ batching decisions

## Snapshot

- **Total wrappers (file-level):** 83
- **AUDITED (post-Session 21):** 62 (Sessions 1-21)
- **DEFERRED:** 1 (critical_slowing_down)
- **REMAINING UNAUDITED:** 21

## Roadmap by category

| Category | Audited / Total (file-level) | Status | Remaining wrappers |
|---|---|---|---|
| State Space / Filtering | 6/6 | CLOSED | (kalman_filter, kalman_smoother, local_level, local_linear_trend, structural_ts, particle_filter) |
| Stationarity Tests | 3/3 | CLOSED | none |
| Decomposition | 4/4 | CLOSED | none |
| Change Points / Anomalies | 5/5 | CLOSED | none |
| Causality / Lead-Lag | 6/6 | CLOSED | none |
| Frequency Domain | 7/7 | CLOSED | none |
| Markov / Regime | 5/6 | EXTENSION-CLOSED | critical_slowing_down (DEFERRED) |
| Forecasting Classical | 7/8 | CLOSED | (ets_hw remains; tbats_forecast already in ML/DL) |
| Volatility / Risk / Tails | 8/8 | CLOSED | none |
| Missing Data | 3/3 | CLOSED | none |
| Evaluation / Uncertainty | 5/5 | **CLOSED (Session 21)** | none |
| **ML / Deep Learning** | 0/15 | **OPEN** | autoencoder_anomaly, echo_state_network, gaussian_process_forecast, gradient_boosting_forecast, lightgbm_forecast, lstm_gru_forecast, nbeats_forecast, nhits_forecast, prophet_forecast, quantile_regression_model, random_forest_forecast, svr_forecast, tcn_forecast, transformer_forecast, xgboost_forecast |
| **Multivariate Systems** | 3/7 | **OPEN** | bvar, dynamic_factor_model, forecast_reconciliation, pca_analysis (johansen, var, vecm already audited) |
| **Forecasting Classical (residual)** | — | OPEN | ets_hw |

## Recommended sequence for Sessions 22+

Given the remaining 21 wrappers, recommended sequencing:

### Session 22 — Multivariate Systems (4 wrappers)
- bvar (Bayesian VAR; likely shares VAR machinery from Session 9)
- dynamic_factor_model
- forecast_reconciliation (already touched in B1 cleanup but never CAI-audited)
- pca_analysis

Likely batch yield: 1-3 findings per wrapper based on Sessions 12/14 pattern
for custom statistical wrappers. Total expected: 5-10 findings.

### Sessions 23-27 — ML / Deep Learning (15 wrappers)

Suggested split into 3-4 sub-batches:

- **Session 23:** Tree-based forecasters (4 wrappers)
  - gradient_boosting_forecast, lightgbm_forecast, random_forest_forecast,
    xgboost_forecast
- **Session 24:** Neural sequence models (4 wrappers)
  - lstm_gru_forecast, tcn_forecast, transformer_forecast, nbeats_forecast
- **Session 25:** Specialized neural models (3 wrappers)
  - nhits_forecast, autoencoder_anomaly, echo_state_network
- **Session 26:** Statistical ML (4 wrappers)
  - gaussian_process_forecast, prophet_forecast, quantile_regression_model,
    svr_forecast

### Session 27 — ets_hw (solo)
Single forecasting-classical wrapper; small audit scope.

### Total estimated remaining sessions
**6 sessions** to complete remaining 21 wrappers at current cadence (~3-4
wrappers per batch; ML/DL natural sub-grouping by family).

## Wrappers that don't fit existing categories

None — all 21 remaining wrappers fit cleanly into existing CAI taxonomy.

## Notes on tbats_forecast

`tbats_forecast` was tentatively listed under Forecasting Classical but
is actually ML/DL-adjacent (uses pmdarima/tbats package). Recommendation:
audit alongside neural models in Session 24 or include in Session 26
(Statistical ML) as a separate forecasting-augmentation tool. Keeping it
under ML/DL for inventory purposes.

## CAI Phase 2 progress as of Session 21

| Metric | Value |
|---|---|
| Sessions completed | 21 |
| Wrappers audited (file-level) | 62 |
| Wrappers remaining (file-level) | 21 |
| Severe findings (cumulative) | 24 (all fixed) |
| Operational findings (cumulative) | 13 (all fixed) |
| Cosmetic findings (cumulative) | 6 |
| Validation-presence pattern accuracy | 100% across 56 extension wrappers |
| Engine LOC delta (cumulative) | ~600 across all sessions |
| Estimated sessions remaining | 6 |
