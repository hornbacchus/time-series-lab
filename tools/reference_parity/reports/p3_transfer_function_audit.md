# Phase 3 Batch 10 — `p3_transfer_function` Audit

**Wrapper:** `engine/techniques/transfer_function.py`
**Reference:** from-scratch self-parity (numpy lstsq on lag-feature design matrix)
**Verdict:** **PASS** (Pattern A self-parity bit-exact)
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `betas` | 0.0 | PASS (exact) |
| `sse` | 0.0 | PASS (exact) |

Distributed-lag OLS is closed-form normal-equations solve.
Self-parity reference mirrors TSL's lag-feature construction
+ lstsq. Bit-exact betas + SSE.

**Master plan §15.12 reference (R TSA::arimax) deselected:**
TSA::arimax has a transfer-function form with `xtransf` that
requires explicit numerator/denominator polynomials, not
directly aligned with TSL's simple distributed-lag OLS.
Pattern J catalog entry B.6.1.

DGP: AR(1) X with FDL response y = sum(β·x_lags) + noise
(true betas (0.5, 0.3, 0.1), T=200, seed=42).
