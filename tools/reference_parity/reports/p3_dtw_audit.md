# Phase 3 Batch 10 — `p3_dtw` Audit

**Wrapper:** `engine/techniques/dtw_alignment_lag.py`
**Reference:** Python `dtaidistance.dtw` (dtaidistance 2.4.0)
**Verdict:** **PASS** (Pattern A cross-package bit-exact)
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `dtw_distance` | 0.0 | PASS (exact) |

DTW is closed-form dynamic programming. Numpy reference (TSL
mirror) and dtaidistance C-implementation produce byte-
identical distances on the test fixture.

DGP: warped sinusoid pair (T=100, warp_factor=1.2, σ=0.05,
seed=42).
