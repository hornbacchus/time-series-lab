# Phase 4 Session 4 — BYF candidate #2 Minnesota dummy-obs Pattern A.3

**Date:** 2026-05-01
**Scope:** Phase 4 master plan §15 S4 — close BYF candidate #2 via
Pattern A.3 self-parity reimpl. Introduce shared scaffold helpers
(`_pattern_a_helpers.py`) for the Pattern A audit cluster S4–S6.
**Status:** COMPLETE. PASS-A.3 (1318 elements bit-exact at 0.0 abs
diff across two configs).

## Pre-flight: R BVAR availability check

Per S4 trigger, verified R BVAR (Kuschnig & Vashold 2021) install
on R 4.5.3 BEFORE building the scaffold (Phase 3 hit unavailable
references on `bvars`; Phase 4 might hit similar issues). Outcome:

```
BVAR currently installed: FALSE
---attempting install BVAR---
package 'BVAR' successfully unpacked and MD5 sums checked
---verify install---
BVAR post-install installed: TRUE
BVAR loaded; version: 1.0.5
Available functions: bv_alpha, bv_dummy, bv_fcast, bv_irf, bv_lambda,
bv_metropolis, bv_mh, bv_minnesota, bv_mn, bv_priors, bv_psi, bv_soc,
bv_sur, bvar, companion, fevd, fevd<-, fred_code, fred_md, fred_qd
```

R BVAR available. **S5 may proceed as planned per master plan
§15 S5.** S4 proceeds per main-scope branch (R BVAR not actually
needed at S4 — Pattern A.3 reimpl is pure Python — but pre-flight
ensures S5 environment is known-good).

## Scaffold design — `_pattern_a_helpers.py`

Per S4 trigger discipline ("helpers should accept fixture / tolerance
/ comparison parameters via injection, not hard-coded for Minnesota.
S5 and S6 depend on generalizable scaffold quality"):

```python
# tools/reference_parity/harness/checks/_pattern_a_helpers.py

def synthesize_bvar_panel(*, seed, n_vars, n_lags, T,
                          A_blocks=None, sigma_innov=None) -> dict:
    """VAR(p) panel generator. Used by S5 (R BVAR cross-check) +
    S6 (stochvol partial). S4 doesn't need synthetic data — the
    Minnesota dummy-observation construction operates on
    configuration alone, not panel values. Default A_blocks =
    diagonal-decay matrices with spectral radius < 1."""

def synthesize_minnesota_config(*, n_vars, n_lags, seed) -> dict:
    """Build a complete, consistent Minnesota-prior hyperparameter
    configuration. Exercises all 5 dummy blocks (A coefficients,
    B covariance, C intercept, D sum-of-coefs, E initial-obs)."""

def compare_array_pair(tsl, ref, *, abs_tol, rel_tol, name) -> dict:
    """Element-wise comparison at Pattern A tolerance bands.
    PASS / CAVEAT / BLOCK status with max_abs_diff, max_rel_diff,
    n_compared. Drop-in compatible with ParityResult.metrics dict
    shape."""
```

Three injectable helpers; all three caller-side parameters
(fixture, tolerance, comparison) are passed via signature, not
hard-coded for any specific audit. S5 and S6 will reuse
`synthesize_bvar_panel` (data fixture) + `compare_array_pair`
(comparison). S4 uses `synthesize_minnesota_config` (config-only
fixture) + `compare_array_pair`.

**Total scaffold LOC:** ~190.

## Audit script — `p3_byf_minnesota_dummies.py`

Pattern A.3 self-parity reimplementation of the Sims-Zha 1998 / BGR
dummy-observation construction. The reference is a from-scratch
reimpl following Doan-Litterman-Sims 1984 §3 + Sims-Zha 1998
verbatim; bit-exact comparison applies (closed-form arithmetic on
identical hyperparameter inputs must produce element-wise
identical arrays).

**Five dummy blocks reimplemented:**

| Block | Rows | Description | Reference |
|---|---|---|---|
| A | n*p | Coefficient priors (sigma + lag-decay scaling) | DLS-1984 §3 |
| B | n | Covariance prior (sigma diag) | BGR-2010 §3.4 |
| C | 1 | Intercept diffuse (1/lambda_4) | Sims-Zha 1998 |
| D | n | Sum-of-coefficients (unit-root prior) | Sims-Zha 1998 |
| E | 1 | Initial-observation (cointegration-friendly) | Sims-Zha 1998 |

**Two test configurations** in `BYFMinnesotaDummiesParity.CONFIGS`:

- 3-var × 2-lag (n_d=14 dummy rows; X_d shape (14, 7))
- 6-var × 4-lag (n_d=38 dummy rows; X_d shape (38, 25))

Total comparison: 42 + 98 + 228 + 950 = **1318 elements per audit
run**, all at machine-epsilon tolerance.

**verdict_class:** `closed_form` per master plan §7.1.
**Tier:** `fast` (~10ms wall-clock; pure matrix construction).

## Mid-session §11.9 trigger investigation (NOT escalated)

Initial audit run produced **BLOCK** with max_abs_diff = 0.00999 on
both configs' X_d arrays. Per S4 trigger discipline ("§11.9
escalation trigger ACTIVE: if Pattern A audit reveals actual
divergence (not methodology-equivalent), do NOT silently bank-and-fix
mid-session"), I investigated before any code change.

**Diagnosis:** the divergence localized to a single column of X_d
(column 0, the intercept-prior row in Block C). The mathematical
structure: TSL writes `X_d[offset, 0] = 1.0 / lambda_4`; reference
reimpl writes the same `1.0 / lambda_4`. Same formula, divergent
output → must be different `lambda_4` values flowing into the two
sides.

Confirmed: the audit script's `synthesize_minnesota_config` set
`lambda_4 = 100.0` and passed it to the reference reimpl. The TSL
construction did NOT pass `lambda_4` to `MinnesotaPrior(...)` —
TSL fell back to its constructor default (`lambda_4 = 1e5` per
`priors.py:102`). So `1.0 / 100 = 0.01` (reference) vs
`1.0 / 1e5 = 0.00001` (TSL) → max_abs_diff = 0.00999.

**Disposition: §11.9 NOT triggered.** Both implementations execute
the same formula correctly with the inputs they received. The
divergence was an **audit-script-side bug** (inconsistent
hyperparameter passing) — methodology-equivalent in the §11.9
sense. Fix:

1. Update `synthesize_minnesota_config` default `lambda_4` from
   `100.0` to `1e5` to match TSL convention (more realistic for
   users; less likely to mislead future audits).
2. Pass `lambda_4=cfg["lambda_4"]` to TSL's `MinnesotaPrior(...)`
   constructor in `run_tsl`, so both sides receive identical
   hyperparameters.

After fix: bit-exact PASS on both configs. **Genuine §11.9 trigger
would have required a divergence in the formula or its
implementation; this was a test-script wiring error.**

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ 96 passed |
| `parity-fast --check-environment` clean | ✅ |
| New audit (`p3_byf_minnesota_dummies`) PASS | ✅ 1318 elements bit-exact at 0.0 abs diff (config_0::Y_d 42 elem; config_0::X_d 98 elem; config_1::Y_d 228 elem; config_1::X_d 950 elem) |
| Fast-tier outcome distribution | ✅ **73 PASS + 5 CAVEAT, 0 BLOCK** (was 72+5; +1 from new audit) |
| Existing wrappers unaffected | ✅ no engine code touched; only new harness files |

## File topology

| File | Action | LOC |
|---|---|---|
| `tools/reference_parity/harness/checks/_pattern_a_helpers.py` | NEW (scaffold for S4-S6) | ~190 |
| `tools/reference_parity/harness/checks/p3_byf_minnesota_dummies.py` | NEW (Pattern A.3 audit) | ~270 |
| `tools/reference_parity/harness/tolerances.py` | New `p3_byf_minnesota_dummies` ladder entry (closed_form 1e-15) | +30 |
| `docs/reference_parity_phase4/session_4_findings.md` | NEW (this file) | ~180 |
| **Total** | | **~670 LOC** |

## v1.2.0 amendment ledger update

S4 contributes to the P-2 v1.1.x → v1.2.0 ledger per master plan
§15.1:

- **P-2 §C.3/§C.4 NEW**: BYF Minnesota dummy-obs Pattern A.3 entry
  (~40 LOC). Pending S12 issuance.

Accumulated v1.2.0 amendment LOC at S4 close:
- P-1: ~75 (S1 §8.5)
- P-2: ~40 (S4 §C.3/§C.4)
- C-1: ~50 (S1 §4.6)
- **Total: ~165** (under §11.11 ceiling 600)

## Disposition

| Item | Pre-S4 status | Post-S4 status |
|---|---|---|
| BYF candidate #2 (Minnesota dummy-obs Pattern A.3) | banked Phase 4 | **CLOSED** (PASS-A.3 1318/1318 bit-exact) |
| 13-item inheritance register | 10 open + 3 closed | **9 open + 4 closed** |
| Phase 4 cycle progress | 3 of 13 sessions complete | **4 of 13 sessions complete** |
| Pattern A audit cluster S4-S6 | scaffold pending | **scaffold built; #2 audit done; S5/S6 ready** |

## Banked observations from S4

**B-Phase4-S4-1 — Audit-script hyperparameter wiring discipline.**
The mid-session BLOCK was caused by the audit script passing
`lambda_4` to the reference reimpl but not to TSL's constructor.
Pre-fix verdict was BLOCK; post-fix PASS at 0.0 abs diff. Future
Pattern A audits in S5/S6 (and any subsequent Phase A audits)
should systematically pass ALL hyperparameters explicitly to both
TSL and reference sides — never rely on default-fallback alignment.

The §11.9 trigger framework correctly distinguishes
"methodology-equivalent divergence" (this case; audit-script
wiring) from "actual wrapper bug" (escalation-worthy). The
investigation discipline is the gate; the formula is sound.

**B-Phase4-S4-2 — Scaffold injectability holds.** Per S4 trigger
("S5 and S6 depend on generalizable scaffold quality"):
`_pattern_a_helpers.py` is consumed by `p3_byf_minnesota_dummies.py`
via narrow injection (`synthesize_minnesota_config` + `compare_array_pair`).
S5/S6 will exercise `synthesize_bvar_panel` (data fixture) +
`compare_array_pair` (comparison) without touching
`synthesize_minnesota_config`. The three helpers are
independently consumed; no cross-contamination.

## Next session

**S5 — BYF candidate #1 R `BVAR` constant-vol Pattern A.2.** R
BVAR pre-flight verified at S4. Proceed per master plan §15 S5:
fit TSL BVAR-SV with stochastic-vol OFF (constant-vol mode);
R `BVAR::bvar()` at same prior config; compare Minnesota-prior
coefficient posteriors at `mcmc` tolerance band (5e-3 abs /
5e-2 rel). ~250 LOC R audit harness. §11.9 trigger remains
ACTIVE for S5 — divergence > 1 order beyond tolerance must
escalate.
