# Calibration Audit: Specialized Neural batch (Session 25)

**Audit date:** 2026-04-27
**Wrappers audited (3):**
  - `engine/techniques/nhits_forecast.py`
  - `engine/techniques/autoencoder_anomaly.py`
  - `engine/techniques/echo_state_network.py`

## Summary

**Findings: 2 severe / 5 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~95 across 3 files
(within raised 150-LOC budget for multi-wrapper batches).

**KEY FINDING: N-HiTS pooling_sizes pattern PROPAGATED from
Session 24's N-BEATS stack_types finding.** The two architectures
share lineage and the wrapper-level Follow-up 1a fix used
identical try/except-pass pattern that silently fell through to
preset on invalid input. Both now fixed.

| ID | Severity | Wrapper | Bug Class |
|---|---|---|---|
| F-SN-NHITS-POOLING | severe | nhits_forecast | string fall-through `pooling_sizes` |
| F-SN-NHITS-POOLING-NEG | severe | nhits_forecast | numeric content fall-through `pooling_sizes` (same fix) |
| F-SN-NHITS-HORIZON | operational | nhits_forecast | numeric range `horizon` |
| F-SN-AE-CONTAMINATION | operational | autoencoder_anomaly | numeric range `contamination` |
| F-SN-ESN-HORIZON | operational | echo_state_network | numeric range `horizon` |
| F-SN-ESN-SPECTRAL | operational | echo_state_network | numeric range `spectral_radius` |
| F-SN-ESN-LEAK | operational | echo_state_network | numeric range `leak_rate` |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Wrapper | (1) String | (2) try/except | (3) Numeric | (4) Fall-through | (5) Multi-param |
|---|---|---|---|---|---|
| nhits_forecast | n/a | SAFE-FALLBACK (sklearn) | ❌→✅ | ❌→✅ pooling_sizes | OK |
| autoencoder_anomaly | n/a | SAFE-PROPAGATE | ❌→✅ contamination | n/a | OK |
| echo_state_network | n/a | SAFE-PROPAGATE + reservoirpy fallback | ❌→✅ × 3 | n/a | OK |

### N-HiTS pooling_sizes propagation analysis

Session 24 found `nbeats_forecast.stack_types` had a Follow-up
1a guard with `try: candidate = list(_user); if all(...): use; else: silent fallback`.
The pattern silently reverted to preset when invalid entries
appeared.

This Session probed the same pattern in `nhits_forecast`
(architectural sibling). At lines 330-338 pre-fix:
```python
_pooling_user = ctx.get_param("pooling_sizes", None)
if _pooling_user is not None:
    try:
        _candidate = list(_pooling_user)
        if all(isinstance(p, (int, float)) and p >= 1 for p in _candidate) and _candidate:
            preset_cfg["pooling_sizes"] = [int(p) for p in _candidate]
    except (TypeError, ValueError):
        pass  # ← silent fall-through!
```

**Confirmed: identical Session 18 silent-fall-through pattern.**
Both severe in same defect class, both fixed via explicit
allowlist-rejection.

### try/except taxonomy (Session 18 framework)

| Wrapper | Pattern | Classification |
|---|---|---|
| nhits_forecast | outer + sklearn fallback | SAFE-PROPAGATE + SAFE-FALLBACK |
| autoencoder_anomaly | outer | SAFE-PROPAGATE |
| echo_state_network | outer + reservoirpy fallback | SAFE-PROPAGATE + SAFE-FALLBACK |

No HARMFUL try/except suppression.

## Real-data baselines

| Wrapper | DGS10 (T=200) | GSPC log returns |
|---|---|---|
| nhits_forecast | success, 0.08s | n/a |
| autoencoder_anomaly | success, <0.01s | n_anomalies=0 (no extreme moves in last 200 obs) |
| echo_state_network | success, <0.01s | n/a |

**Cross-reference Session 15 anomaly results:** autoencoder
flagged 0 anomalies on the GSPC subsample; Session 15's
stl_esd_anomaly on similar GSPC found 17 anomalies on a
500-obs window. Different methods give different counts —
autoencoder requires extreme reconstruction error which is
sensitive to model capacity (small `hidden_dim=16` here is
intentionally restrictive for audit speed). Production runs
with larger autoencoders may flag more.

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Hierarchical interpolation forecasting | `nhits_forecast` | Multi-rate sampling; outperforms N-BEATS on long horizons |
| Unsupervised anomaly detection | `autoencoder_anomaly` | Reconstruction error; no labels needed |
| Fast nonlinear dynamics modeling | `echo_state_network` | Reservoir computing; trains in seconds |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-SN-NHITS-POOLING | Severe | invalid `pooling_sizes` silently fell through to preset | **Fixed inline** |
| F-SN-NHITS-POOLING-NEG | Severe | numeric-content invalid `pooling_sizes` (same fix) | **Fixed inline** |
| F-SN-NHITS-HORIZON | Op | horizon<1 silently coerced | **Fixed inline** |
| F-SN-AE-CONTAMINATION | Op | contamination out of (0,1) silently reset | **Fixed inline** |
| F-SN-ESN-HORIZON | Op | horizon<1 silently coerced | **Fixed inline** |
| F-SN-ESN-SPECTRAL | Op | spectral_radius<=0 silently accepted | **Fixed inline** |
| F-SN-ESN-LEAK | Op | leak_rate out of [0,1] silently accepted | **Fixed inline** |

## Validation-presence pattern update

Cumulative across 71 wrappers in 20 extension sessions:
- **WITH validation OR low math**: 36 wrappers → 0 findings
- **WITHOUT validation**: 35 wrappers → 62 severe/op findings (all fixed inline)

Pattern remains 100% predictive.

## Inventory roadmap update

After Session 25:
- 77 wrappers AUDITED (74 + 3)
- 6 wrappers UNAUDITED (4 statistical ML + 1 forecasting-classical residual + 1 deferred)
- **2 sessions remaining (S26-S27)**

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 3 wrapper APIs verified. |
| **CAL-R3** | 3 rows AUDITED. Cycle 74 → 77. |
| **CAL-R4** | 3 NEW canonical scripts (6 each = 18 canonicals). |
| **CAL-R5** | DGS10 + GSPC subsamples on all 3 wrappers. |
| **CAL-R6** | 7 inline fixes (~95 LOC across 3 files). Within raised 150 LOC budget. |

## Recommended follow-ups

None. Specialized Neural extension batch CLOSED.
