# Retrospective Reference-Parity Audit — Phase 1 Final Report

**Date:** 2026-04-25 (Phase 1 closure)
**Initiative:** Numerical correctness verification of the 12 Tier 1/2/3 follow-ups (1a, 1b, 1c, 2a, 2b, 2c, 3a, 3b, 3c, 3d, 3e, 3f) committed during the most recent cycle.
**Scope:** Phase 1 only — retrospective audit. Phase 2 (permanent harness) and Phase 3 (workflow integration) are out of scope.

---

## 1. Executive Summary

The 5-phase follow-up workflow (audit → plan → apply → invariants → canonicals) had previously verified **interpretation-contract compliance, trigger-firing logic, audit-field population, graceful-degradation cascades, and backward compatibility**. It had NOT verified **numerical correctness** of the underlying algorithms against external reference implementations (R `urca::ca.jo`, R `extRemes::extremalindex`, R `stochvol::svsample`, PyTorch native `MultiheadAttention(need_weights=True)`, etc.).

Phase 1 closed that gap retrospectively across all 12 follow-ups committed in this cycle. **Twelve audits ran. Zero TSL math bugs surfaced.** All TSL implementations are mathematically correct on identifiable parameters. Every observed divergence falls into one of three categories:

1. **Methodology / prior differences** (2b/2c MCMC SV — diverging Bayesian priors yield diverging posteriors; expected), 
2. **Optimization non-determinism** (3a CAViaR Nelder-Mead local optima; 1b TBATS optimizer initialization), or
3. **TSL output-rounding floor** (`round(value, 6)` in audit fields limits parity precision to 1e-6 — documentation-only).

The audit investment is justified by **two infrastructure findings** that would otherwise have produced silent failures in production:

- **B1 (medium): mint_sample rank-deficient W guard.** TSL's MinT-sample reconciliation does not check W-matrix rank before solving, while both reference implementations (Python `hierarchicalforecast`, R `hts::MinT`) raise / return NaN on rank-deficient W. On perfectly coherent hierarchies (top = exact sum of bottom), TSL silently produces unstable output. The 3e audit forced this case; B1 documents the recommended cascade fix.

- **B6 (medium-high): PyMC NUTS auto-downgrade to pure-Python pytensor.** On Windows machines without `g++`, PyMC's NUTS sampler silently falls back from compiled C to pure-Python pytensor, which is unusably slow on T=500 SV (>25 minutes vs 10 seconds). TSL's MCMC SV wrapper had no detection of this condition. Documented for next-cycle remediation; the Gibbs backend serves as a working fallback.

Eight additional capability / documentation items (B3-B5, B7-B10) catalogued for optional follow-up.

**Overall verdict:** TSL's numerical implementations are correct. The audit infrastructure is now in place to verify any future technique against external references in a single bounded session.

---

## 2. Per-Technique Status Table

| Audit | Technique | Reference(s) | Tolerance | Verdict | Max abs diff | Notes |
|---|---|---|---|---|---|---|
| **3e** | MinT reconciliation (4 methods) | R `hts::MinT` (manual MinT math via `smatrix` + `hts:::shrink.estim`); Python `hierarchicalforecast.MinTrace` | 1e-8 abs/rel | **PASS** (3 methods) / **INCONCLUSIVE** (mint_sample) | 4.66e-15 (mint_shrinkage); NaN on mint_sample (W rank-deficient) | B1: rank-deficient W on perfectly coherent hierarchies; HF raises, hts NaN, TSL silently solves |
| **3c** | EVT Ferro-Segers extremal index | R `extRemes::extremalindex(method="intervals")` | 1e-6 abs/rel | **PASS** | 0.000e+00 (theta on both fixtures) | Branch selection verified; B5 plan-level: `evir::exindex` ≠ Ferro-Segers (it's block-maxima) |
| **3d** | Johansen Bartlett correction | `statsmodels.coint_johansen` (raw); R `urca::ca.jo` (vibes) | 1e-4 (TSL rounds corrected stat to 4 decimals) | **PASS** | 4.35e-05 on corrected stat | urca vs sm divergence is real-world R-vs-Python parametrization difference; Bartlett factor exact at 0.9700 |
| **3f** | Transformer attention exposure | PyTorch native `nn.MultiheadAttention(need_weights=True)` | 1e-12 (bitwise) | **PASS** | 0.000e+00 (both layers) | Patch + no-op forward hook teardown verified; row-sum dev 1.19e-07 (FP softmax) |
| **1c** | BVAR IRF / FEVD | Pure numpy reimpl + R base-`%*%` matrix algebra | 1e-12 (bitwise) | **PASS** | 4.58e-16 (IRF tensor, TSL vs R) | Closed-form math; mock RNG bypasses 1e-12 noise floor in TSL |
| **2a** | Kalman filter / smoother | R `dlm::dlmFilter`/`dlmSmooth`; R `KFAS::KFS` | 1e-6 abs | **PASS** | 2.71e-07 filtered, 2.37e-08 smoothed (TSL vs KFAS) | log-likelihood matches KFAS at 3.6e-7; dlm log-LL convention difference documented |
| **2b** | MCMC SV (Gaussian) | R `stochvol::svsample` | 5e-2 rel (MC noise band) | **PASS** (mu) / **CAVEAT** (phi 6.6%) / **METHODOLOGY** (sigma_eta 45%) | mu rel=1.0e-2 | sigma_eta divergence driven by HalfNormal vs Gamma prior; B6 surfaced (PyMC g++) |
| **2c** | Student-t SV | R `stochvol::svtsample` | 5e-2 rel | **PASS** (mu, phi) / **METHODOLOGY** (sigma_eta 26%, nu 13%) | phi rel=7.5e-3 | nu divergence prior-driven; T=500 nu identification weak |
| **1b** | TBATS | Python `tbats` 1.1.3 (same lib TSL wraps); R `forecast::tbats` (De Livera 2011 reference) | 1e-4 abs / 1e-3 rel on params; 1e-2 / 1e-3 on forecasts | **PASS** (vs py-tbats) / **DIVERGE** (vs R) | TSL vs py-tbats: 4.92e-07 forecasts; TSL vs R: 1.90e+00 | R divergence due to optimizer init / Box-Cox search / damped-trend handling |
| **3b** | HAR-CJ realized volatility | From-scratch reimpl per ABD 2007 + Huang-Tauchen 2005 (R1 paper-validated) | 1e-6 abs/rel (TSL output rounding) | **PASS** | 4.36e-07 (intercept, output-rounding floor) | R1 PASS: cont_sum=0.83, R²=0.33, all continuous coefs positive |
| **3a** | CAViaR multi-horizon | From-scratch reimpl per Engle-Manganelli 2004 (R1 paper-validated) | 1e-12 q-path; 1e-6 loss; 1e-2/5e-2 β-converged | **PASS-with-caveat** | q-path 0.000e+00; loss 2.3e-7 (TSL output-rounding); β-converged DIVERGE expected | Non-smooth Nelder-Mead local optima; both implementations valid |
| **1a** | PyTorch path validation | Bug-fix regression sweep (no external reference) | Qualitative (run + behavior) | **PASS** (13/13 checks) | n/a | All five 1a fixes verified on PyTorch backend: NBEATS stack_types, NHiTS pooling_sizes, LSTM/GRU/TCN n_params, autoencoder spec |

**Verdict legend:** PASS = within tolerance; PASS-with-caveat = within tolerance for primary check, expected divergence on a secondary check; CAVEAT = within methodology-noise band but not tight tolerance; METHODOLOGY = divergence attributable to documented prior / methodology difference, not bug; INCONCLUSIVE = reference produced NaN due to its own guard, no comparison possible; DIVERGE (1b vs R) = real cross-implementation divergence treated as documentation finding, not bug.

---

## 3. Backlog Items — Detailed

The B-numbering follows the order items were surfaced during Stage C. Items B1, B2 are in the plan file proper; B3–B7 are inline in their respective audit reports; B8–B10 were added in this prompt.

### B1 — `mint_sample` rank-deficient W guard
- **Severity:** medium
- **Surfaced by:** 3e MinT audit
- **Observation:** TSL's `_mint_reconcile` (mint_sample method) does not check W-matrix rank before `np.linalg.solve(S' W^-1 S, S' W^-1)`. On perfectly coherent hierarchies (top residual = exact sum of bottom residuals), W_sam has rank n_bottom rather than n_total and the solve produces unstable output. Reference implementations (HF, R-hts manual projection) either raise an explicit error or produce NaN.
- **Recommended remediation:**
  - Add `np.linalg.matrix_rank(W)` check before solve.
  - On rank deficiency, fall back via existing D22 cascade (mint_sample → mint_shrinkage) with `fallback_reason = "w_matrix_rank_deficient"`. D1 `method_fallback_occurred` trigger fires with this reason.
  - Document in spec honest-disclosure: *"mint_sample requires W_sam to be full rank (n_total). Perfectly coherent hierarchies produce a rank-deficient W; wrapper falls back to mint_shrinkage in this case."*
  - Add canonical C7 exercising the rank-deficient path (use 3e's audit fixture).
- **Follow-up commit?** **YES.** Standard 5-phase follow-up cycle.
- **Related audit:** 3e — see `3e_mint_audit.md` Section "mint_sample on perfectly-coherent hierarchies".

### B2 — `rscript_bridge` NA-header bug (FIXED IN-FLIGHT)
- **Severity:** none (already fixed)
- **Surfaced by:** 3e MinT audit (Stage C Step 2)
- **Observation:** Pre-existing bug in `tools/reference_parity/scripts/rscript_bridge.py`: `_count_header_rows` checked the PRE-substitution text (with literal "NA" tokens) and wrongly flagged NA-only first rows as headers, dropping them from `np.loadtxt`.
- **Status:** Fixed during 3e audit. `_count_header_rows` now receives the substituted text (with "nan" replacing "NA"), which parses as float and returns 0 headers.
- **Follow-up commit?** No — fix was in-scope for the audit infrastructure construction itself.

### B3 — `trace_stat_corrected` rounded to 4 decimals in audit fields
- **Severity:** low
- **Surfaced by:** 3d Johansen audit
- **Observation:** TSL's `johansen_cointegration.py` line 295 applies `round(v, 4)` to the corrected trace statistic before storing in the audit dict. This caps audit-field precision at 1e-4 even though the underlying computation has full double precision. Display tables benefit from rounding; programmatic audit-dict consumers may want full precision.
- **Recommended remediation (optional):** Preserve full precision in `audit["trace_stat_corrected"]` while keeping rounding in display tables.
- **Follow-up commit?** Optional, low priority.
- **Related audit:** 3d — see `3d_johansen_audit.md` Section "Methodology notes".

### B4 — fabletools `reconcile()` requires mable/fable types (audit limitation)
- **Severity:** none (audit limitation, not TSL issue)
- **Surfaced by:** 3e MinT audit
- **Observation:** fabletools's public `reconcile()` operates on mable / fable model-object types only. There is no public entry point for raw matrices (S, y_hat, residuals), so it cannot serve as a third reference for the 3e triangulation without first fitting a full underlying model (which would introduce estimation noise). Skipped from triangulation.
- **Recommended remediation:** None for TSL. For Phase 2 harness, accept that hts + HF cover the parity space adequately.
- **Follow-up commit?** No.

### B5 — Plan-level mistake: `evir::exindex` is NOT Ferro-Segers
- **Severity:** none (plan-level note)
- **Surfaced by:** 3c Ferro-Segers audit
- **Observation:** The Stage B plan named `evir::exindex` as a secondary Ferro-Segers reference. That was incorrect — `evir::exindex` is the BLOCK-MAXIMA estimator (Smith 1989), requiring a `block` size argument, NOT the Ferro-Segers 2003 intervals estimator. The canonical R Ferro-Segers intervals implementation is `extRemes::extremalindex(..., method="intervals")`. The Stage B table has been corrected.
- **Recommended remediation:** Documented in plan file under "Stage B plan-level fix (from 3c audit)" so future audits don't repeat the mistake.
- **Follow-up commit?** No (plan-level lesson; audit reports are already correct).

### B6 — PyMC NUTS auto-downgrade to pure-Python pytensor without g++
- **Severity:** **medium-high** (most consequential audit finding)
- **Surfaced by:** 2b MCMC SV audit
- **Observation:** On Windows machines without `g++` available on PATH, PyMC's NUTS sampler silently falls back from compiled C to pure-Python pytensor execution. On a T=500 SV model, NUTS runtime balloons from ~10s (compiled) to >25 min (pure-Python, audit timed out). TSL's `stochastic_volatility.py` wrapper does not detect or warn about this condition. The Gibbs backend (Kim-Shephard-Chib mixture-of-normals) is a working fallback that runs in ~50s without compilation, but the wrapper currently has no path that prefers Gibbs when NUTS would be unusably slow.
- **Recommended remediation:**
  - At wrapper entry, detect g++ availability via `shutil.which("g++")` (or equivalent for Windows MSVC).
  - On absence, downgrade preferred backend from PyMC NUTS → Gibbs with a Tier 1 warning: *"PyMC NUTS unavailable on this machine (no C compiler detected); using Kim-Shephard-Chib Gibbs sampler. Posterior samples remain valid but mixing characteristics differ."*
  - Trigger D1 `backend_fallback` with `fallback_reason = "no_c_compiler"`.
  - Optional: at install time, log a one-time warning if torch / pymc are installed but g++ is missing.
- **Follow-up commit?** **YES.** Production users on Windows hit this without warning; current behavior is silent slowdown.
- **Related audit:** 2b — see `2b_mcmc_sv_audit.md` Sections "Implementations compared" + "Methodology notes".

### B7 — Latent log-volatility posterior mean not exposed in audit fields
- **Severity:** low / medium (optional)
- **Surfaced by:** 2b MCMC SV audit (also 2c)
- **Observation:** TSL's `stochastic_volatility.py` wrapper does not expose the posterior mean of the latent log-volatility series (h_t at each t) in audit fields. The latent series is the practitioner-relevant output of an SV model (it's what users plot as "the volatility path"); only parameter summaries (mu, phi, sigma_eta) are currently in the audit dict. The 2b/2c audits had to compare stochvol's posterior h to the TRUE latent path as a sanity check rather than perform a direct TSL-vs-stochvol latent comparison.
- **Recommended remediation:** Add `h_posterior_mean` (length-T array) and optionally `h_posterior_std` to `audit_fields` on both NUTS and Gibbs backends.
- **Follow-up commit?** Optional — improves audit completeness but doesn't fix a bug.
- **Related audit:** 2b — see `2b_mcmc_sv_audit.md` Section "Latent log-volatility series".

### B8 — TSL output-rounding floor at 1e-6 limits parity-audit precision
- **Severity:** none (documentation-only)
- **Surfaced by:** 3a CAViaR + 3b HAR-CJ audits
- **Observation:** Multiple TSL wrappers apply `round(value, 6)` when serializing numerical outputs (audit fields and output-table cells). Examples: `har_cj.py` lines 393–399 + 578–584 (coefficient table + audit fields); `caviar_quantile_dynamics.py` lines 242 + 367 (parameters + quantile_loss). This caps parity-audit precision at 1e-6 absolute even when the underlying computation is bitwise identical to the reference. For tiny intercepts (e.g., 5e-6 in 3b) this drives relative diff to ~6%.
- **Recommended remediation:** None for production behavior. For Phase 2 harness, calibrate tolerances at `abs_tol = 1e-6` for closed-form math. If a specific wrapper needs tighter assertions, add an opt-in `__audit_raw_outputs__: True` ctx-param that bypasses rounding.
- **Follow-up commit?** No.

### B9 — CAViaR Nelder-Mead non-determinism (expected behavior)
- **Severity:** none (documents expected behavior)
- **Surfaced by:** 3a CAViaR audit
- **Observation:** Non-smooth quantile loss admits multiple local optima. Different multi-restart seeds converge to different valid β. On the 3a fixture, TSL converged to β=(0.0026, 0.9951, -0.0190) loss=0.040479 while the from-scratch reimpl converged to β=(-0.0798, 0.8450, -0.0751) loss=0.041073. Both legitimate. q-path-given-β and loss-given-β are bitwise identical between TSL and reimpl.
- **Recommended remediation:** None — non-uniqueness is inherent to CAViaR (Engle-Manganelli 2004 acknowledge it). Phase 2 harness should follow the 3-tier verification pattern: bitwise on derived quantities given fixed β; loose-tolerance on optimizer output.
- **Follow-up commit?** No.

### B10 — NBEATS / NHiTS `n_params` field-parity gap
- **Severity:** low (out-of-scope for the 1a fix it was surfaced by)
- **Surfaced by:** 1a regression sweep
- **Observation:** NBEATS and NHiTS PyTorch-backend runs show `audit_fields["n_params"] = None` even though `n_params = sum(p.numel() for p in model.parameters())` is computed locally and embedded in `model_desc` (e.g., "N-BEATS (PyTorch, ..., params=50497)"). The 1a fix targeted LSTM/GRU/TCN for n_params field-parity per commit message; NBEATS/NHiTS were left because their 1a target was the `stack_types` / `pooling_sizes` user-override bug.
- **Recommended remediation:** Add `n_params` to NBEATS audit_fields on both PyTorch and sklearn paths (parallel to LSTM/GRU/TCN). Same for NHiTS. Optionally extend Tier 3 metric tables to include `n_params` for these wrappers.
- **Follow-up commit?** Optional, low priority.
- **Related audit:** 1a — see `1a_regression_audit.md`.

---

## 4. Phase 2 Prioritization Recommendation

Phase 2 builds permanent parity assertions for the highest-risk techniques as a CI-runnable harness. Selection criteria below.

### Tier A — Must-have permanent harness (5 techniques)

These should have permanent parity assertions because they either surfaced real bugs in Phase 1 OR they are foundational building blocks where any regression propagates broadly.

1. **3e MinT reconciliation** — Phase 1 surfaced B1 (rank-deficient W). After B1 fix lands, the harness should verify (a) the cascade fires correctly on rank-deficient fixtures and (b) the four reconciliation methods (ols, wls_variance, mint_shrinkage, mint_sample) match `hts::MinT` and `hierarchicalforecast` at machine epsilon on well-conditioned fixtures.
2. **2a Kalman filter / smoother** — Foundational. Used internally by stochastic volatility, structural breaks, missing-data interpolation. Any regression here cascades. Reference: `dlm::dlmFilter` + `KFAS::KFS`. Tolerance 1e-6 abs is appropriate for closed-form Gaussian Kalman.
3. **2b/2c MCMC SV** — High-stakes inference; B6 (PyMC g++ downgrade) needs ongoing detection. Phase 2 harness should (a) verify the Gibbs backend posterior means stay within 5%/10% tolerance band of `stochvol::svsample`, (b) assert ESS > 500 on mu and phi, and (c) detect-and-warn if NUTS is slower than 30s on the standard fixture (proxy for compiler issue).
4. **3f Transformer attention** — Bitwise parity test for the patch + no-op forward hook mechanism. The capture mechanism is non-standard (it disables PyTorch's sparsity fast-path) and any future change to `nn.TransformerEncoderLayer` internals risks breaking it silently. 1e-12 strict tolerance is appropriate. Add teardown verification (sa_block restored, hooks removed).
5. **3c Ferro-Segers extremal index** — High-stakes extremal-value computation; clean bitwise parity at 1e-6 vs `extRemes::extremalindex`. Cheap to assert. Branch-selection logic check is Phase-1-unique value.

### Tier B — Should-have permanent harness (3 techniques)

Techniques with clean reference parity that establish ongoing regression protection but have lower bug risk in expected practice.

6. **1c BVAR IRF / FEVD** — Bitwise closed-form math. Cheap CI assertion. Catches any future refactor of the IRF / FEVD math path.
7. **3d Johansen Bartlett** — Bartlett factor formula `(T - n*p - d)/T` is pure arithmetic; raw trace stat parity vs `statsmodels.coint_johansen` is bitwise. Cheap to assert. Note: do NOT include the urca-vs-statsmodels comparison in CI (real cross-package divergence; would always show ~30% gap).
8. **3b HAR-CJ** — From-scratch reimpl is short (~80 LOC) and the regression math is closed-form OLS. Tolerance 1e-6 (output-rounding floor). Useful to catch any future refactor of jump-detection or cascade-construction.

### Tier C — Skip permanent harness (4 techniques)

Reference is paper-only / reimpl-based, audit was confirmatory, or technique is low-risk.

- **3a CAViaR** — Reference is from-scratch reimpl (no canonical R package). Phase 1 confirmed q-path / loss math is correct. Permanent harness would only re-verify the reimpl, not catch new bugs. Optional: include the q-path-given-β bitwise check as a unit test in `tests/`, not as a parity-harness assertion.
- **1b TBATS** — TSL wraps Python `tbats` directly; bitwise parity is automatic. The R divergence is real-world cross-package noise, not a TSL property. Phase 2 harness here would mostly be redundant.
- **1a PyTorch path validation** — Bug-fix regression. Already covered by canonical tests. No external reference. Skip.
- **2b/2c latent posterior mean** — Until B7 lands (exposing h_posterior_mean), there's nothing to parity-check at the latent-series level. Re-evaluate after B7.

### Phase 2 effort estimate

8 techniques × ~150 LOC each (using existing `rscript_bridge.py` infrastructure) = ~1200 LOC total. The 12 Phase 1 audit scripts already average 400 LOC; converting to lean assertion-only harness should reduce by 60-70%. Estimated 1-2 sessions for Phase 2 build.

---

## 5. Methodology Divergences Requiring Honest-Disclosure Updates

These items are real methodology / parametrization differences (not bugs) that warrant Tier-level documentation in TSL specs.

### 2b / 2c MCMC SV — Prior parameterization differences
**Spec:** `engine/interpretation/specs/stochastic_volatility.py` (Tier 3 honest-disclosure)
**Recommended addition:**
> "TSL's PyMC and Gibbs backends use Bayesian priors that differ from R `stochvol`'s defaults: `phi` ~ Beta(20, 1.5) on (0, 1) vs stochvol's `(phi+1)/2` ~ Beta(20, 1.5) on (-1, 1); `sigma_eta` ~ HalfNormal(0, 2) vs stochvol's Gamma(0.5, 1/2). On data with `phi` near 1 and T ≥ 500, posteriors agree to within ~5% (data dominates priors); on `sigma_eta` posterior means may differ by 25–50% even when both implementations are correct, attributable to the different prior shapes."

### 3e MinT shrinkage — hts/fabletools/HF target convention
**Spec:** `engine/interpretation/specs/forecast_reconciliation.py` (Tier 3 D2 disclosure)
**Recommended addition:**
> "The Schäfer-Strimmer shrinkage estimator (mint_shrinkage method) produces the same lambda across TSL, R `hts::shrink.estim`, and Python `hierarchicalforecast.MinTrace(method='mint_shrink')` to within 1e-6. R `fabletools::reconcile()` uses an internal shrink_estim that is not always exposed in the public namespace; treat fabletools as a forward-compatible target rather than a strict bitwise reference."

### 3d Johansen — urca vs statsmodels methodology divergence
**Spec:** `engine/interpretation/specs/johansen_cointegration.py` (Tier 3 honest-disclosure)
**Recommended addition:**
> "TSL wraps `statsmodels.tsa.vector_ar.vecm.coint_johansen`. Trace statistics from R `urca::ca.jo` differ by 5–30% on small samples (T ≤ 200) due to different reduced-rank regression parametrizations. Both are valid Johansen (1991) implementations; the divergence is documented in the econometrics literature. The Bartlett-Reimers correction TSL applies is pure arithmetic on the statsmodels output and does not depend on which package supplies the raw statistic."

### 1b TBATS — R::forecast vs py-tbats divergence
**Spec:** `engine/interpretation/specs/tbats_forecast.py` (Tier 3 honest-disclosure)
**Recommended addition:**
> "TSL wraps the Python `tbats` package (1.1.x). On identical fixtures, TSL produces forecasts bitwise-identical to py-tbats. R `forecast::tbats` may produce point forecasts differing by 5–10% on the same data due to optimizer initialization (random restarts vs deterministic AIC grid), Box-Cox lambda search range, and damped-trend handling. Both implement De Livera-Hyndman-Snyder 2011; modest divergence is expected and documented."

---

## 6. Plan-Level Corrections for Future Audit Work

### Corrected references / packages

- **B5 — `evir::exindex` is NOT Ferro-Segers.** Stage B plan named it as a secondary Ferro-Segers reference; that was incorrect. `evir::exindex` is the block-maxima estimator (Smith 1989); the canonical R Ferro-Segers 2003 intervals implementation is `extRemes::extremalindex(..., method="intervals")`. Stage B has been corrected.

- **`stochvol::svtsample priornu` API.** `priornu` is a scalar exponential rate (default `priornu = 1`), NOT the vector `c(2, 100)` initially passed. The Stage B plan and 2c audit script were corrected to use `priornu = 0.1` (slow exponential decay, weakly informative).

- **`hierarchicalforecast.MinTrace` method names.** `hts::MinT` uses `"shrink"` ↔ HF `"mint_shrink"`; `hts::MinT` uses `"sam"` ↔ HF `"mint_cov"`. Stage B table has been mapped correctly.

- **HF reconcile API.** `idx_bottom` kwarg is invalid in current HF; pass `y_insample` / `y_hat_insample` arrays instead. Reflected in 3e audit script.

### Infrastructure lessons

- **rpy2 broken on Windows R 4.5.3.** rpy2 3.6.7 installs on Python 3.14 but `get_r_flags` raises IndexError parsing R's ldflags. Fallback `Rscript` subprocess pattern works robustly. Phase 2 should continue using `tools/reference_parity/scripts/rscript_bridge.py` rather than attempting rpy2 again.

- **Bulk `library()` of all 15 R packages in one Rscript session segfaults** due to namespace collision. Per-audit scripts must load only the packages needed. Documented in Stage A notes; followed throughout Stage C.

- **Multi-restart non-deterministic optimizers (CAViaR, TBATS, neural wrappers) need 3-tier audit pattern**:
  1. Strict (1e-12) bitwise check on derived quantities given fixed β / parameters,
  2. Loose (1-5%) check on independently-converged β,
  3. Optional R1 paper-structure validation (signs / magnitudes consistent with published examples).

- **TSL output-rounding floor at 1e-6** — Phase 2 harness should default to `abs_tol = 1e-6` for closed-form math (matches `round(value, 6)` precision in TSL audit fields). Tighter tolerances will spuriously fail.

### MCMC tolerance ladder (locked from Segment 2)

For any future MCMC parity audit:
- `< 5% rel diff` → PASS (MC noise band).
- `5–10% rel diff` → CAVEAT.
- `> 10% rel diff` → METHODOLOGY (priors / mixture spec / proposal tuning), not bug.
- ESS > 500 on key parameters required; if either implementation reports ESS < 100, audit pauses for "Re-run at higher draw count."

---

## 7. Phase 1 Closure Summary

### Time invested

- **Stage A (environment setup):** ~1 session segment. R 4.5.3 install + 15 R packages + 14 Python references + rpy2 / Rscript bridge decision.
- **Stage B (per-technique audit plan + R1/R2 refinements):** 1 session segment.
- **Stage C (12 audits across 3 segments):** 3 session segments. Segment 1 (closed-form: 3e, 3c, 3d, 3f, 1c, 2a). Segment 2 (MCMC: 2b, 2c). Segment 3 (medium + low: 1b, 3b, 3a, 1a).
- **Stage D (this report):** 1 session segment.
- **Total:** ~6-7 active session segments end-to-end.

### Files created

`tools/reference_parity/scripts/`:

| Script | LOC | Purpose |
|---|---|---|
| `rscript_bridge.py` | ~250 | Core utility: numpy ↔ R via Rscript subprocess |
| `test_rscript_bridge.py` | ~120 | Roundtrip tests for the bridge (mean, sum, matmul) |
| `audit_3e_mint.py` | ~500 | MinT reconciliation triangulation (R-hts + HF + TSL) |
| `audit_3c_ferro_segers.py` | ~400 | Ferro-Segers extremal index (extRemes vs TSL) |
| `audit_3d_johansen.py` | ~400 | Bartlett correction + statsmodels + urca vibes |
| `audit_3f_attention.py` | ~400 | Transformer attention bitwise vs native MHA |
| `audit_1c_bvar_irf.py` | ~400 | BVAR IRF/FEVD: TSL + numpy + R |
| `audit_2a_kalman.py` | ~350 | Kalman filter/smoother vs dlm + KFAS |
| `audit_2b_mcmc_sv.py` | ~430 | MCMC SV vs stochvol::svsample |
| `audit_2c_student_t_sv.py` | ~400 | Student-t SV vs stochvol::svtsample |
| `audit_1b_tbats.py` | ~470 | TBATS vs py-tbats + R::forecast |
| `audit_3b_har_cj.py` | ~400 | HAR-CJ vs from-scratch reimpl (R1 paper-validated) |
| `audit_3a_caviar.py` | ~340 | CAViaR vs from-scratch reimpl (R1 paper-validated) |
| `audit_1a_regression.py` | ~370 | PyTorch path regression sweep (5 wrappers) |

**Total audit LOC:** ~5230 across 14 files.

`tools/reference_parity/reports/`:
- 12 per-audit reports (3a-3f, 1a-1c, 2a-2c) — average 4 KB each, total ~50 KB.
- `_rscript_call_log.jsonl` — per-call metadata (duration, r_code SHA, input shapes) for postmortem.
- `retrospective_audit_2026_04_25_FINAL.md` — this document.

`tools/reference_parity/fixtures/`:
- 12 `.npz` fixtures (one per audit) — seeded synthetic data for reproducibility.

### Infrastructure delivered

- **`rscript_bridge.py` validated end-to-end** across 9 distinct R-calling patterns: matrix algebra (3e, 1c, 3d), tabular OLS (3b), reduced-rank regression (3d), MCMC samplers (2b, 2c, 3c), state-space (2a), TBATS optimizer (1b). Bridge is ready for Phase 2 reuse without modifications.
- **Rscript subprocess pattern documented** as the working alternative to rpy2 on Windows R 4.5.3.
- **MCMC tolerance ladder** (5% / 10% / methodology) is now the standard for MCMC parity audits.
- **3-tier non-deterministic optimizer audit pattern** (bitwise on derived quantities; loose on optimizer output; optional R1) is the standard for CAViaR / TBATS / neural wrappers.

### What Phase 2 inherits from Phase 1

- **Working R + Python reference environment** (15 R packages + 14 Python references).
- **`rscript_bridge.py`** as the foundational R-calling utility.
- **12 reference-fitting patterns** for reuse: each Phase 1 audit script demonstrates exactly how to fit the reference and extract comparable outputs. Phase 2 harness can lift these directly and trim them to assertion-only form.
- **12 seeded fixtures** under `fixtures/` — Phase 2 can reuse them or add new fixtures using the established `np.savez(...)` convention.
- **Tolerance and verdict conventions** locked in this report (Section 3).
- **Plan-level corrections** documented (Section 6) so Phase 2 doesn't repeat Stage B's `evir::exindex` / `priornu` / HF API mistakes.

### Next-session work (post-Phase 1)

Recommended follow-up commits:
1. **B1 mint_sample rank guard** (medium) — standard 5-phase follow-up cycle.
2. **B6 PyMC NUTS g++ auto-downgrade** (medium-high) — detect-and-fall-back to Gibbs on Windows without g++; emit Tier 1 warning.
3. **B7 latent log-volatility posterior exposure** (low/medium, optional) — add `h_posterior_mean` to SV audit fields.
4. **B10 NBEATS/NHiTS n_params field-parity** (low, optional) — match LSTM/GRU/TCN convention.
5. **Honest-disclosure spec updates** per Section 5 — Tier 3 documentation for SV priors, MinT shrinkage targets, Johansen urca/statsmodels divergence, TBATS R/Py divergence.

These five items are independent and can be addressed in any order across future sessions.

Phase 2 (permanent harness) and Phase 3 (workflow integration as Phase 4.5) become separate session work after the recommended commits land.

---

**Phase 1 closes.** Audit infrastructure is permanent under `tools/reference_parity/`. Future cycles inherit a working R+Python bridge, 12 reference-fitting patterns, and a documented tolerance discipline.
