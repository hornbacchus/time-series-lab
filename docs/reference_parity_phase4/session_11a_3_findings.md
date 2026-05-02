# Phase 4 Session 11a-3 — Decision 3 P-3 §3.4.2 forward-provisioning interval entry

**Date:** 2026-05-02
**Scope:** Third of three sub-sessions in S11a three-way
split. Closes Decision 3 (DOCUMENTED-DIVERGENCE forward-
provisioning interval banking) per Decision 14 disposition.
Closes the S11a sub-session series.
**Status:** COMPLETE.

## Why this is the third sub-session

Per Decision 14 (S11a three-way split honoring §13.2
sharpened criteria): S11a-1 closed clean (#4 + #9 + O-1,
139 LOC); S11a-2 cascaded into S11a-2-1 / S11a-2-2 (Decision
A, 167 + 218 = 385 LOC across two sub-sub-sessions); S11a-3
closes Decision 3 alone — the final S11a sub-session.

Decision 3 is the standalone DOCUMENTED-DIVERGENCE forward-
provisioning interval banking entry; it does NOT have
architectural inseparability with any other S11a item.
Decision 14's disposition explicitly placed it in its own
sub-session.

## What changed

### P-3 §3.4.2 NEW — DOCUMENTED-DIVERGENCE forward-provisioning interval

**Insertion location:** `docs/engineering/parity_empirical_findings.md`
between §3.4.1 (S11a-1's near-unit-root banking entry) and
§4 (Surprises and reversals). Sibling subsection to §3.4.1
under §3.4. No back-edit to §3.4.1 needed.

**Content added (~121 LOC):**

- **Origin** (~12 LOC): Phase 3.5 Session 1 wired the
  DOCUMENTED-DIVERGENCE verdict path forward-provisioned;
  no in-tree audit produced DD at the time of wiring;
  documented at the time as P-3 §6.6.
- **First runtime exercise** (~12 LOC): Phase 4 Session 5
  (commit `2b54acb`, 2026-05-01) — BYF candidate #1 R
  `BVAR::bvar()` constant-volatility cross-check landed as
  PASS-A.2 (DOCUMENTED-DIVERGENCE) with `max_rel_diff=1.76`
  on Minnesota-prior coefficient posterior.
- **Forward-provisioning interval** (~6 LOC): ~6 months;
  the longest forward-provisioning interval in TSL parity
  history.
- **S5 first-runtime exercise validated three wiring
  layers** (~22 LOC): exit-code mapping (P-1 §6.4 exit 4 →
  CI green); audit-script return shape (DD with
  characterization metadata); P-4 status tracker
  secondary-verdict-line rendering. All three fired
  correctly at first organic occurrence.
- **Self-validating-irony parallel** (~12 LOC): cross-
  reference to S1/S5 install-matrix gate parallel; framing
  as **complementary verification-pattern case studies**
  (DD wiring stayed correct over 6 months; §8.5 gate
  failed within same cycle).
- **Pattern as institutional precedent** (~22 LOC):
  forward-provisioning safety net + two complementary
  hardening mechanisms (test coverage at provisioning time;
  periodic provisioned-path inventory check).
- **Forward-looking discipline** (~10 LOC): future forward-
  provisioning decisions should anticipate end-to-end
  exercise within reasonable time (months, not years);
  6-month interval was at upper edge of acceptable.
- **Forward-provisioning candidates to monitor for
  analogous rot** (~5 LOC).
- **Cross-references** (~12 LOC): P3.5 S1 origin, P4 S5
  first-runtime, P-1 §13.5.4 cross-pattern, B-Phase4-S5-4
  banked observation.

### Trigger verify-at-close items

**P-3 §3.4 sub-section ordering verified:**
- §3.4 — Pattern A.1 production-locked across 4 dimensions (Phase 3.5 v1.1.0)
- §3.4.1 — O-1 banking: near-unit-root VAR companion margin observation (Phase 4 Session 11a-1)
- §3.4.2 — DOCUMENTED-DIVERGENCE forward-provisioning interval (Phase 4 Session 11a-3) ← NEW

Both subsections sit cleanly within §3.4. §3.4.1 was added
at S11a-1; §3.4.2 added at S11a-3 (this session); §3.4.1
required no back-edit (sibling subsection, not amendment).

**No back-edit to S11a-1 §3.4.1.** Confirmed.

**Forward-reference resolution status:** §3.4.2 cross-
references P-1 §13.5.4 (S1/S5 install-matrix self-
validating-irony parallel). §13.5.4 lives at S11a-2-2
(commit `c765917`, CI PASS 7m4s). Forward-reference
resolves cleanly.

## §13.4 spill compliance

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC (excluding findings doc) |
| Sub-session projection | ~72 LOC |
| **Sub-session actual** | **+121 net LOC** |
| Margin under default | 79 LOC (~40% headroom) |
| §13.4 marginal-overshoot tolerance band (codified at S11a-2-2) | n/a — well under default; tolerance band not engaged |

S11a-3 commits unblocked under §13.1 default. Original
estimate ~72 LOC was conservative; actual ~121 LOC is
larger because each scope sub-bullet (S5 wiring layers,
self-validating-irony parallel framing, forward-looking
discipline, complementary hardening mechanisms) needed
~15-25 LOC to be operationally useful. No scope creep; all
content per trigger.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | n/a (no engine code touched) |
| Per-wrapper test suite green | n/a (no wrappers touched) |
| `parity-fast --check-environment` clean | n/a (no MANIFEST.toml changes) |
| `parity-fast` tier outcome distribution unchanged | n/a (doc-only) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S11a-3 contributes to the v1.2.0 ledger:

| Doc | Section | Source | LOC |
|---|---|---|---|
| P-3 | §3.4.2 (NEW) | S11a-3 Decision 3 | ~121 |

**Cumulative ledger after S11a-3:**

| Doc | LOC accumulator |
|---|---|
| P-1 | ~75 (S1 §8.5) + ~30 (S11a-1 §6.1) + ~167 (S11a-2-1 §13 binding) + ~218 (S11a-2-2 §13.4 + §13.5) = **~490** |
| P-2 | ~261 (S4-S9 + S11a-1 §B.6.4) |
| P-3 | ~70 (S5-S6 + S9) + ~54 (S11a-1 §3.4.1) + ~121 (S11a-3 §3.4.2) = **~245** |
| C-1 | ~205 (S1 + S10) |
| **Total** | **~1201 LOC** (over §11.11 ceiling 600 by ~100%) |

**§11.11 cumulative ledger:** crossed 600 ceiling at S11a-1
(~695 LOC); after the full S11a series ledger sits at
~1201 LOC — twice the §11.11 trigger ceiling. **S12a/S12b
split confirmed as expected path.** S11b + S11c will further
increase the cumulative ledger, possibly forcing S12a/S12b/
S12c split if total approaches ~1500-1800 LOC.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_empirical_findings.md` | New §3.4.2 (sibling subsection to §3.4.1) | +121 |
| `docs/reference_parity_phase4/session_11a_3_findings.md` | NEW (this file) | ~165 |
| **Total (commit-counted; excludes findings doc)** | | **+121 LOC** |

## Inheritance register reconciliation (per trigger verify-at-close)

The original 13-item inheritance register has accumulated
additional institutional-decision tracking during S11a sub-
session series. Surfacing a clean disentangled state:

### Original 13-item inheritance register (master plan §15.1)

| # | Item | Status | Closed at |
|---|---|---|---|
| 1 | P4-1 (P3.5 carry-forward — structural_invariants 12 wrappers) | **CLOSED** | S7 + S8 + S9 (3-session cluster) |
| 2 | P4-2 (P3.5 carry-forward — statsmodels-x13ashtml integration) | **CLOSED** | S2 |
| 3 | P4-3 (P3.5 carry-forward — CSD wrapper engineering) | **CLOSED** | S3 |
| 4 | BYF #1 (R BVAR constant-vol Pattern A.2) | **CLOSED** | S5 (PASS-A.2 with DOCUMENTED-DIVERGENCE) |
| 5 | BYF #2 (Minnesota Pattern A.3) | **CLOSED** | S4 |
| 6 | BYF #3 (stochvol partial Pattern A.2) | **CLOSED** | S6 (PASS-A.2 with DOCUMENTED-DIVERGENCE) |
| 7 | BYF #4 (P-2 §B.6.4 bvars trigger) | **CLOSED** | S11a-1 |
| 8 | BYF #5 (P-1 §3.4 docstring convention + engine backfill ~10 wrappers) | **OPEN** | S11c (scheduled) |
| 9 | BYF #6 (C-1 §6.1 module-vs-package layout) | **CLOSED** | S10 |
| 10 | BYF #7 (C-1 §6.2 bundled-workbook input) | **CLOSED** | S10 |
| 11 | BYF #8 (C-1 §6.3 layered validation) | **CLOSED** | S10 |
| 12 | BYF #9 (P-1 §6.1 tier classification) | **CLOSED** | S11a-1 |
| 13 | BYF #10 (P-1 §8.5 install-matrix gate) | **CLOSED** | S1 |

**Original 13-item state: 12 CLOSED + 1 OPEN (BYF #5).**

### BYF Mod-2 banked observations (NOT in the 13)

| Item | Status | Closed at |
|---|---|---|
| O-1 (near-unit-root VAR companion margin) | **CLOSED** | S9 (corrective action — Pattern F threshold tightening) + S11a-1 (banking entry P-3 §3.4.1) |
| O-2 (Pattern F invariant tightness) | **CLOSED** | S9 |

### Institutional decisions accumulated during cycle (NOT in original 13)

| Decision | Status | Closed at |
|---|---|---|
| Decision 3 (DOCUMENTED-DIVERGENCE forward-provisioning interval banking) | **CLOSED** | S11a-3 (this session, P-3 §3.4.2) |
| Decision A (P-1 §13 NEW per-session cycle discipline) | **CLOSED** | S11a-2-1 (binding rules) + S11a-2-2 (examples + marginal-tolerance amendment) |
| Decision 14 (S11a three-way split) | **CLOSED** (operational/procedural) | S11a (split executed) |
| Decision 15 (S11a-2 two-way split) | **CLOSED** (operational/procedural) | S11a-2 (split executed) |
| Decision 16C (S11a-2-2 consolidated with marginal-tolerance) | **CLOSED** (operational/procedural) | S11a-2-2 (executed) |

### Operational items banked for Phase 4 remaining sessions (S11b, S11c)

| Item | Status | Scheduled |
|---|---|---|
| B-Phase4-S5-4 (install-matrix operational enforcement: pre-commit hook + CI step) | **OPEN** | S11b |
| BYF #5 (P-1 §3.4 docstring convention + engine docstring backfill ~10 wrappers) | **OPEN** | S11c |

### Operational items banked for Phase 4.5+ (post-Phase-4)

| Item | Status |
|---|---|
| B-Phase4-S7-1 (None-handling bug in 6 concrete checkers) | OPEN — Phase 4.5+ |
| B-Phase4-S10-3 (Smoke-test n_draws insufficiency — runner-integration concern) | OPEN — Phase 4.5+ |

### Informational/banked items for S12 doc-set issuance

| Item | Bank for |
|---|---|
| B-Phase4-S10-1 (Major-version bump precedent for non-parity docs) | S12 P-1 issuance — version-bump policy |
| B-Phase4-S10-2 (Cross-doc theme acknowledgment in P-1 §1 framing) | S12 P-1 issuance — §1 framing |
| B-Phase4-S11a1-1 (Forward-reference discipline) | S12 — informational |
| B-Phase4-S11a21-1 (Cascading-split self-application) | S12 — informational |
| B-Phase4-S11a21-2 (Forward-reference between sub-sessions) | S12 — informational |
| B-Phase4-S11a-2-2-1 (Marginal-overshoot principled tolerance) | S12 — informational |
| B-Phase4-S11a-2-2-2 (Cascading-split stopping condition) | S12 — informational |

### Clean state summary at S11a-3 close

| Layer | Open | Closed |
|---|---|---|
| Original 13-item inheritance | 1 (BYF #5) | 12 |
| BYF Mod-2 banked observations | 0 | 2 |
| Institutional decisions accumulated | 0 | 5 (Decision 3, A, 14, 15, 16C) |
| Phase 4 remaining-session operational | 2 (B-Phase4-S5-4 → S11b; BYF #5 → S11c) | n/a |
| Phase 4.5+ banked operational | 2 (B-Phase4-S7-1, B-Phase4-S10-3) | n/a |
| S12 informational banking | 7 | n/a |

**For Phase 4 cycle close at S13:** 1 original-13 item
remaining (BYF #5, scheduled S11c); 1 operational item
remaining (B-Phase4-S5-4, scheduled S11b). Both close before
S12 v1.2.0 doc-set issuance.

## Disposition

| Item | Pre-S11a-3 status | Post-S11a-3 status |
|---|---|---|
| Decision 3 (DOCUMENTED-DIVERGENCE forward-provisioning banking) | banked | **CLOSED** — P-3 §3.4.2 NEW |
| 13-item inheritance register | 2 open + 11 closed | **1 open + 12 closed** |
| S11a sub-session series | 3 of 4 sub-sessions complete (S11a-1, S11a-2-1, S11a-2-2 closed; S11a-3 in flight) | **S11a CLOSED** (all 4 sub-sessions complete: S11a-1, S11a-2-1, S11a-2-2, S11a-3) |
| Phase 4 cycle progress | 10 of 13 sessions (77%) | **11 of 13 sessions (85%)** |

## Banked observations from S11a-3

**B-Phase4-S11a-3-1 — Cycle-close inheritance-register
disentanglement discipline.** S11a-3's verify-at-close
inheritance-register reconciliation surfaced that the
13-item register had been tangled with institutional-
decision tracking and operational-banked-item tracking
during S11a sub-session series. Future cycle final
sessions should explicitly disentangle these tracking
layers (original-N register; banked observations from
prior cycles; institutional decisions accumulated during
current cycle; operational items banked forward) and
report each layer's closure state separately. Bank for
S13 cycle-close template.

## S11a sub-session series CLOSED

S11a series complete:

| Sub-session | Scope | LOC | Commit | CI |
|---|---|---|---|---|
| S11a-1 | #4 + #9 + O-1 doc patches | +139 | `1d8b0ff` | PASS 8m8s |
| S11a-2-1 | Decision A binding rules (§13.1-§13.4) | +167 | `0256474` | PASS 8m32s |
| S11a-2-2 | Decision A examples (§13.5) + marginal-tolerance amendment | +218 | `c765917` | PASS 7m4s |
| S11a-3 | Decision 3 (P-3 §3.4.2 forward-provisioning) | +121 | (this) | (pending) |
| **S11a total** | | **+645 LOC** | (4 commits) | (4 CI runs) |

S11a closure state: 4 inheritance items + 2 institutional
decisions disposed of across 4 sub-sessions; 645 net LOC
shipped; cascading-split discipline empirically validated
at one-level + two-level + three-level (decision tracking
plus the avoid-S11a-2-2-1 codification of marginal-overshoot
tolerance) precedent.

## Next session

**S11b — B-Phase4-S5-4 install-matrix gate operational
enforcement.** Per master plan §15 S11 + B-Phase4-S5-4
banking. Engine touches: pre-commit hook script + CI
workflow step that probes 4-surface install-matrix
consistency. ~150-200 LOC depending on pre-commit-hook
implementation choice. Last engine-touch session before
v1.2.0 doc-set issuance at S12 + cycle close at S13.

S11b's spill discipline applies; if engine LOC + test LOC
combined approaches the §13.3 combined ceiling (350 LOC),
surface to Chat for split discipline. Operational
enforcement of §8.5 (install-matrix gate) is itself the
operational-enforcement of §13.5.4's "operational
enforcement is the hardening layer" finding — institutional
self-application continues at S11b.
