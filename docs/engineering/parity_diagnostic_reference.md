# TSL Parity Diagnostic Reference (P-2)

**Version:** v1.1.0 (issued at Phase 3.5 Session 11, 2026-04-30; v1.0.0 at Phase 3 Session 16)

**Status:** Living document. Spec for parity-harness diagnostic
patterns and reference-library quirks accumulated across Phase 3
batches and Phase 3.5 cycle.

This document captures **lessons learned** from Phase 3 reference
parity audits — patterns of cross-implementation divergence that
recur often enough to deserve documentation, with concrete
resolution recipes. Future contributors building parity checks for
new wrappers should consult this reference to anticipate quirks
and align tolerances + comparison logic accordingly.

Authoritative status: this document supersedes ad-hoc per-batch
notes once a pattern recurs across 3+ wrappers.

---

## Section A — Tolerance Class Taxonomy

**Status:** Locked at Session 16 close. The 11 verdict_class
values below are the authoritative class taxonomy used by
`harness/tolerances.py` and required-declared on every parity
check via the `verdict_class` attribute (binding per
[P-1 §5.1](parity_standard.md#51-verdict_class-taxonomy-11-classes--locked-session-14)).

This section explains *what each class means* and *when to
pick it* for new wrappers. Bands listed are the canonical
defaults; per-wrapper widening is acceptable with audit-report
justification.

### A.1 — `closed_form` (1e-10 abs / 1e-10 rel)

**Use when:** the algorithm is closed-form arithmetic
(eigendecomposition, FFT, OLS, classical decomposition,
quantile of sorted array). No iteration, no optimization, no
random state. Both implementations execute identical math.

**Empirical floor:** machine-precision (~1e-13 to 1e-16).
The 1e-10 abs floor in tolerances.py leaves headroom for
subprocess CSV roundtrip noise and BLAS-implementation drift.

**21 wrappers in Phase 3** at this band:

- `1c_bvar_irf_fevd` (Phase 1: 4.58e-16)
- `3e_mint_family` (Phase 1: 4.66e-15)
- `p3_intermittent` (S3: 3.77e-15)
- `p3_classical_decompose` (S4: 7.11e-14)
- `p3_har_rv` (S6: 8.88e-16)
- `p3_var` (S7: 7.22e-16)
- `p3_vecm` (S7: 9.99e-16)
- `p3_pca` (S7: 7.99e-15)
- `p3_local_level`, `p3_kalman_imputation` (S9; closed-form
  when MLE optima align)
- `p3_adf` (S10: 1.07e-14)
- `p3_kpss` (S10: 5.55e-17)
- `p3_pp` (S10: 2.09e-06; Pattern J widening for HAC kernel
  divergence)
- `p3_ccf` (S14: 1.33e-15)
- `p3_dtw` (S14: 0.0)
- `p3_denton_chowlin` (S14: 6.39e-14)
- `p3_robust_estimators` (S12: 4.22e-15)
- `p3_loess` (S14: 0.0; Pattern A.1 same-library)
- `p3_periodogram` (S11: 0.0; Pattern A.1)
- `p3_wavelet_transform` (S11: 0.0; Pattern A.1)
- `p3_wavelet_coherence` (S11: 0.0; self-parity)

### A.2 — `mle_fit` (1e-3 abs / 1e-2 rel)

**Use when:** the algorithm requires MLE optimization with a
deterministic optimizer (BFGS, L-BFGS-B, scoring algorithm,
Newton-Raphson). Both implementations optimize the same
likelihood but may converge to slightly different parameter
values due to optimizer-stopping-criterion differences.

**Master plan §7.1 baseline.** Coefficient-level divergence
typically 1e-5 to 1e-4 abs; the 1e-3 abs / 1e-2 rel band leaves
~3 orders of headroom.

**4 wrappers in Phase 3** at this band:

- `p3_arima_manual`, `p3_sarima`, `p3_arimax_sarimax` (S2-S3:
  ~5e-6 abs typical)
- `p3_tbats` (S3: harness promotion of Phase 1 audit)
- `p3_intervention_analysis` (S10: ar1 4.20e-04, omega
  1.70e-05)

**S12 split candidate (banked Item #2):** evidence from S7
(p3_var headroom 8.1 orders inside band) and from Batch 2
GARCH (rugarch boundary attractor at the band's outer edge)
suggests a future split:

- `single_impl_mle` — TSL backend and reference share
  optimizer lineage (e.g., both use L-BFGS-B variants);
  achievable 1e-5 abs typical → tighten band to 1e-5 abs /
  1e-4 rel
- `optimizer_divergent_mle` — independent optimizer
  implementations with different initialization heuristics
  (arch SLSQP vs rugarch hybrid); keep the §7.1 1e-3 abs /
  1e-2 rel baseline

Currently use `mle_fit` as the default; refinement deferred
to Phase 3.5 or P-2 v1.1.

### A.3 — `state_space_reform` (5e-2 abs / 1e-1 rel — widened)

**Use when:** TSL and reference implement the same algorithm
via mathematically-equivalent but implementationally-different
state-space reformulations. Hyndman-Khandakar 2008 §6.4
documents this for ETS (statsmodels exponential-smoothing
recursion vs R `forecast::ets` state-space innovation form).

**2 wrappers in Phase 3:**

- `p3_ets` (S3; AIC scale offset Pattern D as Secondary
  documented divergence)
- `p3_theta` (S3; Hyndman-Billah 2003 reformulation vs
  Assimakopoulos-Nikolopoulos 2000)

### A.4 — `iterative_loess` (5e-2 abs / 5e-2 rel — widened; CAVEAT-acceptable)

**Use when:** the algorithm uses iterative LOESS smoothing
with implementation-defined inner-iteration counts +
LOESS-bandwidth defaults. Per-component divergence ~1e-2 abs
is reproducible across seeds (deterministic; not MC noise).

**2 wrappers in Phase 3:**

- `p3_stl` (S4; CAVEAT verdict)
- `p3_mstl` (S4; CAVEAT — non-unique decomposition)

`reroll_on_caveat = False` is the operational default
(established at S4); CAVEAT does not escalate to BLOCK.

### A.5 — `mcmc` (5e-3 abs / 5e-2 rel — three-outcome PASS / CAVEAT / BLOCK)

**Use when:** the algorithm uses MCMC sampling. Posterior
moments have inherent MC error O(1/sqrt(N_eff)); tolerance
must reflect this even when both implementations are
mathematically correct.

**Severity ladder (locked at Phase 1 Stage B):**

- `< 5%` rel diff → PASS (MC noise band)
- `5-10%` rel diff → CAVEAT (high but plausibly MC)
- `>10%` rel diff → CAVEAT escalation; investigate prior
  parameterization, mixture-component spec, proposal
  tuning differences (NOT classified as bug)

**2 wrappers in Phase 3** (Phase 1 audit IDs):

- `2b_mcmc_sv_gaussian`
- `2c_mcmc_sv_student_t`

### A.6 — `em_stochastic` (1e-2 abs / 5e-2 rel — widened)

**Use when:** the algorithm uses EM iteration with multiple
local optima of the same likelihood surface. HMM transition
matrix, Markov-switching mean estimates, DFM factor loadings.
TSL and reference can converge to different local optima
even on the same fixture.

**Per-metric widening within em_stochastic** (Item #10
**CLOSED at Phase 3.5 Session 4**): the original v1.0.0 entry
identified that means + log-likelihood typically agree at
1e-5 abs (4+ orders headroom) while transition matrices
diverge at 0.05-0.25 abs (0-2 orders headroom). Phase 3.5
Session 4 implemented the per-metric schema (see
[P-1 §5.2.1](parity_standard.md#521-per-metric-tolerance-ladder-schema-locked-phase-35-session-4))
and split two wrappers' ladders.

**5 wrappers in Phase 3 + per-metric tier status:**

- `p3_dfm` (S7: loadings 1.22e-3) — single-band, no split
  warranted (S4 audit found aligned per-metric headroom).
- `p3_hmm` (S8: means 1.48e-5; transmat 0.237 — 0.3 widened
  band) — **per-metric SPLIT at S4**:

  | Metric | Per-metric band | Achieved abs | Headroom (orders) |
  |---|---:|---:|---:|
  | transition_matrix | 0.3 abs / 1.0 rel (kept — Pattern H DSCD-EM) | 2.37e-1 | 0.1 |
  | emission_means | 1e-3 abs / 1e-3 rel (tightened) | 1.48e-5 | 1.8 |
  | emission_covars | 1e-3 abs / 1e-3 rel (tightened) | 7.74e-5 | 1.1 |
  | log_likelihood | 1e-3 abs / 1e-3 rel (tightened) | 5.46e-6 | 2.3 |

- `p3_markov_switching` (S8: means 5.91e-5; transmat 5.46e-2)
  — **per-metric SPLIT at S4**:

  | Metric | Per-metric band | Achieved abs | Headroom (orders) |
  |---|---:|---:|---:|
  | regime_means | 1e-2 abs / 1e-2 rel (tightened) | 5.90e-5 | 2.2 |
  | transition_matrix | 2.0 abs / 1.0 rel (kept) | 5.46e-2 | 1.6 |
  | log_likelihood | 2.0 abs / 1.0 rel (kept) | 0.348 | 0.8 |

- `p3_emd_hht` (S11: CAVEAT — different sifting libraries)
  — single-band; CAVEAT verdict already accommodates the
  per-metric divergence pattern.
- `p3_nar_narx` (S8: NO-REFERENCE Tier C correlation-based)
  — N/A; no reference for per-metric calibration.

**Pattern H per-metric finding** (Phase 3.5 Session 4):
within em_stochastic wrappers, the DSCD pattern is
**metric-specific**, not wrapper-wide. Both audited wrappers
showed DSCD on transition matrices and log-likelihoods
(where EM label-permutation and sign-convention ambiguities
live) but per-component agreement at machine-precision-
adjacent tolerances on emission / regime means. This
strengthens the [P-3 §3.3 DSCD finding](parity_empirical_findings.md#33--dscd-is-a-real-phenomenon-not-a-tolerance-bug)
with metric-level granularity.

### A.7 — `dl_seed_pinned` (1e-6 abs / 1e-5 rel)

**Use when:** the algorithm uses deep-learning training with
seed pinning + cuDNN deterministic flag. Same-library self-
test gives bit-exact reproducibility on float32 outputs;
1e-6 abs floor accommodates float32 accumulation drift.

**6 wrappers in Phase 3:**

- `p3_lstm_gru`, `p3_tcn`, `p3_nbeats`, `p3_nhits`,
  `p3_autoencoder`, `p3_esn` (S13: all 0.0 abs)

### A.8 — `bootstrap_distributional` (planned)

**Reserved.** Phase 3 Batch 10 (`p3_block_bootstrap`)
exercised this class via self-parity at 0.0 abs, classified
under `closed_form` since seed-pinning makes it deterministic.
The `bootstrap_distributional` class is reserved for any
future check that compares bootstrap distribution shapes
(quantile match, distributional centering) rather than
seed-pinned identical samples.

### A.9 — `conformal_coverage` (1e-12 abs predictions; slack on coverage)

**Use when:** the algorithm produces conformal prediction
intervals. Predictions are closed-form (quantile of
calibration residuals); coverage is probabilistic with finite-
sample slack.

**1 wrapper in Phase 3:**

- `p3_conformal` (S13: predictions 0.0 abs; coverage 0.8625
  vs nominal 0.9 within finite-sample slack)

### A.10 — `single_impl_mle` (production-locked at Phase 3.5 Session 3)

**Band: 1e-5 abs / 1e-4 rel** (block: 1e-3 abs / 1e-2 rel)

**Status:** Production-locked at Phase 3.5 Session 3 (2026-04-29).
Was P-2 v1.0.0 candidate; v1.1.0 promotes per [P-1 §5.1](parity_standard.md#51-verdict_class-taxonomy-11-classes--locked-session-14)
production-lock criteria.

The `single_impl_mle` class applies to MLE-fit wrappers where:
1. There is a single canonical implementation shared across
   TSL + reference (no optimizer divergence between
   independent MLE implementations).
2. Empirical evidence shows ≥3 orders of headroom inside the
   canonical `mle_fit` band (1e-3 abs / 1e-2 rel) on the
   wrapper's primary metrics.

The class is the natural tightening of `mle_fit` for the
sub-population where TSL + reference share the optimizer
machinery (e.g., both wrap statsmodels under the hood, or
both invoke the same R-package implementation). The
`mle_fit` band's 1e-3 abs ceiling is calibrated for the
worst-case across independent MLE implementations; when that
worst-case doesn't apply, the achievable precision is several
orders better.

**Production-lock evidence:**

| Wrapper | Worst-metric achieved abs | Old `mle_fit` band | Headroom (orders) |
|---|---:|---:|---:|
| `p3_vecm` (the only current member) | 9.99e-16 (beta vector) | 1e-3 | 13 |

`p3_vecm` migrated from `mle_fit` → `single_impl_mle` at S3.
Tightening preserved 9 orders of margin against the new 1e-5
abs band. Fast-tier sweep 76/76 unchanged post-migration;
master plan §8.1 risk 4 (tolerance tightening produces
regression on previously-passing checks) NOT triggered.

**Audit of remaining `mle_fit` wrappers at S3:** no other
candidates met the ≥3-orders headroom criterion:

| Wrapper | Worst-metric achieved abs | Headroom (orders) | Decision |
|---|---:|---:|---|
| `p3_arimax_sarimax` | 5.52e-06 | 2.3 | Keep `mle_fit` |
| `p3_sarima` | 2.22e-05 | 1.7 | Keep `mle_fit` |
| `p3_arima_manual` | 1.02e-04 | 1.0 | Keep `mle_fit` |
| `p3_intervention_analysis` | 4.20e-04 | 0.4 | Keep `mle_fit` (right at band) |
| `3a_caviar_sav` | (Nelder-Mead non-uniqueness) | — | Keep `mle_fit` (not a candidate) |
| `p3_var` / `p3_pca` | (already `closed_form`) | — | Already in tighter band |

**Selecting `single_impl_mle` for new wrappers:** use the
decision tree at [A.12](#a12--selecting-a-class-for-new-wrappers).
The class is appropriate when both TSL and the reference are
known to call the same underlying optimizer / linear-algebra
routines (e.g., both wrap `statsmodels.tsa.vector_ar.vecm`
internals, OR both compile to a shared C/Fortran routine).

### A.11 — `optimizer_divergent_mle` (candidate; not yet locked)

The `optimizer_divergent_mle` candidate would tighten the
`mle_fit` band for wrappers where optimizer divergence
between independent MLE implementations is empirically
larger than the canonical 1e-3 abs band can cleanly contain
(i.e., the wrapper would benefit from a WIDER band, not a
tighter one).

**Banked status:** Phase 3 + Phase 3.5 surfaced no wrapper
that demonstrated ≥3 orders of headroom in the opposite
direction (i.e., evidence that the canonical band is too
tight to admit a passing verdict for genuinely divergent
optimizers). The GARCH family at S6 was a borderline case,
but rugarch's gosolnp pinning brought divergence within
1e-4 abs (~1 order outside band, not inside).

**No action required at v1.1.0.** Reserve the candidate
status for Phase 4 if/when an optimizer-divergent MLE
wrapper surfaces.

### A.12 — Selecting a class for new wrappers

Use the following decision tree:

1. **Is the algorithm closed-form (no optimization)?**
   → `closed_form`
2. **Is it MLE with a single optimizer family?**
   → `mle_fit` (canonical default); promote to
   `single_impl_mle` when the wrapper meets the [A.10
   production-lock criteria](#a10--single_impl_mle-production-locked-at-phase-35-session-3)
   (single canonical implementation across TSL + reference,
   ≥3 orders headroom evidence)
3. **Is it state-space reformulation across implementations?**
   → `state_space_reform`
4. **Is it iterative LOESS / iterative smoothing?**
   → `iterative_loess`
5. **Is it MCMC sampling?**
   → `mcmc`
6. **Is it EM with multiple local optima?**
   → `em_stochastic`
7. **Is it DL training with seed pinning?**
   → `dl_seed_pinned`
8. **Is it conformal prediction?**
   → `conformal_coverage`
9. **None of the above?** → audit-report justification
   required; propose a new class candidate.

---

## Section B — Pattern J Reference-Library Quirks Catalog

**Started:** 2026-04-29 (Phase 3 Session 12, Batch 8 entry close,
per check-in 1.5 act-now decision #1).

**Scoping rule** (Phase 3.5 Session 9 / v1.1.0 hardening):
Pattern J catalog entries describe **behaviors of the
reference library** that the TSL parity harness must
accommodate. The catalog is NOT a general "things we
encountered" list. Three categories of finding that LOOK
like Pattern J entries but are NOT, and should route
elsewhere:

| Category | Example | Routes to |
|---|---|---|
| **TSL wrapper defects** | CSD `n_surrogates=1000` default produces 11.7 GiB scipy memory blow-up on long real-data series (Phase 3.5 S8 finding) | Phase 4 wrapper-engineering candidate |
| **Fixture conventions** | T10Y2Y constructed as `DGS10 - DGS2` cross-rate (Phase 3.5 S8 fixture expansion) | Tools-level fixture-pool README convention |
| **Applied empirical findings** | GJR-GARCH leverage gap on commodity returns (~16 lik units on WTI vs ~0.2 on FX; Phase 3.5 S8 GARCH sweep) | Macro Strategy product backlog |

These three re-banking decisions were made at Phase 3.5
Session 9 closure to preserve Pattern J's specificity. Without
this scoping rule, the catalog drifts toward becoming a
universal observation-log and loses its diagnostic value
(when a contributor scans Pattern J for a quirk affecting
their reference library, they should find concrete reference-
library behaviors, not TSL-side defects mixed in).

Each entry documents:
1. **Source** — package/version where the quirk surfaces
2. **Quirk** — what the API/default does that differs from
   intuition or from sibling implementations
3. **Resolution** — recipe for aligning the parity comparison
4. **Detected in** — audit ID where surfaced

### B.1 — Statistical methodology / numerical conventions

#### B.1.1 — MSwM `@logLikel` slot vs `@Likelihood` slot (S8)

**Source:** R `MSwM::msmFit` (markov-switching regression);
MSwM 1.5.

**Quirk:** Documentation suggests `ms@Likelihood`; actual slot
is `ms@Fit@logLikel`. Sign convention is also positive (vs
statsmodels which uses negative log-likelihood by convention).

**Resolution:** `as.numeric(ms@Fit@logLikel)` to extract; compare
via `abs()` to neutralize sign convention.

**Detected in:** `p3_markov_switching` audit (Session 8).

#### B.1.2 — tsDyn `setar` threshold via `coef()` not slot (S8)

**Source:** R `tsDyn::setar`; tsDyn 11.0.6.

**Quirk:** Documentation suggests `fit$model.specific$th`; that
slot is NULL. Threshold value is at `coef(fit)["th"]`.

**Resolution:** Use `as.numeric(coef(fit)["th"])`.

**Detected in:** `p3_tar_setar` audit (Session 8).

#### B.1.3 — MSwM Hessian singularity with `sw=c(TRUE,TRUE)` (S8)

**Source:** R `MSwM::msmFit`.

**Quirk:** `sw=c(TRUE,TRUE)` (allow both intercept and
autoregressive coefficient to switch) frequently causes Hessian
singularity → fit fails or returns NaN params on small T.

**Resolution:** Use `sw=c(TRUE,FALSE)` (intercept-only switching)
for parity-test fixtures; document constraint in audit.

**Detected in:** `p3_markov_switching` audit (Session 8).

### B.2 — Internal-default divergence

#### B.2.1 — arch.unitroot.PhillipsPerron HAC kernel vs urca (S10)

**Source:** Python `arch.unitroot.PhillipsPerron` (arch 8.0.0);
R `urca::ur.pp` (urca 1.3.4).

**Quirk:** Even with pinned `lags=5` (Newey-West truncation
bandwidth), the two implementations differ in HAC kernel weights
(arch: triangular kernel; urca: closer to identity weighting in
its Z(t)-stat formula) and residual variance divisor (n-1 vs
n-k). Produces ~1e-6 absolute drift on identical input.

**Resolution:** Tolerance widening to `abs_tol=1e-3, rel_tol=1e-2`.
Documented in `p3_pp` ladder justification.

**Detected in:** `p3_pp` audit (Session 10).

#### B.2.2 — rugarch boundary attractor on default solver (S6)

**Source:** R `rugarch::ugarchfit` (rugarch 1.5.5).

**Quirk:** Default `solver='hybrid'` lands at the alpha+beta≈1
boundary attractor on ~30% of GARCH(1,1) fixtures, even when
arch (Python) reliably finds the global optimum at the same
data.

**Resolution:** Pin `solver='gosolnp'` with `n.restarts=10,
n.sim=2000, rseed=20260428` for reproducible global-optimum
convergence.

**Detected in:** `p3_sgarch`, `p3_gjr_garch`, `p3_egarch` audits
(Session 6). Pattern H DSCD-MLE classification.

#### B.2.3 — arch.GJR-GARCH naming (S6)

**Source:** Python `arch.arch_model`.

**Quirk:** `vol="GJR-GARCH"` is NOT a recognized vol type; the
correct invocation is `vol="GARCH", o=1`.

**Resolution:** Pass `vol="GARCH", o=1` for the GJR-GARCH
parameterization.

**Detected in:** `p3_gjr_garch` audit (Session 6).

#### B.2.4 — arch.EGARCH analytic forecast horizon limit (S6)

**Source:** Python `arch.arch_model` with `vol="EGARCH"`.

**Quirk:** `forecast(horizon>1, method="analytic")` raises a
ValueError; analytic multi-step forecasting is not implemented.

**Resolution:** Use `method="simulation"` with at least 1000
sims for multi-step EGARCH forecasts.

**Detected in:** `p3_egarch` audit (Session 6).

#### B.2.5 — arch / rugarch alpha-vs-gamma EGARCH naming swap (S6)

**Source:** Python `arch.arch_model` (EGARCH) vs R `rugarch`
(eGARCH).

**Quirk:** **SWAPPED naming convention** for the magnitude vs
leverage coefficients:
- arch: `alpha[1]` = magnitude (|z_t|), `gamma[1]` = leverage
  (z_t)
- rugarch: `gamma1` = magnitude (|z_t|), `alpha1` = leverage
  (z_t)

The economic role is the same; only the name is swapped.

**Resolution:** In the parity check's compare(), swap names on
the rugarch side so the comparison aligns by economic role,
not raw name.

**Detected in:** `p3_egarch` audit (Session 6).

### B.3 — Normalization-convention divergence (alignment-via-metric)

#### B.3.1 — scipy / astropy Lomb-Scargle normalization (S11)

**Source:** Python `scipy.signal.lombscargle(normalize=True)` vs
`astropy.timeseries.LombScargle(normalization='standard')`.

**Quirk:** Different power normalization conventions:
- scipy: returns power in [0, 1] range using inverse-variance
  scaling (Lomb 1976 / Scargle 1982)
- astropy: standard normalization (Townsend 2010 generalized LS)

Absolute power values differ expectedly (~1e-3 on identical
input).

**Resolution:** **Alignment-via-metric** — compare peak-frequency
LOCATION (normalization-invariant) rather than absolute power
values. Both implementations identify the same dominant frequency
bin against the same frequency grid; bit-exact peak-bin index
match.

**Detected in:** `p3_lomb_scargle` audit (Session 11).

### B.4 — Version-default drift

#### B.4.1 — xgboost tree_method default flip (S12)

**Source:** Python `xgboost.XGBRegressor`.

**Quirk:** Default `tree_method` has flipped across major
versions:
- xgboost < 1.0: default `'exact'`
- xgboost 1.0+: default `'auto'` (resolves to `'hist'` on most
  platforms)
- xgboost 2.0+: default `'hist'` explicit

Reproducibility breaks if the parity reference relies on the
implicit default.

**Resolution:** Pin `tree_method='hist'` explicitly on both
TSL and reference sides. Combine with `n_jobs=1` for thread
determinism and `random_state=N` for reproducibility.

**Detected in:** `p3_xgboost` audit (Session 12).

#### B.4.2 — lightgbm parameter case sensitivity (S12)

**Source:** Python `lightgbm.LGBMRegressor`.

**Quirk:** Legacy LightGBM C-API parameter names use camelCase
(`numLeaves`, `maxDepth`); the sklearn-API wrapper expects
snake_case (`num_leaves`, `max_depth`). Mixing in a single call
is silently accepted but only some parameters are recognized —
invisible bug surface where a typo'd parameter is silently
ignored and the default is used.

**Resolution:** Always use snake_case via the sklearn API.
Combine with `deterministic=True` + `force_col_wise=True` +
`n_jobs=1` for full reproducibility.

**Detected in:** `p3_lightgbm` audit (Session 12).

#### B.4.3 — CRAN-vs-R-runtime version representation (Phase 3.5 Session 5)

**Source:** R packaging convention vs `packageVersion()`
rendering. Encountered with `robustbase` and `dtw` during the
Phase 3.5 Session 5 first quarterly re-pin cycle.

**Quirk:** CRAN releases R packages with hyphen-suffix versions
for sub-patch revisions:

```
robustbase: 0.99-7
dtw:        1.23-2
```

When R loads the package, `packageVersion()` renders the same
versions in dot-format:

```
> packageVersion("robustbase")
[1] '0.99.7'
> packageVersion("dtw")
[1] '1.23.2'
```

Both representations refer to **bit-identical package code**;
only the string representation differs. The TSL harness's
`--check-environment` reports the manifest pin (CRAN format)
against `packageVersion()` (dot format), surfacing the
cosmetic mismatch as "divergence":

```
R divergences:
  robustbase: pinned=0.99-7 actual=0.99.7
  dtw: pinned=1.23-2 actual=1.23.2
```

**Resolution:** TSL manifest pins use the **dot-format that
matches `packageVersion()` output**. This keeps
`--check-environment` clean (no spurious divergence reports)
without requiring custom normalization code in the harness.

**Why not normalize in the harness?** A custom normalizer
would either accept both formats (silently masking real
version drift if a package's hyphen position shifted) OR
require maintaining a per-package format-rule table (high
maintenance cost for a cosmetic finding). The pin-format
convention is simpler and explicit.

**Detected in:** `MANIFEST.toml` re-pin at Phase 3.5 Session
5 (commit `7620a35`). Pre-S5 had hyphen-format pins for
`robustbase` and `dtw`; S5 normalized to dot-format alongside
the actual minor-version updates (PyWavelets 1.8.0 → 1.9.0,
forecastHybrid 5.0.19 → 5.1.21).

**Severity:** cosmetic; documented to prevent contributors
from confusing format-only differences with actual version
drift, AND to lock the dot-format convention for future
manifest updates.

### B.5 — Framework-incompatibility / wrapper-mismatch (Session 13 additions)

#### B.5.1 — neuralforecast 0.1.0 + pytorch-lightning incompatibility on Python 3.14 (S13)

**Source:** Python `neuralforecast` 0.1.0 (the only version pip
will install on Python 3.14 + current pytorch-lightning
2.6.1).

**Quirk:** Import fails with
`AttributeError: module 'pytorch_lightning.utilities' has no
attribute 'distributed'`. neuralforecast 0.1.0 was written
against pytorch-lightning < 2.0, which had a
`pl.utilities.distributed` namespace; newer pytorch-lightning
removed it.

**Resolution:** Use direct PyTorch self-parity for NBEATS /
NHITS parity tests. TSL's wrappers (`nbeats_forecast.py` /
`nhits_forecast.py`) already use direct `torch.nn` (NOT
neuralforecast), so this is a clean fit. The "self-parity"
here means TSL's torch.nn architecture vs an inline
reproduction of the same architecture in the check module.

**Detected in:** `p3_nbeats`, `p3_nhits` audits (Session 13).

#### B.5.2 — Master-plan-stated reference vs actual TSL backend mismatch (S13)

**Source:** `engine/techniques/gaussian_process_forecast.py`.

**Quirk:** Master plan §15.11 named GPyTorch as the reference
implementation; TSL wrapper actually uses
`sklearn.gaussian_process.GaussianProcessRegressor` (NOT
GPyTorch). Cross-package GPyTorch comparison would test
something different than what TSL ships.

**Resolution:** Always read the actual wrapper imports before
fixing the reference. Align reference to actual TSL backend.
This catches a class of wrapper-naming-vs-implementation
drift bugs (similar to `p3_quantile_regression` Session 12,
where master plan named statsmodels QR but TSL uses sklearn
GBR with quantile loss).

**Detected in:** `p3_gp` audit (Session 13). Same pattern in
`p3_quantile_regression` (Session 12).

#### B.5.3 — PyTorch state isolation via in-test seed reset (S13)

**Source:** `harness/checks/p3_lstm_gru.py` (and 4 other
torch-based checks in Batch 9).

**Quirk:** PyBridge `isolate=True` subprocess spawn adds
~300-500ms per check. For 5 PyTorch wrappers that's 1.5-2.5s
of pure subprocess overhead — and PyBridge `isolate=False`
shim was retired this session (0/14 usage in Batches 7+8).

**Resolution:** Use in-test seed reset at the start of each
TSL/reference fit/predict — call `_seed_torch(seed)` to set
torch + numpy + random + cuDNN deterministic flag IMMEDIATELY
BEFORE model instantiation (so weight initialization is
reproducible). Both arms share this discipline; same-process
state leak is benign because both arms reset before use.

**Bit-exact result:** all 5 PyTorch checks (LSTM/GRU, TCN,
NBEATS, NHITS, autoencoder) achieved 0.0 abs diff with this
in-test seed-reset pattern. PyTorch + cuDNN deterministic
flag + manual_seed at start of fit gives full reproducibility
without subprocess isolation.

**Detected in:** All 5 PyTorch checks (Session 13).

### B.6 — Master plan §15.12 reference adjustments (Session 14 final-batch additions)

#### B.6.1 — R TSA::arimax xtransf form mismatch (S14)

**Source:** R `TSA::arimax` (TSA 1.3.1).

**Quirk:** Master plan §15.12 named `R TSA::arimax` as the
reference for `transfer_function.py`. TSA::arimax has a
transfer-function form with `xtransf` that requires explicit
numerator/denominator polynomials — useful for ARMAX
modeling, but not directly aligned with TSL's simple
distributed-lag (FDL) OLS implementation. Cross-package
parity would test something different than what TSL ships.

**Resolution:** Use from-scratch self-parity reference
(numpy lstsq on lag-feature design matrix) that mirrors
TSL's distributed-lag math verbatim. Same pattern as
`p3_quantile_regression` (S12) and `p3_gp` (S13) where
master-plan-stated reference doesn't match TSL's actual
backend.

**Detected in:** `p3_transfer_function` audit (Session 14).

#### B.6.2 — R seasonal binary unavailable on Windows CI (S14)

**Source:** R `seasonal` package + X-13ARIMA-SEATS binary.

**Quirk:** R `seasonal::seas` wraps the X-13 binary
distributed by the US Census Bureau. Installation requires
separate binary download + PATH configuration. CI runners
(both Windows and Linux GitHub-hosted) typically lack this
binary unless explicitly provisioned. `install.packages("seasonal")`
succeeds but the package is non-functional without the
X-13 binary on PATH.

**Resolution:** Implement SKIP-graceful: catch
`statsmodels.tsa.x13.X13NotFoundError` in the check's
`run_tsl`, re-raise as `ImportError`. Harness runner extended
this session to translate `ImportError` from `run_tsl` into a
SKIP outcome (was previously only handled in `run_reference`).
Generalizes the "missing-dependency = SKIP" discipline.

**Pattern:** any wrapper whose Python or R reference depends
on a host binary (X-13, custom CLI tools, R packages with
binary deps) should follow this convention. The check is
runtime-graceful: SKIPs informatively rather than failing.

**Detected in:** `p3_x13` audit (Session 14).

#### B.6.3 — statsmodels ↔ x13ashtml integration deferred (Phase 3.5 Session 6)

**Source:** Python `statsmodels.tsa.x13.x13_arima_analysis` +
R `x13binary` package's bundled `x13ashtml` binary.

**Quirk:** statsmodels' `x13_arima_analysis` expects the
classic `x13as` binary's output convention — a temp prefix
with `.err` / `.lkr` / `.txt` / `.acm` / `.rcm` / `.tdf`
output files at known locations. The R `x13binary` package
ships `x13ashtml` (HTML-aware build of X-13ARIMA-SEATS) which
writes outputs to a different location (or under different
naming) than statsmodels expects. R `seasonal` accepts the
HTML build; statsmodels does not.

**Concrete error trace** (Phase 3.5 Session 6 WIP-3 CI run on
Linux runner with x13binary binary symlinked as `x13as`):

```
Fixture file missing: [Errno 2] No such file or directory:
'/tmp/tmpbdv0xoyv.err'
```

The binary itself **runs correctly** (verified via R
`seasonal` which uses the same binary and would PASS its
parity check). The integration mismatch is upstream
between statsmodels and x13ashtml output convention, NOT a
TSL wrapper bug.

**Resolution at Phase 3.5 Session 6:** **DEFERRED to Phase 4**
per Session 6.5 escalation criterion #3 (three install
attempts produced three different failure modes — signal of
platform incompatibility):
- WIP-1: Rscript path hardcoded to Windows (5/6 R-using
  checks SKIP) → fixed by [§6.2.1 cross-platform Rscript
  protocol](parity_standard.md#621-cross-platform-rscript-resolution-protocol-phase-35-session-6).
- WIP-2: `x13path()` output type misread (treated as binary
  file when it's a directory).
- WIP-3: x13ashtml-vs-statsmodels output convention mismatch
  (binary runs, but `.err` file missing where statsmodels
  expects).

**Workaround scaffolding preserved** in
`.github/workflows/parity-slow.yml` for Phase 4 forward use:

```yaml
# x13binary install (R seasonal works with this binary)
- name: Install full manifest R packages + X-13 binary
  run: install.packages(c(..., "x13binary", "seasonal"), ...)

# Symlink x13ashtml -> x13as (preserved; documentation only)
- name: Resolve X-13 binary path (documentation only)
  run: |
    X13_DIR=$(Rscript -e 'cat(x13binary::x13path())')
    if [ -f "$X13_DIR/x13ashtml" ] && [ ! -e "$X13_DIR/x13as" ]; then
      ln -s x13ashtml "$X13_DIR/x13as"
    fi
    # X13PATH/X12PATH NOT exported (Phase 3.5 S6.5 deferral)
    # statsmodels then raises X13NotFoundError -> harness SKIP
```

**Outcome:** `p3_x13` SKIPs gracefully on **both** platforms
post-Phase-3.5:
- Windows: binary not on system PATH → SKIP (unchanged).
- Linux: binary present but X13PATH deliberately not
  exported → SKIP (forward-compatible with Phase 4 fix).

**Phase 4 candidates** (NOT actioned at Phase 3.5):
- Patch `engine/techniques/x13_seasonal_adjust.py` to handle
  x13ashtml output convention directly (bypass statsmodels'
  `x13_arima_analysis` abstraction).
- Pin a statsmodels patch / branch that handles x13ashtml
  output correctly.
- Add a TSL-side post-process that normalizes x13ashtml
  output to the format statsmodels expects.

**Pattern:** even when both TSL and the reference invoke
the same upstream binary (Pattern A.1 same-library),
differences in **binary build variants** (`x13as` vs
`x13ashtml`) can produce different output file conventions.
This is distinct from R-package version drift (§B.4) and
distinct from output-name divergence (§B.5) — it's a
**binary-build-variant integration** quirk that emerges only
when the Python and R wrappers consume different binary
builds of the same source code.

---

#### B.6.4 — R `bvars` package install fragility on R 4.5.3 (Phase 4 Session 11a)

**Source:** R `bvars` package (Bayesian VAR with stochastic
volatility — would have been a candidate Pattern A.2
secondary reference for TSL's BVAR-SV wrapper).

**Quirk:** the `bvars` CRAN package failed to install on
R 4.5.3 across multiple Phase 3 + Phase 4 install attempts
on this development machine and on CI runners. Specifically,
`install.packages("bvars")` returns successfully but the
subsequent `library(bvars)` raises a namespace-load error
indicating a compiled-binary / system-library mismatch
incompatible with R 4.5.x ABI changes. The package's CRAN
maintenance has been intermittent; build artifacts for
recent R versions are not reliably available.

**Operational impact:** at Phase 4 Session 5, the BVAR-SV
constant-volatility cross-check (BYF candidate #1) needed
a Pattern A.2 secondary reference. `bvars` was the natural
candidate (BVAR with shared methodological lineage to TSL's
CCM-2019 sampler). With `bvars` unavailable, the audit
fell back to R `BVAR::bvar()` (Kuschnig & Vashold 2021,
JSS) which has a different prior parameterization and
therefore produces methodologically-divergent posterior
draws. This contributed to the Phase 4 S5 audit landing as
PASS-A.2 with **DOCUMENTED-DIVERGENCE** outcome rather
than a clean bit-exact comparison.

**Recommended fallback hierarchy** for future BVAR-family
audits needing a Pattern A.2 secondary reference:

1. R `bvars` if it becomes available for the current R
   release (check via `available.packages("bvars")` in
   R; verify subsequent `library()` succeeds).
2. R `BVAR` (Kuschnig & Vashold 2021) — note that prior
   parameterization differs from CCM-2019 conventions;
   plan for DOCUMENTED-DIVERGENCE outcome.
3. R `BMR::bvarm()` (Bayesian Macroeconometrics in R) —
   alternative; not yet evaluated for Phase 4 BVAR-SV
   parity.
4. Tier-B: paper-formula reimplementation per Banbura,
   Giannone, Reichlin 2010 specification (~250 LOC).

**Pattern:** R-package availability is a real-world
constraint on Pattern A.2 secondary-reference selection.
The audit-design phase must verify package install AND
`library()` load on the target R version BEFORE committing
to a specific reference. A reference that's "in CRAN" is
not the same as a reference that "loads on R 4.5.3 today".

**Cross-references:**
- [P-3 §3.4 Decision 3 forward-provisioning interval](parity_empirical_findings.md#34--pattern-a1-production-locked-across-4-dimensions-phase-35-v110) — the BYF Mod-2 + Phase 4 S5 verification interval surfaced this same fragility class.
- Phase 4 Session 5 findings doc: `docs/reference_parity_phase4/session_5_findings.md`.

---

### B.D — Platform-binary integration sub-pattern (Phase 3.5 v1.1.0 sub-pattern)

**Status:** New sub-pattern formalized at Phase 3.5 Session 11
based on cumulative S6 evidence. Distinct from B.1-B.6 because
the quirks below are not about the reference library's API
or numerical conventions; they're about how the host platform
exposes the reference's binary dependencies.

This sub-pattern collects 3 instances surfaced during Phase
3.5 Session 6 X-13 Linux integration work:

#### B.D.1 — R-bridge platform path resolution (Phase 3.5 S6)

**Quirk:** the harness's `RBridge` originally hardcoded the
Windows dev-machine Rscript path
(`C:/Program Files/R/R-4.5.3/bin/Rscript.exe`) via the
`MANIFEST.toml [r] rscript_exe` field. On Linux CI runners,
this path doesn't exist; every R-using check SKIPped with
"Rscript executable not found".

**Resolution** (Phase 3.5 S6): added `_resolve_rscript_exe()`
3-step fallback to `harness/r_bridge.py` — see
[P-1 §6.2.1](parity_standard.md#621-cross-platform-rscript-resolution-protocol-phase-35-session-6).

**Severity:** structural infrastructure issue. **Empirical
impact:** 5 of 6 R-using slow-tier checks went from SKIP to
PASS on the Linux runner.

#### B.D.2 — Binary naming variation (x13as / x13ashtml) (Phase 3.5 S6)

**Quirk:** the same X-13ARIMA-SEATS source code is built into
two binaries with different default names depending on build
options:
- `x13as` (classic; statsmodels expects this name)
- `x13ashtml` (HTML-aware; what `x13binary` R package ships
  on Linux/macOS)

**Resolution** (Phase 3.5 S6): symlink `x13ashtml` → `x13as`
in the X13PATH directory. See [§B.6.3](#b63--statsmodels-x13ashtml-integration-deferred-phase-35-session-6)
for the deeper output-convention mismatch that defers full
integration to Phase 4.

**Severity:** cosmetic (binary-name) but blocks discovery
without symlink. Easily fixed.

#### B.D.3 — `x13path()` directory semantics (Phase 3.5 S6)

**Quirk:** the R `x13binary::x13path()` function returns the
**bin directory** containing the binary, not the binary file
path itself. WIP-2 of Phase 3.5 S6 misread this — used
`dirname(x13path())` to walk up one level for X13PATH, which
pointed statsmodels at the parent of bin/ instead of bin/.

**Resolution** (Phase 3.5 S6 WIP-3): use `x13path()` output
directly as X13PATH; symlink `x13ashtml` → `x13as` inside.

**Severity:** documentation issue (`x13path()` doc string
doesn't make this explicit; empirical inspection of the
bin-directory listing was the diagnostic).

---

## Section C — Pattern A Taxonomy (formalized at Session 16)

**Status:** Locked at Session 16 close. Pattern A formalized
into three sub-patterns (A.1 / A.2 / A.3) based on Phase 3
empirical evidence (46 wrappers in Pattern A at Phase 3
close).

**Pattern A = "achieves bit-exact or near-machine-precision
parity"**. The sub-patterns describe *how* the bit-exactness
is established. All three sub-patterns share the operational
discipline: **0.0 abs diff or sub-1e-10 abs diff is the
acceptance bar**, with the only exceptions being subprocess
CSV roundtrip noise (~1e-14) and BLAS implementation drift.

### C.1 — Sub-pattern A.1: Same-library reproducibility verification

**Definition:** TSL wrapper invokes a single library
primitive (sklearn, xgboost, lightgbm, scipy, pywt, PyEMD,
reservoirpy, prophet, statsmodels, PyTorch, etc.). The
parity check's reference is a **direct second invocation of
the same library** with identical arguments. Both arms hit
the same C-implementation; output is bitwise-identical.

**Verifies:** wrapper-level preprocessing bugs, parameter-
resolution bugs, audit-field rounding regressions.

**Does NOT verify:** TSL-vs-canonical-implementation
methodology bugs.

**18 wrappers in Phase 3** (locked at Batch 9 close, S13):

| Batch | Wrappers |
|---|---|
| 6 | `p3_pelt` |
| 7 | `p3_periodogram`, `p3_wavelet_transform` |
| 8 | `p3_random_forest`, `p3_gradient_boosting`, `p3_xgboost`, `p3_lightgbm`, `p3_svr`, `p3_quantile_regression` |
| 9 | `p3_lstm_gru`, `p3_tcn`, `p3_nbeats`, `p3_nhits`, `p3_autoencoder`, `p3_esn`, `p3_gp`, `p3_prophet` |
| 10 | `p3_loess` |

**All 18 achieved exactly 0.0 abs diff.**

**P-1 §10.1 designates A.1 as the operational default for
new Python wrappers.** When the wrapper invokes a single
trusted library, A.1 is the path of least resistance — no
need to invent a cross-package reference when the wrapper is
a UX surface around the canonical implementation.

### C.2 — Sub-pattern A.2: Cross-package bit-exact

**Definition:** TSL and reference are **independent
implementations** of the same algorithm, but both implement
identical math (closed-form arithmetic, no optimization, no
randomness). Cross-package comparison achieves machine
precision (~1e-13 to 1e-16 abs).

**Verifies:** algorithm-level correctness across two
independent implementations.

**~12 wrappers in Phase 3:**

- `p3_intermittent` (S3; statsmodels vs R `forecast::croston`
  — 3.77e-15 abs)
- `p3_classical_decompose` (S4; statsmodels vs R
  `stats::decompose` — 7.11e-14)
- `p3_har_rv` (S6; numpy lstsq vs R `lm()` — 8.88e-16)
- `p3_var` (S7; statsmodels vs R `vars::VAR` — 7.22e-16)
- `p3_vecm` (S7; statsmodels vs R urca::ca.jo — 9.99e-16
  after sign normalization)
- `p3_pca` (S7; numpy eigh vs sklearn PCA — 7.99e-15)
- `p3_adf`, `p3_kpss` (S10; statsmodels vs R urca; 1e-14
  range)
- `p3_fft_spectrum` (S11; scipy.fft vs numpy.fft — 2.84e-14)
- `p3_dtw` (S14; numpy reference vs dtaidistance — 0.0)
- `p3_denton_chowlin` (S14; numpy KKT solve vs R tempdisagg
  — 6.39e-14)
- `p3_robust_estimators` (S12; scipy/numpy vs R robustbase
  — 4.22e-15)
- `p3_granger` (S14; statsmodels vs R lmtest — 8.53e-14)
- `p3_ccf` (S14; statsmodels.ccf vs R stats::ccf — 1.33e-15)

### C.3 — Sub-pattern A.3: Self-parity / paper-formula reimplementation

**Definition:** No installable reference exists OR the
candidate references implement different math. The reference
is a **from-scratch reimplementation of the algorithm
directly from the paper**, inline in the check module
(typically 30-80 LOC). The reimpl mirrors TSL's recursion
verbatim; both arms execute the same paper formula.

**Verifies:** wrapper-level regressions. Same scope as A.1.

**Does NOT verify:** TSL-vs-canonical-implementation
methodology bugs (mitigation: audit report MUST cite paper /
formula source for independent reviewer cross-check).

**~10 wrappers in Phase 3:**

- `p3_bocpd` (S10; Adams-MacKay 2007 NIG-conjugate
  recursion)
- `p3_cusum_page_hinkley` (S10; identical recursion)
- `p3_stl_esd` (S10; statsmodels STL + Rosner 1983 GESD)
- `p3_wavelet_coherence` (S11; pywt CWT + scipy smoothing)
- `p3_ssa` (S11; Golyandina-Zhigljavsky 2013 SVD-on-Hankel)
- `p3_gcc_phat` (S14; Knapp-Carter 1976)
- `p3_transfer_function` (S14; distributed-lag OLS)
- `p3_block_bootstrap` (S14; moving-block sampler with seed
  pinning)
- `p3_forecast_combination` (S14; inverse-MSE weighted mean)
- `p3_rolling_origin_cv` (S14; expanding-window loop)
- `p3_conformal` (S13; split-conformal qhat formula)

### C.4 — Pattern K → Pattern A path (sub-pattern A.3 special case)

**Definition:** The wrapper was originally a Pattern K
(NO-REFERENCE) candidate because no canonical CRAN/PyPI
package implemented matching math. Resolution: sub-pattern
A.3 reimplementation that mirrors TSL's recursion verbatim
PROMOTES the verdict from CAVEAT (Pattern K) to PASS
(Pattern A.3).

**5 wrappers in Phase 3** followed this promotion path:

- `p3_bocpd` (PyPI bocd package uses non-conjugate Gaussian
  prior — would not match TSL's NIG conjugate)
- `p3_cusum_page_hinkley` (R cpm/changepoint use different
  formulations)
- `p3_stl_esd` (Twitter AnomalyDetection R archived from
  CRAN; no successor)
- `p3_wavelet_coherence` (R biwavelet uses Liu-Liang-
  Weisberg 2007 + Monte Carlo significance — different
  methodology)
- `p3_ssa` (pyts SSA expects sklearn-API per-row input;
  doesn't fit 1-D series test)

**Documentation discipline:** the audit report explicitly
documents the regression-sentinel scope ("catches wrapper-
level regressions; does NOT catch TSL-vs-canonical-
implementation methodology bugs") and cites the paper /
formula source.

### C.5 — Selecting a sub-pattern for new wrappers

Decision tree:

1. **Does TSL invoke a single trusted library primitive
   (sklearn, scipy, pywt, etc.)?** → A.1 same-library
   self-test (P-1 §10.1 default)
2. **Is there an installable canonical reference (R or
   Python) implementing identical math?** → A.2 cross-
   package bit-exact
3. **Neither (1) nor (2)?** → A.3 paper-formula
   reimplementation. Pattern K candidates promote here when
   the paper formula is reproducible.

If none of A.1/A.2/A.3 fits, the wrapper falls outside
Pattern A — see verdict_class taxonomy in Section A.

---

## Section D — Pattern F structural-invariants registry

See `tools/reference_parity/harness/structural_invariants.py`.
14 concrete invariants populated as of Session 13 close:

| Invariant | Wrapper class | Populated at |
|---|---|---|
| `garch_persistence` | GARCH family | Session 6 |
| `garch_conditional_variance` | GARCH family | Session 6 |
| `var_eigenvalues` | VAR | Session 7 |
| `vecm_cointegration_rank` | VECM | Session 7 |
| `kalman_covariance_ordering` | Kalman family | Session 9 |
| `kalman_innovation_positivity` | Kalman family | Session 9 |
| `hmm_row_sums` | HMM | Session 8 |
| `hmm_emission_normalization` | HMM | Session 8 |
| `fft_roundtrip` | FFT family | Session 11 |
| `fft_energy_conservation` | FFT family | Session 11 |
| `wavelet_inverse_roundtrip` | Wavelet family | Session 11 |
| `wavelet_energy_conservation` | Wavelet family | Session 11 |
| `conformal_nominal_coverage` | Conformal | **Session 13** |
| `conformal_interval_containment` | Conformal | **Session 13** |

Future populations: bootstrap (deferred — Batch 10 used self-
parity at 0.0 abs, no invariant population needed),
decomposition (open).

### D.1 — Pattern F invariant playbook (new wrapper authoring)

When adding a parity check that should declare structural
invariants, follow this playbook:

#### Step 1 — Identify the invariant class

Match the wrapper's algorithm class against the registered
invariant types:

| Algorithm class | Registered invariants | Reference |
|---|---|---|
| GARCH family (sGARCH, GJR, EGARCH) | `garch_persistence`, `garch_conditional_variance` | S6 populations |
| VAR / VECM | `var_eigenvalues`, `vecm_cointegration_rank` | S7 populations |
| Kalman family (local-level, LLT, structural-TS, kalman-imputation) | `kalman_covariance_ordering`, `kalman_innovation_positivity` | S9 populations |
| HMM / Markov switching | `hmm_row_sums`, `hmm_emission_normalization` | S8 populations |
| FFT family | `fft_roundtrip`, `fft_energy_conservation` | S11 populations |
| Wavelet family | `wavelet_inverse_roundtrip`, `wavelet_energy_conservation` | S11 populations |
| Conformal prediction | `conformal_nominal_coverage`, `conformal_interval_containment` | S13 populations |

If the wrapper's class doesn't match any registered type but
has natural structural invariants (e.g., bootstrap with
distributional centering, decomposition with sum-to-y), add
a NEW invariant type to `harness/structural_invariants.py`
following the pattern of existing populated checkers.

#### Step 2 — Declare the invariant on the check class

```python
from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
)

class FutureGarchVariantParity(P3ParityCheck):
    technique_id = "p3_future_garch"
    verdict_class = "mle_fit"
    structural_invariants = (
        StructuralInvariant(
            name="conditional_variance_positivity",
            invariant_type="garch_conditional_variance",
            tolerance=0.0,
            tolerance_type="absolute",
        ),
        StructuralInvariant(
            name="persistence_below_one",
            invariant_type="garch_persistence",
            tolerance=1e-3,  # near-IGARCH boundary slack
            tolerance_type="relative",
        ),
    )
```

#### Step 3 — Output dict shape requirements

Each registered invariant checker reads specific keys from
the TSL output dict. The check's `run_tsl` must populate
those keys:

| Invariant | Required TSL output keys |
|---|---|
| `garch_conditional_variance` | `conditional_variance` (1-D ndarray) |
| `garch_persistence` | `persistence` (scalar) |
| `var_eigenvalues` | `companion_eig_magnitudes` (1-D ndarray) |
| `vecm_cointegration_rank` | `cointegrating_rank` (int; on both TSL and ref) |
| `kalman_covariance_ordering` | `filtered_state_cov`, `predicted_state_cov` (3-D arrays); optional `smoothed_state_cov` |
| `kalman_innovation_positivity` | `innovation_variance` (1-D or 2-D) |
| `hmm_row_sums` | `transition_matrix` (2-D, n_states × n_states) |
| `hmm_emission_normalization` | `emission_means`, `emission_covars` |
| `fft_roundtrip` | `roundtrip_max_abs` (scalar) |
| `fft_energy_conservation` | `energy_time`, `energy_freq` (scalars) |
| `wavelet_inverse_roundtrip` | `roundtrip_max_abs` (scalar) |
| `wavelet_energy_conservation` | `signal_energy`, `coeff_energy` (scalars) |
| `conformal_nominal_coverage` | `coverage`, `alpha` (scalars) |
| `conformal_interval_containment` | `lower`, `upper` (1-D arrays) |

#### Step 4 — Verdict propagation

Per [P-1 §3.3](parity_standard.md#33-tier-propagation-rules),
**Diagnostic-tier (Pattern F) CAVEAT does NOT propagate to
overall outcome by default.** Invariant CAVEAT is reported
in the metrics dict for audit-trail visibility. The check
author may opt-in to propagation if the invariant carries
hard-fail semantics.

### D.2 — Pattern F wavelet-mode interaction (banked Item #18)

**Empirical finding (S11):** wavelet energy conservation
holds at machine precision **only under
`mode='periodization'`** with power-of-2 signal lengths for
orthogonal wavelet families (db4, sym4, coif*).

Other modes break Parseval:

- `'symmetric'` (default): boundary samples duplicated; energy
  inflated by O(boundary_extension_size)
- `'zero'`: boundary samples zeroed; energy deflated
- `'reflect'`, `'periodic'`, `'smooth'`: similar boundary
  effects

**Operational discipline for new wavelet checks:**

1. Use `mode='periodization'` in the parity test fixture
   (NOT in the TSL wrapper — the wrapper uses whatever mode
   the user requested).
2. Ensure fixture length is a power of 2.
3. Document the mode choice in the audit report.

**Empirical evidence:** `p3_wavelet_transform` (S11) failed
with mode='symmetric' (BLOCK on energy invariant); switching
to mode='periodization' resolved to PASS at 5e-16 relative
energy diff. Same fixture, only mode change.

---

## Section E — Pattern I: Sign / scale convention alignment (banked Item #1)

**Status:** Locked at Session 16 close. **Pattern I**
formalized as a comparison-side discipline: when TSL and
reference agree on a quantity *up to sign or scale* (e.g.,
SVD eigenvectors, factor loadings, eigenvector signs), the
parity check **must apply a canonicalization step on both
sides** before comparison. Failure to canonicalize produces
spurious BLOCK verdicts.

### E.1 — When Pattern I applies

Pattern I applies whenever the underlying mathematical object
is unique only up to a sign or scale ambiguity:

| Object | Ambiguity | Canonicalization |
|---|---|---|
| SVD eigenvectors (PCA, SSA, DFM loadings) | Sign: `±u` produce identical reconstructions | "Max-absolute-entry positive" rule (sklearn `svd_flip` convention) |
| Markov-switching state labels | Permutation: state 0 / state 1 are interchangeable | Label by ascending mean (lower regime first) |
| VECM cointegration vectors | Scale + sign: `λβ` produces identical cointegration relation | Normalize first element of β to 1 |
| Wavelet detail coefficients (some pywt versions) | Sign per band | TSL's `flip_sign_vector` helper (max-abs-positive) |

### E.2 — Canonicalization recipe

Apply the canonicalization **on both arms** before comparing.
Comparing one canonicalized side to a non-canonicalized
side produces guaranteed BLOCK.

**Reference implementation** (PCA example from
`harness/checks/p3_pca.py`):

```python
def _sign_canonicalize(eigenvectors: np.ndarray) -> np.ndarray:
    """Apply max-abs-value-positive sign convention per
    column. Loadings sign is arbitrary up to a flip; this
    convention removes the ambiguity for parity comparison."""
    out = eigenvectors.copy()
    for i in range(out.shape[1]):
        max_abs_idx = int(np.argmax(np.abs(out[:, i])))
        if out[max_abs_idx, i] < 0:
            out[:, i] = -out[:, i]
    return out
```

Apply to both TSL's loadings AND reference's loadings.
Recompute scores from sign-canonicalized loadings (otherwise
scores ↔ loadings consistency breaks).

### E.3 — Empirical instances in Phase 3

Pattern I was applied (mostly invisibly inside check
modules) in the following audits:

| Wrapper | Ambiguity | Resolution |
|---|---|---|
| `p3_pca` (S7) | Eigenvector sign | `_sign_canonicalize` on both arms |
| `p3_vecm` (S7) | β scale + sign | Normalize β[0] = 1 |
| `p3_markov_switching` (S8) | State label permutation | Lower-mean state first |
| `p3_ssa` (S11) | SVD U / Vt sign | sklearn `svd_flip` convention |
| `p3_wavelet_transform` (S11) | Detail-band sign (pywt versions) | `flip_sign_vector` helper |
| `p3_local_linear_trend` (S9) | LLT identifiability (sigma_eta vs sigma_zeta swap) | Pattern H DSCD; not canonicalizable, widened band |

### E.4 — When Pattern I does NOT apply

Some cases that *look* like Pattern I but are actually
different:

- **Forecast sign / value differences in independently-fit
  models:** if two forecasters produce different forecast
  signs on the same input, that's not a canonicalization
  problem — it's a bug or methodology divergence.
- **Bootstrap / MCMC sample order:** sample order is
  random; canonicalize by sorting the samples (e.g., compare
  sorted quantiles) but this is "sort canonicalization,"
  classified separately from sign/scale.

---

## Section F — DSCD diagnostic-axis registry (banked Item #4)

**Status:** Locked at Session 16 close. **DSCD = Documented
Sub-Class Divergence within MLE-fit** (first surfaced at
S6, sub-taxonomy locked at S9). Tracks wrapper instances
where TSL backend and reference converge to genuinely
different local optima of the same likelihood surface (or
identifiability-ambiguous parameter sets).

### F.1 — DSCD sub-taxonomy (locked at S9)

| Sub-class | Mechanism | Example |
|---|---|---|
| **DSCD-MLE** | Independent optimizer implementations land at different local optima of the same likelihood. Often boundary attractors or plateau regions where multiple parameter sets give nearly-equivalent likelihood. | GARCH family (rugarch boundary attractor on alpha+beta≈1) |
| **DSCD-EM** | Independent EM implementations converge to different local optima of the same EM objective. State-permutation + transition-matrix divergence patterns. | HMM (transmat 0.05-0.25 abs widening); Markov switching means at S8 |
| **DSCD-Identifiability** | Multiple parameter sets produce identical observable behavior; identifiability is mathematically weak. Not a bug — fundamental property of the model. | LLT 3-variance identifiability (sigma_eta ↔ sigma_zeta); STAR smoothness gamma at orders-of-magnitude divergence |

### F.2 — DSCD instances in Phase 3 (4 wrappers)

| Wrapper | Sub-class | Detail |
|---|---|---|
| `p3_sgarch` / `p3_gjr_garch` / `p3_egarch` (S6) | DSCD-MLE | rugarch default `solver='hybrid'` lands at alpha+beta≈1 boundary attractor on ~30% of GARCH(1,1) fixtures; arch reliably finds global optimum on same data. **Resolution:** pin rugarch `solver='gosolnp'` with `n.restarts=10`, `n.sim=2000`, `rseed=20260428` for global-optimum convergence. |
| `p3_local_linear_trend` (S9) | DSCD-Identifiability | statsmodels UC drives sigma_eta → 0.51 while KFAS drives sigma_eta → 1e-4 (with corresponding flip in sigma_zeta). Both are valid local optima of the same Kalman likelihood. **Resolution:** widened band; classified Pattern H. |
| `p3_markov_switching` (S8) | DSCD-EM | statsmodels MarkovRegression and R MSwM converge to genuinely different mean estimates on synthetic fixtures (~5e-2 abs); transition matrices diverge by 0.05. **Resolution:** widened band (2.0 abs / 1.0 rel on means). |
| `p3_star` (S8) | DSCD-Identifiability | Smoothness parameter gamma diverges by orders of magnitude (TSL gamma=1024 vs R gamma=100). Both fit acceptably on observable behavior. **Resolution:** widened gamma band (5e-1 abs / 5e-1 rel); Tier B per master plan §5. |

### F.3 — Diagnostic-axis convention

Each DSCD instance documents three axes in the audit report:

1. **Mechanism axis:** is divergence due to optimizer
   convergence (MLE) / EM iteration (EM) / identifiability
   weakness (Identifiability)?
2. **Reproducibility axis:** does the divergence reproduce
   across seed re-rolls, or is it MC noise?
3. **Resolution axis:** can the divergence be eliminated by
   pinning a solver / initial condition? (Yes for GARCH via
   gosolnp; No for LLT identifiability — fundamental.)

These three axes give future contributors a structured way
to triage new DSCD candidates: pinning solver + n_restarts
typically resolves DSCD-MLE; widening band is the right move
for DSCD-Identifiability.

### F.4 — DSCD vs Pattern J — what's the difference?

| Aspect | Pattern J (Section B) | DSCD (this section) |
|---|---|---|
| Source of divergence | Library-API quirks: parameter naming, default flips, normalization conventions | Mathematical: multiple local optima of same objective; identifiability ambiguity |
| Resolution | Align comparison logic to handle the quirk (rename, swap, alignment-via-metric) | Pin solver / n_restarts (DSCD-MLE) OR widen band (DSCD-Identifiability) |
| Verdict | PASS after alignment | PASS after band widening (often CAVEAT-class) |
| Catalog | Section B Appendix entries | Section F sub-taxonomy + per-instance audit-report documentation |

---

## Section G — Pattern J resolution sub-patterns (banked Item #11)

**Status:** Formalized at Session 16 close. Pattern J
(reference-library quirks, see Section B catalog) admits
**three distinct resolution sub-patterns** based on Phase 3
empirical evidence (3 concrete instances, S6 / S10 / S11).
This section formalizes the resolution typology so future
contributors can match a new quirk against the right
resolution pattern.

### G.1 — Resolution Pattern J.A: Name-mapping in compare()

**When:** the two implementations agree on the math but use
different *names* for the same economic role (e.g., arch's
`alpha` vs rugarch's `gamma1` for EGARCH magnitude).

**Resolution:** swap names on one side in the check's
`compare()` method. The compare logic explicitly maps
`tsl["alpha"]` ↔ `ref["gamma1"]` based on the documented
naming-swap.

**Empirical instance:**

- **B.2.5** arch / rugarch alpha-vs-gamma EGARCH naming
  swap (S6) — resolved by name-mapping in
  `harness/checks/p3_egarch.py`.

### G.2 — Resolution Pattern J.B: Tolerance widening

**When:** the two implementations agree on the math but
have internal default-divergence (e.g., HAC kernel weights,
numerical-conditioning paths). Output values agree to a
*specific* tolerance band that's wider than the
canonical-class band.

**Resolution:** widen the tolerance ladder entry
specifically for that wrapper, with audit-report
justification documenting the source of the widening.

**Empirical instance:**

- **B.2.1** arch / urca PP HAC kernel divergence (S10) —
  widened from machine-precision floor to 1e-3 abs / 1e-2
  rel.

### G.3 — Resolution Pattern J.C: Alignment-via-metric

**When:** the two implementations agree on the math but
use different output *normalizations* / *scales*. Absolute
output values differ by a multiplicative factor; the
*shape* / *peak location* of the output is invariant under
the scale difference.

**Resolution:** select a comparison metric that's invariant
under the normalization (peak-location index instead of
absolute peak power; sign-invariant correlation instead of
absolute coefficient values).

**Empirical instance:**

- **B.3.1** scipy / astropy Lomb-Scargle normalization
  (S11) — resolved by comparing peak-frequency LOCATION
  (normalization-invariant) instead of absolute peak power.

### G.4 — Selecting a resolution pattern for new Pattern J quirks

Decision tree:

1. **Is the quirk a naming difference (different parameter
   names for the same role)?** → Pattern J.A name-mapping
2. **Is the quirk an internal-default that produces
   small-magnitude output drift?** → Pattern J.B tolerance
   widening
3. **Is the quirk a normalization / scale convention?** →
   Pattern J.C alignment-via-metric

If none fits, document the new resolution sub-pattern
candidate at Section G when it surfaces a third time.

---

## Section H — Document maintenance + change log

This document is **descriptive** — it captures what we
learned. The directive equivalent is
[P-1 parity standard](parity_standard.md). When directive
guidance is needed, P-1 wins; this document explains the
empirical foundation for the directive.

### H.1 — Update protocol

Living document. Updates happen as new patterns surface in
post-Phase-3 audits:

1. New Pattern J entry surfaces → append to Section B with
   a new B.x.y sub-section.
2. New verdict_class candidate locks → update Section A.
3. New structural invariant populated → update Section D.
4. New DSCD instance → update Section F.
5. New Pattern J resolution sub-pattern (third concrete
   instance) → formalize a new G.x sub-section.

### H.2 — Change log

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | 2026-04-29 | Claude Code (S12) | Section B Pattern J catalog launched (B.1-B.4). |
| 0.2.0 | 2026-04-29 | Claude Code (S13) | Section B extended with B.5 framework-incompatibility entries; Section D structural-invariants registry table populated (12 entries). |
| 0.3.0 | 2026-04-29 | Claude Code (S14) | Section B extended with B.6 master-plan-reference adjustments; Section D extended to 14 invariants. |
| 1.0.0 | 2026-04-29 | Claude Code (S16) | Section A tolerance class taxonomy locked (11 classes); Section C Pattern A taxonomy formalized (A.1/A.2/A.3 sub-patterns); Section D extended with invariant playbook + wavelet-mode interaction; Section E Pattern I sign/scale (Item #1); Section F DSCD diagnostic-axis registry (Item #4); Section G Pattern J resolution sub-patterns (Item #11). All banked Items #1, #4, #11, #18, #20 closed at this version. |
| **1.1.0** | **2026-04-30** | **Claude Code (Phase 3.5 Session 11)** | **Phase 3.5 cycle close amendments:** (A.6) `em_stochastic` per-metric tier docs added for `p3_hmm` + `p3_markov_switching` (Phase 3.5 S4 implementation; 4 + 3 metric tables); Pattern H per-metric finding added (DSCD is metric-specific, not wrapper-wide). (A.10) `single_impl_mle` production-locked at 1e-5 abs / 1e-4 rel band (was candidate); promotion criteria + `p3_vecm` migration evidence documented. (A.11) `optimizer_divergent_mle` candidate banked status preserved (no Phase 3 / 3.5 wrapper exhibits opposite-direction headroom). (A.12) decision-tree updated with [A.10] cross-reference. (B header) Pattern J catalog scoping rule added — J entries describe reference-library quirks, NOT TSL wrapper defects (→ Phase 4) / fixture conventions (→ tools docs) / applied empirical findings (→ product backlogs); 3 re-banking decisions from Phase 3.5 S9 codified. (B.4.3 NEW) CRAN-vs-R-runtime version representation (Phase 3.5 S5; hyphen-format → dot-format pin convention). (B.6.3 NEW) statsmodels-x13ashtml integration deferred to Phase 4 (Phase 3.5 S6 escalation criterion #3 — 3 distinct failure modes; SKIP-graceful preserved both platforms; Phase 4 paths documented). (B.D NEW sub-pattern) platform-binary integration: B.D.1 R-bridge platform path resolution; B.D.2 binary naming variation x13as / x13ashtml; B.D.3 x13path() directory semantics. |

---

**End of Parity Diagnostic Reference P-2 v1.1.0.**
