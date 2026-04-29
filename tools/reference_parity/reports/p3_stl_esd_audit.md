# Phase 3 Batch 6 — `p3_stl_esd` Audit

**Wrapper:** `engine/techniques/stl_esd_anomaly.py`
**Reference:** from-scratch reference (statsmodels STL +
Generalized ESD test) inline in `harness/checks/p3_stl_esd.py`
**Verdict:** **PASS** (Pattern A self-parity bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | status |
|---|---:|---:|---|
| `n_anomalies` | 6 | 6 | PASS (exact) |
| `anomaly_indices_set_match` | identical | identical | PASS (exact) |

**Outcome:** TSL and reference detect the same 6 anomalies
at the same indices. Both arms invoke statsmodels STL with
identical configuration (period=12, seasonal_window=13,
inner_iter=5, outer_iter=2, robust=True) producing
bitwise-identical remainder. The Generalized ESD test
(Rosner 1983) is closed-form sequential — both arms apply
identical critical-value formula to identical remainder.

## Fixture

- DGP: 12-period sinusoidal seasonal + linear trend +
  N(0, 0.25) noise + 5 injected outliers (magnitude ±5σ)
  at randomly-selected non-edge positions, T=240, seed=42
- ESD config: α=0.05, max_anomalies=24 (10% of T), direction='both'

## Diagnostics

- 5 outliers injected; 6 detected (1 false positive — likely
  a noise observation that happens to fall in the rejection
  region after STL detrending)
- The set-equality match means TSL and reference agree on
  the false positive identity, not just count
- All 5 true outlier indices are detected by both arms

## Pattern J / K avoidance

Twitter ``AnomalyDetection`` R package (the historical
canonical STL+ESD reference) was archived from CRAN; no
actively-maintained CRAN successor matches the STL+ESD
recipe shape. Self-parity reference establishes the
regression sentinel. The reference is a faithful Rosner 1983
implementation (~80 LOC inline) so the comparison catches
any TSL drift in the ESD recursion, critical-value formula,
or anomaly-index extraction.
