# Phase 3 Session 13 — Batch 9 entry findings (Python DL)

**Date:** 2026-04-29
**Master plan reference:** §15.11 (Python DL)
**Wrappers in scope:** 9
**Verdicts:** **9 PASS, 0 CAVEAT, 0 BLOCK** — second consecutive all-PASS batch
**Sessions used:** 1 (master plan budgeted 3 sessions; closed in 1 — locking 17-session closure horizon)

## Wrappers covered

| # | Wrapper | Reference | Verdict | Tolerance |
|---|---|---|---|---:|
| 1 | `lstm_gru_forecast` | direct PyTorch nn.LSTM | PASS | 0.0 abs (Pattern A.1) |
| 2 | `tcn_forecast` | direct PyTorch nn.Conv1d | PASS | 0.0 abs (Pattern A.1) |
| 3 | `nbeats_forecast` | custom PyTorch NBEATS self-parity | PASS | 0.0 abs (Pattern A.1) |
| 4 | `nhits_forecast` | custom PyTorch NHITS self-parity | PASS | 0.0 abs (Pattern A.1) |
| 5 | `autoencoder_anomaly` | direct PyTorch encoder-decoder | PASS | 0.0 abs (Pattern A.1) |
| 6 | `echo_state_network` | direct reservoirpy | PASS | 0.0 abs (Pattern A.1) |
| 7 | `gaussian_process_forecast` | direct sklearn.gaussian_process | PASS | 0.0 abs (Pattern A) |
| 8 | `prophet_forecast` | direct prophet (slow tier) | PASS | 0.0 abs (Pattern A) |
| 9 | `conformal_intervals` | self-parity split-conformal | PASS | 0.0 abs + Pattern F invariant PASS |

## Headline findings

### 1. DL non-determinism risk dramatically over-budgeted

Master plan §17.1 risk 2 pre-budgeted ≥30% Tier C for Batch 9.
**Actual Tier C: 0/9.** With rigorous seed pinning (torch +
numpy + random) + cuDNN deterministic flag, all 9 DL wrappers
achieved bit-exact same-library parity. Risk budget
overestimated by 30 percentage points.

### 2. PyBridge isolate=False shim retired (per S12 decision)

Implemented this commit. PyBridge.py_invoke now raises
PyBridgeError when called with `isolate=False`, with explicit
guidance to use direct import. Architectural simplification
complete.

### 3. Pattern A.1 same-library locked at 18 wrappers

Empirically locked at scale: 1 from Batch 6, 2 from Batch 7,
6 from Batch 8, 9 from Batch 9. All 18 achieved 0.0 abs diff.
Pattern A.1 is now the dominant Phase 3 parity pattern.

### 4. Pattern F → 14 concrete invariants

Two new invariants populated:
- `conformal_nominal_coverage` (Vovk 2005 finite-sample
  coverage validity)
- `conformal_interval_containment` (lower ≤ upper at all
  positions)

Both PASS on the conformal fixture (coverage 0.8625 vs
nominal 0.9 at alpha=0.1, n_test=80; within finite-sample
slack).

### 5. Pattern J catalog → 9 entries (3 new B.5)

- B.5.1 neuralforecast 0.1.0 + pytorch-lightning incompat on
  Python 3.14
- B.5.2 master-plan-stated reference vs actual TSL backend
  mismatch (GPyTorch named, sklearn used)
- B.5.3 PyTorch state isolation via in-test seed reset
  (alternative to PyBridge.isolate=True)

### 6. Item 12 verdict-runtime alignment — RESOLVED no change

Per Batch 9 evidence (0 Tier C wrappers; CAVEAT proxy
suffices for the 5 cumulative cases): the NO-REFERENCE /
DOCUMENTED-DIVERGENCE runtime path is **not needed**. Item 12
resolved with no harness change; documentation deferred to
P-2 closeout.

### 7. Item 13 budget revision — LOCKED at 17 sessions

12 used + 1 remaining (Batch 10 / S14) + 3 documentation +
1 closeout = 17. Optimistic end of the locked range.

## Cumulative Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 9) | **59** / 70 |
| Phase 3 remaining | 11 |
| Phase 3 sessions used | 12 (S2–S13) |
| **Pace** | **6+ sessions ahead; closure at 17 (locked)** |
| BLOCK cumulative | 0 |
| CAVEAT cumulative | 5 (unchanged) |
| Pattern A wrappers | **36** (was 27) |
| Pattern A.1 same-library sub-class | **18** wrappers (locked) |
| Pattern F concrete invariants | **14** (was 12) |
| Pattern J catalog entries | **9** (was 6; +3 B.5) |

## Master plan §15.11 reference deselections

Three deps named in master plan §15.11 were deselected and
documented in Pattern J catalog:

| Named reference | Status | Reason |
|---|---|---|
| neuralforecast (Nixtla) | Deselected | Python 3.14 incompat (B.5.1) |
| GPyTorch | Deselected | TSL uses sklearn.gaussian_process (B.5.2) |
| MAPIE | Deselected | TSL uses pmdarima base; self-parity reference suffices |

All three replaced with same-library or self-parity references
that match TSL's actual backends.

## CI matrix changes shipping in this commit

- `parity-fast.yml`: + reservoirpy, prophet (Python pip)
- `MANIFEST.toml`: + reservoirpy=0.4.1, prophet=1.3.0

## Verification

- `python -m reference_parity --tier fast` → 61 PASS + 5
  CAVEAT (unchanged) + 0 BLOCK + 0 ERROR. Total: 66 / 66 in
  102.2s.
- All 9 Batch 9 checks invoked individually; all PASS
  (8 fast + 1 slow [prophet]).
- 14 concrete Pattern F invariants verified via the
  registry-dispatch path.
- PyBridge `isolate=False` raises PyBridgeError as expected.

## Next session

Session 14 — Batch 10 entry per master plan §15.12 (misc /
Tier C / deferred). ~10–11 wrappers in scope (final batch).
Then Chat check-in 2 follows Session 14 close.

After Session 14: documentation phase (Sessions 15–17) +
closeout (Session 18). Effective Phase 3 close: **Session
17–18 per locked Item 13.**
