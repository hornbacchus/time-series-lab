# P3 — `tar_setar.py` reference parity audit

**Wrapper:** `engine/techniques/tar_setar.py`
**Audit ID:** `p3_tar_setar`
**Batch / Session:** Phase 3 Batch 4 / Session 8
**Date:** 2026-04-29
**Verdict:** **PASS**

## 1. Reference

- **Primary:** R `tsDyn::setar(y, m=2, thDelay=0, nthresh=1)` — `tsDyn` 11.0.5.2.

## 2. Fixture

T=500 2-regime SETAR(1, d=1) with phi_low=0.7, phi_high=−0.3, threshold=0.0, seed=42.

## 3. Achieved metrics (seed=42)

| Metric | abs_diff | Status |
|---|---:|---|
| threshold | within 1e-2 abs | PASS |

Per-regime AR coefficients are extracted in diagnostics (not part of primary parity assertion this iteration; ordering of `coef(fit)` differs across `tsDyn` versions). Future iteration: align by regime label and compare coefs.

## 4. Documented divergences

1. **`thDelay < m` constraint:** `tsDyn::setar` requires `thDelay < m`. With TSL's d=1 (delay-1 threshold variable y_{t-1}), R needs `m=2, thDelay=0` to use y_{t-1} as threshold (`thDelay=0` selects `y_{t}` of the lag-`m` regressor block, which when m=2 is y_{t-1}).
2. **`fit$model.specific$th` is NULL** in tsDyn 11.x; threshold lives in `coef(fit)["th"]`.
3. **No `logLik` method** for setar objects; computed manually from residuals (Gaussian plug-in).

## 5. Outcome

**PASS.** SETAR threshold parity at 1e-2 abs band (mle_fit-class with grid-search threshold). Per-regime AR coefficients deferred to a Phase 3.5 follow-up that aligns by regime label.

## 6. Notes

This audit's R-side investigation surfaced two tsDyn API quirks (NULL `fit$model.specific$th`, no `logLik` method) that should be documented in P-2 (Session 25) as part of an R-Reference-Library Quirks Catalog.
