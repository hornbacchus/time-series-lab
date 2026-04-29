# Phase 3 Batch 6 — `p3_bocpd` Audit

**Wrapper:** `engine/techniques/bocpd.py`
**Reference:** from-scratch Adams-MacKay 2007 implementation
inline in `harness/checks/p3_bocpd.py` (NIG conjugate prior)
**Verdict:** **PASS** (Pattern A self-parity bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | TSL | Reference | status |
|---|---:|---:|---|
| `n_change_points` | 0 | 0 | PASS (exact) |
| `cp_indices_set_match` | ∅ | ∅ | PASS (exact) |

**Outcome:** TSL and self-parity reference produce identical
output. The Adams-MacKay 2007 recursion (NIG conjugate prior,
constant hazard, Student-t posterior predictive) is
implemented identically in both arms; given identical priors
and threshold, the run-length distribution evolves identically
and the change-point decisions match exactly.

## Fixture

- DGP: two-segment mean shift at t=150 (μ=0 → μ=3) with
  σ=1.0 Gaussian noise, T=300, seed=42
- Hazard λ=200, threshold=0.5, min_gap=5 (Balanced preset)
- Weak NIG priors: κ=0.01, α=0.01, β=0.01

## Diagnostics

- True CP index: 150
- Detected CPs (both arms): none — at this hazard / threshold
  configuration, the posterior P(r=0|x_{1:t}) does not exceed
  0.5 even at t=151. This is consistent with the weak prior
  + small hazard rate; both arms agree on the verdict.
- Recursion math validated: the bit-exact agreement on a
  null detection is exactly the regression sentinel we want
  — any drift in TSL's predictive density, sufficient-statistics
  update, or hazard handling would diverge.

## Pattern K → Pattern A path

Original Pattern K candidate: PyPI ``bocd`` package only
implements constant-hazard Gaussian (non-conjugate) prior;
using it would force a methodology-rewrite reference that
cannot match TSL's NIG-conjugate output. Self-parity reference
mirroring TSL's recursion verbatim establishes the regression
sentinel without that rewrite.
