# Phase 3 Batch 9 — `p3_esn` Audit

**Wrapper:** `engine/techniques/echo_state_network.py`
**Reference:** direct reservoirpy in-process (reservoirpy 0.4.1)
**Verdict:** **PASS** (Pattern A.1 same-library bit-exact)
**Tolerance class:** dl_seed_pinned
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |

Echo State Network (reservoir_size=50, spectral_radius=0.9,
leak_rate=0.3) with `reservoirpy.set_seed(42)` pinned for both
the random reservoir initialization and the ridge-regression
solve. Bit-exact same-library self-parity at machine precision.
