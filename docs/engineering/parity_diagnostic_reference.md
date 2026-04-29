# TSL Parity Diagnostic Reference (P-2)

**Status:** Living document. Spec for parity-harness diagnostic
patterns and reference-library quirks accumulated across Phase 3
batches.

This document captures **lessons learned** from Phase 3 reference
parity audits — patterns of cross-implementation divergence that
recur often enough to deserve documentation, with concrete
resolution recipes. Future contributors building parity checks for
new wrappers should consult this reference to anticipate quirks
and align tolerances + comparison logic accordingly.

Authoritative status: this document supersedes ad-hoc per-batch
notes once a pattern recurs across 3+ wrappers.

---

## Section A — Tolerance class taxonomy

(Deferred to Session 14 / check-in 2 triage. The tolerance ladder
in `tools/reference_parity/harness/tolerances.py` is currently the
authoritative ladder for Phase 3.)

---

## Section B — Pattern J Reference-Library Quirks Catalog

**Started:** 2026-04-29 (Phase 3 Session 12, Batch 8 entry close,
per check-in 1.5 act-now decision #1).

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

---

## Section C — Pattern A taxonomy (formalization deferred)

(Same-library self-test, closed-form bit-exact, recursion-self-
parity, Pattern K → A path. Empirically locked at 27 wrappers as
of Batch 8 close. Formalize at Session 25 / P-2 close.)

---

## Section D — Pattern F structural-invariants registry

See `tools/reference_parity/harness/structural_invariants.py`.
12 concrete invariants populated as of Session 12 close:

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

Future populations: bootstrap (Batch 10), conformal (Batch 9),
decomposition (open).
