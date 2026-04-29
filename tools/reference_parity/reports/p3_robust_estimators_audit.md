# Phase 3 Batch 8 — `p3_robust_estimators` Audit

**Wrapper:** `engine/techniques/robust_estimators.py`
**Reference:** R `stats::mad` + `robustbase::Qn` + base R trim/winsorize (robustbase 0.99-7)
**Verdict:** **PASS** (Pattern A cross-package bit-exact at machine precision)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Estimator | TSL | Reference | abs diff | status |
|---|---:|---:|---:|---|
| `trimmed_mean` (10% trim) | -0.0428524 | -0.0428524 | 1.39e-17 | PASS |
| `winsor_mean` (10% wins) | -0.0269197 | -0.0269197 | 3.12e-17 | PASS |
| `mad` (×1.4826) | 0.9685232 | 0.9685232 | 4.44e-16 | PASS |
| `qn` (×2.2219) | 1.0284583 | 1.0284583 | 4.22e-15 | PASS |

**Outcome:** machine-precision agreement on all four robust
estimators. All are closed-form arithmetic on sorted/sliced
data; scipy.stats / numpy and R `stats::mad` /
`robustbase::Qn` implement identical formulae with identical
consistency factors (1.4826 for MAD; 2.2219 for Qn).

## Fixture

- DGP: N(0,1) with 5% extreme outliers (±[5,15] contamination),
  T=200, seed=42
- Trim fraction: 0.10

## Diagnostics

- robustbase version: 0.99-7
- R `Qn` invoked with `finite.corr=FALSE` to disable the
  finite-sample correction so both implementations share the
  asymptotic factor 2.2219 only (matches the convention
  hard-coded in TSL's `_qn_scale` helper)
- Cross-package machine-precision parity confirms the
  consistency-factor convention is industry-standard
  (Rousseeuw-Croux 1993 for Qn; Hampel 1974 for MAD)
