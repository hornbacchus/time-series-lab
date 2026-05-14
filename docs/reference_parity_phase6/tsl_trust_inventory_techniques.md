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
- 2 catalog techniques with Phase 7+ Q1 trust documentation
  remediation (§2.5; Tier-characterization + disclosure
  templates + validation provenance audit checklist;
  post-Phase-7+-S12+S13 amendments)
- 73 catalog techniques without reference-parity validation
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

## §3 Unvalidated catalog techniques (73 entries; ID-only enumeration)

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

### Causality / Relationships / Lead-Lag (4 unvalidated; granger_causality + cross_correlation_lag moved to §2.5 per Phase 7+ S12 + S13)
`dtw_alignment_lag`, `gcc_phat_delay`, `prewhitened_ccf_lag`, `rolling_ccf_lag`

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

**Total: 73 unvalidated technique IDs across 13 catalog categories** (post-Phase-7+-S12+S13 amendments; granger_causality + cross_correlation_lag moved to §2.5).

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

**Tier 3 — UNVALIDATED (73 catalog techniques; §3 enumeration; post-Phase-7+-S12+S13 amendments):**

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
