# Audit-Hygiene Inventory Verification — Full 71-Harness Enumeration (2026-05-22)

**HEAD at execution:** `a06646e` (p3_conformal Category 3 DEGENERATE-VACUOUS rewrite close)

**Methodology authority:** Refined Cat 1d criterion (revision 2) with mandatory
Validation-Surface Coverage section + Cat 2D DEGENERATE-COHERENT-WITH-
STOCHASTIC-ENGINE sub-category added at full-enumeration dispatch (this
session). Plan-mode ratification preceded full-enumeration authorization;
plan recorded at `C:\Users\matth\.claude\plans\glistening-wishing-mountain.md`.

**Inventory state recorded:** BEFORE state pre-remediation. Forward-amendment
cycles (Tier 1 bulk + Tier 2 incremental + Cat 3 remediation cycle + S62
re-execution) will produce AFTER state across ~2-3 calendar weeks at
part-time pace per ratified disposition.

---

## §1. Methodology evolution summary

### §1.1 Original Explore-agent inventory (commit `e72d6f5`)

The original methodology grouped harnesses by file-structure pattern.
Harnesses with a `_fit_predict` helper called by both `run_tsl` and
`run_reference` were classified as "Self-parity (same-library) pattern"
LEGITIMATE on the grounds that "the helper invokes the actual
engine/library code, not a reimplemented algorithm."

**Reported distribution:** 96% LEGITIMATE / 3% Category 2 / 1% Category 3
(71 harnesses; only `p3_rolling_origin_cv` surfaced as Category 3).

**Defect:** The heuristic conflated **engine code path** with **library
primitive invocation** — those are different things. The Explore agent
did not verify that the engine wrapper at `engine/techniques/<technique>.py`
invokes library X at the same abstraction layer (or invokes library X
at all). Three failure modes:

1. Engine implements different algorithm than harness helper
   (e.g. `p3_conformal` pre-hygiene: engine uses `pmdarima.auto_arima`
   base forecaster; harness helper used naive last-value forecaster).
2. Engine wraps library at higher abstraction layer with preprocessing /
   feature engineering pipeline (e.g. ML/DL `_fit_predict` cohort:
   engine wrapper adds lag-feature engineering + NaN handling + train/
   test split + audit_fields construction; harness helper instantiates
   library primitive directly with hardcoded hyperparameters and
   identical feature construction in both arms).
3. Engine wraps library directly with no algorithmic transformation but
   harness validates against itself (tautological self-parity at
   `p3_ssa` + `p3_wavelet_coherence` already disclosed via §4.7.A
   variant 3 sub-variant CRITICAL CAVEAT).

### §1.2 Gate 1 refinement — Cat 1c criterion + direct code inspection

Spot-check at S62 (p3_conformal) surfaced the structural defect.
Plan-mode session designed the corrected per-harness verification
methodology:

- Step A binary determination: (a) DIRECT ENGINE INVOCATION / (b)
  SHARED HELPER ENGINE INVOCATION / (c) NO ENGINE INVOCATION
- Step B sub-determination for (c) candidates: Cat 1c LEGITIMATE same-
  library self-test / Cat 2 DEGENERATE-COHERENT / Cat 3 DEGENERATE-
  VACUOUS

Gate 1 verified the criterion against `p3_pca` (substantive-work-
between-args-and-primitive criterion) — preserved S56 `p3_har_rv`
precedent by introducing Cat 1d framework.

### §1.3 Gate 2 refinement — Cat 1d framework + mandatory VSC section

Gate 2 verified 6 candidates against refined Cat 1d criterion.
`p3_pca` + `p3_intervention_analysis` surfaced as Cat 1d but with
preset-default validation-surface coverage mismatch (harness validates
config different from engine preset Balanced default).

Refined Cat 1d criterion (revision 2) — four-condition framework:

1. TSL arm inlines engine math with documented bypass rationale (e.g.
   output-rounding floor per Phase 1 finding B8)
2. Algorithm-level faithfulness to engine (same primitive + identity-
   preserving transformations)
3. Reference arm uses INDEPENDENT cross-package primitive (different
   library or self-implementation structurally distinct)
4. **Validation-Surface Coverage (VSC):** §2.5 entry MUST disclose
   whether harness validated config matches engine preset default
   config (YES/NO); NO requires explicit mismatch disclosure section

### §1.4 Cat 2D refinement — stochastic-engine sub-category (this session)

Full-enumeration dispatch surfaced 17 Cat 3 candidates (vs 1 at original
inventory). The ML/DL cohort (14 candidates) shares the `_fit_predict`
anti-pattern. Disposition introduces a triage step before remediation:

**Cat 2D DEGENERATE-COHERENT-WITH-STOCHASTIC-ENGINE:** harness helper
mirrors engine math at algorithm level (standard Cat 2 framing applies);
engine wrapper produces non-deterministic or insufficiently-reproducible
output at runtime such that math-layer parity against engine code path
is not reliably achievable.

Distinguishing criteria vs standard Cat 2:

- **Standard Cat 2** (S60/S61): engine output IS reproducible at fixed
  seed; helper-mirrors-engine-math at algorithm level; Sub-variant 3.D.
- **Cat 2D:** engine output is NOT reproducible at fixed seed (DL
  training stochasticity, GPU non-determinism, RNG state issues);
  helper-mirrors-engine-math at algorithm level under fixed seed but
  engine code path output varies run-to-run.

Cat 2D requires §2.5 disclosure section enumerating: source of non-
determinism + whether engine attempts seed control + whether
reproducibility holds at fixed seed for typical use + user advisory.

---

## §2. Full classification table

Per-harness Step A determination + Step B sub-determination for (c)
candidates. Deterministic alphabetical order within batches.

### §2.1 Step A (a) DIRECT ENGINE INVOCATION (20 harnesses)

```
technique_id              | verification rationale
p3_arima                  | run_tsl constructs RunContext + calls arima_mod.run; PRIMARY math is raw statsmodels — engine call is wrapper sanity
p3_arimax_sarimax         | run_tsl constructs RunContext + calls ax_mod.run; PRIMARY math SARIMAX(exog) direct — engine call is wrapper sanity
p3_bocpd                  | run_tsl constructs RunContext + calls bocpd_run; ref from-scratch Adams-MacKay self-parity
p3_bond_yield_forecast    | both arms call engine BVARSV.estimate() (Pattern A.1 self-parity + Pattern F invariants)
p3_byf_bvar_constant_vol  | run_tsl calls engine BVARSV(force_constant_h=True).estimate(); ref R BVAR::bvar cross-pkg
p3_byf_minnesota_dummies  | run_tsl calls engine MinnesotaPrior class + _compute_dummies directly; ref from-scratch reimpl
p3_byf_stochvol_partial   | run_tsl calls engine BVARSV.estimate(); ref R stochvol::svsample cross-pkg
p3_conformal              | post-hygiene a06646e: run_tsl calls conf_mod.run via RunContext; ref from-scratch VGS 2005 reimpl
p3_cusum_page_hinkley     | run_tsl constructs RunContext + calls engine cusum_run; ref from-scratch self-parity
p3_intermittent           | run_tsl invokes engine private helper id_mod._croston directly (engine code path executed)
p3_kalman_imputation      | run_tsl calls techniques.kalman_imputation.run via RunContext (not via _kalman_helpers); ref R KFAS cross-pkg
p3_nar_narx               | run_tsl constructs RunContext + calls nn_mod.run; ref R tsDyn::nlar cross-pkg
p3_particle_filter        | run_tsl calls techniques.particle_filter.run via RunContext; ref Python particles cross-pkg
p3_pelt                   | run_tsl constructs RunContext + calls engine pelt_run; ref direct ruptures.Pelt cross-pkg
p3_rolling_origin_cv      | post-hygiene e72d6f5+2f46381: run_tsl invokes rocv_mod.run via RunContext
p3_sarima                 | run_tsl constructs RunContext + calls sarima_mod.run; PRIMARY math SARIMAX direct — engine call is wrapper sanity
p3_star                   | run_tsl constructs RunContext + calls star_mod.run; ref R tsDyn::star cross-pkg
p3_stl_esd                | run_tsl constructs RunContext + calls stl_esd_run; ref from-scratch Rosner ESD self-parity
p3_tar_setar              | run_tsl constructs RunContext + calls ts_mod.run; ref R tsDyn::setar cross-pkg
p3_x13                    | run_tsl calls tsl_x13_run via RunContext per Phase 4 Session 2 amendment
```

**NOTE (p3_arima/sarima/arimax_sarimax):** Mechanically (a) per Step A
literal definition (`.run(ctx)` invoked); spirit-of-validation is closer
to (c) Cat 1c since the PRIMARY parity surface is raw statsmodels (engine
`.run()` return value used only for `wrapper_aic` cross-check, not parity
ladder). Inventory flag preserved: "(a) with PRIMARY-NOT-ENGINE caveat".

### §2.2 Step A (c) Step B Cat 1c LEGITIMATE same-primitive (16 harnesses)

```
technique_id              | verification rationale
p3_ccf                    | engine wraps stats.ccf; harness calls same primitive directly
p3_dfm                    | harness calls stats.DynamicFactor directly; engine wraps same; ref R MARSS cross-pkg
p3_egarch                 | _garch_helpers calls arch.arch_model directly; engine garch_model wraps same EGARCH primitive
p3_gjr_garch              | _garch_helpers calls arch.arch_model directly; engine wraps same GJR primitive
p3_granger                | engine wraps stats.grangercausalitytests at same layer; harness identical primitive
p3_hmm                    | uses hmmlearn.GaussianHMM identically to engine wrapper (Phase 1 B8 bypass-rationale)
p3_local_level            | _kalman_helpers calls stats.UC directly; engine local_level.py wraps same UC primitive
p3_local_linear_trend     | same helper pattern; engine wraps same UC(level='local linear trend') primitive
p3_markov_switching       | uses stats.MarkovRegression identically to engine; engine adds forecast helpers
p3_mstl                   | inlines stats.MSTL(periods); engine adds period inference + NaN interp (inert on clean fixture)
p3_robust_estimators      | scipy primitives direct; engine _mad/_qn_scale/_trimmed_mean identical scipy formulas
p3_sgarch                 | _garch_helpers calls arch.arch_model directly; engine wraps same symmetric GARCH primitive
p3_structural_ts          | _kalman_helpers calls stats.UC directly; engine wraps same UC primitive with seasonal=m
p3_theta                  | inlines stats.ThetaModel(period, deseasonalize=True); engine default same
p3_var                    | harness calls stats.VAR directly; engine wraps same; ref R vars::VAR cross-pkg
p3_vecm                   | harness calls stats.VECM directly; engine wraps same; ref R urca::ca.jo cross-pkg
```

**STRUCTURAL FINDING:** `_kalman_helpers.fit_uc_model` and
`_garch_helpers.run_tsl_garch` do NOT invoke engine `techniques.*.run`
— they call backbone library (statsmodels UC / arch.arch_model)
directly. All prior "Cat 1b SHARED HELPER ENGINE" classifications
downgrade to (c) Cat 1c. Math equivalence at validation surface
preserved (engine wraps same primitive at same layer); engine adds only
output rounding (Phase 1 finding B8). Helper math = engine math at the
parity surface.

### §2.3 Step A (c) Step B Cat 1d LEGITIMATE bypass-with-rationale (12 harnesses)

```
technique_id              | VSC | verification rationale
p3_adf                    | Y   | calls stats.adfuller directly; engine adds NaN/Schwert/triage preproc; ref R urca::ur.df independent
p3_denton_chowlin         | N   | inlines PFD via x/z parameterization; engine preset method="chowlin"; ref R denton-cholette
p3_emd_hht                | N   | inlines engine's numpy EMD fallback path only (not preferred emd-package path); ref PyEMD independent
p3_ets                    | N   | inlines stats.ExponentialSmoothing(AAA, damped=False); engine Balanced preset varies trend/damped/boxcox
p3_fft_spectrum           | Y   | calls scipy.fft directly; engine adds window/peak/top-N downstream; ref numpy.fft independent
p3_har_rv                 | Y   | inlines np.linalg.lstsq + Corsi 2009 regressor construction; ref R lm() independent
p3_intervention_analysis  | N   | SARIMAX trend='n' enforce_*=False; engine ARIMA wrapper default trend='c' enforce_*=True
p3_kpss                   | Y   | calls stats.kpss directly; engine adds NaN/allowlist preproc; ref R urca::ur.kpss independent
p3_lomb_scargle           | N   | scipy.signal.lombscargle direct; ref astropy.LombScargle different normalization
p3_pp                     | Y   | calls arch.PhillipsPerron; engine multi-backend dispatcher; ref R urca::ur.pp independent
p3_stl                    | N   | inlines stats.STL(robust=F, inner=2, outer=0); engine Balanced robust=T, inner=5, outer=2
p3_tbats                  | N   | inlines tbats.TBATS(use_box_cox=F, use_arma_errors=F); engine Balanced uses None/None auto-select
```

VSC=Y count: 5 — `p3_adf`, `p3_fft_spectrum`, `p3_har_rv`, `p3_kpss`, `p3_pp`
VSC=N count: 7 — all others above

### §2.4 Step A (c) Step B Cat 2 DEGENERATE-COHERENT (8 harnesses)

Standard Cat 2 (reproducible engine; helper-mirrors-engine-math algorithm-
level identity; Sub-variant 3.D framing):

```
technique_id              | verification rationale
p3_block_bootstrap        | engine Andrews-corrected auto block-length; harness fixed block_len reduced ACF1 (S61)
p3_classical_decompose    | inlines stats.seasonal_decompose(extrapolate_trend=0); engine uses "freq" boundary handling
p3_forecast_combination   | engine 3 combos + ARIMA+ETS+Theta bases + holdout weights; harness pure inv-MSE (S60)
p3_gcc_phat               | engine n_peaks/interp_factor/bootstrap preset + 4 weighting variants; harness PHAT-only
p3_periodogram            | engine adds NaN drop + preset param resolution before scipy.signal.periodogram
p3_ssa                    | tautological self-parity (both arms call same _ssa_reference); §2.5 S40 already discloses
p3_wavelet_coherence      | tautological self-parity (both arms call same _wavelet_coherence_reference); §2.5 S42 already discloses
p3_wavelet_transform      | engine adds NaN interpolation + preset-based level resolution
```

**Reclassification disposition for p3_ssa + p3_wavelet_coherence:**
Per ratified Option 1 PRESERVE disposition this session — existing §4.7.A
PRESENT variant 3 degenerate-dual-arm-self-parity sub-variant framing at
S40 + S42 is institutionally equivalent to Sub-variant 3.D framing at
S60/S61 (both document degenerate dual-arm + algorithm-level identity +
explicit acknowledgment engine code path NOT exercised). Both reclassified
Cat 2 DEGENERATE-COHERENT at inventory scope; existing §2.5 entries get
wrapper-layer 3-check addition + cross-reference note (Tier 1 forward-
amendment).

### §2.5 Step A (c) Step B Cat 3 candidates pre-triage (17 harnesses)

Per ratified Option 3 disposition this session — triage session will
classify each into genuine Cat 3 (rewrite feasible) vs Cat 2D (stochastic
engine, no rewrite).

```
technique_id              | pre-triage flag | verification rationale
p3_autoencoder            | Cat 2D candidate | engine window_size + 20-80 epochs PyTorch AE + sklearn PCA fallback; harness 5 epochs MLP AE
p3_dtw                    | Cat 3 candidate  | harness basic DP squared-cost DTW; engine has configurable window/normalization/step pattern
p3_esn                    | ambiguous        | engine manual-numpy reservoir + sparsity + warmup + 100-500 reservoir preset; harness 50-unit single
p3_gp                     | ambiguous        | engine sklearn n_restarts/max_train/alpha preset + kernel-type + CI; harness fixed RBF+White 2 restarts
p3_gradient_boosting      | Cat 3 candidate  | engine _PRESET_CONFIG + _prepare_series + rolling-mean/std features; harness only lag features
p3_lightgbm               | Cat 3 candidate  | engine preset + NaN + rolling + fallback; harness raw LGBMRegressor + n_lags only
p3_loess                  | Cat 3 candidate  | harness validates stats.lowess smoothing; engine is fundamentally NaN-imputation w/ rolling-window iter
p3_lstm_gru               | Cat 2D candidate | engine PyTorch LSTM + Fast→sklearn-MLP fallback + 50/100/300 epochs preset; harness 5 epochs 1-layer
p3_nbeats                 | Cat 2D candidate | engine trend/seasonality/generic stacks PyTorch + 50-500 epochs + sklearn fallback; harness 3 epochs generic
p3_nhits                  | Cat 2D candidate | engine n_stacks/n_blocks/pooling PyTorch + 50-150 epochs + sklearn fallback; harness 3 epochs hardcoded
p3_prophet                | ambiguous        | engine seasonal-naive fallback + changepoint_prior preset + freq inference; harness raw Prophet()
p3_quantile_regression    | Cat 3 candidate  | engine 5+ quantiles preset + NaN + rolling features; harness 3-quantile + 6-lag only
p3_random_forest          | Cat 3 candidate  | engine preset-resolution + NaN + rolling stats + diff + time features; harness raw RFRegressor n_lags only
p3_svr                    | Cat 3 candidate  | engine preset + NaN + rolling + recursive multi-step; harness scaler + 6-lag SVR
p3_tcn                    | Cat 2D candidate | engine PyTorch TCN + n_channels preset + variable kernel + 50-300 epochs + MLP fallback; harness 5 epochs 2-layer
p3_transfer_function      | Cat 3 candidate  | harness plain 3-lag OLS; engine adds AR(r)-noise + Almon polynomial options
p3_xgboost                | Cat 3 candidate  | engine preset + NaN + rolling + xgboost→GBR fallback; harness raw XGBRegressor n_lags only
```

Pre-triage breakdown:

- Cat 2D candidates (5 confirmed DL-family): `p3_autoencoder`, `p3_lstm_gru`, `p3_nbeats`, `p3_nhits`, `p3_tcn`
- Cat 3 candidates (9 deterministic-likely): `p3_dtw`, `p3_gradient_boosting`, `p3_lightgbm`, `p3_loess`, `p3_quantile_regression`, `p3_random_forest`, `p3_svr`, `p3_transfer_function`, `p3_xgboost`
- Ambiguous (3 — triage will classify): `p3_esn` (numpy reservoir likely deterministic at seed; closed-form readout), `p3_gp` (sklearn typically deterministic at random_state), `p3_prophet` (Stan optimization mostly deterministic at fixed seed when mcmc_samples=0)

---

## §3. Per-category counts

| Category | Count | % of 73 | Prior post-S62 claim | Delta |
|---|---|---|---|---|
| (a) DIRECT ENGINE INVOCATION | 20 | 27% | (folded) | — |
| (c) Cat 1c LEGITIMATE same-primitive | 16 | 22% | (folded) | — |
| (c) Cat 1d LEGITIMATE bypass-rationale | 12 | 16% | (folded) | — |
| **LEGITIMATE total (1a+1c+1d)** | **48** | **66%** | 95% | **−29 pp** |
| (c) Cat 2 DEGENERATE-COHERENT | 8 | 11% | 3% | +8 pp |
| (c) Cat 3 candidates pre-triage | 17 | 23% | 3% | +20 pp |
| ↳ Cat 2D candidates (DL-family pre-triage) | 5 | 7% | — | new |
| ↳ Cat 3 candidates (deterministic pre-triage) | 9 | 12% | — | new |
| ↳ ambiguous (triage will classify) | 3 | 4% | — | new |
| **Total enumerated** | **73** | 100% | 71 reported | +2 (post-hygiene rewrites) |

Vs original Explore-agent reported 96/3/1 distribution: empirical defect
rate at same-library-helper-only-harness scope is **~23× higher** than
original methodology surfaced (23% vs 1%). Materially significant
correction for any downstream institutional consumers of the original
inventory.

---

## §4. Forward-amendment scope enumeration

### §4.1 Tier 1 IMMEDIATE BULK (single session, ~3-4 hours, post-this-commit)

Scope: 5 entries, all documentation/wrapper-layer additions with no
dependency on Cat 3 harness rewrites.

| Entry | Required amendment | Est. LOC |
|---|---|---|
| S26 denton_chowlin_disaggregation | VSC section addition (VSC=N: engine preset method="chowlin"; harness validates denton) | ~30 LOC |
| S39 lomb_scargle | VSC section addition (VSC=N: astropy normalization differs from scipy) | ~30 LOC |
| S40 ssa | Wrapper-layer 3-check addition per S49+ protocol; Sub-variant 3.D cross-reference note | ~60 LOC |
| S42 wavelet_coherence_phase_lag | Wrapper-layer 3-check addition per S49+ protocol; Sub-variant 3.D cross-reference note | ~60 LOC |
| S56 har_rv | VSC section addition (VSC=Y: harness daily=1, weekly=5, monthly=22 matches engine lines 130-136) | ~30 LOC |

Tier 1 commit prefix: `audit-hygiene:`
Single commit covering all five entries; institutional rationale per
ratified disposition: all are mechanical additions, no remediation
dependency, unblocks immediately after this inventory verification
commit lands.

### §4.2 Tier 2 INCREMENTAL (paired with each Cat 3 remediation session)

Scope (post-triage):

| Entry | Required amendment | Pairing |
|---|---|---|
| S17 dtw_alignment_lag | Forward-amendment to corrected harness verdict | Paired with p3_dtw rewrite session |
| S27 loess_interpolation | Forward-amendment to corrected harness verdict | Paired with p3_loess rewrite session |
| (additional triage-pending) | TBD | TBD |

Per-session pattern matches p3_conformal hygiene precedent at commits
e72d6f5 + 2f46381: harness rewrite + compare()-rounding alignment +
runner CLI verification + §2.5 entry forward-amendment all in one
session/commit (not separate commits).

### §4.3 NOT IN SCOPE for forward-amendment (existing §2.5 entries preserved)

The following §2.5 entries are confirmed Cat 1c or Cat 1a per refined
methodology and require NO amendment:

- S12 granger_causality (Cat 1c via stats.grangercausalitytests)
- S13/S14c/S15 ccf-family triple (Cat 1c via stats.ccf)
- S18 gcc_phat_delay (Cat 2 standard; existing §4.7.A variant 3
  framing equivalent to Sub-variant 3.D — but already at single-layer
  framing scope; preserve as-is)
- S21/S22/S23 stationarity tests triple (Cat 1d VSC=Y per §2.3 — but
  S21/S22/S23 are existing entries; VSC sections may be useful to add
  but ratified disposition explicitly lists only S26/S39/S56 for Tier
  1; treat S21-S23 as optional future-tier amendment, NOT this cycle)
- S48/S49/S50/S51 State Space block (Cat 1c via _kalman_helpers
  downgrade per structural finding §2.2)
- S53/S54/S55 GARCH-family triple (Cat 1c via _garch_helpers
  downgrade per structural finding §2.2)
- S57 har_cj (paper-formula self-parity per Tier IV; preserved)
- S58 robust_estimators (Cat 1c per §2.2; preserved)
- S59 rolling_origin_cv (post-hygiene Cat 1a; preserved)
- S60 forecast_combination (Cat 2 Sub-variant 3.D; preserved per S60)
- S61 block_bootstrap (Cat 2 Sub-variant 3.D; preserved per S61)

S62 conformal_intervals §2.5 entry remains pending — will be authored
against post-hygiene corrected harness (`p3_conformal.py` at commit
a06646e) as final step before Q1 cadence resumption.

---

## §5. Cat 2D candidates (pre-triage)

Per ratified Option 3 disposition this session — triage session will
classify these 5 confirmed + 3 ambiguous candidates into genuine Cat 3
(rewrite feasible) vs Cat 2D (stochastic engine, no rewrite required;
Cat 2D framing with stochasticity disclosure section in §2.5 entry).

### §5.1 Triage workflow specification

Per-harness:

1. Set fixed seed: `numpy.random.seed(42)` + `torch.manual_seed(42)`
   if PyTorch + `python random.seed(42)` + any technique-specific seed
   mechanism (`torch.cuda.manual_seed` if GPU; `torch.use_deterministic_
   algorithms(True)` if available)
2. Construct RunContext with fixture series + default Balanced preset
   config + `ctx.seed=42`
3. Invoke `engine.techniques.<technique>.run(ctx, _noop_progress)`
   twice with identical context; capture both outputs
4. Compare across two runs:
   - `max_abs_diff < 1e-10` → engine deterministic at fixed seed
   - `max_abs_diff < 1e-2` → engine convergence-precision deterministic
   - `max_abs_diff > 1e-2` → engine non-deterministic
5. Classify per outcome:
   - bit-exact or mle-band → GENUINE Cat 3 (queue for remediation)
   - stochastic → Cat 2D (no rewrite; Cat 2D framing applies)

### §5.2 Candidate list

```
technique_id          | pre-triage flag  | rationale for flagging
p3_autoencoder        | Cat 2D candidate | PyTorch training stochasticity (Adam optimizer + dropout + random init)
p3_esn                | ambiguous        | numpy-only reservoir init seedable; closed-form least-squares readout deterministic
p3_gp                 | ambiguous        | sklearn GP typically deterministic at random_state; multi-start optimization may vary
p3_lstm_gru           | Cat 2D candidate | PyTorch LSTM training stochasticity (Adam + dropout + random init)
p3_nbeats             | Cat 2D candidate | PyTorch NBEATS training stochasticity
p3_nhits              | Cat 2D candidate | PyTorch NHITS training stochasticity
p3_prophet            | ambiguous        | Stan optimization mostly deterministic at fixed seed when mcmc_samples=0; may vary at MCMC mode
p3_tcn                | Cat 2D candidate | PyTorch TCN training stochasticity
```

Post-triage outputs will be appended to this artifact OR committed as a
separate triage-close artifact (Code call at triage session close).

---

## §6. Institutional findings summary

### §6.1 Empirical defect rate correction

Original Explore-agent inventory at commit `e72d6f5` reported 1%
Category 3 defect rate. Refined methodology revision-2 enumeration
reveals **23% Cat 3 candidate rate** (17 of 73 harnesses) pre-triage.
Triage will partition into genuine Cat 3 (rewrite required) vs Cat 2D
(stochastic engine; documented limitation). Cat 2 standard rate
corrected from 3% → 11% (8 of 73).

Empirical LEGITIMATE rate corrected from 96% → 66% (48 of 73). This is
materially significant and downgrades the institutional reliability
claim attached to the original inventory.

### §6.2 Methodology refinement across three iterations

1. **Original (e72d6f5):** file-pattern grouping; classified
   `_fit_predict` cohort as LEGITIMATE without verifying engine
   abstraction layer.
2. **Gate 1 (this plan):** Cat 1c criterion + direct code inspection
   per harness; substantive-work-between-args-and-primitive criterion
   to distinguish Cat 1c from Cat 2.
3. **Gate 2 (this plan):** Cat 1d framework + mandatory VSC section
   for preset-default validation-surface coverage disclosure;
   four-condition criterion (revision 2).
4. **Full-enumeration dispatch (this session):** Cat 2D
   DEGENERATE-COHERENT-WITH-STOCHASTIC-ENGINE sub-category added to
   capture DL-cohort where engine non-determinism precludes math-layer
   parity validation.

### §6.3 Audit infrastructure reliability post-correction

Depends on Cat 3 remediation outcome (calendar ~2-3 weeks pending):

- Tier 1 bulk session: ~3-4 hours (immediate post-this-commit)
- Triage session: ~3-4 hours (classifies 8 Cat 2D candidates +
  9 confirmed Cat 3 candidates)
- Genuine Cat 3 remediations: count × ~1-2 hours each
  (estimated 8-12 sessions; ~12-24 hours)
- Bulk forward-amendment session for residual: ~2-3 hours
- S62 re-execution: ~1-2 hours
- Total post-inventory-verification: ~20-35 hours focused;
  ~2-3 weeks calendar at part-time pace

### §6.4 BEFORE / AFTER state institutional argument

This artifact serves as BEFORE record for inventory state. Subsequent
forward-amendment + remediation commits produce AFTER record.

Forward-cross-reference cycle:

1. THIS commit (inventory verification BEFORE record)
2. Tier 1 bulk session commit (5 entries amended)
3. Triage session commit (8 candidates classified Cat 3 / Cat 2D)
4. Per Cat 3 remediation cycle (~8-12 sessions): each commit pairs
   harness rewrite + §2.5 entry forward-amendment
5. S62 re-execution commit (conformal_intervals §2.5 entry against
   post-hygiene corrected harness)
6. Future inventory verification re-execution (audit-hygiene cycle
   close) — final AFTER state record vs this BEFORE record

---

## §7. Cross-references

- **Original inventory:** commit `e72d6f5` (audit-hygiene: p3_*
  harness-structure inventory + p3_rolling_origin_cv Category 3
  rewrite) + commit `2f46381` (4-decimal output-rounding alignment)
- **p3_conformal hygiene:** commit `a06646e` (audit-hygiene:
  p3_conformal Category 3 DEGENERATE-VACUOUS rewrite)
- **Plan-mode methodology:**
  `C:\Users\matth\.claude\plans\glistening-wishing-mountain.md`
- **Phase 1 finding B8:** engine `round(val, N)` at table
  serialization caps parity at display precision; REF rounding
  required to match — applies across Cat 1d entries with engine
  output-rounding floor
- **S60/S61 Sub-variant 3.D precedent:** existing Cat 2 §2.5 entries
  applying §4.7.A Sub-variant 3.D DEGENERATE DUAL-ARM framing —
  institutionally equivalent to S40/S42 §4.7.A variant 3 framing
- **S49+ wrapper-layer 3-check protocol:** NaN handling + preset
  config + output shape/type verification — required for Cat 2 / Cat
  2D entries to exercise engine code execution path that math-layer
  harness does not under degenerate dual-arm framing

---

**END OF ARTIFACT.** Forward state: Tier 1 bulk session next, then
triage session, then Cat 3 remediation cycle, then S62 re-execution.
Q1 audit cadence resumes at final remediation + S62 entry close.
