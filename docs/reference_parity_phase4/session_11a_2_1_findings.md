# Phase 4 Session 11a-2-1 — P-1 §13 binding rules block (§13.1-§13.4)

**Date:** 2026-05-02
**Scope:** First of two sub-sessions in the S11a-2 cascading
split. Codifies the per-session LOC budget binding rules
(§13.1-§13.4 + closing footer); retrospective examples
(§13.5) deferred to S11a-2-2.
**Status:** COMPLETE.

## Why this is a sub-sub-session (cascading split)

S11a-2's full draft (~289 LOC across §13.1-§13.5) breached
§13.4's 200 LOC default budget at the very session
codifying §13. The institutional irony: the binding rule
fired on its own codification.

§13.2 bundled-category exception check on the unsplit S11a-2:

| Criterion | Status |
|---|---|
| 1. Architectural inseparability | ✓ technically (single §13 section; cross-references resolve internally) |
| 2. Categorical orthogonality | ❌ NOT MET — single category (one new section in one doc) |
| 3. Per-category LOC under threshold | ❌ NOT MET — single category at +289 LOC > 200 default |

Two of three criteria fail. Per the rule being codified
("not 'most of three' — the conjunction is binding"),
§13.4 spill protocol applies even on §13's own codification
session.

User Decision 15 disposition: **two-way split S11a-2-1
(binding rules) / S11a-2-2 (retrospective examples)** at
the natural seam between §13.4 and §13.5. The binding-rules
block stands alone — a future cycle author can read
§13.1-§13.4 without §13.5 and have complete operational
guidance. §13.5 expands and validates with retrospective
grounding but is supplementary.

## What changed

### P-1 §13 NEW — Per-Session Cycle Discipline (binding rules block)

**Insertion location:** `docs/engineering/parity_standard.md`
between §12.1 (Change log) and the "End of P-1 v1.1.0"
footer.

**Content added (~167 LOC including section header,
binding-rule blocks §13.1-§13.4, §13.5 placeholder
forward-reference, and updated closing footer):**

- **§13 header** (~10 LOC): codification framing referencing
  Phase 4 Session 9's bundled-category cluster + Check-in
  #2 verification protocol.
- **§13.1 Per-session LOC budget (B)** (~30 LOC): default
  200 net LOC across modified files (excluding findings
  doc); enumerated counted-toward / not-counted-toward
  surfaces.
- **§13.2 Bundled-category exception (B)** (~50 LOC): three
  sharpened criteria (architectural inseparability,
  categorical orthogonality, per-category LOC under
  threshold); explicit "all three required, not 'most of
  three'" framing; commit-body documentation requirement;
  rationale for each criterion.
- **§13.3 Test-LOC accounting (B)** (~20 LOC): 150 LOC
  test-LOC ceiling; combined ceiling 350 LOC for sessions
  hitting both budgets; counted surfaces enumerated.
- **§13.4 Spill protocol (B)** (~35 LOC): split-before-
  commit preferred over commit-and-explain; cascading-
  split naming convention covering arbitrary depth (Na →
  Na-1 → Na-1-1 → ...); reasons (reviewability, rollback
  granularity, CI verification per concern, discipline
  reinforcement); spill-doesn't-apply exclusions.
- **§13.5 Reserved (forward-reference)** (~10 LOC):
  placeholder for retrospective examples block; explicitly
  notes §13.5 lands at S11a-2-2 per cascading-split
  protocol; explicitly notes §13.1-§13.4 are operationally
  complete without §13.5.
- **Updated closing footer** (~5 LOC): cumulative Phase 4
  amendments documented in §12.1 + §13.

### Forward-reference resolution

S11a-1 added a forward-reference from P-1 §6.1 to P-1 §13
(`[§13](#13-per-session-cycle-discipline)`). Verification:
the §13 header at the post-S11a-2-1 line position matches
the Markdown-generated anchor `#13-per-session-cycle-discipline`.
Forward-reference resolves cleanly. ✓

S11a-2-1's §13.4 internally referenced "§13.5 institutional
self-application" in the cascading-split-naming-convention
text. Since §13.5 is now a placeholder (not the institutional
self-application content), the reference was rephrased to:
"Retrospective grounding for these naming conventions is
documented at §13.5 (forward-reference; lands at the next
sub-session per the cascading-split protocol)." Internal
forward-reference resolves to a §13.5 placeholder that
explicitly identifies as a forward-reference. No broken
link.

## §13.4 spill compliance

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC (excluding findings doc) |
| Sub-sub-session projection | ~140 LOC |
| **Sub-sub-session actual** | **+167 net LOC** on `parity_standard.md` |
| Margin under default | 33 LOC (~17% headroom) |

S11a-2-1 commits unblocked under §13.1 default; no §13.2
bundled-category exception engagement needed; no further
spill protocol re-engagement.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | n/a (no engine code touched) |
| Per-wrapper test suite green | n/a (no wrappers touched) |
| `parity-fast --check-environment` clean | n/a (no MANIFEST.toml changes) |
| `parity-fast` tier outcome distribution unchanged | n/a (doc-only) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

Doc-only sub-sub-session; verification surface is the docs
themselves plus post-push CI confirming no Markdown-side
regressions (none expected; CI does not parse Markdown).

## v1.2.0 amendment ledger update

S11a-2-1 contributes to the v1.2.0 ledger per master plan
§15.1:

| Doc | Section | Source | LOC |
|---|---|---|---|
| P-1 | §13 NEW (binding rules block §13.1-§13.4 + §13.5 placeholder + footer update) | S11a-2-1 Decision A | ~167 |

**Cumulative ledger after S11a-2-1:**

| Doc | LOC accumulator |
|---|---|
| P-1 | ~75 (S1 §8.5) + ~30 (S11a-1 §6.1) + ~167 (S11a-2-1 §13 binding) = **~272** |
| P-2 | ~261 (S4-S9 + S11a-1 §B.6.4) |
| P-3 | ~124 (S5-S6 + S9 + S11a-1 §3.4.1) |
| C-1 | ~205 (S1 + S10) |
| **Total** | **~862 LOC** (over §11.11 ceiling 600) |

**§11.11 cumulative ledger:** crossed 600 ceiling at S11a-1;
S11a-2-1 raises total to ~862 LOC. S12a/S12b split confirmed
as expected path. S11a-2-2 + S11a-3 + S11b + S11c will
further increase the cumulative ledger.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_standard.md` | New §13 binding-rules block (§13.1-§13.4 + §13.5 placeholder + footer update) | +167 |
| `docs/reference_parity_phase4/session_11a_2_1_findings.md` | NEW (this file) | ~155 |
| **Total (commit-counted; excludes findings doc)** | | **+167 LOC** |

## Disposition

| Item | Pre-S11a-2-1 status | Post-S11a-2-1 status |
|---|---|---|
| Decision A (P-1 §13 NEW per-session cycle discipline) | banked (post Check-in #2) | **PARTIAL — binding rules CLOSED; §13.5 retrospective examples deferred to S11a-2-2** |
| 13-item inheritance register | 3 open + 10 closed | **3 open + 10 closed** (Decision A is partial; full closure at S11a-2-2) |
| Phase 4 cycle progress | 10 of 13 sessions (77%) | **(no full-session count change; sub-sub-session)** |

## Banked observations from S11a-2-1

**B-Phase4-S11a21-1 — Cascading-split self-application
demonstrates §13's operational maturity.** §13's binding
rules fired on §13's own codification session, requiring
the split that produced this S11a-2-1 / S11a-2-2 pair. The
discipline holds even at meta-level applications. Future
cycle authors can rely on §13 firing whenever it would
fire on routine work; no implicit "codification session
exemption" exists.

**B-Phase4-S11a21-2 — Forward-reference between sub-sessions
discipline.** S11a-2-1 forward-references §13.5 as a
placeholder lands cleanly because §13.5 lands within the
hour at S11a-2-2. Same discipline as S11a-1's forward-
reference from §6.1 to §13 (B-Phase4-S11a1-1). Pattern
across both: forward-references between same-day
sub-sessions are acceptable; same-cycle forward-references
are acceptable; cross-cycle forward-references should be
avoided (rot risk). For future cycles: any forward-
reference that would not land within the same cycle should
either inline the referenced content or remove the
forward-reference until the referenced material is in tree.

## Next sub-sub-session

**S11a-2-2 — §13.5 retrospective examples block.**
~150 LOC. Three retrospective cases:
- S9 precedent disclosure (311 LOC bundled-category cluster
  meeting all three §13.2 criteria; Check-in #2 three-probe
  verification confirmed substance).
- S11a institutional self-application (Decision 14 + Decision
  15 disposition trail; "two of three is enough" anti-
  precedent).
- S1 / S5 self-validating-irony parallel (§8.5 install-
  matrix gate codified at S1 caught the gate-author at S5;
  same meta-pattern as §13 self-application).

Trigger: ready to fire after S11a-2-1 CI confirms green.
