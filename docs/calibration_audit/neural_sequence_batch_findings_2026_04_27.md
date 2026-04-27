# Calibration Audit: Neural Sequence forecasters batch (Session 24)

**Audit date:** 2026-04-27
**Wrappers audited (4):**
  - `engine/techniques/lstm_gru_forecast.py`
  - `engine/techniques/tcn_forecast.py`
  - `engine/techniques/transformer_forecast.py`
  - `engine/techniques/nbeats_forecast.py`

## Summary

**Findings: 2 severe / 4 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~110 across 4 files
(within raised 150-LOC budget for multi-wrapper batches).

| ID | Severity | Wrapper | Bug Class |
|---|---|---|---|
| F-NN-LG-MODELTYPE | severe | lstm_gru_forecast | string fall-through `model_type` |
| F-NN-NB-STACKTYPES | severe | nbeats_forecast | string fall-through `stack_types` (list of strings) |
| F-NN-LG-HORIZON | operational | lstm_gru_forecast | numeric range `horizon` |
| F-NN-TCN-HORIZON | operational | tcn_forecast | numeric range `horizon` |
| F-NN-TF-HORIZON | operational | transformer_forecast | numeric range `horizon` |
| F-NN-TF-DMODEL | operational | transformer_forecast | multi-parameter consistency `d_model % n_heads != 0` |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Wrapper | (1) String | (2) try/except | (3) Numeric range | (4) Fall-through | (5) Multi-param |
|---|---|---|---|---|---|
| lstm_gru_forecast | ❌→✅ | SAFE | ❌→✅ | ❌→✅ same fix | OK |
| tcn_forecast | n/a | SAFE | ❌→✅ | OK | OK |
| transformer_forecast | n/a | SAFE | ❌→✅ | OK | ❌→✅ (d_model/n_heads) |
| nbeats_forecast | ❌→✅ | SAFE | ❌→✅ (added) | ❌→✅ same fix | OK |

### try/except taxonomy classification (Session 18 framework)

| Wrapper | Pattern | Classification |
|---|---|---|
| lstm_gru_forecast | outer make_error_response + sklearn fallback when torch unavailable | SAFE-PROPAGATE + SAFE-FALLBACK |
| tcn_forecast | outer + sklearn fallback | SAFE-PROPAGATE + SAFE-FALLBACK |
| transformer_forecast | outer + sklearn fallback + attention-exposure try/except (verification 3f machinery) | SAFE-PROPAGATE + SAFE-FALLBACK |
| nbeats_forecast | outer + sklearn fallback + per-block error catches | SAFE-PROPAGATE + SAFE-FALLBACK |

**No HARMFUL try/except suppression in this batch.** All 4
wrappers have a consistent pattern: try torch path, fall
back to sklearn MLPRegressor on torch unavailability or
explicit error. The fallback pattern is SAFE-FALLBACK
(retries with different specification — Session 18
structural_ts pattern).

## Real-data baseline (DGS10 yield, T=200)

All 4 wrappers SUCCESS with small-model defaults:

| Wrapper | Status | Runtime |
|---|---|---|
| lstm_gru_forecast | success | 0.01s |
| tcn_forecast | success | <0.01s |
| transformer_forecast | success | 0.01s |
| nbeats_forecast | success | 0.12s |

(Runtimes reflect tiny epoch budget of 5 for tractable
audit speed; production training takes 100-1000× longer.)

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| General-purpose sequence forecasting | `lstm_gru_forecast` | LSTM/GRU cells; well-understood; PyTorch + sklearn fallback |
| Parallelizable training on long sequences | `tcn_forecast` | Dilated convolutions; no sequential bottleneck |
| Long-range pattern attention | `transformer_forecast` | Multi-head attention; verification 3f tested attention-weight exposure |
| Interpretable trend+seasonal stacks | `nbeats_forecast` | Generic / trend / seasonality block decomposition |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-NN-LG-MODELTYPE | Severe | invalid model_type silently fell through to LSTM | **Fixed inline** |
| F-NN-NB-STACKTYPES | Severe | invalid stack_types silently reverted to preset default | **Fixed inline** |
| F-NN-LG-HORIZON | Op | horizon<1 silently coerced to 1 | **Fixed inline** |
| F-NN-TCN-HORIZON | Op | horizon<1 silently coerced to 1 | **Fixed inline** |
| F-NN-TF-HORIZON | Op | horizon<1 silently coerced to 1 | **Fixed inline** |
| F-NN-TF-DMODEL | Op | d_model not divisible by n_heads silently adjusted | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 68 wrappers in 19 extension sessions:
- **WITH validation OR low math**: 36 wrappers → 0 findings
- **WITHOUT validation**: 32 wrappers → 55 severe/op findings (all fixed inline)

Pattern remains 100% predictive. Neural wrappers had higher
finding density than tree forecasters (S23) due to:
- Custom string handling for model_type (lstm_gru) and
  stack_types (nbeats)
- Multi-parameter consistency (transformer d_model/n_heads)
- Same numeric range gaps as tree forecasters

## Inventory roadmap update

After Session 24:
- 74 wrappers AUDITED (70 + 4)
- 9 wrappers UNAUDITED (7 ML/DL + ets_hw + critical_slowing_down)
- **3 sessions remaining (S25-S27)**

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 4 wrapper APIs verified. |
| **CAL-R3** | 4 rows AUDITED. Cycle 70 → 74. |
| **CAL-R4** | 4 NEW canonical scripts (6 each = 24 canonicals). |
| **CAL-R5** | DGS10 (T=200) baseline on all 4 wrappers + sweeps. |
| **CAL-R6** | 6 inline fixes (~110 LOC across 4 files). Within raised 150 LOC budget. |

## Recommended follow-ups

None. Neural Sequence extension batch CLOSED.
