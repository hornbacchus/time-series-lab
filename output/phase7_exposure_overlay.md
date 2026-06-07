# Phase 7+ - Exposure Overlay on the 90-row Evidence Map

Publication-priority ranking (Matt, 1=highest) applied to `output/phase7_evidence_map.md`. Read-only; no engine/check change.

**Reconciliation:** 90 rows = 44 tier-upgrade (weak n {cross-package, functional-check}) + 22 disclosure-register (weak n none-intrinsic) + 16 scope-extension (strong n partial: 7 T1-core + 9 non-core) + 8 strong-genuine (strong n full). 12 rows fall **outside** the supplied 11-family ranking (State-Space, Evaluation/robustness, Conformal, bespoke) - tagged `U` (unranked).

## 1. The 44 TIER-UPGRADE rows - [family, priority], sorted (priority up, cross-package before functional-check, weakest tier first)

| # | technique | family | pri | tier | upgrade_path | independent reference / note |
|--|--|--|--|--|--|--|
| 1 | `var` | Yield-curve/rates | 1 | T6 | cross-package | yes-unused (R vars) |
| 2 | `vecm` | Yield-curve/rates | 1 | T6 | cross-package | yes-unused (R urca/vars) |
| 3 | `forecast_combination` | Multivariate structure | 2 | T6 | cross-package | yes-unused (forecastHybrid) |
| 4 | `pca_analysis` | Multivariate structure | 2 | T6 | functional-check | no (R prcomp unpinned) |
| 5 | `forecast_reconciliation` | Multivariate structure | 2 | T4 | functional-check | yes-used (hts/hierarchicalforecast) |
| 6 | `gcc_phat_delay` | Causality/lead-lag | 3 | T6 | functional-check | no |
| 7 | `gaussian_process_forecast` | ML/DL | 4 | T6 | functional-check | no (gpytorch ruled out) |
| 8 | `random_forest_forecast` | ML/DL | 4 | T6 | functional-check | no (sklearn = engine lib) |
| 9 | `gradient_boosting_forecast` | ML/DL | 4 | T6 | functional-check | no (sklearn) |
| 10 | `xgboost_forecast` | ML/DL | 4 | T6 | functional-check | no (xgboost = engine lib) |
| 11 | `lightgbm_forecast` | ML/DL | 4 | T6 | functional-check | no (lightgbm = engine lib) |
| 12 | `svr_forecast` | ML/DL | 4 | T6 | functional-check | no (sklearn) |
| 13 | `quantile_regression` | ML/DL | 4 | T6 | functional-check | no (sklearn) |
| 14 | `echo_state_network` | ML/DL | 4 | T6 | functional-check | no (reservoirpy = engine lib) |
| 15 | `autoencoder_anomaly` | ML/DL | 4 | T6 | functional-check | no (torch; neuralforecast ruled out) |
| 16 | `lstm_gru_forecast` | ML/DL | 4 | T6 | functional-check | no (torch) |
| 17 | `tcn_forecast` | ML/DL | 4 | T6 | functional-check | no (torch) |
| 18 | `nbeats_forecast` | ML/DL | 4 | T6 | functional-check | no (torch) |
| 19 | `nhits_forecast` | ML/DL | 4 | T6 | functional-check | no (torch) |
| 20 | `transformer_forecast` | ML/DL | 4 | T6 | functional-check | no (torch) |
| 21 | `arima` | Classical | 6 | T5 | cross-package | yes-unused (R forecast::Arima) |
| 22 | `sarima` | Classical | 6 | T5 | cross-package | yes-unused (R forecast) |
| 23 | `arimax_sarimax` | Classical | 6 | T5 | cross-package | yes-unused (R forecast) |
| 24 | `auto_arima` | Classical | 6 | T5 | cross-package | yes-unused (R forecast::auto.arima) |
| 25 | `ets_hw` | Classical | 6 | T5 | cross-package | yes-unused (R forecast::ets) |
| 26 | `theta_forecast` | Classical | 6 | T4 | cross-package | yes-unused (R forecast::thetaf) |
| 27 | `intermittent_demand` | Classical | 6 | T6 | functional-check | no |
| 28 | `transfer_function` | Classical | 6 | T6 | functional-check | no |
| 29 | `critical_slowing_down` | Regime/nonlinear | 7 | T6 | functional-check | no (ewstools = engine lib) |
| 30 | `har_cj` | Vol/tails | 8 | T6 | functional-check | no |
| 31 | `caviar_quantile_dynamics` | Vol/tails | 8 | T6 | functional-check | no (no standard pkg) |
| 32 | `loess_interpolation` | Decomposition | 9 | T6 | functional-check | no (statsmodels = engine lib) |
| 33 | `periodogram_spectral_density` | Frequency | 10 | T6 | functional-check | no (scipy = engine lib) |
| 34 | `wavelet_transform` | Frequency | 10 | T6 | functional-check | no (pywt = engine lib) |
| 35 | `ssa` | Frequency | 10 | T6 | functional-check | no |
| 36 | `wavelet_coherence_phase_lag` | Frequency | 10 | T6 | functional-check | no |
| 37 | `intervention_analysis` | Change-point/anomaly | 11 | T4 | cross-package | yes-unused (R forecast) |
| 38 | `bocpd` | Change-point/anomaly | 11 | T6 | functional-check | no |
| 39 | `pelt_change_points` | Change-point/anomaly | 11 | T6 | functional-check | no (ruptures = engine lib) |
| 40 | `cusum_page_hinkley` | Change-point/anomaly | 11 | T6 | functional-check | no |
| 41 | `stl_esd_anomaly` | Change-point/anomaly | 11 | T6 | functional-check | no |
| 42 | `rolling_origin_cv` | UNRANKED | U | T6 | functional-check | no |
| 43 | `particle_filter` | UNRANKED | U | T6 | functional-check | no |
| 44 | `block_bootstrap` | UNRANKED | U | T5 | functional-check | no |

## 2. * FIRST WAVE - priority 1-4 n cross-package (the asymmetric-payoff cheap wins)

| technique | family | pri | tier | independent reference (available) |
|--|--|--|--|--|
| `var` | Yield-curve/rates | 1 | T6 | yes-unused (R vars) |
| `vecm` | Yield-curve/rates | 1 | T6 | yes-unused (R urca/vars) |
| `forecast_combination` | Multivariate structure | 2 | T6 | yes-unused (forecastHybrid) |

**FUND-NOW = 3 rows.** Every other cross-package upgrade (arima, sarima, arimax_sarimax, auto_arima, ets_hw, theta - P6 Classical; intervention_analysis - P11) sits at priority 5-11.

## 3. * ML/DL REFERENCE-AVAILABILITY (priority 4 - the decisive empirical answer)

| technique | tier | upgrade_path | independent cross-package reference? |
|--|--|--|--|
| `random_forest_forecast` | T6 | functional-check | NONE - sklearn RandomForest (engine lib) - same-lib |
| `gradient_boosting_forecast` | T6 | functional-check | NONE - sklearn GBR (engine lib) - same-lib |
| `xgboost_forecast` | T6 | functional-check | NONE - xgboost (engine lib) - same-lib |
| `lightgbm_forecast` | T6 | functional-check | NONE - lightgbm (engine lib) - same-lib |
| `svr_forecast` | T6 | functional-check | NONE - sklearn SVR (engine lib) - same-lib |
| `quantile_regression` | T6 | functional-check | NONE - sklearn/statsmodels (engine lib) - same-lib |
| `gaussian_process_forecast` | T6 | functional-check | NONE - sklearn GP (engine lib) - same-lib; gpytorch ruled out |
| `prophet_forecast` | T5 | none-intrinsic | NONE - prophet/Stan (engine lib) - non-deterministic, none-intrinsic |
| `echo_state_network` | T6 | functional-check | NONE - reservoirpy/bespoke (engine lib) - same-lib |
| `autoencoder_anomaly` | T6 | functional-check | NONE - torch (engine lib) - same-lib |
| `lstm_gru_forecast` | T6 | functional-check | NONE - torch (engine lib) - same-lib; neuralforecast ruled out |
| `tcn_forecast` | T6 | functional-check | NONE - torch (engine lib) - same-lib |
| `nbeats_forecast` | T6 | functional-check | NONE - torch (engine lib) - same-lib; neuralforecast ruled out |
| `nhits_forecast` | T6 | functional-check | NONE - torch (engine lib) - same-lib; neuralforecast ruled out |
| `transformer_forecast` | T6 | functional-check | NONE - torch (engine lib) - same-lib |
| `nar_narx` | T3 | n/a | NONE - R tsDyn::nlar FAILS (NO-REFERENCE); self-parity (corrected T6) |

**Empirical answer: ZERO of the 16 ML/DL techniques has an independent cross-package reference.** The engine IS the canonical implementation (sklearn / xgboost / lightgbm / torch / prophet); any 'independent' run uses the *same library* -> the same-lib trap. 14 are functional-check (correctness validatable only by a constructed discriminating check - learn-a-known-signal / relevant-vs-irrelevant / recover-a-DGP), 1 none-intrinsic (prophet/Stan, non-deterministic -> disclosure-terminal), 1 self-parity (nar_narx, R tsDyn unavailable). **No ML/DL is cheap-fundable; the whole family is costly-functional-check or disclosure-terminal.**

## 4. The 9 SCOPE-EXTENSION rows (non-T1-core; strong n partial) - family + priority

| technique | family | pri | tier | note |
|--|--|--|--|--|
| `var_irf_bands` | Yield-curve/rates | 1 | T2 | partial-scope, already strong; extend coverage |
| `bond_yield_forecast` | Yield-curve/rates | 1 | T2 | partial-scope, already strong; extend coverage |
| `var_proxy_svar` | Yield-curve/rates | 1 | T3 | partial-scope, already strong; extend coverage |
| `var_sign_restriction` | Yield-curve/rates | 1 | T3 | partial-scope, already strong; extend coverage |
| `var_bq` | Yield-curve/rates | 1 | T3 | partial-scope, already strong; extend coverage |
| `stochastic_volatility (Gaussian)` | Vol/tails | 8 | T2 | partial-scope, already strong; extend coverage |
| `stochastic_volatility (Student-t)` | Vol/tails | 8 | T2 | partial-scope, already strong; extend coverage |
| `conformal_enbpi` | UNRANKED (Conformal/Uncertainty) | U | T2 | partial-scope, already strong; extend coverage |
| `conformal_intervals` | UNRANKED (Conformal/Uncertainty) | U | T3 | partial-scope, already strong; extend coverage |

(7 T1-core scope-extensions already shipped: `adf_test`, `cross_correlation_lag`, `denton_chowlin_disaggregation`, `dtw_alignment_lag`, `kpss_test`, `prewhitened_ccf_lag`, `rolling_ccf_lag`.)

## 5. The 22 DISCLOSURE-REGISTER rows (weak n none-intrinsic) - family + priority (ordered by exposure)

| technique | family | pri | tier | none-intrinsic reason |
|--|--|--|--|--|
| `johansen_cointegration` | Multivariate structure | 2 | T4 | yes-used (urca ca.jo) |
| `dfm` | Multivariate structure | 2 | T4 | yes-used (MARSS anchor) |
| `prophet_forecast` | ML/DL | 4 | T5 | no (Stan) |
| `pp_test` | Stationarity | 5 | T5 | yes-used (urca ur.pp) |
| `tar_setar` | Regime/nonlinear | 7 | T4 | yes-used (R tsDyn::setar) |
| `hmm` | Regime/nonlinear | 7 | T4 | yes-used (R depmixS4) |
| `markov_switching` | Regime/nonlinear | 7 | T4 | yes-used (R MSwM) |
| `star` | Regime/nonlinear | 7 | T5 | yes-used (R tsDyn::star) |
| `garch` | Vol/tails | 8 | T4 | yes-used (rugarch) |
| `egarch` | Vol/tails | 8 | T4 | yes-used (rugarch) |
| `gjr_garch` | Vol/tails | 8 | T4 | yes-used (rugarch) |
| `evt_pot_gpd` | Vol/tails | 8 | T4 | yes-used (extRemes/POT) |
| `kalman_imputation` | Decomposition | 9 | T4 | yes-used (KFAS) |
| `mstl_decompose` | Decomposition | 9 | T5 | yes-used (R forecast::mstl) |
| `stl_decompose` | Decomposition | 9 | T5 | yes-used (R stats::stl) |
| `x13_seasonal_adjust` | Decomposition | 9 | T5 | yes-unused (seasonal::seas, **not installed**) |
| `lomb_scargle` | Frequency | 10 | T5 | yes-used (astropy) |
| `emd_hht` | Frequency | 10 | T5 | yes-used (PyEMD) |
| `local_level` | UNRANKED | U | T4 | yes-used (KFAS) |
| `local_linear_trend` | UNRANKED | U | T4 | yes-used (KFAS) |
| `structural_ts` | UNRANKED | U | T4 | yes-used (KFAS) |
| `kalman_filter+smoother` | UNRANKED | U | T4 | yes-used (KFAS) |

## 6. INDICATIVE 3-band cut (disclose-honestly; for adjudication, not a decision)

| band | definition | count |
|--|--|--|
| **FUND-NOW** | cross-package wins in priority 1-4 | **3** |
| **FUND-OR-DISCLOSE** | functional-check upgrades in priority 1-4 (costly, judgment-needed) | **17** |
| **DISCLOSE-TERMINAL** | weak rows in priority 5-11 + all none-intrinsic + unranked | **46** |

**FUND-NOW (3):** `var`, `vecm`, `forecast_combination`

> ★ **CORRECTION (source-read; harness Commit `1ab1018`) — the FUND-NOW=3 count was a MIS-READ.** The looks-covered read inverted this band's premise (same class as the conformal/nar_narx map-digest errors — the map's labels overstate, the source reads correct them):
> - **`var`** and **`vecm`** were NOT "pinned-but-unwired" — their checks already carry R arms, but invoke statsmodels DIRECTLY (engine bypassed). The real gap was **engine-invocation**, now closed by `p3_var_crosspkg` (modest: cross-package OLS, engine-WRAPPER-validated — VAR is tautological exact-OLS) + `p3_vecm_crosspkg` (**genuine** cross-package: independent Johansen, β 9.99e-16 / α 2.78e-13).
> - **`forecast_combination`** was NOT a cross-package win — **R forecastHybrid is an INFEASIBLE reference** (6 components incl. state-space ETS vs the engine's 3 incl. classical Holt-Winters; the components differ, so the combined forecast can't match; ties to the banked B1 classical→state-space finding). No arm built; the existing self-parity check stays.
> **Real shape: 2 engine-invocation upgrades (1 modest, 1 genuine) + 1 infeasibility finding — NOT 3 cross-package cheap wins.** The genuine cross-package gain from this band is **1 row (`vecm`)**.

**FUND-OR-DISCLOSE (17):** `pca_analysis`, `forecast_reconciliation`, `gcc_phat_delay`, `gaussian_process_forecast`, `random_forest_forecast`, `gradient_boosting_forecast`, `xgboost_forecast`, `lightgbm_forecast`, `svr_forecast`, `quantile_regression`, `echo_state_network`, `autoencoder_anomaly`, `lstm_gru_forecast`, `tcn_forecast`, `nbeats_forecast`, `nhits_forecast`, `transformer_forecast` - * the ML/DL subset (14): `autoencoder_anomaly`, `echo_state_network`, `gaussian_process_forecast`, `gradient_boosting_forecast`, `lightgbm_forecast`, `lstm_gru_forecast`, `nbeats_forecast`, `nhits_forecast`, `quantile_regression`, `random_forest_forecast`, `svr_forecast`, `tcn_forecast`, `transformer_forecast`, `xgboost_forecast`.

**Read:** the genuine FUND-NOW set is tiny - **3 rows** (`var`, `vecm`, `forecast_combination`), all priority 1-2 with off-the-shelf R references; priority-3 causality is already T1-core-done and ML/DL (priority 4) has **no** cross-package option, so the real decision is the **17-row FUND-OR-DISCLOSE band** (14 of them deep-learning functional-checks) - fund the discriminating checks, or disclose honestly.
