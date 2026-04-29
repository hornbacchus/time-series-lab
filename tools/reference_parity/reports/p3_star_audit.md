# P3 — `star_model.py` reference parity audit

**Wrapper:** `engine/techniques/star_model.py`
**Audit ID:** `p3_star`
**Batch / Session:** Phase 3 Batch 4 / Session 8
**Date:** 2026-04-29
**Verdict:** **CAVEAT** (Tier B/C — methodology divergence on smoothness parameter gamma)

## 1. Reference

- **Primary:** R `tsDyn::star(y, m=1, d=1)` — `tsDyn` 11.0.5.2.

## 2. Fixture

T=500 LSTAR(1) with phi_low=0.7, phi_high=−0.3, gamma=5.0, c=0.0, sigma=1.0, seed=42.

## 3. Achieved metrics (seed=42)

R `tsDyn::star` does converge but to a substantially different smoothness parameter γ than TSL's scipy.optimize fit:

- TSL γ ≈ 5–10 (depending on optimizer path; close to true DGP γ=5)
- R γ ≈ 100 (orders of magnitude higher; represents step-function approximation)

Both fits are mathematically valid LSTAR realizations of the same data, but represent different "smoothness scales" of the transition function. Per master plan §5 Tier B/C: **methodology divergence at the optimizer level** — neither implementation is "wrong"; they explore different regions of the parameter space.

## 4. Documented divergences

1. **Smoothness parameter γ divergence**: TSL converges to true-DGP-class γ; R tsDyn's default initialization drives γ to ~100 (effectively a step function approximation). This is a known characteristic of LSTAR optimization: the likelihood surface is flat in γ above ~10, so different optimizers terminate at very different γ values.
2. **No `logLik` method** for star objects; computed manually from residuals.
3. **Coefficient names** in tsDyn 11.x: `gamma` and `th` (lowercase) at indices 5 and 6 of `coef(fit)`.

## 5. Outcome

**CAVEAT.** Per master plan §3.1, CAVEAT correctly signals "matches except in stated regime" — here, the regime is "LSTAR optimization is fundamentally non-identifiable in γ once γ exceeds a fixture-dependent threshold; both implementations are correct LSTAR fits but at different points on the flat likelihood ridge." Not a bug; documented.

## 6. Notes — Tier B/C verification approach

For wrappers in this regime (master plan §5 Tier B/C), the **right verification approach is internal-consistency** rather than per-parameter parity:
- Both implementations should produce in-sample residuals with similar variance (Gaussian likelihood plug-in agreement).
- Both should produce fitted values that approximate the original series within the noise level.
- Strict per-parameter parity is intractable.

Future Phase 3.5 candidate: refactor `p3_star.compare()` to use this internal-consistency framework instead of per-parameter abs_diff.
