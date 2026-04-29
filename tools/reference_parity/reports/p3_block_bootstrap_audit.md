# Phase 3 Batch 10 — `p3_block_bootstrap` Audit

**Wrapper:** `engine/techniques/block_bootstrap.py`
**Reference:** from-scratch self-parity (moving-block bootstrap with seed pinning)
**Verdict:** **PASS** (Pattern A bit-exact)
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `mean_of_means` | 0.0 | PASS (exact) |
| `std_of_means` | 0.0 | PASS (exact) |
| `median_of_vars` | 0.0 | PASS (exact) |

Block bootstrap with `numpy.random.default_rng(seed=42)` is
fully deterministic. Self-parity reference mirrors TSL's
moving-block sampler. Bit-exact summary statistics across
200 bootstrap replicates.

DGP: AR(1) (T=200, seed=42); block_len=20, n_boot=200.
