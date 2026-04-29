# P3 — `vecm_model.py` reference parity audit

**Wrapper:** `engine/techniques/vecm_model.py`
**Audit ID:** `p3_vecm`
**Batch / Session:** Phase 3 Batch 3 / Session 7
**Date:** 2026-04-29
**Verdict:** **PASS** (machine precision after sign normalization)

## 1. Reference

- **Primary:** R `urca::ca.jo(Y, K=2, ecdet="const", spec="longrun")` followed by `vars::cajorls(jt, r=1)` for coefficient extraction. `urca` 1.3.4 + `vars` 1.6.1.

Both statsmodels `VECM` and the urca+vars combo implement the Johansen reduced-rank regression. Coefficient parity expected at MLE-class tolerance.

## 2. Fixture

Synthetic bivariate cointegrated VAR(2) with rank=1 cointegration:

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 500 |
| `k_ar_diff` | 1 |
| `coint_rank` | 1 |
| `deterministic` | `"ci"` (TSL) / `ecdet="const"` (R) |

DGP: `y2_t` ~ random walk; `y1_t = 0.7 * y2_t + xi_t` with stationary `xi`. True cointegrating vector: `(1, -0.7)`.

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | beta cointegrating vectors (k, r), alpha loadings (k, r) |
| **Secondary** | log-likelihood |

Beta is **first-element-normalized to 1** on both sides for parity comparison (statsmodels does this by default; R's `@V` eigenvectors have arbitrary norm). Alpha is sign-aligned to match beta sign convention.

## 4. Tolerance ladder

MLE-fit class baseline (1e-2 abs / 1e-2 rel) — actually achieved closed-form-class (Pattern A).

## 5. Achieved metrics (seed=42)

### Primary

| Metric | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---|
| beta (sign-normalized) | **9.99e-16** | 1.42e-15 | PASS |
| alpha (sign-aligned) | 2.78e-13 | 2.98e-13 | PASS |

### Secondary

| Metric | abs_diff | rel_diff | Status |
|---|---:|---:|---|
| log-likelihood | 5.91e-11 | 5.45e-14 | PASS |

**Bit-exact** modulo sign-normalization handling.

## 6. Documented divergences

**None on Primary tier.** beta and alpha agree at machine precision after applying:
1. **Beta first-element normalization to 1.0** (handles different sign + scale conventions between statsmodels and ca.jo's eigenvector output).
2. **Alpha sign-alignment** with beta (handles joint sign-flip ambiguity: alpha @ beta.T is identified, not alpha alone).

Both pre-processing steps are **methodology-equivalent** alignment (not error correction); the underlying Johansen MLE produces equivalent point estimates.

## 7. Runtime

0.76s. Fast-tier eligible.

## 8. Structural invariants verification

`vecm_cointegration_rank`: TSL asserts r=1 (input parameter); R `urca::ca.jo` infers r from the trace-statistic test. Both must agree exactly. On the seed=42 fixture: TSL_rank=1, REF_rank=1 → invariant PASS.

## 9. Outcome

**PASS** at machine precision after sign normalization. **Pattern A 9th wrapper** (closed-form / Johansen MLE achieving bit-exact via reduced-rank regression's algebraic structure). Cointegrating-rank invariant matches exactly.

## 10. Notes — beta sign + alpha alignment pattern

The normalize-and-align pattern this audit uses is generalizable to other reduced-rank MLE wrappers (Bayesian VAR, factor-analytic state-space). Documented in cross-batch findings as a candidate Pattern I (sign / scale convention alignment) — needs 2+ more wrappers exhibiting the same pattern before formalizing.
