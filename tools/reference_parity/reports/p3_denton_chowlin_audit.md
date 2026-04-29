# Phase 3 Batch 10 — `p3_denton_chowlin` Audit

**Wrapper:** `engine/techniques/denton_chowlin_disaggregation.py`
**Reference:** R `tempdisagg::td(method="denton-cholette")` (tempdisagg 1.2.0)
**Verdict:** **PASS** (Pattern A cross-package machine precision)
**Date:** 2026-04-29

| Metric | max abs diff | max rel diff | status |
|---|---:|---:|---|
| `disaggregated` | 6.39e-14 | 1.35e-15 | PASS |

Denton-Cholette / Chow-Lin disaggregation is closed-form
quadratic optimization. TSL solves via numpy block-elimination
of the KKT system; R tempdisagg::td uses GLS-equivalent
reformulation. Both produce machine-precision-identical
disaggregated series.

DGP: 12 quarterly aggregates of 48 monthly indicator values
(seed=42).
