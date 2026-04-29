# Phase 3 Batch 6 — `p3_pelt` Audit

**Wrapper:** `engine/techniques/pelt_change_points.py`
**Reference:** direct in-process `ruptures.Pelt` invocation
(same library; ruptures 1.1.9)
**Verdict:** **PASS** (Pattern A bit-exact same-library)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | status |
|---|---:|---:|---|
| `n_change_points` | 2 | 2 | PASS (exact) |
| `positions_set_match` | {a, b} | {a, b} | PASS (exact) |

**Outcome:** TSL and reference produce identical breakpoint
counts AND identical breakpoint positions. ``ruptures.Pelt``
is deterministic dynamic programming (Killick-Fearnhead-
Eckley 2012) — given identical model='l2', min_size=5,
jump=1, and pen=log(n)*sigma², output is bitwise-identical.

## Fixture

- DGP: 4-segment piecewise-constant signal with means drawn
  from N(0, 4) per segment, σ=1.0 noise within segment, T=600,
  seed=42
- Penalty: ``log(n) * Var(y)`` (BIC-like; same formula TSL's
  wrapper applies internally for "bic" string)

## Diagnostics

- True segments: 4 (3 internal change points)
- Detected change points (both arms): 2 — fewer than the
  ground truth's 3, because the BIC penalty under-segments
  on a fixture where one of the segment-mean transitions is
  small relative to noise. Both arms agree on the under-
  segmentation, which is the regression sentinel.
- ruptures version: 1.1.9

## Same-library design rationale

This is a SAME-LIBRARY parity test, not a cross-package
comparison. The audit purpose is to verify that TSL's
preprocessing (NaN handling, time-axis alignment), parameter
resolution (string-to-numeric penalty mapping), and audit-
field rounding round-trip ``ruptures.Pelt`` output without
introducing wrapper-level bugs. Cross-package comparison
(R changepoint, R cpm) was rejected because those packages
implement non-PELT change-point algorithms.
