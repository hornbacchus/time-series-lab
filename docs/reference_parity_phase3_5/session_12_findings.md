# Phase 3.5 Session 12 — PHASE 3.5 CLOSEOUT (final session)

**Date:** 2026-04-30
**Scope:** Closeout per Phase 3 Session 18 precedent.
**Status:** **PHASE 3.5 CLOSED.** Phase 4 launches immediately
at this commit.

Final session of Phase 3.5 cycle. Verifies CI workflow state +
P-4 v1.1.0 final state, retro-edits master plan with PHASE 3.5
CLOSED banner, commits + pushes the closeout artifact, and
launches Phase 4.

## Verification checklist

### 1. CI workflows current state

**`parity-fast.yml`:**
- `runs-on: windows-latest`
- `timeout-minutes: 15` (bumped from 10 at Phase 3.5 S6
  follow-up commit `d0a6ee6`)
- Triggers: `pull_request` + `push` to master
- Exit-code policy: CAVEAT (exit 2) → CI green; DOCUMENTED-
  DIVERGENCE (exit 4) → CI green (per Phase 3.5 S1 wiring);
  BLOCK (exit 1) / ERROR (exit 3) fail
- Coverage: 76 fast-tier checks (71 PASS + 5 CAVEAT + 0 BLOCK
  baseline)

**`parity-slow.yml`:**
- Two parallel jobs:
  - `slow` — Windows (canonical Phase 3 platform)
  - `slow-linux` — Ubuntu (Phase 3.5 S6 addition; cross-
    platform Rscript resolution; X-13 binary install +
    symlink scaffolding preserved for Phase 4)
- Triggers: `schedule` nightly 06:00 UTC + `push` tags +
  `workflow_dispatch`
- Exit-code policy: same as fast-tier
- Coverage: 6 slow-tier checks (5 PASS + 1 SKIP — `p3_x13`
  SKIP-graceful both platforms)

**No workflow modifications needed at closeout.** The CI
matrix is in its v1.1.0 final state.

### 2. Local fast-tier sweep (final)

```
Total: 76 / 76
PASS: 71
CAVEAT: 5 (p3_emd_hht, p3_mstl, p3_nar_narx, p3_star, p3_stl)
BLOCK: 0
```

Identical to S10/S11 baseline. No regression.

### 3. P-4 v1.1.0 final state

| Confirmation point | Status |
|---|---|
| 9 Phase 3.5 candidates dispositioned (8 closed + 1 partial) | ✓ |
| 3 Phase 4 carry-forward items documented | ✓ |
| 12 inherited wrappers migrated to P3ParityCheck contract (S2) | ✓ |
| All 82 active checks declare `verdict_class` (P-1 §8.1 invariant) | ✓ — 82/82 verified via `grep -c "verdict_class = "` |
| `p3_x13` verdict SKIP-graceful both platforms | ✓ |
| No PENDING placeholders | ✓ — only the definitional reference in the legend remains |
| v1.1.0 doc set table reflects all 4 docs at v1.1.0 | ✓ |

### 4. Master plan retro-edit

`plans/reference_parity_phase3_master_plan.md` header status
banner extended to include PHASE 3.5 CLOSED at Session 12
alongside PHASE 3 CLOSED at Session 18. Light retro-edit
matching Phase 3 Session 18 precedent (status banner only;
no substantive edits to plan body).

### 5. Scripts/ residual cleanup

No residual cleanup work surfaces at S12. The `tools/reference_parity/scripts/`
deprecated audit scripts were removed at Phase 3.5 Session 1;
no further deprecation candidates surfaced through Sessions
2-11.

## Phase 3.5 cycle complete — final statistics

| Metric | Phase 3.5 final |
|---|---:|
| Sessions used | **12 of 17 budgeted** |
| **Sessions under budget** | **5** |
| Banked candidates closed in-cycle | 8 of 9 |
| Banked candidates with Phase 4 partial deferral | 1 (Item #6 X-13 statsmodels-x13ashtml integration) |
| Verdict-class production-locks | 1 (`single_impl_mle` at S3) |
| Schema extensions | 1 (per-metric tolerance ladder at S4) |
| Fixture pool growth | 5 → 16 series (Sessions 7-9) |
| CI infrastructure additions | Linux runner job (slow-tier); cross-platform Rscript resolution |
| P-* documents amended | 4 (P-1, P-2, P-3, P-4 all at v1.1.0) |
| Amendment sites | 22 |
| Estimated amendment LOC | ~1015 (vs ~610 estimated; expansion in P-3 §6 rewrite + Phase 4 §7) |
| Phase 4 carry-forward items | **3** |

## Per-session retrospective

| Session | Item | Disposition |
|---:|---|---|
| S1 | Items 4 + 5 + 7 (CI cleanup + DD provision) | CLOSED |
| S2 | Item 8 (12 pre-Phase-3 wrapper migration) | CLOSED |
| S3 | Item 1 (`single_impl_mle` band tightening) | CLOSED — production-locked |
| S4 | Item 2 (em_stochastic per-metric bands) | CLOSED — schema extension |
| S5 | Item 3 (manifest re-pin cadence) | CLOSED — quarterly protocol formalized |
| S6 | Item 6 (X-13 binary on Linux CI) | PARTIAL — Phase 4 deferral on statsmodels-x13ashtml |
| S7 | Item 9 entry (FX expansion) | CLOSED — 4 FX pairs added |
| S8 | Item 9 second (rates + commodity) | CLOSED — 7 series added; Pattern A.1 cross-asset confirmed |
| S9 | Item 9 third (cross-pair synthesis) | CLOSED — Stream 1; Stream 2 deferred to Phase 4 |
| S10 | Slack absorption + Session 11 amendment plan | CLOSED — preparation artifacts produced |
| S11 | Documentation phase (P-* v1.1.0 issuances) | CLOSED — 22 amendment sites; 4 docs at v1.1.0 |
| **S12 (this)** | **Phase 3.5 closeout** | **CLOSED — Phase 4 launches** |

## Phase 4 launch

**Effective:** Phase 3.5 Session 12 closeout commit (this).

**Handoff doc:** P-1/P-2/P-3/P-4 v1.1.0. No separate handoff
doc produced (per Session 12 prompt — v1.1.0 serves the role).

**Phase 4 master plan drafts in next Chat session** per
established handoff-doc → master-plan pattern.

**Phase 4 entry scope:**

1. **structural_invariants on 12 inherited wrappers**
   - Engine-side audit-field expansion for 2 fit wrappers
     (2a_kalman_filter_smoother kalman_covariance_ordering;
     3d_johansen_bartlett vecm_cointegration_rank).
   - Registry expansion for 10 non-fit wrappers (new
     invariant types: mcmc_convergence,
     evt_extremal_index_validity, mint_coherence,
     transformer_attention_normalization, etc.).

2. **statsmodels ↔ x13ashtml integration**
   - Resolution path (one of):
     a. Patch `engine/techniques/x13_seasonal_adjust.py` to
        handle x13ashtml output convention directly (bypass
        statsmodels' `x13_arima_analysis` abstraction).
     b. Pin a statsmodels patch / branch that handles
        x13ashtml output correctly.
     c. Add a TSL-side post-process that normalizes x13ashtml
        output to the format statsmodels expects.
   - Or: formal deferral to "permanent SKIP-graceful" if no
     viable resolution path emerges.

3. **CSD wrapper engineering (n_surrogates default cap)**
   - Resolution path (one of):
     a. Chunk the surrogate dimension to bound peak memory.
     b. Reduce default n_surrogates from 1000 → 200.
     c. Auto-cap n_surrogates per series length (length >
        1500 → cap at 200).
   - Workaround verified at n_surrogates=100; the engineering
     fix should preserve the option to run at higher
     surrogate counts when memory allows.

**Mid-cycle banked items** add at midpoint check-in per Phase
3.5 precedent.

**Phase 4 launch timing:** immediate at Session 12 closeout.
Code's context loaded; continuity preserved.

**Phase 4 carry-forward framing:** Phase 4 holds Phase 3
discipline:
- Honest disposition (PASS/CAVEAT/DD/NO-REFERENCE per verdict
  taxonomy).
- No verdict-forcing — carry-forward items resolve to correct
  verdict per methodology, not to maximum-PASS optimization.

## Commit footprint

| File | Change |
|---|---|
| `docs/reference_parity_phase3_5/session_12_findings.md` | new (~150 LOC) |
| `docs/reference_parity_status.md` | -1 / +30 LOC (S12 closeout marker) |
| `plans/reference_parity_phase3_master_plan.md` | -1 / +12 LOC (status banner extended) |
| **Total** | **0 LOC code; ~190 LOC docs** within CAL-R6 100-LOC engine-side budget (zero engine changes) |

## Phase 3.5 closeout — final state

✅ Phase 3.5 cycle complete.
✅ P-1 / P-2 / P-3 / P-4 all at v1.1.0.
✅ CI workflows current state covers 82 active checks.
✅ Master plan PHASE 3.5 CLOSED banner.
✅ 3 Phase 4 carry-forward items documented for immediate
   Phase 4 launch.

**Phase 4 launches at this commit.**
