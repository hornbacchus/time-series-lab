# Phase 3 Batch 9 — `p3_nbeats` Audit

**Wrapper:** `engine/techniques/nbeats_forecast.py`
**Reference:** custom PyTorch NBEATS self-parity (torch 2.11.0+cpu)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `final_loss` | 0.0 | PASS (exact) |

NBEATS architecture (2 stacks of FC blocks producing backcast
+ forecast) with seed pinning + 3 epochs Adam. Bit-exact.

**Master plan §15.11 reference (neuralforecast Nixtla)
deselected:** neuralforecast 0.1.0 incompatible with Python
3.14 (AttributeError on `pl.utilities.distributed`). Pattern J
catalog entry B.5.1. TSL wrapper itself uses direct torch.nn,
so self-parity reference is the practical alternative.
