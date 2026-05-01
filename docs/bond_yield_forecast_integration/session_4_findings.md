# Bond Yield Forecast Session 4 — Parity audit at P-1 v1.1.0 standard

**Date:** 2026-05-01
**Scope:** Reference selection, audit script, tolerance ladder,
fixture pin, audit execution, verdict assignment per integration
plan §4.
**Status:** COMPLETE.

## Pre-Session 4 verification gate

| Check | Status |
|---|---|
| Session 3 commit `39fd4e6` + CI run 25212421737 success | ✓ |
| Dispatch test 8/8 PASS (S2 6 cases + S3 2 carry-forward cases) | ✓ |
| Migration tests 86 PASS + 16 SKIP unchanged | ✓ |
| Parity-fast 76/76 unchanged | ✓ |
| Existing `engine/techniques/bvar.py` unchanged | ✓ |
| Sample template + Ribbon dropdown shipped | ✓ |

## Reference-selection decision

Per integration plan §4.1 fallback discipline:

### R `bvars` (Krueger) — Pattern A.2 primary candidate: UNAVAILABLE

`install.packages("bvars", repos="https://cloud.r-project.org")` on R 4.5.3 returns:

```
Warning: package 'bvars' is not available for this version of R
Error: there is no package called 'bvars'
```

Per plan §4.1 fallback ("if R `bvars` Pattern A.2 doesn't work cleanly, do not force it") — selection moves on.

### Pattern A.3 paper-formula reimpl: OUT OF LOC BUDGET

A faithful from-scratch BVAR-SV reimpl (CCM-2019 + KSC-1998 + CK-1994 + K-FS-2014) is ~1000 LOC across 6+ modules — same order of magnitude as TSL's own implementation. Out of session-LOC budget for a single audit script.

### Selected: Pattern A.1 + Pattern F

- **Pattern A.1 same-implementation reproducibility self-parity:** invoke TSL twice with identical seed; assert byte-identical output across all `BVARSVResults` arrays. Validates determinism contract.
- **Pattern F structural invariants:** mathematical-property checks (VAR companion eig < 1; SV |φ| < 1; PCA explained-variance ≥ 99%; coef finiteness).

This combination matches Phase 3 precedent for techniques without a clean cross-reference (e.g., `critical_slowing_down`).

## Audit script — `tools/reference_parity/harness/checks/p3_bond_yield_forecast.py`

| Attribute | Value |
|---|---|
| Class | `BondYieldForecastParity(P3ParityCheck)` |
| `technique_id` | `p3_bond_yield_forecast` |
| `tier` | `fast` (~20s wall-clock; reduced chain config) |
| `verdict_class` | `mcmc` |
| `fixture_id` | `""` (no on-disk loader; canonical .xlsx referenced via path) |
| `reroll_on_caveat` | `False` (deterministic given seed) |
| Audit chain | `n_draws=2000`, `n_burn=500`, `seed=20260427` |

**Run protocol:** `_invoke_dispatch` runs the BVAR-SV estimation directly (mirrors `_dispatch._build_panel_in_memory` + `BVARSV.estimate()` invocation). The dispatch's table-summary output isn't byte-comparable; the audit needs raw posterior arrays. Both `run_tsl()` and `run_reference()` invoke `_invoke_dispatch()` with the same seed; bit-exactness comes from numpy + numba determinism.

## Tolerance ladder — `harness/tolerances.py`

```python
"p3_bond_yield_forecast": {
    "type": "tiered_outputs",
    "primary": {
        "abs_tol": 1e-15,    # Pattern A.1 bit-exact
        "rel_tol": 1e-15,
        ...
    },
    "secondary": {
        "abs_tol": 5e-3,     # reserved for Phase 4 Pattern A.3
        ...
    },
    "justification": "..."   # explains R bvars unavailability + selection
}
```

The strict `abs_tol=1e-15` reflects what's achievable at same-implementation reproducibility, not the typical mcmc inter-implementation tolerance band. Structural invariants are property-level (PASS by threshold; no abs/rel tolerance band).

## Audit results — verdict: PASS (10/10)

### Pattern A.1 reproducibility (6 arrays)

| Array | Shape | n_compared | max_abs_diff | Status |
|---|---|---:|---:|---|
| coefficients | (1500, 6, 25) | 225,000 | **0.0** | PASS |
| A_lower_triangular | (1500, 6, 6) | 54,000 | **0.0** | PASS |
| log_volatilities | (1500, 139, 6) | 1,251,000 | **0.0** | PASS |
| mu | (1500, 6) | 9,000 | **0.0** | PASS |
| omega | (1500, 6) | 9,000 | **0.0** | PASS |
| phi | (1500, 6) | 9,000 | **0.0** | PASS |

**1,557,000 elements bit-exact** across two TSL invocations.

### Pattern F invariants (4 checks)

| Invariant | Measurement | Threshold | Status |
|---|---:|---:|---|
| VAR companion-form max\|eig\| | 0.948 | < 0.999 PASS | **PASS** |
| SV \|φ\| (max across 6 equations) | 0.996 | < 0.999 PASS | **PASS** |
| PCA explained-variance ratio | 0.9991 | ≥ 0.99 PASS | **PASS** |
| Coef finiteness | 0 non-finite | = 0 PASS | **PASS** |

**Overall verdict: PASS.** No CAVEAT, no BLOCK, no ERROR.

### Mid-session corrections (banked as audit-script discoveries)

Three iteration cycles before final PASS:

1. **PCA loadings convention misread** (initial ERROR): the BVAR subpackage stores loadings as `pca.components_.T` (n_features × n_components) rather than the standard sklearn `pca.components_` (n_components × n_features). My initial encode/decode used the standard convention. Fix: reread `data.py:392` and adjust matmul orientation. Resolved in the same session.

2. **Companion-form intercept position** (initial BLOCK with max\|eig\|=2.96): the BVAR design matrix layout has the intercept as the FIRST column (`X[:, 0] = 1` per `estimation._build_lag_design`), not the last. My initial code dropped the LAST column for companion construction. Fix: drop the FIRST column instead. Max\|eig\| dropped to 0.948 — clean PASS.

3. **PCA roundtrip semantics** (initial BLOCK with residual=0.41): the BVAR pipeline uses a TRUNCATED PCA (3 components out of 10 maturities) per `data.py:382-383`. A full encode-decode roundtrip on a truncated PCA is intentionally lossy by definition — the reconstruction residual reflects unmodeled variance in the 4th-10th PCs, not a numerical bug. Replaced "PCA roundtrip residual" invariant with the meaningful "PCA explained variance ratio ≥ 99%" invariant per Litterman-Scheinkman 1991. Truncated reconstruction residual surfaced as diagnostic-only field.

These three iterations are documented as **audit-script learning, not BVAR/wrapper bugs.** The wrapper is correct; my audit-side computations needed alignment with the migrated subpackage's internal conventions.

## Verification gates

| Gate | Status |
|---|---|
| Audit verdict (10 checks) | **PASS** (10/10) |
| Audit wall-clock | ~20s (fast tier) |
| Migration test suite (102 collected) | 86 passed + 16 skipped unchanged from S3 |
| Fast-tier sweep (now 77 with new check) | **72 PASS + 5 CAVEAT, 0 BLOCK** (was 71+5 pre-S4) |
| Existing `engine/techniques/bvar.py` | UNCHANGED |
| Catalog JSON | unchanged from S2 (no new params) |
| `--check-environment` | clean |

## Plan §4.5 outcome dispositions

Plan §4.5 listed 4 possible outcomes. Reality: **Outcome 1 (PASS) at full P-1 v1.1.0 standard**, with the caveat that the "PASS" is at the strict same-implementation reproducibility level, not at cross-implementation parity (which was the plan's underlying intent).

| Outcome | Disposition |
|---|---|
| 1. PASS at full Phase 3 standard | **Achieved** at the strict reproducibility level. Limitation: no cross-implementation reference — see audit report §4.1-4.4 for what this verifies / does not verify. |
| 2. CAVEAT | Not triggered |
| 3. DOCUMENTED-DIVERGENCE | **Not exercised at runtime in any Phase 3 / Phase 3.5 / BYF audit yet.** Forward-provisioning per Phase 3.5 Session 1 holds. |
| 4. BLOCK | Not triggered |

**Plan §4.5 Outcome 1 banking note:** "Bank as P-3 v1.2.0 evidence for Pattern H DSCD-MCMC sub-class if applicable." DSCD (Documented Sub-Class Divergence) requires inter-implementation evidence; Pattern A.1 self-parity doesn't surface DSCD-MCMC directly. **Not banked at this audit.** When a future cross-implementation Pattern A.2/A.3 audit lands, that's the first opportunity to bank a DSCD-MCMC entry.

## Banked items (Session 5+ / Phase 4)

| Item | Disposition |
|---|---|
| Investigate R `BVAR` (Kuschnig & Vashold) constant-vol cross-check | Phase 4 |
| Partial Pattern A.3 reimpl: Minnesota dummy-observation construction in isolation | Phase 4 |
| Stochvol cross-check via rpy2 (`validation.py`): partial Pattern A.2 for SV component only | Phase 4 |
| P-2 §B.6 entry if R `bvars` becomes available in future R release | Session 11 / Phase 4 docs |
| Conditional-forecast invariants (curve smoothness; horizon-monotonicity) | Phase 4 |
| Re-bench audit at default chain config (n_draws=10000) — confirm bit-exactness scales beyond reduced chain | Banked for Phase 4 nightly slow-tier |

## Schedule status

Bond Yield Forecast cycle: **4 of 6 TSL-side sessions complete.**
Sessions 5-6 follow per locked plan. No Session 4.5 continuation
needed — closed at single session per plan §"Session 4.5
reservation."

## Commit footprint

| File | Change |
|---|---|
| `tools/reference_parity/harness/checks/p3_bond_yield_forecast.py` | new ~360 LOC (audit script with self-parity + 4 invariants) |
| `tools/reference_parity/harness/tolerances.py` | +50 LOC (`p3_bond_yield_forecast` tolerance ladder entry) |
| `tools/reference_parity/reports/p3_bond_yield_forecast_audit.md` | new ~270 LOC (audit report) |
| `docs/bond_yield_forecast_integration/session_4_findings.md` | new ~250 LOC |
| **Total** | **~930 LOC across 4 files** |

## Next session

Bond Yield Forecast Session 5 — MANIFEST + CI integration + JIT
warming integration with engine_worker + P-4 v1.1.x update per
integration plan §5.
