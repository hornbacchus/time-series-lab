# Phase 3 Batch 9 — `p3_tcn` Audit

**Wrapper:** `engine/techniques/tcn_forecast.py`
**Reference:** direct PyTorch `nn.Conv1d` TCN in-process (torch 2.11.0+cpu)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `final_loss` | 0.0 | PASS (exact) |

Seed-pinned PyTorch TCN with dilated 1-D convolutions
(kernel=3, dilations=[1,2]); 5 epochs Adam(lr=0.01).
Bit-exact same-library self-parity.
