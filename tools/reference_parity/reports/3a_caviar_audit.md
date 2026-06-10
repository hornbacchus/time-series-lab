# 3a CAViaR multi-horizon — reference parity audit

**Date:** 2026-04-24

**Fixture:** GARCH(1,1) returns. T=500, seed=42, ω=0.01, α=0.05, β=0.9 (high persistence: α+β=0.9500000000000001). CAViaR-SAV fit at theta=0.05 (5% left-tail VaR).

**Verification strategy (Refinement R1):**
1. Build from-scratch Python reimpl of CAViaR-SAV
   following Engle-Manganelli 2004 equations:
       q_t = β_0 + β_1 · q_{t-1} + β_2 · |y_{t-1}|
       L(β) = (1/T) · Σ (θ − 1{y_t < q_t})(y_t − q_t)
2. R1 paper-validation: fit reimpl from fixed seed and
   check β_1 (persistence) ∈ [0.70, 0.95] on GARCH(α+β=0.95)
   simulation, and β_2 (coefficient on |y_{t-1}|) is negative
   for left-tail VaR.
3. Audit step (Nelder-Mead is non-deterministic across
   restarts):
    - Verify q-path-given-fixed-β bitwise match between
      TSL's converged β and reimpl's recursion.
    - Verify quantile-loss-given-fixed-β bitwise match.
    - Compare independently-converged β with looser
      tolerance accounting for Nelder-Mead local-optimum
      sensitivity.

**Tolerance:**
- q-path-given-fixed-β:   `abs_tol=1e-12, rel_tol=1e-12`
- quantile-loss-given-β:  `abs_tol=1e-6` (TSL rounds loss
  to 6 decimals via `round(loss, 6)` in audit_fields)
- β-converged:            `abs_tol=1e-2, rel_tol=5e-2`

## R1 paper validation — reimpl sanity

| Check | Value | Threshold | Verdict |
|---|---|---|---|
| Persistence β_1 | 0.8450 | in [0.70, 0.95] | PASS |
| Abs-return coef β_2 | -0.0751 | < 0 (left-tail VaR) | PASS |
| Intercept β_0 | -0.0798 | (no threshold) | — |
| Quantile loss | 0.041073 | (smaller=better) | — |

**R1 paper validation:** PASS

## TSL vs reimpl — converged β comparison

| Param | TSL | reimpl | abs_diff | rel_diff | Verdict |
|---|---|---|---|---|---|
| β_0 (intercept) | 0.002621 | -0.079786 | 8.241e-02 | 1.033e+00 | **DIVERGE** |
| β_1 (persistence) | 0.995075 | 0.845036 | 1.500e-01 | 1.508e-01 | **DIVERGE** |
| β_2 (|y_{t-1}| coef) | -0.018987 | -0.075082 | 5.610e-02 | 7.471e-01 | **DIVERGE** |

**β converged max abs diff:** 1.500e-01
**β converged max rel diff:** 1.033e+00

## TSL vs reimpl — q-path-given-fixed-β bitwise check

Using TSL's converged β, compute the q-path with the
from-scratch reimpl and compare to TSL's q-path (deterministic given β).

- max abs diff: **0.000e+00**
- max rel diff: **0.000e+00**
- verdict: **PASS**

## TSL vs reimpl — quantile-loss-given-fixed-β bitwise check

- TSL loss:    0.0404790000
- reimpl loss: 0.0404792291
- abs diff:    **2.291e-07**
- rel diff:    **5.659e-06**
- verdict: **PASS**

## TSL diagnostic outputs

| Field | Value |
|---|---|
| n_violations | 23 |
| expected_violations | 25.0 |
| violation_ratio | 0.92 |
| Kupiec p-value | 0.677587 |
| 1-step-ahead VaR | -0.771512 |
| Multi-horizon quantiles | {1: -0.74073, 5: -0.756637, 10: -0.741917} |
| Stationarity OK | False |

## Methodology notes

- **Optimization non-determinism.** Nelder-Mead on the
  CAViaR quantile loss is non-smooth (the indicator
  function makes the gradient discontinuous) and has
  multiple local optima. Different starting points and
  random-restart sequences can converge to slightly
  different β. The audit therefore uses a 3-tier
  verification:
    1. Strict (1e-12) bitwise check on the q-path and
       loss given any FIXED β,
    2. Loose (5%) check on independently-converged β,
    3. R1 paper-structure validation (persistence in
       expected range, sign of |y| coefficient).

- **Engle-Manganelli 2004 Table III SAV-1 estimates** (stocks):
    - Coca-Cola: β=(0.018, 0.876, -0.391), loss=0.097
    - Walt Disney: β=(0.005, 0.929, -0.273), loss=0.114
    - General Motors: β=(0.024, 0.847, -0.452), loss=0.131
  Persistence is consistently in 0.85-0.93; the
  coefficient on |y_{t-1}| is consistently negative
  (since q is negative for left-tail VaR). The audit's
  R1 thresholds reflect these empirical regularities.

- **Multi-horizon VaR** is Monte-Carlo simulated and
  contains genuine random noise. The audit doesn't
  parity-check multi-horizon values against an
  external reference (no off-the-shelf multi-horizon
  CAViaR is widely available); we report the values
  as an audit-trail diagnostic only.
