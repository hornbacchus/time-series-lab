# Phase 3 Batch 9 — `p3_nhits` Audit

**Wrapper:** `engine/techniques/nhits_forecast.py`
**Reference:** custom PyTorch NHITS self-parity (torch 2.11.0+cpu)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `final_loss` | 0.0 | PASS (exact) |

NHITS architecture (NBEATS variant with multi-rate hierarchical
sampling via 1-D MaxPool with pool_sizes=[2,4]) with seed
pinning. Bit-exact. Same-library self-parity rationale as
`p3_nbeats` (Pattern J B.5.1).
