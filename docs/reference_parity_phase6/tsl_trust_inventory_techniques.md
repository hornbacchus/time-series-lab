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
- 6 catalog techniques with Phase 7+ Q1 trust documentation
  remediation (§2.5; Tier-characterization + disclosure
  templates + validation provenance audit checklist;
  post-Phase-7+-S12+S13+S14c+S15+S17+S18 amendments)
- 69 catalog techniques without reference-parity validation
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

## §3 Unvalidated catalog techniques (69 entries; ID-only enumeration)

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

### Missing Data / Temporal Disaggregation (3 unvalidated)
`denton_chowlin_disaggregation`, `kalman_imputation`, `loess_interpolation`

### Multivariate Systems (5 unvalidated; johansen_cointegration + forecast_reconciliation + bond_yield_forecast validated separately)
`bvar`, `dynamic_factor_model`, `pca_analysis`, `var`, `vecm`

### Regimes / Nonlinear (6 unvalidated)
`critical_slowing_down`, `hmm`, `markov_switching`, `nar_narx`, `star`, `tar_setar`

### State Space / Filtering (4 unvalidated; kalman_filter + kalman_smoother validated separately)
`local_level`, `local_linear_trend`, `particle_filter`, `structural_ts`

### Stationarity / Tests (3 unvalidated)
`adf_test`, `kpss_test`, `pp_test`

### Volatility / Risk / Tails (5 unvalidated; stochastic_volatility + caviar_quantile_dynamics + evt_pot_gpd validated separately)
`egarch`, `garch`, `gjr_garch`, `har_cj`, `har_rv`

**Total: 69 unvalidated technique IDs across 13 catalog categories** (post-Phase-7+-S12+S13+S14c+S15+S17+S18 amendments; granger_causality + cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag + dtw_alignment_lag + gcc_phat_delay moved to §2.5; **Block 1 Causality FULLY Q1-AMENDED — first catalog block to complete per Q1 work program scope**).

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

**Tier 3 — UNVALIDATED (69 catalog techniques; §3 enumeration; post-Phase-7+-S12+S13+S14c+S15+S17+S18 amendments):**

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
