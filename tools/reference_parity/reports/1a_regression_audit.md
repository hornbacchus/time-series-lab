# 1a — PyTorch path validation regression sweep

**Date:** 2026-04-24

**Audit type:** Bug-fix regression sweep (NOT an
external parity check). Validates that the five
fixes in commit 7329241 remain in place.

**Source commit:** `7329241` — "Validate PyTorch paths for C7 neural specs and fix surfaced bugs (follow-up 1a)"

**Overall:** **PASS** (13/13 checks passed)

## Checks

| # | Check | Verdict | Detail |
|---|---|---|---|
| 1 | 1a-A NBEATS run completes | PASS | status=success |
| 2 | 1a-A NBEATS stack_types override honored | PASS | requested=['trend', 'seasonality', 'generic'], returned=['trend', 'seasonality', 'generic'], backend=pytorch |
| 3 | 1a-B NHiTS run completes | PASS | status=success |
| 4 | 1a-B NHiTS pooling_sizes override honored | PASS | requested=[8, 4, 1], returned=[8, 4, 1], backend=pytorch |
| 5 | 1a-C LSTM run completes | PASS | status=success |
| 6 | 1a-C LSTM n_params reported (backend=pytorch) | PASS | n_params=50497 |
| 7 | 1a-C GRU run completes | PASS | status=success |
| 8 | 1a-C GRU n_params reported (backend=pytorch) | PASS | n_params=37889 |
| 9 | 1a-D TCN run completes | PASS | status=success |
| 10 | 1a-D TCN n_params reported (backend=pytorch) | PASS | n_params=9537 |
| 11 | 1a-E Autoencoder run completes | PASS | status=success |
| 12 | 1a-E Autoencoder backend reported | PASS | backend=pytorch_autoencoder |
| 13 | 1a-E Autoencoder backend_fallback trigger absent on PyTorch | PASS | backend=pytorch_autoencoder, trigger fired=None |

## Summary

- **NBEATS backend:** `pytorch`
- **NBEATS stacks:** `['trend', 'seasonality', 'generic']`
- **NHiTS backend:** `pytorch`
- **NHiTS pooling:** `[8, 4, 1]`
- **LSTM:** `{'backend': 'pytorch', 'n_params': 50497}`
- **GRU:** `{'backend': 'pytorch', 'n_params': 37889}`
- **TCN backend:** `pytorch`
- **TCN n_params:** `9537`
- **Autoencoder backend:** `pytorch_autoencoder`

## Methodology notes

- All runs use `preset='Balanced'` (so the PyTorch
  branch is actually exercised — Fast preset forces
  sklearn fallback) and `epochs=8` to keep the
  regression sweep fast (minutes, not hours).
- AR(1) fixture is sufficient to exercise both
  PyTorch and sklearn fallback paths; we don't need
  long high-quality forecasts here, only that the
  bug-fix code paths execute.
- Loss-decrease verification is omitted because:
  (1) wrappers don't expose per-epoch loss curves in
  audit_fields,
  (2) the bug fixes are about parameter pass-through
  and field reporting, not training-loop correctness
  (which was already validated during the original C7).

- The autoencoder spec test verifies the trigger
  function `_trigger_backend_fallback` does NOT fire
  when the wrapper reports `backend='pytorch_autoencoder'`.
  This is the specific symptom the 1a fix corrected:
  before the fix, the spec checked `backend == 'pytorch'`
  and treated `pytorch_autoencoder` as a fallback.
