"""
Technique registry: maps technique_id strings to their module paths.

Modules are imported lazily by engine_worker when a request arrives.
Each module must expose a ``run(ctx, progress_callback)`` function.
"""

TECHNIQUE_REGISTRY = {
    # --- Decomposition ---
    "stl_decompose": "techniques.stl_decompose",
    "classical_decompose": "techniques.classical_decompose",
    "mstl_decompose": "techniques.mstl_decompose",

    # --- Exponential Smoothing / Forecasting ---
    "ets_hw": "techniques.ets_hw",
    "holt_winters": "techniques.ets_hw",
    "theta_forecast": "techniques.theta_forecast",
    "theta": "techniques.theta_forecast",

    # --- TBATS / BATS (Follow-up 1b) ---
    # Multi-seasonal forecaster. `use_trigonometric=False` (param) selects
    # BATS instead of TBATS within the same wrapper; the `bats` alias
    # routes to the same module and users can override the default in
    # params.
    "tbats_forecast": "techniques.tbats_forecast",
    "tbats": "techniques.tbats_forecast",
    "bats": "techniques.tbats_forecast",

    # --- ARIMA family ---
    "auto_arima": "techniques.arima",
    "arima": "techniques.arima",
    "sarima": "techniques.sarima",

    # --- Unit root / Stationarity tests ---
    "adf_test": "techniques.adf_test",
    "kpss_test": "techniques.kpss_test",
    "pp_test": "techniques.pp_test",
    "phillips_perron": "techniques.pp_test",

    # --- Causality / Lead-lag ---
    "granger_causality": "techniques.granger_causality",
    "prewhitened_ccf_lag": "techniques.prewhitened_ccf_lag",
    "cross_correlation_lag": "techniques.cross_correlation_lag",
    "ccf_lag": "techniques.cross_correlation_lag",

    # --- Multivariate models ---
    "var_model": "techniques.var_model",
    "var": "techniques.var_model",
    "vecm_model": "techniques.vecm_model",
    "vecm": "techniques.vecm_model",

    # --- PCA ---
    "pca_analysis": "techniques.pca_analysis",
    "pca": "techniques.pca_analysis",
    "principal_component_analysis": "techniques.pca_analysis",

    # --- Cointegration ---
    "johansen_cointegration": "techniques.johansen_cointegration",
    "johansen": "techniques.johansen_cointegration",

    # --- Volatility ---
    "garch_model": "techniques.garch_model",
    "garch": "techniques.garch_model",

    # --- Change point detection ---
    "pelt_change_points": "techniques.pelt_change_points",
    "change_points": "techniques.pelt_change_points",

    # --- Spectral / Frequency domain ---
    "fft_spectrum": "techniques.fft_spectrum",
    "fft": "techniques.fft_spectrum",

    # --- Wavelet ---
    "wavelet_transform": "techniques.wavelet_transform",
    "wavelet": "techniques.wavelet_transform",

    # --- State space / Kalman ---
    # NOTE: `kalman_filter`, `kalman_smoother`, `kalman`, and `ucm` aliases
    # were removed when the "Kalman Filter" ribbon button was renamed to
    # "Structural TS" and kalman_filter_model.py was retired in favor of
    # the richer structural_ts.py wrapper. The catalog IDs `kalman_filter`
    # and `kalman_smoother` are reserved for the genuine filter/smoother
    # techniques that Prompt C's State Space batch will implement as
    # distinct wrappers.

    # --- Evaluation / Uncertainty (K) ---
    "rolling_origin_cv": "techniques.rolling_origin_cv",
    "block_bootstrap": "techniques.block_bootstrap",
    "conformal_intervals": "techniques.conformal_intervals",
    "forecast_combination": "techniques.forecast_combination",
    "robust_estimators": "techniques.robust_estimators",

    # --- Missing Data / Temporal Disaggregation (L) ---
    "kalman_imputation": "techniques.kalman_imputation",
    "loess_interpolation": "techniques.loess_interpolation",
    "lowess_interpolation": "techniques.loess_interpolation",
    "denton_disaggregation": "techniques.denton_chowlin_disaggregation",
    "chowlin_disaggregation": "techniques.denton_chowlin_disaggregation",
    "temporal_disaggregation": "techniques.denton_chowlin_disaggregation",

    # --- ML / Deep Learning (M) ---
    "gradient_boosting_forecast": "techniques.gradient_boosting_forecast",
    "gbr_forecast": "techniques.gradient_boosting_forecast",
    "quantile_regression": "techniques.quantile_regression_model",
    "quantile_forecast": "techniques.quantile_regression_model",
    "gaussian_process_forecast": "techniques.gaussian_process_forecast",
    "gp_forecast": "techniques.gaussian_process_forecast",
    "lstm_forecast": "techniques.lstm_gru_forecast",
    "gru_forecast": "techniques.lstm_gru_forecast",
    "lstm_gru_forecast": "techniques.lstm_gru_forecast",
    "tcn_forecast": "techniques.tcn_forecast",
    "nbeats_forecast": "techniques.nbeats_forecast",
    "nbeats": "techniques.nbeats_forecast",
    "transformer_forecast": "techniques.transformer_forecast",

    # --- Seasonal Adjustment ---
    "x13_seasonal_adjust": "techniques.x13_seasonal_adjust",
    "x13": "techniques.x13_seasonal_adjust",
    "x13_arima_seats": "techniques.x13_seasonal_adjust",

    # --- Stochastic Volatility / Risk (Batch 3) ---
    "stochastic_volatility": "techniques.stochastic_volatility",
    "sv_model": "techniques.stochastic_volatility",
    "har_rv": "techniques.har_rv",
    "har": "techniques.har_rv",
    "evt_pot_gpd": "techniques.evt_pot_gpd",
    "evt": "techniques.evt_pot_gpd",
    "gpd": "techniques.evt_pot_gpd",
    "caviar_quantile_dynamics": "techniques.caviar_quantile_dynamics",
    "caviar": "techniques.caviar_quantile_dynamics",

    # --- Spectral / Frequency domain (Batch 3) ---
    "periodogram_spectral_density": "techniques.periodogram_spectral_density",
    "periodogram": "techniques.periodogram_spectral_density",
    "lomb_scargle": "techniques.lomb_scargle",
    "lomb_scargle_periodogram": "techniques.lomb_scargle",

    # --- Wavelet / SSA (Batch 3) ---
    "wavelet_coherence": "techniques.wavelet_coherence",
    "ssa_model": "techniques.ssa_model",
    "ssa": "techniques.ssa_model",
    "singular_spectrum_analysis": "techniques.ssa_model",

    # --- Change Point Detection (Batch 3) ---
    "bocpd": "techniques.bocpd",
    "bayesian_change_point": "techniques.bocpd",
    "cusum_page_hinkley": "techniques.cusum_page_hinkley",
    "cusum": "techniques.cusum_page_hinkley",
    "page_hinkley": "techniques.cusum_page_hinkley",

    # --- Anomaly Detection (Batch 3) ---
    "stl_esd_anomaly": "techniques.stl_esd_anomaly",
    "anomaly_detection": "techniques.stl_esd_anomaly",
    "esd_anomaly": "techniques.stl_esd_anomaly",

    # --- Intervention Analysis (Batch 3) ---
    "intervention_analysis": "techniques.intervention_analysis",
    "intervention": "techniques.intervention_analysis",

    # --- Cross-correlation / Delay / Alignment (Batch 3) ---
    "gcc_phat_delay": "techniques.gcc_phat_delay",
    "gcc_phat": "techniques.gcc_phat_delay",
    "rolling_ccf_lag": "techniques.rolling_ccf_lag",
    "rolling_ccf": "techniques.rolling_ccf_lag",
    "dtw_alignment_lag": "techniques.dtw_alignment_lag",
    "dtw": "techniques.dtw_alignment_lag",
    "dynamic_time_warping": "techniques.dtw_alignment_lag",

    # --- ARIMAX / SARIMAX (Batch 2) ---
    "arimax": "techniques.arimax_sarimax",
    "sarimax": "techniques.arimax_sarimax",
    "arimax_sarimax": "techniques.arimax_sarimax",

    # --- Transfer Function / Distributed Lag (Batch 2) ---
    "transfer_function": "techniques.transfer_function",
    "distributed_lag": "techniques.transfer_function",

    # --- Intermittent Demand (Batch 2) ---
    "intermittent_demand": "techniques.intermittent_demand",
    "croston": "techniques.intermittent_demand",
    "sba": "techniques.intermittent_demand",
    "tsb": "techniques.intermittent_demand",

    # --- Bayesian VAR (Batch 2) ---
    "bvar": "techniques.bvar",
    "bayesian_var": "techniques.bvar",

    # --- Dynamic Factor Model (Batch 2) ---
    "dynamic_factor_model": "techniques.dynamic_factor_model",
    "dynamic_factor": "techniques.dynamic_factor_model",
    "dfm": "techniques.dynamic_factor_model",

    # --- Forecast Reconciliation (Batch 2) ---
    "forecast_reconciliation": "techniques.forecast_reconciliation",
    "reconciliation": "techniques.forecast_reconciliation",
    "hierarchical_forecast": "techniques.forecast_reconciliation",

    # --- Local Level Model (Batch 2) ---
    "local_level": "techniques.local_level",

    # --- Local Linear Trend Model (Batch 2) ---
    "local_linear_trend": "techniques.local_linear_trend",

    # --- Structural Time Series / UCM (Batch 2) ---
    "structural_ts": "techniques.structural_ts",
    "structural_time_series": "techniques.structural_ts",

    # --- Particle Filter (Batch 2) ---
    "particle_filter": "techniques.particle_filter",
    "bootstrap_particle_filter": "techniques.particle_filter",

    # --- Markov Switching (Batch 2) ---
    "markov_switching": "techniques.markov_switching",
    "markov_regression": "techniques.markov_switching",
    "regime_switching": "techniques.markov_switching",

    # --- Hidden Markov Model (Batch 2) ---
    "hmm_model": "techniques.hmm_model",
    "hmm": "techniques.hmm_model",
    "gaussian_hmm": "techniques.hmm_model",

    # --- TAR / SETAR (Batch 2) ---
    "tar_setar": "techniques.tar_setar",
    "setar": "techniques.tar_setar",
    "tar": "techniques.tar_setar",
    "threshold_ar": "techniques.tar_setar",

    # --- STAR Model (Batch 2) ---
    "star_model": "techniques.star_model",
    "star": "techniques.star_model",
    "lstar": "techniques.star_model",
    "estar": "techniques.star_model",

    # --- NAR / NARX (Batch 2) ---
    "nar_narx": "techniques.nar_narx",
    "nar": "techniques.nar_narx",
    "narx": "techniques.nar_narx",
    "mlp_forecast": "techniques.nar_narx",

    # --- ML / Deep Learning (new) ---
    "prophet_forecast": "techniques.prophet_forecast",
    "prophet": "techniques.prophet_forecast",
    "random_forest_forecast": "techniques.random_forest_forecast",
    "rf_forecast": "techniques.random_forest_forecast",
    "xgboost_forecast": "techniques.xgboost_forecast",
    "xgboost": "techniques.xgboost_forecast",
    "xgb_forecast": "techniques.xgboost_forecast",
    "svr_forecast": "techniques.svr_forecast",
    "svr": "techniques.svr_forecast",
    "support_vector_regression": "techniques.svr_forecast",
    "autoencoder_anomaly": "techniques.autoencoder_anomaly",
    "autoencoder": "techniques.autoencoder_anomaly",
    "nhits_forecast": "techniques.nhits_forecast",
    "nhits": "techniques.nhits_forecast",
    "echo_state_network": "techniques.echo_state_network",
    "esn": "techniques.echo_state_network",
    "reservoir_computing": "techniques.echo_state_network",

    # --- LightGBM ---
    "lightgbm_forecast": "techniques.lightgbm_forecast",
    "lightgbm": "techniques.lightgbm_forecast",
    "lgbm_forecast": "techniques.lightgbm_forecast",
    "lgbm": "techniques.lightgbm_forecast",

    # --- EMD / Hilbert-Huang ---
    "emd_hht": "techniques.emd_hht",
    "emd": "techniques.emd_hht",
    "eemd": "techniques.emd_hht",
    "hilbert_huang": "techniques.emd_hht",
    "empirical_mode_decomposition": "techniques.emd_hht",

    # --- Aliases for exact catalog IDs ---
    "denton_chowlin_disaggregation": "techniques.denton_chowlin_disaggregation",
    "gjr_garch": "techniques.garch_model",
    "egarch": "techniques.garch_model",
    "wavelet_coherence_phase_lag": "techniques.wavelet_coherence",
    # kalman_filter / kalman_smoother aliases intentionally absent — see
    # the State Space block above. They will be re-added by Prompt C as
    # their own distinct technique IDs.
}
