# Phase 4 Session 11c-1 — P-1 §3.4 NEW + 5 audit-field-touched wrappers (Option A split, 1 of 2)

**Date:** 2026-05-03
**Scope:** First of two sub-sessions in S11c two-way split per
Decision 19A (Option A). Lands P-1 §3.4 docstring convention
codification + applies it to the 5 wrappers most directly
motivated by recent S8 + B-Phase4-S8-2 audit-field surface
additions. Closes BYF #5 partially; S11c-2 closes the
remaining 5 general-improvement wrappers.
**Status:** COMPLETE.

## Why this is a sub-session (Option A split)

S11c trigger projected ~150 LOC (P-1 §3.4 ~30 + 10 wrappers
× ~12 each = ~120). Pre-commit §13.4 spill check returned
+251 net LOC (+62 §3.4 + +197 across 10 wrappers - 8
deletions). Per-wrapper backfills landed at ~20 LOC each
(References + Audit-fields blocks; both content blocks earn
their LOC) rather than ~12 LOC each.

§13.2 bundled-category exception check on the unsplit S11c
returned 2 of 3 criteria (criterion 3 per-category LOC
borderline; combined 251 > 200 default). Per Decision 17 /
S11b-1 ORIGINAL precedent ("DO NOT classify content-density
variance as measurement-variance; honest disposition is split,
not amendment"), §13.4 spill protocol applied.

User Decision 19A (Option A): two-way split per natural seam.
S11c-1 = §3.4 + 5 audit-field-touched wrappers (S8/B-Phase4-S8-2
motivated). S11c-2 = remaining 5 general-improvement wrappers.

Decline of Option C (tighten in place): per Decision 19A
verbatim, "per-wrapper docstrings have two distinct content
blocks (References + Audit-fields) serving two distinct
reader populations (academic/research vs parity-audit
infrastructure). Removing either block degrades the artifact
for that population. This is not analogous to S11b-1
ORIGINAL's case ... Here, both blocks earn their LOC."

## What changed

### `docs/engineering/parity_standard.md` §3.4 NEW (+62 LOC)

Codifies the docstring convention for engine wrapper modules
under `engine/techniques/`. Six requirement blocks:

- **Module-level docstring**: technique name + methodology
  summary + reference citations + audit-fields documentation
  block + cross-references.
- **Per-function docstring**: purpose + key user-facing
  parameters + returns dict shape + raises clause.
- **Cross-references and exemplars**: pointer to `critical_slowing_down.py`
  (thorough Stage A/B/C breakdown) + `kalman_filter.py`
  (post-S11c audit-fields documentation block pattern).
- **Cross-doc family**: §3.4 is part of the C-1 §6 wrapper
  structural patterns family; engine-side companion to C-1
  §6.1 module-vs-package layout.
- **Application to new audit_fields**: per-cycle pattern is
  to add audit-fields documentation block in the same commit
  that introduces the new field. S11c backfills closed gaps
  from prior cycles where audit-field surface was added
  without corresponding docstring documentation.
- **Cycle precedent citations**: S8 P4-1.2 + B-Phase4-S8-2
  BYF diagnostics elevation cited as motivating cases for
  the convention's application discipline.

### Five audit-field-touched wrapper backfills

| Wrapper | LOC | Backfill rationale |
|---|---|---|
| `engine/techniques/kalman_filter.py` | +22 | References (Kalman 1960; Harvey 1989; Durbin & Koopman 2012) + audit-fields block documenting the 3 S8-added fields (filtered_state_cov, predicted_state_cov, smoothed_state_cov); cross-reference to P-2 §D.1 ``kalman_covariance_ordering`` invariant |
| `engine/techniques/kalman_smoother.py` | +17 | References + audit-fields block (cross-references kalman_filter for shape semantics; emphasizes RTS smoother PSD-ordering property) |
| `engine/techniques/johansen_cointegration.py` | +21 | References (Johansen 1988/1991; Reimers 1992; MacKinnon-Haug-Michelis 1999) + audit-fields block documenting the 3 S8-added alias fields (trace_rank legacy + determined_rank_trace + cointegrating_rank); explanation of multi-name surface |
| `engine/techniques/bvar.py` | +11 | References-only (Litterman 1986; Doan-Litterman-Sims 1984; Banbura-Giannone-Reichlin 2010); cross-reference to P-3 §3.4.2 forward-provisioning case study + BVAR-SV subpackage location |
| `engine/techniques/bond_yield_forecast/_dispatch.py` | +23 | References (CCM-2019; KSC 1998; Litterman 1986) + audit-fields block documenting the 3 B-Phase4-S8-2 elevated fields (ess_min, rhat_max, geweke_max_abs_z); single-chain Gibbs note on rhat_max=None |

The 5 selected wrappers all received audit-field surface
additions during recent Phase 4 cycle work:
- kalman_filter / kalman_smoother / johansen_cointegration
  → S8 P4-1.2 audit-field expansion (filtered_state_cov +
  determined_rank_trace + alias fields).
- bond_yield_forecast/_dispatch → B-Phase4-S8-2 BVAR
  diagnostics elevation (ess_min / rhat_max /
  geweke_max_abs_z elevated from results.convergence_diagnostics()).
- bvar → BYF #1 + BYF #2 audit work (Phase 4 S4 + S5)
  motivated reference-citation backfill.

§3.4 NEW lands with its most institutionally consequential
applications in the same commit. Convention validates
against its motivating cases — analogous to S11a-2-2's
marginal-tolerance amendment landing in the same commit it
needed.

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| **S11c-1 actual** | **+156 net LOC** (62 §3.4 + 94 wrappers; or as gross +156 / -0 net) |
| Position vs default | UNDER by 44 LOC (~22% headroom) |
| §13.4 marginal-tolerance band | 5-10% (200-220 LOC); not engaged |

Clean commit. §13.2 bundled-category exception cleanly
engaged per Decision 19A:
- **Architectural inseparability:** ✓ convention codification
  + first applications (the convention validates against the
  audit-field-touched wrappers).
- **Categorical orthogonality:** ✓ P-1 doc text + engine
  wrapper code = distinct concerns.
- **Per-category LOC under threshold:** ✓ §3.4 NEW = 62 LOC
  (under 200); 5 wrappers subtotal = 94 LOC (under 200).
  Combined = 156 LOC (under 200; bundled exception not
  needed for spill, only for review-grouping rationale).

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 36.64s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| `parity-fast` tier outcome distribution unchanged | n/a (docstring-only changes) |
| Numerical-array byte-identical equivalence | n/a (docstring-only; no semantic engine changes) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S11c-1 contributes to the v1.2.0 ledger per master plan §15.1:

| Doc | Section | Source | LOC |
|---|---|---|---|
| P-1 | §3.4 (NEW) | S11c-1 BYF #5 | +62 |

Engine wrapper docstring backfills are NOT v1.2.0 doc-set
content (operational engine documentation, not P-x doc-set
amendments).

**Cumulative ledger after S11c-1:**

| Doc | LOC accumulator |
|---|---|
| P-1 | ~490 (S1 §8.5 + S11a-1 §6.1 + S11a-2-1 §13 binding + S11a-2-2 §13.5/§13.4) + ~62 (S11c-1 §3.4) = **~552** |
| P-2 | ~261 (S4-S9 + S11a-1 §B.6.4) |
| P-3 | ~245 (S5-S6 + S9 + S11a-1 §3.4.1 + S11a-3 §3.4.2) |
| C-1 | ~205 (S1 + S10) |
| **Total** | **~1263 LOC** (over §11.11 ceiling 600 by ~110%) |

§11.11 cumulative ledger crossed 600 ceiling at S11a-1; now
sits at ~1263 LOC. **S12a/S12b split firmly required.**

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_standard.md` | New §3.4 (between §3.3 and §4) | +62 |
| `engine/techniques/kalman_filter.py` | References + audit-fields block | +22 |
| `engine/techniques/kalman_smoother.py` | References + audit-fields block | +17 |
| `engine/techniques/johansen_cointegration.py` | References + audit-fields block | +21 |
| `engine/techniques/bvar.py` | References (BYF-cycle motivated) | +11 |
| `engine/techniques/bond_yield_forecast/_dispatch.py` | References + audit-fields block (B-Phase4-S8-2) | +23 |
| `docs/reference_parity_phase4/session_11c_1_findings.md` | NEW (this file) | ~165 |
| **Total (commit-counted; excludes findings doc)** | | **+156 LOC** |

## Disposition

| Item | Pre-S11c-1 status | Post-S11c-1 status |
|---|---|---|
| BYF #5 (P-1 §3.4 docstring convention + ~10-wrapper engine backfill) | banked (S11c scope) | **PARTIAL** — P-1 §3.4 NEW + 5 wrappers backfilled; remaining 5 wrappers deferred to S11c-2 |
| 13-item inheritance register | 1 open + 12 closed | **1 open + 12 closed** (BYF #5 partial; full closure at S11c-2) |
| Phase 4 cycle progress | 12 of 13 sessions (92%) | **(no full-session count change; sub-sub-session)** |

## Banked observations from S11c-1

**B-Phase4-S11c-1-1 — Convention-with-application landing
pattern.** §3.4 lands with its most institutionally
consequential applications (S8 + B-Phase4-S8-2 audit-field-
touched wrappers) in the same commit. Same pattern as
S11a-2-2 marginal-tolerance amendment landing in the same
commit that needed it. Bank as institutional precedent: when
codifying a new convention/discipline, prefer landing the
codification with its first applications when possible —
the application validates the codification on the same
commit, and operating-context examples are co-located with
the rule for future cycle authors.

**B-Phase4-S11c-1-2 — Two-block docstring pattern earns its
LOC.** Per Decision 19A: per-wrapper docstrings with both
References block + Audit-fields block serve two distinct
reader populations (academic/research vs parity-audit
infrastructure). Removing either block degrades the artifact
for that population. This is principled content density,
NOT measurement-variance LOC noise. Bank as institutional
precedent: future docstring-backfill sessions should
preserve both block types when both are operationally
relevant; tighten only inline narrative rationale (which is
the S11b-1 ORIGINAL anti-pattern).

## Next sub-session

**S11c-2 — Remaining 5 general-improvement wrappers.**

| File | LOC |
|---|---|
| `engine/techniques/var_model.py` | +16 |
| `engine/techniques/dynamic_factor_model.py` | +22 |
| `engine/techniques/pelt_change_points.py` | +21 |
| `engine/techniques/dtw_alignment_lag.py` | +18 |
| `engine/techniques/x13_seasonal_adjust.py` | +26 |
| **Total** | **+103** |

Clean under §13.1 default (200 LOC; 97 LOC headroom). No
expected spill. Closes BYF #5 in full + S11c sub-session
series + Phase 4 engine-touch session class. Trigger: ready
to fire after S11c-1 CI confirms green.
