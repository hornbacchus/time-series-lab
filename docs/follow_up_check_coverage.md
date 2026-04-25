# Phase 4.5 Harness Coverage Mapping

Static mapping from TSL wrappers in `engine/techniques/` to
harness checks that exercise them. Used by Phase 4.5 of the
follow-up workflow to determine which parity check(s) apply
to a given follow-up.

See [`follow_up_workflow.md`](follow_up_workflow.md) for usage.

## Coverage table

| TSL wrapper | Harness check (technique_id) | Tier | Invocation pattern |
|---|---|---|---|
| stochastic_volatility.py | 2b_mcmc_sv_gaussian | slow | full wrapper via run(ctx) |
| stochastic_volatility.py | 2c_mcmc_sv_student_t | slow | full wrapper via run(ctx) |
| bvar.py | 1c_bvar_irf_fevd | fast | helper-level direct import |
| kalman_filter.py | 2a_kalman_filter_smoother | fast | direct external library |
| kalman_smoother.py | 2a_kalman_filter_smoother | fast | direct external library |
| caviar_quantile_dynamics.py | 3a_caviar_sav | fast | full wrapper via run(ctx) |
| har_cj.py | 3b_har_cj | fast | full wrapper via run(ctx) |
| evt_pot_gpd.py | 3c_evt_ferro_segers | fast | full wrapper via run(ctx) |
| johansen_cointegration.py | 3d_johansen_bartlett | fast | mixed (helper + wrapper) |
| forecast_reconciliation.py | 3e_mint_family | fast | helper-level direct import |
| transformer_forecast.py | 3f_transformer_attention | fast | helper-level direct import |
| critical_slowing_down.py | critical_slowing_down | fast | full wrapper via run(ctx) |

**Coverage summary:** 11 wrappers covered by 12 checks across
10 fast-tier + 2 slow-tier. The `_smoke_test` check exercises
no wrapper (harness end-to-end smoke test).

**Partial-coverage caveats:**

- `caviar_quantile_dynamics.py` is covered for the **SAV
  specification only**. The AS (Asymmetric Slope) and IG
  (Indirect GARCH) specifications share the same wrapper code
  path but are not exercised by `3a_caviar_sav`. Follow-ups
  touching AS/IG-specific code paths should disclose Phase
  4.5 coverage gap.
- `stochastic_volatility.py` is covered for the **MCMC
  inference path only**, with the Gibbs backend forced via
  the `_check_c_compiler_available` monkey-patch. The PyMC
  NUTS backend is not exercised in CI environments without
  a C++ compiler. The quasi-ML inference path is not
  exercised by either parity check.
- `johansen_cointegration.py` is covered for the **trace
  statistic + Bartlett correction**. Maximum-eigenvalue
  statistic and critical-value tables are not parity-checked
  (the directive's Q1 from Session 3a explicitly skipped
  CV comparison as a methodology choice between Osterwald-
  Lenum and urca's tables).

## Wrappers without harness coverage

The following wrappers in `engine/techniques/` have no Phase
4.5 harness check. Follow-ups touching these should disclose
"Phase 4.5 N/A: no harness check covers `<wrapper>`" in the
commit message. Adding harness coverage for any of these is a
follow-up opportunity.

### Forecasting (classical)

- `arima.py`
- `arimax_sarimax.py`
- `sarima.py`
- `ets_hw.py`
- `theta_forecast.py`
- `tbats_forecast.py`
- `prophet_forecast.py`
- `intermittent_demand.py`

### Forecasting (ML / DL)

- `lstm_gru_forecast.py`
- `tcn_forecast.py`
- `nbeats_forecast.py`
- `nhits_forecast.py`
- `gradient_boosting_forecast.py`
- `lightgbm_forecast.py`
- `xgboost_forecast.py`
- `random_forest_forecast.py`
- `svr_forecast.py`
- `gaussian_process_forecast.py`
- `nar_narx.py`
- `echo_state_network.py`

### Decomposition / Spectral / Frequency

- `classical_decompose.py`
- `mstl_decompose.py`
- `stl_decompose.py`
- `x13_seasonal_adjust.py`
- `emd_hht.py`
- `ssa_model.py`
- `wavelet_transform.py`
- `wavelet_coherence.py`
- `fft_spectrum.py`
- `periodogram_spectral_density.py`
- `lomb_scargle.py`

### Volatility / Risk (other than stochastic_volatility, har_cj,
evt_pot_gpd, caviar_quantile_dynamics)

- `garch_model.py`
- `har_rv.py`
- `quantile_regression_model.py`

### State space / Filters (other than kalman_filter,
kalman_smoother)

- `kalman_imputation.py`
- `local_level.py`
- `local_linear_trend.py`
- `structural_ts.py`
- `dynamic_factor_model.py`
- `particle_filter.py`

### Multivariate (other than bvar, johansen_cointegration,
forecast_reconciliation, transformer_forecast)

- `var_model.py`
- `vecm_model.py`

### Stationarity / Unit root tests

- `adf_test.py`
- `kpss_test.py`
- `pp_test.py`

### Causality / Lead-lag

- `granger_causality.py`
- `cross_correlation_lag.py`
- `prewhitened_ccf_lag.py`
- `rolling_ccf_lag.py`
- `dtw_alignment_lag.py`
- `gcc_phat_delay.py`
- `transfer_function.py`

### Regimes / Nonlinear

- `markov_switching.py`
- `tar_setar.py`
- `star_model.py`
- `hmm_model.py`

### Change points / Anomalies

- `bocpd.py`
- `pelt_change_points.py`
- `cusum_page_hinkley.py`
- `stl_esd_anomaly.py`
- `autoencoder_anomaly.py`

### Missing data / Imputation / Resampling

- `denton_chowlin_disaggregation.py`
- `loess_interpolation.py`

### Evaluation / Combination / CV

- `forecast_combination.py`
- `rolling_origin_cv.py`
- `block_bootstrap.py`
- `conformal_intervals.py`

### Other

- `intervention_analysis.py`
- `pca_analysis.py`
- `robust_estimators.py`

### Non-wrapper modules (excluded from coverage tracking)

These are infrastructure / shared helpers, not user-facing
techniques:

- `_kalman_common.py`
- `_sv_mcmc.py`
- `_sv_mcmc_gibbs.py`
- `base.py`
- `registry.py`

## Invocation pattern legend

- **full wrapper via run(ctx):** Check builds a `RunContext`
  and calls the wrapper's `run(ctx)` function. Exercises the
  user-facing code path end-to-end.
- **helper-level direct import:** Check imports private
  helpers from the wrapper module (functions prefixed with
  `_`) and exercises them directly. Bypasses `run(ctx)`;
  tests the algorithm/math layer only.
- **mixed (helper + wrapper):** Check uses both patterns
  above. Typically validates a private helper plus the
  `run(ctx)` integration.
- **direct external library:** Check bypasses TSL entirely
  and calls the underlying external library that TSL wraps.
  Validates the same code path TSL exercises while bypassing
  the presentation layer.

## Maintenance

When adding a new harness check (per
[`reference_parity_contributor_guide.md`](reference_parity_contributor_guide.md)),
update this table in the same commit. Stale coverage silently
weakens Phase 4.5 enforcement.

When adding a new technique wrapper to `engine/techniques/`,
either add an entry to the "Wrappers without harness coverage"
section above or add a harness check (per the contributor
guide) and add the wrapper to the coverage table. The two
sections together should enumerate every `*.py` file in
`engine/techniques/` that is a user-facing technique wrapper.
