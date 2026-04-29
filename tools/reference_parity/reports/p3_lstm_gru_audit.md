# Phase 3 Batch 9 — `p3_lstm_gru` Audit

**Wrapper:** `engine/techniques/lstm_gru_forecast.py`
**Reference:** direct PyTorch `nn.LSTM` in-process (torch 2.11.0+cpu)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `final_loss` | 0.0 | PASS (exact) |

**Outcome:** byte-identical agreement after 5 epochs of Adam
training. Seed pinning (`torch.manual_seed` + `np.random.seed` +
`random.seed`) + `cuDNN.deterministic=True` produces fully
deterministic LSTM training; same-library self-test verifies
wrapper architecture-construction reproducibility.

## Fixture
- DGP: AR(1), φ=0.6, T=200, seed=42
- LSTM: hidden=16, lookback=12, 5 epochs Adam(lr=0.01)
