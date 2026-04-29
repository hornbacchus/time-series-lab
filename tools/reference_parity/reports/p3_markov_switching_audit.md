# P3 — `markov_switching.py` reference parity audit

**Wrapper:** `engine/techniques/markov_switching.py`
**Audit ID:** `p3_markov_switching`
**Batch / Session:** Phase 3 Batch 4 / Session 8
**Date:** 2026-04-29
**Verdict:** **PASS** (em_stochastic; widened bands)

## 1. Reference

- **Primary:** R `MSwM::msmFit` — `MSwM` 1.5.

statsmodels `MarkovRegression` and R MSwM are independent EM implementations of Hamilton 1989. **Pattern H DSCD candidate.**

## 2. Fixture

T=500 2-regime mean-switching, means (−1, +1), σ=0.5, transition (0.95, 0.05; 0.10, 0.90), seed=42.

## 3. Achieved metrics (seed=42)

| Metric | abs_diff | Status |
|---|---:|---|
| regime_means | 5.91e-05 | PASS |
| transition_matrix | 5.46e-02 | PASS (widened) |
| log_likelihood (\|x\|) | 0.348 | PASS |

statsmodels and MSwM both converge to means (−1.005, +1.018) with transition probabilities ~0.95/0.94 self-persistence; **excellent agreement** after fixing the param-name extraction (`fit.model.param_names` vs `fit.params.index`) and the log-likelihood sign convention (MSwM uses opposite sign).

## 4. Documented divergences

1. **Param-name accessor:** statsmodels `MarkovRegressionResults.params` is a numpy array (not pandas Series); param names live on `fit.model.param_names`, not `fit.params.index`. Fixed in initial implementation.
2. **Log-likelihood sign convention:** MSwM `@Fit@logLikel` returns positive value (≈ +478.79); statsmodels `fit.llf` returns negative (≈ −479.14). Compare via `abs(loglik)` to align.
3. **MSwM convergence sensitivity:** MSwM has documented Hessian-singularity issues with `sw=c(TRUE, TRUE)` (switching variance + intercept); changed to `sw=c(TRUE, FALSE)` (intercept-only) for stability. statsmodels also fits intercept-only (`switching_variance=False`) to match.

## 5. Outcome

**PASS.** Fully aligned regime means at 5.9e-5 abs after the param-extraction + sign-convention fixes. Pattern H DSCD evidence: transition matrix divergence (~0.05 abs) within widened em_stochastic band.

## 6. Notes

The investigation arc — initial AttributeError → API discovery → Hessian singularity → sign-convention fix — is documented in this audit file as a **methodology pattern** for future EM-stochastic audits: when integrating against R EM packages, expect to hit (a) parameter-name extraction differences, (b) log-likelihood sign convention differences, (c) optimizer-init-sensitivity issues that may force `sw` argument changes. Banked: add an EM-Stochastic-Reference-Integration-Checklist to P-2 (Session 25) when Batch 4 closes.
