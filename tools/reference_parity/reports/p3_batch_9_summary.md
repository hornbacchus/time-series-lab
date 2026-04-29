# Phase 3 Batch 9 — Python DL: Per-Batch Summary

**Batch:** 9 (Python DL)
**Sessions:** S13 (single-session close — master plan §15.11
budgeted 3 sessions; closed in 1, locking 17–18 closure horizon
at the optimistic end)
**Date:** 2026-04-29
**Wrappers audited:** 9 distinct
**Verdicts:** **9 PASS, 0 CAVEAT, 0 BLOCK** — second consecutive all-PASS batch

## Coverage matrix

| # | Wrapper | Audit ID | Reference | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | `lstm_gru_forecast.py` | `p3_lstm_gru` | direct PyTorch nn.LSTM | **PASS** | Pattern A.1 same-library bit-exact (0.0); seed-pinned |
| 2 | `tcn_forecast.py` | `p3_tcn` | direct PyTorch nn.Conv1d | **PASS** | Pattern A.1 same-library bit-exact (0.0); seed-pinned |
| 3 | `nbeats_forecast.py` | `p3_nbeats` | custom PyTorch NBEATS self-parity | **PASS** | Pattern A.1 (0.0); neuralforecast Nixtla ruled out (Py 3.14) |
| 4 | `nhits_forecast.py` | `p3_nhits` | custom PyTorch NHITS self-parity | **PASS** | Pattern A.1 (0.0); same rationale as NBEATS |
| 5 | `autoencoder_anomaly.py` | `p3_autoencoder` | direct PyTorch encoder-decoder | **PASS** | Pattern A.1 (0.0); seed-pinned |
| 6 | `echo_state_network.py` | `p3_esn` | direct reservoirpy | **PASS** | Pattern A.1 (0.0); same-library |
| 7 | `gaussian_process_forecast.py` | `p3_gp` | direct sklearn.gaussian_process | **PASS** | Pattern A (0.0); GPyTorch ruled out (TSL uses sklearn) |
| 8 | `prophet_forecast.py` | `p3_prophet` | direct prophet (cmdstanpy MAP) | **PASS** (slow tier) | Pattern A (0.0); uncertainty_samples=0 for determinism |
| 9 | `conformal_intervals.py` | `p3_conformal` | self-parity split-conformal | **PASS** | Pattern A (0.0); Pattern F invariant `conformal_nominal_coverage` populated |

## Patterns

### Pattern A → 36 wrappers

ALL 9 Batch 9 wrappers achieved bit-exact parity (8 at exactly
0.0 abs diff via same-library; 1 conformal with 0.0 on
predictions + 0.86 coverage which is within the PASS band of
the conformal_nominal_coverage invariant).

Pattern A wrapper count is now **36** (was 27 at Batch 8 close):

- 27 from Batches 1–8
- **NEW Session 13 (9):** lstm_gru, tcn, nbeats, nhits,
  autoencoder, esn, gp, prophet, conformal

### Pattern A.1 same-library sub-class — 18 wrappers cumulatively

Same-library self-test pattern continues at scale:

| Batch | Same-library wrappers | Pattern |
|---|---:|---|
| Batch 6 | 1 | p3_pelt (ruptures self-test) |
| Batch 7 | 2 | p3_periodogram, p3_wavelet_transform |
| Batch 8 | 6 | sklearn/xgboost/lightgbm self-test |
| **Batch 9** | **9** | **PyTorch / reservoirpy / sklearn-GP / prophet / conformal-self** |

**18 wrappers cumulatively** establish Pattern A.1 (same-
library reproducibility verification with seed pinning + cuDNN
deterministic). All 18 achieved 0.0 abs diff or near-machine
precision. **Pattern A.1 is now the dominant Phase 3 pattern.**

### Pattern F → 14 concrete invariants

**Two new invariants populated this batch** (replacing Session
5 stubs):

| Invariant | Wrapper | Status |
|---|---|---|
| `conformal_nominal_coverage` | `p3_conformal` | PASS (0.8625 coverage @ alpha=0.1; nominal 0.9; within finite-sample slack) |
| `conformal_interval_containment` | `p3_conformal` | PASS (0 violations of lower ≤ upper) |

**14 concrete invariants in production** (was 12 at Batch 7
close).

### Pattern J catalog appends

3 new entries (B.5 PyTorch / framework-incompatibility):

- **B.5.1 neuralforecast 0.1.0 + pytorch-lightning incompatibility on Python 3.14** —
  AttributeError on `pl.utilities.distributed`. Resolution:
  use direct PyTorch self-parity (TSL's NBEATS/NHITS already
  use direct torch.nn).
- **B.5.2 GPyTorch vs sklearn.gaussian_process namespace mismatch** —
  master plan §15.11 named GPyTorch; TSL wrapper actually
  uses sklearn. Resolution: align reference to actual TSL
  backend, not master-plan-stated reference.
- **B.5.3 PyTorch state isolation via in-test seed reset** —
  PyTorch's manual_seed + cuDNN deterministic flag, set at
  the START of each fit/predict, gives bit-exact
  reproducibility without subprocess isolation. Same-process
  state leak is benign as long as both arms reset before
  use. Documented as alternative to PyBridge.isolate=True
  for in-process DL parity tests.

### PyBridge isolate=False shim retired (per S12 decision)

Per Session 12 check-in 1.5 act-now decision #3, this commit
retires the PyBridge `isolate=False` shim:

```python
if not isolate:
    raise PyBridgeError(
        "PyBridge.py_invoke now requires isolate=True. "
        "The in-process shim was retired in Session 13 ..."
    )
```

PyBridge is now subprocess-isolation-only. In-process Python
references continue using the established direct-import
pattern (p3_pca / p3_dfm / now 18 same-library Pattern A.1
wrappers).

Architectural simplification: PyBridge purpose narrowed to
its essential role (subprocess isolation for DL state
preservation). The `isolate=True` path is preserved for
future use.

### Pattern H DSCD candidates ruled out (again)

S13 hypothesis (cross-framework wrappers may produce
DSCD-Identifiability) ruled out: TSL uses single-library
backbones (PyTorch nn for DL; sklearn for GP; reservoirpy for
ESN; prophet for Prophet). Same-library means no
cross-framework optimizer divergence; bit-exact parity at all
9 wrappers. **Pattern H DSCD count remains 4.**

## §10.3 criteria — fourth consecutive batch passing both 1 and 2

| Batch | Criterion 1 | Criterion 2 sub-criterion |
|---|---|---|
| Batch 6 (S10) | 80% improvement | 30-40% (criterion 2c) |
| Batch 7 (S11) | 70% improvement | 35-45% (criterion 2c) |
| Batch 8 (S12) | 7 wrappers/session | 55-70% (criterion 2c) |
| **Batch 9 (S13)** | **9 wrappers/session vs 3-session budget** | **50-60% (criterion 2c)** |

Sub-criterion 2c (distinct-wrapper Python in-process / self-
parity ≥30%) reported. No subprocess-isolated checks this
batch (PyTorch state isolation done via in-test seed reset;
shim retired). Criterion 2d ("subprocess-isolated DL")
candidate from S12 prompt is **not exercised this batch**;
remains reserved for any future check that genuinely needs
PyBridge.isolate=True.

## DL non-determinism risk — pre-budget vs actual

Master plan §17.1 risk 2: pre-budgeted ≥30% Tier C for
Batch 9 (DL non-determinism). **Actual Tier C count: 0/9.**

Empirical result: with rigorous seed pinning (torch +
numpy + random) + cuDNN deterministic flag, ALL 9 DL
wrappers achieved bit-exact same-library parity. The risk
budget overestimated DL non-determinism by 30 percentage
points.

Implication for Item 12 (verdict-runtime alignment): Tier C
runtime outcome is **not needed** for any current Phase 3
wrapper. The CAVEAT proxy + diagnostic note convention
(established at Session 8 for `p3_nar_narx` + extended at
Session 11 for `p3_emd_hht`) covers all in-scope NO-REFERENCE
cases. Item 12 disposition: **no harness change needed**;
defer formalization to P-2 documentation phase.

## Aggregate Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 3 covered (cumulative through Batch 9) | **59** (Batches 1+2+3+4+5+6+7+8+9 complete) |
| Phase 3 remaining | 11 |
| Phase 3 sessions used | 12 (S2–S13) |
| **Pace** | **6+ sessions ahead; closure horizon at 17 (optimistic end of locked Item 13 range)** |
| BLOCK | 0 |
| CAVEAT cumulative | 5 (unchanged from Batch 8: p3_stl, p3_mstl, p3_star, p3_nar_narx, p3_emd_hht) |
| Pattern A wrappers | **36** (was 27 at Batch 8 close) |
| Pattern A.1 same-library sub-class | **18** wrappers (locked at scale) |
| Pattern F concrete invariants | **14** (was 12) |
| Pattern J catalog entries | **9** (was 6; +3 B.5 framework entries) |

## CI install matrix update

Batch 9 install additions in this commit:
- Python: `reservoirpy` (0.4.1), `prophet` (1.3.0); torch
  already in matrix
- R: no additions (no R refs this batch)

Deps explicitly ruled out:
- neuralforecast — Python 3.14 incompatibility
- gpytorch — TSL wrapper uses sklearn instead
- mapie — TSL conformal uses pmdarima base; self-parity
  reference suffices

## Next session

Session 14 — Batch 10 entry per master plan §15.12 (misc /
Tier C / deferred including `x13_seasonal_adjust`). ~10
wrappers in scope. Then Chat check-in 2 follows Session 14
close.

Effective closure horizon: **Sessions 17–18 (locked at
optimistic end of Item 13)**. Phase 3 buffer absorbs savings;
documentation phase Sessions 15-17; closeout Session 18.
