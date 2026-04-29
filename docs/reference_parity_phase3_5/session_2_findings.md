# Phase 3.5 Session 2 — Item 8: 12 pre-Phase-3 wrapper migration

**Date:** 2026-04-29
**Scope:** Item 8 only. Single-session.
**Status:** COMPLETE.

Migrates the 12 pre-Phase-3 inherited parity checks from
the legacy `ParityCheck` base (in `harness/base.py`) to the
P3ParityCheck contract (in `harness/check_base.py`) per the
S5-locked Session 5 mandate (verdict_class declaration
required for all new checks).

## Migration scope

12 check files:

| # | File | Audit ID | verdict_class assigned |
|---|---|---|---|
| 1 | `_smoke.py` | `_smoke_test` | `closed_form` |
| 2 | `bvar_irf_fevd.py` | `1c_bvar_irf_fevd` | `closed_form` |
| 3 | `caviar_sav.py` | `3a_caviar_sav` | `mle_fit` |
| 4 | `critical_slowing_down.py` | `critical_slowing_down` | `closed_form` |
| 5 | `evt_ferro_segers.py` | `3c_evt_ferro_segers` | `closed_form` |
| 6 | `har_cj.py` | `3b_har_cj` | `closed_form` |
| 7 | `johansen_bartlett.py` | `3d_johansen_bartlett` | `closed_form` |
| 8 | `kalman_filter.py` | `2a_kalman_filter_smoother` | `closed_form` |
| 9 | `mcmc_sv_gaussian.py` | `2b_mcmc_sv_gaussian` | `mcmc` |
| 10 | `mcmc_sv_student_t.py` | `2c_mcmc_sv_student_t` | `mcmc` |
| 11 | `mint_family.py` | `3e_mint_family` | `closed_form` |
| 12 | `transformer_attention.py` | `3f_transformer_attention` | `dl_seed_pinned` |

## Migration recipe (applied uniformly)

For each check, the migration changed:

1. **Import line:** `from reference_parity.harness.base import ParityCheck, ParityResult` →
   ```python
   from reference_parity.harness.base import ParityResult
   from reference_parity.harness.check_base import P3ParityCheck
   ```
2. **Class declaration:** `class XxxParity(ParityCheck):` →
   `class XxxParity(P3ParityCheck):`
3. **Added mandatory class attributes** per Session 5 lock:
   - `verdict_class` — one of the 11 registered classes
     (P-2 §A taxonomy)
   - `verdict_class_rationale` — 2-4 sentence justification
     citing Phase 1 audit numbers where available

Optional attribute set on MCMC checks:
- `reroll_on_caveat = True` (MC noise re-roll for 2b/2c).
  Other 10 checks inherit `False` from the P3ParityCheck
  default.

## verdict_class assignment rationale

Choices follow [P-2 §A.12 decision tree](../engineering/parity_diagnostic_reference.md#a12--selecting-a-class-for-new-wrappers):

- **`closed_form` (8 checks):** _smoke_test (mean-of-100-
  normals); 1c_bvar (closed-form matrix algebra given
  coefficients); critical_slowing_down (rolling stats);
  3c_evt (Ferro-Segers 2003 closed-form intervals
  estimator); 3b_har_cj (OLS + BNS test); 3d_johansen
  (closed-form trace stat + arithmetic Bartlett); 2a_kalman
  (closed-form Kalman recursions); 3e_mint (closed-form
  matrix algebra).
- **`mle_fit` (1 check):** 3a_caviar (Nelder-Mead on
  non-smooth quantile loss).
- **`mcmc` (2 checks):** 2b_mcmc_sv_gaussian, 2c_mcmc_sv_student_t.
- **`dl_seed_pinned` (1 check):** 3f_transformer_attention
  (PyTorch attention capture; weights frozen + seed-pinned
  initialization).

## Why no `structural_invariants` declarations

I considered declaring `structural_invariants` for:

- **2a_kalman:** could declare `kalman_covariance_ordering`
  + `kalman_innovation_positivity` (P-2 §D.1 registered
  invariants).
- **3d_johansen:** could declare `vecm_cointegration_rank`.

**Decision: skip in this session.** Rationale:

1. The migration scope is narrowly "P3ParityCheck contract
   compliance" (verdict_class declaration). Adding new
   invariant declarations is feature work, not migration.
2. The existing checks don't populate the required output-
   dict keys for those invariants. Adding the invariant
   declarations would require also modifying the `run_tsl`
   methods to populate the keys, broadening the commit
   scope beyond Item 8.
3. None of the original Phase 1 fixtures exercise the
   structural invariants explicitly. Adding invariants for
   the inherited checks is **best done at the same time as
   a new audit pass** that cross-checks against fresh
   evidence.

Banked: structural-invariant additions for the 12 inherited
checks is a Phase 3.5 Session 9 candidate (new banked item).
Out of scope this session.

## Verification

### Per-check execution (10 fast-tier inherited checks)

| Audit ID | Outcome |
|---|---|
| `_smoke_test` | PASS |
| `1c_bvar_irf_fevd` | PASS |
| `2a_kalman_filter_smoother` | PASS |
| `3a_caviar_sav` | PASS |
| `3b_har_cj` | PASS |
| `3c_evt_ferro_segers` | PASS |
| `3d_johansen_bartlett` | PASS |
| `3e_mint_family` | PASS |
| `3f_transformer_attention` | PASS |
| `critical_slowing_down` | PASS |

10/10 fast-tier inherited checks PASS post-migration.

### Slow-tier inherited checks (2b/2c MCMC SV)

Skipped per locked discipline (slow-tier checks run nightly /
on-demand, not in single-session validation). Both checks
have populated `verdict_class = "mcmc"` and `reroll_on_caveat
= True` post-migration; the contract enforcement at class-
definition time (`__init_subclass__` raises TypeError on
missing attributes) confirms migration succeeded — both
classes load successfully. Runtime verification deferred to
the next slow-tier nightly run.

### Full fast-tier sweep

```
Total: 76 / 76 in 112.4s
PASS: 71, CAVEAT: 5 (p3_stl, p3_mstl, p3_star, p3_nar_narx,
                     p3_emd_hht — unchanged from Phase 3 close)
BLOCK: 0, ERROR: 0
```

**Identical outcome distribution to pre-migration baseline.**
Migration is verdict-neutral; only class-attribute schema
changed.

## Commit footprint

| File | Change |
|---|---|
| 12 check files | import line update + class parent + verdict_class + verdict_class_rationale (~10 LOC each) |
| 0 tolerance ladder changes | Existing tolerances unchanged |
| 0 invariant registry changes | No new invariants populated |
| 1 status doc + 1 session findings | This file |
| **Total** | **~120 LOC** within Phase 3.5 §6 sub-200 LOC envelope |

## Implications

### P-1 Pre-Merge Checklist now empirically locked

[P-1 §8.1](../engineering/parity_standard.md#81-required-artifacts)
specifies `verdict_class` declaration + `verdict_class_rationale`
+ `tier` declaration + tolerance ladder entry as required
artifacts. Pre-Session-2, the 12 inherited checks were
**non-compliant with P-1 §8.1** (missing verdict_class).
Session 2 closes the compliance gap; **all 82 active checks
now satisfy P-1 §8.1** (76 fast + 6 slow).

### Verdict-class taxonomy validated empirically

The 11-class taxonomy locked in P-2 §A covers all 82 checks
without needing a new class. The classes used:

| Class | Wrapper count |
|---|---:|
| `closed_form` | 30+ |
| `mle_fit` | 6 |
| `state_space_reform` | 2 |
| `iterative_loess` | 2 |
| `mcmc` | 2 |
| `em_stochastic` | 5 |
| `dl_seed_pinned` | 7 |
| `bootstrap_distributional` | 0 (reserved) |
| `conformal_coverage` | 1 |
| `single_impl_mle` | 0 (banked Item 1 candidate) |
| `optimizer_divergent_mle` | 0 (banked Item 1 candidate) |

The taxonomy fits Phase 3 + inherited evidence without
revision. The two reserved classes (`single_impl_mle` /
`optimizer_divergent_mle`) remain as candidate refinements
for Phase 3.5 Item 1.

## Banked items remaining (after Session 2)

| Item | Status | Session |
|---|---|---|
| 1 | `single_impl_mle` band tightening | Pending |
| 2 | em_stochastic per-metric bands | Pending |
| 3 | Manifest re-pin cadence | Pending |
| 6 | X-13 binary on Linux CI | Pending |
| 9 | Macro fixture expansion | Pending |
| (new) | structural_invariants declarations on 12 inherited checks | Pending (Phase 3.5 Session 9 candidate) |
| (doc) | Phase 3.5 documentation phase | Session 11 |
| (close) | Phase 3.5 closeout | Session 12 |

## Next session

Phase 3.5 Session 3 — TBD per locked schedule. Likely Item 1
(`single_impl_mle` band tightening): add new verdict_class +
1e-5 abs / 1e-4 rel band; migrate `p3_var`, `p3_vecm`, `p3_pca`
+ audit current `mle_fit`-class wrappers for similar
headroom evidence.
