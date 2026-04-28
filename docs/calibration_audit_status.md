# Calibration Audit Status

Tracking artifact for the Calibration Audit Initiative (CAI).
Parallel to `docs/follow_up_check_coverage.md` (verification-
initiative coverage), this document tracks per-wrapper
calibration-audit status: parameter-sweep + real-data stress
+ adversarial-canonical findings.

See `plans/calibration_audit_phase1_2026_04_25.md` for the
Phase 1 design audit and methodology.

> **Engineering reference (post-Session 29 consolidation):**
> CAI's institutional knowledge is now consolidated into three
> engineering documents under `docs/engineering/`:
>
> - **[Wrapper Development Standard](engineering/wrapper_development_standard.md)** —
>   directive ("must"); binding for new wrapper PRs.
> - **[Validation Patterns Reference](engineering/validation_patterns_reference.md)** —
>   diagnostic tests + fix patterns + per-finding cross-reference.
> - **[CAI Phase 2 Empirical Findings](engineering/cai_empirical_findings.md)** —
>   descriptive synthesis of "what we learned" across 28 sessions.
>
> Per-session findings docs under `docs/calibration_audit/`
> remain as the audit trail for future re-investigation.
> The three engineering docs are the primary reference for
> day-to-day wrapper development.

## CAI Phase 2: 28 sessions COMPLETE — TRUE CYCLE CLOSURE 2026-04-28

**FINAL STATE:** 83 / 83 wrappers AUDITED (100%); 0 deferred.
40 severe + 42 operational findings (ALL FIXED INLINE) +
6 cosmetic across 5 failure modes:
1. String acceptance via if/elif/else default
2. HARMFUL try/except suppression
3. Numeric range silent coercion
4. String-handling chain fall-through
5. Multi-parameter consistency violation

Validation-presence pattern: 100% predictive across 76
extension wrappers. See
`docs/calibration_audit/ets_hw_findings_2026_04_27.md`
for full cycle closure summary.

The 5-session core cycle closed cleanly on 2026-04-26
(Session 5 commit `a2464ac`). Session 6 begins the extension
cycle by batching the GARCH family (3 catalog technique IDs
that route to a single `garch_model.py` wrapper).

| Session | Wrapper(s) | Commit | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| 1 | kalman_filter + kalman_smoother (co-audited) | 74ce1ae | 0 | 2 (fixed inline) | 0 |
| 2 | har_cj | 4b06eab | 0 | 1 (fixed inline) | 1 |
| 3 | evt_pot_gpd | 47848e0 | 0 | 0 | 1 |
| 4 | johansen_cointegration | 340a714 | 0 | 0 | 2 |
| 5 | stochastic_volatility | a2464ac | 0 | 0 | 2 |
| 6 | garch + gjr_garch + egarch (batch; first extension) | fcc73b3 | 2 (both fixed inline) | 0 | 0 |
| 7 | har_rv (second extension) | d32dd75 | 0 | 0 | 0 |
| 8 | caviar_quantile_dynamics (closes vol/risk batch) | 757a354 | 0 | 0 | 0 |
| 9 | var + vecm (multivariate batch) | a2b7872 | 1 (fixed inline) | 0 | 0 |
| 10 | arima + auto_arima + sarima (forecasting classical batch) | 696181a | 1 (fixed inline) | 0 | 0 |
| 11 | arimax_sarimax + intermittent_demand + theta_forecast (closes forecasting classical) | 8743512 | 0 | 0 | 0 |
| 12 | hmm + markov_switching + tar_setar + star + nar_narx (Markov/regime batch) | a21bcd0 | 1 (fixed inline) | 0 | 0 |
| 13 | fft + periodogram + lomb_scargle + wavelet_transform + wavelet_coherence + emd_hht + ssa (Frequency Domain batch) | 1090ac5 | 3 (all fixed inline) | 0 | 0 |
| 14 | granger_causality + cross_correlation_lag + gcc_phat_delay + prewhitened_ccf_lag + rolling_ccf_lag + dtw_alignment_lag (Causality/Lead-Lag batch) | ff0aefa | 2 (both fixed inline) | 0 | 0 |
| 15 | bocpd + cusum_page_hinkley + intervention_analysis + pelt_change_points + stl_esd_anomaly (Change Points/Anomalies batch) | 7711045 | 3 (all fixed inline) | 0 | 0 |
| 16 | stl_decompose + mstl_decompose + classical_decompose + x13_seasonal_adjust (Decomposition batch) | c24de96 | 2 (both fixed inline) | 0 | 0 |
| 17 | adf_test + kpss_test + pp_test (Stationarity Tests batch) | ff36cef | 5 (all fixed inline) | 0 | 0 |
| 18 | local_level + local_linear_trend + structural_ts + particle_filter (State Space batch) | f2ebd94 | 1 (fixed inline) | 0 | 0 |
| 19 | denton_chowlin_disaggregation + kalman_imputation + loess_interpolation (Missing Data batch) | 3c9c56e | 2 (both fixed inline) | 3 (all fixed inline) | 0 |
| 20 | transfer_function (solo; closes S11 deferred items) | 72cb4a1 | 1 (fixed inline) | 3 (all fixed inline) | 0 |
| 21 | block_bootstrap + conformal_intervals + forecast_combination + robust_estimators + rolling_origin_cv (Evaluation/Uncertainty batch) + INVENTORY SURVEY | 3ea6114 | 0 | 4 (all fixed inline) | 0 |
| 22 | bvar + dynamic_factor_model + forecast_reconciliation + pca_analysis (Multivariate Systems batch) | 854c832 | 4 (all fixed inline) | 1 (fixed inline) | 0 |
| 23 | gradient_boosting_forecast + lightgbm_forecast + random_forest_forecast + xgboost_forecast (Tree Forecasters batch) | d614dda | 0 | 9 (all fixed inline) | 0 |
| 24 | lstm_gru_forecast + tcn_forecast + transformer_forecast + nbeats_forecast (Neural Sequence batch) | 9d03923 | 2 (both fixed inline) | 4 (all fixed inline) | 0 |
| 25 | nhits_forecast + autoencoder_anomaly + echo_state_network (Specialized Neural batch) | 002c86c | 2 (both fixed inline) | 5 (all fixed inline) | 0 |
| 26 | gaussian_process_forecast + prophet_forecast + quantile_regression_model + svr_forecast (Statistical ML batch) | 9cac0f7 | 2 (both fixed inline) | 6 (all fixed inline) | 0 |
| 27 | ets_hw (solo; closes Forecasting-Classical residual) | 40e80be | 4 (all fixed inline) | 2 (both fixed inline) | 0 |
| 28 | critical_slowing_down (deferred-wrapper closure; TRUE CYCLE CLOSURE 83/83) | (this commit) | 2 (both fixed inline) | 2 (both fixed inline) | 0 |
| **Total** | **83 wrappers AUDITED (100%)** | — | **40 (all fixed)** | **42 (all fixed)** | **6** |

### Volatility/risk extension batch closure (Sessions 6-8)

Original recommended extension target was the volatility/risk
family. Across 3 sessions the batch covered 5 wrappers:
garch + gjr_garch + egarch (Session 6 batch), har_rv (Session
7), caviar_quantile_dynamics (Session 8). Aggregate:
**2 severe (both fixed) / 0 operational / 0 cosmetic** — all
findings concentrated in Session 6's GARCH dispatch + EGARCH
persistence-formula bugs. Sessions 7 and 8 each produced
zero findings, validating the refined pattern: real wrapper
findings concentrate in wrappers with high math complexity
AND specification ambiguity. The `vol_garch_risk_ext` cycle
arc is now CLOSED.

**Sessions 1-5 produced zero severe wrapper findings** — all
3 operational fixes were Windows cp1252 console encoding bugs
in canonical validation scripts (audit infrastructure, not
wrapper bugs).

**Session 6 surfaced 2 SEVERE wrapper findings** — both fixed
inline within the same commit (15 LOC total in
`engine/techniques/garch_model.py`):
- F-G-DISPATCH: 3 catalog technique IDs (garch, gjr_garch,
  egarch) routed to vanilla GARCH math because no code path
  injected `vol` based on technique_id. EGARCH UI invocations
  silently produced GARCH(1,1) fits.
- F-G-PERSIST-FORMULA: EGARCH persistence formula misapplied
  the GARCH-family formula (alpha+beta+0.5*gamma) instead of
  the EGARCH-correct |beta|. 4 of 5 macro real-data EGARCH
  cells reported spurious persistence > 1 with misleading
  IGARCH-style warnings.

The Session 6 finding shape (real wrapper bugs, fixed inline)
contrasts with the Sessions 1-5 pattern (mostly cosmetic
methodology documentation). This validates the extension cycle's
hypothesis from Session 5's recommendations: **non-core
wrappers may surface real findings**; calibration audit
extensions are operationally valuable.

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
- AUDITED: 83 (Sessions 1-28; Session 28 closed deferred CSD wrapper after deferral rationale resolved)
- PENDING: 0 (CAI Phase 2 TRUE CYCLE CLOSURE 2026-04-28)
- DEFERRED: 0 (CSD deferral lifted Session 28)
- UNAUDITED: 0

## Per-wrapper status

### Causality / Relationships / Lead-Lag

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| cross_correlation_lag | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| dtw_alignment_lag | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| gcc_phat_delay | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| granger_causality | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| prewhitened_ccf_lag | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| rolling_ccf_lag | AUDITED | [causality_leadlag_batch_findings_2026_04_26.md](calibration_audit/causality_leadlag_batch_findings_2026_04_26.md) | 0 | 0 | 0 |

### Change Points / Anomalies / Interventions

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| bocpd | AUDITED | [change_points_batch_findings_2026_04_26.md](calibration_audit/change_points_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| cusum_page_hinkley | AUDITED | [change_points_batch_findings_2026_04_26.md](calibration_audit/change_points_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| intervention_analysis | AUDITED | [change_points_batch_findings_2026_04_26.md](calibration_audit/change_points_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| pelt_change_points | AUDITED | [change_points_batch_findings_2026_04_26.md](calibration_audit/change_points_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| stl_esd_anomaly | AUDITED | [change_points_batch_findings_2026_04_26.md](calibration_audit/change_points_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |

### Decomposition & Seasonal Adjustment

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| classical_decompose | AUDITED | [decomposition_batch_findings_2026_04_26.md](calibration_audit/decomposition_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| mstl_decompose | AUDITED | [decomposition_batch_findings_2026_04_26.md](calibration_audit/decomposition_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| stl_decompose | AUDITED | [decomposition_batch_findings_2026_04_26.md](calibration_audit/decomposition_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| x13_seasonal_adjust | AUDITED | [decomposition_batch_findings_2026_04_26.md](calibration_audit/decomposition_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |

### Evaluation / Uncertainty

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| block_bootstrap | AUDITED | [evaluation_uncertainty_batch_findings_2026_04_27.md](calibration_audit/evaluation_uncertainty_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| conformal_intervals | AUDITED | [evaluation_uncertainty_batch_findings_2026_04_27.md](calibration_audit/evaluation_uncertainty_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| forecast_combination | AUDITED | [evaluation_uncertainty_batch_findings_2026_04_27.md](calibration_audit/evaluation_uncertainty_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| robust_estimators | AUDITED | [evaluation_uncertainty_batch_findings_2026_04_27.md](calibration_audit/evaluation_uncertainty_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| rolling_origin_cv | AUDITED | [evaluation_uncertainty_batch_findings_2026_04_27.md](calibration_audit/evaluation_uncertainty_batch_findings_2026_04_27.md) | 0 | 0 | 0 |

### Forecasting (Classical)

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| arima | AUDITED | [arima_family_findings_2026_04_26.md](calibration_audit/arima_family_findings_2026_04_26.md) | 0 | 0 | 0 |
| arimax_sarimax | AUDITED | [forecasting_classical_batch2_findings_2026_04_26.md](calibration_audit/forecasting_classical_batch2_findings_2026_04_26.md) | 0 | 0 | 0 |
| auto_arima | AUDITED | [arima_family_findings_2026_04_26.md](calibration_audit/arima_family_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| ets_hw | AUDITED | [ets_hw_findings_2026_04_27.md](calibration_audit/ets_hw_findings_2026_04_27.md) | 4 (all fixed inline) | 2 (both fixed inline) | 0 |
| intermittent_demand | AUDITED | [forecasting_classical_batch2_findings_2026_04_26.md](calibration_audit/forecasting_classical_batch2_findings_2026_04_26.md) | 0 | 0 | 0 |
| sarima | AUDITED | [arima_family_findings_2026_04_26.md](calibration_audit/arima_family_findings_2026_04_26.md) | 0 | 0 | 0 |
| theta_forecast | AUDITED | [forecasting_classical_batch2_findings_2026_04_26.md](calibration_audit/forecasting_classical_batch2_findings_2026_04_26.md) | 0 | 0 | 0 |
| transfer_function | AUDITED | [transfer_function_findings_2026_04_27.md](calibration_audit/transfer_function_findings_2026_04_27.md) | 1 (fixed inline) | 3 (all fixed inline) | 0 |

### Frequency Domain / Signal

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| emd_hht | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| fft_spectrum | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 2 (fixed inline) | 0 | 0 |
| lomb_scargle | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| periodogram_spectral_density | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| ssa | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| wavelet_coherence_phase_lag | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| wavelet_transform | AUDITED | [frequency_domain_batch_findings_2026_04_26.md](calibration_audit/frequency_domain_batch_findings_2026_04_26.md) | 0 | 0 | 0 |

### ML / Deep Learning

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| autoencoder_anomaly | AUDITED | [specialized_neural_batch_findings_2026_04_27.md](calibration_audit/specialized_neural_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| echo_state_network | AUDITED | [specialized_neural_batch_findings_2026_04_27.md](calibration_audit/specialized_neural_batch_findings_2026_04_27.md) | 0 | 3 (all fixed inline) | 0 |
| gaussian_process_forecast | AUDITED | [statistical_ml_batch_findings_2026_04_27.md](calibration_audit/statistical_ml_batch_findings_2026_04_27.md) | 1 (fixed inline) | 2 (both fixed inline) | 0 |
| gradient_boosting_forecast | AUDITED | [tree_forecasters_batch_findings_2026_04_27.md](calibration_audit/tree_forecasters_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| lightgbm_forecast | AUDITED | [tree_forecasters_batch_findings_2026_04_27.md](calibration_audit/tree_forecasters_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| lstm_gru_forecast | AUDITED | [neural_sequence_batch_findings_2026_04_27.md](calibration_audit/neural_sequence_batch_findings_2026_04_27.md) | 1 (fixed inline) | 1 (fixed inline) | 0 |
| nbeats_forecast | AUDITED | [neural_sequence_batch_findings_2026_04_27.md](calibration_audit/neural_sequence_batch_findings_2026_04_27.md) | 1 (fixed inline) | 0 | 0 |
| nhits_forecast | AUDITED | [specialized_neural_batch_findings_2026_04_27.md](calibration_audit/specialized_neural_batch_findings_2026_04_27.md) | 2 (both fixed inline) | 1 (fixed inline) | 0 |
| prophet_forecast | AUDITED | [statistical_ml_batch_findings_2026_04_27.md](calibration_audit/statistical_ml_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| quantile_regression | AUDITED | [statistical_ml_batch_findings_2026_04_27.md](calibration_audit/statistical_ml_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| random_forest_forecast | AUDITED | [tree_forecasters_batch_findings_2026_04_27.md](calibration_audit/tree_forecasters_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| svr_forecast | AUDITED | [statistical_ml_batch_findings_2026_04_27.md](calibration_audit/statistical_ml_batch_findings_2026_04_27.md) | 1 (fixed inline) | 1 (fixed inline) | 0 |
| tcn_forecast | AUDITED | [neural_sequence_batch_findings_2026_04_27.md](calibration_audit/neural_sequence_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| transformer_forecast | AUDITED | [neural_sequence_batch_findings_2026_04_27.md](calibration_audit/neural_sequence_batch_findings_2026_04_27.md) | 0 | 2 (both fixed inline) | 0 |
| xgboost_forecast | AUDITED | [tree_forecasters_batch_findings_2026_04_27.md](calibration_audit/tree_forecasters_batch_findings_2026_04_27.md) | 0 | 3 (all fixed inline) | 0 |

### Missing Data / Temporal Disaggregation

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| denton_chowlin_disaggregation | AUDITED | [missing_data_batch_findings_2026_04_27.md](calibration_audit/missing_data_batch_findings_2026_04_27.md) | 1 (fixed inline) | 2 (both fixed inline) | 0 |
| kalman_imputation | AUDITED | [missing_data_batch_findings_2026_04_27.md](calibration_audit/missing_data_batch_findings_2026_04_27.md) | 1 (fixed inline) | 0 | 0 |
| loess_interpolation | AUDITED | [missing_data_batch_findings_2026_04_27.md](calibration_audit/missing_data_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |

### Multivariate Systems

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| bvar | AUDITED | [multivariate_systems_batch_findings_2026_04_27.md](calibration_audit/multivariate_systems_batch_findings_2026_04_27.md) | 0 | 1 (fixed inline) | 0 |
| dynamic_factor_model | AUDITED | [multivariate_systems_batch_findings_2026_04_27.md](calibration_audit/multivariate_systems_batch_findings_2026_04_27.md) | 1 (fixed inline) | 0 | 0 |
| forecast_reconciliation | AUDITED | [multivariate_systems_batch_findings_2026_04_27.md](calibration_audit/multivariate_systems_batch_findings_2026_04_27.md) | 2 (both fixed inline) | 0 | 0 |
| johansen_cointegration | AUDITED | [johansen_findings_2026_04_26.md](calibration_audit/johansen_findings_2026_04_26.md) | 0 | 0 | 2 |
| pca_analysis | AUDITED | [multivariate_systems_batch_findings_2026_04_27.md](calibration_audit/multivariate_systems_batch_findings_2026_04_27.md) | 1 (fixed inline) | 0 | 0 |
| var | AUDITED | [var_vecm_findings_2026_04_26.md](calibration_audit/var_vecm_findings_2026_04_26.md) | 0 | 0 | 0 |
| vecm | AUDITED | [var_vecm_findings_2026_04_26.md](calibration_audit/var_vecm_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |

### Regimes / Nonlinear

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| critical_slowing_down | AUDITED | [critical_slowing_down_findings_2026_04_28.md](calibration_audit/critical_slowing_down_findings_2026_04_28.md) | 2 (both fixed inline) | 2 (both fixed inline) | 0 |
| hmm | AUDITED | [markov_regime_batch_findings_2026_04_26.md](calibration_audit/markov_regime_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| markov_switching | AUDITED | [markov_regime_batch_findings_2026_04_26.md](calibration_audit/markov_regime_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| nar_narx | AUDITED | [markov_regime_batch_findings_2026_04_26.md](calibration_audit/markov_regime_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| star | AUDITED | [markov_regime_batch_findings_2026_04_26.md](calibration_audit/markov_regime_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| tar_setar | AUDITED | [markov_regime_batch_findings_2026_04_26.md](calibration_audit/markov_regime_batch_findings_2026_04_26.md) | 0 | 0 | 0 |

### State Space / Filtering

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| kalman_filter | AUDITED | [kalman_findings_2026_04_25.md](calibration_audit/kalman_findings_2026_04_25.md) | 0 | 2 (both fixed inline) | 0 |
| kalman_smoother | AUDITED | [kalman_findings_2026_04_25.md](calibration_audit/kalman_findings_2026_04_25.md) | 0 | 2 (shared with kalman_filter) | 0 |
| local_level | AUDITED | [state_space_batch_findings_2026_04_26.md](calibration_audit/state_space_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| local_linear_trend | AUDITED | [state_space_batch_findings_2026_04_26.md](calibration_audit/state_space_batch_findings_2026_04_26.md) | 0 | 0 | 0 |
| particle_filter | AUDITED | [state_space_batch_findings_2026_04_26.md](calibration_audit/state_space_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |
| structural_ts | AUDITED | [state_space_batch_findings_2026_04_26.md](calibration_audit/state_space_batch_findings_2026_04_26.md) | 0 | 0 | 0 |

### Stationarity / Tests

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| adf_test | AUDITED | [stationarity_tests_batch_findings_2026_04_26.md](calibration_audit/stationarity_tests_batch_findings_2026_04_26.md) | 2 (both fixed inline) | 0 | 0 |
| kpss_test | AUDITED | [stationarity_tests_batch_findings_2026_04_26.md](calibration_audit/stationarity_tests_batch_findings_2026_04_26.md) | 2 (both fixed inline) | 0 | 0 |
| pp_test | AUDITED | [stationarity_tests_batch_findings_2026_04_26.md](calibration_audit/stationarity_tests_batch_findings_2026_04_26.md) | 1 (fixed inline) | 0 | 0 |

### Volatility / Risk / Tails

| Wrapper | Status | Findings doc | Severe | Operational | Cosmetic |
|---|---|---|---|---|---|
| caviar_quantile_dynamics | AUDITED | [caviar_findings_2026_04_26.md](calibration_audit/caviar_findings_2026_04_26.md) | 0 | 0 | 0 |
| egarch | AUDITED | [garch_family_findings_2026_04_26.md](calibration_audit/garch_family_findings_2026_04_26.md) | 1 (fixed inline; shared with garch/gjr_garch) | 0 | 0 |
| evt_pot_gpd | AUDITED | [evt_pot_gpd_findings_2026_04_26.md](calibration_audit/evt_pot_gpd_findings_2026_04_26.md) | 0 | 0 | 1 |
| garch | AUDITED | [garch_family_findings_2026_04_26.md](calibration_audit/garch_family_findings_2026_04_26.md) | 1 (fixed inline; shared) | 0 | 0 |
| gjr_garch | AUDITED | [garch_family_findings_2026_04_26.md](calibration_audit/garch_family_findings_2026_04_26.md) | 1 (fixed inline; shared) | 0 | 0 |
| har_cj | AUDITED | [har_cj_findings_2026_04_26.md](calibration_audit/har_cj_findings_2026_04_26.md) | 0 | 1 (fixed inline) | 1 |
| har_rv | AUDITED | [har_rv_findings_2026_04_26.md](calibration_audit/har_rv_findings_2026_04_26.md) | 0 | 0 | 0 |
| stochastic_volatility | AUDITED | [stochastic_volatility_findings_2026_04_26.md](calibration_audit/stochastic_volatility_findings_2026_04_26.md) | 0 | 0 | 2 |

## Notes

- Phase 2 ships ~5 commits, one per audit session, per CAI
  Phase 1 §5.1 sequencing.
- `critical_slowing_down` was originally deferred because it
  shipped on 2026-04-25 (commit `94742fe`); too new for the
  calibration audit cycle. Deferral lifted 2026-04-28 in
  Session 28 after wrapper stabilized. 4 findings fixed inline
  (2 severe + 2 operational). See findings doc for full
  details.
- All 82 in-scope wrappers AUDITED;
  not in this initiative's scope. Future calibration cycles
  may extend coverage.
