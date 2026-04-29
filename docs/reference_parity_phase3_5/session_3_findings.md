# Phase 3.5 Session 3 — Item 1: single_impl_mle band tightening

**Date:** 2026-04-29
**Scope:** Item 1 only. Single-session.
**Status:** COMPLETE.

Adds the `single_impl_mle` verdict_class to the taxonomy (band:
1e-5 abs / 1e-4 rel) and migrates one wrapper (`p3_vecm`) from
`mle_fit` based on confirmed >=3 orders headroom evidence.

## Audit findings (deviation from prompt premise)

The Session 3 prompt listed `p3_var`, `p3_vecm`, `p3_pca` as
candidate migrations from `mle_fit` to `single_impl_mle`.
Empirical audit revealed only **p3_vecm is a genuine candidate**;
the prompt's premise was partially incorrect:

| Wrapper | Current verdict_class | Achieved abs | Migration verdict |
|---|---|---:|---|
| **p3_vecm** | `mle_fit` (1e-3 band) | 9.99e-16 (beta) | **MIGRATE** — 13 orders headroom |
| p3_var | `closed_form` (1e-10 band, ALREADY tighter) | 7.22e-16 | NO — already in tighter band than single_impl_mle |
| p3_pca | `closed_form` (1e-10 band, ALREADY tighter) | 7.99e-15 | NO — already in tighter band than single_impl_mle |

Migrating p3_var or p3_pca from `closed_form` to
`single_impl_mle` would **widen** their bands (1e-10 → 1e-5),
not tighten them. The prompt's premise about these two
wrappers was incorrect; they're already classified at the
tightest available band per [P-2 §A.1](../engineering/parity_diagnostic_reference.md#a1--closed_form-1e-10-abs--1e-10-rel).

## Audit of remaining mle_fit wrappers

Per Session 3 prompt scope item 3 ("audit remaining mle_fit
class wrappers for ≥3 orders headroom"). Achieved tolerances
read from Phase 3.5 Session 2 fast-tier sweep
(`parity_fast_p35s2.json`):

| Wrapper | Worst-metric achieved abs | Band 1e-3 | Headroom (orders) | Decision |
|---|---:|---:|---:|---|
| `p3_vecm` | 9.99e-16 (beta) | 1e-3 | 13 | **MIGRATE** |
| `p3_arimax_sarimax` | 5.52e-06 (exog_coefs) | 1e-3 | 2.3 | Keep `mle_fit` (<3 threshold) |
| `p3_sarima` | 2.22e-05 (forecast) | 1e-3 | 1.7 | Keep `mle_fit` |
| `p3_arima_manual` | 1.02e-04 (forecast) | 1e-3 | 1.0 | Keep `mle_fit` |
| `p3_intervention_analysis` | 4.20e-04 (ar1) | 1e-3 | 0.4 | Keep `mle_fit` (right at band) |
| `3a_caviar_sav` | (three-outcome metric; non-uniform) | — | — | Keep `mle_fit` (Nelder-Mead non-uniqueness; not a candidate) |
| `p3_tbats` | (slow tier; not in fast-tier audit JSON) | — | — | Defer; slow-tier verification |

**One migration only: `p3_vecm`.** Other `mle_fit` wrappers
have <3 orders headroom and stay at the canonical 1e-3 abs /
1e-2 rel band per [P-2 §A.2](../engineering/parity_diagnostic_reference.md#a2--mle_fit-1e-3-abs--1e-2-rel).

## Changes

### 1. Add `single_impl_mle` to taxonomy

**File:** `tools/reference_parity/harness/check_base.py`

- Added `"single_impl_mle"` to the `VerdictClass` Literal type
- Added to `_REGISTERED_VERDICT_CLASSES` frozen set (the
  enforcement set used by `__init_subclass__`)
- Inline doc comment cites P-2 §A criteria + master plan §4
  Item 1 spec (1e-5 abs / 1e-4 rel; 1.5x achieved-tolerance
  margin per §4 risk 4 mitigation)

### 2. Migrate p3_vecm verdict_class

**File:** `tools/reference_parity/harness/checks/p3_vecm.py`

- `verdict_class`: `"mle_fit"` → `"single_impl_mle"`
- `verdict_class_rationale` rewritten to cite the closed-form
  OLS-on-cointegrating-vectors collapse + Phase 3 Session 7
  measured 9.99e-16 abs evidence

### 3. Tighten p3_vecm tolerance ladder

**File:** `tools/reference_parity/harness/tolerances.py`

| Metric | Before (`mle_fit`) | After (`single_impl_mle`) |
|---|---:|---:|
| `primary.abs_tol` | 1e-2 | 1e-5 |
| `primary.rel_tol` | 1e-2 | 1e-4 |
| `primary.block_abs_tol` | 1e-1 | 1e-3 |
| `primary.block_rel_tol` | 1e-1 | 1e-2 |

`secondary` ladder unchanged (loglik AIC/BIC scale offsets are
documented Pattern D Secondary-tier divergences; tightening
them would spuriously trip CAVEAT on documented Pattern D).

`justification` updated to cite Phase 3.5 Session 3 migration
+ 1.5x margin rationale.

## Verification

### Single-check: p3_vecm at tightened band

```
[PASS] p3_vecm (0.69s seed=42)
    primary.beta: status=PASS, max_abs_diff=9.99e-16
    primary.alpha: status=PASS, max_abs_diff=2.78e-13
    secondary.loglik: status=PASS, abs_diff=5.91e-11
overall: PASS
```

p3_vecm PASS at the tightened single_impl_mle band.
Achieved 9.99e-16 abs (beta) is **9 orders inside** the new
1e-5 band — tightening preserved 9-order headroom margin.

### Full fast-tier sweep

```
Total: 76 / 76 in 121.6s
PASS: 71, CAVEAT: 5 (p3_emd_hht, p3_mstl, p3_nar_narx,
                     p3_star, p3_stl — unchanged)
BLOCK: 0, ERROR: 0
```

**Identical outcome distribution to pre-tightening baseline.**
Master plan §8.1 risk 4 ("tolerance tightening produces
regression on previously-passing checks") **NOT triggered**.

## Commit footprint

| File | Change |
|---|---|
| `harness/check_base.py` | +13 LOC (add single_impl_mle to literal + registered set) |
| `harness/checks/p3_vecm.py` | -8 / +12 LOC (verdict_class + rationale rewrite) |
| `harness/tolerances.py` | -7 / +18 LOC (tighten ladder + update justification) |
| `docs/reference_parity_phase3_5/session_3_findings.md` | new (~150 LOC) |
| `docs/reference_parity_status.md` | -1 / +5 LOC |
| **Total** | **~50 LOC functional + ~150 LOC docs** within CAL-R6 100-LOC budget |

## Implications

### 11-class taxonomy → 10-class core + 1 candidate refinement (Phase 3.5 S3)

P-2 §A documented 11 classes with `single_impl_mle` and
`optimizer_divergent_mle` as candidate refinements
(banked Item #2). Session 3 promotes `single_impl_mle` to
**production-locked**:

- `closed_form` — 30+ wrappers
- `mle_fit` — 5 wrappers (was 6; p3_vecm migrated out)
- **`single_impl_mle` — 1 wrapper (NEW; p3_vecm)**
- `state_space_reform` — 2 wrappers
- `iterative_loess` — 2 wrappers
- `mcmc` — 2 wrappers
- `em_stochastic` — 5 wrappers
- `dl_seed_pinned` — 7 wrappers
- `bootstrap_distributional` — 0 (reserved)
- `conformal_coverage` — 1 wrapper

`optimizer_divergent_mle` remains a banked candidate — no
Phase 3 wrapper has demonstrated the ≥3 orders headroom in
the OPPOSITE direction (i.e., evidence that the canonical
mle_fit band is too tight). The GARCH family at S6 was a
borderline case, but rugarch's gosolnp pinning brought
divergence within 1e-4 abs (~1 order outside band, not
inside). No action this session.

### P-1 §5.1 verdict_class enum reflects 11 entries

Session 11 documentation phase will update [P-1 §5.1](../engineering/parity_standard.md#51-verdict_class-taxonomy-11-classes--locked-session-14)
to mark `single_impl_mle` as production-locked (was
"candidate refinement banked at check-in 1.5"). Out of
scope for Session 3; banked for Session 11.

### P-2 §A.10 update banked

Session 11 will also update [P-2 §A.10](../engineering/parity_diagnostic_reference.md#a10--single_impl_mle-candidate-not-yet-locked)
from "candidate; not yet locked" to "production-locked at
Phase 3.5 Session 3" with the empirical evidence cited (1
wrapper migrated; 13 orders headroom; 9 orders preserved
post-tightening). Out of scope for Session 3; banked for
Session 11.

## Banked items remaining (after Session 3)

| Item | Status | Session |
|---|---|---|
| 2 | em_stochastic per-metric bands | Session 4 (next) |
| 3 | Manifest re-pin cadence | Pending |
| 6 | X-13 binary on Linux CI | Pending |
| 9 | Macro fixture expansion | Pending |
| (S2 banked) | structural_invariants on 12 inherited | Phase 3.5 S9 candidate |
| (doc) | Phase 3.5 documentation phase incl. P-1 §5.1 + P-2 §A.10 updates | Session 11 |
| (close) | Phase 3.5 closeout | Session 12 |

## Next session

Phase 3.5 Session 4 — Item 2: em_stochastic per-metric bands.
Per locked schedule. Per-session findings doc + status doc
update + commit/push at session end. No Chat re-engagement
unless escalation triggers.
