# TSL Reference Parity — Per-Wrapper Status Tracker (P-4)

**Status:** v1.0.0 — Phase 3 closed at Session 18 (2026-04-29).
Authoritative coverage data tracker. Companion to:

- [P-1 parity standard](engineering/parity_standard.md)
  v1.0.0 — directive ("must") for new wrapper PRs
- [P-2 parity diagnostic reference](engineering/parity_diagnostic_reference.md)
  v1.0.0 — descriptive reference / playbook
- [P-3 parity empirical findings](engineering/parity_empirical_findings.md)
  v1.0.0 — descriptive narrative

**Status legend (per master plan §3.1; see [P-1 §2](engineering/parity_standard.md#2-four-verdict-closure-rule-b) for binding semantics):**

- `PASS` — Output matches reference within stated tolerance on stated fixtures.
- `CAVEAT` — Matches except in stated regime (boundary, near-singular, MC noise band, finite-sample slack).
- `DOCUMENTED-DIVERGENCE` — Does not match; divergence is methodology-equivalent (different optimizer / prior / default), not a bug. **Empirical note:** not encountered as distinct outcome in Phase 3; CAVEAT absorbed all such cases.
- `NO-REFERENCE` — No clean external reference; internal-consistency proxy (Tier C).
- `SKIP` — Runtime dependency unavailable (host binary, package install fails); informative-not-failing per [P-1 §2.4](engineering/parity_standard.md#24-skip-graceful-runtime-convention-b).
- `PENDING` — Audit not yet started.
- `IN-PROGRESS` — Audit in flight (mid-session).

CI gate: `parity-fast.yml` and `parity-slow.yml` run all `PASS`, `CAVEAT`, and `SKIP` verdicts (CAVEAT exit-code 2 → CI green per [P-1 §6.4](engineering/parity_standard.md#64-exit-code-policy-b)).

---

## Verification Initiative coverage (Phase 1/2; pre-Phase-3)

| # | Wrapper | Audit ID | Reference | Tolerance class | Tier | Verdict | Audit report | Audit script |
|---|---|---|---|---|---|---|---|---|
| 1 | `bvar.py` (IRF / FEVD given coefs) | `1c_bvar_irf_fevd` | R `vars` | Closed-form analytical | fast | **PASS** | `reports/1c_bvar_irf_audit.md` | `harness/checks/bvar_irf_fevd.py` |
| 2 | `caviar_quantile_dynamics.py` | `3a_caviar_sav` | Engle-Manganelli paper reimpl + R `quantreg` | MLE-fit (3-tier) | fast | PASS (with documented β non-uniqueness) | `reports/3a_caviar_audit.md` | `harness/checks/caviar_sav.py` |
| 3 | `critical_slowing_down.py` | `critical_slowing_down` | Python `ewstools` 2.1.2 | MLE-fit / closed-form | fast | **PASS** | (Phase 2 cleanup; check-only) | `harness/checks/critical_slowing_down.py` |
| 4 | `evt_pot_gpd.py` (Ferro-Segers) | `3c_evt_ferro_segers` | R `extRemes` | Closed-form | fast | **PASS** | `reports/3c_ferro_segers_audit.md` | `harness/checks/evt_ferro_segers.py` |
| 5 | `forecast_reconciliation.py` (4 methods: ols, wls_variance, mint_shrinkage, mint_sample) | `3e_mint_family` | R `hts` + Python `hierarchicalforecast` | Closed-form analytical | fast | **PASS** (≤ 4.66e-15 vs hts) | `reports/3e_mint_audit.md` | `harness/checks/mint_family.py` |
| 6 | `har_cj.py` | `3b_har_cj` | From-scratch reimpl per ABD 2007 paper | OLS / closed-form | fast | **PASS** | `reports/3b_har_cj_audit.md` | `harness/checks/har_cj.py` |
| 7 | `johansen_cointegration.py` | `3d_johansen_bartlett` | R `urca::ca.jo` (Reimers correction) | Closed-form | fast | **PASS** | `reports/3d_johansen_audit.md` | `harness/checks/johansen_bartlett.py` |
| 8 | `kalman_filter.py` + `kalman_smoother.py` | `2a_kalman_filter_smoother` | R `dlm` + R `KFAS` | Closed-form (drift-banded) | fast | PASS (with documented dlm-vs-KFAS log-lik methodology offset) | `reports/2a_kalman_audit.md` | `harness/checks/kalman_filter.py` |
| 9 | `stochastic_volatility.py` (Gaussian) | `2b_mcmc_sv_gaussian` | R `stochvol::svsample` | MCMC samplers | slow | PASS (with caveat on sigma_eta prior divergence) | `reports/2b_mcmc_sv_audit.md` | `harness/checks/mcmc_sv_gaussian.py` |
| 10 | `stochastic_volatility.py` (Student-t) | `2c_mcmc_sv_student_t` | R `stochvol::svtsample` | MCMC samplers | slow | PASS (with caveat on ν posterior divergence) | `reports/2c_student_t_sv_audit.md` | `harness/checks/mcmc_sv_student_t.py` |
| 11 | `tbats_forecast.py` | `p3_tbats` (promoted at Session 3) | R `forecast::tbats` + Python `tbats` | MLE-fit | slow | **PASS** | `reports/p3_tbats_audit.md` | `harness/checks/p3_tbats.py` |
| 12 | `transformer_forecast.py` (attention-capture only) | `3f_transformer_attention` | PyTorch native `nn.MultiheadAttention(need_weights=True)` | DL deterministic-flag | fast | **PASS** | `reports/3f_attention_audit.md` | `harness/checks/transformer_attention.py` |

**Verification Initiative summary:** 12 wrappers covered; **all 12 PASS**. `tbats_forecast.py` audit-script promotion to harness check completed at Phase 3 Session 3 (Batch 1).

---

## Phase 3 — Batch 1: R `forecast` family (10 deliverables)

| # | Wrapper | Audit ID | Reference | Tolerance class | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `arima.py` | `p3_arima_manual` | R `forecast::Arima(method="ML")` | MLE-fit | fast | **PASS** | `reports/p3_arima_audit.md` | `harness/checks/p3_arima.py` | S2 |
| 2 | `arimax_sarimax.py` | `p3_arimax_sarimax` | R `forecast::Arima(xreg=...)` | MLE-fit | fast | **PASS** | `reports/p3_arimax_sarimax_audit.md` | `harness/checks/p3_arimax_sarimax.py` | S2 |
| 3 | `sarima.py` | `p3_sarima` | R `forecast::Arima(seasonal=...)` | MLE-fit | fast | **PASS** | `reports/p3_sarima_audit.md` | `harness/checks/p3_sarima.py` | S2 |
| 4 | `ets_hw.py` | `p3_ets` | R `forecast::ets` | MLE-fit (widened) | fast | **PASS** (with documented AIC scale offset) | `reports/p3_ets_audit.md` | `harness/checks/p3_ets.py` | S3 |
| 5 | `theta_forecast.py` | `p3_theta` | R `forecast::thetaf` | Closed-form (widened band, observed tight) | fast | **PASS** | `reports/p3_theta_audit.md` | `harness/checks/p3_theta.py` | S3 |
| 6 | `intermittent_demand.py` (Croston) | `p3_intermittent` | R `forecast::croston` | Closed-form | fast | **PASS** (3.77e-15 abs diff on forecast value) | `reports/p3_intermittent_audit.md` | `harness/checks/p3_intermittent.py` | S3 |
| 7 | `mstl_decompose.py` | `p3_mstl` | R `forecast::mstl` | Iterative-LOESS (widened) | fast | **CAVEAT** (non-unique decomp; structural identity bit-exact) | `reports/p3_mstl_audit.md` | `harness/checks/p3_mstl.py` | S4 |
| 8 | `classical_decompose.py` | `p3_classical_decompose` | R `stats::decompose` | Closed-form | fast | **PASS** (bit-exact 7e-14) | `reports/p3_classical_decompose_audit.md` | `harness/checks/p3_classical_decompose.py` | S4 |
| 9 | `stl_decompose.py` | `p3_stl` | R `stats::stl` | Iterative-LOESS (widened) | fast | **CAVEAT** (per-index 9e-2 abs; impl-diff) | `reports/p3_stl_audit.md` | `harness/checks/p3_stl.py` | S4 |
| 10 | `tbats_forecast.py` | `p3_tbats` (harness promotion) | R `forecast::tbats` | MLE-fit | slow | **PASS** | `reports/p3_tbats_audit.md` | `harness/checks/p3_tbats.py` | S3 |

**Batch 1 Session 4 status: COMPLETE.** 10/10 deliverables (8 PASS + 2 CAVEAT + 0 BLOCK). Per-batch summary: `tools/reference_parity/reports/p3_batch_1_summary.md`.

---

## Phase 3 — Batch 2: R volatility (4 audit IDs across 2 wrappers)

| # | Wrapper / Variant | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `garch_model.py` (sGARCH path) | `p3_sgarch` | R `rugarch` (sGARCH, gosolnp solver) | fast | **PASS** | `reports/p3_sgarch_audit.md` | `harness/checks/p3_sgarch.py` | S6 |
| 2 | `garch_model.py` (GJR-GARCH path) | `p3_gjr_garch` | R `rugarch` (gjrGARCH) | fast | **PASS** | `reports/p3_gjr_garch_audit.md` | `harness/checks/p3_gjr_garch.py` | S6 |
| 3 | `garch_model.py` (EGARCH path) | `p3_egarch` | R `rugarch` (eGARCH, with alpha-gamma name swap) | fast | **PASS** | `reports/p3_egarch_audit.md` | `harness/checks/p3_egarch.py` | S6 |
| 4 | `har_rv.py` | `p3_har_rv` | R base `lm()` reimpl (Corsi 2009 OLS) | fast | **PASS** (bit-exact 8.88e-16) | `reports/p3_har_rv_audit.md` | `harness/checks/p3_har_rv.py` | S6 |

**Batch 2 Session 6 status: COMPLETE in single session.** 4/4 PASS, 0 CAVEAT, 0 BLOCK. Master plan §15.4 budgeted 2 sessions (S6+S7); closed in S6 alone. Per-batch summary: `tools/reference_parity/reports/p3_batch_2_summary.md`. Cross-batch findings (Pattern H — DSCD): `tools/reference_parity/reports/phase3_cross_batch_findings.md`.

## Phase 3 — Batch 3: R multivariate (4 audit IDs, single-session close)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `var_model.py` | `p3_var` | R `vars::VAR` | fast | **PASS** (bit-exact 7.22e-16) | `reports/p3_var_audit.md` | `harness/checks/p3_var.py` | S7 |
| 2 | `vecm_model.py` | `p3_vecm` | R `urca::ca.jo` + `vars::cajorls` | fast | **PASS** (bit-exact 9.99e-16 after sign norm) | `reports/p3_vecm_audit.md` | `harness/checks/p3_vecm.py` | S7 |
| 3 | `dynamic_factor_model.py` | `p3_dfm` | R `MARSS::MARSS` | slow | **PASS** (loadings 1.22e-3; first em_stochastic class) | `reports/p3_dfm_audit.md` | `harness/checks/p3_dfm.py` | S7 |
| 4 | `pca_analysis.py` | `p3_pca` | Python `sklearn.decomposition.PCA` | fast | **PASS** (bit-exact 7.99e-15) | `reports/p3_pca_audit.md` | `harness/checks/p3_pca.py` | S7 |

**Batch 3 Session 7 status: COMPLETE in single session.** 4/4 PASS, 0 CAVEAT, 0 BLOCK. Master plan §15.5 budgeted 2 sessions (S8+S9); closed in S7. Per-batch summary: `tools/reference_parity/reports/p3_batch_3_summary.md`.

## Phase 3 — Batch 4: R Markov / nonlinear (5 audit IDs, single-session close)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `hmm_model.py` | `p3_hmm` | R `depmixS4` | fast | **PASS** (em_stochastic; widened transmat) | `reports/p3_hmm_audit.md` | `harness/checks/p3_hmm.py` | S8 |
| 2 | `markov_switching.py` | `p3_markov_switching` | R `MSwM::msmFit` | fast | **PASS** (means 5.9e-5; sign-convention aligned) | `reports/p3_markov_switching_audit.md` | `harness/checks/p3_markov_switching.py` | S8 |
| 3 | `tar_setar.py` | `p3_tar_setar` | R `tsDyn::setar` | fast | **PASS** (threshold 1e-2 abs) | `reports/p3_tar_setar_audit.md` | `harness/checks/p3_tar_setar.py` | S8 |
| 4 | `star_model.py` | `p3_star` | R `tsDyn::star` | fast | **CAVEAT** (Tier B/C — γ smoothness divergence) | `reports/p3_star_audit.md` | `harness/checks/p3_star.py` | S8 |
| 5 | `nar_narx.py` | `p3_nar_narx` | R `tsDyn::nlar` | fast | **CAVEAT** (NO-REFERENCE Tier C; R reference non-finite) | `reports/p3_nar_narx_audit.md` | `harness/checks/p3_nar_narx.py` | S8 |

**Batch 4 Session 8 status: COMPLETE in single session.** 3/5 PASS + 2/5 CAVEAT, 0 BLOCK. Master plan §15.6 budgeted 2 sessions (S10+S11); closed in S8. Per-batch summary: `tools/reference_parity/reports/p3_batch_4_summary.md`.

## Phase 3 — Batch 5: R state space (5 audit IDs, single-session close)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit script | Session |
|---|---|---|---|---|---|---|---|
| 1 | `local_level.py` | `p3_local_level` | R KFAS | fast | **PASS** | `harness/checks/p3_local_level.py` | S9 |
| 2 | `local_linear_trend.py` | `p3_local_linear_trend` | R KFAS | fast | **PASS** (widened LLT band) | `harness/checks/p3_local_linear_trend.py` | S9 |
| 3 | `structural_ts.py` | `p3_structural_ts` | R KFAS | fast | **PASS** | `harness/checks/p3_structural_ts.py` | S9 |
| 4 | `particle_filter.py` | `p3_particle_filter` | Python `particles` | fast | **PASS** | `harness/checks/p3_particle_filter.py` | S9 |
| 5 | `kalman_imputation.py` | `p3_kalman_imputation` | R KFAS | fast | **PASS** | `harness/checks/p3_kalman_imputation.py` | S9 |

**Batch 5 Session 9 status: COMPLETE in single session.** 5/5 PASS, 0 CAVEAT, 0 BLOCK. Per-batch summary: `tools/reference_parity/reports/p3_batch_5_summary.md`.

## Phase 3 — Batch 6: R change-points / stationarity (8 audit IDs, single-session close)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `adf_test.py` | `p3_adf` | R `urca::ur.df` | fast | **PASS** (1.07e-14 abs) | `reports/p3_adf_audit.md` | `harness/checks/p3_adf.py` | S10 |
| 2 | `kpss_test.py` | `p3_kpss` | R `urca::ur.kpss` | fast | **PASS** (5.55e-17 abs) | `reports/p3_kpss_audit.md` | `harness/checks/p3_kpss.py` | S10 |
| 3 | `pp_test.py` | `p3_pp` | R `urca::ur.pp` | fast | **PASS** (Pattern J widening — 2.09e-06 abs) | `reports/p3_pp_audit.md` | `harness/checks/p3_pp.py` | S10 |
| 4 | `bocpd.py` | `p3_bocpd` | self-parity NIG-conjugate Adams-MacKay 2007 | fast | **PASS** (bit-exact) | `reports/p3_bocpd_audit.md` | `harness/checks/p3_bocpd.py` | S10 |
| 5 | `cusum_page_hinkley.py` | `p3_cusum_page_hinkley` | self-parity identical recursion | fast | **PASS** (bit-exact) | `reports/p3_cusum_page_hinkley_audit.md` | `harness/checks/p3_cusum_page_hinkley.py` | S10 |
| 6 | `intervention_analysis.py` | `p3_intervention_analysis` | R `stats::arima(..., xreg=...)` | fast | **PASS** (mle_fit) | `reports/p3_intervention_analysis_audit.md` | `harness/checks/p3_intervention_analysis.py` | S10 |
| 7 | `pelt_change_points.py` | `p3_pelt` | direct `ruptures.Pelt` in-process | fast | **PASS** (bit-exact same-library) | `reports/p3_pelt_audit.md` | `harness/checks/p3_pelt.py` | S10 |
| 8 | `stl_esd_anomaly.py` | `p3_stl_esd` | self-parity STL + Rosner 1983 GESD | fast | **PASS** (bit-exact) | `reports/p3_stl_esd_audit.md` | `harness/checks/p3_stl_esd.py` | S10 |

**Batch 6 Session 10 status: COMPLETE in single session.** 8/8 PASS, 0 CAVEAT, 0 BLOCK. Master plan §15.8 budgeted 2 sessions (S13–S14); closed in S10 alone, extending Phase 3 lead to 5 sessions ahead. Per-batch summary: `tools/reference_parity/reports/p3_batch_6_summary.md`. **`x13_seasonal_adjust` (originally Batch 6 9th wrapper) deferred** per Appendix A — R `seasonal` package wraps X-13ARIMA-SEATS binary; non-trivial Windows install.

## Phase 3 — Batch 7: Python spectral (7 audit IDs, single-session close)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `fft_spectrum.py` | `p3_fft_spectrum` | Python `numpy.fft` | fast | **PASS** (2.84e-14 abs) | `reports/p3_fft_spectrum_audit.md` | `harness/checks/p3_fft_spectrum.py` | S11 |
| 2 | `periodogram_spectral_density.py` | `p3_periodogram` | Python `scipy.signal.periodogram` | fast | **PASS** (0.0 abs same-library) | `reports/p3_periodogram_audit.md` | `harness/checks/p3_periodogram.py` | S11 |
| 3 | `lomb_scargle.py` | `p3_lomb_scargle` | Python `astropy.timeseries.LombScargle` | fast | **PASS** (Pattern J alignment-via-metric) | `reports/p3_lomb_scargle_audit.md` | `harness/checks/p3_lomb_scargle.py` | S11 |
| 4 | `wavelet_transform.py` | `p3_wavelet_transform` | direct `pywt.wavedec` in-process | fast | **PASS** (0.0 same-library; Pattern F invariants populated) | `reports/p3_wavelet_transform_audit.md` | `harness/checks/p3_wavelet_transform.py` | S11 |
| 5 | `wavelet_coherence.py` | `p3_wavelet_coherence` | self-parity reference (Pattern K → A) | fast | **PASS** (0.0 abs) | `reports/p3_wavelet_coherence_audit.md` | `harness/checks/p3_wavelet_coherence.py` | S11 |
| 6 | `emd_hht.py` | `p3_emd_hht` | Python `PyEMD.EMD` (Laszuk) | fast | **CAVEAT** (Tier C — n_imfs ±2; ρ=0.991) | `reports/p3_emd_hht_audit.md` | `harness/checks/p3_emd_hht.py` | S11 |
| 7 | `ssa_model.py` | `p3_ssa` | from-scratch numpy SVD reference | fast | **PASS** (0.0 abs; Pattern K → A) | `reports/p3_ssa_audit.md` | `harness/checks/p3_ssa.py` | S11 |

**Batch 7 Session 11 status: COMPLETE in single session.** 6/7 PASS + 1/7 CAVEAT, 0 BLOCK. Master plan §15.9 budgeted 2 sessions; closed in 1, extending Phase 3 lead to 5–6 sessions ahead. Per-batch summary: `tools/reference_parity/reports/p3_batch_7_summary.md`. **Pattern F first concrete population beyond GARCH/Kalman/HMM/VAR**: 4 new invariants (fft_roundtrip, fft_energy_conservation, wavelet_inverse_roundtrip, wavelet_energy_conservation) replace Session 5 NotImplementedError stubs. **PyBridge first production batch**: all 7 checks used direct import (PyBridge.py_invoke shim NOT invoked); banked for check-in 1.5 simplification triage.

## Phase 3 — Batch 8: Python ML (7 audit IDs, single-session close — first all-PASS batch since Batch 1)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `random_forest_forecast.py` | `p3_random_forest` | sklearn RandomForestRegressor | fast | **PASS** (0.0 abs same-library) | `reports/p3_random_forest_audit.md` | `harness/checks/p3_random_forest.py` | S12 |
| 2 | `gradient_boosting_forecast.py` | `p3_gradient_boosting` | sklearn GradientBoostingRegressor | fast | **PASS** (0.0 abs same-library) | `reports/p3_gradient_boosting_audit.md` | `harness/checks/p3_gradient_boosting.py` | S12 |
| 3 | `xgboost_forecast.py` | `p3_xgboost` | xgboost.XGBRegressor direct | fast | **PASS** (0.0 abs same-library) | `reports/p3_xgboost_audit.md` | `harness/checks/p3_xgboost.py` | S12 |
| 4 | `lightgbm_forecast.py` | `p3_lightgbm` | lightgbm.LGBMRegressor direct | fast | **PASS** (0.0 abs same-library) | `reports/p3_lightgbm_audit.md` | `harness/checks/p3_lightgbm.py` | S12 |
| 5 | `svr_forecast.py` | `p3_svr` | sklearn.svm.SVR direct | fast | **PASS** (0.0 abs same-library) | `reports/p3_svr_audit.md` | `harness/checks/p3_svr.py` | S12 |
| 6 | `quantile_regression_model.py` | `p3_quantile_regression` | sklearn GBR with quantile loss | fast | **PASS** (0.0 abs same-library) | `reports/p3_quantile_regression_audit.md` | `harness/checks/p3_quantile_regression.py` | S12 |
| 7 | `robust_estimators.py` | `p3_robust_estimators` | R stats::mad + robustbase::Qn | fast | **PASS** (4.22e-15 abs cross-package) | `reports/p3_robust_estimators_audit.md` | `harness/checks/p3_robust_estimators.py` | S12 |

**Batch 8 Session 12 status: COMPLETE in single session.** 7/7 PASS, 0 CAVEAT, 0 BLOCK — **first all-PASS batch since Batch 1**. Master plan §15.10 budgeted 1 session; on-budget. Per-batch summary: `tools/reference_parity/reports/p3_batch_8_summary.md`. **Pattern A → 27 wrappers** (was 20). **Pattern J catalog launched** at `docs/engineering/parity_diagnostic_reference.md` Appendix B (6 entries; check-in 1.5 act-now #1). **§10.3 criterion 2 split-lock applied** (sub-criterion 2c reported; check-in 1.5 act-now #2). **PyBridge `isolate=False` shim retire decision locked** (0/14 wrappers used the shim across Batches 7+8; check-in 1.5 act-now #3 — retire at S13).

## Phase 3 — Batch 9: Python DL (9 audit IDs, single-session close — second consecutive all-PASS batch)

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `lstm_gru_forecast.py` | `p3_lstm_gru` | direct PyTorch nn.LSTM | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_lstm_gru_audit.md` | `harness/checks/p3_lstm_gru.py` | S13 |
| 2 | `tcn_forecast.py` | `p3_tcn` | direct PyTorch nn.Conv1d | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_tcn_audit.md` | `harness/checks/p3_tcn.py` | S13 |
| 3 | `nbeats_forecast.py` | `p3_nbeats` | custom PyTorch NBEATS self-parity | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_nbeats_audit.md` | `harness/checks/p3_nbeats.py` | S13 |
| 4 | `nhits_forecast.py` | `p3_nhits` | custom PyTorch NHITS self-parity | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_nhits_audit.md` | `harness/checks/p3_nhits.py` | S13 |
| 5 | `autoencoder_anomaly.py` | `p3_autoencoder` | direct PyTorch encoder-decoder | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_autoencoder_audit.md` | `harness/checks/p3_autoencoder.py` | S13 |
| 6 | `echo_state_network.py` | `p3_esn` | direct reservoirpy | fast | **PASS** (0.0 abs Pattern A.1) | `reports/p3_esn_audit.md` | `harness/checks/p3_esn.py` | S13 |
| 7 | `gaussian_process_forecast.py` | `p3_gp` | direct sklearn.gaussian_process | fast | **PASS** (0.0 abs Pattern A) | `reports/p3_gp_audit.md` | `harness/checks/p3_gp.py` | S13 |
| 8 | `prophet_forecast.py` | `p3_prophet` | direct prophet (cmdstanpy MAP) | slow | **PASS** (0.0 abs Pattern A) | `reports/p3_prophet_audit.md` | `harness/checks/p3_prophet.py` | S13 |
| 9 | `conformal_intervals.py` | `p3_conformal` | self-parity split-conformal | fast | **PASS** (0.0 abs + Pattern F invariant PASS) | `reports/p3_conformal_audit.md` | `harness/checks/p3_conformal.py` | S13 |

**Batch 9 Session 13 status: COMPLETE in single session.** 9/9 PASS, 0 CAVEAT, 0 BLOCK — **second consecutive all-PASS batch**. Master plan §15.11 budgeted 3 sessions; closed in 1, locking 17-session closure horizon. Per-batch summary: `tools/reference_parity/reports/p3_batch_9_summary.md`. **Pattern A → 36 wrappers; Pattern A.1 same-library sub-class locked at 18 wrappers**. **PyBridge `isolate=False` shim retired** (per S12 decision). **Pattern F → 14 concrete invariants** (+conformal_nominal_coverage, conformal_interval_containment). **Pattern J catalog → 9 entries** (+3 B.5 framework-incompat / wrapper-mismatch). **DL non-determinism risk pre-budget (≥30% Tier C) dramatically over-estimated: actual 0/9.** **Item 12 (verdict-runtime alignment) RESOLVED — no harness change needed.**

## Phase 3 — Batch 10: Misc + Tier C (FINAL BATCH) — 11 audit IDs, single-session close

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Audit report | Audit script | Session |
|---|---|---|---|---|---|---|---|---|
| 1 | `granger_causality.py` | `p3_granger` | R lmtest::grangertest | fast | **PASS** (8.5e-14 abs Pattern A) | `reports/p3_granger_audit.md` | `harness/checks/p3_granger.py` | S14 |
| 2 | `prewhitened_ccf_lag.py` | `p3_ccf` | R stats::ccf | fast | **PASS** (1.3e-15 abs Pattern A) | `reports/p3_ccf_audit.md` | `harness/checks/p3_ccf.py` | S14 |
| 3 | `gcc_phat_delay.py` | `p3_gcc_phat` | from-scratch self-parity | fast | **PASS** (0.0 Pattern A) | `reports/p3_gcc_phat_audit.md` | `harness/checks/p3_gcc_phat.py` | S14 |
| 4 | `dtw_alignment_lag.py` | `p3_dtw` | Python dtaidistance | fast | **PASS** (0.0 abs Pattern A) | `reports/p3_dtw_audit.md` | `harness/checks/p3_dtw.py` | S14 |
| 5 | `transfer_function.py` | `p3_transfer_function` | from-scratch self-parity | fast | **PASS** (0.0 Pattern A) | `reports/p3_transfer_function_audit.md` | `harness/checks/p3_transfer_function.py` | S14 |
| 6 | `block_bootstrap.py` | `p3_block_bootstrap` | from-scratch self-parity | fast | **PASS** (0.0 Pattern A) | `reports/p3_block_bootstrap_audit.md` | `harness/checks/p3_block_bootstrap.py` | S14 |
| 7 | `forecast_combination.py` | `p3_forecast_combination` | from-scratch self-parity | fast | **PASS** (0.0 Pattern A) | `reports/p3_forecast_combination_audit.md` | `harness/checks/p3_forecast_combination.py` | S14 |
| 8 | `rolling_origin_cv.py` | `p3_rolling_origin_cv` | from-scratch self-parity | fast | **PASS** (0.0 Pattern A) | `reports/p3_rolling_origin_cv_audit.md` | `harness/checks/p3_rolling_origin_cv.py` | S14 |
| 9 | `denton_chowlin_disaggregation.py` | `p3_denton_chowlin` | R tempdisagg::td | fast | **PASS** (6.4e-14 abs Pattern A) | `reports/p3_denton_chowlin_audit.md` | `harness/checks/p3_denton_chowlin.py` | S14 |
| 10 | `loess_interpolation.py` | `p3_loess` | direct statsmodels.lowess | fast | **PASS** (0.0 Pattern A.1) | `reports/p3_loess_audit.md` | `harness/checks/p3_loess.py` | S14 |
| 11 | `x13_seasonal_adjust.py` | `p3_x13` | R seasonal | slow | **SKIP** (X-13 binary unavailable; Tier C) | `reports/p3_x13_audit.md` | `harness/checks/p3_x13.py` | S14 |

**Batch 10 Session 14 status: COMPLETE in single session.** 10/11 PASS, 0 CAVEAT, 0 BLOCK, 1 SKIP-graceful. Master plan §15.12 budgeted 1-2 sessions; closed in 1. Per-batch summary: `tools/reference_parity/reports/p3_batch_10_summary.md`. **Pattern A → 46 wrappers** (was 36). **Pattern J catalog → 11 entries** (+2 B.6 master-plan-reference adjustments). **Harness improvement:** runner extended to SKIP on `run_tsl` ImportError (enables p3_x13 SKIP-graceful via X13NotFoundError → ImportError translation).

---

## Phase 3 batch-execution COMPLETE — 70/70 wrappers covered

**13 sessions used (S2-S14)** vs locked 17-session closure horizon — **5 sessions ahead** at batch-execution close.

Documentation phase (Sessions 15-17) + closeout (Session 18) per Item 13 lock:

- **Session 15 — P-1 parity standard:** **COMPLETE** — `docs/engineering/parity_standard.md` issued v1.0.0. Binding directive for new wrapper PRs (parity dimension). 11 sections: purpose/scope, four-verdict closure rule, output-surface discipline, reference-tier policy, tolerance bands per class, CI tier classification, manifest pinning protocol, pre-merge checklist, cross-reference to wrapper-development standard, empirical-additions Phase 3 surfaced (Pattern A.1 default, self-parity pattern, PyBridge subprocess-only, CAVEAT exit-code policy), Trigger 8/9 candidates.
- **Session 16 — P-2 diagnostic reference:** **COMPLETE** — `docs/engineering/parity_diagnostic_reference.md` v1.0.0 issued. 8 sections (A–H): tolerance class taxonomy locked at 11 classes (A); Pattern J catalog complete with 11 entries across 6 sub-sections (B); Pattern A taxonomy formalized into A.1 same-library / A.2 cross-package / A.3 self-parity (C); Pattern F structural-invariants registry with 14 concrete invariants + 4-step new-wrapper playbook + wavelet-mode interaction note (D); Pattern I sign/scale convention alignment (E); DSCD diagnostic-axis registry with 3 sub-classes + 4 instances (F); Pattern J resolution sub-patterns J.A/J.B/J.C (G). Banked items #1, #4, #11, #18, #20 closed at P-2 venue.
- **Session 17 — P-3 empirical findings synthesis:** **COMPLETE** — `docs/engineering/parity_empirical_findings.md` v1.0.0 issued. Descriptive narrative document covering Phase 3 batch-execution + documentation phase. 9 sections: the numbers / what made Phase 3 work (Pattern A.1 unlock, harness held, CI green discipline) / empirical patterns the harness exposed / surprises and reversals / CAVEAT taxonomy in practice / Phase 3.5 candidates banked / meta-lessons (reference selection is hardest decision, scaffolding pays for itself, documentation-as-you-go) / TSL parity discipline going forward / change log. Banked items #6, #7, #9, #10 closed at P-3 venue. **All 13 evidence-complete banked items now closed across P-1, P-2, P-3.**
- **Session 18:** CI workflow finalization + P-4 status tracker finalization + Phase 3 closeout commit

---

## Aggregate progress (FINAL — Phase 3 closed)

| Metric | Value |
|---|---:|
| Phase 1+2 covered (Verification Initiative) | 12 wrappers (all PASS) |
| Phase 3 in-scope total | 70 audit deliverables |
| **Phase 3 covered (FINAL)** | **70 / 70** (100%; Batches 1-10 complete) |
| Phase 3 remaining | **0 — COMPLETE** |
| Phase 3 BLOCK | **0** |
| Phase 3 PASS | **65** (93%) |
| Phase 3 CAVEAT | 5 (7% — p3_stl, p3_mstl, p3_star, p3_nar_narx, p3_emd_hht) |
| Phase 3 SKIP-graceful | 1 (p3_x13 — Tier C runtime) |
| Documented Secondary-tier divergences (non-blocking) | 2 (ETS + VAR AIC scale offsets; Pattern D) |
| Total parity checks under CI | **82** (76 fast + 6 slow; 70 Phase 3 + 12 pre-Phase-3 inherited) |
| Phase 3 sessions used (batch-execution) | 13 (S2–S14) |
| Phase 3 sessions used (documentation) | 3 (S15–S17) |
| Phase 3 sessions used (closeout) | 1 (S18) |
| **Total Phase 3 sessions** | **17** (vs original master plan budget 18-22; vs locked Item 13 horizon 17) |
| Pattern A wrappers | **46** (66% of Phase 3 in-scope) |
| Pattern A.1 same-library sub-class | **18** wrappers (locked at scale) |
| Pattern A.2 cross-package bit-exact | ~12 wrappers |
| Pattern A.3 self-parity / paper-formula reimpl | ~10 wrappers |
| Pattern F concrete invariants | **14** |
| Pattern J catalog entries | **11** (B.1-B.6 sections in P-2) |
| Pattern I sign/scale instances | **6** (P-2 Section E) |
| DSCD instances | **4** across 3 sub-classes (P-2 Section F) |
| Banked items resolved | **18 / 18** (5 RESOLVED at S12-S13 in-execution; 13 closed across S15-S17 documentation phase) |
| Cross-batch patterns surfaced | A–H + I/J/K candidates fully populated; A.1 dominant; K → A path for 5 wrappers; J resolution sub-patterns J.A/J.B/J.C |

## Documentation set (FINAL)

| Document | Type | Version | Issued at |
|---|---|---|---|
| [P-1 parity standard](engineering/parity_standard.md) | Directive ("must") | v1.0.0 | Session 15 (commit `04054a4`) |
| [P-2 parity diagnostic reference](engineering/parity_diagnostic_reference.md) | Descriptive reference / playbook | v1.0.0 | Session 16 (commit `3b08431`) |
| [P-3 parity empirical findings](engineering/parity_empirical_findings.md) | Descriptive narrative | v1.0.0 | Session 17 (commit `dedb89c`) |
| **P-4 status tracker (this document)** | Authoritative coverage data | **v1.0.0** | **Session 18 closeout** |

## Phase 3.5 candidates (banked at P-3 §6)

For forward-look:

1. **Item #9 — `single_impl_mle` band tightening:** evidence from `p3_var` (8.1 orders headroom), `p3_vecm` (13 orders), `p3_pca` (8 orders). Add new `single_impl_mle` verdict_class with 1e-5 abs / 1e-4 rel band; migrate the 3 wrappers; audit other current `mle_fit`-class wrappers.
2. **Item #10 — Per-metric bands within `em_stochastic`:** evidence from HMM (means 1e-5 abs vs transmat 0.05-0.25). Extend tolerance ladder schema to support per-metric granularity within a single verdict_class.
3. **Manifest re-pin cadence:** `MANIFEST.toml`'s `next_review` fired during batch execution without scheduled action. First quarterly re-pin window at Phase 3.5 entry.
4. **`parity-slow.yml` install matrix cleanup:** stale install lists (missing `prophet`, `dtaidistance`, `reservoirpy`, etc.) cause SKIPs in slow-tier nightly runs. Informative-not-failing per harness SKIP convention but worth fixing for full slow-tier coverage.
5. **`scripts/` cleanup:** 12 deprecated Phase 1 audit scripts under `tools/reference_parity/scripts/` superseded by `harness/checks/`. Defer cleanup to Phase 3.5 to avoid bundling with closeout commit.
6. **X-13 binary on Linux CI:** investigate whether `x13as` package is feasible in a Linux CI runner (Ubuntu has it in some distributions). If yes, add Linux-only slow-tier job for `p3_x13`.
7. **DOCUMENTED-DIVERGENCE first-instance reservation:** when this verdict first surfaces in post-Phase-3 work, document classification recipe in P-2.

---

**Last updated:** 2026-04-29 (**Phase 3.5 Session 1 close** — Items 4/5/7 bundled commit per §6 of locked Phase 3.5 plan: parity-slow.yml install matrix aligned with fast-tier (Python +12 pkgs, R +4 pkgs); deprecated Phase 1 `scripts/` directory removed (14 untracked files; INVENTORY.md §1.4 updated); DOCUMENTED-DIVERGENCE wired end-to-end as runtime outcome (`Outcome` literal + `_OUTCOME_PRIORITY` rank 3 + runner exit code 4 + both workflow YAMLs map exit 4 → CI green per CAVEAT precedent). Forward-provisioning: no current wrapper triggers DD. Fast-tier sweep 76/76 unchanged from Phase 3 close. Phase 3 closure state preserved (70/70 wrappers covered; 0 BLOCK; 18/18 banked items resolved; P-1/P-2/P-3/P-4 v1.0.0 issued; 10 sessions under master plan §17.1 worst-case projection).
