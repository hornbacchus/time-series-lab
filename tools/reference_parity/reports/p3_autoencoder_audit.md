# Phase 3 Batch 9 — `p3_autoencoder` Audit

**Wrapper:** `engine/techniques/autoencoder_anomaly.py`
**Reference:** direct PyTorch encoder-decoder MLP in-process (torch 2.11.0+cpu)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `reconstruction_errors` | 0.0 | PASS (exact) |
| `final_loss` | 0.0 | PASS (exact) |

Encoder-decoder MLP (window=10 → hidden=8 → bottleneck=4 →
hidden=8 → window=10) with seed pinning + 5 epochs Adam.
Bit-exact same-library self-parity on per-window reconstruction
errors.
