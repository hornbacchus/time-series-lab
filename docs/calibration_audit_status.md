# Calibration Audit Status

Tracking artifact for the Calibration Audit Initiative (CAI).
Parallel to `docs/follow_up_check_coverage.md` (verification-
initiative coverage), this document tracks per-wrapper
calibration-audit status: parameter-sweep + real-data stress
+ adversarial-canonical findings.

See `plans/calibration_audit_phase1_2026_04_25.md` for the
Phase 1 design audit and methodology.

## CAI Phase 2 cycle: COMPLETE (2026-04-26)

All 5 selected wrapper audits shipped clean across 5 sessions
on 2026-04-25 / 2026-04-26:

| Session | Wrapper(s) | Commit | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| 1 | kalman_filter + kalman_smoother (co-audited) | 74ce1ae | 0 | 2 (fixed inline) | 0 |
| 2 | har_cj | 4b06eab | 0 | 1 (fixed inline) | 1 |
| 3 | evt_pot_gpd | 47848e0 | 0 | 0 | 1 |
| 4 | johansen_cointegration | 340a714 | 0 | 0 | 2 |
| 5 | stochastic_volatility | (this commit) | 0 | 0 | 2 |
| **Total** | **6 wrappers AUDITED** | — | **0** | **3 (all fixed)** | **6** |

**Zero severe findings on any wrapper.** All 3 operational
findings were Windows cp1252 console UnicodeEncodeError in
canonical validation scripts (audit-infrastructure issues, not
wrapper bugs); fixed inline within CAL-R6 thresholds. The 6
cosmetic findings document well-known methodological properties
(EVT small-N MLE bias, Johansen det_order sensitivity, KSC
Gibbs autocorrelation, etc.) — not wrapper bugs but
user-facing calibration guidance worth preserving.

CAI Phase 2 demonstrated that the verification-initiative-
validated wrappers are **operationally sound at default
parameters** across realistic synthetic + real-data sweep
matrices, complementing the verification initiative's math-
correctness focus. Future CAI cycles may extend coverage to
the 76 currently-UNAUDITED wrappers if calibration concerns
arise from production usage.

## Status legend

- **AUDITED** — calibration audit complete; findings doc
  exists at `docs/calibration_audit/<wrapper>_findings_*.md`
- **PENDING** — selected for Phase 2 audit (one of the 5)
  but not yet executed
- **DEFERRED** — explicitly out of scope; reason logged
- **UNAUDITED** — not selected for Phase 2; no audit planned
  in this initiative cycle

## Counts

- Total wrappers: 83
- AUDITED: 6 (kalman_filter + kalman_smoother — co-audited Session 1, 2026-04-25; har_cj — Session 2, 2026-04-26; evt_pot_gpd — Session 3, 2026-04-26; johansen_cointegration — Session 4, 2026-04-26; stochastic_volatility — Session 5, 2026-04-26)
- PENDING: 0 (CAI Phase 2 cycle COMPLETE)
  (Note: 6 selected wrapper IDs map to 5 logical audit sessions; kalman_filter + kalman_smoother were co-audited in Session 1.)
- DEFERRED: 1 (critical_slowing_down — too new, shipped 2026-04-25)
- UNAUDITED: 76

## Per-wrapper status

### Causality / Relationships / Lead-Lag

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| cross_correlation_lag | UNAUDITED | — | — | — | — |
| dtw_alignment_lag | UNAUDITED | — | — | — | — |
| gcc_phat_delay | UNAUDITED | — | — | — | — |
| granger_causality | UNAUDITED | — | — | — | — |
| prewhitened_ccf_lag | UNAUDITED | — | — | — | — |
| rolling_ccf_lag | UNAUDITED | — | — | — | — |

### Change Points / Anomalies / Interventions

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| bocpd | UNAUDITED | — | — | — | — |
| cusum_page_hinkley | UNAUDITED | — | — | — | — |
| intervention_analysis | UNAUDITED | — | — | — | — |
| pelt_change_points | UNAUDITED | — | — | — | — |
| stl_esd_anomaly | UNAUDITED | — | — | — | — |

### Decomposition & Seasonal Adjustment

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| classical_decompose | UNAUDITED | — | — | — | — |
| mstl_decompose | UNAUDITED | — | — | — | — |
| stl_decompose | UNAUDITED | — | — | — | — |
| x13_seasonal_adjust | UNAUDITED | — | — | — | — |

### Evaluation / Uncertainty

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| block_bootstrap | UNAUDITED | — | — | — | — |
| conformal_intervals | UNAUDITED | — | — | — | — |
| forecast_combination | UNAUDITED | — | — | — | — |
| robust_estimators | UNAUDITED | — | — | — | — |
| rolling_origin_cv | UNAUDITED | — | — | — | — |

### Forecasting (Classical)

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| arima | UNAUDITED | — | — | — | — |
| arimax_sarimax | UNAUDITED | — | — | — | — |
| auto_arima | UNAUDITED | — | — | — | — |
| ets_hw | UNAUDITED | — | — | — | — |
| intermittent_demand | UNAUDITED | — | — | — | — |
| sarima | UNAUDITED | — | — | — | — |
| theta_forecast | UNAUDITED | — | — | — | — |
| transfer_function | UNAUDITED | — | — | — | — |

### Frequency Domain / Signal

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| emd_hht | UNAUDITED | — | — | — | — |
| fft_spectrum | UNAUDITED | — | — | — | — |
| lomb_scargle | UNAUDITED | — | — | — | — |
| periodogram_spectral_density | UNAUDITED | — | — | — | — |
| ssa | UNAUDITED | — | — | — | — |
| wavelet_coherence_phase_lag | UNAUDITED | — | — | — | — |
| wavelet_transform | UNAUDITED | — | — | — | — |

### ML / Deep Learning

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| autoencoder_anomaly | UNAUDITED | — | — | — | — |
| echo_state_network | UNAUDITED | — | — | — | — |
| gaussian_process_forecast | UNAUDITED | — | — | — | — |
| gradient_boosting_forecast | UNAUDITED | — | — | — | — |
| lightgbm_forecast | UNAUDITED | — | — | — | — |
| lstm_gru_forecast | UNAUDITED | — | — | — | — |
| nbeats_forecast | UNAUDITED | — | — | — | — |
| nhits_forecast | UNAUDITED | — | — | — | — |
| prophet_forecast | UNAUDITED | — | — | — | — |
| quantile_regression | UNAUDITED | — | — | — | — |
| random_forest_forecast | UNAUDITED | — | — | — | — |
| svr_forecast | UNAUDITED | — | — | — | — |
| tcn_forecast | UNAUDITED | — | — | — | — |
| transformer_forecast | UNAUDITED | — | — | — | — |
| xgboost_forecast | UNAUDITED | — | — | — | — |

### Missing Data / Temporal Disaggregation

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| denton_chowlin_disaggregation | UNAUDITED | — | — | — | — |
| kalman_imputation | UNAUDITED | — | — | — | — |
| loess_interpolation | UNAUDITED | — | — | — | — |

### Multivariate Systems

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| bvar | UNAUDITED | — | — | — | — |
| dynamic_factor_model | UNAUDITED | — | — | — | — |
| forecast_reconciliation | UNAUDITED | — | — | — | — |
| johansen_cointegration | AUDITED | [johansen_findings_2026_04_26.md](calibration_audit/johansen_findings_2026_04_26.md) | 0 | 0 | 2 |
| pca_analysis | UNAUDITED | — | — | — | — |
| var | UNAUDITED | — | — | — | — |
| vecm | UNAUDITED | — | — | — | — |

### Regimes / Nonlinear

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| critical_slowing_down | DEFERRED | — | — | — | — |
| hmm | UNAUDITED | — | — | — | — |
| markov_switching | UNAUDITED | — | — | — | — |
| nar_narx | UNAUDITED | — | — | — | — |
| star | UNAUDITED | — | — | — | — |
| tar_setar | UNAUDITED | — | — | — | — |

### State Space / Filtering

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| kalman_filter | AUDITED | [kalman_findings_2026_04_25.md](calibration_audit/kalman_findings_2026_04_25.md) | 0 | 2 (both fixed inline) | 0 |
| kalman_smoother | AUDITED | [kalman_findings_2026_04_25.md](calibration_audit/kalman_findings_2026_04_25.md) | 0 | 2 (shared with kalman_filter) | 0 |
| local_level | UNAUDITED | — | — | — | — |
| local_linear_trend | UNAUDITED | — | — | — | — |
| particle_filter | UNAUDITED | — | — | — | — |
| structural_ts | UNAUDITED | — | — | — | — |

### Stationarity / Tests

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| adf_test | UNAUDITED | — | — | — | — |
| kpss_test | UNAUDITED | — | — | — | — |
| pp_test | UNAUDITED | — | — | — | — |

### Volatility / Risk / Tails

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| caviar_quantile_dynamics | UNAUDITED | — | — | — | — |
| egarch | UNAUDITED | — | — | — | — |
| evt_pot_gpd | AUDITED | [evt_pot_gpd_findings_2026_04_26.md](calibration_audit/evt_pot_gpd_findings_2026_04_26.md) | 0 | 0 | 1 |
| garch | UNAUDITED | — | — | — | — |
| gjr_garch | UNAUDITED | — | — | — | — |
| har_cj | AUDITED | [har_cj_findings_2026_04_26.md](calibration_audit/har_cj_findings_2026_04_26.md) | 0 | 1 (fixed inline) | 1 |
| har_rv | UNAUDITED | — | — | — | — |
| stochastic_volatility | AUDITED | [stochastic_volatility_findings_2026_04_26.md](calibration_audit/stochastic_volatility_findings_2026_04_26.md) | 0 | 0 | 2 |

## Notes

- Phase 2 ships ~5 commits, one per audit session, per CAI
  Phase 1 §5.1 sequencing.
- `critical_slowing_down` deferred because it shipped on
  2026-04-25 (commit `94742fe`); too new for the calibration
  audit cycle. Will be candidate for next CAI cycle.
- The 77 UNAUDITED wrappers are documented for awareness;
  not in this initiative's scope. Future calibration cycles
  may extend coverage.
