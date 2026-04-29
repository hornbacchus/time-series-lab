# Phase 3 Batch 6 — `p3_cusum_page_hinkley` Audit

**Wrapper:** `engine/techniques/cusum_page_hinkley.py`
**Reference:** from-scratch identical-recursion implementation
inline in `harness/checks/p3_cusum_page_hinkley.py`
**Verdict:** **PASS** (Pattern A self-parity bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | status |
|---|---:|---:|---|
| `n_cusum_up` | 11 | 11 | PASS (exact) |
| `n_cusum_down` | 12 | 12 | PASS (exact) |
| `n_ph_up` | 190 | 190 | PASS (exact) |
| `n_ph_down` | 0 | 0 | PASS (exact) |

**Outcome:** all four alarm counters bitwise-identical
between TSL and the reference. Both implement identical
deterministic accumulator recursions:

- CUSUM upper: ``S_up[t] = max(0, S_up[t-1] + (y_t - target) - k)``
  with reset to 0 on alarm (``S_up[t] > h``).
- Page-Hinkley upper: ``m_t = m_{t-1} + (y_t - μ̂_t - δ)``,
  ``M_t = min(M_{t-1}, m_t)``, alarm if ``m_t - M_t > λ`` and
  ``t > 10``.

## Fixture

- DGP: single mean shift at t=200 (μ=0 → μ=1.5), σ=1.0
  Gaussian noise, T=400, seed=42
- Thresholds chosen to actually trigger alarms on the 1.5σ
  shift (``cusum_h=3*sigma`` rather than the default
  ``5*sigma``; ``ph_lambda=20`` rather than 50)
- Fast preset (no bootstrap) for determinism

## Diagnostics

- True shift: t=200
- Total alarms across all four channels: 213 (TSL) = 213
  (reference)
- The PH-upper count of 190 reflects PH's no-reset semantics
  (unlike CUSUM, which resets after each alarm); both arms
  share this convention so the comparison remains genuine.

## Pattern J avoidance

R ``cpm`` (Adams-Ross changepoint models, Generalized-Lambda
test statistics) and R ``changepoint`` (PELT-style cost
functions on segment likelihood) implement different
formulations and would not match TSL's specific recursion.
Self-parity is the only path to bit-exact verdict on the
exact wrapper math; this catches preprocessing /
parameter-forwarding regressions.
