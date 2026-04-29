# TSL Reference Parity — Per-Wrapper Status Tracker (P-4)

**Authoritative tracker for Phase 3 execution.**
Updated per session per master plan §3.2 and §15.

**Status legend (per master plan §3.1):**

- `PASS` — Output matches reference within stated tolerance on stated fixtures.
- `CAVEAT` — Matches except in stated regime (boundary, near-singular, etc.).
- `DOCUMENTED-DIVERGENCE` — Does not match; divergence is methodology-equivalent (different optimizer / prior / default), not a bug.
- `NO-REFERENCE` — No clean external reference; internal-consistency only (Tier C).
- `PENDING` — Audit not yet started.
- `IN-PROGRESS` — Audit in flight (mid-session).

CI gate: `parity-fast.yml` and `parity-slow.yml` run all `PASS` and `CAVEAT` verdicts.

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
| 11 | `tbats_forecast.py` | `1b_tbats` (audit-script only) | R `forecast::tbats` + Python `tbats` | MLE-fit | (TBD) | PENDING (harness promotion) — Phase 3 Batch 1 | `reports/1b_tbats_audit.md` | (deprecated `scripts/audit_1b_tbats.py`; needs harness check) |
| 12 | `transformer_forecast.py` (attention-capture only) | `3f_transformer_attention` | PyTorch native `nn.MultiheadAttention(need_weights=True)` | DL deterministic-flag | fast | **PASS** | `reports/3f_attention_audit.md` | `harness/checks/transformer_attention.py` |

**Verification Initiative summary:** 12 wrappers covered; 11 PASS, 1 PENDING harness promotion (`tbats_forecast.py`).

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

## Phase 3 — Batches 5–10 (PENDING)

(Wrappers enumerated in `plans/reference_parity_phase3_master_plan.md` Appendix A; status rows added per session as audits complete.)

| Batch | Theme | Wrapper count | Sessions | Status |
|---|---|---:|---|---|
| 4 | R Markov / nonlinear | 5 | S10–S11 | PENDING |
| 5 | R state space | 5 | S12 | PENDING |
| 6 | R change-points / stationarity | 9 | S13–S14 | PENDING |
| 7 | Python spectral | 7 | S15–S16 | PENDING |
| 8 | Python ML | 7 | S17–S18 | PENDING |
| 9 | Python DL | 9 | S19–S21 | PENDING |
| 10 | Misc + Tier C | 12 | S22–S23 | PENDING |

---

## Aggregate progress

| Metric | Value |
|---|---:|
| Phase 1+2 covered (Verification Initiative) | 12 wrappers |
| Phase 3 in-scope total | 70 audit deliverables |
| Phase 3 covered as of latest update | **23** (19 PASS + 4 CAVEAT — Batches 1+2+3+4 complete) |
| Phase 3 remaining | 47 |
| Phase 3 BLOCK | 0 |
| Documented Secondary-tier divergences (non-blocking) | 2 (ETS + VAR AIC scale offsets; Pattern D) |
| Phase 3 sessions used | 7 (S2–S8) — **3 sessions ahead of master plan** |
| Cross-batch patterns surfaced | A–H + Pattern I/J/K candidates |

**Last updated:** 2026-04-29 (Phase 3 Session 8 close — Batch 4 complete in single session, 3 sessions ahead of schedule).
