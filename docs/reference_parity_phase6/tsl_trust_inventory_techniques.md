# TSL trust inventory — techniques (Option γ scope: 9 validated wrappers + BYF + 75 unvalidated enumeration)

**Date:** 2026-05-10
**Master HEAD at authoring:** `6e5d32b`
**Scope:** Option γ per Phase 6+ S8 Chat ratification — direct
UDFs (deferred to subsequent sub-sessions) + technique catalog
entries with reference-parity validation evidence (this document).
**Class:** trust-infrastructure documentation (NEW class for
Phase 6+; first instance produces empirical baseline; §19.4 A4
amendment candidate informational).

## §1 Document framing

This document inventories the **TSL technique catalog** (84
entries at `resources/catalog/techniques_catalog.json`) from
the perspective of **reference-parity validation evidence**.
Techniques accessible from Excel via `TSL_RUN_THR(technique_id,
…)` (the THOROUGH orchestration UDF; documentation deferred to
Phase 6+ S9+ infrastructure category).

**Scope this document covers:**
- 9 catalog techniques with reference-parity validation
  evidence (§2; full Phase 1 + extractable Phase 2 + explicit
  gap markings)
- 12 catalog techniques with Phase 7+ Q1 trust documentation
  remediation (§2.5; Tier-characterization + disclosure
  templates + validation provenance audit checklist;
  post-Phase-7+-S12+S13+S14c+S15+S17+S18+S21+S22+S23+S26+S27+S28 amendments)
- 63 catalog techniques without reference-parity validation
  (§3; ID-only enumeration with explicit status framing)

**Scope this document does NOT cover:**
- 15 Excel-callable UDFs (`TSL_VERSION`, `TSL_SEASONAL_ADJUST`,
  `TSL_GRANGER`, `TSL_LAG_FIND`, `TSL_ADF`, `TSL_KPSS`,
  `TSL_FORECAST`, `TSL_TRIGGER`, `TSL_RUN_THR`,
  `TSL_FORECAST_THR`, `TSL_TABLE`, `TSL_VALUE`, `TSL_STATUS`,
  `TSL_WARNINGS`, `TSL_RUNINFO`) — direct UDF inventory
  deferred to Phase 6+ S9+ subsequent sub-sessions per Chat
  ratification pause-and-review protocol
- Trust content for unvalidated techniques (§3 enumeration only;
  per-technique trust documentation requires expert review
  and/or extending reference-parity coverage)

**Empirical state correction (A2 verify-state-at-activation
protocol third operational application):** Pre-flight
enumeration estimated 67 catalog techniques per CLAUDE.md
memory. Empirical catalog at activation: **84 techniques**.
Unvalidated count corrected from pre-flight 58 to **75**.
Pattern of stale-banking-vs-empirical-state continues to recur
per A2 graduation observation.

**EXPLICIT FABRICATION PROHIBITION (per trigger):** §2 Phase 2
content is extracted from wrapper docstrings + Phase 5/Phase 6+
banking entries + parity report references. When content is
not in artifacts, **explicit gap marking** ("requires expert
review of underlying technique") is used in place of
generated content. The strategist publishing under their name
cannot independently distinguish authoritative knowledge from
fabricated trust content; honest gaps are institutional safety.

## §2 Reference-parity-validated techniques (9 entries)

### kalman_filter + kalman_smoother (parity wrapper 2a_kalman_filter_smoother)

- **Catalog IDs:** `kalman_filter` + `kalman_smoother` (2 entries; covered together)
- **Excel access:** `TSL_RUN_THR("kalman_filter", …)` or `TSL_RUN_THR("kalman_smoother", …)`
- **Invariant class:** closed-form deterministic
- **Reference parity status:** VALIDATED (dual reference: R `dlm` + R `KFAS`); 8-wrapper allowlist member
- **Source files:** `tools/reference_parity/harness/checks/kalman_filter.py`; engine path via `statsmodels.tsa.statespace.structural.UnobservedComponents` (local_level template)

**Phase 2 algorithmic basis (extracted from wrapper docstring):**
Closed-form Kalman recursions on linear-Gaussian state-space
models; filtered/smoothed states, log-likelihood, steady-state
Kalman gain. TSL invokes statsmodels UnobservedComponents
directly with same parameters TSL's wrapper uses internally on
the local_level template path.

**Phase 2 known failure modes (extracted):**
- R dlm uses large-variance approximation for diffuse prior →
  known methodology offset on log-likelihood (~9 absolute
  vs TSL); detection-only at 15.0 abs tolerance
- KFAS implements same Koopman-Durbin convention as TSL/
  statsmodels → tight parity at 1e-6 absolute (Phase 1 audit
  baseline 3.64e-7)

**Phase 2 boundary of validity (extracted):**
- Linear-Gaussian state-space models (local-level template
  validated; broader UCM specifications NOT in parity scope)
- T=200 main fixture + T=100 Phase 1 fixture (smaller T not
  validated)

**Phase 2 gap markings:** Non-linear state-space models, non-
Gaussian observation noise, multivariate state-space, custom
UCM specifications beyond local_level template — **requires
expert review of underlying technique for use beyond validated
scope.**

### johansen_cointegration (parity wrapper 3d_johansen_bartlett)

- **Catalog ID:** `johansen_cointegration`
- **Excel access:** `TSL_RUN_THR("johansen_cointegration", …)`
- **Invariant class:** closed-form deterministic (rank invariant strict integer match)
- **Reference parity status:** VALIDATED (triple reference: R `urca::ca.jo` + Python `statsmodels.coint_johansen` + TSL); 8-wrapper allowlist member
- **Source files:** `tools/reference_parity/harness/checks/johansen_bartlett.py`; engine path `statsmodels.tsa.vector_ar.vecm.coint_johansen` with Reimers 1992 Bartlett correction

**Phase 2 algorithmic basis (extracted):** Closed-form
generalized eigenvalue problem on residual covariance; Reimers
correction `(T-n*p)/T` pure arithmetic.

**Phase 2 known failure modes (extracted):**
- Cross-package divergence between urca and statsmodels: 10-30%
  on small T documented Phase 1 finding; reduced-rank-regression
  parameterization differences (Pattern J at 50.0 abs)
- Critical-value comparison SKIPPED at parity test: methodology
  choice between Osterwald-Lenum (statsmodels) and urca tables;
  not a TSL correctness question

**Phase 2 boundary of validity (extracted):** T sufficient for
trace statistic stability; cointegration rank determined via
Johansen procedure with Bartlett correction.

**Phase 2 gap markings:** Critical-value tables not validated;
small-T behavior beyond fixture scope; **requires expert review
for cointegration rank determination at small T or non-standard
deterministic-trend specifications.**

### evt_pot_gpd (parity wrapper 3c_evt_ferro_segers; extremal index sub-component) — Tier 1b (sub-component validation only)

- **Catalog ID:** `evt_pot_gpd`
- **Excel access:** `TSL_RUN_THR("evt_pot_gpd", …)`
- **Invariant class:** closed-form deterministic
- **Reference parity status:** VALIDATED for extremal index sub-component (Ferro-Segers 2003 intervals estimator); R `extRemes::extremalindex(method='intervals')`; 8-wrapper allowlist member; **§4 Tier 1b — sub-component validation only**
- **Source files:** `tools/reference_parity/harness/checks/evt_ferro_segers.py`; engine `evt_pot_gpd.py:_ferro_segers_extremal_index`

**Phase 2 algorithmic basis (extracted):** Ferro-Segers 2003
intervals estimator; closed-form given inter-exceedance times.
Branch selection: `max(T_i) <= 2` → T_i_form; `> 2` →
(T_i-1)(T_i-2)_form.

**Phase 2 known failure modes (extracted):** Phase 1 audit 3c
baseline 0.000e+00 absolute diff (bitwise) on GARCH + iid
fixtures; threshold computation held constant outside parity
test (97.5th percentile of absolute returns/data passed to both
implementations).

**Phase 2 boundary of validity (extracted):** Theta in [0, 1]
structural; tolerance 0.01 absolute slack outside [0, 1] for
numerical noise; threshold-sensitivity NOT tested at parity
layer.

**Phase 2 gap markings:** Threshold choice (97.5th percentile
default) not validated for sensitivity; POT/GPD parameter
estimation (peaks-over-threshold tail fitting) NOT covered by
this parity wrapper — only the extremal index sub-component;
**requires expert review for threshold selection and POT/GPD
tail-parameter inference.**

### stochastic_volatility (Gaussian variant; parity wrapper 2b_mcmc_sv_gaussian)

- **Catalog ID:** `stochastic_volatility` (gaussian innovations variant)
- **Excel access:** `TSL_RUN_THR("stochastic_volatility", innovations="gaussian", …)`
- **Invariant class:** MCMC stochastic
- **Reference parity status:** VALIDATED (R `stochvol::svsample`); 8-wrapper allowlist member; **parameter-aware exclusion mechanism active per Phase 6+ S1** (sigma_eta non-gating)
- **Source files:** `tools/reference_parity/harness/checks/mcmc_sv_gaussian.py`; engine `engine/techniques/stochastic_volatility.py` + `_sv_mcmc.py` (Kim-Shephard-Chib Gibbs branch forced via B6 monkey-patch)

**Phase 2 algorithmic basis (extracted):** Kim-Shephard-Chib
Gibbs sampler (forced via B6 g++-probe monkey-patch);
mathematically equivalent to NUTS for parity purposes per Phase
4 S6 design rationale. **"Parity purposes" here means TSL's
Gibbs vs R stochvol's Gibbs comparison** — the equivalence
claim is parity-scoped (same algorithm both sides), NOT a
general claim that Gibbs and NUTS are interchangeable in
production inference.

**Phase 2 known failure modes (extracted from S1 banking +
docstrings):**
- sigma_eta posterior exhibits lag-1 autocorrelation ~0.98
  (pathological mixing); ess_min ~28-33 typical at engine
  default chain length (well below 200 threshold; non-gating
  per Phase 6+ S1 mechanism)
- Phase 1 audit 2b documented prior-divergence-driven sigma_eta
  rel_diff up to 45%; recorded as diagnostic, not gating
- mu/phi parameters mix well at engine default chain length

**Phase 2 boundary of validity (extracted):** T=500 fixture;
default engine chain length; mu/phi gate omnibus per parity-
side `ess_min_check.gates_outcome_for=["mu", "phi"]`;
sigma_eta breach non-gating per non_gating_params=("sigma_eta",).

**Phase 2 empirical evidence:** Phase 6+ S1 + S1-FU parity-slow
run `25606689820` confirmed PASS via sigma_eta exclusion (ess_min=28.5,
ess_min_param=sigma_eta).

**Phase 2 gap markings:** NUTS branch not tested in fast-tier
(g++ availability dependent); chain length sufficient ONLY when
sigma_eta non-gating applies (mu/phi mix well); non-T=500
fixtures not validated; **requires expert review for chain
length sufficiency on application-specific data.**

### stochastic_volatility (Student-t variant; parity wrapper 2c_mcmc_sv_student_t)

- **Catalog ID:** `stochastic_volatility` (student_t innovations variant)
- **Excel access:** `TSL_RUN_THR("stochastic_volatility", innovations="student_t", …)`
- **Invariant class:** MCMC stochastic
- **Reference parity status:** VALIDATED (R `stochvol::svtsample`); 8-wrapper allowlist member; **parameter-aware exclusion mechanism active per Phase 6+ S1 + S1-FU** (sigma_eta + nu non-gating)
- **Source files:** `tools/reference_parity/harness/checks/mcmc_sv_student_t.py`; engine same as Gaussian variant + Student-t innovations branch

**Phase 2 algorithmic basis (extracted):** Same as Gaussian
variant + Student-t innovations specification; nu (degrees of
freedom) parameter additional.

**Phase 2 known failure modes (extracted from S1-FU banking +
docstrings):**
- sigma_eta + nu posteriors prior-divergence-driven; expected
  to mix less efficiently under Gibbs
- Phase 1 audit 2c documented nu prior-parameterization
  divergence: TSL TruncatedNormal vs stochvol Exponential rate
  prior produces ~13% nu rel_diff (classified as methodology,
  not bug)
- nu ess breach empirically observed at parity-slow run
  `25605525820` (ess_min=33.4, ess_min_param=nu); resolved via
  Phase 6+ S1-FU non_gating_params extension

**Phase 2 boundary of validity (extracted):** T=500 fixture;
default engine chain length; mu/phi gate omnibus; sigma_eta + nu
breaches non-gating per non_gating_params=("sigma_eta", "nu").

**Phase 2 empirical evidence:** Phase 6+ S1-FU parity-slow run
`25606689820` confirmed PASS via sigma_eta + nu exclusion;
caveat-reroll protocol active (first run CAVEAT, retry seed+1
PASS observed).

**Phase 2 gap markings:** Same as Gaussian variant; **requires
expert review for nu prior choice on application-specific data.**

### forecast_reconciliation (parity wrapper 3e_mint_family)

- **Catalog ID:** `forecast_reconciliation`
- **Excel access:** `TSL_RUN_THR("forecast_reconciliation", method=…, …)` (4 methods: ols, wls_variance, mint_shrinkage, mint_sample)
- **Invariant class:** closed-form deterministic (mint_coherence at 1e-10 floor)
- **Reference parity status:** VALIDATED (R `hts` primary + Python `hierarchicalforecast` secondary); 8-wrapper allowlist member
- **Source files:** `tools/reference_parity/harness/checks/mint_family.py`; engine `engine/techniques/forecast_reconciliation.py`

**Phase 2 algorithmic basis (extracted):** Closed-form matrix
algebra `y_tilde = S (S' W^-1 S)^-1 S' W^-1 y_hat` with 4 W
variants. Method-name mapping: TSL ols ↔ hts ols ↔ HF ols; TSL
wls_variance ↔ hts wls ↔ HF wls_var; TSL mint_shrinkage ↔ hts
shrink ↔ HF mint_shrink; TSL mint_sample ↔ hts sam ↔ HF
mint_cov.

**Phase 2 known failure modes (extracted):** hts 6.0.3
`combinef()` and `MinT()` broken on platform ("non-conformable
arguments" in cbind.Matrix internals) — workaround in parity
wrapper implements MinT math manually using `smatrix()` +
`hts:::shrink.estim`. Closed-form-safe MinT produces L2 = 0.0
exactly on real fixture (well within tolerance=1e-10).

**Phase 2 boundary of validity (extracted):** Phase 1 audit 3e
baseline max abs diff 4.66e-15 on mint_shrinkage vs hts; harness
asserts at 1e-8 (7 orders of magnitude headroom). 2-level
synthetic hierarchy fixture only.

**Phase 2 gap markings:** Hierarchical structures beyond 2-level
synthetic fixture not tested; reconciliation methods other than
the 4 covered (ols/wls_variance/mint_shrinkage/mint_sample) not
in parity scope; **requires expert review for hierarchies
larger than 2 levels or non-standard summing matrices.**

### transformer_forecast (attention-capture sub-component; parity wrapper 3f_transformer_attention) — Tier 1b (sub-component validation only)

- **Catalog ID:** `transformer_forecast` (attention-capture sub-component only)
- **Excel access:** `TSL_RUN_THR("transformer_forecast", …)` (full forecast pipeline)
- **Invariant class:** closed-form deterministic (attention_normalization at 1e-12 bit-exact floor)
- **Reference parity status:** VALIDATED for attention-capture mechanism only (PyTorch native MHA); 8-wrapper allowlist member; **§4 Tier 1b — sub-component validation only**
- **Source files:** `tools/reference_parity/harness/checks/transformer_attention.py`; engine `engine/techniques/transformer_forecast.py` (`_patch_sa_blocks_for_capture` + no-op forward-hook mechanism)

**Phase 2 algorithmic basis (extracted):** TSL's
`_patch_sa_blocks_for_capture` + no-op forward-hook mechanism vs
PyTorch native `nn.MultiheadAttention(need_weights=True,
average_attn_weights=True)`. Bitwise-identical attention matrices
expected given identical model weights + input + architecture.

**Phase 2 known failure modes (extracted):** **Failure = TSL
production bug, NOT tolerance question** (per docstring Q2).
Strict bit-exact assertion at 1e-12 abs (8 orders of magnitude
headroom over Phase 1 baseline 0.000e+00). Bug-localization
per-layer comparison (encoder_layers loop).

**Phase 2 boundary of validity (extracted):** Identical model
weights + identical input tensor + identical encoder layer
architecture + `model.eval()` (no dropout, no training-mode
effects); small Transformer architecture validated (d_model=32,
n_heads=4, n_encoder_layers=2).

**Phase 2 gap markings:** **Attention-capture mechanism only;
full Transformer forecast pipeline (positional encoding, output
projection, training loop, hyperparameter sensitivity) NOT in
parity scope.** **Requires expert review for any production use
of transformer_forecast — the parity coverage validates a sub-
component, not the forecasting end-product.**

### caviar_quantile_dynamics (SAV variant; parity wrapper 3a_caviar_sav)

- **Catalog ID:** `caviar_quantile_dynamics` (SAV variant only)
- **Excel access:** `TSL_RUN_THR("caviar_quantile_dynamics", specification="SAV", …)`
- **Invariant class:** INVERTED tolerance (Christoffersen p-value floor; larger = better)
- **Reference parity status:** VALIDATED for SAV variant (from-scratch Python reimpl in check file + Engle-Manganelli 2004 paper structural-sign + range thresholds); 8-wrapper allowlist member
- **Source files:** `tools/reference_parity/harness/checks/caviar_sav.py` (reimpl bundled in check); engine `engine/techniques/caviar_quantile_dynamics.py`

**Phase 2 algorithmic basis (extracted):** Engle-Manganelli 2004
CAViaR-SAV specification; three-tier comparison: tier 1
recursion math given fixed beta (strict 1e-10); tier 2 loss
ratio (PASS<1.05/CAVEAT<1.10); tier 3 beta divergence
record-only.

**Phase 2 known failure modes (extracted):**
- Nelder-Mead local-optimum non-uniqueness on non-smooth
  quantile loss (Phase 1 audit B9 documented as expected
  behavior, not bug)
- TSL exposes parameters rounded to 6 decimals → recursion
  error amplifies to ~2.5e-5 in one_step_ahead_var over T=500
  (TSL output-precision limitation, not correctness issue)

**Phase 2 boundary of validity (extracted):**
- SAV specification only; non-SAV CAViaR variants out of scope
- T=500 fixture
- Persistence beta_1 in [0.70, 0.95] paper-validated range
  (Engle-Manganelli 2004 Table III observed 0.85-0.93 across
  stocks)
- Coefficient on |y_{t-1}| (beta_2) negative for left-tail VaR
  (paper observed all negative)

**Phase 2 gap markings:** Paper validation is structural-sign +
range only (1986-1999 daily stock data not in harness for
licensing reasons); **non-SAV CAViaR variants (AS, IGARCH,
adaptive) NOT validated; requires expert review for non-SAV
specifications or non-stock asset classes.**

### bond_yield_forecast (BYF; parity wrapper p3_bond_yield_forecast; DORMANT)

- **Catalog ID:** `bond_yield_forecast`
- **Excel access:** `TSL_RUN_THR("bond_yield_forecast", …)`
- **Invariant class:** MCMC stochastic (mcmc_convergence DECLARATION ONLY; declaration DORMANT — not allowlisted; not dispatched)
- **Reference parity status:** **DORMANT** — Pattern A.1 self-parity (no external R reference; bvars unavailable for R 4.5.3) + Pattern F structural invariants only; **NOT in 8-wrapper allowlist**; **mcmc_convergence declaration would BLOCK if allowlisted** (chain length insufficient per Phase 4 S9 + Phase 6+ S6 keep-dormant disposition)
- **Source files:** `tools/reference_parity/harness/checks/p3_bond_yield_forecast.py`; engine `engine/techniques/bond_yield_forecast/` (multi-module: PCA + BVAR-SV + conditioning)

**Phase 2 algorithmic basis (extracted):** Pattern A.1
reproducibility self-parity (TSL invoked twice with identical
seed → byte-identical output) + Pattern F structural invariants
(VAR companion eigenvalue stability; SV stationarity; PCA
explained-variance threshold; posterior coefficient finiteness).
**Self-parity is NOT external-reference parity** — Pattern A.1
validates determinism-given-seed (necessary precondition for
reproducibility), not correctness-against-canonical-reference;
no external R / Python implementation cross-checks BYF output.

**Phase 2 known failure modes (extracted from Phase 4 S9 + S6
banking):**
- BYF n_draws=1000 produced ess_min=7.4 (Phase 4 S9 empirical;
  catastrophically low for omnibus PASS at threshold=200)
- BYF n_draws bumped to 2000 at intervening Phase 4-5 work
  (uncross-referenced banking change); extrapolated ess_min~15-20
  still well below threshold/2=100
- Phase 6+ S1 parameter-aware exclusion mechanism does NOT
  apply to BVAR-SV parameter set (mechanism designed for SV-
  class single-variable mu/phi/sigma_eta/nu; BVAR-SV is K-var
  with K² parameters; multiple parameters likely below
  threshold simultaneously)
- **mcmc_convergence declaration kept DORMANT** per Phase 6+
  S6 keep-dormant disposition (would BLOCK if allowlisted)

**Phase 2 boundary of validity (extracted):**
- 10-maturity grid (3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y)
  + 34-maturity grid (1M-30Y; 24 inserted maturities linearly
  interpolated in maturity-years space)
- PCA explained-variance ratio: 99.91% on 10-mat, 99.92% on
  34-mat; threshold preserved at 99% per BYF-Mod-2 §2.5
- Pattern F structural invariants HOLD by construction on both
  fixtures
- Reduced chain config (n_draws=2000, n_burn=500); ~25-30s
  wall-clock end-to-end

**Phase 2 gap markings:**
- **NO external R reference parity** (bvars unavailable; BGR-2010
  / KSC-1998 / K-FS-2014 paper-formula reimpl ~1000+ LOC
  out-of-budget per Phase 3.5 audit plan)
- **NO parameter posterior parity** — only structural invariants
  + reproducibility validated; posterior means / quantiles /
  forecast distributions NOT validated against any reference
- **BVAR-SV chain-length insufficiency unresolved** — Phase 6+
  S6 keep-dormant disposition active; future activation paths
  (engine retuning to higher n_draws OR mechanism extension to
  BVAR-SV parameter set) are deferred per S6 ratification
- **Requires expert review for ANY published use** — TSL's
  bond_yield_forecast has NO external-reference parity
  validation; the strategist using BYF output should treat it
  as un-cross-validated regardless of TSL internal Pattern F
  invariants holding

## §2.5 — Phase 7+ Q1 trust documentation remediation entries

**Class context:** Per Phase 7+ S6 scope re-framing (premise correction
at §1 of `docs/reference_parity_phase7/scope_reframing_s6_banking.md`)
+ S9 amendments (tier taxonomy split + Tier I.partial introduction +
Tier VII correction + multi-map handling) + Workstream B disposition
2 artifact (`docs/reference_parity_phase7/operational_disciplines_disposition_2_banking.md`)
operational disciplines: per-technique trust documentation remediation
amends inventory entries from pre-correction premise framing to
post-correction tier-characterization-with-disclosure-templates framing.

§2.5 entries follow Workstream B §3 disclosure templates + Workstream B
§1 validation provenance audit checklist applied at technique close.
Path α expert review preparation: per-technique audit checklist
applications + disclosure templates + status documented per entry.

### granger_causality (Phase 7+ S12; first §2.5 entry; S14b refinement applied per S14a harness-vs-engine empirical findings)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2; synthesis attribution per audit Pattern A + §2 sub-class
taxonomy).

**Reference:** R `lmtest::grangertest` (lmtest 0.9.40)
**Verdict:** PASS Pattern A bit-exact
**Audit:** `tools/reference_parity/reports/p3_granger_audit.md`
**Audit date:** 2026-04-29
**f_stat abs diff:** 8.53e-14
**p_value abs diff:** 5.20e-25

**Source files (refined per S14b informational clarification):**
`tools/reference_parity/harness/checks/p3_granger.py` lines 53-69
(harness TSL arm invokes `statsmodels.tsa.stattools.grangercausalitytests`
directly on np.column_stack([y, x]) and extracts ssr_ftest result)
+ `engine/techniques/granger_causality.py` lines 9, 119, 122 (engine
module delegates to SAME `statsmodels.tsa.stattools.grangercausalitytests`
function with orchestration wrapper around it: input validation lines
49-76, NaN drop line 78, preset-based max_lag lines 93-105, multi-lag
sweep finding best by p-value lines 131-147, reverse-direction Thorough
test lines 200-220, plain English construction, audit field population)
+ `tools/reference_parity/reports/p3_granger_audit.md`

**Validation claim scope:** TSL granger_causality output bit-exact
against R `lmtest::grangertest` at single seeded fixture configuration.
Single-fixture parity established at machine precision; parameter-
sensitivity coverage NOT established at this validation tier (Q3b
extension pending). **Harness-vs-engine code path clarification (per
S14b informational refinement):** bit-exact PASS verdict applies to
`statsmodels.tsa.stattools.grangercausalitytests` (the harness TSL arm
AND the function engine module delegates to for core F-test math per
S14a empirical investigation Step 1+3). Engine module orchestration
layer (multi-lag sweep, reverse causality test in Thorough preset,
plain English construction, audit field population) NOT directly
tested by harness but inherits validity of the delegated F-test math
the orchestration consumes; engine module uses the SAME validated
statsmodels function for core computation, so the validation claim
maps cleanly from harness scope to engine module behavior. Reference
selection + tolerance specification AI-assisted with user ratification
per Phase 7+ work program; pre-Path α expert review status; expert
review pending end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique granger_causality, cross-package
> bit-exact parity validated against R `lmtest::grangertest` (lmtest
> 0.9.40) per Phase 3 audit dated 2026-04-29 (f_stat abs diff 8.53e-14).
> Pre-Path α expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique granger_causality validated per Phase 3
> reference parity infrastructure. **Reference:** R `lmtest::grangertest`
> (lmtest 0.9.40). **Verdict:** PASS Pattern A.2 bit-exact at machine
> precision; f_stat abs diff 8.53e-14, p_value abs diff 5.20e-25.
> **Audit date:** 2026-04-29. **Fixture:** seeded single-fixture
> configuration; parameter-sensitivity coverage NOT established at
> this validation tier; Q3b extension pending. Reference selection +
> tolerance specification AI-assisted with user ratification. Pre-Path
> α expert review status; expert review pending end-of-Phase-7+-work-
> program.

*Pattern (iii) Risk model documentation:*
> granger_causality validation: TSL Tier II.bit-exact. Reference: R
> `lmtest::grangertest` (lmtest 0.9.40). Audit: `tools/reference_parity/reports/p3_granger_audit.md`
> dated 2026-04-29. Verdict: PASS Pattern A.2 bit-exact at machine
> precision (f_stat abs diff 8.53e-14). Fixture: single-seeded;
> parameter-sensitivity coverage NOT established; Q3b extension scope.
> Risk attribution conditional on parameter configurations matching
> fixture-similar conditions. Pre-Path α expert review status.

*Pattern (iv) Internal use disclosure:*
> granger_causality cross-package bit-exact validated against R
> `lmtest::grangertest`; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):** Extracted/
  cited. Reference selection from MANIFEST.toml + audit report;
  tolerance bands from Phase 3 closed-form class per tolerances.py
  ladder; fixture characteristics from p3_granger_audit.md; Pattern
  classification from audit report verbatim. **S14b additional Q-A
  verification per S14a empirical investigation:** harness-vs-engine
  code path alignment confirmed at S14a Step 1+3 — harness wrapper
  (p3_granger.py lines 53-69) invokes
  `statsmodels.tsa.stattools.grangercausalitytests` directly; engine
  module (granger_causality.py lines 9, 119, 122) delegates to SAME
  function for core F-test math; clean engine-uses-same-function
  pattern (4 of 5 contextually sampled harnesses follow this
  convention).
- **Q-B (user genuine contestation vs default ratification):** Default
  ratification at first-technique selection (user ratified
  granger_causality under Tier 2 case-against framing per Phase 7+
  S12 Path 1 disposition; case-against weighted but not invalidating).
  Pro-forma elements present; not pro-forma across all upstream
  decisions for this technique.
- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes, defensible to all three audiences (published audience: bit-exact
  PASS verdict at machine precision is institutional-grade evidence;
  Morgan Stanley compliance review: precise audit citation + tier
  taxonomy + reference package version; external expert reviewer at
  Path α close: verbatim audit numerics + disclosure language
  acknowledging single-fixture limitation + Q3b extension pending).
  Confidence: yes.
- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-to-low. granger_causality typically appears as supporting
  evidence in causal-inference research; not headline-driving for
  strategic recommendations or client positioning; not typically
  referenced in public commentary at single-technique level.
  Retraction surface: limited; per-note retroactive disclosure
  correction would suffice if expert review surfaces upstream error.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; first technique to enter status per S12
ratification. **S14b refinement: framing clarified per S14a empirical
findings — harness validates `statsmodels.tsa.stattools.grangercausalitytests`
directly; engine module delegates to same function with orchestration
wrapper around it; validation claim maps cleanly from harness scope
to engine module behavior.**

### cross_correlation_lag (Phase 7+ S13; second §2.5 entry; first of p3_ccf-covered triple per Workstream B §3.3 multi-map handling; S14b layered framing amendment per S14a harness-vs-engine empirical findings)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2; synthesis attribution per audit Pattern A + §2 sub-class
taxonomy). **Important nuance (per S14b layered framing per S14a
empirical findings):** tier classification applies to the CCF math
layer validated by harness (statsmodels.tsa.stattools.ccf vs R
stats::ccf); engine module uses custom numpy CCF implementation NOT
directly validated by p3_ccf audit; bit-exact equivalence between
statsmodels.ccf and engine module custom numpy CCF plausible but NOT
empirically verified (see Validation claim scope below for layered
framing).

**Multi-map note (per Workstream B §3.3):** cross_correlation_lag is
one of 3 catalog techniques covered by shared Phase 3 wrapper p3_ccf
(covers cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag);
validation evidence per p3_ccf_audit.md applies to the
`statsmodels.tsa.stattools.ccf` computation against R `stats::ccf`
at the harness TSL arm. **Per-catalog interpretation per
technique-specific output mapping AND per-catalog code path mapping
(per S14b refinement per S14a Step 3 findings):** for
cross_correlation_lag specifically, engine module
(`engine/techniques/cross_correlation_lag.py` lines 95-121) uses
custom numpy CCF implementation (manual normalized cross-covariance
computation across lags -max_lag..+max_lag), NOT
statsmodels.tsa.stattools.ccf. The two implementations compute the
same mathematical quantity (Pearson cross-correlation across lags)
using the same formula in principle, but represent DIFFERENT code
paths with potentially different floating-point rounding behavior at
machine-precision level; bit-exact equivalence plausible but
unverified. prewhitened_ccf_lag (S14c candidate) + rolling_ccf_lag
(S15 candidate) entries pending per sequential disposition; both have
similar layered framing requirement.

**Reference:** R `stats::ccf` (base R 4.5.3)
**Verdict:** PASS Pattern A bit-exact (CCF math layer at
statsmodels.ccf; see Validation claim scope for engine module layer
coverage)
**Audit:** `tools/reference_parity/reports/p3_ccf_audit.md`
**Audit date:** 2026-04-29
**ccf_positive max abs diff:** 1.33e-15
**ccf_positive max rel diff:** 1.46e-15

**Source files (amended per S14b layered framing per S14a Step 1-3
empirical findings):** `tools/reference_parity/harness/checks/p3_ccf.py`
lines 51-59 (harness TSL arm invokes `statsmodels.tsa.stattools.ccf`
directly on input fixture; does NOT invoke engine modules)
+ `engine/techniques/cross_correlation_lag.py` lines 95-121 (engine
module computes raw CCF using custom numpy implementation: x_dm =
x_clean - np.mean(x_clean); y_dm = y_clean - np.mean(y_clean); denom
= sx*sy; ccf_vals[idx] = np.sum(x_dm[:n - k] * y_dm[k:]) / denom for
positive lags + separate branch for negative lags; computes CCF
across lags -max_lag..+max_lag whereas harness validates positive
lags 0..MAX_LAG only)
+ `engine/techniques/prewhitened_ccf_lag.py` + `engine/techniques/rolling_ccf_lag.py`
(per-catalog engine modules for other p3_ccf-covered catalog
techniques; not exercised by p3_ccf harness)
+ `tools/reference_parity/reports/p3_ccf_audit.md`

**Validation claim scope (LAYERED per S14b amendment per S14a
empirical findings):** TSL cross_correlation_lag output relies on
custom numpy CCF implementation in engine module. p3_ccf audit
validates `statsmodels.tsa.stattools.ccf` (the harness TSL arm) vs R
`stats::ccf` at single seeded fixture configuration (lagged-pair
series, T=200, true lag=3, seed=42); ccf_positive metric measures
statsmodels.ccf vs R stats::ccf agreement, NOT engine module custom
numpy CCF vs R stats::ccf agreement. **Layered framing:**
- **Layer 1 — CCF math at statsmodels.ccf:** bit-exact PASS verdict
  applies at machine precision; parity covers Pearson cross-correlation
  across positive lags 0..MAX_LAG. Lag-convention reconciliation per
  audit: statsmodels.ccf(x,y)[k] = cor(x[t+k], y[t]); R ccf(x,y) at
  lag k = same; both arms use POSITIVE lags 0..MAX_LAG; initial run
  blocked at 9% abs diff due to R lag-sign extraction error, corrected
  pre-PASS.
- **Layer 2 — engine module custom numpy CCF:** NOT empirically
  verified bit-exact against statsmodels.ccf at p3_ccf audit. Bit-exact
  equivalence plausible (same mathematical formula — normalized
  Pearson cross-correlation; same float64 arithmetic underlying), but
  requires expert review OR engine-output cross-check against
  statsmodels.ccf to close the gap empirically. Engine module also
  computes negative lags (-max_lag..0) which p3_ccf audit does NOT
  cover; negative-lag CCF validity inherits from same formula but is
  one further step removed from validated evidence.

Single-fixture parity established at machine precision for Layer 1;
parameter-sensitivity coverage NOT established at this validation
tier (Q3b extension pending); Layer 2 closure pending engine-output
cross-check OR expert review. Reference selection + tolerance
specification AI-assisted with user ratification per Phase 7+ work
program; pre-Path α expert review status; expert review pending
end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates; multi-map cross-reference per §3.3;
institutional-grade three-tier disclosure shape per S14b layered
framing):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique cross_correlation_lag. CCF math
> layer (statsmodels.tsa.stattools.ccf) is cross-package bit-exact
> parity validated against R `stats::ccf` (base R 4.5.3) per Phase 3
> audit dated 2026-04-29 (ccf_positive max abs diff 1.33e-15; shared
> p3_ccf wrapper covers cross_correlation_lag + prewhitened_ccf_lag
> + rolling_ccf_lag). TSL engine module uses custom numpy CCF
> implementation mathematically equivalent to validated math but
> not directly tested by parity audit; engine-output equivalence to
> validated statsmodels.ccf plausible but unverified; requires
> expert review or cross-check for published use. Pre-Path α expert
> review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique cross_correlation_lag validated at
> **CCF math layer** per Phase 3 reference parity infrastructure.
> **Reference:** R `stats::ccf` (base R 4.5.3). **Verdict:** PASS
> Pattern A.2 bit-exact at machine precision; ccf_positive max abs
> diff 1.33e-15, max rel diff 1.46e-15. **Audit date:** 2026-04-29.
> **Multi-map coverage:** cross_correlation_lag is one of 3 catalog
> techniques covered by shared Phase 3 wrapper p3_ccf; validation
> evidence per p3_ccf audit applies to `statsmodels.tsa.stattools.ccf`
> (the harness TSL arm) vs R `stats::ccf`; per-catalog interpretation
> per technique-specific output mapping. **Layered validation
> framing:** p3_ccf harness invokes statsmodels.ccf directly; TSL
> engine module (`engine/techniques/cross_correlation_lag.py` lines
> 95-121) uses custom numpy CCF implementation NOT directly tested
> by parity audit. Bit-exact equivalence between statsmodels.ccf and
> engine module custom numpy CCF is plausible (same Pearson
> cross-correlation formula; same float64 arithmetic) but is NOT
> empirically verified; requires expert review of engine
> implementation OR engine-output cross-check against statsmodels.ccf
> to close the gap. **Fixture:** seeded single-fixture configuration
> (lagged-pair series, T=200, true lag=3, seed=42);
> parameter-sensitivity coverage NOT established at this validation
> tier; Q3b extension pending. Reference selection + tolerance
> specification AI-assisted with user ratification. Pre-Path α
> expert review status; expert review pending end-of-Phase-7+-work-
> program.

*Pattern (iii) Risk model documentation:*
> cross_correlation_lag validation: TSL Tier II.bit-exact (CCF math
> layer at statsmodels.ccf only). Reference: R `stats::ccf` (base R
> 4.5.3). Audit: `tools/reference_parity/reports/p3_ccf_audit.md`
> dated 2026-04-29. Verdict: PASS Pattern A.2 bit-exact at machine
> precision (ccf_positive max abs diff 1.33e-15). Multi-map coverage:
> cross_correlation_lag is one of 3 catalog techniques covered by
> shared Phase 3 wrapper p3_ccf; per-catalog interpretation per
> technique-specific output mapping. **Engine module layer (custom
> numpy CCF) NOT directly parity-validated; bit-exact equivalence to
> validated statsmodels.ccf plausible but unverified.** Fixture:
> single-seeded; parameter-sensitivity coverage NOT established;
> Q3b extension scope. Risk attribution conditional on (a) parameter
> configurations matching fixture-similar conditions AND (b) engine
> module CCF implementation equivalence to validated statsmodels.ccf
> (not covered by parity audit; expert review recommended). Pre-Path
> α expert review status.

*Pattern (iv) Internal use disclosure:*
> cross_correlation_lag CCF math layer (statsmodels.ccf) cross-package
> bit-exact validated against R `stats::ccf` via shared p3_ccf
> wrapper (one of 3 catalog techniques covered); engine module
> custom numpy CCF NOT directly parity-validated, bit-exact
> equivalence plausible but unverified; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):** Extracted/
  cited. Reference selection from p3_ccf_audit.md verbatim (R
  `stats::ccf` base R 4.5.3); verdict + Pattern + date verbatim from
  audit; numeric metrics (ccf_positive max abs diff 1.33e-15 / max
  rel diff 1.46e-15) verbatim from audit. Multi-map characterization
  extracted from scope_reframing §2 lines 122-131 + Workstream B §3.3
  multi-map handling guidance (per S9 Disposition 4 codification).
  Engine path mapping (cross_correlation_lag.py separate from
  prewhitened_ccf_lag.py and rolling_ccf_lag.py) verified empirically
  via Step 0 file enumeration. **S14b layered framing extracted per
  S14a empirical investigation:** harness-vs-engine code path
  divergence verified at S14a Step 1+3 — p3_ccf.py lines 51-59
  invokes statsmodels.tsa.stattools.ccf directly;
  cross_correlation_lag.py lines 95-121 uses custom numpy CCF
  (manual normalized cross-covariance computation, NOT
  statsmodels.ccf); two implementations compute same mathematical
  quantity using same formula but represent DIFFERENT code paths.
  Layered framing (Layer 1 statsmodels.ccf validated; Layer 2
  engine module custom numpy CCF plausibly equivalent but
  unverified) is institutional-grade disclosure decision per
  verify-state-at-first-consumption sub-discipline. S13 entry's
  "p3_ccf audit's ccf_positive metric directly applies" framing was
  synthesis claim misaligned with empirical harness-engine
  relationship; misalignment caught at S14 prewhitened_ccf_lag Step 0
  first downstream consumption (Code's Step 0 empirical re-read of
  p3_ccf.py harness wrapper surfaced the harness-engine code path
  divergence); S14a investigation confirmed pattern at p3_ccf scope;
  S14b amendment corrects S13 retroactively + applies layered framing
  forward.
- **Q-B (user genuine contestation vs default ratification):** Default
  ratification at second-technique selection (user ratified
  cross_correlation_lag under Tier 2 case-against framing per Phase 7+
  S12-close proposal; case-against weighted but not invalidating per
  efficient ratification disposition). Pro-forma elements present per
  Mark 3 efficient-ratification pattern (operating-context preservation
  per Workstream B §5.3); not pro-forma across all upstream decisions
  for this technique (multi-map characterization required substantive
  Step 0 empirical verification of catalog↔wrapper mapping + per-catalog
  output mapping clarification; S14b layered framing additionally
  required substantive Step 0 + S14a empirical investigation of
  harness-engine code path divergence).
- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (CCF math at statsmodels.ccf)** per bit-exact PASS
  verdict at machine precision against canonical R `stats::ccf`;
  disclosure language clearly delineates layered validation coverage.
  **Conditional for Layer 2 (engine module custom numpy CCF)** —
  requires expert review of engine implementation OR engine-output
  cross-check against validated statsmodels.ccf to close the
  equivalence gap empirically; published research using
  cross_correlation_lag output relies on Layer 2 engine implementation
  (Layer 1 is what the harness validates, NOT what the engine
  produces). Defensible to all three audiences with disclosure
  language as drafted: published audience (layered validation framing
  transparent); Morgan Stanley compliance review (precise audit
  citation + tier taxonomy + Layer 1/Layer 2 scope delineation);
  external expert reviewer at Path α close (verbatim audit numerics
  + honest disclosure of what's validated and what's not + Q3b
  extension pending + Layer 2 equivalence verification candidate for
  expert review scope).
- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium. cross_correlation_lag typically appears as diagnostic /
  preliminary lead-lag analysis in time-series research; not
  headline-driving for strategic recommendations or client
  positioning at single-technique level. **Layer-specific retraction
  surface (per S14b layered framing):**
  - Layer 1 (CCF math at statsmodels.ccf): low retraction surface;
    bit-exact PASS verdict against canonical R reference at machine
    precision; expert review surfacing upstream error would propagate
    to all 3 p3_ccf-covered techniques (multi-map propagation risk).
  - Layer 2 (engine module custom numpy CCF): MEDIUM retraction
    surface specifically for cross_correlation_lag (and analogously
    for prewhitened_ccf_lag + rolling_ccf_lag); if engine
    implementation found to diverge from validated statsmodels.ccf at
    machine-precision level, retraction would affect all
    engine-produced outputs from these catalog techniques (per-note
    retroactive disclosure correction + engine code remediation OR
    cross-check addition).

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; second technique to enter status per S13
ratification; first of p3_ccf-covered triple (prewhitened_ccf_lag +
rolling_ccf_lag pending S14c + S15 per sequential disposition).
**S14b amendment: layered framing per S14a empirical findings —
validation evidence applies to statsmodels.ccf math layer (Layer 1;
bit-exact PASS); engine module custom numpy CCF (Layer 2) bit-exact
equivalence to validated math plausible but unverified; expert review
OR engine-output cross-check required to close Layer 2 gap
empirically.**

### prewhitened_ccf_lag (Phase 7+ S14c; third §2.5 entry; second of p3_ccf-covered triple per Workstream B §3.3 multi-map handling; THREE-LAYER framing per S14b layered framing precedent + S14a harness-vs-engine empirical findings + prewhitened_ccf_lag-specific AR-prewhitening upstream addition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2). **Important nuance (three-layer framing per S14c
extending S14b two-layer framing):** tier classification applies to
Layer 1 (statsmodels.tsa.stattools.ccf vs R stats::ccf); Layer 2a
(engine module CCF implementation on prewhitened residuals)
plausibly equivalent but unverified; Layer 2b (AR-prewhitening
pipeline upstream of CCF) NOT covered by p3_ccf parity audit. See
Validation claim scope below.

**Multi-map note (per Workstream B §3.3):** prewhitened_ccf_lag is
one of 3 catalog techniques covered by shared Phase 3 wrapper p3_ccf
(covers cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag);
validation evidence per p3_ccf_audit.md applies to the
`statsmodels.tsa.stattools.ccf` computation against R `stats::ccf`
at the harness TSL arm. **Per-catalog interpretation + per-catalog
code path mapping (per S14b multi-map refinement + S14c three-layer
extension):** for prewhitened_ccf_lag specifically, engine module
applies AR-prewhitening to input series X upstream of CCF
computation (`engine/techniques/prewhitened_ccf_lag.py` lines 99-118:
pmdarima.auto_arima fit on X OR user-specified ARIMA order; ARIMA
filter applied to Y per "purist prewhitening" via `_apply_arima_filter`
helper lines 319-353 with fallback to differencing; residual
extraction) and computes CCF on prewhitened residuals via custom
numpy implementation (lines 356-375 `_compute_ccf`: normalized
Pearson cross-correlation across positive lags 0..max_lag; separate
positive + negative lag branches for full -max_lag..+max_lag
coverage). cross_correlation_lag (S13 shipped + S14b layered framing
amendment) handled raw CCF without prewhitening; rolling_ccf_lag
(S15 candidate) computes rolling-window CCF without prewhitening;
AR-prewhitening is prewhitened_ccf_lag-specific (not shared with
other p3_ccf-covered catalog techniques).

**Reference:** R `stats::ccf` (base R 4.5.3)
**Verdict:** PASS Pattern A bit-exact (Layer 1 only; see Validation
claim scope for Layer 2a + Layer 2b coverage)
**Audit:** `tools/reference_parity/reports/p3_ccf_audit.md`
**Audit date:** 2026-04-29
**ccf_positive max abs diff:** 1.33e-15
**ccf_positive max rel diff:** 1.46e-15

**Source files (three-layer per S14c framing extending S14b layered
framing):** `tools/reference_parity/harness/checks/p3_ccf.py` lines
51-59 (harness TSL arm invokes `statsmodels.tsa.stattools.ccf`
directly on input fixture; does NOT invoke engine modules OR
AR-prewhitening pipeline)
+ `engine/techniques/prewhitened_ccf_lag.py` lines 99-118
(AR-prewhitening: pmdarima.auto_arima fit on X with stepwise mode
for Fast/Balanced presets + non-stepwise for Thorough; ARIMA filter
applied to Y via `_apply_arima_filter` helper lines 319-353;
fallback to differencing if filtering fails; residual extraction)
+ `engine/techniques/prewhitened_ccf_lag.py` lines 356-375
(`_compute_ccf` custom numpy CCF: manual normalized cross-covariance
on prewhitened residuals; separate ccf_pos + ccf_neg branches for
full -max_lag..+max_lag coverage)
+ `engine/techniques/cross_correlation_lag.py` + `engine/techniques/rolling_ccf_lag.py`
(per-catalog engine modules for other p3_ccf-covered catalog
techniques; not exercised by p3_ccf harness)
+ `tools/reference_parity/reports/p3_ccf_audit.md`

**Validation claim scope (THREE-LAYER per S14c amendment per S14b
layered framing precedent + AR-prewhitening upstream addition):**
TSL prewhitened_ccf_lag output relies on three layered computations.
p3_ccf audit validates Layer 1 (statsmodels.ccf) vs R stats::ccf at
single seeded fixture configuration (lagged-pair series, T=200, true
lag=3, seed=42); ccf_positive metric measures statsmodels.ccf vs R
stats::ccf agreement, NOT engine module CCF agreement, NOT
AR-prewhitening pipeline correctness.

- **Layer 1 — CCF math at statsmodels.ccf (validated):** bit-exact
  PASS verdict applies at machine precision; parity covers Pearson
  cross-correlation across positive lags 0..MAX_LAG.
- **Layer 2a — engine module custom numpy CCF on prewhitened
  residuals (plausibly equivalent but unverified):** Engine module
  `_compute_ccf` (lines 356-375) implements same normalized Pearson
  cross-correlation formula as cross_correlation_lag's manual numpy
  CCF; bit-exact equivalence to validated statsmodels.ccf plausible
  (same formula; same float64 arithmetic) but unverified at p3_ccf
  audit; analogous to S14b-amended cross_correlation_lag Layer 2
  framing.
- **Layer 2b — AR-prewhitening pipeline upstream of CCF
  (engine-specific; NOT parity-validated):** Engine module lines
  99-118 apply ARIMA prewhitening to input X (auto_arima fit via
  pmdarima OR user-specified order; ARIMA filter applied to Y per
  "purist prewhitening"; residual extraction) BEFORE CCF computation.
  AR-prewhitening pipeline is prewhitened_ccf_lag-specific (NOT
  shared with cross_correlation_lag or rolling_ccf_lag) and NOT
  covered by p3_ccf parity audit. Pipeline correctness requires
  expert review of: (i) auto_arima model selection logic via
  pmdarima; (ii) ARIMA filter application to Y via `_apply_arima_filter`
  ("purist prewhitening" with same-order fallback); (iii) residual
  independence assumption underlying Bartlett band effective-n
  correction; (iv) fallback behavior when filtering fails.

Single-fixture parity established at machine precision for Layer 1;
parameter-sensitivity coverage NOT established (Q3b extension
pending); Layer 2a closure pending engine-output cross-check OR
expert review (analogous to S14b-amended cross_correlation_lag);
Layer 2b closure pending expert review of AR-prewhitening pipeline
(no parity validation available without separate prewhitening
reference). Reference selection + tolerance specification AI-assisted
with user ratification per Phase 7+ work program; pre-Path α expert
review status; expert review pending end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates; multi-map cross-reference per §3.3;
three-layer framing per S14c Bundle option II depth distribution):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique prewhitened_ccf_lag. CCF math
> layer (statsmodels.tsa.stattools.ccf) is cross-package bit-exact
> parity validated against R `stats::ccf` (base R 4.5.3) per Phase 3
> audit dated 2026-04-29 (ccf_positive max abs diff 1.33e-15; shared
> p3_ccf wrapper covers cross_correlation_lag + prewhitened_ccf_lag
> + rolling_ccf_lag). TSL engine module's custom numpy CCF on
> prewhitened residuals plausibly equivalent to validated math but
> not directly tested. AR-prewhitening pipeline upstream (auto_arima
> fit + ARIMA filter) is engine-specific and NOT covered by parity
> audit; requires expert review for published use. Pre-Path α
> expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique prewhitened_ccf_lag implements three
> layered computations validated separately. **Layer 1 — CCF math
> at statsmodels.ccf:** validated per Phase 3 reference parity
> infrastructure. **Reference:** R `stats::ccf` (base R 4.5.3).
> **Verdict:** PASS Pattern A.2 bit-exact at machine precision;
> ccf_positive max abs diff 1.33e-15, max rel diff 1.46e-15.
> **Audit date:** 2026-04-29. **Multi-map coverage:**
> prewhitened_ccf_lag is one of 3 catalog techniques covered by
> shared Phase 3 wrapper p3_ccf; validation evidence per p3_ccf
> audit applies to `statsmodels.tsa.stattools.ccf` (the harness TSL
> arm) vs R `stats::ccf`. **Layer 2a — engine module CCF
> implementation:** TSL engine module
> (`engine/techniques/prewhitened_ccf_lag.py` lines 356-375
> `_compute_ccf`) uses custom numpy CCF on prewhitened residuals;
> bit-exact equivalence to validated statsmodels.ccf plausible (same
> Pearson cross-correlation formula; same float64 arithmetic) but
> NOT empirically verified; requires expert review OR engine-output
> cross-check to close the gap. **Layer 2b — AR-prewhitening
> pipeline upstream:** engine module lines 99-118 apply ARIMA
> prewhitening to input X via pmdarima.auto_arima and apply same-order
> ARIMA filter to Y per "purist prewhitening" approach (with fallback
> to differencing); residuals feed Layer 2a CCF computation.
> AR-prewhitening pipeline is prewhitened_ccf_lag-specific and NOT
> covered by p3_ccf parity audit; pipeline correctness requires
> expert review of auto_arima model selection + ARIMA filter
> application + residual independence assumption. **Fixture:** seeded
> single-fixture configuration (lagged-pair series, T=200, true
> lag=3, seed=42); parameter-sensitivity coverage NOT established;
> Q3b extension pending. Pre-Path α expert review status; expert
> review pending end-of-Phase-7+-work-program.

*Pattern (iii) Risk model documentation:*
> prewhitened_ccf_lag validation: TSL Tier II.bit-exact (Layer 1 CCF
> math at statsmodels.ccf only). Reference: R `stats::ccf` (base R
> 4.5.3). Audit: `tools/reference_parity/reports/p3_ccf_audit.md`
> dated 2026-04-29. Verdict: PASS Pattern A.2 bit-exact at machine
> precision (ccf_positive max abs diff 1.33e-15). Multi-map coverage:
> shared p3_ccf wrapper covers cross_correlation_lag +
> prewhitened_ccf_lag + rolling_ccf_lag. **Three-layer framing:**
> Layer 1 (statsmodels.ccf) parity-validated; Layer 2a (engine CCF
> on prewhitened residuals) bit-exact equivalence plausible but
> unverified; Layer 2b (AR-prewhitening pipeline) NOT parity-validated,
> engine-specific implementation requires expert review. Fixture:
> single-seeded; Q3b extension pending. Risk attribution conditional
> on (a) parameter configurations matching fixture-similar conditions
> AND (b) Layer 2a engine CCF equivalence AND (c) Layer 2b
> AR-prewhitening correctness — (b) + (c) require expert review.
> Pre-Path α expert review status.

*Pattern (iv) Internal use disclosure:*
> prewhitened_ccf_lag CCF math layer (statsmodels.ccf) cross-package
> bit-exact validated against R `stats::ccf` via shared p3_ccf
> wrapper; Layer 2a (engine module custom numpy CCF on prewhitened
> residuals) bit-exact equivalence plausible but unverified;
> Layer 2b (AR-prewhitening pipeline) NOT parity-validated,
> engine-specific implementation requires expert review; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):** Extracted/
  cited. Reference selection from p3_ccf_audit.md verbatim (R
  `stats::ccf` base R 4.5.3); verdict + Pattern + date + numerics
  verbatim from audit. Multi-map characterization extracted from
  scope_reframing §2 lines 122-131 + Workstream B §3.3 multi-map
  handling guidance. Three-layer framing extracted per S14a empirical
  investigation (harness-vs-engine code path divergence at p3_ccf
  scope) + S14b layered framing precedent (two-layer for
  cross_correlation_lag; S14c three-layer extension for
  prewhitened_ccf_lag-specific AR-prewhitening upstream addition).
  Engine module behavior at Layer 2a (lines 356-375 `_compute_ccf`)
  + Layer 2b (lines 99-118 AR-prewhitening pipeline + lines 319-353
  `_apply_arima_filter` helper) verified empirically per Step 0
  re-reads. Three-layer framing is institutional-grade disclosure
  per verify-state-at-first-consumption sub-discipline applied
  forward at entry authoring time (8th instance application of
  sub-discipline; preemptive rather than retroactive vs S14b
  application).
- **Q-B (user genuine contestation vs default ratification):** Default
  ratification at third-technique selection (user ratified
  prewhitened_ccf_lag under Tier 2 case-against framing per
  Phase 7+ S13-close proposal; case-against weighted but not
  invalidating per efficient ratification disposition). Pro-forma
  elements present per Mark 3 efficient-ratification pattern
  (operating-context preservation per Workstream B §5.3); Q-B
  pattern persists at n=4 across S12 + S13 + S14b cross_correlation_lag
  amendment + S14c (Q1 audit checklist operational pattern codification
  candidate per S13 forward instrumentation; n=4 threshold reached;
  forward instrumentation for §19.4 absorption). Not pro-forma across
  all upstream decisions for this technique (three-layer framing
  required substantive Step 0 + S14a empirical investigation + S14b
  layered framing precedent extension; user three-layer disclosure
  depth ratification at S14b STOP 1 disposition surfacing reflects
  substantive engagement with layered framing structure).
- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (CCF math at statsmodels.ccf)** per bit-exact
  PASS verdict at machine precision against canonical R `stats::ccf`.
  **Conditional for Layer 2a (engine module custom numpy CCF on
  prewhitened residuals)** — requires expert review of engine
  implementation OR engine-output cross-check against validated
  statsmodels.ccf (analogous to S14b-amended cross_correlation_lag
  Layer 2 framing). **Conditional for Layer 2b (AR-prewhitening
  pipeline)** — requires expert review of auto_arima model selection
  + ARIMA filter application + residual independence assumption +
  Y-arm "purist" filtering vs same-order fallback behavior;
  AR-prewhitening is engine-specific and has NO parity validation
  available within p3_ccf audit scope. Defensible to all three
  audiences with disclosure language as drafted: published audience
  (three-layer framing transparent); Morgan Stanley compliance review
  (precise audit citation + tier taxonomy + Layer 1 / Layer 2a /
  Layer 2b scope delineation); external expert reviewer at Path α
  close (verbatim audit numerics + honest disclosure of what's
  validated and what's not + Q3b extension pending + Layer 2a +
  Layer 2b expert review scope identified).
- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-to-high. prewhitened_ccf_lag is typically used for
  causal-inference lead-lag identification where prewhitening adds
  credibility over raw CCF; widely cited Box-Jenkins methodology in
  financial time-series research. **Layer-specific retraction
  surface (per S14c three-layer framing):**
  - Layer 1 (CCF math at statsmodels.ccf): low; multi-map propagation
    risk if shared CCF error found.
  - Layer 2a (engine module custom numpy CCF on prewhitened residuals):
    MEDIUM analogous to S14b-amended cross_correlation_lag Layer 2.
  - Layer 2b (AR-prewhitening pipeline): MEDIUM-HIGH specifically
    for prewhitened_ccf_lag (NOT shared with other p3_ccf-covered
    techniques). AR-prewhitening is the operational distinctive of
    prewhitened_ccf_lag — Box-Jenkins methodology relies on
    prewhitening for cleaner CCF estimates; expert review surfacing
    material errors (auto_arima model selection; ARIMA filter
    application; residual independence violation; "purist" filtering
    fallback behavior) would invalidate the cleaner-CCF claim
    motivating prewhitened_ccf_lag use over raw cross_correlation_lag.
    Higher surface than Layer 2a because Layer 2b errors affect
    published-research framing ("prewhitened" provides cleaner
    lead-lag than raw CCF) rather than just engine-vs-validated-math
    equivalence.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; third technique to enter status per S14c
ratification; second of p3_ccf-covered triple under corrected
layered framing (cross_correlation_lag shipped S13 with S14b
layered framing amendment; rolling_ccf_lag pending S15 per sequential
disposition; rolling_ccf_lag likely two-layer not three-layer per
absence of upstream prewhitening). **S14c three-layer framing:
Layer 1 (statsmodels.ccf vs R stats::ccf) bit-exact PASS; Layer 2a
(engine module custom numpy CCF on prewhitened residuals) plausibly
equivalent but unverified; Layer 2b (AR-prewhitening pipeline) NOT
parity-validated, engine-specific implementation requires expert
review.**

### rolling_ccf_lag (Phase 7+ S15; fourth §2.5 entry; third of p3_ccf-covered triple per Workstream B §3.3 multi-map handling; completes triple; THREE-LAYER DOWNSTREAM-TOPOLOGY framing per S15 STOP 2 empirical investigation + S14b + S14c precedent + α disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2). **Important nuance (three-layer downstream-topology
framing per S15 extending S14b/S14c precedent):** tier classification
applies to Layer 1 (statsmodels.tsa.stattools.ccf vs R stats::ccf);
Layer 2 (engine module CCF + rolling-window orchestration) plausibly
equivalent at CCF math but rolling-window orchestration
engine-specific; Layer 3 (engine-specific post-processing DOWNSTREAM
of CCF: boundary-hit flagging + structural break detection via
ruptures.Pelt + AC-corrected Bartlett band + split-regime summary)
NOT covered by p3_ccf parity audit. **Topology distinction from S14c
three-layer:** S14c had Layer 2b AR-prewhitening UPSTREAM of CCF
(engine-specific upstream layer between input and CCF computation);
S15 has Layer 3 post-processing DOWNSTREAM of CCF (engine-specific
downstream layer between CCF computation and final output). Both
topologically distinct; same layer depth (three); different
operational risk surface. See Validation claim scope below.

**Multi-map note (per Workstream B §3.3):** rolling_ccf_lag is one of
3 catalog techniques covered by shared Phase 3 wrapper p3_ccf
(covers cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag);
validation evidence per p3_ccf_audit.md applies to
`statsmodels.tsa.stattools.ccf` vs R `stats::ccf` at harness TSL arm.
**Per-catalog interpretation + per-catalog code path mapping
(completes p3_ccf-covered triple under corrected layered framing):**
for rolling_ccf_lag specifically, engine module computes CCF on
rolling-window sub-series (engine-specific window iteration +
per-window custom numpy CCF) + applies substantial DOWNSTREAM
post-processing (boundary-hit flagging + ruptures.Pelt structural
break detection + AC-corrected Bartlett band + split-regime summary).
cross_correlation_lag (S13 + S14b two-layer) handled raw CCF without
rolling-window or post-processing; prewhitened_ccf_lag (S14c
three-layer-upstream) applied AR-prewhitening BEFORE CCF but no
post-processing; rolling_ccf_lag (S15 three-layer-downstream) applies
rolling-window + substantial post-processing AFTER CCF. Completes
p3_ccf-covered triple sequential disposition.

**Reference:** R `stats::ccf` (base R 4.5.3)
**Verdict:** PASS Pattern A bit-exact (Layer 1 only; see Validation
claim scope for Layer 2 + Layer 3 coverage)
**Audit:** `tools/reference_parity/reports/p3_ccf_audit.md`
**Audit date:** 2026-04-29
**ccf_positive max abs diff:** 1.33e-15
**ccf_positive max rel diff:** 1.46e-15

**Source files (three-layer downstream-topology per S15 framing
extending S14b/S14c precedent):**
`tools/reference_parity/harness/checks/p3_ccf.py` lines 51-59 (harness
TSL arm invokes `statsmodels.tsa.stattools.ccf` directly on input
fixture; does NOT invoke engine modules)
+ `engine/techniques/rolling_ccf_lag.py` lines 396-462 (Layer 2:
rolling-window orchestration + per-window custom numpy CCF;
window_starts = list(range(0, n - window + 1, step)); per-window
x_dm + y_dm + denom + ccf_val across lags -max_lag..+max_lag;
preset-based window/step/max_lag config lines 55-72)
+ `engine/techniques/rolling_ccf_lag.py` lines 464-472 (Layer 3a:
boundary-hit flagging via flag_boundary_hits helper; threshold
default 0.8; excludes boundary-lag windows from summary statistics)
+ `engine/techniques/rolling_ccf_lag.py` lines 75-254 + 492-498
(Layer 3b: structural break detection via ruptures.Pelt;
_detect_structural_break helper; 4-criteria validation —
min-segment run-length, modal-sign consistency ≥2/3, sign contrast,
magnitude contrast ≥0.25; PELT penalty `pen = log(len(arr)) *
max(var, 1e-6)`)
+ `engine/techniques/rolling_ccf_lag.py` lines 412-490 (Layer 3c:
AC-corrected Bartlett band with per-window scaling;
`bartlett_effective_n` on full series + per-window scaling
`n_eff_window = max(3.0, min(window, n_eff_full * window / n))`)
+ `engine/techniques/rolling_ccf_lag.py` lines 651-715 + helper
`_regime_stats` (Layer 3d: split-regime summary; regime-specific
lag/correlation summary when break detected)
+ `engine/techniques/cross_correlation_lag.py` +
`engine/techniques/prewhitened_ccf_lag.py` (other p3_ccf-covered
engine modules; not exercised by p3_ccf harness)
+ `tools/reference_parity/reports/p3_ccf_audit.md`

**Validation claim scope (THREE-LAYER DOWNSTREAM-TOPOLOGY per S15
amendment per S14b/S14c precedent + α disposition):** TSL
rolling_ccf_lag output relies on three layered computations with
downstream topology (Layer 3 post-processing follows CCF; contrasts
with S14c prewhitened_ccf_lag upstream topology where Layer 2b
prewhitening precedes CCF). p3_ccf audit validates Layer 1
(statsmodels.ccf) vs R stats::ccf at single seeded fixture
(lagged-pair series, T=200, true lag=3, seed=42); ccf_positive
metric measures statsmodels.ccf vs R stats::ccf agreement, NOT
engine module CCF agreement, NOT rolling-window orchestration
correctness, NOT downstream post-processing correctness.

- **Layer 1 — CCF math at statsmodels.ccf (validated):** bit-exact
  PASS verdict at machine precision; parity covers Pearson
  cross-correlation across positive lags 0..MAX_LAG.

- **Layer 2 — engine module CCF + rolling-window orchestration
  (plausibly equivalent at CCF math; rolling-window engine-specific):**
  Engine module lines 396-462 iterate over windows (preset-based
  window/step/max_lag config) + per-window custom numpy CCF
  computation (manual normalized cross-covariance: x_dm - mean;
  y_dm - mean; ccf_val = sum(x_dm * y_dm) / denom across lags).
  CCF math bit-exact equivalence to validated statsmodels.ccf
  plausible (same Pearson formula; same float64) but unverified
  analogous to S14b cross_correlation_lag Layer 2 framing.
  Rolling-window iteration engine-specific (window sizing heuristic
  per preset; step size; max_lag_frac); NOT covered by p3_ccf
  parity audit; correctness depends on window/step/max_lag
  heuristics being appropriate for the analysis use case.

- **Layer 3 — engine-specific post-processing DOWNSTREAM of CCF
  (NOT parity-validated):** Engine module applies four post-processing
  sub-components AFTER per-window CCF computation:
  - **3a — Boundary-hit flagging** (lines 464-472 + flag_boundary_hits
    helper from base): windows with optimal lag at/near ±max_lag
    (threshold default 0.8) flagged as unreliable; excluded from
    summary statistics. Engine-specific threshold heuristic;
    correctness requires expert review of threshold
    appropriateness.
  - **3b — Structural break detection via ruptures.Pelt** (lines
    75-254 helper `_detect_structural_break` + lines 492-498
    invocation): 180+ LOC engine-specific changepoint detection
    logic. Runs PELT on optimal_ccfs + sign-of-CCF series; applies
    4-criteria validation — (1) min-segment run-length, (2)
    modal-sign consistency ≥2/3, (3) sign contrast across segments,
    (4) magnitude contrast ≥0.25. PELT penalty `pen = log(len(arr))
    * max(var, 1e-6)`. NOT covered by p3_ccf parity audit;
    correctness depends on ruptures.Pelt library + 4-criteria
    heuristic + penalty formula appropriateness for rolling-CCF
    output series.
  - **3c — AC-corrected Bartlett band with per-window scaling**
    (lines 412-490): `bartlett_effective_n` on full series + per-window
    scaling `n_eff_window = max(3.0, min(window, n_eff_full * window
    / n))`. Engine-specific scaling heuristic; AC correction has its
    own assumptions (Bartlett formula validity for cross-correlation;
    per-window scaling appropriateness).
  - **3d — Split-regime summary** (lines 651-715 + helper
    `_regime_stats`): regime-specific lag/correlation summary when
    break detected; format_pairwise_summary with pre/post regime
    stats; engine-specific summary construction.

Single-fixture parity established at machine precision for Layer 1;
parameter-sensitivity coverage NOT established (Q3b extension
pending); Layer 2 CCF math closure pending engine-output cross-check
OR expert review (analogous to S14b cross_correlation_lag Layer 2);
Layer 2 rolling-window orchestration + Layer 3 post-processing
closure pending expert review (engine-specific; no parity validation
available; rolling_ccf_lag's value-add over raw cross_correlation_lag
IS the rolling + post-processing functionality, so expert review of
these layers is operationally distinctive). Reference selection +
tolerance specification AI-assisted with user ratification per
Phase 7+ work program; pre-Path α expert review status; expert
review pending end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates; multi-map cross-reference per §3.3;
three-layer downstream-topology framing per S15 α disposition;
Bundle option II depth distribution):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique rolling_ccf_lag. CCF math layer
> (statsmodels.tsa.stattools.ccf) is cross-package bit-exact parity
> validated against R `stats::ccf` (base R 4.5.3) per Phase 3 audit
> dated 2026-04-29 (ccf_positive max abs diff 1.33e-15; shared
> p3_ccf wrapper covers cross_correlation_lag + prewhitened_ccf_lag
> + rolling_ccf_lag). TSL engine module's custom numpy CCF +
> rolling-window orchestration plausibly equivalent at CCF math but
> rolling-window engine-specific. Downstream post-processing
> (boundary flagging + structural break detection via ruptures.Pelt
> + AC-corrected Bartlett band + split-regime summary) is
> engine-specific and NOT covered by parity audit; requires expert
> review for published use. Pre-Path α expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique rolling_ccf_lag implements three layered
> computations with downstream topology (Layer 3 post-processing
> follows CCF; contrasts with prewhitened_ccf_lag upstream topology).
> **Layer 1 — CCF math at statsmodels.ccf:** validated per Phase 3
> reference parity infrastructure. **Reference:** R `stats::ccf` (base
> R 4.5.3). **Verdict:** PASS Pattern A.2 bit-exact at machine
> precision; ccf_positive max abs diff 1.33e-15, max rel diff
> 1.46e-15. **Audit date:** 2026-04-29. **Multi-map coverage:**
> rolling_ccf_lag is one of 3 catalog techniques covered by shared
> Phase 3 wrapper p3_ccf; validation evidence applies to
> `statsmodels.tsa.stattools.ccf` (the harness TSL arm) vs R
> `stats::ccf`. **Layer 2 — engine module CCF + rolling-window
> orchestration:** TSL engine module (`engine/techniques/rolling_ccf_lag.py`
> lines 396-462) computes CCF on rolling-window sub-series via custom
> numpy implementation; bit-exact equivalence to validated
> statsmodels.ccf plausible (same Pearson cross-correlation formula;
> same float64 arithmetic) but NOT empirically verified; rolling-window
> iteration is engine-specific (preset-based window/step/max_lag
> heuristics). **Layer 3 — engine-specific post-processing downstream:**
> engine module applies four post-processing sub-components AFTER
> per-window CCF: (3a) boundary-hit flagging with threshold default
> 0.8 (lines 464-472); (3b) structural break detection via
> ruptures.Pelt with 4-criteria validation (min-segment run-length,
> modal-sign consistency ≥2/3, sign contrast, magnitude contrast
> ≥0.25; PELT penalty pen = log(len(arr)) * max(var, 1e-6); lines
> 75-254 + 492-498; 180+ LOC); (3c) AC-corrected Bartlett band with
> per-window scaling (n_eff_window = max(3.0, min(window,
> n_eff_full * window / n)); lines 412-490); (3d) split-regime
> summary when break detected (lines 651-715). Layer 3
> post-processing is engine-specific and NOT covered by p3_ccf
> parity audit; correctness requires expert review of boundary
> threshold + ruptures.Pelt 4-criteria heuristic + AC correction
> scaling + split-regime construction. **Fixture:** seeded
> single-fixture (lagged-pair series, T=200, true lag=3, seed=42);
> parameter-sensitivity coverage NOT established; Q3b extension
> pending. Reference selection + tolerance specification AI-assisted
> with user ratification. Pre-Path α expert review status; expert
> review pending end-of-Phase-7+-work-program.

*Pattern (iii) Risk model documentation:*
> rolling_ccf_lag validation: TSL Tier II.bit-exact (Layer 1 CCF
> math at statsmodels.ccf only). Reference: R `stats::ccf` (base R
> 4.5.3). Audit: `tools/reference_parity/reports/p3_ccf_audit.md`
> dated 2026-04-29. Verdict: PASS Pattern A.2 bit-exact at machine
> precision (ccf_positive max abs diff 1.33e-15). Multi-map coverage:
> shared p3_ccf wrapper covers cross_correlation_lag +
> prewhitened_ccf_lag + rolling_ccf_lag. **Three-layer
> downstream-topology framing:** Layer 1 (statsmodels.ccf)
> parity-validated; Layer 2 (engine CCF + rolling-window) bit-exact
> equivalence plausible but unverified at CCF math, rolling-window
> engine-specific; Layer 3 (post-processing) NOT parity-validated,
> engine-specific implementation requires expert review of (3a)
> boundary-hit flagging threshold + (3b) ruptures.Pelt 4-criteria
> structural break detection + (3c) AC-corrected Bartlett band
> per-window scaling + (3d) split-regime summary construction.
> Fixture: single-seeded; Q3b extension pending. Risk attribution
> conditional on (a) parameter configurations matching
> fixture-similar conditions AND (b) Layer 2 engine CCF +
> rolling-window correctness AND (c) Layer 3 post-processing
> correctness across 3a/3b/3c/3d sub-components — (b) + (c) require
> expert review. Pre-Path α expert review status.

*Pattern (iv) Internal use disclosure:*
> rolling_ccf_lag CCF math layer (statsmodels.ccf) cross-package
> bit-exact validated against R `stats::ccf` via shared p3_ccf
> wrapper; Layer 2 (engine custom numpy CCF + rolling-window)
> bit-exact equivalence at CCF math plausible but unverified +
> rolling-window engine-specific; Layer 3 (post-processing: boundary
> flagging + structural break detection via ruptures.Pelt with
> 4-criteria validation + AC-corrected Bartlett band per-window
> scaling + split-regime summary) NOT parity-validated, requires
> expert review; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):**
  Extracted/cited. Reference selection from p3_ccf_audit.md verbatim
  (R `stats::ccf` base R 4.5.3); verdict + Pattern + date + numerics
  verbatim. Multi-map characterization extracted from scope_reframing
  §2 + Workstream B §3.3. Three-layer downstream-topology framing
  extracted per S15 STOP 2 empirical investigation (Step 0 (f) read
  of `engine/techniques/rolling_ccf_lag.py` 845 LOC) + S14b two-layer
  precedent + S14c three-layer-upstream precedent + α disposition
  ratification. Layer 2 (lines 396-462 rolling-window + custom numpy
  CCF) + Layer 3 (lines 464-472 3a + 75-254 + 492-498 3b + 412-490
  3c + 651-715 3d) sub-components empirically grounded per Step 0
  (f) verbatim line ranges. Topology distinction from S14c
  (downstream post-processing vs upstream prewhitening) surfaced
  per institutional-grade disclosure decision. Verify-state-at-first-consumption
  sub-discipline 9th instance application (forward-at-authoring +
  STOP 2 caught two-layer framing assumption empirical falsification;
  matures from S14c 8th-instance proactive-disclosure to S15
  9th-instance proactive-disclosure-with-assumption-falsification-catch).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at fourth-technique selection (user ratified
  rolling_ccf_lag under Tier 2 case-against framing per Phase 7+
  S14c-close proposal; case-against weighted but not invalidating
  per efficient ratification disposition). Pro-forma elements
  present per Mark 3 efficient-ratification pattern (operating-context
  preservation per Workstream B §5.3); **Q-B pattern persists at n=5
  across S12 + S13 + S14b + S14c + S15; well past n=4 codification
  candidate threshold** (ratified at S14b STOP 1 + S14c STOP 1 +
  S15 STOP 2 disposition; forward instrumentation for §19.4
  absorption — Q1 audit checklist operational pattern observation
  alongside Class A + Class B + forward Q1 Step 0 discipline + Q1
  amendment class baseline + Option II workflow + sub-discipline
  maturation). Not pro-forma across all upstream decisions for this
  technique (three-layer downstream-topology framing required STOP 2
  empirical investigation + α disposition ratification + Layer 3
  sub-component 4-fold enumeration).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (CCF math at statsmodels.ccf)** per bit-exact
  PASS verdict at machine precision against canonical R `stats::ccf`.
  **Conditional for Layer 2 (engine CCF + rolling-window
  orchestration)** — CCF math bit-exact equivalence to validated
  statsmodels.ccf plausible but unverified (analogous to S14b
  cross_correlation_lag Layer 2); rolling-window iteration engine-specific
  (window/step/max_lag heuristics require expert review of
  appropriateness). **Conditional for Layer 3 (post-processing)** —
  requires expert review of: 3a boundary-hit threshold heuristic
  (0.8 default; appropriateness for analysis use case); 3b
  ruptures.Pelt structural break detection (4-criteria validation
  + PELT penalty formula; correctness for rolling-CCF output
  series); 3c AC-corrected Bartlett band per-window scaling
  (formula appropriateness for rolling cross-correlation
  significance assessment); 3d split-regime summary construction
  (regime-specific aggregation methodology). Defensible to all
  three audiences with disclosure language as drafted: published
  audience (three-layer downstream-topology framing transparent);
  Morgan Stanley compliance review (precise audit citation + tier
  taxonomy + Layer 1 / Layer 2 / Layer 3 scope delineation +
  topology distinction from S14c); external expert reviewer at
  Path α close (verbatim audit numerics + honest disclosure of
  what's validated and what's not + Q3b extension pending + Layer
  2 + Layer 3 sub-components expert review scope identified with
  specific line ranges).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-to-high. rolling_ccf_lag is typically used for time-varying
  lead-lag analysis in financial/macro time-series research where
  structural break detection is a value-add over raw or prewhitened
  CCF; widely cited rolling-window methodology with regime-shift
  awareness. **Layer-specific retraction surface (per S15
  three-layer downstream-topology framing):**
  - Layer 1 (CCF math at statsmodels.ccf): low; multi-map
    propagation risk if shared CCF error found.
  - Layer 2 (engine CCF + rolling-window orchestration): MEDIUM
    analogous to S14b cross_correlation_lag Layer 2 (CCF math
    equivalence) + engine-specific window/step/max_lag heuristic
    appropriateness.
  - Layer 3 (downstream post-processing): MEDIUM-HIGH specifically
    for rolling_ccf_lag (NOT shared with cross_correlation_lag or
    prewhitened_ccf_lag). Downstream post-processing is the
    operational distinctive of rolling_ccf_lag — rolling-CCF
    methodology relies on boundary flagging + structural break
    detection + AC-corrected significance + split-regime summary
    to deliver value-add over raw CCF; expert review surfacing
    material errors (boundary threshold; ruptures.Pelt 4-criteria
    validation; AC correction scaling; split-regime construction)
    would invalidate the regime/break-aware lead-lag claim
    motivating rolling_ccf_lag use over raw cross_correlation_lag.
    **Topologically distinct from S14c Layer 2b MEDIUM-HIGH:**
    S14c upstream prewhitening errors affect what CCF sees
    (cleaner-CCF claim invalidated); S15 downstream post-processing
    errors affect what user sees (regime/break-aware claim
    invalidated); both MEDIUM-HIGH but operationally distinct risk
    surfaces.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; fourth technique to enter status per S15
ratification; third of p3_ccf-covered triple under corrected
layered framing (cross_correlation_lag S13 + S14b two-layer
amendment; prewhitened_ccf_lag S14c three-layer-upstream;
rolling_ccf_lag S15 three-layer-downstream). **Completes
p3_ccf-covered triple sequential disposition.** **S15 three-layer
downstream-topology framing topologically distinct from S14c
three-layer-upstream:** S14c had Layer 2b AR-prewhitening UPSTREAM
of CCF; S15 has Layer 3 post-processing DOWNSTREAM of CCF (boundary
flagging + structural break detection via ruptures.Pelt with
4-criteria validation + AC-corrected Bartlett band per-window
scaling + split-regime summary). Both topologically distinct; same
layer depth (three); different operational risk surface.

### dtw_alignment_lag (Phase 7+ S17; fifth §2.5 entry; first 1:1 catalog↔wrapper entry under layered framing; THREE-LAYER DOWNSTREAM-TOPOLOGY framing per S15 rolling_ccf_lag precedent + S17 STOP 2 empirical investigation + α disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A cross-package per p3_dtw audit). **Important nuance
(three-layer downstream-topology framing per S17 α disposition;
analogous to S15 rolling_ccf_lag precedent with catalog-mapping
distinction):** tier classification applies to Layer 1 (DTW math at
harness reference DP + dtaidistance.dtw); Layer 2 (engine module DTW
core with Sakoe-Chiba window + step_pattern variants + pre-processing
helpers) plausibly equivalent at base case but parameter variants +
pre-processing engine-specific; Layer 3 (engine-specific
post-processing DOWNSTREAM of DTW core: warping path extraction +
time-varying lag extraction + lag segmentation + multi-table output)
NOT covered by p3_dtw parity audit. See Validation claim scope below.

**Framing precedent note (1:1 catalog↔wrapper; layered framing per
empirical engine module complexity):** dtw_alignment_lag is 1:1
catalog↔wrapper mapping per scope_reframing §2 line 129 (p3_dtw NOT
in multi-map list; distinct from p3_ccf-covered triple of S13-S15).
Layered framing applies despite 1:1 mapping per S17 STOP 2 empirical
finding: framing shape orthogonal to catalog mapping. Three-layer-
downstream framing analogous to S15 rolling_ccf_lag (multi-map
three-layer-downstream baseline; A10 Sub-class 2c) but with
DTW-methodology-specific Layer 2 + Layer 3 sub-components instead
of CCF-methodology. **A10 sub-class disposition deferred to next
§19.4 absorption cycle:** does S17 count as A10 Sub-class 2c
three-layer-downstream n=2 (treating 1:1 vs multi-map as orthogonal
to framing topology) OR establish new A10 Sub-class 2d 1:1-three-
layer-downstream n=1 (treating catalog mapping as structurally
relevant)? Both interpretations plausible; resolution pending
absorption with both empirical observations available.

**Reference:** Python `dtaidistance.dtw` (dtaidistance 2.4.0)
**Verdict:** PASS Pattern A cross-package bit-exact (Layer 1 only;
see Validation claim scope for Layer 2 + Layer 3 coverage)
**Audit:** `tools/reference_parity/reports/p3_dtw_audit.md`
**Audit date:** 2026-04-29
**dtw_distance abs diff:** 0.0 (exact match)

**Source files (three-layer downstream-topology per S17 framing
extending S15 precedent for DTW methodology):**
`tools/reference_parity/harness/checks/p3_dtw.py` lines 36-69
(harness TSL arm invokes harness-internal `_dtw_distance` reference
DP defined inside p3_dtw.py — 10-line unconstrained DP with squared
Euclidean local cost; does NOT invoke engine module's `run()` OR
`_dtw` helper; harness comment line 68: "Use numpy reference DTW
(mirrors TSL's custom impl)" — mirrors engine BASE CASE only,
without window or step_pattern variants)
+ `tools/reference_parity/harness/checks/p3_dtw.py` lines 71-82
(harness reference arm invokes `dtaidistance.dtw.distance(x, y)`
directly; canonical C-implementation)
+ `engine/techniques/dtw_alignment_lag.py` lines 416-491 (Layer 2
forward DP + Layer 3 3a backtrack DP per Layer 2/Layer 3 boundary
clarification below; engine module `_dtw` helper; 76-LOC custom
numpy DTW with Sakoe-Chiba window constraint via j_start/j_end
bounds AND step_pattern variants — symmetric1 diagonal-only OR
symmetric2 diagonal+horizontal+vertical; harness's `_dtw_distance`
has NEITHER window NOR step_pattern variants)
+ `engine/techniques/dtw_alignment_lag.py` lines 140-164 (Layer 2
pre-processing helpers: subsampling for large series + z-normalization;
folded into Layer 2 as DTW pre-processing helpers per α disposition;
NOT elevated to separate Layer 2a upstream per rationale "pre-
processing is wrapper-level standard time-series preparation, not
operational distinctive")
+ `engine/techniques/dtw_alignment_lag.py` lines 178-198 + 494-525
(Layer 3 post-processing sub-components 3b + 3c; see Validation
claim scope below)
+ `tools/reference_parity/reports/p3_dtw_audit.md`

**Validation claim scope (THREE-LAYER DOWNSTREAM-TOPOLOGY per S17
amendment per S15 precedent + DTW-methodology adaptation):** TSL
dtw_alignment_lag output relies on three layered computations with
downstream topology (Layer 3 post-processing follows DTW core;
analogous to S15 rolling_ccf_lag downstream topology). p3_dtw audit
validates Layer 1 (harness reference DP vs dtaidistance.dtw) at
single seeded fixture (warped sinusoid pair, T=100, warp_factor=1.2,
σ=0.05, seed=42); dtw_distance metric measures harness's
`_dtw_distance` vs dtaidistance.dtw agreement (0.0 abs diff PASS),
NOT engine module DTW core agreement, NOT engine post-processing
correctness.

- **Layer 1 — DTW math at harness reference DP + dtaidistance.dtw
  (validated):** bit-exact 0.0 abs diff PASS verdict against
  canonical dtaidistance C-implementation; parity covers unconstrained
  DTW dynamic programming with squared Euclidean local cost; DGP
  is warped sinusoid pair establishing closed-form DP recurrence
  produces byte-identical distances modulo numpy float64 vs C-double
  drift (empirically zero drift on test fixture).

- **Layer 2 — engine module DTW core (custom numpy with Sakoe-Chiba
  window + step_pattern variants + pre-processing helpers;
  plausibly equivalent at base case but variants engine-specific):**
  Engine module `_dtw` (lines 416-468 forward DP) implements DTW with
  j_start = max(1, i - window) + j_end = min(ny, i + window) bounding
  (Sakoe-Chiba window constraint) + symmetric1 (diagonal-only) OR
  symmetric2 (diagonal + horizontal + vertical) step_pattern
  variants. Bit-exact equivalence to validated harness reference
  DP plausible at default settings (no window OR window >= max(nx,
  ny); symmetric2 default) but variants unverified at p3_dtw audit.
  Pre-processing helpers (lines 140-164 subsampling for large
  series + z-normalization) fold into Layer 2 per α disposition.

**Layer 2/Layer 3 boundary clarification:** Cost matrix construction
(DTW DP forward pass via `_dtw` helper lines 416-468) is Layer 2 —
engine module's core DTW computation. Cost matrix backtrack-to-
warping-path (lines 469-491) is Layer 3 sub-component 3a —
post-processing that consumes Layer 2 output to produce warping
path as engine-specific output. Lines 416-491 are physically
contiguous within `_dtw` helper but operationally distinct (forward
DP = Layer 2; backtrack DP = Layer 3 3a). Expert review scope:
Layer 2 forward DP correctness vs Layer 3 3a backtrack
step-pattern-aware path reconstruction.

- **Layer 3 — engine-specific post-processing DOWNSTREAM of DTW
  core (NOT parity-validated):** Engine module applies four
  post-processing sub-components AFTER DTW core distance + path
  computation:
  - **3a — Warping path backtrack + extraction** (lines 469-491):
    backtrack through cost matrix from (nx, ny) to (0, 0)
    selecting minimum-cost step at each cell per step_pattern;
    builds path as list of (i, j) tuples. Engine-specific
    backtrack logic; correctness depends on step_pattern
    implementation matching forward DP.
  - **3b — Time-varying lag extraction** (lines 178-198): builds
    `x_to_y` dict mapping each x_index to list of matched
    y_indices; per-x-index averaging produces local_lags array;
    carry-forward heuristic for unmatched indices (line 198:
    "elif xi > 0: local_lags[xi] = local_lags[xi - 1]"). Engine-
    specific lag-extraction methodology; correctness depends on
    averaging + carry-forward heuristic appropriateness.
  - **3c — Lag segmentation via change-point heuristic**
    (`_segment_lags` lines 494-525): segments local_lags into
    regions of approximately constant lag using running-mean +
    deviation threshold (default 2.0); minimum 5-window segment
    length. Engine-specific change-point heuristic; correctness
    depends on threshold + minimum-length appropriateness for
    lag-segmentation analysis.
  - **3d — Multi-table output construction** (4 tables: lag
    time-series + warping path + segments + summary): engine-
    specific output decomposition; correctness depends on table
    construction matching analytical use case.

Single-fixture parity established at machine precision for Layer 1
(0.0 abs diff bit-exact); parameter-sensitivity coverage NOT
established at this validation tier (Q3b extension pending); Layer
2 closure pending engine-output cross-check at default settings OR
expert review of Sakoe-Chiba window + step_pattern variants
implementation; Layer 3 closure pending expert review of
post-processing sub-components (engine-specific; no parity
validation available; dtw_alignment_lag's value-add for
time-varying lead-lag detection IS the Layer 3 post-processing
functionality, so expert review of these sub-components is
operationally distinctive). Reference selection + tolerance
specification AI-assisted with user ratification per Phase 7+
work program; pre-Path α expert review status; expert review
pending end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates; three-layer downstream-topology framing
per S17 α disposition + S15 precedent; Bundle option II depth
distribution):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique dtw_alignment_lag. DTW math
> layer is cross-package bit-exact parity validated against Python
> `dtaidistance.dtw` (dtaidistance 2.4.0) per Phase 3 audit dated
> 2026-04-29 (dtw_distance abs diff 0.0). TSL engine module's
> custom numpy DTW core with Sakoe-Chiba window + step_pattern
> variants plausibly equivalent at base case but variants
> engine-specific. Downstream post-processing (warping path
> extraction + time-varying lag extraction + lag segmentation +
> multi-table output) is engine-specific and NOT covered by
> parity audit; requires expert review for published use.
> Pre-Path α expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique dtw_alignment_lag implements three
> layered computations with downstream topology (Layer 3
> post-processing follows DTW core; analogous to rolling_ccf_lag
> downstream topology). **Layer 1 — DTW math at harness reference
> DP + dtaidistance.dtw:** validated per Phase 3 reference parity
> infrastructure. **Reference:** Python `dtaidistance.dtw`
> (dtaidistance 2.4.0). **Verdict:** PASS Pattern A cross-package
> bit-exact at machine precision; dtw_distance abs diff 0.0 (exact
> match). **Audit date:** 2026-04-29. **Catalog mapping:** 1:1
> catalog↔wrapper (distinct from multi-map p3_ccf-covered triple).
> **Layer 2 — engine module DTW core:** TSL engine module
> (`engine/techniques/dtw_alignment_lag.py` lines 416-468 forward
> DP) implements custom numpy DTW with Sakoe-Chiba window constraint
> + step_pattern variants (symmetric1 diagonal-only OR symmetric2
> diagonal + horizontal + vertical); pre-processing helpers
> (subsampling + z-normalization lines 140-164) fold into Layer 2;
> bit-exact equivalence to validated DP plausible at base case
> (no window, symmetric2 default) but parameter variants
> unverified. **Layer 3 — engine-specific post-processing
> downstream:** engine module applies four post-processing
> sub-components AFTER DTW core: (3a) warping path backtrack +
> extraction (lines 469-491); (3b) time-varying lag extraction via
> x_to_y dict + per-index averaging + carry-forward heuristic
> (lines 178-198); (3c) lag segmentation via change-point heuristic
> with deviation threshold 2.0 (lines 494-525); (3d) multi-table
> output construction (lag time-series + warping path + segments
> + summary). Layer 3 post-processing is engine-specific and NOT
> covered by p3_dtw parity audit; correctness requires expert
> review of backtrack logic + lag extraction heuristic +
> segmentation threshold + output construction. **Fixture:**
> seeded single-fixture (warped sinusoid pair, T=100,
> warp_factor=1.2, σ=0.05, seed=42); parameter-sensitivity
> coverage NOT established; Q3b extension pending. Pre-Path α
> expert review status; expert review pending end-of-Phase-7+-
> work-program.

*Pattern (iii) Risk model documentation:*
> dtw_alignment_lag validation: TSL Tier II.bit-exact (Layer 1 DTW
> math at harness reference DP + dtaidistance.dtw only). Reference:
> Python `dtaidistance.dtw` (dtaidistance 2.4.0). Audit:
> `tools/reference_parity/reports/p3_dtw_audit.md` dated 2026-04-29.
> Verdict: PASS Pattern A cross-package bit-exact at machine
> precision (dtw_distance abs diff 0.0). Catalog mapping: 1:1
> catalog↔wrapper. **Three-layer downstream-topology framing:**
> Layer 1 (dtaidistance.dtw) parity-validated; Layer 2 (engine DTW
> core with Sakoe-Chiba window + step_pattern variants +
> pre-processing helpers) bit-exact equivalence at base case
> plausible but variants engine-specific; Layer 3 (post-processing)
> NOT parity-validated, engine-specific implementation requires
> expert review of (3a) warping path backtrack + (3b) time-varying
> lag extraction + (3c) lag segmentation + (3d) multi-table
> output construction. Fixture: single-seeded; Q3b extension
> pending. Risk attribution conditional on (a) parameter
> configurations matching fixture-similar conditions AND (b)
> Layer 2 engine DTW core + window/step_pattern variants
> correctness AND (c) Layer 3 post-processing correctness across
> 3a/3b/3c/3d sub-components — (b) + (c) require expert review.
> Pre-Path α expert review status.

*Pattern (iv) Internal use disclosure:*
> dtw_alignment_lag DTW math layer (harness reference DP +
> dtaidistance.dtw) cross-package bit-exact validated; 1:1
> catalog↔wrapper. Layer 2 (engine DTW core + Sakoe-Chiba window +
> step_pattern variants + pre-processing helpers) bit-exact
> equivalence at base case plausible but variants engine-specific;
> Layer 3 (post-processing: warping path extraction + time-varying
> lag extraction + lag segmentation + multi-table output) NOT
> parity-validated, requires expert review; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):**
  Extracted/cited. Reference selection from p3_dtw_audit.md verbatim
  (Python `dtaidistance.dtw` 2.4.0); verdict + Pattern + date +
  numerics verbatim from audit. Three-layer downstream-topology
  framing extracted per S17 STOP 2 empirical investigation (Step 0
  (e)+(f)+(g) reads of p3_dtw_audit.md + p3_dtw.py harness + 526
  LOC engine module) + S15 rolling_ccf_lag three-layer-downstream
  precedent + α disposition ratification. Layer 2 (lines 416-468
  forward DP + 140-164 pre-processing) + Layer 3 sub-components
  3a/3b/3c/3d (lines 469-491 + 178-198 + 494-525 + multi-table
  construction) empirically grounded per Step 0 (g) verbatim line
  ranges. Catalog mapping (1:1) verified per scope_reframing §2
  line 129. Verify-state-at-first-consumption sub-discipline 10th
  instance application (forward-at-authoring + STOP 2 caught 1:1
  simple-case framing assumption empirical falsification at Step 0
  per A9 Class B mitigation pattern; matures from S15 9th-instance
  proactive-with-assumption-falsification-catch with reinforced
  pattern at second observation — Stage 3 lifecycle now n=2
  observations calibrating it as established pattern).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at fifth-technique selection (user ratified
  dtw_alignment_lag under Tier 2 case-against framing per Phase 7+
  S16-absorption-close proposal; case-against weighted but not
  invalidating per efficient ratification disposition). Pro-forma
  elements present per Mark 3 efficient-ratification pattern
  (operating-context preservation per Workstream B §5.3). **Q-B
  pattern persists at n=6 across S12 + S13 + S14b + S14c + S15 +
  S17; well past n=4 codification candidate threshold; sub-class
  refinement candidate at next §19.4 absorption cycle** (cross-
  reference §4 forward instrumentation note "Q-B audit checklist
  operational pattern" codified at S16-absorption). Not pro-forma
  across all upstream decisions for this technique (three-layer
  downstream-topology framing required STOP 2 empirical
  investigation + α disposition ratification + Layer 3 sub-component
  4-fold enumeration; catalog-mapping framing precedent note
  required substantive Step 0 + S17 STOP 2 disposition trigger
  framing; Layer 2/Layer 3 boundary clarification required
  operational distinction codification per Adjustment).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (DTW math at harness reference DP +
  dtaidistance.dtw)** per bit-exact 0.0 abs diff PASS verdict
  against canonical Python `dtaidistance.dtw` C-implementation.
  **Conditional for Layer 2 (engine DTW core with Sakoe-Chiba
  window + step_pattern variants + pre-processing helpers)** —
  requires expert review of engine implementation OR engine-output
  cross-check against validated harness reference DP (analogous to
  S15 Layer 2 framing). Default-settings equivalence (no window,
  symmetric2) plausible but variant correctness (window
  constraint handling + symmetric1 diagonal-only path; subsampling
  threshold + z-normalization correctness) unverified.
  **Conditional for Layer 3 (post-processing)** — requires expert
  review of: 3a warping path backtrack logic (step_pattern-aware
  minimum-cost step selection); 3b time-varying lag extraction
  heuristic (x_to_y dict + per-index averaging + carry-forward);
  3c lag segmentation threshold + minimum-segment-length
  appropriateness; 3d multi-table output construction for
  analytical use case. Defensible to all three audiences with
  disclosure language as drafted: published audience (three-layer
  downstream-topology framing transparent); Morgan Stanley
  compliance review (precise audit citation + tier taxonomy +
  Layer 1 / Layer 2 / Layer 3 scope delineation + catalog-mapping
  precedent note); external expert reviewer at Path α close
  (verbatim audit numerics + honest disclosure of what's validated
  and what's not + Q3b extension pending + Layer 2 + Layer 3
  sub-components expert review scope identified with specific
  line ranges).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-to-high. dtw_alignment_lag is typically used for
  time-varying lead-lag analysis in financial/macro time-series
  research where non-linear time distortions complicate cross-
  correlation interpretation; widely cited DTW methodology with
  warping path interpretation as lead-lag tracking. **Layer-specific
  retraction surface (per S17 three-layer downstream-topology
  framing):**
  - Layer 1 (DTW math at harness reference DP + dtaidistance.dtw):
    LOW; bit-exact 0.0 abs diff PASS verdict against canonical
    dtaidistance C-implementation; expert review surfacing
    upstream error would affect dtw_alignment_lag specifically
    (NO multi-map propagation risk distinct from S15 multi-map
    framing; 1:1 catalog↔wrapper).
  - Layer 2 (engine DTW core + Sakoe-Chiba window + step_pattern
    variants + pre-processing helpers): MEDIUM analogous to S15
    Layer 2 (engine implementation equivalence) + engine-specific
    window/step_pattern variant correctness + pre-processing
    heuristic appropriateness.
  - Layer 3 (downstream post-processing): MEDIUM-HIGH specifically
    for dtw_alignment_lag (NOT shared with other catalog techniques
    due to 1:1 mapping). Downstream post-processing is the
    operational distinctive of dtw_alignment_lag — DTW methodology's
    value-add over raw CCF for time-varying lead-lag detection
    IS the warping path extraction + local lag extraction +
    segmentation functionality; expert review surfacing material
    errors (backtrack step-pattern correctness; x_to_y averaging
    heuristic; segmentation threshold; multi-table output
    construction) would invalidate the time-varying lead-lag claim
    motivating dtw_alignment_lag use over raw cross_correlation_lag.
    **Analogous to S15 Layer 3 MEDIUM-HIGH but for DTW methodology
    distinctive ("time-varying lead-lag claim invalidated" vs S15's
    "regime/break-aware claim invalidated"); both downstream-topology
    Layer 3 surfaces operationally distinct but parallel risk
    structures.**

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; fifth technique to enter status per S17
ratification; first 1:1 catalog↔wrapper entry under layered framing.
**S17 three-layer-downstream framing applies to 1:1 catalog entry**
(distinct from S15 three-layer-downstream for multi-map p3_ccf-covered
triple); framing shape orthogonal to catalog mapping per S17 empirical
observation. A10 sub-class disposition (Sub-class 2c n=2 OR new
Sub-class 2d 1:1-three-layer-downstream n=1) deferred to next §19.4
absorption cycle. **A9 Class B counter post-S17: n=2 ACTIVE**
(codification threshold reached per A9 forward instrumentation;
sub-class refinement candidate for next §19.4 absorption).

### gcc_phat_delay (Phase 7+ S18; sixth §2.5 entry; FIRST Tier IV Q1 entry; FIRST Pattern A.3 self-parity Q1 entry; completes Block 1 Causality; THREE-LAYER DOWNSTREAM-TOPOLOGY framing per S15/S17 precedent + Tier IV adaptation per S18 STOP 2 empirical investigation + β disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
IV — Phase 3 self-parity / paper-formula validated (Pattern A.3 per
scope_reframing §2 lines 159-168 codification; ~10 wrappers per
P-3 v1.2.0 §1 estimate). **CRITICAL DISTINCTION from S12-S17
Tier II.bit-exact entries:** gcc_phat_delay validation is paper-
formula self-parity (Knapp-Carter 1976 formula reimplemented and
validated against itself; harness validates from-scratch
implementation against same from-scratch implementation), NOT
cross-package bit-exact validation. **Important nuance (three-layer
downstream-topology framing per S18 β disposition; analogous to S15
rolling_ccf_lag + S17 dtw_alignment_lag precedent with Tier IV +
Pattern A.3 self-parity adaptations):** tier classification applies
to Layer 1 (Knapp-Carter 1976 paper-formula self-parity at harness
`_gcc_phat` reproducibility); Layer 2 (engine module GCC-PHAT core
with 4 weighting variants + interpolation + zero-mean normalization)
plausibly equivalent at base case but variants engine-specific;
Layer 3 (engine-specific post-processing DOWNSTREAM of GCC core:
GCC fftshift + lag-axis construction + max_lag restriction + peak
detection + bootstrap CI + multi-table output + sampling-frequency
handling) NOT covered by p3_gcc_phat parity audit. See Validation
claim scope below for Pattern A.3 self-parity caveat + Layer 1
retraction surface calibration (MEDIUM, elevated from S17 LOW per
self-parity weaker than cross-package).

**Framing precedent note (Tier IV three-layer-downstream;
operationally distinct from Tier II.bit-exact three-layer-downstream
of S15+S17):** gcc_phat_delay is 1:1 catalog↔wrapper mapping per
p3_gcc_phat audit Wrapper field (`engine/techniques/gcc_phat_delay.py`
sole engine module); analogous to S17 dtw_alignment_lag 1:1 entry
under layered framing but with Tier IV (paper-formula self-parity)
instead of Tier II.bit-exact (cross-package). Three-layer-downstream
framing applies per S18 STOP 2 empirical finding (engine module 386
LOC with 4 weighting variants + interpolation + peak detection +
bootstrap CI + multi-table output is structurally analogous to S15/
S17 Layer 3 post-processing complexity). **Tier IV adaptation** per
Workstream B §3 Tier IV templates (Pattern A.3 self-parity framing
replaces Tier II.bit-exact cross-package framing): Layer 1
validation evidence is paper-formula reproducibility (harness
validates Knapp-Carter formula against itself; reproducibility not
cross-package correctness); Layer 2 + Layer 3 substantively
unchanged in framing pattern from S15/S17 (engine-specific code
unverified at audit). **A10 sub-class disposition deferred to next
§19.4 absorption cycle:** S18 calibrates new Tier IV three-layer-
downstream sub-class (distinct from S15/S17 Tier II.bit-exact
three-layer-downstream); A10 taxonomy decisions (including pending
S17 2c-vs-2d resolution AND S18 Tier IV three-layer-downstream
sub-class placement) deferred per accumulation pattern.

**Reference:** From-scratch self-parity (Knapp-Carter 1976 formula)
**Verdict:** PASS Pattern A bit-exact under Pattern A.3 self-parity
caveat (Layer 1 only; reproducibility validated NOT cross-package
correctness; see Validation claim scope for Layer 2 + Layer 3
coverage + self-parity caveat operational implication)
**Audit:** `tools/reference_parity/reports/p3_gcc_phat_audit.md`
**Audit date:** 2026-04-29
**delay abs diff:** 0.0 (exact, integer-valued)

**Source files (Tier IV three-layer-downstream per S18 β framing
extending S15/S17 precedent with Tier IV adaptations):**
`tools/reference_parity/harness/checks/p3_gcc_phat.py` lines 32-43
(harness `_gcc_phat` reference function defined INSIDE p3_gcc_phat.py;
12-LOC implementation of Knapp-Carter 1976 formula: FFT + cross-power
spectrum + PHAT weighting + IFFT + argmax delay extraction)
+ `tools/reference_parity/harness/checks/p3_gcc_phat.py` lines 65-78
(BOTH run_tsl AND run_reference call SAME `_gcc_phat(x, y)` function;
literal-identity self-parity — both arms compute byte-identical
output; harness comment line 69-71: "TSL's gcc_phat_delay computes
the same formula — bypass wrapper output rounding by calling the
math directly (mirrors TSL implementation exactly)"; harness claims
to mirror engine module but engine is materially more complex per
Step 0 (g))
+ `engine/techniques/gcc_phat_delay.py` lines 116-145 (Layer 2:
engine module GCC-PHAT core; 4 weighting variants — phat default +
scot + roth + unfiltered per lines 129-139; FFT zero-padding for
interpolation per line 121 + preset interp_factor 1/4/16; zero-mean
normalization per lines 117-118; cross-power spectrum + weighting +
IFFT per lines 124-145; harness's `_gcc_phat` does NOT exercise
weighting variants, interpolation factor, OR zero-mean preprocessing)
+ `engine/techniques/gcc_phat_delay.py` lines 145-156 + 161-175 +
357-385 + 179-210 + multi-table construction (Layer 3 post-processing
sub-components; see Validation claim scope below)
+ `tools/reference_parity/reports/p3_gcc_phat_audit.md`

**Validation claim scope (TIER IV THREE-LAYER DOWNSTREAM-TOPOLOGY
per S18 amendment per S15/S17 precedent + Tier IV self-parity
adaptation):** TSL gcc_phat_delay output relies on three layered
computations with downstream topology (Layer 3 post-processing
follows GCC core; analogous to S15 rolling_ccf_lag + S17
dtw_alignment_lag downstream topology). p3_gcc_phat audit validates
Layer 1 (harness `_gcc_phat` vs same harness `_gcc_phat`; Pattern
A.3 self-parity at literal identity) at single seeded fixture
(delayed pair, T=512, true_delay=5, σ=0.05 noise, seed=42); delay
metric measures harness `_gcc_phat` self-consistency (0.0 abs diff
PASS), NOT cross-package agreement, NOT engine module GCC-PHAT core
agreement, NOT engine post-processing correctness.

- **Layer 1 — Knapp-Carter 1976 paper-formula self-parity (validated
  under Pattern A.3 SELF-PARITY caveat):** bit-exact 0.0 abs diff
  PASS verdict at literal-identity self-parity (both arms compute
  byte-identical output); validates **reproducibility of paper
  formula implementation**, NOT cross-package correctness.
  **Pattern A.3 self-parity caveat (per Workstream B §3 Tier IV
  template):** if Knapp-Carter 1976 paper formula implementation
  has subtle error (sign convention, FFT convention, indexing
  off-by-one, normalization convention), both harness arms
  propagate identically and 0.0 abs diff PASS verdict does NOT
  catch it. Pattern A.3 validates implementation matches paper-
  defined formula; paper formula is itself the reference. If
  paper formula is incorrect or under-specified, parity does not
  catch it. Materially weaker validation evidence than Tier
  II.bit-exact cross-package validation; Layer 1 retraction
  surface calibrated MEDIUM (elevated from S17 1:1 cross-package
  framing LOW).

- **Layer 2 — engine module GCC-PHAT core (custom numpy with 4
  weighting variants + interpolation + zero-mean normalization;
  plausibly equivalent to validated Knapp-Carter formula at base
  case but variants engine-specific):** Engine module lines 116-145
  implement GCC-PHAT with configurable weighting (phat default +
  scot + roth + unfiltered variants per lines 92-110 + 129-139);
  zero-padding for interpolation (line 121 with preset-based
  interp_factor 1/4/16); zero-mean normalization (lines 117-118);
  uses `np.fft.rfft` (real FFT) while harness uses `np.fft.fft`
  (complex FFT) — different code paths producing mathematically
  equivalent base-case output. Bit-exact equivalence to validated
  paper formula plausible at default settings (phat weighting +
  interp_factor=1 + zero-mean as pre-processing) but variants +
  interpolation + rfft-vs-fft code path unverified at p3_gcc_phat
  audit. **Compound with Layer 1 Pattern A.3 caveat:** Layer 2
  cross-validation against Layer 1 only validates against paper
  formula reproducibility, NOT cross-package correctness; expert
  review of paper formula AND engine implementation both required
  for full validation confidence.

- **Layer 3 — engine-specific post-processing DOWNSTREAM of GCC
  core (NOT parity-validated):** Engine module applies six
  post-processing sub-components AFTER GCC core distance + path
  computation:
  - **3a — GCC fftshift + lag-axis construction** (lines 145-150):
    fftshift to center zero lag; lag-axis with interpolation
    factor scaling. Engine-specific output preparation;
    correctness depends on fftshift convention matching IFFT
    output ordering.
  - **3b — max_lag restriction** (lines 152-156): boolean mask
    restricting GCC output to |lags_samples| ≤ max_lag (default
    N//4). Engine-specific heuristic; correctness depends on
    max_lag default + user-override appropriateness for
    analysis use case.
  - **3c — Peak detection with multi-peak support** (lines
    161-175 + `_find_peaks` helper lines 357-385): primary peak
    via argmax + secondary peaks via local-maximum detection
    (preset-based n_peaks 3/5/10); peak detection beyond argmax
    is engine-specific feature NOT in harness `_gcc_phat`.
  - **3d — Bootstrap CI for delay estimate** (lines 179-210):
    block bootstrap with block_size = n//10 (preset-based
    bootstrap count 0/200/1000); 95% percentile CI on delay
    estimate. Engine-specific uncertainty quantification NOT in
    harness `_gcc_phat`; correctness depends on block bootstrap
    appropriateness for delay-estimate uncertainty quantification.
  - **3e — Multi-table output construction** (3 tables: peaks +
    summary + GCC function): engine-specific output decomposition;
    correctness depends on table construction matching analytical
    use case.
  - **3f — Sampling-frequency handling** (lines 149-150 + 162-163):
    fs parameter for time-unit delay conversion; lags_time =
    lags_samples / fs. Engine-specific feature; correctness depends
    on fs interpretation matching user expectation.

Single-fixture parity established at literal-identity self-parity
for Layer 1 (0.0 abs diff bit-exact; reproducibility only NOT
cross-package); parameter-sensitivity coverage NOT established at
this validation tier (Q3b extension pending); Layer 2 closure
pending engine-output cross-check at default settings (phat
weighting + interp_factor=1) OR expert review of weighting variants
+ interpolation + zero-mean normalization implementation; Layer 3
closure pending expert review of post-processing sub-components
(engine-specific; no parity validation available; gcc_phat_delay's
value-add for time-delay estimation IS the Layer 3 post-processing
functionality — multi-peak detection + bootstrap CI + sampling-
frequency handling — so expert review of these sub-components is
operationally distinctive). **Critical Pattern A.3 self-parity
caveat at Layer 1:** even at base case, Layer 1 validates paper
formula reproducibility NOT correctness; if Knapp-Carter 1976
implementation has subtle error, downstream Layer 2 + Layer 3
inherit the error without detection. Expert review of paper formula
implementation correctness recommended alongside Layer 2 + Layer 3
review. Reference selection + tolerance specification AI-assisted
with user ratification per Phase 7+ work program; pre-Path α expert
review status; expert review pending end-of-work-program.

**Methodology disclosure templates** (per Workstream B §3 Tier IV
templates — paper-formula self-parity; multi-map cross-reference
N/A per 1:1 mapping; three-layer downstream-topology framing per S18
β disposition + S15/S17 precedent with Tier IV adaptations):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique gcc_phat_delay, paper-formula
> from-scratch reimplementation validated per Phase 3 audit dated
> 2026-04-29 (Pattern A.3 self-parity; Knapp-Carter 1976 formula
> reimplemented and validated against itself; delay abs diff 0.0).
> TSL engine module's GCC-PHAT core with 4 weighting variants +
> interpolation + zero-mean normalization plausibly equivalent at
> base case but variants engine-specific. Downstream post-processing
> (peak detection + bootstrap CI + sampling-frequency handling +
> multi-table output) is engine-specific and NOT covered by parity
> audit; requires expert review for published use. **Critical
> Pattern A.3 self-parity caveat:** validation is paper-formula
> reproducibility NOT cross-package correctness; if Knapp-Carter
> 1976 formula implementation has subtle error, both arms propagate
> identically. Pre-Path α expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique gcc_phat_delay validated against
> from-scratch reimplementation of Knapp-Carter 1976 paper-defined
> formula; Pattern A.3 self-parity (Tier IV per Phase 7+ tier
> taxonomy). **Paper reference:** Knapp & Carter 1976 (Generalized
> Cross-Correlation Method for Estimation of Time Delay).
> **Verdict:** PASS Pattern A bit-exact at machine precision; delay
> abs diff 0.0 (exact, integer-valued). **Audit date:** 2026-04-29.
> **Catalog mapping:** 1:1 catalog↔wrapper. **Validation claim
> scope:** TSL `_gcc_phat` harness implementation matches Knapp-
> Carter formula; paper formula is itself the reference. **Validation
> claim exclusion:** if Knapp-Carter formula implementation has
> subtle error (sign convention, FFT convention, indexing, or
> normalization), both arms propagate identically and 0.0 abs diff
> PASS verdict does NOT catch it. **Three-layer downstream-topology
> framing per S18 β disposition (Tier IV adaptation of S15/S17
> precedent):** **Layer 2 — engine module GCC-PHAT core:** TSL
> engine module (`engine/techniques/gcc_phat_delay.py` lines 116-145)
> implements GCC-PHAT with 4 weighting variants (phat / scot / roth
> / unfiltered) + zero-padding interpolation + zero-mean
> normalization; uses np.fft.rfft (real FFT) while harness uses
> np.fft.fft (complex FFT); bit-exact equivalence to validated
> Knapp-Carter formula plausible at base case (phat default +
> interp_factor=1) but variants unverified. **Layer 3 — engine-
> specific post-processing downstream:** engine module applies six
> post-processing sub-components AFTER GCC core: (3a) GCC fftshift
> + lag-axis construction; (3b) max_lag restriction; (3c) peak
> detection with multi-peak support via _find_peaks helper; (3d)
> bootstrap CI for delay estimate via block bootstrap; (3e)
> multi-table output construction; (3f) sampling-frequency
> handling. Layer 3 post-processing is engine-specific and NOT
> covered by p3_gcc_phat parity audit; correctness requires expert
> review across sub-components. **Fixture:** seeded single-fixture
> (delayed pair, T=512, true_delay=5, σ=0.05 noise, seed=42);
> parameter-sensitivity coverage NOT established; Q3b extension
> pending. Pre-Path α expert review status; expert review pending
> end-of-Phase-7+-work-program.

*Pattern (iii) Risk model documentation:*
> gcc_phat_delay validation: TSL Tier IV (paper-formula self-parity;
> Pattern A.3). Paper reference: Knapp-Carter 1976. Audit:
> `tools/reference_parity/reports/p3_gcc_phat_audit.md` dated
> 2026-04-29. Verdict: PASS Pattern A bit-exact at machine precision
> (delay abs diff 0.0). Catalog mapping: 1:1 catalog↔wrapper.
> Validated against from-scratch reimplementation; paper formula is
> reference; if paper formula incorrect or under-specified, parity
> does not catch it. **Three-layer downstream-topology framing:**
> Layer 1 (Knapp-Carter paper-formula self-parity) reproducibility-
> validated under Pattern A.3 caveat; Layer 2 (engine GCC core +
> weighting variants + interpolation + zero-mean) bit-exact
> equivalence at base case plausible but variants engine-specific;
> Layer 3 (post-processing) NOT parity-validated, engine-specific
> implementation requires expert review of (3a) fftshift + lag-axis
> + (3b) max_lag restriction + (3c) peak detection + (3d) bootstrap
> CI + (3e) multi-table output + (3f) sampling-frequency handling.
> Fixture: single-seeded; Q3b extension pending. Risk attribution
> conditional on (a) parameter configurations matching fixture-
> similar conditions AND (b) Knapp-Carter formula implementation
> correctness (self-parity caveat) AND (c) Layer 2 engine variant
> correctness AND (d) Layer 3 post-processing correctness — (b)+(c)+(d)
> require expert review. Pre-Path α expert review status.

*Pattern (iv) Internal use disclosure:*
> gcc_phat_delay paper-formula self-parity validated (Pattern A.3;
> Knapp-Carter 1976; reproducibility NOT cross-package); 1:1
> catalog↔wrapper. Layer 2 (engine GCC core + 4 weighting variants
> + interpolation + zero-mean) bit-exact equivalence at base case
> plausible but variants engine-specific; Layer 3 (post-processing:
> peak detection + bootstrap CI + multi-table output +
> sampling-frequency handling) NOT parity-validated, requires
> expert review; Pattern A.3 self-parity caveat applies (paper
> formula correctness inherits to downstream layers); pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):**
  Extracted/cited. Reference selection from p3_gcc_phat_audit.md
  verbatim ("from-scratch self-parity (Knapp-Carter 1976 formula)");
  verdict + Pattern A.3 + date + delay abs diff 0.0 verbatim from
  audit. Tier IV classification per scope_reframing §2 lines
  159-168 codification (Pattern A.3 self-parity / paper-formula
  validated). Three-layer downstream-topology framing extracted per
  S18 STOP 2 empirical investigation (Step 0 (e)+(f)+(g) reads of
  p3_gcc_phat_audit.md + p3_gcc_phat.py harness + 386 LOC engine
  module) + S15 rolling_ccf_lag + S17 dtw_alignment_lag three-layer-
  downstream precedent + β disposition + Tier IV adaptation
  ratification. Layer 2 (lines 116-145 engine GCC core) + Layer 3
  sub-components 3a/3b/3c/3d/3e/3f (lines 145-150 + 152-156 + 161-175
  + 357-385 + 179-210 + multi-table construction + 149-150) empirically
  grounded per Step 0 (g) verbatim line ranges. Catalog mapping
  (1:1) verified per audit Wrapper field sole engine module
  reference. **A9 Class A 5th instance acknowledgment:** S18 STOP 2
  caught tier-enumeration incompleteness in Chat Ratification 3
  (omitted Tier IV; 5 of 7 tiers enumerated); Class A counter
  n=4 → n=5 ACTIVE; codification reinforced at §19.4 LOCKED state;
  sub-class refinement candidate (identical-misattribution-recurrence
  sub-pattern instances #2+#4; tier-enumeration-omission sub-pattern
  instance #5) for next §19.4 absorption cycle. Verify-state-at-first-
  consumption sub-discipline 11th instance application (S18 STOP 2
  caught Tier II.bit-exact framing assumption + tier-enumeration
  omission at Step 0 per A9 Class A + Class B mitigation patterns
  both operating).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at sixth-technique selection (user ratified
  gcc_phat_delay under Tier 2 case-against framing per Phase 7+
  S17-close proposal as "completes Block 1 Causality"; case-against
  weighted but not invalidating per efficient ratification
  disposition). Pro-forma elements present per Mark 3 efficient-
  ratification pattern. **Q-B pattern persists at n=7 across S12 +
  S13 + S14b + S14c + S15 + S17 + S18; well past n=4 codification
  candidate threshold; sub-class refinement candidate at next §19.4
  absorption cycle** (cross-reference §4 forward instrumentation
  note "Q-B audit checklist operational pattern" codified at
  S16-absorption alongside A9 Class A 5th instance + Class B n=2 +
  A10 sub-class taxonomy 2c/2d/Tier-IV-three-layer-downstream
  resolution + Option II workflow + forward Q1 Step 0 discipline +
  Workstream B amendment cycle deferrals). Not pro-forma across all
  upstream decisions for this technique (Tier IV three-layer
  downstream-topology framing required STOP 2 empirical
  investigation + β disposition ratification + Pattern A.3 self-
  parity caveat surfacing + Layer 3 six-sub-component enumeration).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (Knapp-Carter 1976 paper-formula self-parity
  reproducibility)** per bit-exact 0.0 abs diff PASS verdict at
  literal-identity self-parity AND Pattern A.3 self-parity caveat
  explicit in disclosure language; reproducibility evidence
  defensible to all three audiences UNDER Pattern A.3 caveat
  acknowledging weaker validation than cross-package. **Conditional
  for Layer 2 (engine GCC core with weighting variants +
  interpolation + zero-mean normalization)** — requires expert
  review of engine implementation OR engine-output cross-check
  against harness `_gcc_phat` at default settings (phat +
  interp_factor=1) for base-case equivalence verification + variant
  correctness review. **Conditional for Layer 3 (post-processing)** —
  requires expert review of: 3a fftshift convention + 3b max_lag
  default heuristic + 3c peak detection logic + 3d bootstrap CI
  appropriateness for delay-estimate uncertainty + 3e multi-table
  output construction + 3f sampling-frequency handling. **Compound
  caveat across layers:** Pattern A.3 self-parity caveat at Layer 1
  applies to downstream Layer 2 + Layer 3 (if Knapp-Carter formula
  implementation has subtle error, all downstream layers inherit).
  Defensible to all three audiences with disclosure language as
  drafted: published audience (Tier IV three-layer downstream-
  topology framing transparent with Pattern A.3 caveat); Morgan
  Stanley compliance review (precise audit citation + tier taxonomy
  + Layer 1 / Layer 2 / Layer 3 scope delineation + Pattern A.3
  self-parity caveat surfacing); external expert reviewer at Path α
  close (verbatim audit numerics + honest disclosure of self-parity
  caveat + Q3b extension pending + Layer 2 + Layer 3 sub-components
  expert review scope identified + paper formula implementation
  correctness review recommended alongside engine review).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-to-high. gcc_phat_delay is typically used for time-delay
  estimation in signal processing + sensor-array applications
  (audio source localization; sensor synchronization; cross-modality
  alignment) where Knapp-Carter 1976 formula is canonical methodology
  with widespread implementation. **Layer-specific retraction
  surface (per S18 Tier IV three-layer downstream-topology framing
  with Pattern A.3 self-parity caveat):**
  - Layer 1 (Knapp-Carter paper-formula self-parity): **MEDIUM
    (elevated from S17 LOW per Pattern A.3 self-parity caveat).**
    Self-parity is materially weaker validation than cross-package
    bit-exact (S17 framing). If paper formula implementation has
    subtle error (sign convention; FFT convention; indexing
    off-by-one; normalization convention), 0.0 abs diff PASS
    verdict does NOT catch it because both arms compute byte-
    identical output. Expert review of paper formula
    implementation correctness recommended; Knapp-Carter 1976
    formula is well-established but TSL's specific implementation
    (FFT conventions; argmax handling; sign for delay
    interpretation) requires verification.
  - Layer 2 (engine GCC core + weighting variants + interpolation
    + zero-mean): MEDIUM analogous to S15/S17 Layer 2 (engine
    implementation equivalence) + engine-specific weighting variant
    correctness + interpolation factor correctness + zero-mean
    normalization appropriateness.
  - Layer 3 (downstream post-processing): MEDIUM-HIGH specifically
    for gcc_phat_delay (NOT shared with other catalog techniques
    due to 1:1 mapping). Downstream post-processing is the
    operational distinctive of gcc_phat_delay — GCC-PHAT
    methodology's value-add for time-delay estimation IS the peak
    detection + bootstrap CI uncertainty quantification +
    sampling-frequency handling functionality; expert review
    surfacing material errors (peak detection logic; bootstrap CI
    appropriateness; sampling-frequency interpretation) would
    invalidate the time-delay-estimate-with-uncertainty claim
    motivating gcc_phat_delay use. **Analogous to S15 Layer 3
    MEDIUM-HIGH and S17 Layer 3 MEDIUM-HIGH but for GCC-PHAT
    methodology distinctive ("time-delay-estimate-with-uncertainty
    claim invalidated" vs S17's "time-varying lead-lag claim
    invalidated" vs S15's "regime/break-aware claim invalidated");
    three downstream-topology Layer 3 surfaces now observed
    operationally distinct but parallel risk structures.**
  **Compound retraction surface (Pattern A.3 self-parity caveat
  Layer 1 + Layer 2 unverified + Layer 3 unverified):** if any
  combination of Layer 1 paper formula error + Layer 2 variant
  error + Layer 3 sub-component error surfaces, retraction
  surface compounds across layers; conservative publication
  pacing recommended pending Path α expert review.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; sixth technique to enter status per S18
ratification; **FIRST Tier IV Q1 entry under layered framing**
(distinct from S12-S17 all Tier II.bit-exact entries); FIRST Pattern
A.3 self-parity Q1 entry; **COMPLETES Block 1 Causality (first
catalog block fully Q1-amended per Q1 work program scope)**.
**S18 Tier IV three-layer-downstream framing** applies with Pattern
A.3 self-parity caveat at Layer 1 (retraction surface MEDIUM
elevated from S17 LOW per self-parity weaker than cross-package);
catalog-mapping-distinct from S15 multi-map three-layer-downstream;
tier-distinct from S15/S17 Tier II.bit-exact three-layer-downstream.
A10 sub-class disposition (Tier IV three-layer-downstream as new
sub-class observation distinct from existing 2a/2b/2c) deferred to
next §19.4 absorption cycle. **A9 Class A counter post-S18: n=5
ACTIVE** (tier-enumeration-omission sub-pattern instance #5;
identical-misattribution-recurrence sub-pattern observation across
instances #2+#4; sub-class refinement codification candidate per
next §19.4 absorption). **A9 Class B counter post-S18: n=2 ACTIVE**
(unchanged; revised default layered-framing-applicable expectation
empirically confirmed at S18 Step 0).

### adf_test (Phase 7+ S21; seventh §2.5 entry; FIRST Block 12 Stationarity Tests entry; FIRST three-layer-parallel-tests topology entry; A10 Sub-class 2d NEW topology candidate; THREE-LAYER-PARALLEL-TESTS framing per S21 STOP 2 empirical investigation + γ disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2 per scope_reframing §2 line 130). **Important nuance
(three-layer-parallel-tests framing per S21 γ disposition; NOVEL
topology distinct from S14c three-layer-upstream + S15/S17/S18
three-layer-downstream):** tier classification applies to Layer 1
(statsmodels.tsa.stattools.adfuller vs R urca::ur.df); Layer 2
(engine module ADF single-test orchestration: Schwert lag bound +
AIC autolag + trend detection + NaN handling) plausibly equivalent
at base pinned config but variants engine-specific; Layer 3 (joint
triage mode parallel tests + verdict computation; DEFAULT FOR RIBBON
PATH) NOT covered by p3_adf parity audit. **Critical operational
implication:** published-research output from `adf_test` ribbon
invocation is the joint verdict from ADF + KPSS + PP, NOT pure ADF;
p3_adf audit validates single pinned ADF call only; Layer 3
operational distinctive drives ribbon publication output but has
ZERO parity validation. See Validation claim scope below.

**Framing precedent note (1:1 catalog↔wrapper; NOVEL three-layer-
parallel-tests topology):** adf_test is 1:1 catalog↔wrapper mapping
per p3_adf audit Wrapper field (`engine/techniques/adf_test.py` sole
engine module). Three-layer-parallel-tests topology applies per S21
STOP 2 empirical finding: harness invokes statsmodels.adfuller
directly at pinned single-test config; engine module uses SAME
statsmodels.adfuller at math layer (clean engine-uses-same-function
pattern per Forward Q1 Step 0 discipline §4.7) BUT engine module
extends substantially beyond harness exercise via joint triage mode
(default for ribbon path) running ADF + KPSS + PP in parallel and
computing joint verdict. **NOVEL topology distinct from existing
A10 sub-classes:**
- S14c three-layer-upstream (Layer 2b pipeline BEFORE math; AR-
  prewhitening for prewhitened_ccf_lag)
- S15/S17 three-layer-downstream Tier II.bit-exact (Layer 3 pipeline
  AFTER math; rolling_ccf_lag + dtw_alignment_lag)
- S18 three-layer-downstream Tier IV variant (Sub-class 2c-IV;
  gcc_phat_delay Pattern A.3 self-parity)
- **S21 three-layer-parallel-tests NEW (Layer 3 INVOKES PARALLEL
  math calls + computes verdict from combined results; adf_test
  joint triage mode running ADF + KPSS + PP)**

**Engine-extends-beyond-harness pattern characterization (NEW per
§4.7 Forward Q1 Step 0 discipline forward observation):** adf_test
is NOT harness-bypasses-engine outlier (S14a p3_ccf + S18 p3_gcc_phat
pattern); engine module uses SAME statsmodels.adfuller function as
harness. Pattern instead is engine-extends-beyond-harness — engine
module has substantial additional functionality (joint triage mode
+ KPSS + PP integration) beyond what harness exercises. Forward
observation for §4.7 codification refinement at next Workstream B
amendment cycle if pattern recurs (KPSS + PP entries may surface
analogous pattern).

**A10 sub-class disposition deferred to next §19.4 absorption cycle:**
S21 first-instance observation calibrates Sub-class 2d (three-layer-
parallel-tests) baseline candidate (distinct from existing 2a + 2b
+ 2c + 2c-IV). Codification deferred per accumulation pattern;
absorption #3 resolves Sub-class 2d codification + Sub-class 2c-IV
n=2 if observed + Block 1 Causality completion milestone + A9
Class A 5th sub-pattern accumulation + A9 Class B n=3 codification
reinforcement + etc.

**Reference:** R `urca::ur.df` (urca 1.3.4)
**Verdict:** PASS Pattern A bit-exact (Layer 1 only; see Validation
claim scope for Layer 2 + Layer 3 coverage)
**Audit:** `tools/reference_parity/reports/p3_adf_audit.md`
**Audit date:** 2026-04-29
**test_statistic (tau) abs diff:** 1.07e-14 (TSL -9.46555379266110
vs Reference -9.46555379266109; rel diff 1.13e-15)

**Source files (three-layer-parallel-tests per S21 γ framing):**
`tools/reference_parity/harness/checks/p3_adf.py` lines 62-73
(harness TSL arm invokes `statsmodels.tsa.stattools.adfuller`
directly with pinned LAG=1, autolag=None, regression="c"; returns
test_statistic + p_value + n_used)
+ `tools/reference_parity/harness/checks/p3_adf.py` lines 75-99
(harness reference arm invokes R `urca::ur.df(y, type="drift",
lags=1)` via RBridge; extracts tau-stat + 5pct critical value)
+ `engine/techniques/adf_test.py` line 23 + lines 151-153 (Layer 1
shared math: engine module imports SAME `statsmodels.tsa.stattools.adfuller`
function harness validates; `_run_adf_single` helper calls
`adfuller(clean, maxlag=maxlag, regression=regression, autolag=autolag)`
at line 151)
+ `engine/techniques/adf_test.py` lines 351-474 + 57-118 + 65-88
(Layer 2: engine ADF single-test orchestration; `_run_single_test`
helper lines 351-474 + Schwert lag bound `_schwert_bound` lines
57-62 + trend detection `_detect_trend` lines 91-118 + NaN handling
`_prepare_series` lines 65-88 + regression specification allowlist
gating lines 282-326)
+ `engine/techniques/adf_test.py` lines 506-714 + 200-228 + 559-565
+ 568-650 (Layer 3: joint triage mode; `_run_triage` helper lines
506-714 + joint verdict logic `_joint_verdict` lines 200-228 + PP
tie-breaker for CONFLICTING lines 559-565 + triage table + summary
construction lines 568-650)
+ `engine/techniques/adf_test.py` lines 231-239 (Layer 3 dispatch:
`_is_triage_mode` helper detecting ctx.run_id prefix; udf_* → single
test; pane_* / anything else → triage default for ribbon path)
+ `tools/reference_parity/reports/p3_adf_audit.md`

**Validation claim scope (THREE-LAYER-PARALLEL-TESTS per S21
amendment per S14c upstream + S15/S17/S18 downstream precedent + γ
parallel-tests topology disposition):** TSL adf_test output relies
on three layered computations with parallel-tests topology (Layer 3
invokes parallel math calls — KPSS + PP alongside ADF — and computes
joint verdict from combined results; contrasts with S14c upstream
topology where Layer 2b prewhitening precedes math AND S15/S17/S18
downstream topology where Layer 3 post-processing follows math).
p3_adf audit validates Layer 1 (statsmodels.adfuller) vs R urca::ur.df
at single seeded fixture (stationary AR(1), φ=0.7, σ=1.0, T=500,
seed=42, burn-in 100, LAG=1 pinned, regression="c"); test_statistic
metric measures statsmodels.adfuller tau output vs urca::ur.df tau
agreement (abs diff 1.07e-14 PASS), NOT engine module orchestration
correctness, NOT joint triage mode correctness, NOT KPSS or PP
integration correctness.

- **Layer 1 — statsmodels.adfuller math layer (validated):** bit-
  exact PASS verdict at machine precision (abs diff 1.07e-14; rel
  diff 1.13e-15); parity covers ADF tau statistic at OLS-on-
  differenced-series regression with pinned LAG=1 + autolag=None +
  regression="c"; MacKinnon critical values via statsmodels +
  urca::ur.df identical tables; both packages compute identical
  closed-form statistic given identical lag specification.

- **Layer 2 — engine module ADF single-test orchestration (plausibly
  equivalent at pinned config but variants engine-specific):**
  Engine module uses SAME `statsmodels.tsa.stattools.adfuller`
  function harness validates (clean engine-uses-same-function
  pattern per §4.7 Forward Q1 Step 0 discipline; NOT harness-
  bypasses-engine outlier). Engine ADF single-test mode (`_run_single_test`
  lines 351-474) extends beyond harness exercise via: Schwert lag
  bound rule (max_lag = floor(12 × (T/100)^(1/4)); lines 57-62) vs
  harness pinned LAG=1; AIC autolag selection (default per `autolag`
  parameter) vs harness pinned autolag=None; regression specification
  allowlist gating ({c, ct, ctt, n, nc}; lines 282-326) vs harness
  pinned regression="c"; trend detection heuristic (t-stat threshold
  2.0 on linear time regressor; lines 91-118; advisory note for
  regression='c' on apparently trending series); per-series NaN
  handling (edge NaN strip + interior NaN linear interp; lines 65-88);
  multi-series support (loop through `all_series`). Bit-exact
  equivalence to validated math plausible at base pinned config
  (LAG=1, autolag=None, regression="c"; no trend; no NaN) but variants
  unverified at p3_adf audit.

- **Layer 3 — joint triage mode parallel tests + verdict computation
  DEFAULT FOR RIBBON PATH (NOT parity-validated; engine-specific
  operational distinctive driving published research output):**
  Engine module applies five Layer 3 sub-components in triage mode
  (default for ribbon invocations per `_is_triage_mode` dispatch
  lines 231-239 detecting ctx.run_id prefix):
  - **3a — Triage dispatch** (lines 231-239): ctx.run_id prefix
    detection; `udf_*` → single-test mode; `pane_*` or anything else
    → triage mode default. Engine-specific dispatch logic; ribbon
    publication output goes through triage path.
  - **3b — Parallel KPSS + PP test invocation** (lines 511-512 +
    529-535 in `_run_triage`): imports `_run_kpss_single` from
    techniques.kpss_test + `_run_pp_single` from techniques.pp_test;
    invokes both tests alongside ADF on same fixture; KPSS regression
    spec ("ct" if ADF regression "ct" else "c"); PP trend spec ("ct"
    if ADF regression "ct" else "n" if regression in {n, nc} else
    "c"). Engine-specific parallel-tests orchestration NOT exercised
    by harness.
  - **3c — Joint verdict logic** (`_joint_verdict` lines 200-228):
    four-outcome verdict computation based on ADF + KPSS rejection
    pattern: (ADF rejected + KPSS not rejected) → STATIONARY;
    (ADF not rejected + KPSS rejected) → UNIT ROOT (I(1));
    (both rejected) → CONFLICTING; (neither rejected) → INCONCLUSIVE.
    Engine-specific verdict heuristic; correctness depends on ADF
    + KPSS hypothesis-test rejection logic being appropriate for
    joint stationarity inference.
  - **3d — PP tie-breaker for CONFLICTING verdicts** (lines 559-565):
    if joint verdict is CONFLICTING, PP test acts as tie-breaker;
    "PP agrees with ADF (unit root rejected)" if PP rejects null;
    "PP agrees with KPSS (unit root not rejected)" if PP fails to
    reject. Engine-specific tie-breaker heuristic; correctness
    depends on PP rejection logic being appropriate for tie-breaking
    between ADF + KPSS disagreement.
  - **3e — Triage table + per-series summary construction** (lines
    568-650): triage table with per-test rows per series + critical
    value detail tables + per-series summary string with joint
    verdict + per-test rejection phrases + trend advisory if
    applicable. Engine-specific output construction; correctness
    depends on summary phrasing + table construction matching
    published-research presentation expectations.

Single-fixture parity established at machine precision for Layer 1
(test_statistic abs diff 1.07e-14); parameter-sensitivity coverage
NOT established at this validation tier (Q3b extension pending);
Layer 2 closure pending engine-output cross-check at base pinned
config OR expert review of Schwert + AIC + trend detection + NaN
handling implementation; Layer 3 closure pending expert review of
joint triage mode + KPSS + PP integration + joint verdict heuristic
+ PP tie-breaker (engine-specific; no parity validation available;
adf_test ribbon publication output IS the joint verdict, so expert
review of Layer 3 is operationally distinctive AND high-stakes).
**Critical Layer 3 framing per ribbon-default-publication context:**
published-research user invoking `adf_test` from ribbon receives
joint verdict from three tests + heuristic verdict computation;
publishing under their name relies on Layer 3 correctness, not just
Layer 1 ADF math. Expert review of Layer 3 sub-components 3b/3c/3d
operationally critical. Reference selection + tolerance specification
AI-assisted with user ratification per Phase 7+ work program;
pre-Path α expert review status; expert review pending end-of-work-
program.

**Methodology disclosure templates** (per Workstream B §3 Tier
II.bit-exact templates; three-layer-parallel-tests framing per S21
γ disposition; Bundle option II depth distribution):

*Pattern (i) Research note footnote:*
> This analysis uses TSL technique adf_test. ADF math layer
> (statsmodels.tsa.stattools.adfuller) is cross-package bit-exact
> parity validated against R `urca::ur.df` (urca 1.3.4) per Phase 3
> audit dated 2026-04-29 (test_statistic abs diff 1.07e-14). TSL
> engine module ADF single-test orchestration (Schwert lag bound +
> AIC autolag + trend detection + NaN handling) plausibly equivalent
> at base pinned config but variants engine-specific. **Joint triage
> mode (DEFAULT for ribbon invocations; engine module's default
> publication output): ADF + KPSS + PP parallel tests + joint verdict
> + PP tie-breaker** is engine-specific and NOT covered by parity
> audit; requires expert review for published use. Published-research
> output from ribbon invocation is the joint verdict, NOT pure ADF
> result. Pre-Path α expert review status.

*Pattern (ii) Technical appendix:*
> Methodology: TSL technique adf_test implements three layered
> computations with parallel-tests topology (Layer 3 invokes
> parallel math calls — KPSS + PP alongside ADF — and computes joint
> verdict from combined results; NOVEL topology distinct from
> upstream/downstream layered framings of prior Q1 entries). **Layer
> 1 — statsmodels.adfuller math layer:** validated per Phase 3
> reference parity infrastructure. **Reference:** R `urca::ur.df`
> (urca 1.3.4). **Verdict:** PASS Pattern A.2 bit-exact at machine
> precision; test_statistic (tau) abs diff 1.07e-14 (TSL -9.46555379266110
> vs Reference -9.46555379266109; rel diff 1.13e-15). **Audit date:**
> 2026-04-29. **Catalog mapping:** 1:1 catalog↔wrapper. **Layer 2 —
> engine module ADF single-test orchestration:** TSL engine module
> (`engine/techniques/adf_test.py` line 23 + lines 151-153) uses
> SAME statsmodels.adfuller function harness validates (clean
> engine-uses-same-function pattern); orchestration extends beyond
> harness exercise via Schwert lag bound (`_schwert_bound` lines
> 57-62; max_lag = floor(12 × (T/100)^(1/4))) + AIC autolag
> selection + regression specification allowlist gating + trend
> detection heuristic + per-series NaN handling + multi-series
> support; bit-exact equivalence to validated math plausible at base
> pinned config (LAG=1, autolag=None, regression="c") but variants
> unverified. **Layer 3 — joint triage mode parallel tests + verdict
> computation (DEFAULT FOR RIBBON PATH):** engine module applies
> five Layer 3 sub-components in triage mode (default for ribbon
> invocations per ctx.run_id prefix dispatch): (3a) triage dispatch;
> (3b) parallel KPSS + PP test invocation alongside ADF; (3c) joint
> verdict logic (4 outcomes: STATIONARY / UNIT ROOT I(1) /
> CONFLICTING / INCONCLUSIVE); (3d) PP tie-breaker for CONFLICTING
> verdicts; (3e) triage table + per-series summary construction.
> Layer 3 is engine-specific and NOT covered by p3_adf parity audit;
> correctness requires expert review of joint verdict heuristic +
> KPSS/PP integration + PP tie-breaker logic. **Published-research
> output from ribbon invocation is the joint verdict, NOT pure ADF
> result.** **Fixture:** seeded single-fixture (stationary AR(1),
> φ=0.7, σ=1.0, T=500, seed=42, burn-in 100; LAG=1 pinned);
> parameter-sensitivity coverage NOT established at this validation
> tier; Q3b extension pending. Pre-Path α expert review status;
> expert review pending end-of-Phase-7+-work-program.

*Pattern (iii) Risk model documentation:*
> adf_test validation: TSL Tier II.bit-exact (Layer 1 statsmodels.adfuller
> math layer only). Reference: R `urca::ur.df` (urca 1.3.4). Audit:
> `tools/reference_parity/reports/p3_adf_audit.md` dated 2026-04-29.
> Verdict: PASS Pattern A.2 bit-exact at machine precision
> (test_statistic abs diff 1.07e-14). Catalog mapping: 1:1
> catalog↔wrapper. **Three-layer-parallel-tests framing (NOVEL
> topology):** Layer 1 (statsmodels.adfuller) parity-validated;
> Layer 2 (engine ADF orchestration: Schwert + AIC + trend detection
> + NaN handling) bit-exact equivalence at base pinned config
> plausible but variants engine-specific; Layer 3 (joint triage
> mode parallel tests + verdict computation; DEFAULT FOR RIBBON
> PATH) NOT parity-validated, engine-specific implementation requires
> expert review of (3a) triage dispatch + (3b) parallel KPSS + PP
> invocation + (3c) joint verdict logic + (3d) PP tie-breaker +
> (3e) triage table/summary construction. **Critical risk
> consideration:** ribbon-default publication output is joint
> verdict from three tests + heuristic verdict computation, NOT
> pure ADF; risk attribution from ribbon invocation conditional on
> (a) parameter configurations matching fixture-similar conditions
> AND (b) Layer 2 engine ADF orchestration correctness AND (c)
> Layer 3 joint triage mode + KPSS + PP + verdict heuristic
> correctness — (b) + (c) require expert review. Pre-Path α expert
> review status.

*Pattern (iv) Internal use disclosure:*
> adf_test ADF math layer (statsmodels.adfuller) cross-package
> bit-exact validated against R `urca::ur.df`; 1:1 catalog↔wrapper.
> Layer 2 (engine ADF orchestration: Schwert + AIC + trend +
> NaN) bit-exact equivalence at base pinned config plausible but
> variants engine-specific; Layer 3 (joint triage mode parallel
> tests + KPSS + PP + verdict logic; DEFAULT FOR RIBBON PATH) NOT
> parity-validated, requires expert review; **ribbon publication
> output IS the joint verdict, NOT pure ADF**; pre-Path α.

**Validation provenance audit checklist (per Workstream B §1; applied
at technique close):**

- **Q-A (decision substance extracted/cited vs inferred):** Extracted/
  cited. Reference selection from p3_adf_audit.md verbatim (R
  `urca::ur.df` 1.3.4); verdict + Pattern + date + numerics (test_statistic
  abs diff 1.07e-14; TSL -9.46555379266110 vs Reference -9.46555379266109)
  verbatim from audit. Three-layer-parallel-tests framing extracted
  per S21 STOP 2 empirical investigation (Step 0 (e)+(f)+(g) reads
  of p3_adf_audit.md + p3_adf.py harness + 756 LOC engine module) +
  S14c upstream / S15/S17/S18 downstream layered framing precedent
  + γ parallel-tests topology disposition. Layer 2 (lines 351-474 +
  57-118 + 65-88 + 282-326) + Layer 3 sub-components 3a/3b/3c/3d/3e
  (lines 231-239 + 506-714 + 200-228 + 559-565 + 568-650) empirically
  grounded per Step 0 (g) verbatim line ranges. Catalog mapping
  (1:1) verified per audit Wrapper field sole engine module
  reference. **A9 Class B 3rd instance acknowledgment:** S21 STOP 2
  caught single-layer simple-case framing assumption empirical
  falsification at Step 0 per A9 Class B mitigation pattern; Class
  B counter n=2 → n=3 ACTIVE; codification reinforced per §19.4
  forward instrumentation (post-S19-absorption codification stated
  "3rd instance would reinforce codification"). **Engine-extends-
  beyond-harness pattern characterization (NEW per §4.7 Forward Q1
  Step 0 discipline forward observation):** adf_test NOT harness-
  bypasses-engine outlier (engine uses same statsmodels function
  harness validates); pattern is engine-extends-beyond-harness via
  joint triage mode + KPSS + PP integration; forward observation
  for §4.7 codification refinement at next Workstream B amendment
  cycle if pattern recurs (KPSS + PP entries may surface analogous
  pattern). Verify-state-at-first-consumption sub-discipline 12th
  instance application (forward-at-authoring + STOP 2 caught
  single-layer assumption empirical falsification at Step 0;
  matures from S18 11th-instance Tier IV framing falsification with
  reinforced parallel-tests topology pattern as third Stage 3
  observation now operationally established as recurring).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at seventh-technique selection (user
  ratified adf_test under Tier 2 case-against framing per Phase 7+
  S20-close proposal as "Block 12 Stationarity Tests first entry
  per operational priority; calibrates per-block baseline at first-
  instance new-block observation"; case-against weighted but not
  invalidating per efficient ratification disposition). Pro-forma
  elements present per Mark 3 efficient-ratification pattern
  (operating-context preservation per Workstream B §5.3) **per
  Workstream B §1.4 Q-B operational pattern codification at S20**.
  **Q-B pattern persists at n=8 across S12 + S13 + S14b + S14c +
  S15 + S17 + S18 + S21; well past n=4 codification candidate
  threshold; §1.4 codified observation refinement at empirical
  pattern accumulation** (n=7 at §1.4 S20 codification → n=8 at
  S21 reinforcement). Not pro-forma across all upstream decisions
  for this technique (three-layer-parallel-tests novel topology
  framing required STOP 2 empirical investigation + γ disposition
  ratification + Layer 3 five-sub-component enumeration + engine-
  extends-beyond-harness pattern characterization).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (statsmodels.adfuller math layer)** per bit-
  exact PASS verdict at machine precision (test_statistic abs diff
  1.07e-14) against canonical R `urca::ur.df` reference;
  reproducibility + cross-package agreement institutional-grade
  evidence. **Conditional for Layer 2 (engine ADF orchestration)**
  — requires expert review of engine implementation OR engine-
  output cross-check against harness statsmodels.adfuller at base
  pinned config for variant correctness review (Schwert + AIC +
  trend detection + NaN handling appropriateness). **Conditional
  for Layer 3 (joint triage mode parallel tests)** — requires expert
  review of: 3a triage dispatch (ctx.run_id prefix logic
  appropriateness); 3b parallel KPSS + PP test invocation
  (cross-test parameter mapping correctness); 3c joint verdict logic
  (four-outcome verdict heuristic appropriateness for stationarity
  inference); 3d PP tie-breaker (CONFLICTING resolution
  appropriateness); 3e triage table + summary construction
  (published-research presentation correctness). **Critical Q-C
  framing per ribbon-default-publication context:** published-
  research user invoking `adf_test` from ribbon receives joint
  verdict from three tests + heuristic verdict computation;
  defensibility to all three audiences (published audience + Morgan
  Stanley compliance + Path α expert reviewer) UNDER Layer 3
  expert review acknowledgment. Defensible to all three audiences
  with disclosure language as drafted: published audience (three-
  layer-parallel-tests framing transparent with joint-verdict
  caveat); Morgan Stanley compliance review (precise audit citation
  + tier taxonomy + Layer 1 / Layer 2 / Layer 3 scope delineation +
  Layer 3 expert review scope); external expert reviewer at Path α
  close (verbatim audit numerics + honest disclosure of Layer 3
  joint triage mode + KPSS/PP integration + verdict heuristic +
  PP tie-breaker scope; Q3b extension pending).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-HIGH-CRITICAL. adf_test is canonical stationarity testing
  methodology in time-series research; widely used for unit-root
  hypothesis testing in published research + risk model
  documentation. **Layer-specific retraction surface (per S21 three-
  layer-parallel-tests framing):**
  - Layer 1 (statsmodels.adfuller math layer): LOW; bit-exact
    PASS verdict against canonical R urca::ur.df at machine
    precision; expert review surfacing upstream error would affect
    adf_test specifically (NO multi-map propagation risk; 1:1
    catalog↔wrapper).
  - Layer 2 (engine ADF orchestration: Schwert + AIC + trend +
    NaN): MEDIUM analogous to S14b/S15 Layer 2 (engine
    implementation equivalence) + engine-specific Schwert lag bound
    + AIC autolag selection + trend detection heuristic + NaN
    handling correctness.
  - Layer 3 (joint triage mode parallel tests + verdict logic):
    **MEDIUM-HIGH-CRITICAL** specifically for adf_test (NOT shared
    with other catalog techniques due to 1:1 mapping; engine-
    specific operational distinctive). Joint triage mode is the
    operational distinctive of adf_test ribbon invocation —
    stationarity-testing methodology's value-add over pure ADF
    is the joint ADF + KPSS + PP verdict via four-outcome
    heuristic + PP tie-breaker; expert review surfacing material
    errors (joint verdict logic; KPSS/PP integration; PP tie-
    breaker correctness; triage dispatch appropriateness) would
    invalidate the "stationarity testing with joint verdict" claim
    motivating adf_test ribbon use. **Topologically distinct from
    S15/S17/S18 Layer 3 MEDIUM-HIGH downstream framings and S14c
    Layer 2b MEDIUM-HIGH upstream framing:** S21 Layer 3 invokes
    PARALLEL math calls (additional tests) + computes verdict
    from combined results; operationally distinct risk surface
    from upstream pipeline OR downstream post-processing patterns.
    **Critical ribbon-publication context elevation:** ribbon-
    default publication output IS the joint verdict per `_is_triage_mode`
    dispatch; expert review surfacing Layer 3 errors specifically
    invalidates ribbon publication output (the typical user-facing
    output channel), not just an optional analytical alternative.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; seventh technique to enter status per
S21 ratification; **FIRST Block 12 Stationarity Tests entry**
(transitions Q1 work program from Block 1 Causality completion to
Block 12; calibrates per-block baseline at first-instance new-block
observation); **FIRST three-layer-parallel-tests topology entry**
(NOVEL topology distinct from S14c three-layer-upstream + S15/S17
three-layer-downstream + S18 three-layer-downstream Tier IV variant);
**A10 Sub-class 2d NEW topology candidate** (codification deferred
to next §19.4 absorption cycle). **S21 three-layer-parallel-tests
framing: Layer 1 (statsmodels.adfuller vs R urca::ur.df) bit-exact
PASS; Layer 2 (engine ADF orchestration) plausibly equivalent at
base pinned config but variants engine-specific; Layer 3 (joint
triage mode parallel tests + verdict computation; DEFAULT FOR
RIBBON PATH) NOT parity-validated, engine-specific operational
distinctive driving published research output requires expert
review.** **A9 Class B counter post-S21: n=3 ACTIVE** (S15 + S17 +
S21; codification reinforced per §19.4 forward instrumentation post-
S19-absorption stated "3rd instance would reinforce codification";
sub-class refinement codification candidate for §19.4 absorption #3
alongside A10 Sub-class 2d codification + A9 Class A 5th sub-pattern
accumulation + Block 1 Causality completion milestone). **A9 Class
A counter post-S21: n=5 ACTIVE** (unchanged; no Class A 6th instance
at S21 Step 0).

### kpss_test (Phase 7+ S22; eighth §2.5 entry; SECOND Block 12 Stationarity Tests entry; FIRST two-layer-primary-with-dual-role-disclosure entry; A10 Sub-class 2a first-instance baseline observation resolves pending status; TWO-LAYER PRIMARY + DUAL-ROLE DISCLOSURE framing per S22 STOP 2 empirical investigation + β disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2 per scope_reframing §2 line 130). **Important nuance
(two-layer-primary + dual-role-disclosure framing per S22 β
disposition; FIRST-INSTANCE A10 Sub-class 2a baseline; topology
distinct from S14c three-layer-upstream + S15/S17/S18 three-layer-
downstream + S21 three-layer-parallel-tests):** tier classification
applies to Layer 1 (statsmodels.tsa.stattools.kpss vs R urca::ur.kpss
at pinned LAG=5 / regression="c"); Layer 2 (engine module
kpss_test.py orchestration: regression/nlags allowlist gating + NaN
handling + per-series loop + significance disclosure + interpretation)
plausibly equivalent at base pinned config but variants engine-
specific. **Critical operational nuance — DUAL-ROLE engine module
per Step 0 (g) empirical (kpss_test.py module docstring lines 11-13
verbatim):** kpss_test engine plays two roles — (a) standalone-
technique role via `run()` entry point for direct ribbon `kpss_test`
invocation (two-layer framing applies); (b) helper-export role via
`_run_kpss_single` (lines 68-110) called by `adf_test.py`'s
`_run_triage` as S21 adf_test entry Layer 3 sub-component 3b
"parallel KPSS + PP test invocation". See Dual-role disclosure
section below for Q-D retraction surface compounding.

**Framing precedent note (1:1 catalog↔wrapper; TWO-LAYER PRIMARY +
DUAL-ROLE DISCLOSURE; FIRST-INSTANCE A10 Sub-class 2a baseline):**
kpss_test is 1:1 catalog↔wrapper mapping per p3_kpss audit Wrapper
field (`engine/techniques/kpss_test.py` sole engine module). Two-
layer-primary framing applies per S22 STOP 2 empirical finding:
harness invokes statsmodels.kpss directly at pinned single-test
config; engine module uses SAME statsmodels.kpss at math layer (clean
engine-uses-same-function pattern per Forward Q1 Step 0 discipline
§4.7) AND extends moderately beyond harness via Layer 2 orchestration
(regression/nlags allowlist + NaN handling + per-series loop +
interpretation; NO Layer 3 of its own — joint triage mode is OWNED BY
adf_test.py NOT kpss_test.py). **A10 Sub-class 2a first-instance
baseline observation: resolves "Sub-class 2a baseline observation
pending" status from §19.4 S16-absorption codification.** Topology
distinct from existing A10 sub-class instances:
- S14b cross_correlation_lag (amendment context; not first-instance
  Sub-class 2a baseline per §19.4 codification)
- S14c three-layer-upstream Sub-class 2b (prewhitened_ccf_lag)
- S15/S17 three-layer-downstream Sub-class 2c (rolling_ccf_lag +
  dtw_alignment_lag)
- S18 three-layer-downstream Tier IV variant Sub-class 2c-IV
  (gcc_phat_delay)
- S21 three-layer-parallel-tests Sub-class 2d candidate (adf_test)
- **S22 TWO-LAYER PRIMARY + DUAL-ROLE Sub-class 2a first-instance
  baseline (kpss_test direct-invocation + helper-export)**

**Dual-role disclosure section (institutional-grade per (β) ratification;
operational coupling explicit):** Per `engine/techniques/kpss_test.py`
module docstring lines 11-13 (verbatim): *"This wrapper exposes
`_run_kpss_single(clean, regression, nlags)` for the triage path in
`adf_test.py` to call directly, bypassing the per-series progress-
callback / response-building overhead."* Operational consequence:

- **Standalone-technique role** — direct ribbon `kpss_test` invocation
  (or pane_kpss / udf_kpss); two-layer framing per primary structure
  above; Layer 1 statsmodels.kpss + Layer 2 engine orchestration
- **Helper-export role** — `_run_kpss_single` helper (lines 68-110)
  invoked by `adf_test.py`'s `_run_triage` (lines 506-714 per S21
  adf_test entry Layer 3 sub-component 3b enumeration "parallel KPSS
  + PP test invocation"); kpss_test correctness PROPAGATES to
  adf_test ribbon joint verdict publication output (S21 adf_test
  ribbon-default publication context)
- **Cross-reference:** S21 adf_test §2.5 entry (line 2233) cites
  `kpss_test._run_kpss_single` invocation at Layer 3 sub-component 3b;
  S22 kpss_test entry reciprocally cites adf_test joint triage as
  helper-consumer per institutional-grade disclosure
- **Retraction surface compounding:** kpss_test errors propagate to
  BOTH standalone publication context AND adf_test ribbon publication
  context; see Q-D below

**Engine-extends-beyond-harness pattern characterization (NEW per §4.7
Forward Q1 Step 0 discipline forward observation; SECOND OBSERVATION
with scale-of-extension variation per S21 first observation):**
kpss_test engine module is NOT harness-bypasses-engine outlier (S14a
p3_ccf + S18 p3_gcc_phat pattern); engine module uses SAME
statsmodels.kpss function as harness (Layer 1 shared-math pattern
confirmed). Pattern is engine-extends-beyond-harness AT LAYER 2 SCALE
ONLY (orchestration only — regression/nlags allowlist + NaN handling
+ per-series loop + interpretation; NO Layer 3 of its own). Distinct
from S21 adf_test engine-extends-beyond-harness AT LAYER 3 SCALE
(entirely new joint triage sub-system). **§4.7 codification refinement
candidate** at next Workstream B amendment cycle distinguishing:
(i) Layer 3 extension pattern (adf_test) — DRAMATIC extension via
    entirely new computational sub-system
(ii) Layer 2 extension pattern (kpss_test) — MODERATE extension via
     orchestration only
(iii) potentially other patterns at S23+ entries

**A10 Sub-class 2a taxonomy resolution deferred to §19.4 absorption #3:**
S22 first-instance baseline observation under Sub-class 2a (originally
framed at S16-absorption as "two-layer multi-map" with cross_correlation_lag
context). Empirical kpss_test entry is 1:1 catalog↔wrapper (NOT multi-
map); Sub-class 2a taxonomy refinement (does Sub-class 2a require
multi-map context OR generalize to any two-layer framing regardless
of catalog mapping?) deferred to absorption #3 alongside Sub-class 2d
codification (S21 first-instance) + new Class B sub-pattern
subdivision (B.i simpler-than-expected + B.ii different-topology-than-
expected) + Class A 5th sub-pattern accumulation + Block 1 Causality
completion milestone.

**Reference:** R `urca::ur.kpss` (urca 1.3.4)
**Verdict:** PASS Pattern A bit-exact (Layer 1 only; see Validation
claim scope for Layer 2 + Dual-role coverage)
**Audit:** `tools/reference_parity/reports/p3_kpss_audit.md`
**Audit date:** 2026-04-29
**test_statistic (η) abs diff:** 5.55e-17 (TSL 0.09170600105152636 vs
Reference 0.0917060010515263; rel diff 6.05e-16)
**Tolerance class:** closed_form

**Source files (two-layer-primary + dual-role per S22 β framing):**
`tools/reference_parity/harness/checks/p3_kpss.py` lines 72-87
(harness TSL arm invokes `statsmodels.tsa.stattools.kpss` directly
with pinned regression="c", nlags=LAG=5; returns test_statistic +
p_value + used_lags + cv5)
+ `tools/reference_parity/harness/checks/p3_kpss.py` lines 89-113
(harness reference arm invokes R `urca::ur.kpss(y, type="mu",
use.lag=5)` via RBridge; extracts test_statistic + 5pct critical
value)
+ `engine/techniques/kpss_test.py` line 18 + lines 89-94 (Layer 1
shared math: engine module imports SAME `statsmodels.tsa.stattools.kpss`
function harness validates; `_run_kpss_single` helper calls
`kpss(clean, regression=regression, nlags=nlags)` at line 92)
+ `engine/techniques/kpss_test.py` lines 113-359 + 42-65 + 126-174 +
68-110 + 187-296 + 298-346 (Layer 2 orchestration: `run()` main
entry lines 113-359 + `_prepare_series` NaN handling lines 42-65 +
regression/nlags allowlist gating lines 126-174 + `_run_kpss_single`
helper lines 68-110 + per-series loop lines 187-296 + result
formatting + significance disclosure + interpretation + audit_fields
construction lines 298-346)
+ `engine/techniques/kpss_test.py` lines 11-13 (DUAL-ROLE engine
module docstring verbatim: helper-export disclosure for adf_test
triage path)
+ `engine/techniques/kpss_test.py` lines 68-110 (helper-export call
site: `_run_kpss_single(clean, regression, nlags)` invoked by
adf_test.py `_run_triage` lines 506-714 per S21 adf_test entry Layer
3 sub-component 3b enumeration "parallel KPSS + PP test invocation")
+ `tools/reference_parity/reports/p3_kpss_audit.md`

**Validation claim scope (TWO-LAYER PRIMARY + DUAL-ROLE DISCLOSURE per
S22 amendment per S14b two-layer-amendment precedent + S14c upstream +
S15/S17/S18 downstream + S21 parallel-tests topology precedents +
A10 Sub-class 2a first-instance baseline observation per β disposition):**
TSL kpss_test output relies on two layered computations (Layer 1
statsmodels.kpss math + Layer 2 engine module orchestration; no Layer
3 within kpss_test invocation path itself; topologically distinct from
S21 three-layer-parallel-tests where Layer 3 invokes parallel math
calls). p3_kpss audit validates Layer 1 (statsmodels.kpss) vs R
urca::ur.kpss at single seeded fixture (stationary AR(1), φ=0.7,
σ=1.0, T=500, seed=42, burn-in 100, LAG=5 bandwidth pinned both
sides via Schwert "short" rule, regression="c"); test_statistic
metric measures statsmodels.kpss η output vs urca::ur.kpss η
agreement (abs diff 5.55e-17 PASS), NOT engine module orchestration
correctness, NOT dual-role helper-export correctness.

- **Layer 1 — statsmodels.kpss math layer (validated):** bit-exact
  PASS verdict at machine precision (abs diff 5.55e-17; rel diff
  6.05e-16) against canonical R `urca::ur.kpss` reference; closed-
  form ratio of partial-sum-of-residuals to Newey-West-style long-
  run variance estimator; statsmodels and urca compute identical
  statistic given identical bandwidth per audit verdict_class_rationale.
- **Layer 2 — engine module kpss_test.py orchestration (validation
  scope conditional):**
  - regression/nlags allowlist gating (lines 126-174; CAI Phase 2
    Session 17 fix F-ST-KPSS-REGRESSION + F-ST-KPSS-NLAGS):
    appropriateness of allowlist scope for published-research input
    validation
  - `_prepare_series` NaN handling (lines 42-65): edge NaN stripping
    + interior NaN linear interpolation correctness
  - Per-series loop (lines 187-296): multi-series invocation pattern
    correctness; first-series interpretation_dict capture for
    multi-series cases (lines 230-260)
  - Result formatting + significance disclosure (lines 298-346):
    significance_level threshold logic + decision flag construction
    + critical_values_ordered representation + interpretation block
    construction + audit_fields significance disclosure
- **Dual-role helper-export — `_run_kpss_single` (lines 68-110;
  validation scope conditional + cross-references S21 Layer 3
  sub-component 3b):**
  - Helper-export contract correctness: returned dict structure
    (stat, pvalue, used_lag, critical_values_ordered,
    decision_h0_rejected, pvalue_clipped) consumed by adf_test
    `_run_triage` per S21 entry Layer 3 sub-component 3b
    enumeration; contract correctness impacts adf_test joint verdict
    computation
  - Helper-export error path correctness: error capture (lines 86-
    101) propagates to adf_test triage error handling

#### Disclosure pattern (i) — Research note footnote (Tier II.bit-exact + two-layer + dual-role)

> This analysis uses TSL technique `kpss_test`, cross-package bit-
> exact parity validated against R `urca::ur.kpss` (urca 1.3.4) per
> Phase 3 audit dated 2026-04-29 (test_statistic abs diff 5.55e-17).
> TSL output relies on a two-layer computation (Layer 1 statsmodels
> KPSS math + Layer 2 engine orchestration including regression/nlags
> allowlist + NaN handling + per-series loop + interpretation); Layer
> 1 bit-exact validated, Layer 2 conditional on expert review.
> Engine module is dual-role per `engine/techniques/kpss_test.py`
> module docstring: also exposes `_run_kpss_single` helper to
> `adf_test.py` triage path. Pre-Path α expert review status.

#### Disclosure pattern (ii) — Technical appendix (Tier II.bit-exact + two-layer + dual-role)

> Methodology: TSL technique `kpss_test` validated per Phase 3
> reference parity infrastructure under two-layer primary framing
> with dual-role disclosure. **Reference:** R `urca::ur.kpss` (urca
> 1.3.4). **Verdict:** PASS Pattern A.2 bit-exact at machine
> precision; test_statistic abs diff 5.55e-17 (TSL
> 0.09170600105152636 vs reference 0.0917060010515263; rel diff
> 6.05e-16). **Audit date:** 2026-04-29. **Fixture:** seeded single-
> fixture configuration (stationary AR(1), φ=0.7, σ=1.0, T=500,
> seed=42, burn-in 100, bandwidth pinned 5 via Schwert "short" rule,
> regression="c"); parameter-sensitivity coverage NOT established at
> this validation tier; Q3b extension pending. Reference selection +
> tolerance specification AI-assisted with user ratification. **Two-
> layer framing scope:** parity validation covers Layer 1
> (statsmodels.tsa.stattools.kpss math layer; closed-form ratio per
> KPSS 1992 formula) vs canonical R reference at machine precision;
> Layer 2 (engine module orchestration: regression/nlags allowlist
> gating per CAI Phase 2 Session 17 fix + NaN handling via
> `_prepare_series` + per-series loop + significance disclosure +
> interpretation) NOT parity-validated and engine-specific. **Dual-
> role engine module:** `engine/techniques/kpss_test.py` plays two
> operational roles per module docstring lines 11-13: (a) standalone-
> technique role for direct ribbon invocation (two-layer framing
> applies); (b) helper-export role via `_run_kpss_single` (lines 68-
> 110) called by `adf_test.py`'s `_run_triage` as Layer 3 sub-
> component 3b "parallel KPSS + PP test invocation" per S21 adf_test
> entry codification; kpss_test correctness propagates to adf_test
> ribbon joint verdict publication context. Pre-Path α expert review
> status; expert review pending [target date].

#### Disclosure pattern (iii) — Risk model documentation (Tier II.bit-exact + two-layer + dual-role + audit citation)

> `kpss_test` validation: TSL Tier II.bit-exact under two-layer-
> primary + dual-role-disclosure framing. **Reference:** R
> `urca::ur.kpss` (urca 1.3.4). **Audit:**
> `tools/reference_parity/reports/p3_kpss_audit.md` dated 2026-04-29.
> **Verdict:** PASS Pattern A.2 bit-exact at machine precision;
> test_statistic abs diff 5.55e-17 / rel diff 6.05e-16. **Fixture:**
> stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42, burn-in 100,
> bandwidth pinned 5 (Schwert "short"), regression="c"; single-seeded
> fixture; parameter-sensitivity coverage NOT established at this
> validation tier; Q3b extension scope. **Two-layer-framing risk
> attribution:** Layer 1 (statsmodels.kpss math) bit-exact validated;
> attribution from kpss_test output for parameter configurations
> matching fixture-similar conditions conditional on Layer 2 engine
> orchestration correctness (regression/nlags allowlist + NaN handling
> + per-series loop + significance disclosure + interpretation;
> validation scope per `engine/techniques/kpss_test.py` lines 113-359
> + 42-65 + 126-174 + 68-110 + 187-296 + 298-346). **Dual-role
> retraction surface elevation:** kpss_test engine module plays both
> standalone-technique role AND helper-export role per module
> docstring lines 11-13 verbatim; `_run_kpss_single` (lines 68-110)
> consumed by `adf_test.py` `_run_triage` as S21 adf_test Layer 3
> sub-component 3b; kpss_test errors propagate to adf_test ribbon
> joint verdict publication output. Pre-Path α expert review status.

#### Disclosure pattern (iv) — Internal use disclosure (Tier II.bit-exact + two-layer + dual-role)

> `kpss_test` cross-package bit-exact validated against R `urca::ur.kpss`
> (Layer 1; statsmodels.kpss math layer); Layer 2 engine orchestration
> pending expert review. Dual-role engine module: also exposes
> `_run_kpss_single` helper to `adf_test.py` triage. Pre-Path α.

**Validation provenance audit checklist (Workstream B §1 four-question
audit; applied per Q1 entry close):**

- **Q-A (extracted/cited evidence vs inferred reasoning):**
  Extracted/cited evidence. Reference (R urca::ur.kpss 1.3.4) per
  audit Reference field (verbatim). Audit date (2026-04-29) per
  audit Date field (verbatim). Verdict + Pattern (Pattern A bit-exact)
  per audit Verdict line (verbatim). Tolerance class (closed_form)
  per audit Tolerance class line (verbatim). Numeric metric (abs diff
  5.55e-17; rel diff 6.05e-16; TSL 0.09170600105152636 vs Reference
  0.0917060010515263) per audit Result table (verbatim). Fixture (AR(1)
  φ=0.7 σ=1.0 T=500 seed=42 burn-in 100 bandwidth=5 regression="c")
  per audit Fixture + Diagnostics sections (verbatim). Tier II.bit-
  exact characterization per scope_reframing §2 line 130 (`p3_kpss`
  in Tier II.bit-exact 12-wrapper enumeration). Two-layer-primary +
  dual-role-disclosure framing per S22 STOP 2 Step 0 empirical
  investigation (verbatim re-Reads of p3_kpss_audit.md + p3_kpss.py
  harness + 360 LOC engine module) + S14b two-layer-amendment +
  S14c upstream + S15/S17/S18 downstream + S21 parallel-tests
  topology precedent + β disposition. Layer 2 (lines 113-359 + 42-65
  + 126-174 + 187-296 + 298-346) sub-components empirically grounded
  per Step 0 (g) verbatim line ranges. Dual-role engine module
  characterization per module docstring lines 11-13 verbatim. Helper-
  export consumption by adf_test.py `_run_triage` per S21 adf_test
  entry Layer 3 sub-component 3b codification (cross-reference).
  Catalog mapping (1:1) verified per audit Wrapper field sole engine
  module reference. **A9 Class B 4th instance acknowledgment:** S22
  STOP 2 caught three-layer-parallel-tests framing assumption
  empirical falsification at Step 0 per A9 Class B mitigation pattern;
  Class B counter n=3 → n=4 ACTIVE; codification reinforced per §19.4
  forward instrumentation post-S19-absorption stated "3rd instance
  would reinforce codification" (already triggered at S21; S22
  continues reinforcement); sub-pattern subdivision candidate (B.i
  simpler-than-expected at S15+S17; B.ii different-topology-than-
  expected at S21+S22) deferred to §19.4 absorption #3. **Engine-
  extends-beyond-harness pattern second observation per §4.7 with
  scale-of-extension variation:** kpss_test Layer 2 scale extension
  (orchestration only) distinct from S21 adf_test Layer 3 scale
  extension (entirely new joint triage sub-system); codification
  refinement candidate at next Workstream B §4.7 amendment cycle.
  Verify-state-at-first-consumption sub-discipline 13th instance
  application (forward-at-authoring + STOP 2 caught three-layer-
  parallel-tests assumption empirical falsification at Step 0;
  matures from S21 12th-instance single-layer falsification with
  second different-topology-than-expected observation now codified
  as B.ii sub-pattern candidate).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at eighth-technique selection (user ratified
  kpss_test under Tier 2 case-against framing per S21-close proposal
  as "Block 12 Stationarity Tests second entry; sequential
  disposition per (c) γ; coordinated framing decision deferred to
  S22 close per S22 empirical findings"; case-against weighted but
  not invalidating per efficient ratification disposition). Pro-
  forma elements present per Mark 3 efficient-ratification pattern
  (operating-context preservation per Workstream B §5.3) **per
  Workstream B §1.4 Q-B operational pattern codification at S20**.
  **Q-B pattern persists at n=9 across S12 + S13 + S14b + S14c + S15
  + S17 + S18 + S21 + S22; well past n=4 codification candidate
  threshold; §1.4 codified observation refinement at empirical
  pattern accumulation** (n=7 at §1.4 S20 codification → n=8 at S21
  → n=9 at S22 reinforcement). Not pro-forma across all upstream
  decisions for this technique (two-layer-primary + dual-role-
  disclosure framing required STOP 2 empirical investigation + β
  disposition ratification + Layer 2 five-sub-component enumeration
  + dual-role disclosure section institutional-grade authoring +
  engine-extends-beyond-harness pattern scale-of-extension variation
  characterization).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 (statsmodels.kpss math layer)** per bit-exact
  PASS verdict at machine precision (test_statistic abs diff 5.55e-17;
  closed-form ratio per KPSS 1992 formula) against canonical R
  `urca::ur.kpss` reference; reproducibility + cross-package
  agreement institutional-grade evidence. **Conditional for Layer 2
  (engine kpss_test orchestration)** — requires expert review of
  engine implementation OR engine-output cross-check against harness
  statsmodels.kpss at base pinned config for variant correctness
  review (regression/nlags allowlist appropriateness + NaN handling
  via `_prepare_series` correctness + per-series loop pattern +
  significance disclosure construction + interpretation block
  construction). **Conditional for Dual-role helper-export** —
  requires expert review of: `_run_kpss_single` returned-dict
  contract correctness (consumed by adf_test._run_triage Layer 3
  3b); error path correctness (consumed by adf_test triage error
  handling); critical_values_ordered ordering correctness (consumed
  by interpretation block AND adf_test joint verdict logic).
  **Critical Q-C framing per dual-role context:** published-research
  user invoking `kpss_test` directly receives standalone single-test
  output (two-layer framing applies); published-research user
  invoking `adf_test` from ribbon receives joint verdict that
  CONSUMES kpss_test._run_kpss_single output; defensibility to all
  three audiences (published audience + Morgan Stanley compliance +
  Path α expert reviewer) UNDER Layer 2 + Dual-role helper-export
  expert review acknowledgment. Defensible to all three audiences
  with disclosure language as drafted: published audience (two-
  layer + dual-role framing transparent with helper-export caveat);
  Morgan Stanley compliance review (precise audit citation + tier
  taxonomy + Layer 1 / Layer 2 / Dual-role scope delineation + dual-
  role retraction surface compounding disclosure); external expert
  reviewer at Path α close (verbatim audit numerics + honest
  disclosure of Layer 2 orchestration + dual-role helper-export
  contract scope; Q3b extension pending).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-HIGH compounding. kpss_test is canonical stationarity
  testing methodology (complementary null to ADF; widely used in
  joint stationarity inference per published research + risk model
  documentation). **Layer-specific + dual-role retraction surface
  (per S22 two-layer-primary + dual-role-disclosure framing):**
  - Layer 1 (statsmodels.kpss math layer): LOW; bit-exact PASS
    verdict against canonical R urca::ur.kpss at machine precision;
    closed-form KPSS 1992 formula; expert review surfacing upstream
    error would affect kpss_test specifically (NO multi-map
    propagation risk; 1:1 catalog↔wrapper).
  - Layer 2 (engine kpss_test orchestration: regression/nlags
    allowlist + NaN handling + per-series loop + significance
    disclosure + interpretation): MEDIUM analogous to S14b/S15/S21
    Layer 2 (engine implementation equivalence) + KPSS-specific
    regression/nlags allowlist scope + interpretation block
    construction + significance disclosure formula.
  - **Dual-role helper-export (`_run_kpss_single`): MEDIUM-HIGH
    COMPOUNDING** — kpss_test correctness affects BOTH standalone
    publication output AND adf_test ribbon joint verdict publication
    output (the S21 adf_test ribbon-default publication context per
    `_is_triage_mode` dispatch). Expert review surfacing material
    errors in `_run_kpss_single` contract (returned-dict structure;
    error path; critical_values_ordered ordering; decision_h0_rejected
    logic) would invalidate BOTH the standalone "stationarity testing
    via KPSS" claim AND the adf_test "joint ADF + KPSS + PP verdict"
    claim (Layer 3 sub-component 3b "parallel KPSS + PP test
    invocation" consumes this helper). **Topologically distinct from
    S14b/S15/S17/S18 Layer 2 MEDIUM downstream framings, S14c Layer
    2b MEDIUM-HIGH upstream framing, and S21 Layer 3 MEDIUM-HIGH-
    CRITICAL parallel-tests framings:** S22 dual-role helper-export
    propagates kpss_test errors INTO adf_test ribbon publication
    context (operational coupling across techniques); operationally
    distinct risk surface from single-technique upstream/downstream/
    parallel-tests patterns. **Critical dual-role publication-context
    elevation:** adf_test ribbon-default publication output IS the
    joint verdict per `_is_triage_mode` dispatch (per S21 Layer 3
    framing); kpss_test errors via `_run_kpss_single` propagate into
    that publication output; expert review surfacing kpss_test errors
    specifically also invalidates adf_test ribbon publication output,
    not just standalone kpss_test output.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; eighth technique to enter status per S22
ratification; **SECOND Block 12 Stationarity Tests entry** (continues
Q1 work program in Block 12 after S21 adf_test first-entry; calibrates
per-block continuation pattern); **FIRST two-layer-primary-with-dual-
role-disclosure entry** (topologically distinct from S14c three-layer-
upstream + S15/S17/S18 three-layer-downstream + S21 three-layer-
parallel-tests + S14b two-layer-amendment context); **A10 Sub-class 2a
first-instance baseline observation** (resolves "Sub-class 2a baseline
observation pending" status from §19.4 S16-absorption codification;
taxonomy refinement deferred to absorption #3). **S22 two-layer-primary
+ dual-role-disclosure framing: Layer 1 (statsmodels.kpss vs R
urca::ur.kpss) bit-exact PASS; Layer 2 (engine kpss_test orchestration)
plausibly equivalent at base pinned config but variants engine-
specific; Dual-role helper-export (`_run_kpss_single` consumed by
adf_test `_run_triage` Layer 3 3b) NOT parity-validated, engine-
specific operational coupling driving compounded retraction surface
requires expert review.** **A9 Class B counter post-S22: n=4 ACTIVE**
(S15 + S17 + S21 + S22; codification reinforced; sub-pattern
subdivision candidate (B.i simpler-than-expected at S15+S17; B.ii
different-topology-than-expected at S21+S22 with two distinct topology
classes) deferred to §19.4 absorption #3 alongside A10 Sub-class 2a
taxonomy resolution + A10 Sub-class 2d codification + A9 Class A 5th
sub-pattern accumulation + Block 1 Causality completion milestone +
engine-extends-beyond-harness Layer-scale-variation pattern §4.7
codification refinement). **A9 Class A counter post-S22: n=5 ACTIVE**
(unchanged; no Class A 6th instance at S22 Step 0).

### pp_test (Phase 7+ S23; ninth §2.5 entry; THIRD Block 12 Stationarity Tests entry — Block 12 FULLY Q1-AMENDED; FIRST Tier II.bit-exact-loose + Tier V Pattern J B.2 overlay entry; FIRST triple-role helper-export entry; FIRST dedicated novelty enumeration sub-section; TRIPLE-ROLE + PATTERN J OVERLAY + BACKEND-DISPATCHER + LAYER 1 ENGINE-EXTENDS-BEYOND-HARNESS framing per S23 STOP 2 empirical investigation + α tier + αa-conditional A10 dispositions)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** **Tier
II.bit-exact-loose with Tier V Pattern J B.2 overlay** — Phase 3
cross-package PASS at closed_form tolerance (2.09e-06 abs / 2.26e-07
rel; within closed_form ladder accommodating internal HAC kernel
divergence and residual variance divisor differences at sub-1e-6
levels per audit Pattern J observation). **First §2.5 entry with
dual-tier characterization (II.bit-exact-loose primary + V Pattern J
B.2 overlay)** per S23 α disposition ratification; precedent for
future Pattern J-affected wrappers entering §2.5. Pattern J B.2 sub-
class per scope_reframing §2 line 176-177 (internal-default
divergence; p3_egarch is existing exemplar). Tier V overlay
treatment per scope_reframing §2 line 236-237 ("distributed across
other tiers as overlay"). **Important nuance (triple-role + backend-
dispatcher + Layer 1 engine-extends-beyond-harness framing per S23 α
+ αa-conditional disposition):** tier classification applies to
Layer 1 (`arch.unitroot.PhillipsPerron` vs R `urca::ur.pp` at pinned
LAG=5 / trend="c" / type="Z-tau"); Layer 2 (engine pp_test.py
backend-dispatcher + manual fallback + standalone-technique
orchestration) plausibly equivalent at base pinned config but variants
engine-specific; **Triple-role coupling (standalone + 3b parallel-
helper + 3d CONFLICTING tie-breaker) NOT parity-validated, engine-
specific operational coupling driving compounded retraction surface
across THREE publication contexts (standalone + adf_test ribbon
parallel verdict + adf_test ribbon tie-breaker resolution)
requires expert review.**

**Framing precedent note (1:1 catalog↔wrapper; TRIPLE-ROLE
helper-export + BACKEND-DISPATCHER engine + Layer 1 engine-extends-
beyond-harness variant; A10 Sub-class 2a candidate second-observation
with αa/αb taxonomy refinement deferred to absorption #3):** pp_test
is 1:1 catalog↔wrapper mapping per p3_pp audit Wrapper field
(`engine/techniques/pp_test.py` sole engine module). Triple-role +
backend-dispatcher framing applies per S23 STOP 2 empirical finding:
harness invokes `arch.unitroot.PhillipsPerron` directly at pinned
single-test config (statsmodels < 0.14 on audit Python; comment per
p3_pp.py line 76-78); engine module has 3-tier backend-dispatcher
fallback chain (statsmodels.phillips_perron → arch.unitroot.PhillipsPerron
→ `_manual_pp` 64 LOC Newey-West Bartlett kernel implementation per
pp_test.py lines 106-169); engine extends moderately beyond harness
via Layer 2 orchestration (4-option regression allowlist gating per
CAI Phase 2 Session 17 fix F-ST-PP-REGRESSION + NaN handling + per-
series loop + backend-dispatcher method recording + significance
disclosure); AND engine `_run_pp_single` (lines 172-208) exposes
helper to `adf_test.py` `_run_triage` consumed at TWO Layer 3 sub-
components: 3b parallel-tests invocation (lines 533-535) AND 3d
CONFLICTING tie-breaker (lines 559-565 per S21 adf_test entry
codification). **A10 Sub-class 2a candidate second-observation under
existing taxonomy** (resolves to n=2 with S22 kpss_test first-instance
baseline). **Taxonomy refinement question — whether triple-role fits
Sub-class 2a (αa keeps-2a-as-general-two-layer) or warrants Sub-class
2a-triple-role split (αb splits-2a-vs-2a-triple-role) — deferred to
§19.4 absorption #3 with both (αa) and (αb) surfaced as disposition
options under full A3 second-observation tightening discipline.**
Topology distinct from existing A10 sub-class instances:
- S14b cross_correlation_lag (amendment context; not first-instance
  Sub-class 2a baseline per §19.4 codification)
- S14c three-layer-upstream Sub-class 2b (prewhitened_ccf_lag)
- S15/S17 three-layer-downstream Sub-class 2c (rolling_ccf_lag +
  dtw_alignment_lag)
- S18 three-layer-downstream Tier IV variant Sub-class 2c-IV
  (gcc_phat_delay)
- S21 three-layer-parallel-tests Sub-class 2d candidate (adf_test)
- S22 TWO-LAYER PRIMARY + DUAL-ROLE Sub-class 2a first-instance
  baseline (kpss_test direct-invocation + helper-export)
- **S23 TWO-LAYER + TRIPLE-ROLE + BACKEND-DISPATCHER Sub-class 2a
  candidate second-observation (pp_test direct-invocation + 3b
  helper-export + 3d tie-breaker; αa/αb taxonomy disposition
  deferred)**

**Novelty enumeration sub-section (FIRST-INSTANCE per S23; novel
sub-section pattern; codification candidate for §4.7 amendment
cycle OR Workstream B §3 addendum if S24+ Q1 entries replicate
pattern per A3 design-class second-observation precedent):**

- **3a — A10 Sub-class 2a candidate second-observation; taxonomy
  disposition deferred to absorption #3:** pp_test is Sub-class 2a
  candidate second-observation under existing taxonomy (S22 kpss_test
  first-instance baseline → S23 pp_test second-observation candidate).
  **Taxonomy refinement question carries to absorption #3:** (αa)
  keeps Sub-class 2a as general two-layer class accommodating both
  dual-role (kpss_test) and triple-role (pp_test) variants OR (αb)
  splits into Sub-class 2a (dual-role) + Sub-class 2a-triple-role
  (triple-role) per topology convention analogous to Sub-class 2c-IV
  Tier-variant suffix taxonomy at §19.4 A10 codification. Both
  options surfaced for absorption #3 under full A3 second-observation
  tightening discipline; entry does NOT pre-commit. Cross-reference:
  S22 kpss_test entry §2.5 lines 2776-2783 (Sub-class 2a first-
  instance baseline observation + multi-map vs 1:1 generalization
  taxonomy question deferred); analogous deferred-disposition pattern.

- **3b — Tier II.bit-exact-loose + Tier V Pattern J B.2 overlay
  first-instance §2.5 precedent:** First §2.5 entry with dual-tier
  characterization. Tier V overlay treatment per scope_reframing §2
  line 236-237 ("distributed across other tiers as overlay"); Pattern
  J B.2 sub-class per scope_reframing §2 line 176-177 (internal-
  default divergence; p3_egarch is existing exemplar). Establishes
  precedent for future Pattern J-affected wrappers entering §2.5
  (scope_reframing §2 lists 4 Pattern J wrappers in Tier V
  enumeration: p3_ets + p3_var Pattern D + p3_egarch + p3_lomb_scargle;
  p3_pp NOT in original enumeration — added by post-S6 inference per
  audit Pattern J observation explicit). **Forward instrumentation:**
  if S24+ surfaces second Pattern J overlay §2.5 entry, sub-class
  formalization candidate per A3 second-observation precedent —
  banked at this commit message for absorption #3 or Workstream B
  amendment cycle disposition.

- **3c — Backend-dispatcher engine pattern first observation
  (statsmodels → arch → `_manual_pp` 64 LOC fallback chain):** Engine
  module `_run_pp_test` (pp_test.py lines 70-103) implements 3-tier
  fallback dispatcher: tries `statsmodels.tsa.stattools.phillips_perron`
  (statsmodels ≥ 0.14) first; falls back to `arch.unitroot.PhillipsPerron`
  if statsmodels unavailable; falls back to `_manual_pp` (lines 106-
  169) if both library implementations unavailable. Manual fallback
  is SUBSTANTIAL (64 LOC) with: OLS for ρ̂ (lines 121-122) + Schwert
  (2/9) auto-bandwidth rule (line 128) + Newey-West Bartlett kernel
  long-run variance (lines 132-138) + standard error for ρ̂ (lines
  140-143) + Phillips-Perron correction (lines 146-147) + MacKinnonP
  p-value with hardcoded fallback (lines 149-160) + hardcoded
  critical values per regression (lines 162-167). Backend selection
  recorded in `method` field of returned dict per audit Diagnostics
  line 29-30 ("TSL backend: arch.PhillipsPerron — statsmodels < 0.14
  on this Python; arch path used"); audit-time backend was arch path.
  **Operational distinctive:** TSL output depends on which backend
  was selected at runtime; p3_pp audit validates arch path
  specifically; statsmodels path + manual fallback path NOT parity-
  validated. Layer 2 sub-component for Q-A documentation + Q-D
  retraction surface.

- **3d — Engine-extends-beyond-harness Layer 1 backend-dispatcher
  variant (THIRD observation completing §4.7 codification refinement
  triad):** §4.7 Forward Q1 Step 0 discipline observed two engine-
  extends-beyond-harness pattern variants pre-S23: (i) Layer 3
  extension scale at S21 adf_test (entirely new joint triage sub-
  system) + (ii) Layer 2 extension scale at S22 kpss_test
  (orchestration only). **S23 pp_test surfaces THIRD variant: Layer 1
  backend-dispatcher** — engine has fallback chain across THREE
  underlying library implementations whereas harness invokes ONE
  fixed library (arch); engine extends harness Layer 1 dimension via
  optionality across implementations. Pattern recurs at n=3 with
  three operationally distinct scale-of-extension variations (Layer 1
  / Layer 2 / Layer 3); **§4.7 codification refinement triad
  empirically complete per A3 design-class second-observation
  tightening precedent threshold satisfied at n=3.** Forward
  instrumentation for Workstream B §4.7 amendment cycle (separate
  lane; Workstream B candidate B per S23 commit message banking).

- **3e — Triple-role helper-export to adf_test triage 3b parallel +
  3d CONFLICTING tie-breaker (operationally distinct from S22
  kpss_test dual-role):** pp_test engine module plays THREE
  operational roles vs kpss_test DUAL-ROLE (S22 codification): (i)
  standalone-technique role via `run()` entry point for direct
  ribbon `pp_test` invocation; (ii) **3b parallel-test helper-export
  role** via `_run_pp_single` (lines 172-208) called by adf_test.py
  `_run_triage` line 535 alongside ADF + KPSS on same fixture per
  S21 adf_test entry Layer 3 sub-component 3b codification (line
  2388); (iii) **3d CONFLICTING tie-breaker role** via same
  `_run_pp_single` consumed by adf_test.py `_run_triage` lines 559-565
  when joint ADF + KPSS verdict surfaces CONFLICTING outcome per S21
  adf_test entry Layer 3 sub-component 3d codification (lines 2402-
  2408). Triple-role compounds retraction surface beyond kpss_test
  dual-role: pp_test errors propagate to THREE publication contexts
  (standalone + adf_test ribbon 3b parallel verdict + adf_test ribbon
  3d tie-breaker resolution); see Q-D below for compounded retraction
  surface characterization.

- **3f — Auto-bandwidth rule divergence (Schwert (2/9) standalone vs
  Schwert (1/4) kpss) + triage-path bandwidth divergence from Layer 1
  fixture (Q-A documentation depth + Q-D retraction surface):**
  **(i) Auto-bandwidth rule divergence within triage members:**
  pp_test `_manual_pp` auto rule (line 128) is `int(np.floor(4 * (n
  / 100) ** (2 / 9)))` — **Schwert (2/9) rule**; kpss_test "short" rule
  per harness/audit is `int(4 * (n / 100) ** (1/4))` — **Schwert (1/4)
  rule**. Both pinned to 5 at p3_kpss + p3_pp audits (n=500 fixture
  yields same numeric value at coincidence: (2/9)→5 vs (1/4)→5) which
  MASKS the rule difference at audit time; rule difference is
  operative at non-pinned production invocations at n≠500. **(ii)
  Triage-path bandwidth divergence from Layer 1 fixture:** p3_pp
  audit validates `arch.PhillipsPerron(y, trend="c", lags=5)` (pinned
  LAG=5); adf_test triage invokes `_run_pp_single(clean, pp_trend,
  lags=None)` (line 535) which `_run_pp_single` line 195 maps to
  "auto" → Schwert (2/9) rule → varies with n. **Triage-path
  bandwidth NOT in p3_pp-validated parameter space at non-fixture n;
  Layer 3 sub-component 3b operational distinctive.** Asymmetric
  disclosure vs S22 kpss_test (which did NOT surface analogous KPSS
  triage-path bandwidth divergence — KPSS triage uses `nlags="auto"`
  at adf_test.py line 532 ALSO not in pinned-LAG=5 audit parameter
  space) ACCEPTED at S23 per Chat probing question disposition:
  empirical discovery at S23 Step 0 not S22 Step 0; retroactive S22
  amendment violates CHAT RATIFICATION #4 independent sequential;
  absorption #3 dispositions retroactive S22 kpss_test Q-A disclosure
  amendment candidate (symmetric to S23 disclosure) under full
  structure visibility.

**Triple-role disclosure section (institutional-grade per S22 dual-
role precedent extended for 3d tie-breaker role; operational
coupling explicit):** Per `engine/techniques/pp_test.py` module
docstring lines 9-15 (verbatim): *"Tries in order: 1.
`statsmodels.tsa.stattools.phillips_perron` (statsmodels ≥ 0.14); 2.
`arch.unitroot.PhillipsPerron`; 3. A manual Z(t) implementation
using Newey-West HAC correction. Exposes `_run_pp_single(clean,
regression, lags)` for the triage path in `adf_test.py`."*
Operational consequence:

- **Standalone-technique role** — direct ribbon `pp_test` invocation
  (or pane_pp_test / udf_pp_test); two-layer framing applies; Layer
  1 math layer (backend selected by dispatcher at runtime; arch-path
  audit-validated, statsmodels-path + manual-path unverified) +
  Layer 2 engine orchestration. Audit-time backend was
  arch.PhillipsPerron per audit Diagnostics; statsmodels-path +
  manual-path NOT audit-validated.
- **3b parallel-test helper-export role** — `_run_pp_single` helper
  (lines 172-208) invoked by `adf_test.py`'s `_run_triage` line 535
  (`pp = _run_pp_single(clean, pp_trend, lags=None)`); invocation
  pattern alongside ADF + KPSS on same fixture per S21 adf_test
  entry Layer 3 sub-component 3b enumeration; pp_trend mapping
  ("ct" if ADF regression "ct" else "n" if regression in {n, nc}
  else "c") per adf_test.py lines 533-534; lags=None resolves to
  "auto" → Schwert (2/9) rule.
- **3d CONFLICTING tie-breaker role** — SAME `_run_pp_single` output
  consumed by adf_test.py `_run_triage` lines 559-565 for tie-
  breaker resolution when joint ADF + KPSS verdict surfaces
  CONFLICTING. Tie-breaker logic verbatim per adf_test.py:
  *"PP agrees with ADF (unit root rejected)" if PP rejects null;
  "PP agrees with KPSS (unit root not rejected)" if PP fails to
  reject.* Engine-specific tie-breaker heuristic; correctness depends
  on PP rejection logic appropriateness for tie-breaking between
  ADF + KPSS disagreement.
- **Cross-reference:** S21 adf_test §2.5 entry (line 2233) cites
  `_run_pp_single from techniques.pp_test` at Layer 3 sub-component
  3b (line 2388) AND PP tie-breaker logic at Layer 3 sub-component
  3d (lines 2402-2408); S22 kpss_test §2.5 entry (line 2683) cites
  reciprocal cross-reference precedent at lines 2750-2753; S23
  pp_test entry reciprocally cites adf_test joint triage as helper-
  consumer per institutional-grade disclosure (extending S22 precedent
  for triple-role coupling).
- **Retraction surface compounding (THREE publication contexts):**
  pp_test errors propagate to (i) standalone pp_test publication
  output; (ii) adf_test ribbon joint verdict publication output via
  3b parallel-test invocation; (iii) adf_test ribbon tie-breaker
  resolution via 3d CONFLICTING disposition. Compounds beyond S22
  kpss_test dual-role retraction surface; see Q-D below.

**Engine-extends-beyond-harness pattern characterization (NEW per §4.7
Forward Q1 Step 0 discipline forward observation; THIRD OBSERVATION
completing codification refinement triad per A3 second-observation
tightening precedent threshold satisfied at n=3):** pp_test engine
module is NOT harness-bypasses-engine outlier (S14a p3_ccf + S18
p3_gcc_phat pattern); engine module uses SAME `arch.unitroot.PhillipsPerron`
function as harness validates at base config (statsmodels-path +
manual-path are engine-specific extensions). Pattern is engine-
extends-beyond-harness AT LAYER 1 SCALE via BACKEND-DISPATCHER
variant — engine has fallback chain across THREE underlying library
implementations whereas harness invokes ONE fixed library. Distinct
from S21 adf_test engine-extends-beyond-harness AT LAYER 3 SCALE
(entirely new joint triage sub-system) AND S22 kpss_test engine-
extends-beyond-harness AT LAYER 2 SCALE (orchestration only). **§4.7
codification refinement triad EMPIRICALLY COMPLETE per A3 design-
class second-observation tightening precedent threshold at n=3
observations distinguishing:**
(i) Layer 3 extension scale (S21 adf_test) — DRAMATIC extension via
    entirely new computational sub-system
(ii) Layer 2 extension scale (S22 kpss_test) — MODERATE extension
     via orchestration only
(iii) Layer 1 extension scale (S23 pp_test) — BACKEND-DISPATCHER
      variant via fallback chain across underlying implementations

**Workstream B §4.7 codification refinement candidate ratified for
next amendment cycle** (Workstream B candidate B per S23 commit
message banking; separate lane from §19.4 absorption #3).

**Reference:** R `urca::ur.pp` (urca 1.3.4); type="Z-tau";
model="constant"
**Verdict:** PASS Pattern J widening (closed-form with internal HAC
kernel divergence accommodated; Layer 1 only; see Validation claim
scope for Layer 2 + Triple-role coverage)
**Audit:** `tools/reference_parity/reports/p3_pp_audit.md`
**Audit date:** 2026-04-29
**test_statistic (Z(τ)) abs diff:** 2.09e-06 (TSL -9.25345071447954
vs Reference -9.25345280545195; rel diff 2.26e-07)
**Tolerance class:** closed_form (within ladder accommodating Pattern
J widening per audit Pattern J observation lines 36-43)

**Source files (TRIPLE-ROLE + BACKEND-DISPATCHER + Pattern J overlay
per S23 α + αa-conditional framing):**
`tools/reference_parity/harness/checks/p3_pp.py` lines 73-87
(harness TSL arm invokes `arch.unitroot.PhillipsPerron(y, trend="c",
lags=LAG=5)` directly; comment line 76-78 "statsmodels >= 0.14
phillips_perron may not exist on this Python; arch is installed";
returns test_statistic + p_value + lags + method)
+ `tools/reference_parity/harness/checks/p3_pp.py` lines 89-114
(harness reference arm invokes R `urca::ur.pp(y, type="Z-tau",
model="constant", use.lag=5)` via RBridge; extracts test_statistic
+ 5pct critical value)
+ `engine/techniques/pp_test.py` lines 70-103 (Layer 1 backend-
dispatcher: `_run_pp_test` tries statsmodels.tsa.stattools.phillips_perron
→ arch.unitroot.PhillipsPerron → `_manual_pp` fallback chain;
harness validates arch path specifically; statsmodels-path + manual-
path engine-specific extensions)
+ `engine/techniques/pp_test.py` lines 106-169 (Layer 2 manual
fallback: `_manual_pp` 64 LOC Newey-West Bartlett kernel
implementation; OLS for ρ̂ lines 121-122 + Schwert (2/9) auto-
bandwidth line 128 + LRV via Bartlett kernel lines 132-138 + PP
correction lines 146-147 + MacKinnonP p-value lines 149-160 +
hardcoded critical values per regression lines 162-167)
+ `engine/techniques/pp_test.py` lines 172-208 (3b/3d helper-export:
`_run_pp_single` thin helper for triage path; docstring "same shape
as `_run_adf_single` / `_run_kpss_single` so the triage path can
consume all three uniformly")
+ `engine/techniques/pp_test.py` lines 211-434 + 45-67 + 253-264 +
274-368 + 372-422 (Layer 2 standalone orchestration: `run()` main
entry lines 211-434 + `_prepare_series` NaN handling lines 45-67 +
4-option regression allowlist gating lines 253-264 per CAI Phase 2
Session 17 fix F-ST-PP-REGRESSION + per-series loop lines 274-368 +
result formatting + significance disclosure + interpretation +
audit_fields construction lines 372-422)
+ `engine/techniques/pp_test.py` lines 9-15 (TRIPLE-ROLE +
BACKEND-DISPATCHER engine module docstring verbatim: backend-
dispatcher fallback chain disclosure + helper-export disclosure for
adf_test triage path)
+ `engine/techniques/adf_test.py` lines 510-512 (Layer 3 imports:
`from techniques.kpss_test import _run_kpss_single` + `from
techniques.pp_test import _run_pp_single`; local imports per inline
comment "so unit-test/UDF paths don't eagerly import arch/kpss")
+ `engine/techniques/adf_test.py` lines 533-535 (Layer 3 sub-
component 3b parallel invocation: pp_trend mapping per adf_test
regression space + `pp = _run_pp_single(clean, pp_trend, lags=None)`;
lags=None resolves to "auto" → Schwert (2/9) rule)
+ `engine/techniques/adf_test.py` lines 559-565 (Layer 3 sub-
component 3d CONFLICTING tie-breaker: pp_note construction per PP
rejection logic appropriateness for ADF + KPSS disagreement
resolution)
+ `tools/reference_parity/reports/p3_pp_audit.md`

**Validation claim scope (TIER II.BIT-EXACT-LOOSE + TIER V PATTERN J
B.2 OVERLAY + TRIPLE-ROLE + BACKEND-DISPATCHER per S23 α + αa-
conditional disposition):** TSL pp_test output relies on two layered
computations within standalone-technique role (Layer 1 backend-
dispatcher implementation math + Layer 2 engine orchestration) PLUS
triple-role helper-export coupling (3b parallel + 3d tie-breaker) at
adf_test ribbon publication context. p3_pp audit validates Layer 1
arch-path (`arch.unitroot.PhillipsPerron`) vs R urca::ur.pp at single
seeded fixture (stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42,
burn-in 100, LAG=5 bandwidth pinned both sides, trend="c");
test_statistic metric measures arch.PhillipsPerron Z(τ) output vs
urca::ur.pp Z(τ) agreement (abs diff 2.09e-06 PASS within Pattern J
widening accommodation), NOT engine module orchestration correctness,
NOT statsmodels-path / manual-path correctness, NOT triple-role
helper-export correctness.

- **Layer 1 — arch.PhillipsPerron math layer (validated within
  Pattern J widening):** PASS Pattern J widening at closed_form
  tolerance (abs diff 2.09e-06; rel diff 2.26e-07) against canonical
  R `urca::ur.pp` reference; closed-form Newey-West correction to
  Dickey-Fuller t-statistic. Pattern J B.2 internal-default
  divergence accommodation per audit Pattern J observation: kernel
  weights (triangular vs Bartlett vs identical) + residual variance
  divisor (n-1 vs n-k) differ at sub-1e-6 levels; 1e-3 abs / 1e-2
  rel ladder accommodates without masking real regressions.
- **Layer 1 backend-dispatcher alternatives (validation scope
  unverified):**
  - statsmodels.phillips_perron path (preferred per pp_test.py line
    78-87 fallback order): NOT exercised at audit time (statsmodels
    < 0.14 on audit Python); validation pending statsmodels ≥ 0.14
    environment + cross-check against arch path
  - `_manual_pp` path (lines 106-169 fallback): NOT exercised at
    audit time (arch installed per audit Diagnostics); validation
    pending environment without arch + cross-check against arch path
    AND/OR against urca reference
- **Layer 2 — engine pp_test orchestration (validation scope
  conditional):**
  - 4-option regression allowlist gating (lines 253-264; CAI Phase 2
    Session 17 fix F-ST-PP-REGRESSION): appropriateness of allowlist
    scope for published-research input validation; 4 options ("c",
    "ct", "n", "nc") vs kpss_test 2 options ("c", "ct") — broader
    parameter space requires correspondingly broader expert review
  - `_prepare_series` NaN handling (lines 45-67): edge NaN stripping
    + interior NaN linear interpolation correctness (analogous to
    kpss_test pattern)
  - Per-series loop (lines 274-368): multi-series invocation pattern
    correctness; first-series interpretation_dict capture for multi-
    series cases (lines 294-323)
  - Result formatting + significance disclosure (lines 372-422):
    significance_level threshold logic + decision flag construction
    + critical_values_ordered representation + interpretation block
    construction + method field disclosure (backend selected at
    runtime) + audit_fields significance disclosure
- **Triple-role helper-export — `_run_pp_single` (lines 172-208;
  validation scope conditional + cross-references S21 Layer 3 sub-
  components 3b + 3d):**
  - 3b helper-export contract correctness: returned dict structure
    (stat, pvalue, used_lag, critical_values_ordered, method,
    decision_h0_rejected) consumed by adf_test `_run_triage` per
    S21 entry Layer 3 sub-component 3b enumeration; contract
    correctness impacts adf_test joint verdict computation
  - 3d helper-export tie-breaker contract correctness: SAME returned
    dict consumed by adf_test `_run_triage` lines 559-565 for
    CONFLICTING tie-breaker; pp_rej derived from pvalue < significance
    drives tie-breaker disposition; correctness impacts adf_test
    ribbon tie-breaker resolution
  - Helper-export error path correctness: error capture (lines 187-
    192 + 196-198) propagates to adf_test triage error handling
  - **Triage-path bandwidth divergence:** `_run_pp_single` invoked
    by triage with `lags=None` (adf_test line 535) → "auto" →
    Schwert (2/9) → varies with n; Layer 1 fixture validates pinned
    LAG=5 only; triage-path operational behavior NOT in audit
    parameter space at non-fixture n

#### Disclosure pattern (i) — Research note footnote (Tier II.bit-exact-loose + Pattern J B.2 overlay + triple-role)

> This analysis uses TSL technique `pp_test`, cross-package PASS
> validated against R `urca::ur.pp` (urca 1.3.4) per Phase 3 audit
> dated 2026-04-29 (test_statistic abs diff 2.09e-06 within Pattern
> J widening accommodation for internal HAC kernel divergence). TSL
> output relies on two-layer computation within standalone-technique
> role (Layer 1 backend-dispatcher selecting statsmodels/arch/manual
> Phillips-Perron implementation + Layer 2 engine orchestration);
> Layer 1 arch-path bit-exact-loose validated, statsmodels/manual
> alternatives + Layer 2 conditional on expert review. Engine module
> is triple-role: also exposes `_run_pp_single` helper to
> `adf_test.py` triage at 3b parallel + 3d CONFLICTING tie-breaker.
> Pre-Path α expert review status.

#### Disclosure pattern (ii) — Technical appendix (Tier II.bit-exact-loose + Pattern J B.2 overlay + triple-role)

> Methodology: TSL technique `pp_test` validated per Phase 3
> reference parity infrastructure under Tier II.bit-exact-loose +
> Tier V Pattern J B.2 overlay framing with triple-role helper-
> export disclosure. **Reference:** R `urca::ur.pp` (urca 1.3.4);
> type="Z-tau"; model="constant". **Verdict:** PASS Pattern J
> widening at closed_form tolerance; test_statistic abs diff
> 2.09e-06 (TSL -9.25345071447954 vs reference -9.25345280545195;
> rel diff 2.26e-07); within ladder accommodating internal HAC
> kernel weights + residual variance divisor differences at sub-
> 1e-6 levels per audit Pattern J observation. **Audit date:**
> 2026-04-29. **Fixture:** seeded single-fixture configuration
> (stationary AR(1), φ=0.7, σ=1.0, T=500, seed=42, burn-in 100,
> bandwidth pinned 5, trend="c"); parameter-sensitivity coverage
> NOT established at this validation tier; Q3b extension pending.
> Reference selection + tolerance specification AI-assisted with
> user ratification. **Two-layer + Pattern J B.2 overlay framing
> scope:** parity validation covers Layer 1 arch-path
> (`arch.unitroot.PhillipsPerron`) vs canonical R reference at
> closed_form ladder; Pattern J B.2 overlay accommodates internal
> HAC kernel divergence (Bartlett kernel + Schwert auto-bandwidth);
> Layer 1 statsmodels-path + manual-path alternatives NOT validated;
> Layer 2 (engine orchestration: 4-option regression allowlist
> gating per CAI Phase 2 Session 17 fix + NaN handling via
> `_prepare_series` + per-series loop + backend-dispatcher method
> recording + significance disclosure + interpretation) NOT parity-
> validated and engine-specific. **Triple-role engine module:**
> `engine/techniques/pp_test.py` plays THREE operational roles per
> module docstring lines 9-15: (a) standalone-technique role for
> direct ribbon invocation (two-layer framing applies); (b) 3b
> parallel-test helper-export role via `_run_pp_single` (lines 172-
> 208) called by `adf_test.py`'s `_run_triage` line 535 as Layer 3
> sub-component 3b "parallel KPSS + PP test invocation" per S21
> adf_test entry codification; (c) 3d CONFLICTING tie-breaker role
> via SAME `_run_pp_single` consumed by `adf_test.py` `_run_triage`
> lines 559-565 for tie-breaker resolution when joint ADF + KPSS
> verdict is CONFLICTING. pp_test correctness propagates to THREE
> publication contexts (standalone + adf_test ribbon parallel verdict
> + adf_test ribbon tie-breaker resolution). Pre-Path α expert
> review status; expert review pending [target date].

#### Disclosure pattern (iii) — Risk model documentation (Tier II.bit-exact-loose + Pattern J B.2 overlay + triple-role + audit citation)

> `pp_test` validation: TSL Tier II.bit-exact-loose with Tier V
> Pattern J B.2 overlay (internal-default divergence accommodation)
> under triple-role helper-export framing. **Reference:** R
> `urca::ur.pp` (urca 1.3.4); type="Z-tau"; model="constant".
> **Audit:** `tools/reference_parity/reports/p3_pp_audit.md` dated
> 2026-04-29. **Verdict:** PASS Pattern J widening at closed_form
> tolerance; test_statistic abs diff 2.09e-06 / rel diff 2.26e-07.
> Pattern J B.2 overlay per scope_reframing §2 line 176-177
> (internal-default divergence; p3_egarch is existing exemplar; p3_pp
> NOT in original §2 enumeration — added per S23 α disposition under
> §2 line 236-237 overlay permission). **Fixture:** stationary AR(1),
> φ=0.7, σ=1.0, T=500, seed=42, burn-in 100, bandwidth pinned 5,
> trend="c"; single-seeded fixture; parameter-sensitivity coverage
> NOT established at this validation tier; Q3b extension scope.
> **Two-layer-framing risk attribution:** Layer 1 arch-path
> (arch.PhillipsPerron) bit-exact-loose validated within Pattern J
> widening; attribution from pp_test output for parameter
> configurations matching fixture-similar conditions conditional on
> (a) Layer 1 backend-dispatcher selecting arch path (statsmodels-
> path + manual-path NOT validated); (b) Layer 2 engine orchestration
> correctness (4-option regression allowlist + NaN handling + per-
> series loop + backend-dispatcher method recording + significance
> disclosure + interpretation; validation scope per
> `engine/techniques/pp_test.py` lines 211-434 + 45-67 + 253-264 +
> 274-368 + 372-422). **Triple-role retraction surface compounding
> (THREE publication contexts):** pp_test engine module plays
> standalone-technique role AND 3b parallel-test helper-export role
> AND 3d CONFLICTING tie-breaker role per module docstring lines
> 9-15 verbatim; `_run_pp_single` (lines 172-208) consumed by
> `adf_test.py` `_run_triage` at line 535 (3b) AND lines 559-565
> (3d); pp_test errors propagate to standalone publication output
> + adf_test ribbon joint verdict publication output + adf_test
> ribbon tie-breaker resolution. **Triage-path bandwidth divergence
> from Layer 1 fixture:** triage invokes `_run_pp_single` with
> `lags=None` → "auto" → Schwert (2/9) → varies with n; Layer 1
> fixture validates pinned LAG=5 only; triage-path operational
> behavior NOT in audit parameter space at non-fixture n. Pre-Path
> α expert review status.

#### Disclosure pattern (iv) — Internal use disclosure (Tier II.bit-exact-loose + Pattern J B.2 overlay + triple-role)

> `pp_test` cross-package PASS validated against R `urca::ur.pp`
> within Pattern J widening (Layer 1 arch-path; bit-exact-loose
> at 2e-6 abs); Layer 1 statsmodels/manual alternatives + Layer 2
> engine orchestration pending expert review. Triple-role engine
> module: also exposes `_run_pp_single` helper to `adf_test.py`
> triage at 3b parallel + 3d tie-breaker. Pre-Path α.

**Validation provenance audit checklist (Workstream B §1 four-question
audit; applied per Q1 entry close):**

- **Q-A (extracted/cited evidence vs inferred reasoning):**
  Extracted/cited evidence. Reference (R urca::ur.pp 1.3.4;
  type="Z-tau"; model="constant") per audit Reference field
  (verbatim). Audit date (2026-04-29) per audit Date field (verbatim).
  Verdict + Pattern (PASS Pattern J widening) per audit Verdict line
  (verbatim). Tolerance class (closed_form) per audit Tolerance class
  line (verbatim). Numeric metric (abs diff 2.09e-06; rel diff
  2.26e-07; TSL -9.25345071447954 vs Reference -9.25345280545195) per
  audit Result table (verbatim). Fixture (AR(1) φ=0.7 σ=1.0 T=500
  seed=42 burn-in 100 bandwidth=5 trend="c") per audit Fixture +
  Diagnostics sections (verbatim). Pattern J B.2 overlay
  characterization per scope_reframing §2 line 176-177 (internal-
  default divergence; p3_egarch exemplar) + §2 line 236-237 (Tier V
  overlay permission); p3_pp NOT in original §2 Tier II.bit-exact OR
  Tier V enumeration — added per S23 α disposition under post-S6
  inference grounded at audit Pattern J observation explicit
  (verbatim audit lines 36-43). Two-layer + triple-role +
  backend-dispatcher + Layer 1 engine-extends-beyond-harness framing
  per S23 STOP 2 Step 0 empirical investigation (verbatim re-Reads
  of p3_pp_audit.md + p3_pp.py harness + 435 LOC pp_test.py engine +
  adf_test.py `_run_triage` lines 506-565) + S14b two-layer-amendment
  + S14c upstream + S15/S17/S18 downstream + S21 parallel-tests +
  S22 dual-role topology precedent + α tier + αa-conditional A10
  disposition. Layer 2 (lines 211-434 + 45-67 + 253-264 + 274-368 +
  372-422) sub-components empirically grounded per Step 0 (d)
  verbatim line ranges. Triple-role engine module characterization
  per module docstring lines 9-15 verbatim. Helper-export consumption
  by adf_test.py `_run_triage` at 3b (line 535) + 3d (lines 559-565)
  per S21 adf_test entry Layer 3 sub-components 3b + 3d codification
  (cross-reference). Catalog mapping (1:1) verified per audit Wrapper
  field sole engine module reference. **A9 Class B revised default
  discipline operating observation:** S23 Step 0 STOP 2 working-
  hypothesis-anchors empirically CONFIRMED on triple-role + backend-
  dispatcher (NOT diverging); tier disposition non-obvious per CHAT
  RATIFICATION #2 pre-ratification-declined → Step 0 surfaces α/β/γ
  tier disposition options → Chat ratifies α. Class B counter post-
  S23 n=4 ACTIVE unchanged; no instance increment because no
  complexity-assumption failure manifested at S23 trigger or entry
  text. **Pattern maturation observation: A9 Class B revised default
  discipline successfully shifts operation from reactive-catch
  (S15+S17+S21+S22 precedent: complexity-assumption failures
  manifested at trigger drafting, caught at Step 0 empirical re-Read,
  re-disposition cycle absorbed via Option II Stage 3-4) to
  proactive-prevention (S23 first-instance: tier disposition pre-
  ratification-declined at trigger drafting under CHAT RATIFICATION
  #2; α/β/γ options surfaced at Step 0 per design; no manifest
  failure to catch).** Discipline maturation forward-instrumentation
  candidate for §19.4 absorption #3 codification refinement
  (institutional discipline observation; NOT a Class B sub-pattern
  subdivision per Previous Chat 1.3 walkback collapsing B.i/B.ii to
  single Class B with bidirectional manifestation). **A9 Class A
  6th-instance candidate caught at S23-pre Step 0 (b):** Doc 2
  handoff script (Previous Chat authored) asserted 'Tier expected
  II.bit-exact per scope_reframing §2 line 130 (p3_pp explicitly
  listed)' without empirical re-Read; empirical scope_reframing §2
  line 127-131 Tier II.bit-exact 12-wrapper enumeration shows p3_pp
  NOT in list — schema-misattribution failure mode analogous to
  Sub-pattern 4 (S18 tier-enumeration omission Instance #5). Class A
  counter post-S23 candidate n=6 pending §19.4 absorption #3
  codification (deferred per CHAT RATIFICATION standard pattern).
  **Sub-pattern variant distinctive: catch at S23-pre Step 0 (b)
  empirical re-Read per A6 BLOCKING + A9 Class A mitigation
  discipline operating proactively; failure pattern did NOT manifest
  in S23 trigger or entry text.** Absorption #3 codification
  distinguishes (i) Class A instances where failure manifested in
  committed entry text and amended at next sub-session (S11 + S12 +
  S16-absorption + S18 precedent: reactive-catch operation) vs (ii)
  Class A candidate where failure caught at Step 0 pre-trigger
  empirical re-Read (S23 first-instance: proactive-prevention
  operation). Sub-pattern variant codification candidate for
  absorption #3 — pairs with A9 Class B revised default maturation
  observation above; both reflect discipline maturation from
  reactive-catch to proactive-prevention operation as institutional
  discipline observation. **Engine-extends-beyond-harness pattern
  THIRD observation per §4.7 forward instrumentation — codification
  refinement triad EMPIRICALLY COMPLETE at n=3 per A3 second-
  observation tightening precedent threshold satisfied:** Layer 3
  (S21) + Layer 2 (S22) + Layer 1 backend-dispatcher (S23);
  Workstream B §4.7 amendment cycle candidate B per S23 commit
  banking. Verify-state-at-first-consumption sub-discipline 17th
  instance application (forward-at-authoring + Step 0 confirmation
  of triple-role + backend-dispatcher working hypothesis under §4.6
  Option II workflow Stage 3 mature operation; matures from S22 13th-
  instance Class B different-topology-than-expected falsification
  with confirmation-rather-than-falsification observation now codified
  as standard operation under revised default). **Q-A bullet density
  acknowledgment:** Q-A density at S23 elevated per first-instance
  novelty enumeration sub-section pattern + triple-role + Pattern J
  overlay + backend-dispatcher + Layer 1 engine-extends-beyond-
  harness + bandwidth divergence content compounding. Workstream B
  amendment cycle codification candidate for Q-A density convention
  if pattern recurs at S24+ Q1 entries (candidate C per S23 commit
  message banking).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at ninth-technique selection (user ratified
  pp_test under Tier 2 case-against framing per S22-close proposal
  as "Block 12 Stationarity Tests completion second catalog block
  fully Q1-amended; sequential disposition per (c) γ continuation"
  + S23-pre meta ratification (α) Mark 3 unprompted case-against
  discipline operative; case-against weighted but not invalidating
  per efficient ratification disposition). Pro-forma elements present
  per Mark 3 efficient-ratification pattern (operating-context
  preservation per Workstream B §5.3) **per Workstream B §1.4 Q-B
  operational pattern codification at S20**. **Q-B pattern persists
  at n=10 across S12 + S13 + S14b + S14c + S15 + S17 + S18 + S21 +
  S22 + S23; well past n=4 codification candidate threshold; §1.4
  codified observation refinement at empirical pattern accumulation**
  (n=7 at §1.4 S20 codification → n=8 at S21 → n=9 at S22 → n=10 at
  S23 reinforcement; Workstream B amendment cycle candidate A per
  S23 commit banking). Not pro-forma across all upstream decisions
  for this technique (Tier disposition required substantive STOP 2
  cycle + α/β/γ disposition options ratification + (α) Tier II.bit-
  exact-loose + Tier V Pattern J B.2 overlay first-instance precedent
  ratified + αa-conditional A10 Sub-class 2a taxonomy refinement
  modification + NEW Findings (i) + (ii) inclusion ratifications +
  asymmetric disclosure probing question disposition + dedicated
  novelty enumeration sub-section 6-sub-section framing ratified;
  substantive Chat engagement at structural-decision points
  empirically observed).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 arch-path (arch.PhillipsPerron math layer)** per
  PASS Pattern J widening verdict at closed_form tolerance
  (test_statistic abs diff 2.09e-06; closed-form Newey-West correction
  to Dickey-Fuller t-statistic) against canonical R `urca::ur.pp`
  reference; reproducibility + cross-package agreement institutional-
  grade evidence within Pattern J widening accommodation.
  **Conditional for Layer 1 backend-dispatcher alternatives** —
  statsmodels.phillips_perron path + `_manual_pp` fallback require
  expert review of: equivalence to arch-path at base config OR cross-
  package agreement at non-arch-installed environments. **Conditional
  for Layer 2 (engine pp_test orchestration)** — requires expert
  review of engine implementation OR engine-output cross-check
  against harness arch.PhillipsPerron at base pinned config for
  variant correctness review (4-option regression allowlist
  appropriateness + NaN handling via `_prepare_series` correctness +
  per-series loop pattern + backend-dispatcher method disclosure +
  significance disclosure construction + interpretation block
  construction). **Conditional for Triple-role helper-export** —
  requires expert review of: `_run_pp_single` returned-dict contract
  correctness (consumed by adf_test._run_triage at 3b parallel
  invocation AND 3d CONFLICTING tie-breaker); error path correctness
  (consumed by adf_test triage error handling); critical_values_ordered
  ordering correctness; decision_h0_rejected logic appropriateness
  for both 3b parallel-test verdict computation AND 3d tie-breaker
  resolution; triage-path bandwidth divergence (lags=None → auto →
  Schwert (2/9)) operational appropriateness at non-fixture n.
  **Critical Q-C framing per triple-role context:** published-research
  user invoking `pp_test` directly receives standalone single-test
  output (two-layer framing applies); published-research user
  invoking `adf_test` from ribbon receives joint verdict that
  CONSUMES pp_test._run_pp_single output at BOTH 3b parallel verdict
  AND 3d CONFLICTING tie-breaker resolution; defensibility to all
  three audiences (published audience + Morgan Stanley compliance +
  Path α expert reviewer) UNDER Layer 1 backend-dispatcher + Layer 2
  + Triple-role helper-export expert review acknowledgment. Defensible
  to all three audiences with disclosure language as drafted: published
  audience (two-layer + triple-role + Pattern J overlay framing
  transparent with backend-dispatcher caveat + helper-export caveat
  + triage-path bandwidth caveat); Morgan Stanley compliance review
  (precise audit citation + tier taxonomy + Layer 1 / Layer 2 /
  Triple-role scope delineation + Pattern J B.2 overlay justification
  + triple-role retraction surface compounding disclosure); external
  expert reviewer at Path α close (verbatim audit numerics + honest
  disclosure of Pattern J widening + backend-dispatcher alternatives
  + Layer 2 orchestration + triple-role helper-export contract scope
  + triage-path bandwidth divergence; Q3b extension pending).

- **Q-D (retraction surface if expert review later finds inadequacy):**
  Medium-HIGH compounding ACROSS THREE PUBLICATION CONTEXTS. pp_test
  is canonical stationarity testing methodology (companion to ADF
  + KPSS for joint stationarity inference; serial-correlation-
  robust Z(τ) statistic via Newey-West correction; widely used in
  joint stationarity inference per published research + risk model
  documentation). **Layer-specific + triple-role retraction surface
  (per S23 two-layer + triple-role + Pattern J overlay framing):**
  - Layer 1 arch-path (arch.PhillipsPerron math layer within Pattern
    J widening): LOW; PASS verdict against canonical R urca::ur.pp
    at closed_form tolerance; Pattern J B.2 internal-default
    divergence (HAC kernel + variance divisor) accommodated; expert
    review surfacing upstream error would affect pp_test specifically
    (NO multi-map propagation risk; 1:1 catalog↔wrapper).
  - Layer 1 backend-dispatcher alternatives (statsmodels-path +
    `_manual_pp` path): MEDIUM; alternative implementations NOT
    audit-validated; runtime backend selection drives published
    output; expert review surfacing material divergence in
    statsmodels-path OR `_manual_pp` from arch-path baseline would
    invalidate pp_test output specifically when alternative path
    selected at runtime.
  - Layer 2 (engine pp_test orchestration: 4-option regression
    allowlist + NaN handling + per-series loop + backend-dispatcher
    method recording + significance disclosure + interpretation):
    MEDIUM analogous to S14b/S15/S21/S22 Layer 2 (engine
    implementation equivalence) + PP-specific 4-option regression
    allowlist scope (broader than kpss_test 2-option) + interpretation
    block construction + significance disclosure formula.
  - **Triple-role helper-export (`_run_pp_single` at 3b + 3d):
    MEDIUM-HIGH-CRITICAL COMPOUNDING ACROSS THREE PUBLICATION
    CONTEXTS** — pp_test correctness affects (i) standalone publication
    output (the typical pp_test ribbon invocation use case); (ii)
    adf_test ribbon joint verdict publication output via 3b parallel-
    test invocation (the S21 adf_test ribbon-default publication
    context per `_is_triage_mode` dispatch; KPSS shares this
    compounding via S22 dual-role); (iii) adf_test ribbon tie-
    breaker resolution via 3d CONFLICTING disposition (the S21 Layer
    3 sub-component 3d operational distinctive; UNIQUE to pp_test
    among triage members — KPSS does NOT participate in 3d tie-
    breaker). Expert review surfacing material errors in
    `_run_pp_single` contract (returned-dict structure; error path;
    critical_values_ordered ordering; decision_h0_rejected logic)
    would invalidate BOTH the standalone "stationarity testing via
    PP" claim AND the adf_test "joint ADF + KPSS + PP verdict" claim
    AND the adf_test "CONFLICTING tie-breaker resolution" claim
    (Layer 3 sub-component 3d "PP tie-breaker for CONFLICTING
    verdicts" consumes this helper UNIQUELY). **Topologically
    distinct from S14b/S15/S17/S18 Layer 2 MEDIUM downstream
    framings, S14c Layer 2b MEDIUM-HIGH upstream framing, S21 Layer
    3 MEDIUM-HIGH-CRITICAL parallel-tests framings, AND S22 Layer
    2 + Dual-role MEDIUM-HIGH compounding framing:** S23 Triple-
    role propagates pp_test errors INTO adf_test ribbon publication
    context at TWO distinct operational coupling points (3b
    parallel + 3d tie-breaker); operationally distinct risk surface
    from single-coupling-point upstream/downstream/parallel-tests/
    dual-role patterns. **Critical triple-role publication-context
    elevation:** adf_test ribbon-default publication output IS the
    joint verdict per `_is_triage_mode` dispatch (per S21 Layer 3
    framing); pp_test errors via `_run_pp_single` propagate into
    that publication output via 3b AND 3d operational coupling
    points; expert review surfacing pp_test errors specifically also
    invalidates adf_test ribbon publication output at both coupling
    points, not just standalone pp_test output.
  - **Triage-path bandwidth divergence retraction surface:** triage
    invokes `_run_pp_single` with `lags=None` → "auto" → Schwert
    (2/9) → varies with n; Layer 1 fixture validates pinned LAG=5
    only; triage-path operational behavior NOT in audit parameter
    space at non-fixture n; expert review surfacing bandwidth-
    selection material divergence would invalidate triage-path
    pp_test output at non-fixture n while leaving standalone
    pinned-LAG operations intact (asymmetric retraction surface).

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; ninth technique to enter status per S23
ratification; **THIRD Block 12 Stationarity Tests entry — Block 12
FULLY Q1-AMENDED** (second catalog block to complete after Block 1
Causality at S18; per-block continuation pattern from first-entry
through completion at three-entry block instantiated; Block 1
milestone forward instrumentation note at §19.4 lines 1086-1107
refinement candidate for absorption #3 to characterize per-block
continuation pattern at n=2 catalog block observations); **FIRST
Tier II.bit-exact-loose + Tier V Pattern J B.2 overlay entry**
(precedent for future Pattern J-affected wrappers entering §2.5;
sub-class formalization forward instrumentation if S24+ surfaces
second Pattern J overlay entry per A3 second-observation tightening
precedent); **FIRST triple-role helper-export entry** (operationally
distinct from S22 kpss_test dual-role; 3b parallel + 3d CONFLICTING
tie-breaker compounding across THREE publication contexts);
**FIRST dedicated novelty enumeration sub-section** (3a-3f six-
sub-section framing; codification candidate for Workstream B §3
addendum or §5.4 if S24+ Q1 entries replicate pattern per A3
second-observation tightening precedent). **S23 two-layer +
triple-role + backend-dispatcher + Pattern J overlay framing:
Layer 1 arch-path (arch.PhillipsPerron vs R urca::ur.pp) bit-
exact-loose PASS within Pattern J widening; Layer 1 statsmodels-
path + manual-path alternatives NOT audit-validated, runtime
backend selection drives published output; Layer 2 (engine pp_test
orchestration) plausibly equivalent at base pinned config but
variants engine-specific; Triple-role helper-export
(`_run_pp_single` consumed by adf_test `_run_triage` at 3b + 3d)
NOT parity-validated, engine-specific operational coupling driving
compounded retraction surface across THREE publication contexts;
triage-path bandwidth divergence from Layer 1 fixture asymmetric
disclosure requires expert review.** **A9 Class B counter post-S23:
n=4 ACTIVE** (unchanged; working hypothesis anchors empirically
CONFIRMED at Step 0 per A9 Class B revised default discipline
operating correctly; pattern matures from falsification-cycle to
confirmation-cycle observation now codified as standard operation;
**§19.4 absorption #3 deferred candidates:** (1) A9 Class B n=4
codification reinforcement with single-pattern refinement per
Previous Chat 1.3 walkback (B.i/B.ii collapse to bidirectional
manifestation; NOT sub-pattern subdivision); (2) A9 Class B revised
default discipline maturation observation (reactive-catch →
proactive-prevention; institutional discipline forward
instrumentation); (3) A10 Sub-class 2a taxonomy disposition (αa)
keeps-2a-as-general-two-layer vs (αb) splits-2a-vs-2a-triple-role;
n=2 empirical baseline (S22 kpss + S23 pp); (4) A10 Sub-class 2d
codification (S21 three-layer-parallel-tests first-instance); (5)
A9 Class A 5th sub-pattern accumulation (S18 tier-enumeration
omission) + A9 Class A 6th-instance candidate (S23-pre Doc 2 tier-
enumeration omission proactive-catch variant; reactive-vs-proactive
sub-pattern variant codification); (6) Path A canonical lock 7th
instance + elevation-candidate-absorption sub-mechanism 6th baseline
observation; (7) Block 1 Causality milestone refinement + Block 12
Stationarity Tests Q1 completion milestone (per-block continuation
pattern characterization at n=2 catalog block observations); (8)
Pattern J overlay first-instance forward-instrumentation thread
(sub-class formalization candidate if S24+ surfaces second Pattern J
overlay entry); (9) Retroactive S22 kpss_test Q-A disclosure
amendment candidate (triage-path bandwidth divergence symmetric to
S23 NEW Finding 2; CHAT RATIFICATION #4 independent sequential
disposition deferred resolution under absorption #3 full structure
visibility). **Workstream B amendment cycle separate-lane candidates**
(NOT §19.4 absorption #3 scope): (A) §1.4 Q-B operational pattern
n=7 → n=10 codification update; (B) §4.7 codification refinement
triad EMPIRICALLY COMPLETE at n=3 per A3 second-observation
tightening precedent threshold satisfied (Layer 1 backend-dispatcher
S23 + Layer 2 S22 + Layer 3 S21); (C) novelty enumeration sub-
section pattern codification at Workstream B §3 addendum or §5.4
if S24+ Q1 entries replicate pattern; (D) β grant scope-tightening
evaluation per Previous Chat 1.7 honest mark). **A9 Class A counter
post-S23: n=5 ACTIVE + candidate n=6 pending absorption #3
codification** (S23-pre Doc 2 handoff script tier-enumeration
omission caught at S23-pre Step 0 (b) per A6 BLOCKING + A9 Class A
mitigation discipline; Sub-pattern variant catch at Step 0 pre-
trigger empirical re-Read; absorption #3 codifies reactive-vs-
proactive sub-pattern variant). **Block 12 Stationarity Tests Q1
work program COMPLETION milestone (second catalog block fully Q1-
amended after Block 1 Causality at S18):** S21 adf_test + S22
kpss_test + S23 pp_test = 3-entry Block 12 cumulative ~1300 net
LOC across all entries; per-block continuation pattern from first-
entry through completion at three-entry block instantiated;
forward instrumentation for absorption #3 refinement of §19.4
lines 1086-1107 Block 1 milestone characterizing per-block
continuation pattern at n=2 catalog block observations.

### denton_chowlin_disaggregation (Phase 7+ S26; tenth §2.5 entry; FIRST Block 8 Missing Data entry; FIRST §4.7.A harness-bypasses-engine pattern Q1 §2.5 entry per S25 codification; FIRST §4.7.A + §4.7.B COMPOUND pattern Q1 §2.5 entry per S25 §4.7.E pattern relationship codification; TWO-LAYER + HARNESS-REIMPLEMENTS-ENGINE-MATH + ENGINE-METHOD-EXTENSION framing per S26 STOP 2 + Chat α disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** Tier
II.bit-exact — Phase 3 cross-package bit-exact parity validated
(Pattern A.2 per scope_reframing §2 line 130 12-wrapper enumeration:
`p3_denton_chowlin`). **Important nuance (compound §4.7.A + §4.7.B
pattern framing per S25 §4.7.E codification; FIRST §2.5 entry
exhibiting BOTH patterns concurrently):** tier classification
applies to Layer 1 math (Denton PFD closed-form KKT system; harness
reimplements TSL math directly + R `tempdisagg::td(method=
"denton-cholette")` cross-package validated bit-exact). Layer 2
(engine module orchestration: method allowlist gating + NaN handling
+ aggregation constraint verification + method dispatch) plausibly
equivalent at base pinned config but variants engine-specific.
**Engine extends substantially beyond harness audit scope via Layer
2 method extension:** engine implements TWO methods (Denton +
Chow-Lin GLS) + ML ρ estimation `_estimate_rho` (lines 188-234) +
3-option allowlist gates per CAI Phase 2 Session 19 fixes (F-MD-
DENTON-METHOD + F-MD-DENTON-CONVRATIO + F-MD-DENTON-RHO); p3_denton_chowlin
audit validates Denton PFD path ONLY; Chow-Lin path + ML ρ estimation
NOT audit-validated. See Validation claim scope below for compound
pattern detail.

**Framing precedent note (1:1 catalog↔wrapper; TWO-LAYER + HARNESS-
REIMPLEMENTS-ENGINE-MATH + ENGINE-METHOD-EXTENSION; COMPOUND §4.7.A
+ §4.7.B pattern FIRST §2.5 instance; A10 Sub-class disposition
(αa) Sub-class 2c variant tagging with fit-strained acknowledgment
per S26 STOP 1.5 ratification):** denton_chowlin_disaggregation is
1:1 catalog↔wrapper mapping per p3_denton_chowlin audit Wrapper
field (`engine/techniques/denton_chowlin_disaggregation.py` sole
engine module).

**§4.7.A harness-bypasses-engine pattern THIRD observation candidate
per S25 §4.7.A codification** (S14a p3_ccf + S18 p3_gcc_phat n=2
baseline → S26 n=3 codification triad EMPIRICALLY COMPLETE per A3
second-observation tightening precedent threshold). p3_denton_chowlin.py
`run_tsl` lines 66-104 explicitly comments *"Mirror TSL math directly
— proportional Denton (PFD) closed form"* (line 68); harness
REIMPLEMENTS Denton math in numpy/KKT system + linalg.solve; does
NOT invoke `denton_chowlin_disaggregation.py::run()` engine entry
point; harness validates literal-identity-to-engine-Denton-math
(both implement Denton PFD closed-form; mathematically equivalent
at machine precision per audit Pattern A bit-exact 6.39e-14).

**§4.7.B engine-extends-beyond-harness pattern PARTIAL observation
(Layer 2 method extension scale):** Engine module 510 LOC implements
TWO methods + ML ρ estimation + allowlist gates per CAI Phase 2
Session 19 fixes; harness validates Denton PFD ONLY at pinned
conversion_ratio=4 (n_low=12 → n_high=48). Engine Chow-Lin method
(`_chowlin` lines 120-185 GLS regression + AR(1) residuals) + ML ρ
estimation (`_estimate_rho` lines 188-234 log-likelihood grid search)
NOT exercised by audit; engine extends beyond harness audit scope
at Layer 2 method-dispatch scale. Distinct from S22 kpss_test Layer
2 orchestration extension (orchestration-only; same single Layer 1
math function) — S26 denton_chowlin Layer 2 extension adds NEW Layer
1 math function (Chow-Lin GLS) NOT validated by Denton-only harness.

**Compound §4.7.A + §4.7.B pattern observation (NEW per S25 §4.7.E
Pattern relationship codification "technique may exhibit ONE
pattern only, BOTH patterns concurrently, or NEITHER pattern";
FIRST §2.5 entry exhibiting BOTH concurrently):** denton_chowlin
exhibits BOTH §4.7.A (harness uses different code path for Denton
math via reimplementation) AND §4.7.B (engine extends Layer 2
beyond harness Denton-only audit scope via Chow-Lin method
addition). Compound observation operationally distinct from single-
pattern observations; mitigation surface compounds:
- §4.7.A mitigation: layered framing class determination at Step 0
  (Layer 1 Denton math harness-reimplementation vs engine Denton
  implementation; mathematically equivalent but code-path-distinct)
- §4.7.B mitigation: scale-of-extension disclosure (Chow-Lin method
  + ML ρ estimation NOT audit-validated; Q-D retraction surface
  elevated for non-Denton-method invocations)

**A10 Sub-class disposition: (αa) Sub-class 2c three-layer-downstream
variant tagging extension** (conservative working hypothesis per A3
precedent at n=1 first-instance; ratified at S26 STOP 1.5 with
explicit fit-strained acknowledgment): treats compound §4.7.A +
§4.7.B observation as Sub-class 2c variant with harness-reimplements-
math tag + method-extension tag. Preserves taxonomy stability +
documents empirical variation at n=1 first-instance observation.
**Fit-strained acknowledgment:** Sub-class 2c codified instances
(S15 rolling_ccf_lag + S17 dtw_alignment_lag + S18 gcc_phat_delay)
all use CLEAN engine-uses-same-function pattern (harness invokes
engine module's underlying math function; engine extends downstream
via post-processing). denton_chowlin BREAKS this convention: harness
REIMPLEMENTS engine math directly (§4.7.A harness-bypasses-engine
pattern manifestation) + engine extends LAYER 2 via NEW math
function (Chow-Lin method addition; §4.7.B pattern manifestation).
(αa) variant tagging at n=1 is operationally conservative per A3
precedent BUT Sub-class 2c definitional fit is empirically strained.
**Forward instrumentation (NEW per S26 STOP 1.5 ratification):**
(αb) NEW Sub-class 2e codification candidate "harness-reimplements-
engine-math + engine-method-extension" becomes codification-ready
at absorption #4 IF second observation surfaces at S26+1
(kalman_imputation) OR S26+2 (loess_interpolation) per A3 second-
observation tightening precedent threshold at n=2. Absorption #4
dispositions between (i) Sub-class 2c variant tagging preserved +
(αb) deferred indefinitely if second observation absent vs (ii) NEW
Sub-class 2e codified at n=2 with denton_chowlin retroactively
migrated from Sub-class 2c variant to Sub-class 2e first-instance
baseline.

**Reference:** R `tempdisagg::td(method="denton-cholette")` (tempdisagg 1.2.0)
**Verdict:** PASS Pattern A cross-package machine precision (Layer
1 Denton PFD math only; see Validation claim scope for Layer 2 +
Chow-Lin extension coverage)
**Audit:** `tools/reference_parity/reports/p3_denton_chowlin_audit.md`
**Audit date:** 2026-04-29
**disaggregated abs diff:** 6.39e-14 (max abs diff across vector);
rel diff: 1.35e-15
**Tolerance class:** closed_form
**Fixture:** 12 quarterly aggregates of 48 monthly indicator values
(seed=42); pinned conversion_ratio=4 / method=denton-cholette

**Source files (compound §4.7.A + §4.7.B per S26 α framing):**
`tools/reference_parity/harness/checks/p3_denton_chowlin.py` lines
66-104 (harness TSL arm REIMPLEMENTS Denton PFD math directly via
numpy KKT system + linalg.solve; line 68 explicit comment "Mirror
TSL math directly — proportional Denton (PFD) closed form"; harness
does NOT invoke `denton_chowlin_disaggregation.py::run()` engine
entry point; §4.7.A harness-bypasses-engine pattern manifestation)
+ `tools/reference_parity/harness/checks/p3_denton_chowlin.py` lines
106-140 (harness reference arm invokes R `tempdisagg::td(agg_ts ~ 0
+ ind_ts, conversion="sum", method="denton-cholette")` via RBridge;
extracts disaggregated vector)
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 1-12
(module docstring: "Denton and Chow-Lin Temporal Disaggregation...
Implements: Denton (proportional first differences) method + Chow-
Lin (GLS regression-based) method. Both implemented from scratch
with numpy/scipy.")
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 31-42
(`_build_aggregation_matrix`: aggregation matrix C such that
C @ y_high = y_low; shared helper)
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 45-117
(Layer 1E engine Denton implementation: `_denton_proportional` PFD
method with KKT system + first-difference matrix + diagonal scaling;
mathematically equivalent to Layer 1H harness reimplementation per
audit PASS Pattern A bit-exact 6.39e-14 BUT distinct code path)
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 120-185
(Layer 1E engine Chow-Lin math extension: `_chowlin` GLS regression
with AR(1) residuals + indicator-as-regressor + distribution matrix
L = V_high @ C^T @ V_low^-1; NEW Layer 1E function NOT in harness
audit scope; NOT validated by p3_denton_chowlin audit Denton-only
scope)
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 188-234
(Layer 1E Chow-Lin math extension: `_estimate_rho` ML grid search
over rho ∈ (0.01, 0.99) maximizing log-likelihood; n_grid=20 or 50
per preset; NOT validated by audit)
+ `engine/techniques/denton_chowlin_disaggregation.py` lines 237-510
(Layer 2 standalone orchestration: `run()` main entry with method
dispatch denton/chowlin + 3-option allowlist gating per CAI Phase
2 Session 19 fixes F-MD-DENTON-METHOD + F-MD-DENTON-CONVRATIO +
F-MD-DENTON-RHO + NaN handling + indicator series handling +
aggregation constraint verification + result formatting +
significance disclosure + interpretation + audit_fields construction)
+ `tools/reference_parity/reports/p3_denton_chowlin_audit.md`

**Validation claim scope (TIER II.BIT-EXACT + COMPOUND §4.7.A +
§4.7.B PATTERN per S26 α + αa-conditional disposition; Layer 1H /
Layer 1E (Denton) / Layer 1E (Chow-Lin) / Layer 2 framework operative
per S26 STOP 1.5 second close):** TSL denton_chowlin_disaggregation
output relies on two layered computations within standalone-technique
role (Layer 1 Denton OR Chow-Lin math + Layer 2 engine orchestration).
p3_denton_chowlin audit validates Layer 1H Denton PFD math (harness
reimplementation vs R tempdisagg::td) at single seeded fixture (12
quarterly aggregates / 48 monthly indicator / seed=42 /
conversion_ratio=4 / method=denton-cholette pinned); disaggregated
metric measures harness Denton PFD output vs R tempdisagg::td
output agreement (abs diff 6.39e-14 PASS), NOT Layer 1E engine
Denton implementation correctness, NOT Layer 1E engine Chow-Lin
implementation correctness, NOT ML ρ estimation correctness, NOT
Layer 2 engine standalone orchestration correctness.

- **Layer 1H Denton PFD math (HARNESS REIMPLEMENTATION; validated
  cross-package bit-exact):** PASS Pattern A at machine precision
  (abs diff 6.39e-14; rel diff 1.35e-15) against canonical R
  `tempdisagg::td(method="denton-cholette")`; closed-form quadratic
  optimization (minimize sum of squared proportional first
  differences subject to aggregation constraint). Validation
  scope: harness's reimplementation of Denton PFD math equivalent
  to R reference. **§4.7.A pattern caveat:** engine module
  `_denton_proportional` (lines 45-117) is DIFFERENT code path
  from harness reimplementation; mathematically equivalent per
  audit PASS but engine implementation correctness NOT directly
  audit-validated (audit validates harness reimplementation vs R,
  not engine vs R).
- **Layer 1E Denton implementation (ENGINE module; validation scope
  conditional):** engine `_denton_proportional` lines 45-117 +
  `_build_aggregation_matrix` lines 31-42 implement Denton PFD
  closed-form with KKT system + diagonal scaling + first-difference
  matrix; mathematically equivalent to Layer 1H harness
  reimplementation but NOT directly audit-validated against R
  reference. Q-D retraction surface conditional on Layer 1E engine
  implementation correctness AT DENTON METHOD INVOCATION.
- **Layer 1E engine Chow-Lin math extension (NEW Layer 1E function
  NOT in harness audit scope; NOT VALIDATED):** engine `_chowlin`
  lines 120-185 + `_estimate_rho` lines 188-234 implement Chow-Lin
  GLS regression with AR(1) residuals + ML ρ estimation; NOT
  exercised by p3_denton_chowlin audit (audit validates Denton Layer
  1H harness reimplementation only at pinned method=denton-cholette).
  Engine Chow-Lin Layer 1E path active when `method="chowlin"`
  (default per engine line 280!) — ribbon-default invocation goes
  through Chow-Lin Layer 1E NOT Denton Layer 1E. **Critical
  operational nuance:** ribbon-default invocation receives
  UNVALIDATED Chow-Lin Layer 1E output; Denton Layer 1E invocation
  requires explicit `method="denton"` parameter selection (modulo
  §4.7.A caveat that Denton Layer 1E itself is not directly audit-
  validated; audit validates Denton Layer 1H harness reimplementation
  only).
- **Layer 2 engine orchestration (validation scope conditional):**
  - 3-option allowlist gating per CAI Phase 2 Session 19 fixes
    (F-MD-DENTON-METHOD + F-MD-DENTON-CONVRATIO + F-MD-DENTON-RHO
    per lines 281-360): method allowlist (denton, chowlin) +
    conversion_ratio >= 2 + rho ∈ (0, 1) explicit gates
  - NaN handling (line 265-270): low-frequency series NaN removal
  - Indicator series handling (lines 317-328): optional second
    series; fallback to time trend if length insufficient
  - Aggregation constraint verification (lines 367-369): post-
    computation C @ x_high vs y_low check
  - Result formatting + significance disclosure + interpretation +
    audit_fields construction

#### Disclosure pattern (i) — Research note footnote (Tier II.bit-exact + compound §4.7 pattern + Chow-Lin extension)

> This analysis uses TSL technique `denton_chowlin_disaggregation`,
> cross-package bit-exact validated against R `tempdisagg::td(method=
> "denton-cholette")` (tempdisagg 1.2.0) per Phase 3 audit dated
> 2026-04-29 (abs diff 6.39e-14). Validation scope: Denton PFD math
> only at harness reimplementation vs R reference; engine
> implementation conditional on expert review per §4.7.A harness-
> bypasses-engine pattern. Engine module also implements Chow-Lin
> GLS method (DEFAULT method per ribbon invocation) + ML ρ
> estimation; Chow-Lin path NOT audit-validated. Pre-Path α expert
> review status.

#### Disclosure pattern (ii) — Technical appendix (Tier II.bit-exact + compound §4.7 + Chow-Lin extension)

> Methodology: TSL technique `denton_chowlin_disaggregation`
> validated per Phase 3 reference parity infrastructure under
> two-layer + compound §4.7.A + §4.7.B pattern framing. **Reference:**
> R `tempdisagg::td(method="denton-cholette")` (tempdisagg 1.2.0).
> **Verdict:** PASS Pattern A cross-package machine precision;
> disaggregated abs diff 6.39e-14 (rel diff 1.35e-15). **Audit
> date:** 2026-04-29. **Fixture:** 12 quarterly aggregates of 48
> monthly indicator values (seed=42); conversion_ratio=4 pinned;
> method=denton-cholette pinned. **Compound §4.7.A + §4.7.B pattern
> caveats:** (a) §4.7.A harness-bypasses-engine: p3_denton_chowlin
> harness REIMPLEMENTS Denton PFD math directly in numpy/KKT system;
> validates harness reimplementation vs R reference; engine
> `_denton_proportional` implementation NOT directly validated
> against R; mathematically equivalent per audit PASS but code-path-
> distinct from harness; (b) §4.7.B engine-extends-beyond-harness:
> engine implements TWO methods (Denton + Chow-Lin); ribbon-default
> invocation goes through Chow-Lin path (default per engine `method`
> parameter); Chow-Lin path + ML ρ estimation NOT audit-validated;
> Layer 2 method extension scale beyond Denton-only audit scope.
> Q3b extension pending. Pre-Path α expert review status.

#### Disclosure pattern (iii) — Risk model documentation (Tier II.bit-exact + compound §4.7 + audit citation)

> `denton_chowlin_disaggregation` validation: TSL Tier II.bit-exact
> under compound §4.7.A + §4.7.B pattern framing. **Reference:** R
> `tempdisagg::td(method="denton-cholette")` (tempdisagg 1.2.0).
> **Audit:** `tools/reference_parity/reports/p3_denton_chowlin_audit.md`
> dated 2026-04-29. **Verdict:** PASS Pattern A bit-exact at machine
> precision; disaggregated abs diff 6.39e-14 / rel diff 1.35e-15.
> **Fixture:** 12 quarterly aggregates / 48 monthly indicator /
> seed=42 / conversion_ratio=4 / method=denton-cholette pinned;
> single-seeded fixture; parameter-sensitivity coverage NOT
> established at this validation tier; Q3b extension scope.
> **Compound §4.7.A + §4.7.B pattern risk attribution:**
> **(a) Layer 1H Denton PFD math (harness reimplementation)
> validated bit-exact against R; Layer 1E engine `_denton_proportional`
> (lines 45-117) mathematically equivalent but code-path-distinct,
> conditional on expert review of engine implementation matching
> harness reimplementation OR engine cross-check against R at base
> config; **(b) Layer 1E Chow-Lin math extension (engine `_chowlin`
> lines 120-185 + `_estimate_rho` lines 188-234): NOT audit-
> validated; ribbon-default invocation goes through Chow-Lin Layer
> 1E; attribution from ribbon-default `denton_chowlin_disaggregation`
> output conditional on Layer 1E Chow-Lin + ML ρ estimation
> correctness AND appropriate AR(1) ρ parameter selection;
> **(c) Layer 2 standalone orchestration (CAI Phase 2 Session 19
> allowlist gating + NaN handling + indicator handling + aggregation
> constraint verification): validation scope per
> `engine/techniques/denton_chowlin_disaggregation.py` lines 237-510.
> **Method-selection asymmetric retraction surface:** explicit
> `method="denton"` invocation activates audit-validated path
> (modulo §4.7.A caveat); ribbon-default OR explicit `method="chowlin"`
> activates UNVALIDATED Chow-Lin path. Pre-Path α expert review
> status.

#### Disclosure pattern (iv) — Internal use disclosure (Tier II.bit-exact + compound §4.7)

> `denton_chowlin_disaggregation` cross-package bit-exact validated
> against R `tempdisagg::td` (Denton PFD only; harness
> reimplementation per §4.7.A); engine Denton implementation +
> Chow-Lin extension + ML ρ estimation + Layer 2 orchestration
> pending expert review. Ribbon-default uses Chow-Lin (UNVALIDATED).
> Pre-Path α.

**Validation provenance audit checklist (Workstream B §1 four-question
audit; applied per Q1 entry close):**

- **Q-A (extracted/cited evidence vs inferred reasoning):**
  Extracted/cited evidence. Reference (R tempdisagg::td 1.2.0;
  method="denton-cholette") per audit Reference field (verbatim).
  Audit date (2026-04-29) per audit Date field (verbatim). Verdict
  + Pattern (PASS Pattern A cross-package machine precision) per
  audit Verdict line (verbatim). Tolerance class (closed_form) per
  audit Tolerance class line (verbatim). Numeric metric (abs diff
  6.39e-14; rel diff 1.35e-15) per audit Result table (verbatim).
  Fixture (12 quarterly aggregates / 48 monthly indicator / seed=42
  / conversion_ratio=4 / method=denton-cholette pinned) per audit
  Fixture section (verbatim). Tier II.bit-exact characterization per
  scope_reframing §2 line 130 (`p3_denton_chowlin` explicit in
  12-wrapper enumeration). Compound §4.7.A + §4.7.B pattern framing
  per S26 STOP 2 Step 0 empirical investigation (harness lines 66-
  104 reimplementation comment line 68 verbatim + engine 510 LOC
  method-dispatch structure lines 280-362 verbatim + audit Denton-
  only scope per audit Fixture + harness pinned method) + S25 §4.7
  dual-pattern codification + §4.7.E Pattern relationship "BOTH
  patterns concurrently" framing + α Tier + αa-conditional A10
  Sub-class disposition. Layer 1H / Layer 1E (Denton) / Layer 1E
  (Chow-Lin) / Layer 2 framework operative throughout entry per
  S26 STOP 1.5 second close ratification. **§4.7.A pattern THIRD
  observation per A3 second-observation tightening precedent
  threshold satisfied at n=3** (S14a p3_ccf + S18 p3_gcc_phat + S26
  denton_chowlin = codification triad EMPIRICALLY COMPLETE);
  Workstream B §4.7.A codification refinement candidate per next
  amendment cycle (NEW Workstream B candidate G per S26 close
  banking). **§4.7.B pattern PARTIAL observation Layer 2 method-
  extension scale**: Chow-Lin Layer 1E math + ML ρ estimation NOT
  audit-validated; engine extends beyond Denton-only audit scope.
  **Compound pattern observation NEW per S25 §4.7.E codification:**
  FIRST §2.5 entry exhibiting BOTH §4.7.A + §4.7.B patterns
  concurrently per "ONE pattern only, BOTH patterns concurrently,
  or NEITHER pattern" framing. **A9 Class A 7th-instance candidate
  carry-forward from S26-pre** (Chat numerical-claim-baseline
  catalog-count-misattribution catch per A2 codification;
  codification at absorption #4 alongside §4.7.A pattern n=3
  codification triad + compound pattern observation + maturation
  observation promotion). **A9 Class B counter unchanged post-S26
  n=4 ACTIVE**: working hypothesis anchors confirmed at Step 0 per
  A9 Class B revised default discipline operating proactively per
  S22 + S23 + S25 + S26 sustained pattern. **Maturation observation
  third codification-stable observation REACHED at S26 + FIVE
  proactive-prevention timing point empirical surface**: (i) pre-
  trigger session re-entry (S23-pre + S26-pre); (ii) trigger-
  execution Step 0 (S25); (iii) STOP-cycle revision-trigger
  completeness (S25 STOP 1.5); (iv) numerical-claim-baseline pre-
  trigger (S26-pre); (v) framework-consistency-at-STOP-1.5-close
  (S26 STOP 1.5 second close); promotion candidate (§4.5 NEW sub-
  section OR A11 NEW amendment) READY for absorption #4 codification
  disposition. Verify-state-at-first-consumption sub-discipline
  21st instance application (S26-pre catalog-count-baseline + Step
  0 multi-technique empirical re-Read + STOP 2 disposition options
  surface + Step 1 entry drafting under ratified anchors + STOP
  1.5 second cycle Layer 1H/1E framework consistency catch).

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at tenth-technique selection per Mark 3
  efficient-ratification + (α) unprompted case-against discipline
  operative per Workstream B §1.4 codification + S20+S25
  reinforcement. Tier 2 case-against surfaced at S26 Step 0 STOP 2
  (3-option α/β/γ with LOC + framing-class trade-offs); Chat
  ratified α denton_chowlin per Tier II.bit-exact strength priority
  + §4.7.A pattern third observation value + scope_reframing §2
  explicit enumeration. **Q-B pattern persists at n=11 across S12
  + S13 + S14b + S14c + S15 + S17 + S18 + S21 + S22 + S23 + S26;
  §1.4 codified observation refinement at empirical pattern
  accumulation** (n=7 at §1.4 S20 codification → n=10 at S25
  refinement → n=11 at S26 reinforcement; Workstream B amendment
  cycle candidate A continues at next cycle). Substantive Chat
  engagement at structural-decision points empirically observed
  (first-technique 3-option ratification + framing class working
  hypothesis confirmation + A10 Sub-class disposition deferred
  with both (αa) and (αb) surfaced for STOP 1 + Layer 1H/1E
  terminology disambiguation revisions + Chow-Lin Layer 1E framework
  consistency extension).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1H Denton PFD math (validated cross-package via
  harness reimplementation)** per bit-exact PASS verdict at
  machine precision against R `tempdisagg::td`. **Conditional for
  Layer 1E engine Denton implementation** — §4.7.A pattern caveat:
  engine `_denton_proportional` mathematically equivalent to
  harness reimplementation per audit PASS BUT distinct code path;
  requires expert review confirming engine implementation matches
  harness reimplementation correctness OR engine cross-check
  against R reference at base config. **Conditional for Layer 1E
  engine Chow-Lin math extension** — §4.7.B pattern: Chow-Lin
  GLS + ML ρ estimation NOT audit-validated; ribbon-default
  invocation goes through Chow-Lin Layer 1E (engine `method`
  default per line 280: `"chowlin"`); attribution from ribbon-
  default output conditional on Chow-Lin + ML ρ estimation
  correctness. **Conditional for Layer 2 engine orchestration** —
  CAI Phase 2 Session 19 allowlist gating + NaN handling +
  indicator handling + aggregation constraint verification +
  interpretation; requires expert review of engine implementation
  OR engine-output cross-check at base pinned config. **Critical
  Q-C framing per ribbon-default-method context:** published-
  research user invoking `denton_chowlin_disaggregation` from
  ribbon receives Chow-Lin Layer 1E output (DEFAULT method);
  Denton-method output requires explicit `method="denton"`
  parameter selection; defensibility to all three audiences
  (published audience + Morgan Stanley compliance + Path α expert
  reviewer) UNDER compound §4.7 pattern + Layer 1E method-
  extension expert review acknowledgment.

- **Q-D (retraction surface if expert review later finds inadequacy):**
  MEDIUM-HIGH compound-pattern retraction surface. denton_chowlin
  is canonical temporal disaggregation methodology (quarterly →
  monthly OR annual → quarterly conversion preserving aggregation
  constraint; widely used in macroeconomic + financial time series
  applications). **Layer-specific + compound-pattern retraction
  surface (per S26 compound §4.7.A + §4.7.B framing; Layer 1H /
  Layer 1E framework operative):**
  - Layer 1H Denton PFD math harness-reimplementation: LOW; bit-
    exact PASS against canonical R reference; expert review
    surfacing upstream error would affect denton_chowlin Denton-
    method-only invocation specifically (NO multi-map propagation
    risk; 1:1 catalog↔wrapper).
  - **Layer 1E engine Denton implementation (§4.7.A pattern
    caveat): MEDIUM** — engine `_denton_proportional` (lines 45-
    117) NOT directly audit-validated against R reference; expert
    review surfacing material divergence from Layer 1H harness
    reimplementation would invalidate engine Denton-method
    invocations specifically; Tier II.bit-exact tier classification
    holds at Layer 1H harness validation BUT Layer 1E engine
    validation is conditional.
  - **Layer 1E engine Chow-Lin math extension (§4.7.B pattern):
    MEDIUM-HIGH** — engine `_chowlin` (lines 120-185) + ML ρ
    estimation (`_estimate_rho` lines 188-234) NOT audit-validated;
    ribbon-default invocation goes through Chow-Lin Layer 1E
    (engine `method` default = "chowlin" per line 280); expert
    review surfacing Chow-Lin GLS + ML ρ estimation errors would
    invalidate the ribbon-default `denton_chowlin_disaggregation`
    output specifically; **asymmetric retraction surface across
    method invocations:** explicit `method="denton"` invocation
    relies on Denton Layer 1E + Layer 1H harness validation (per
    §4.7.A caveat that Denton Layer 1E itself is not directly
    audit-validated; only Layer 1H is); ribbon-default + explicit
    `method="chowlin"` relies on UNVALIDATED Chow-Lin Layer 1E.
  - Layer 2 engine orchestration (allowlist gating + NaN handling
    + indicator handling + aggregation constraint verification):
    MEDIUM analogous to S14b/S15/S21/S22 Layer 2 (engine
    implementation equivalence) + denton-specific CAI Phase 2
    Session 19 allowlist scope + indicator series handling.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; tenth technique to enter status per S26
ratification; **FIRST Block 8 Missing Data entry** (initiates third
catalog block transition; Block 8 completion arc S26 + S26+1 + S26+2
anticipated; third catalog block fully Q1-amended milestone at Block
8 close; per-block continuation pattern at n=3 catalog block
observations TBD at Block 8 close); **FIRST §4.7.A harness-bypasses-
engine pattern Q1 §2.5 entry per S25 codification** (third
observation of §4.7.A pattern completing codification triad
EMPIRICALLY COMPLETE per A3 second-observation tightening precedent
threshold at n=3 [S14a + S18 + S26]); **FIRST §4.7.A + §4.7.B
COMPOUND pattern Q1 §2.5 entry per S25 §4.7.E Pattern relationship
codification** ("technique may exhibit ONE pattern only, BOTH
patterns concurrently, or NEITHER pattern"); S26 first-instance
observation of BOTH patterns concurrently within single technique.
**S26 two-layer + compound §4.7.A + §4.7.B + Chow-Lin method
extension framing + Layer 1H/Layer 1E framework operative per S26
STOP 1.5 second close: Layer 1H Denton PFD math harness-
reimplementation vs R tempdisagg::td bit-exact PASS; Layer 1E engine
Denton implementation §4.7.A caveat (mathematically equivalent but
code-path-distinct from Layer 1H; NOT directly audit-validated);
Layer 1E engine Chow-Lin math extension (§4.7.B) NOT audit-validated
and DEFAULT method per ribbon invocation; Layer 2 engine orchestration
NOT parity-validated; compound retraction surface across method-
selection asymmetric paths requires expert review.** **A10 Sub-class
disposition: (αa) Sub-class 2c variant tagging extension with
explicit fit-strained acknowledgment per S26 STOP 1.5 ratification;
(αb) NEW Sub-class 2e candidate codification-ready at absorption #4
if second harness-reimplements-engine-math observation surfaces at
S26+1 or S26+2 per A3 second-observation tightening precedent.**
**A9 Class B counter post-S26: n=4 ACTIVE** (unchanged; working
hypothesis anchors confirmed at Step 0 per A9 Class B revised
default discipline operating proactively per S22+S23+S25+S26
sustained pattern). **A9 Class A counter post-S26: n=6 ACTIVE +
candidates n=7 + n=8 pending absorption #4 codification** (n=7
candidate per S23-pre Doc 2 tier-enumeration omission proactive-
catch variant; n=8 candidate per S26-pre catalog-count-baseline
misattribution catch). **A9 Class A + Class B discipline maturation
THIRD CODIFICATION-STABLE OBSERVATION REACHED at S26** per A3
second-observation tightening precedent threshold satisfied at n=3
observations (S23 + S25 + S26 sustained proactive-prevention
operation across FIVE-timing-point empirical surface); **promotion
candidate (§19.4 §4.5 NEW sub-section OR A11 NEW amendment)
READY for absorption #4 codification disposition**. **Block 8 first-
entry status + Block 8 completion arc forward instrumentation: S26
denton_chowlin (this entry) → S26+1 [kalman_imputation OR
loess_interpolation per Chat disposition] → S26+2 [remaining Block
8 technique] → Block 8 fully Q1-amended milestone at S26+2 close;
third catalog block completion triggers per-block continuation
pattern n=3 codification at §19.4 §4 forward instrumentation note
6 refinement at next absorption cycle**.

### loess_interpolation (Phase 7+ S27; eleventh §2.5 entry; SECOND Block 8 Missing Data entry; FIRST Tier III §2.5 precedent per scope_reframing §2 lines 151-157 Pattern A.1 same-library self-parity definition; FOURTH §4.7.A pattern observation per S25 codification with NEW STRUCTURAL MECHANISM VARIANT "harness-validates-different-use-case-of-same-library-function" per S27 (α) reframe; TWO-LAYER + HARNESS-AND-ENGINE-USE-SAME-LIBRARY-FOR-DIFFERENT-PURPOSES framing per S27 STOP 2 + Chat α reframe disposition)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** **Tier
III — Phase 3 same-library self-parity validated (Pattern A.1 per
scope_reframing §2 lines 151-157 "18 wrappers per P-3 v1.2.0 §1
locked at scale")**. **FIRST §2.5 Tier III entry precedent** —
prior §2.5 entries (S12-S26) all Tier II.bit-exact OR Tier IV OR
Tier II.bit-exact-loose+V Pattern J overlay; S27 loess_interpolation
establishes Tier III handling pattern for Q1 work program forward
continuation. **Important nuance (Tier III definitional scope per
scope_reframing §2 line 154 verbatim):** "Verifies wrapper-integrity
claim only (preprocessing, parameter resolution, audit-field
rounding); does NOT validate against independent implementation."
Tier III strength bounded vs Tier II cross-package validation;
honest Q-D retraction surface characterization per Tier III scope.

**Framing precedent note (1:1 catalog↔wrapper; TWO-LAYER + HARNESS-
AND-ENGINE-USE-SAME-LIBRARY-FOR-DIFFERENT-PURPOSES; NEW §4.7.A
structural mechanism variant per S27 (α) reframe; Sub-class 2e
candidate scope refined per (αb-S27) deferred codification at
absorption #4 with Code S27 Step 0 empirical reframing):**
loess_interpolation is 1:1 catalog↔wrapper mapping per p3_loess
audit Wrapper field (`engine/techniques/loess_interpolation.py`
sole engine module).

**§4.7.A harness-bypasses-engine pattern FOURTH observation per S25
§4.7.A codification (n=4 post-triad reinforcement at S26 + NEW
structural mechanism variant at S27)**:
- S14a p3_ccf + S18 p3_gcc_phat = n=2 baseline (codified at S25)
- S26 denton_chowlin = n=3 codification triad EMPIRICALLY COMPLETE
  per A3 second-observation tightening precedent threshold
- **S27 loess_interpolation = n=4 reinforcement WITH NEW STRUCTURAL
  MECHANISM VARIANT** ("harness-validates-different-use-case-of-
  same-library-function"; distinct from S25 §4.7.A 3-mechanism list
  lines 960-967)

**NEW §4.7.A structural mechanism variant per S27 (α) reframe
ratification:** Both harness AND engine import SAME library function
(`statsmodels.nonparametric.smoothers_lowess.lowess`); use it for
DIFFERENT PURPOSES:
- **Harness use case (Layer 1H):** `statsmodels.lowess` for SMOOTHING
  validation per Pattern A.1 same-library self-parity (`p3_loess.py`
  lines 44-52 `_smooth` helper invoking `lowess(y, x, frac=0.3,
  return_sorted=True)`; both `run_tsl` lines 54-56 + `run_reference`
  lines 58-62 call SAME `_smooth` helper; lowess output validated
  bit-exact against itself per Pattern A.1)
- **Engine use case (Layer 1E):** `statsmodels.lowess` for
  INTERPOLATION OF MISSING VALUES per module docstring lines 1-7
  verbatim: *"LOESS/LOWESS Interpolation for Time Series Lab. Uses
  locally weighted scatterplot smoothing (LOWESS) from statsmodels
  to interpolate missing values in a time series. The smoother is
  fit on observed values and used to predict at missing positions."*

**Structural distinction from S26 denton_chowlin §4.7.A variant:**
S26 denton_chowlin §4.7.A variant = "HARNESS REIMPLEMENTS ENGINE
MATH" (numpy KKT vs engine `_denton_proportional`; SAME use case,
DIFFERENT code paths; mathematically equivalent at machine
precision). S27 loess_interpolation §4.7.A variant = "HARNESS-AND-
ENGINE-USE-SAME-LIBRARY-FUNCTION-FOR-DIFFERENT-PURPOSES" (SAME
library function, DIFFERENT use cases). Empirically distinct §4.7.A
structural mechanism variants per S27 (α) reframe; Workstream B
amendment cycle candidate G refinement scope EXPANDED at S27:
§4.7.A codification refinement at next Workstream B cycle disposes
(a) S25 §4.7.A 3-mechanism list completeness vs (b) §4.7.A 4+
mechanism list inclusion of S27 use-case-divergence variant.

**§4.7.B engine-extends-beyond-harness pattern PARTIAL observation
(Layer 1E use-case extension + Layer 2 orchestration extension):**
Engine extends statsmodels.lowess use case from SMOOTHING (harness
audit scope) to INTERPOLATION (engine primary purpose); engine
adds:
- Fit LOWESS on observed values + predict at missing positions
  (lines 159-160 + missing-value error handling lines 97-115)
- Cross-validation auto-frac selection via LOO-CV (`_auto_select_frac`
  lines 32-74; 43 LOC ML-style cross-validation implementation)
- Preset-based frac + iteration configuration (`_PRESET_CONFIG`
  lines 25-29: Fast/Balanced/Thorough variants with frac + it)
- CAI Phase 2 Session 19 fix F-MD-LOESS-FRAC allowlist gate
  (lines 142-153)
- NaN handling + missing-fraction warning + interpolation result
  formatting

**A10 Sub-class disposition (Sub-class 2e candidate scope refined
per S27 (α) reframe):** loess_interpolation does NOT count toward
Sub-class 2e n=2 second-observation tightening (per S26 (αa-S26)
candidate "harness-reimplements-engine-math + engine-method-
extension" scope). Sub-class 2e n=1 baseline UNCHANGED at
denton_chowlin S26 first-instance only. loess_interpolation S27 =
DIFFERENT §4.7.A variant (use-case divergence; NOT reimplementation);
operationally distinct from Sub-class 2e Sub-class 2c codified
instances.

**Absorption #4 Sub-class taxonomy disposition options per S27 (α)
reframe ratification:**
- (i) Sub-class 2e codification at denton_chowlin n=1 first-instance
  baseline ONLY; Sub-class 2e n=2 tightening deferred to next
  reimplementation observation
- (ii) NEW Sub-class 2f candidate codification at loess_interpolation
  n=1 first-instance baseline ("harness-validates-different-use-case-
  of-same-library-function" variant); separate sub-class from
  Sub-class 2e reimplementation variant
- (iii) Generalize Sub-class 2e definitional scope to "harness-uses-
  different-code-path-from-engine" (covering BOTH reimplementation
  AND use-case divergence variants); denton_chowlin + loess_interpolation
  = n=2 Sub-class 2e generalized baseline

S27 entry surfaces empirical structure; absorption #4 dispositions
taxonomy with full empirical surface across denton_chowlin +
loess_interpolation + accumulated candidates.

**Reference:** direct `statsmodels.nonparametric.smoothers_lowess.lowess`
(statsmodels 0.14.6)
**Verdict:** PASS Pattern A.1 same-library bit-exact
**Audit:** `tools/reference_parity/reports/p3_loess_audit.md`
**Audit date:** 2026-04-29
**smoothed_y abs diff:** 0.0 (EXACT, 200 points)
**Tolerance class:** closed_form
**Fixture:** noisy sinusoid x∈[0,10], y=sin(x)+N(0,0.09) (T=200,
seed=42); frac=0.3 pinned

**Source files (TWO-LAYER + HARNESS-AND-ENGINE-USE-SAME-LIBRARY-FOR-
DIFFERENT-PURPOSES per S27 (α) reframe framing):**
`tools/reference_parity/harness/checks/p3_loess.py` lines 44-52
(harness `_smooth` helper invokes `statsmodels.nonparametric.smoothers_lowess.lowess(y,
x, frac=0.3, return_sorted=True)` directly for SMOOTHING use case;
shared helper for both `run_tsl` + `run_reference` per Pattern A.1
same-library self-parity validation)
+ `tools/reference_parity/harness/checks/p3_loess.py` lines 54-56
(harness TSL arm calls `self._smooth(fixture)`; does NOT invoke
`loess_interpolation.py::run()` engine entry point; §4.7.A harness-
bypasses-engine pattern manifestation via use-case-divergence
variant)
+ `tools/reference_parity/harness/checks/p3_loess.py` lines 58-62
(harness reference arm calls SAME `self._smooth(fixture)` + extracts
statsmodels version; same-library self-parity per Pattern A.1)
+ `engine/techniques/loess_interpolation.py` lines 1-7 (module
docstring: "LOESS/LOWESS Interpolation... interpolate missing
values in a time series. The smoother is fit on observed values
and used to predict at missing positions." — INTERPOLATION use
case distinct from harness SMOOTHING audit scope)
+ `engine/techniques/loess_interpolation.py` line 37 + line 91
(statsmodels.lowess import: SAME library function as harness; used
for DIFFERENT purpose)
+ `engine/techniques/loess_interpolation.py` lines 25-29
(`_PRESET_CONFIG`: Fast/Balanced/Thorough preset variants with frac
+ iteration count configuration)
+ `engine/techniques/loess_interpolation.py` lines 32-74
(`_auto_select_frac`: 43 LOC LOO-CV implementation for optimal
LOWESS fraction selection via leave-one-out cross-validation;
n_obs >= 10 threshold; default frac=0.3 for small samples; grid
search over [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]; NOT validated
by audit)
+ `engine/techniques/loess_interpolation.py` lines 77-314 (Layer 2
standalone orchestration: `run()` main entry with input validation
+ missing-value handling + preset config + frac selection via CV
or explicit param + CAI Phase 2 Session 19 fix F-MD-LOESS-FRAC
allowlist gate lines 142-153 + LOWESS fitting + interpolation at
missing positions + result formatting + significance disclosure +
interpretation + audit_fields construction)
+ `tools/reference_parity/reports/p3_loess_audit.md`

**Validation claim scope (TIER III + §4.7.A harness-bypasses-engine
pattern with NEW use-case-divergence variant per S27 (α) reframe;
Layer 1H smoothing / Layer 1E interpolation / Layer 2 orchestration
framework operative):** TSL loess_interpolation output relies on
two layered computations within standalone-technique role (Layer
1E statsmodels.lowess INTERPOLATION use case + Layer 2 engine
orchestration). p3_loess audit validates Layer 1H statsmodels.lowess
SMOOTHING use case via same-library self-parity at single seeded
fixture (noisy sinusoid T=200 seed=42 frac=0.3 pinned); smoothed_y
metric measures `_smooth` helper output vs itself agreement
(abs diff 0.0 EXACT PASS), NOT Layer 1E engine interpolation use
case correctness, NOT engine `_auto_select_frac` CV correctness,
NOT engine Layer 2 standalone orchestration correctness.

- **Layer 1H statsmodels.lowess SMOOTHING use case (HARNESS audit
  scope; validated Pattern A.1 same-library bit-exact):** PASS
  Pattern A.1 at exact precision (abs diff 0.0; 200 points)
  against itself via `_smooth` helper self-parity; **Tier III
  scope per scope_reframing §2 line 154 verbatim:** "Verifies
  wrapper-integrity claim only (preprocessing, parameter resolution,
  audit-field rounding); does NOT validate against independent
  implementation." Tier III strength bounded — same-library
  determinism + identical inputs verification ONLY; NOT cross-
  package agreement; NOT engine implementation validation.
- **Layer 1E statsmodels.lowess INTERPOLATION use case (ENGINE
  primary purpose; NOT validated by audit):** engine `run()`
  (lines 77-314) fits LOWESS on observed values (lines 159-160)
  and predicts at missing positions via interpolation; harness
  audit Pattern A.1 self-parity validates smoothing use case ONLY;
  engine interpolation use case correctness NOT directly audit-
  validated. **§4.7.A new structural mechanism variant per S27:**
  "harness-validates-different-use-case-of-same-library-function"
  — both harness AND engine import SAME `statsmodels.lowess` BUT
  use for DIFFERENT purposes.
- **Layer 1E engine CV auto-frac selection (NOT VALIDATED):** engine
  `_auto_select_frac` (lines 32-74) LOO-CV grid search over
  [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5] for optimal LOWESS fraction;
  Thorough preset default per `_PRESET_CONFIG` line 28; NOT
  exercised by audit (audit pins frac=0.3); engine extends Layer 1E
  to ML-style cross-validation parameter selection.
- **Layer 2 engine orchestration (validation scope conditional):**
  - Input validation + missing-value handling (lines 88-122):
    missing-value error path + n_valid >= 5 threshold + missing-
    fraction > 0.5 warning
  - Preset config dispatch (lines 124-138): `_PRESET_CONFIG` Fast/
    Balanced/Thorough preset selection
  - Frac selection logic (lines 131-153): explicit frac param OR
    auto-select via CV + CAI Phase 2 Session 19 fix F-MD-LOESS-FRAC
    allowlist gate (frac ∈ (0, 1]) + error_fixes guidance
  - Iteration count selection (line 155): explicit it param OR
    preset default
  - LOWESS fitting + interpolation construction (lines 157+):
    fit on observed values + predict at missing positions
  - Result formatting + significance disclosure + interpretation +
    audit_fields construction

#### Disclosure pattern (i) — Research note footnote (Tier III + §4.7.A use-case-divergence variant)

> This analysis uses TSL technique `loess_interpolation`, validated
> per Phase 3 same-library self-parity (Pattern A.1) against direct
> `statsmodels.nonparametric.smoothers_lowess.lowess` (statsmodels
> 0.14.6) per audit dated 2026-04-29 (smoothed_y abs diff 0.0).
> **Tier III scope caveat:** validation verifies wrapper-integrity
> claim only (same-library self-parity for SMOOTHING use case);
> does NOT validate against independent implementation. Engine
> module uses SAME statsmodels.lowess function for INTERPOLATION
> use case (engine primary purpose: fit on observed + predict at
> missing positions); §4.7.A harness-bypasses-engine pattern via
> use-case-divergence variant. Engine extends Layer 1E to CV auto-
> frac selection + preset config; NOT audit-validated. Pre-Path α
> expert review status.

#### Disclosure pattern (ii) — Technical appendix (Tier III + §4.7.A use-case-divergence variant + interpolation use case extension)

> Methodology: TSL technique `loess_interpolation` validated per
> Phase 3 reference parity infrastructure under Tier III + §4.7.A
> harness-bypasses-engine pattern framing with NEW use-case-divergence
> structural mechanism variant per S27 codification. **Reference:**
> direct `statsmodels.nonparametric.smoothers_lowess.lowess`
> (statsmodels 0.14.6); SAME library function as engine. **Verdict:**
> PASS Pattern A.1 same-library bit-exact; smoothed_y abs diff 0.0
> (EXACT, 200 points). **Audit date:** 2026-04-29. **Fixture:** noisy
> sinusoid x∈[0,10], y=sin(x)+N(0,0.09) (T=200, seed=42); frac=0.3
> pinned. **Tier III scope per scope_reframing §2 line 154 verbatim:
> "Verifies wrapper-integrity claim only; does NOT validate against
> independent implementation."** **§4.7.A use-case-divergence
> variant caveat:** harness validates statsmodels.lowess for
> SMOOTHING use case (same-library self-parity); engine uses SAME
> statsmodels.lowess for INTERPOLATION use case (engine primary
> purpose per module docstring lines 1-7); engine extends Layer 1E
> to interpolation + CV auto-frac selection + preset config NOT
> exercised by audit. Layer 2 (engine orchestration: missing-value
> handling + preset config + F-MD-LOESS-FRAC allowlist gate +
> interpretation) NOT parity-validated. Q3b extension pending. Pre-
> Path α expert review status; expert review pending [target date].

#### Disclosure pattern (iii) — Risk model documentation (Tier III + §4.7.A use-case-divergence + audit citation)

> `loess_interpolation` validation: TSL Tier III (same-library self-
> parity per Pattern A.1) under §4.7.A harness-bypasses-engine
> pattern framing with NEW use-case-divergence structural mechanism
> variant per S27 codification. **Reference:** direct
> `statsmodels.nonparametric.smoothers_lowess.lowess` (statsmodels
> 0.14.6); SAME library function imported by both harness + engine.
> **Audit:** `tools/reference_parity/reports/p3_loess_audit.md`
> dated 2026-04-29. **Verdict:** PASS Pattern A.1 same-library bit-
> exact; smoothed_y abs diff 0.0 (EXACT, 200 points). **Fixture:**
> noisy sinusoid T=200 seed=42 frac=0.3 pinned; single-seeded
> fixture; parameter-sensitivity coverage NOT established; Q3b
> extension scope. **Tier III risk attribution scope:** per
> scope_reframing §2 line 154 verbatim, "Verifies wrapper-integrity
> claim only; does NOT validate against independent implementation."
> Cross-package agreement NOT established; only same-library self-
> parity. Validation evidence stronger for wrapper-preprocessing-
> correctness claim than for math-implementation-correctness claim
> (latter requires independent reference). **§4.7.A use-case-
> divergence variant risk attribution:** **(a) Layer 1H
> statsmodels.lowess SMOOTHING use case (harness audit scope):**
> same-library self-parity at frac=0.3 pinned; Tier III bounded
> validation; **(b) Layer 1E statsmodels.lowess INTERPOLATION use
> case (engine primary purpose; NOT audit-validated):** engine fits
> LOWESS on observed + predicts at missing positions; attribution
> from `loess_interpolation` ribbon invocation conditional on
> engine interpolation construction correctness + CV auto-frac
> selection correctness + Layer 2 orchestration correctness;
> **(c) Layer 1E CV auto-frac selection (NOT audit-validated):**
> `_auto_select_frac` LOO-CV grid search (lines 32-74); Thorough
> preset default; correctness conditional on expert review; **(d)
> Layer 2 standalone orchestration (CAI Phase 2 Session 19 F-MD-
> LOESS-FRAC allowlist gating + NaN handling + missing-value
> handling + preset config + interpolation construction):**
> validation scope per `engine/techniques/loess_interpolation.py`
> lines 77-314. **Asymmetric retraction surface across use cases:**
> SMOOTHING use case (engine standalone smoothing invocation IF
> supported) relies on audit-validated Layer 1H Pattern A.1;
> INTERPOLATION use case (engine primary purpose; ribbon-default)
> relies on UNVALIDATED Layer 1E interpolation + CV auto-frac. Pre-
> Path α expert review status.

#### Disclosure pattern (iv) — Internal use disclosure (Tier III + §4.7.A use-case-divergence variant)

> `loess_interpolation` same-library self-parity validated against
> statsmodels.lowess (Pattern A.1; SMOOTHING use case ONLY per
> harness audit scope); engine INTERPOLATION use case (primary
> purpose) + CV auto-frac + Layer 2 orchestration pending expert
> review. Engine ribbon-default = INTERPOLATION (UNVALIDATED). Tier
> III bounded validation per scope_reframing §2 line 154; does NOT
> validate against independent implementation. Pre-Path α.

**Validation provenance audit checklist (Workstream B §1 four-question
audit; applied per Q1 entry close):**

- **Q-A (extracted/cited evidence vs inferred reasoning):**
  Extracted/cited evidence. Reference (direct statsmodels.lowess
  0.14.6) per audit Reference field (verbatim). Audit date
  (2026-04-29) per audit Date field (verbatim). Verdict + Pattern
  (PASS Pattern A.1 same-library bit-exact) per audit Verdict line
  (verbatim). Tolerance class (closed_form) per audit Tolerance
  class line (verbatim). Numeric metric (smoothed_y abs diff 0.0
  EXACT 200 points) per audit Result table (verbatim). Fixture
  (noisy sinusoid T=200 seed=42 frac=0.3 pinned) per audit Fixture
  section (verbatim). **Tier III characterization per scope_reframing
  §2 lines 151-157 (Pattern A.1 same-library self-parity; 18
  wrappers locked at scale; "Verifies wrapper-integrity claim only;
  does NOT validate against independent implementation").** §4.7.A
  harness-bypasses-engine pattern with NEW use-case-divergence
  structural mechanism variant per S27 Step 0 (d) engine module
  full re-Read empirical investigation (engine docstring lines 1-7
  INTERPOLATION primary purpose + engine + harness BOTH import
  statsmodels.lowess + harness lines 44-52 _smooth helper SMOOTHING
  use case + (α) reframe at S27 STOP 2 disposition). Layer 1H /
  Layer 1E / Layer 2 framework operative per S26 STOP 1.5 second
  close ratification carried forward to S27. **§4.7.A pattern
  FOURTH observation (n=4) per S25 §4.7.A codification + post-S26
  triad reinforcement** (S14a + S18 + S26 + S27 = n=4); NEW
  structural mechanism variant flagged per S27 (α) reframe:
  "harness-validates-different-use-case-of-same-library-function"
  distinct from S25 §4.7.A 3-mechanism codified list (lines 960-
  967); Workstream B amendment cycle candidate G refinement scope
  EXPANDED at S27 to dispose §4.7.A 3-mechanism vs 4+ mechanism
  list at next cycle. **A9 Class A 9th-instance candidate** (Chat
  trigger CHAT RATIFICATION #5 schema-misattribution: labeling
  loess as "second harness-reimplements-engine-math observation"
  when empirical structure is "harness-validates-different-use-
  case-of-same-library-function"; caught at Step 0 (d) engine
  module full re-Read per A9 Class A mitigation discipline
  operating proactively; banked for absorption #4 codification
  alongside A9 Class A n=7 + n=8 candidates). **A9 Class B counter
  unchanged post-S27 n=4 ACTIVE**: framing class working hypothesis
  CONFIRMED at Step 0 per A9 Class B revised default discipline
  operating proactively per S22+S23+S25+S26+S27 sustained pattern.
  **Maturation observation FOURTH SUSTAINED OBSERVATION REACHED at
  S27** + **SIX proactive-prevention timing point empirical surface**
  per Chat ratification ITEM 6: (i) pre-trigger session re-entry
  (S23-pre + S26-pre); (ii) trigger-execution Step 0 (S25); (iii)
  STOP-cycle revision-trigger completeness (S25 STOP 1.5); (iv)
  numerical-claim-baseline pre-trigger (S26-pre); (v) framework-
  consistency-at-STOP-1.5-close (S26 STOP 1.5 second close); (vi)
  trigger-working-hypothesis-labeling-verification at Step 0 (d)
  engine module full re-Read (S27 NEW catch). Promotion candidate
  (§19.4 §4.5 NEW sub-section OR A11 NEW amendment) READY for
  absorption #4 codification disposition per Chat ratification ITEM
  7 AFFIRMED. Verify-state-at-first-consumption sub-discipline 22nd
  instance application.

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at eleventh-technique selection per Mark 3
  efficient-ratification + (α) unprompted case-against discipline
  operative per Workstream B §1.4 codification + S20+S25+S26
  reinforcement. **Q-B pattern persists at n=12 across S12 + S13 +
  S14b + S14c + S15 + S17 + S18 + S21 + S22 + S23 + S26 + S27;
  §1.4 codified observation refinement at empirical pattern
  accumulation** (n=7 at §1.4 S20 codification → n=10 at S25
  refinement → n=11 at S26 → n=12 at S27 reinforcement; Workstream
  B amendment cycle candidate A continues at next cycle). Substantive
  Chat engagement at structural-decision points empirically observed
  (Step 0 STOP 2 (α) reframe disposition + Items 1-7 ratifications
  + Sub-class 2e candidate scope refinement + §4.7.A NEW mechanism
  variant codification banking + A9 Class A 9th-instance candidate
  banking + maturation observation absorption #4 codification
  affirmation).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1H statsmodels.lowess SMOOTHING use case (audit-
  validated Pattern A.1 same-library bit-exact)** per EXACT PASS
  verdict (abs diff 0.0 200 points). **CRITICAL Q-C framing per
  Tier III scope bound:** validation evidence verifies wrapper-
  integrity claim only (same-library determinism + identical inputs)
  per scope_reframing §2 line 154 verbatim; does NOT validate
  against independent implementation; cross-package agreement NOT
  established. **Conditional for Layer 1E statsmodels.lowess
  INTERPOLATION use case (engine primary purpose)** — §4.7.A use-
  case-divergence variant: engine fits LOWESS on observed values
  and predicts at missing positions; harness audit Pattern A.1 self-
  parity validates smoothing use case ONLY; engine interpolation
  use case correctness NOT directly audit-validated; requires
  expert review confirming engine interpolation construction
  correctness OR engine cross-check against independent imputation
  reference. **Conditional for Layer 1E CV auto-frac selection** —
  `_auto_select_frac` LOO-CV grid search (lines 32-74); Thorough
  preset default; correctness conditional on expert review of LOO-CV
  implementation + frac grid appropriateness. **Conditional for
  Layer 2 engine orchestration** — input validation + missing-value
  handling + preset config + F-MD-LOESS-FRAC allowlist gate +
  interpolation construction + interpretation; requires expert
  review of engine implementation OR engine-output cross-check.
  **Critical Q-C framing per ribbon-default use-case context:**
  published-research user invoking `loess_interpolation` from
  ribbon receives INTERPOLATION output (engine primary purpose);
  smoothing output is NOT engine ribbon-default; defensibility to
  all three audiences (published audience + Morgan Stanley
  compliance + Path α expert reviewer) UNDER Tier III scope bound
  + §4.7.A use-case-divergence variant + Layer 1E interpolation
  expert review acknowledgment.

- **Q-D (retraction surface if expert review later finds inadequacy):**
  MEDIUM-HIGH per Tier III scope bound + §4.7.A use-case-divergence
  variant. loess_interpolation is canonical LOWESS-based imputation
  methodology (widely used for missing-value interpolation in time
  series). **Layer-specific + §4.7.A use-case-divergence retraction
  surface (per S27 (α) reframe; Layer 1H smoothing / Layer 1E
  interpolation / Layer 2 orchestration framework):**
  - Layer 1H statsmodels.lowess SMOOTHING use case (harness audit
    scope): LOW; EXACT PASS at same-library self-parity; expert
    review surfacing upstream error would affect harness audit
    scope specifically. **Tier III scope bound caveat:** validation
    evidence does NOT extend to math-implementation-correctness
    claim against independent reference; cross-package agreement
    NOT established.
  - **Layer 1E statsmodels.lowess INTERPOLATION use case (engine
    primary purpose; §4.7.A use-case-divergence variant): MEDIUM-
    HIGH** — engine `run()` fits LOWESS on observed + predicts at
    missing positions; NOT audit-validated; ribbon-default
    invocation goes through Layer 1E interpolation; expert review
    surfacing material error in engine interpolation construction
    would invalidate `loess_interpolation` ribbon publication
    output specifically; **asymmetric retraction surface:** Layer
    1H smoothing use case validated via same-library self-parity
    (Tier III bounded); Layer 1E interpolation use case UNVALIDATED
    (engine primary purpose).
  - Layer 1E CV auto-frac selection: MEDIUM — `_auto_select_frac`
    LOO-CV grid search NOT audit-validated; Thorough preset default;
    expert review of LOO-CV implementation correctness +
    appropriateness of frac grid for non-test data conditional.
  - Layer 2 engine orchestration (input validation + missing-value
    handling + preset config + F-MD-LOESS-FRAC allowlist gate +
    interpolation construction + interpretation): MEDIUM analogous
    to S14b/S15/S21/S22/S26 Layer 2 (engine implementation
    equivalence) + loess-specific CAI Phase 2 Session 19 allowlist
    + interpolation result formatting.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; eleventh technique to enter status per
S27 ratification; **SECOND Block 8 Missing Data entry** (continues
Block 8 completion arc; S28 third-entry triggers Block 8 fully Q1-
amended milestone = THIRD catalog block fully Q1-amended after
Block 1 Causality at S18 + Block 12 Stationarity Tests at S23);
**FIRST Tier III §2.5 precedent** (institutional pattern for Q1
work program Tier III techniques at scope_reframing §2 18-wrapper
"locked at scale" enumeration; bounds expectations per Tier III
scope "Verifies wrapper-integrity claim only" caveat per S6 §2 line
154 verbatim); **FOURTH §4.7.A pattern observation (n=4) WITH NEW
STRUCTURAL MECHANISM VARIANT per S27 (α) reframe** ("harness-
validates-different-use-case-of-same-library-function" distinct
from S25 §4.7.A 3-mechanism list lines 960-967; Workstream B
amendment cycle candidate G refinement scope EXPANDED at S27).
**S27 two-layer + §4.7.A use-case-divergence + Tier III scope bound
framing; Layer 1H/Layer 1E/Layer 2 framework operative per S26
STOP 1.5 second close ratification carried forward: Layer 1H
statsmodels.lowess SMOOTHING (harness audit scope; same-library
self-parity validated EXACT PASS); Layer 1E statsmodels.lowess
INTERPOLATION (engine primary purpose; NOT audit-validated;
ribbon-default goes through Layer 1E); Layer 1E CV auto-frac
selection NOT audit-validated; Layer 2 engine orchestration NOT
parity-validated; compound retraction surface across use cases
requires expert review.** **A10 Sub-class disposition (Sub-class 2e
candidate scope refined per S27 (α) reframe):** loess_interpolation
does NOT count toward Sub-class 2e n=2 second-observation tightening
per (αb-S27) deferred codification at absorption #4; Sub-class 2e
n=1 baseline UNCHANGED at denton_chowlin S26 first-instance only;
loess_interpolation S27 = DIFFERENT §4.7.A variant (use-case
divergence; NOT reimplementation); absorption #4 disposes Sub-class
taxonomy with full empirical surface (Sub-class 2e n=1 + Sub-class
2f candidate at loess n=1 OR generalized Sub-class 2e at n=2 OR
deferred). **A9 Class B counter post-S27: n=4 ACTIVE** (unchanged;
framing class working hypothesis CONFIRMED at Step 0 per A9 Class B
revised default discipline operating proactively per S22+S23+S25+S26+S27
sustained pattern). **A9 Class A counter post-S27: n=6 ACTIVE +
candidates n=7 + n=8 + n=9 pending absorption #4 codification** (n=7
candidate per S23-pre Doc 2 tier-enumeration omission proactive-
catch variant; n=8 candidate per S26-pre catalog-count-baseline
misattribution catch; n=9 candidate per S27 trigger drafting
reimplementation-vs-use-case-divergence schema-misattribution catch
NEW at S27). **A9 Class A + Class B discipline maturation FOURTH
SUSTAINED OBSERVATION REACHED at S27** per A3 second-observation
tightening precedent threshold satisfied at n=4 observations (S23
+ S25 + S26 + S27 sustained proactive-prevention operation across
SIX-timing-point empirical surface). **Promotion candidate (§19.4
§4.5 NEW sub-section OR A11 NEW amendment) ROBUSTNESS REINFORCED
for absorption #4 codification disposition** per Chat ratification
ITEM 7 AFFIRMED at S27 STOP 2 (maturation observation WILL codify
at absorption #4; forward instrumentation banking through S27-S28-
absorption-#4 sequence operates as institutional preparation for
codification surface, NOT self-perpetuating accretion). **Block 8
second-entry status + Block 8 completion arc forward instrumentation:
S26 denton_chowlin + S27 loess_interpolation (this entry) → S28
kalman_imputation (anticipated; per default ordering OR Chat S28
disposition) → Block 8 fully Q1-amended milestone at S28 close;
third catalog block completion triggers per-block continuation
pattern n=3 codification at §19.4 §4 forward instrumentation note
6 refinement at next absorption cycle (absorption #4)**.

### kalman_imputation (Phase 7+ S28; TWELFTH §2.5 entry; THIRD-AND-FINAL Block 8 Missing Data entry; **BLOCK 8 FULLY Q1-AMENDED milestone** = THIRD catalog block fully Q1-amended after Block 1 Causality at S18 + Block 12 Stationarity Tests at S23; FIRST Tier II.mle-band + Pattern A conditional-on-MLE-alignment overlay §2.5 precedent; FIRST Sub-class 2a standalone-only variant Q1 §2.5 entry; Sub-class 2a (αa) variant tagging n=3 baseline UPGRADE to codification-stable per A3 second-observation tightening precedent threshold; FIRST audit-content-distribution variant disclosure per S28 dedicated-audit-absent structural anomaly per CHAT RATIFICATION #6 (α) ratification)

**Tier (per Phase 7+ S6 §2 + S9 amendments tier taxonomy):** **Tier
II.mle-band primary + Pattern A conditional-on-MLE-alignment overlay**
per S28 (α) Chat disposition (analogous to S23 pp_test "Tier II.bit-
exact-loose + Tier V Pattern J B.2 overlay" primary+overlay framing
structure). **Tier II.mle-band primary characterization per
verdict_class "mle_fit" semantic** (harness wrapper code line 56:
`verdict_class = "mle_fit"`); cross-package PASS at MLE-fit band
tolerance per scope_reframing §2 lines 134-137 definitional scope
("operational R reference comparison; NOT bit-exact at machine
precision"). **Pattern A conditional-on-MLE-alignment overlay
characterization** per p3_batch_5_summary.md lines 21-23 verbatim
("`p3_local_level` and `p3_kalman_imputation` join the Pattern A
regime when KFAS + statsmodels agree on the MLE optimum. Pattern A
now 11 wrappers.") + phase3_cross_batch_findings.md line 23 verbatim
("`p3_local_level`, `p3_kalman_imputation` (state-space closed-form
when MLE optima align)"). **Empirical bit-exact-within-MLE-alignment-
window behavior alongside Tier II.mle-band primary characterization;
honest validation strength surface per primary+overlay structure.**
`p3_kalman_imputation` NOT in scope_reframing §2 Tier II.mle-band
13-wrapper explicit enumeration (lines 138-141: arima/sarima/
arimax_sarimax/ets/theta/intervention_analysis/dfm/hmm/markov_switching/
sgarch/gjr_garch/egarch/tar_setar); added per S28 (α) disposition
under post-S6 inference grounded at empirical p3_batch_5_summary
Pattern A characterization + verdict_class "mle_fit" + phase3_cross_batch_findings
Pattern A conditional cross-batch finding (analogous to S23 p3_pp
inference precedent at Tier II.bit-exact addition).

**Framing precedent note (1:1 catalog↔wrapper; CLEAN TWO-LAYER +
ENGINE-USES-SAME-FUNCTION alignment per CHAT RATIFICATION #4
CONFIRMED at Step 0; **NO §4.7.A pattern** distinct from S26 +
S27 §4.7.A variant observations; Sub-class 2a (αa) variant tagging
EXTENDED to standalone-only variant per (αa-S28) ratification):**
kalman_imputation is 1:1 catalog↔wrapper mapping per audit-content-
distribution Wrapper field (`engine/techniques/kalman_imputation.py`
sole engine module).

**Clean engine-uses-same-function alignment empirically confirmed:**
`p3_kalman_imputation.py` line 82 verbatim: `wrapper_resp = ki_mod.run(ctx,
lambda *a, **kw: None)` — harness INVOKES engine module `run()`
directly; engine + harness both use `statsmodels.tsa.statespace.structural.UnobservedComponents`
Kalman smoother via engine module direct invocation; R reference via
KFAS smoother (different package; same Kalman smoother math; Pattern
A conditional alignment regime). **NO §4.7.A harness-bypasses-engine
pattern manifestation** — distinct from S26 denton_chowlin reimplementation
variant + S27 loess_interpolation use-case-divergence variant; S28
kalman_imputation breaks §4.7.A pattern recurrence at Block 8 final
entry; §4.7.A pattern post-S28 n=4 observations across §2.5 entries
(S14a + S18 + S26 + S27); kalman_imputation does NOT add §4.7.A
fifth observation.

**Sub-class 2a (αa) variant tagging EXTENDED per (αa-S28) Chat
ratification:** Sub-class 2a (αa) general two-layer class with
variant tagging UPGRADES from n=2 codified (S22 dual-role + S23
triple-role per S25 codification) to **n=3 baseline tightening at
S28** (S22 + S23 + S28) per A3 second-observation tightening
precedent threshold satisfied at n=3 observations. Sub-class 2a
(αa) variant tagging UPGRADES to codification-stable status at n=3:
- **Dual-role variant (S22 kpss_test):** operational-coupling-count
  = 1 (helper-export to adf_test triage 3b parallel-test invocation)
- **Triple-role variant (S23 pp_test):** operational-coupling-count
  = 2 (helper-export to adf_test triage 3b parallel + 3d CONFLICTING
  tie-breaker)
- **Standalone-only variant (S28 kalman_imputation; NEW third
  variant per (αa-S28) ratification):** operational-coupling-count
  = 0 (NO helper-export role; engine `run()` is sole top-level
  function; standalone-technique-only invocation per ribbon
  kalman_imputation direct call)

Variant tagging mechanism generalized to operational-coupling-count
∈ {0, 1, 2} with per-variant disclosure framing within Sub-class
2a (αa) "general two-layer class" semantic per S25 codification.

**Block 8 Missing Data fully Q1-amended milestone status (THIRD
CATALOG BLOCK COMPLETION):** S26 denton_chowlin + S27 loess_interpolation
+ S28 kalman_imputation = 3-entry Block 8 cumulative completion.
THIRD catalog block fully Q1-amended after Block 1 Causality (6
entries S12-S18) + Block 12 Stationarity Tests (3 entries S21-S23).
Per-block continuation pattern at n=3 catalog block observations
satisfies A3 second-observation tightening precedent threshold;
codification candidate at §19.4 §4 forward instrumentation note 6
refinement at absorption #4.

**Reference:** R `KFAS` smoother (per p3_batch_5_summary.md line 17
+ harness `p3_kalman_imputation.py` reference arm via RBridge)
**Verdict:** PASS (Pattern A regime when KFAS + statsmodels agree
on MLE optimum; per audit-content-distribution disclosure per
CHAT RATIFICATION #6 (α) ratification)
**Audit content distribution (FIRST-INSTANCE STRUCTURAL ANOMALY VARIANT per S28 (α) ratification):**
- `tools/reference_parity/reports/p3_batch_5_summary.md` line 17
  (PASS verdict: "Smoothed-state imputation at NA positions")
- `tools/reference_parity/reports/p3_batch_5_summary.md` lines 21-23
  (Pattern A characterization: "`p3_local_level` and `p3_kalman_imputation`
  join the Pattern A regime when KFAS + statsmodels agree on the
  MLE optimum. Pattern A now 11 wrappers.")
- `tools/reference_parity/reports/phase3_cross_batch_findings.md`
  line 23 ("`p3_local_level`, `p3_kalman_imputation` (state-space
  closed-form when MLE optima align)")
- **NO dedicated `p3_kalman_imputation_audit.md` file** (audit-
  content-distribution structural anomaly first-instance variant
  per S28; distinct from S23 pp_test variant where audit file
  PRESENT but scope_reframing §2 enumeration ABSENT)

**Audit date:** 2026-04-29 (per p3_batch_5_summary.md header)
**Numeric metric:** specific abs/rel diff NOT in surfaced audit
artifacts (audit-content-distribution structural anomaly variant
implication: dedicated audit file absent precludes specific abs
diff numeric extraction; PASS verdict + Pattern A conditional
characterization is load-bearing audit content)
**Tolerance class:** mle_fit (per harness wrapper code line 56
`verdict_class = "mle_fit"`)
**Fixture:** local-level state-space DGP via `_kalman_helpers.generate_local_level_dgp`
(seed=42; n=200 per harness `DGP_N`); 15% missing values injected
at random positions (per harness `MISSING_FRAC=0.15` + `_inject_missing`
helper lines 34-46)

**Source files (CLEAN TWO-LAYER + ENGINE-USES-SAME-FUNCTION +
AUDIT-CONTENT-DISTRIBUTION variant per S28 (α) ratification):**
`tools/reference_parity/harness/checks/p3_kalman_imputation.py`
lines 79-130 (harness TSL arm invokes engine module `kalman_imputation.run(ctx)`
directly at line 82 via `wrapper_resp = ki_mod.run(...)`; extracts
imputed values from wrapper response tables; CLEAN engine-uses-
same-function alignment; NO §4.7.A harness-bypasses-engine pattern
manifestation)
+ `tools/reference_parity/harness/checks/p3_kalman_imputation.py`
lines 132-178 (harness reference arm invokes R `KFAS` smoother via
RBridge: `SSModel(y ~ SSMtrend(degree=1, Q=list(matrix(NA))), H =
matrix(NA))` + `fitSSM(mod, inits, method="BFGS")` + `KFS(mod_fitted)`
+ extract smoothed state at missing positions)
+ `engine/techniques/kalman_imputation.py` lines 1-7 (module
docstring: "Kalman Smoother Imputation... uses a local linear trend
state-space model (UnobservedComponents from statsmodels) to impute
missing values via the Kalman smoother. The smoother provides
optimal estimates and uncertainty bounds for each imputed value.")
+ `engine/techniques/kalman_imputation.py` line 110 (Layer 1 math
import: `from statsmodels.tsa.statespace.structural import UnobservedComponents`
— SAME library function as harness invokes via engine.run())
+ `engine/techniques/kalman_imputation.py` lines 27-31 (`_PRESET_CONFIG`:
Fast=local level / Balanced=local linear trend / Thorough=local
linear trend; preset config dispatches model_type)
+ `engine/techniques/kalman_imputation.py` lines 34-330+ (Layer 2
engine orchestration: `run(ctx, progress_callback)` main entry; sole
top-level function; NO helper-export to other engine module;
standalone-technique-only invocation)
+ `engine/techniques/kalman_imputation.py` lines 89-106 (CAI Phase 2
Session 19 fix F-MD-KALMAN-MODELTYPE allowlist gate: model_type ∈
{"local level", "local linear trend"})
+ `engine/techniques/kalman_imputation.py` lines 115-131 (model fit
with fallback to local level if model fails to converge; convergence
fallback warning)
+ `engine/techniques/kalman_imputation.py` lines 135-160 (smoothed
state extraction + confidence interval construction via `scipy.stats.norm.ppf`
z-score)
+ `engine/techniques/kalman_imputation.py` lines 144-151 (internal
disclosure: model-misspecification CI band understatement risk;
"disclose this honestly rather than applying a pseudo-correction
that the state-space math does not support" — engine-level honest
disclosure built into code per institutional standard)
+ Audit content distribution (NO dedicated audit file):
  - `tools/reference_parity/reports/p3_batch_5_summary.md` lines 11-17
    (Coverage matrix row 5: PASS verdict; Smoothed-state imputation)
  - `tools/reference_parity/reports/p3_batch_5_summary.md` lines 21-23
    (Pattern A section: kalman_imputation Pattern A regime
    conditional-on-MLE-alignment)
  - `tools/reference_parity/reports/phase3_cross_batch_findings.md`
    line 23 (cross-batch Pattern A list: state-space closed-form
    when MLE optima align)

**Validation claim scope (TIER II.MLE-BAND PRIMARY + PATTERN A
CONDITIONAL-ON-MLE-ALIGNMENT OVERLAY + CLEAN TWO-LAYER + Sub-class
2a (αa) standalone-only variant per S28 (α) + (αa-S28) ratifications;
audit-content-distribution variant per (α) Q-A disclosure):** TSL
kalman_imputation output relies on two layered computations within
standalone-technique role (Layer 1 statsmodels.UnobservedComponents
Kalman smoother math + Layer 2 engine orchestration). p3_kalman_imputation
audit-content-distribution validates Pattern A regime conditional-
on-MLE-alignment between statsmodels + KFAS at single seeded fixture
(local-level DGP n=200 seed=42 + 15% missing positions); imputed
values metric measures statsmodels UnobservedComponents smoothed-
state imputation at NA positions vs R KFAS smoother imputation
agreement (PASS verdict per p3_batch_5_summary.md line 17; Pattern
A bit-exact-within-MLE-alignment-window when KFAS + statsmodels MLE
optima align). NOT engine standalone orchestration correctness, NOT
model-misspecification handling correctness, NOT confidence interval
construction correctness.

- **Layer 1 statsmodels.UnobservedComponents Kalman smoother math
  (validated Pattern A regime conditional-on-MLE-alignment):** PASS
  verdict per audit-content-distribution disclosure (p3_batch_5_summary.md
  line 17 + lines 21-23 Pattern A section). **Tier II.mle-band
  primary characterization per verdict_class "mle_fit" semantic** —
  MLE-fit band tolerance scope per scope_reframing §2 lines 134-137
  ("typically 1e-2 to 1e-1 abs"); operational R reference comparison
  via KFAS smoother. **Pattern A conditional-on-MLE-alignment
  overlay** — bit-exact within MLE alignment window when KFAS +
  statsmodels agree on MLE optimum; MLE-fit-band tolerance when
  optima diverge. Validation strength bounded by MLE alignment
  conditional; honest Q-D retraction surface characterization per
  primary+overlay structure.
- **Layer 2 engine orchestration (validation scope conditional):**
  - F-MD-KALMAN-MODELTYPE allowlist gate (lines 89-106; CAI Phase 2
    Session 19 fix): model_type ∈ {"local level", "local linear
    trend"} explicit gate
  - Preset config dispatch (lines 87-88, `_PRESET_CONFIG` lines
    27-31): Fast → local level; Balanced + Thorough → local linear
    trend
  - NaN handling + missing-value validation (lines 53-82): nan_mask
    construction + n_valid >= 5 threshold + missing-fraction > 0.5
    warning + n_missing == 0 error path
  - Model fit fallback (lines 115-131): UnobservedComponents.fit()
    with maxiter=500; fallback to local level if local linear trend
    fails to converge
  - Smoothed state extraction + confidence interval construction
    (lines 135-160): `smoothed_state[0]` level component + state
    covariance posterior_se + z-score CI via scipy.stats.norm.ppf
  - Model-misspecification disclosure built into engine code (lines
    144-151): CI band understatement risk disclosed honestly;
    institutional-standard built-in
  - Result formatting + significance disclosure + interpretation +
    audit_fields construction

#### Disclosure pattern (i) — Research note footnote (Tier II.mle-band primary + Pattern A overlay + audit-content-distribution variant)

> This analysis uses TSL technique `kalman_imputation`, cross-
> package PASS validated against R `KFAS` smoother per Phase 3
> audit dated 2026-04-29 (verdict PASS per audit-content-distribution
> in `p3_batch_5_summary.md` lines 17 + 21-23 + cross-batch findings
> Pattern A regime conditional-on-MLE-alignment per
> `phase3_cross_batch_findings.md` line 23). **Tier II.mle-band
> primary + Pattern A conditional-on-MLE-alignment overlay framing
> per S28 (α) disposition:** verdict_class "mle_fit" semantic;
> bit-exact within MLE alignment window when KFAS + statsmodels MLE
> optima align; MLE-fit-band tolerance when optima diverge. **Audit-
> content-distribution variant disclosure:** dedicated
> `p3_kalman_imputation_audit.md` absent; verdict + Pattern
> characterization distributed across batch summary + cross-batch
> findings. Engine extends to Layer 2 orchestration (allowlist
> gating + preset config + model fit fallback + CI construction);
> NOT audit-validated. Pre-Path α expert review status.

#### Disclosure pattern (ii) — Technical appendix (Tier II.mle-band primary + Pattern A overlay + audit-content-distribution variant + model-misspecification CI disclosure)

> Methodology: TSL technique `kalman_imputation` validated per
> Phase 3 reference parity infrastructure under Tier II.mle-band
> primary + Pattern A conditional-on-MLE-alignment overlay framing
> with audit-content-distribution variant disclosure per S28
> codification. **Reference:** R `KFAS` smoother (per
> p3_batch_5_summary.md Batch 5 R state-space wrappers). **Verdict:**
> PASS per audit-content-distribution: p3_batch_5_summary.md line
> 17 (PASS smoothed-state imputation at NA positions) + lines 21-23
> (Pattern A regime when MLE optima align; Pattern A now 11
> wrappers) + phase3_cross_batch_findings.md line 23 (state-space
> closed-form when MLE optima align). **Audit date:** 2026-04-29.
> **Fixture:** local-level DGP via `_kalman_helpers.generate_local_level_dgp`
> seed=42 + n=200 + 15% missing values injected at random positions
> (`_inject_missing` helper). **Tier II.mle-band primary
> characterization** per verdict_class "mle_fit" semantic;
> scope_reframing §2 lines 134-137: "cross-package PASSes against R
> references at MLE-fit band tolerances (typically 1e-2 to 1e-1
> abs); operational R reference comparison; NOT bit-exact at machine
> precision". **Pattern A conditional-on-MLE-alignment overlay:**
> bit-exact-within-MLE-alignment-window behavior when KFAS +
> statsmodels MLE optima agree; MLE-fit-band tolerance when optima
> diverge. **Audit-content-distribution variant caveat:** dedicated
> `p3_kalman_imputation_audit.md` ABSENT; verdict + Pattern
> characterization distributed across batch summary + cross-batch
> findings artifacts; specific abs/rel diff numerics NOT in surfaced
> audit content. **Engine-level honest disclosure (lines 144-151 of
> engine module):** "If the model is misspecified, the reported
> band understates true imputation uncertainty — disclose this
> honestly rather than applying a pseudo-correction that the state-
> space math does not support." Q3b extension pending. Pre-Path α
> expert review status; expert review pending [target date].

#### Disclosure pattern (iii) — Risk model documentation (Tier II.mle-band + Pattern A overlay + audit-content-distribution + Sub-class 2a standalone-only variant)

> `kalman_imputation` validation: TSL Tier II.mle-band primary +
> Pattern A conditional-on-MLE-alignment overlay framing per S28 (α)
> codification + audit-content-distribution variant disclosure per
> (α) Q-A ratification. **Reference:** R `KFAS` smoother.
> **Audit content distribution:** `tools/reference_parity/reports/p3_batch_5_summary.md`
> line 17 (PASS verdict) + lines 21-23 (Pattern A regime conditional
> on MLE alignment) + `tools/reference_parity/reports/phase3_cross_batch_findings.md`
> line 23 (state-space closed-form when MLE optima align); dedicated
> `p3_kalman_imputation_audit.md` ABSENT per audit-content-
> distribution structural anomaly variant. **Audit date:** 2026-04-29.
> **Verdict:** PASS Pattern A regime conditional-on-MLE-alignment
> (Tier II.mle-band primary + Pattern A overlay). **Fixture:**
> local-level DGP via `_kalman_helpers.generate_local_level_dgp`
> seed=42 + n=200 + 15% missing positions; single-seeded fixture;
> parameter-sensitivity coverage NOT established; Q3b extension
> scope. **Sub-class 2a standalone-only variant** per S28 (αa-S28)
> ratification (Sub-class 2a (αa) variant tagging EXTENDED to
> operational-coupling-count = 0 third variant alongside dual-role
> S22 + triple-role S23; n=3 baseline UPGRADE to codification-stable
> per A3 second-observation tightening precedent). **Tier II.mle-band
> + Pattern A overlay risk attribution:** **(a) Layer 1
> statsmodels.UnobservedComponents Kalman smoother math (validated
> Pattern A regime conditional-on-MLE-alignment):** bit-exact within
> MLE alignment window; MLE-fit-band tolerance when optima diverge;
> validation strength conditional on KFAS + statsmodels MLE
> convergence to compatible optima; **(b) Layer 2 standalone engine
> orchestration (CAI Phase 2 Session 19 F-MD-KALMAN-MODELTYPE
> allowlist gating + preset config + NaN handling + model fit
> fallback + smoothed state extraction + CI construction + model-
> misspecification disclosure):** validation scope per
> `engine/techniques/kalman_imputation.py` lines 34-330+;
> **(c) Confidence interval construction caveat (engine internal
> disclosure):** CI band assumes model-specification correctness;
> if UnobservedComponents variant fails to capture true dynamics,
> reported band understates true imputation uncertainty (per engine
> lines 144-151 honest disclosure). Pre-Path α expert review status.

#### Disclosure pattern (iv) — Internal use disclosure (Tier II.mle-band primary + Pattern A overlay + audit-content-distribution variant)

> `kalman_imputation` Tier II.mle-band primary + Pattern A
> conditional-on-MLE-alignment overlay; cross-package PASS vs R
> KFAS smoother (audit-content-distribution: dedicated audit file
> absent; verdict + Pattern characterization distributed across
> batch summary + cross-batch findings). Sub-class 2a standalone-
> only variant. Engine Layer 2 orchestration + CI construction
> pending expert review. Pre-Path α.

**Validation provenance audit checklist (Workstream B §1 four-question
audit; applied per Q1 entry close):**

- **Q-A (extracted/cited evidence vs inferred reasoning):**
  Extracted/cited evidence. Reference (R KFAS smoother) per
  p3_batch_5_summary.md line 17 (verbatim). Verdict (PASS) per
  p3_batch_5_summary.md line 17 (verbatim). Pattern A regime
  conditional-on-MLE-alignment characterization per
  p3_batch_5_summary.md lines 21-23 + phase3_cross_batch_findings.md
  line 23 (verbatim). Audit date (2026-04-29) per
  p3_batch_5_summary.md header (verbatim). Fixture (local-level DGP
  n=200 seed=42 + 15% missing) per harness `p3_kalman_imputation.py`
  lines 65-66 + `_inject_missing` helper (verbatim). Tier II.mle-
  band primary characterization per verdict_class "mle_fit" (harness
  line 56 verbatim) + scope_reframing §2 lines 134-137 definitional
  scope (verbatim). Pattern A conditional-on-MLE-alignment overlay
  characterization per cross-batch findings (verbatim). **AUDIT-
  CONTENT-DISTRIBUTION FIRST-INSTANCE VARIANT DISCLOSURE per S28 (α)
  Chat ratification:** dedicated `p3_kalman_imputation_audit.md`
  file ABSENT; verdict + Pattern characterization distributed
  across `p3_batch_5_summary.md` (PASS + Pattern A section) +
  `phase3_cross_batch_findings.md` (Pattern A cross-batch list);
  specific abs/rel diff numerics NOT in surfaced audit content;
  audit content distribution structural anomaly variant analogous
  to S23 pp_test (different structural form: S23 = scope_reframing
  §2 enumeration absent; S28 = dedicated audit file absent). Layer
  1 / Layer 2 framework operative per S26 STOP 1.5 second close
  ratification carried forward. Catalog mapping (1:1) verified per
  audit Wrapper field. **§4.7.A pattern NOT observed at S28**
  (clean engine-uses-same-function alignment; harness line 82
  invokes engine.run() directly); distinct from S26 + S27 §4.7.A
  variant observations; S28 breaks §4.7.A pattern recurrence at
  Block 8 final entry; post-S28 §4.7.A pattern observations = n=4
  across §2.5 entries (S14a + S18 + S26 + S27); kalman_imputation
  does NOT add fifth observation. **Sub-class 2a (αa) variant tagging
  EXTENDED to standalone-only variant** per (αa-S28) Chat
  ratification; n=3 baseline UPGRADE to codification-stable per A3
  second-observation tightening precedent threshold satisfied at
  n=3 observations (S22 dual-role + S23 triple-role + S28 standalone-
  only). **A9 Class A 10th-instance candidate** (Chat trigger CHAT
  RATIFICATION #5 Sub-class 2a (αa) variant tagging second-
  observation candidate empirically refined per S28 Step 0 (e) catch
  — kalman_imputation is two-layer standalone-only NOT helper-export-
  bearing analogous to S22 + S23 codified variants; banked for
  absorption #4 codification alongside A9 Class A n=7 + n=8 + n=9
  candidates). **A9 Class B counter unchanged post-S28 n=4 ACTIVE**:
  framing class working hypothesis CONFIRMED at Step 0 per A9 Class
  B revised default discipline operating proactively per S22+S23+
  S25+S26+S27+S28 sustained pattern. **Maturation observation FIFTH
  SUSTAINED OBSERVATION REACHED at S28** + SIX-timing-point empirical
  surface preserved per CHAT RATIFICATION #11 (no new timing point
  variant at S28; proactive-prevention operation SUSTAINED across
  established timing points (i)-(vi) per S27 codification). Promotion
  candidate ROBUSTNESS REINFORCED for absorption #4 codification per
  Chat ITEM 7 AFFIRMED at S27. Verify-state-at-first-consumption
  sub-discipline 23rd instance application.

- **Q-B (user genuine contestation vs default ratification):**
  Default ratification at twelfth-technique selection per Mark 3
  efficient-ratification + (α) unprompted case-against discipline
  operative per Workstream B §1.4 codification + S20+S25+S26+S27
  reinforcement. **Q-B pattern persists at n=13 across S12 + S13 +
  S14b + S14c + S15 + S17 + S18 + S21 + S22 + S23 + S26 + S27 +
  S28; §1.4 codified observation refinement at empirical pattern
  accumulation** (n=7 at §1.4 S20 codification → n=10 at S25
  refinement → n=11 at S26 → n=12 at S27 → n=13 at S28 reinforcement;
  Workstream B amendment cycle candidate A continues at next cycle).
  Substantive Chat engagement at structural-decision points
  empirically observed (Step 0 STOP 2 5-item ratifications + Tier
  (α) primary+overlay + Sub-class (αa-S28) variant tagging extended
  + audit-content-distribution disclosure framing + A9 Class A 10th
  candidate banking + maturation observation fifth sustained
  observation surface).

- **Q-C (Chat confidence for publication tomorrow with disclosure):**
  Yes for **Layer 1 statsmodels.UnobservedComponents Kalman smoother
  math (Pattern A regime conditional-on-MLE-alignment)** per PASS
  verdict at audit-content-distribution (p3_batch_5_summary +
  cross-batch findings). **CRITICAL Q-C framing per Tier II.mle-band
  + Pattern A overlay structure:** validation evidence is bit-exact-
  within-MLE-alignment-window when KFAS + statsmodels MLE optima
  agree; MLE-fit-band tolerance when optima diverge; defensibility
  conditional on MLE alignment. **Conditional for Layer 2 engine
  orchestration** — F-MD-KALMAN-MODELTYPE allowlist gating + preset
  config + NaN handling + model fit fallback + smoothed state
  extraction + CI construction + model-misspecification disclosure;
  requires expert review of engine implementation OR engine-output
  cross-check at base pinned config. **Critical Q-C framing per
  audit-content-distribution variant:** dedicated audit file ABSENT;
  specific abs/rel diff numerics NOT in surfaced audit content;
  publication-research user invoking `kalman_imputation` from ribbon
  receives smoothed-state imputation per Pattern A regime;
  defensibility to all three audiences (published audience + Morgan
  Stanley compliance + Path α expert reviewer) UNDER Tier II.mle-
  band primary + Pattern A overlay + audit-content-distribution
  variant + Layer 2 orchestration + model-misspecification CI
  caveat expert review acknowledgment.

- **Q-D (retraction surface if expert review later finds inadequacy):**
  MEDIUM per Tier II.mle-band primary + Pattern A overlay scope
  bound + audit-content-distribution variant. kalman_imputation is
  canonical Kalman-smoother-based imputation methodology (widely
  used for missing-value imputation in time series with state-space
  structure). **Layer-specific + Tier II.mle-band + Pattern A overlay
  + standalone-only variant retraction surface (per S28 (α) + (αa-S28)
  + (α) ratifications):**
  - Layer 1 statsmodels.UnobservedComponents Kalman smoother math
    (Pattern A regime conditional-on-MLE-alignment): LOW-MEDIUM;
    PASS verdict + Pattern A characterization per audit-content-
    distribution; expert review surfacing upstream error would
    affect kalman_imputation specifically (NO multi-map propagation
    risk; 1:1 catalog↔wrapper). **Tier II.mle-band primary +
    Pattern A overlay caveat:** validation strength conditional on
    KFAS + statsmodels MLE convergence to compatible optima; non-
    aligned MLE optima → MLE-fit-band tolerance only (not bit-exact).
  - **Layer 2 engine orchestration: MEDIUM** — F-MD-KALMAN-MODELTYPE
    allowlist gating + preset config + NaN handling + model fit
    fallback + smoothed state extraction + CI construction + model-
    misspecification disclosure NOT audit-validated; expert review
    of engine implementation conditional on Layer 2 correctness.
  - **Confidence interval construction caveat (engine lines 144-151
    internal disclosure): MEDIUM-HIGH** — CI band assumes model-
    specification correctness; if UnobservedComponents variant
    fails to capture true dynamics, reported band understates true
    imputation uncertainty; expert review surfacing model-
    misspecification cases would invalidate CI bounds specifically
    (imputation point estimates may remain valid; CI bounds may not).
    **Asymmetric retraction surface:** point estimates vs CI bounds
    independently conditional.
  - **Audit-content-distribution variant retraction surface caveat:
    LOW** — audit content present but distributed; expert review
    surfacing audit-content-distribution issue (e.g., specific
    numeric metric absence) would prompt audit content recovery
    (audit re-run to extract numerics); does NOT invalidate Pattern
    A characterization per cross-batch findings.

**Status:** validated-pre-expert-review per Phase 7+ Q1 trust
documentation remediation; twelfth technique to enter status per
S28 ratification; **THIRD-AND-FINAL Block 8 Missing Data entry —
BLOCK 8 FULLY Q1-AMENDED milestone** = THIRD catalog block fully
Q1-amended after Block 1 Causality at S18 + Block 12 Stationarity
Tests at S23; **per-block continuation pattern at n=3 catalog block
observations** satisfies A3 second-observation tightening precedent
threshold at n=3 — codification candidate at §19.4 §4 forward
instrumentation note 6 refinement at absorption #4; **FIRST Tier
II.mle-band primary + Pattern A conditional-on-MLE-alignment overlay
§2.5 precedent** (analogous to S23 pp_test "Tier II.bit-exact-loose
+ Tier V Pattern J B.2 overlay" primary+overlay framing structure;
institutional pattern for Q1 work program Tier II.mle-band techniques
+ Pattern A conditional overlay characterization); **FIRST Sub-class
2a standalone-only variant Q1 §2.5 entry** (operational-coupling-
count = 0 third variant beyond dual-role S22 + triple-role S23
helper-export-bearing variants per S25 codification); **Sub-class
2a (αa) variant tagging n=3 baseline UPGRADE to codification-stable
per A3 second-observation tightening precedent threshold** satisfied
at n=3 observations (S22 + S23 + S28); **FIRST audit-content-
distribution variant disclosure per S28 (α) ratification**
(dedicated `p3_kalman_imputation_audit.md` absent; verdict + Pattern
characterization distributed across `p3_batch_5_summary.md` PASS
verdict + Pattern A section + `phase3_cross_batch_findings.md`
Pattern A cross-batch list; analogous to S23 pp_test audit-content-
distribution Q-A precedent but DIFFERENT structural variant — S23 =
scope_reframing §2 enumeration absent; S28 = dedicated audit file
absent). **S28 clean two-layer + engine-uses-same-function alignment
+ Tier II.mle-band primary + Pattern A overlay framing per CHAT
RATIFICATION #4 CONFIRMED at Step 0: Layer 1 statsmodels.UnobservedComponents
Kalman smoother (engine + harness both use SAME library function
via engine module direct invocation per harness line 82); Layer 2
engine orchestration (F-MD-KALMAN-MODELTYPE allowlist + preset
config + NaN handling + model fit fallback + smoothed state
extraction + CI construction + model-misspecification disclosure);
NO §4.7.A harness-bypasses-engine pattern observation at S28
(distinct from S26 + S27 §4.7.A variant observations); engine-level
model-misspecification CI band understatement disclosure built into
engine code (lines 144-151) per institutional standard.** **A10
Sub-class disposition (αa-S28) Sub-class 2a (αa) variant tagging
EXTENDED to standalone-only variant** per Chat ratification ITEM 3
(operational-coupling-count = 0 third variant; n=3 baseline UPGRADE
to codification-stable per A3 second-observation tightening
precedent). **A9 Class B counter post-S28: n=4 ACTIVE** (unchanged;
framing class working hypothesis CONFIRMED at Step 0 per A9 Class B
revised default discipline operating proactively per S22+S23+S25+
S26+S27+S28 sustained pattern). **A9 Class A counter post-S28: n=6
ACTIVE + candidates n=7 + n=8 + n=9 + n=10 pending absorption #4
codification** (n=7 candidate per S23-pre Doc 2 tier-enumeration
omission proactive-catch variant; n=8 candidate per S26-pre
catalog-count-baseline misattribution catch; n=9 candidate per S27
trigger drafting reimplementation-vs-use-case-divergence schema-
misattribution catch; **n=10 candidate per S28 trigger drafting
Sub-class 2a variant tagging scope-misattribution catch NEW at
S28**). **A9 Class A + Class B discipline maturation FIFTH SUSTAINED
OBSERVATION REACHED at S28** per A3 second-observation tightening
precedent threshold satisfied at n=5 observations (S23 + S25 + S26
+ S27 + S28 sustained proactive-prevention operation across SIX-
timing-point empirical surface preserved per S27 codification).
**Promotion candidate (§19.4 §4.5 NEW sub-section OR A11 NEW
amendment) ROBUSTNESS REINFORCED for absorption #4 codification
disposition** per Chat ratification ITEM 7 AFFIRMED at S27 STOP 2
(maturation observation WILL codify at absorption #4). **Block 8
FULLY Q1-AMENDED milestone** at S28 close = THIRD catalog block
fully Q1-amended (Block 1 Causality 6 entries + Block 12 Stationarity
Tests 3 entries + Block 8 Missing Data 3 entries = 12 §2.5 entries
total across 3 catalog blocks). **Per-block continuation pattern at
n=3 catalog block observations** codification candidate at §19.4 §4
forward instrumentation note 6 refinement at absorption #4: Block
1 (6 entries / ~1837 LOC / S12-S18 / 1 amendment + 1 absorption);
Block 12 (3 entries / ~1737 LOC / S21-S23 / 0 amendments + 1
absorption); Block 8 (3 entries / [TBD LOC at S28 close] / S26-S28
/ 0 amendments + 0 absorptions; absorption #4 anticipated post-
S28); per-block continuation pattern characterization tighter at
n=3 observation.

## §3 Unvalidated catalog techniques (63 entries; ID-only enumeration)

**Status framing for ALL entries below:** available via
`TSL_RUN_THR("<technique_id>", …)`; **no reference parity
validation; not currently recommended for published output
without expert review of underlying technique implementation
and/or extending reference-parity coverage to the technique.**

Per-technique trust documentation requires either (a) extending
reference-parity coverage (Phase 6+ S1+ wrapper integration
pattern) OR (b) external expert review by domain specialist.
This document does NOT provide per-technique Phase 2 content
for unvalidated entries; ID enumeration with category context
serves the strategist's "what's safe to publish" decision at
the level of "what HAS validation evidence vs what does not."

Cross-reference: `resources/catalog/techniques_catalog.json`
for catalog-side documentation (parameters, presets,
descriptions, summaries).

### Causality / Relationships / Lead-Lag (0 unvalidated; Block 1 FULLY Q1-AMENDED — first catalog block to complete per Q1 work program scope; granger_causality + cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag + dtw_alignment_lag + gcc_phat_delay moved to §2.5 per Phase 7+ S12 + S13 + S14c + S15 + S17 + S18)
(all 6 techniques moved to §2.5)

### Change Points / Anomalies / Interventions (5 unvalidated)
`bocpd`, `cusum_page_hinkley`, `intervention_analysis`, `pelt_change_points`, `stl_esd_anomaly`

### Decomposition & Seasonal Adjustment (4 unvalidated)
`classical_decompose`, `mstl_decompose`, `stl_decompose`, `x13_seasonal_adjust`

### Evaluation / Uncertainty (5 unvalidated)
`block_bootstrap`, `conformal_intervals`, `forecast_combination`, `robust_estimators`, `rolling_origin_cv`

### Forecasting (Classical) (8 unvalidated)
`arima`, `arimax_sarimax`, `auto_arima`, `ets_hw`, `intermittent_demand`, `sarima`, `theta_forecast`, `transfer_function`

### Frequency Domain / Signal (7 unvalidated)
`emd_hht`, `fft_spectrum`, `lomb_scargle`, `periodogram_spectral_density`, `ssa`, `wavelet_coherence_phase_lag`, `wavelet_transform`

### ML / Deep Learning (14 unvalidated; transformer_forecast attention-capture validated separately)
`autoencoder_anomaly`, `echo_state_network`, `gaussian_process_forecast`, `gradient_boosting_forecast`, `lightgbm_forecast`, `lstm_gru_forecast`, `nbeats_forecast`, `nhits_forecast`, `prophet_forecast`, `quantile_regression`, `random_forest_forecast`, `svr_forecast`, `tcn_forecast`, `xgboost_forecast`

### Missing Data / Temporal Disaggregation (0 unvalidated; Block 8 FULLY Q1-AMENDED — THIRD catalog block to complete per Q1 work program scope; denton_chowlin_disaggregation moved to §2.5 per Phase 7+ S26; loess_interpolation moved to §2.5 per Phase 7+ S27; kalman_imputation moved to §2.5 per Phase 7+ S28)
(all 3 techniques moved to §2.5)

### Multivariate Systems (5 unvalidated; johansen_cointegration + forecast_reconciliation + bond_yield_forecast validated separately)
`bvar`, `dynamic_factor_model`, `pca_analysis`, `var`, `vecm`

### Regimes / Nonlinear (6 unvalidated)
`critical_slowing_down`, `hmm`, `markov_switching`, `nar_narx`, `star`, `tar_setar`

### State Space / Filtering (4 unvalidated; kalman_filter + kalman_smoother validated separately)
`local_level`, `local_linear_trend`, `particle_filter`, `structural_ts`

### Stationarity / Tests (0 unvalidated; Block 12 FULLY Q1-AMENDED — second catalog block to complete per Q1 work program scope after Block 1 Causality at S18; adf_test moved to §2.5 per Phase 7+ S21; kpss_test moved to §2.5 per Phase 7+ S22; pp_test moved to §2.5 per Phase 7+ S23)
(all 3 techniques moved to §2.5)

### Volatility / Risk / Tails (5 unvalidated; stochastic_volatility + caviar_quantile_dynamics + evt_pot_gpd validated separately)
`egarch`, `garch`, `gjr_garch`, `har_cj`, `har_rv`

**Total: 63 unvalidated technique IDs across 13 catalog categories** (post-Phase-7+-S12+S13+S14c+S15+S17+S18+S21+S22+S23+S26+S27+S28 amendments; granger_causality + cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag + dtw_alignment_lag + gcc_phat_delay + adf_test + kpss_test + pp_test + denton_chowlin_disaggregation + loess_interpolation + kalman_imputation moved to §2.5; **Block 1 Causality + Block 12 Stationarity Tests + Block 8 Missing Data ALL THREE FULLY Q1-AMENDED — first three catalog blocks to complete per Q1 work program scope; per-block continuation pattern at n=3 catalog block observations satisfies A3 second-observation tightening precedent threshold; codification candidate at §19.4 §4 forward instrumentation note 6 refinement at absorption #4**).

## §4 How to use this document

**For the strategist publishing under their name:**

**Tier 1a — VALIDATED with caveats; parity covers
published-output technique (6 catalog techniques):**
`kalman_filter`, `kalman_smoother`, `johansen_cointegration`,
`stochastic_volatility` (Gaussian + Student-t variants per
parameter-aware exclusion mechanism), `forecast_reconciliation`
(4 methods), `caviar_quantile_dynamics` (SAV variant only).

For these techniques: parity validation evidence covers the
analytical output the strategist publishes from. **§2
boundary-of-validity adherence is required; gap markings
identify edge cases.** Read each technique's §2 entry before
publishing output that depends on it.

**Tier 1b — VALIDATED with caveats; parity covers
SUB-COMPONENT only (2 catalog techniques):**
`evt_pot_gpd` (extremal index sub-component; POT/GPD
parameter estimation NOT validated),
`transformer_forecast` (attention-capture sub-component;
full forecasting pipeline NOT validated).

For Tier 1b techniques: parity validation evidence covers a
**sub-component** of the full technique; the **full pipeline**
(POT/GPD tail-parameter inference for `evt_pot_gpd`;
positional encoding + output projection + training loop +
hyperparameter sensitivity for `transformer_forecast`)
**requires expert review for any published use**. The Tier 1b
classification means parity validates internal correctness of
one piece, NOT end-to-end correctness of the technique as
published.

**Tier 2 — DORMANT (1 catalog technique):** `bond_yield_forecast`.

Pattern F structural invariants validated; **NO external
reference parity; NO parameter posterior parity validated**.
**Requires expert review for any published use** regardless of
TSL internal invariants holding.

**Tier 3 — UNVALIDATED (63 catalog techniques; §3 enumeration; post-Phase-7+-S12+S13+S14c+S15+S17+S18+S21+S22+S23+S26+S27+S28 amendments):**

Available via `TSL_RUN_THR` but **no reference-parity validation
evidence**. Two paths to publishable confidence:
(i) extending reference-parity coverage (multi-cycle work; see
master plan §15 sub-domain (i) extension framing); (ii) external
expert review of the underlying technique implementation.

**The 8-wrapper allowlist + BYF dormant set represents ~11% of
the 84-technique catalog.** ~89% of catalog techniques have no
reference-parity validation evidence. This is honest current
state; not a failure of TSL — reference parity work is multi-
cycle scope and intentionally bounded per Phase 5 + Phase 6+
sub-domain (i) discipline.

**What "publishable with confidence" means in current state:**
Tier 1 with §2 boundary-of-validity adherence + cycle-architecture
discipline (master plan v1.3 + §19 Phase 6+ apparatus
operational). Tier 2 + 3 require additional validation work or
expert review.

## §5 Cross-references (compressed)

- Master plan §15 sub-domain (i) at
  `plans/reference_parity_phase5_master_plan.md` lines 297-528
  (8-wrapper allowlist construction; per-wrapper field-
  availability protocol)
- Master plan §15 sub-domain (i) Phase 6+ S1 architectural
  amendment at lines 459-528 (parameter-aware exclusion mechanism;
  applied to mcmc_convergence checker)
- Phase 6+ S1 banking: `s1_banking.md`
  (B-Phase6-S1-STRUCTURAL-INVARIANT-PARAMETER-AWARE-EXCLUSION;
  2b/2c MCMC SV mechanism)
- Phase 6+ S3 banking: `s3_banking.md`
  (B-Phase6-S3-NONE-HANDLING-FIX-S8; 5-function/7-site None-
  handling fix on structural invariant checkers)
- Phase 6+ S6 design: `s4_smoke_test_infrastructure_design.md`
  (BYF disposition keep-dormant + accept-BLOCK; 4 activation
  paths surfaced)
- Phase 6+ S6 banking: `s6_subdomain_iv_deferred_activation_banking.md`
  (sub-domain (iv) audit-driven Outcome C deferred-activation;
  reserve concept validated)
- §19.4 living calibration baseline: `calibration_baseline.md`
  (A1 + A2 + A3 amendments; A2 verify-state-at-activation
  protocol applied at this document authoring)
- Catalog: `resources/catalog/techniques_catalog.json` (84
  techniques; canonical registry)

## Banking footer

**B-Phase6-S8-TRUST-INVENTORY-TECHNIQUES-FIRST-INSTANCE
codification** (inline per CONSTRAINT 2 first-sub-session
framing):

**Trust-infrastructure documentation class established at this
sub-session.** First instance produces empirical baseline.
Class characteristics:
- Output: per-technique inventory document with Phase 1
  mechanical content + extractable Phase 2 trust content +
  explicit gap markings
- Authoring discipline: EXPLICIT FABRICATION PROHIBITION on
  Phase 2; honest gap markings ("requires expert review of
  underlying technique") in place of generated content
- Audit-driven scope: enumeration of validated subset + ID-
  only enumeration of unvalidated subset

**First-instance template (this document):** 9 catalog entries
with full Phase 2 content + 75 catalog entries enumerated by ID
only. Document body LOC + banking footer LOC reported at sub-
session closeout for §19.4 calibration data.

**Subsequent sub-session sequence (per Chat ratification
pause-and-review protocol):**
- Halt for Chat review of THIS document template before
  authoring direct UDF inventory
- Phase 6+ S9: C1 infrastructure direct UDF inventory (8 UDFs;
  TSL_RUN_THR entry cross-references THIS document for
  technique inventory)
- Phase 6+ S10: C2 stationarity direct UDF inventory (2 UDFs)
- Phase 6+ S11+: C3 causality + C4 decomposition + C5
  forecasting direct UDF inventories (5 UDFs total across 3
  categories)

### §19.4 elevation candidate 1 — Soft-estimate-vs-empirical pattern: anecdote → pattern → ESTABLISHED

**Status update at S8: pattern → ESTABLISHED.** Three
observations across three sub-sessions; same root cause
(codebase state has drifted from documented state in load-
bearing artifacts; verify-state-at-activation protocol catches
the drift).

| Observation | Sub-session | Stale claim | Empirical at activation |
|---|---|---|---|
| First | S3 | B-Phase4-S7-1 "6 checkers / S6/8/9" | 5 functions / 7 sites; cross-batch (S7+S13) |
| Second | S6 | B-Phase4-S10-3 "n_draws=1000" | n_draws=2000 (Phase 4-5 intervening work uncross-referenced) |
| Third | S8 | CLAUDE.md memory "67 techniques" | 84 techniques in canonical catalog |

**§19.4 A2 elevation candidate:** A2 currently codifies
operational protocol (verify-state-at-activation). With
established pattern, A2 may warrant content elevation for v1.4+
master plan amendment as cycle-architecture observation: stale
banking entries / stale memory / stale framing across cycle
boundaries are recurrent and unavoidable; verify-state-at-
activation protocol is the load-bearing mitigation. Forward
instrumentation: continued operational application at S9+
sub-sessions; if falsifying observation surfaces (banking entry
remained current at activation), pattern weakens.

### §19.4 elevation candidate 2 — Trust-infrastructure documentation class: first empirical baseline

**S8 first instance LOC (final post-amendment):** ~615 LOC
document body + ~95 LOC banking footer = ~710 LOC total
artifact (post Tier 1a/1b split + 2 minor observation
incorporations + this elevation-candidate banking amendment).

**Provisional class baseline projection (loose; single data
point; refine at second observation per §19.4 A3 design-class
precedent):**
- Document body: 400-700 LOC
- Surface threshold: ~800 LOC

**§19.4 A4 amendment candidate (elevated from informational to
active per first observation):** trust-infrastructure
documentation class taxonomy extension to formally include in
v1.3 §19.1 sub-session class taxonomy. Current taxonomy:
novel-substantive / consolidation / routine-targeted-patch /
synthesis. Trust-infrastructure documentation class is novel;
doesn't fit existing taxonomy cleanly. **First-instance
empirical baseline absorbed at this banking footer for §19.4
calibration data accumulation.** If class recurs at S9-S11+
direct UDF inventory sub-sessions, A4 amendment candidate
codifies class taxonomy + threshold at next recalibration
moment per amendment density criterion.

**A2 verify-state-at-activation protocol third operational
application** (S6 audit was second; this document's CLAUDE.md-
67-vs-empirical-84 catalog count correction is third).
Banking-class A2-evidence accumulation continues; pattern
solidifies per §19.4 A2 forward instrumentation. Per
elevation candidate 1 above, A2 status graduates from
operational protocol to ESTABLISHED pattern at this commit.

**Cross-references:** trigger ratifications 1-6 at Phase 6+ S8
ratification trigger; Code's pre-flight enumeration scope
surface (Chat surface; not committed per Ratification 6); §19.4
calibration data forward-looking per Subsequent sub-session
sequence above.

## Disposition

Trust inventory first instance SHIPPED. 9 validated technique
entries + 75 unvalidated technique enumeration + strategist-
facing usage guidance + cross-references. Trust-infrastructure
documentation class established with empirical baseline. Halt
for Chat review per pause-and-review protocol; subsequent
direct UDF inventory sub-sessions proceed post-review.
