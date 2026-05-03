# Phase 4 Session 12 Phase 1 — Read-only touchpoint enumeration for v1.2.0 doc-set

**Date:** 2026-05-03
**Scope:** First of four phases in S12. Phase 1 produces a
declared touchpoint list across P-1, P-2, P-3 for
v1.2.0 doc-set issuance. **READ-ONLY** — no content edits to
P-x docs in this commit.
**Status:** COMPLETE (Phase 1 deliverable landed as findings
doc).

## Bounded-coherence framing

Per Chat-exchange disposition, S12 issues v1.2.0 doc-set
under bounded-coherence framing: **declared touchpoints +
new codifications + mechanics; no discretionary re-edits**.
Phase 1 (this commit) enumerates the touchpoints + new
codifications + recommended split structure for review
before Phase 2 (write) begins.

## P-1 (parity_standard.md) — touchpoints + new codifications

| ID | Section | Issue / Edit | LOC |
|---|---|---|---|
| P1-T1 | §1 | Cross-doc unifying-theme framing missing (failure classes invisible to local-only testing) | ~12 |
| P1-T2 | §3.4 | Two-block docstring pattern not yet codified per S11c-1 empirical landing | ~10 |
| P1-T3 | §8.5 | Belt-and-suspenders pattern not reflected (was prose-only at S1; S11b-3 made operational) | ~12 |
| P1-T4 | §13.3 | "in addition to" ambiguity needs clarifying sentence (per B-Phase4-S11b-2-1) | ~5 |
| P1-T5 | new §13.6 OR §13.4 addendum | Principled-multi-reader content density vs measurement-variance distinction | ~10-15 |
| Decision 18 | §13.3 | Clarifying sentence (folded into P1-T4) | — |
| Decision 21 | §13.5/§13.6 | Principled-multi-reader (folded into P1-T5) | — |
| B-Phase4-S10-1 | new §1.x or §12.2 | Version-bump criteria mirror to C-1 v2.0.0 precedent | ~10 |
| B-Phase4-S10-2 | §1 | Cross-doc unifying-theme (folded into P1-T1) | — |
| B-Phase4-S11b-3-2 | §8.5 | Belt-and-suspenders (folded into P1-T3) | — |
| B-Phase4-S11c-1-2 | §3.4 | Two-block docstring (folded into P1-T2) | — |
| Change log | §12.1 | v1.2.0 entry | ~10 |

**P-1 total: ~86 LOC** (touchpoints + new codifications + change log).

## P-2 (parity_diagnostic_reference.md) — touchpoints + new codifications

| ID | Section | Issue / Edit | LOC |
|---|---|---|---|
| P2-T1 | §B.6.4 | Cross-reference link-target wrong (points to OLD P-3 §3.4 anchor; should target §3.4.2) | ~1 |
| P2-T2 | §C.2 | Phase 4 S5 BVAR Pattern A.2 DD entry missing; needs B-Phase4-S5-3 sampler correction (CCM-2019 Gibbs not PyMC NUTS) | ~30 |
| P2-T3 | §C.3/§C.4 | Phase 4 S4 Minnesota dummy-observation A.3 reimpl entry missing | ~25 |
| P2-T4 | §C.2 | Phase 4 S6 stochvol partial A.2 entry missing | ~25 |
| P2-T5 | §D registry table | Out-of-date (14 listed; should be 19 with S7 P4-1.1 expansion) + intervals_test INVERTED semantics note | ~15 |
| P2-T6 | §D Step 3 | Output dict shape requirements table missing 5 S7-added invariants' required keys | ~10 |
| P2-T7 | new §D.x | Audit-side wrapper-declaration table (9 S9 declarations; tolerance values; dormant pending runner integration) | ~20 |
| P2-T8 | §D | O-2 Pattern F threshold tightening event undocumented (var_eigenvalues <0.999 → <0.9995 at S9) | ~8 |
| B-Phase4-S5-3 | §C.2 | Sampler correction (folded into P2-T2) | — |
| B-Phase4-S6-1 | §C.x | Auto-DD pattern codification (also lands at P-3 per Disposition 3) | ~10 |
| B-Phase4-S6-4 | new §C.x | Auto-DD audit-design discipline (pre-flight verify methodological compatibility before tolerance band selection) | ~15 |
| B-Phase4-S6-5 | §C.5 | Pattern A.2 vs A.3 expectation differentiation (A.2 expects bit-exact unless DD; A.3 expects regression-sentinel scope only) | ~15 |
| B-Phase4-S7-4 | new §D.x | Registry-expansion-test-coordination discipline (registry stub-vs-concrete contract violation precedent) | ~15 |
| B-Phase4-S8-1 | §C.x or §D.x | trace_rank deprecation marking per Decision 10 (Johansen alias trio) | ~10 |
| B-Phase4-S9-3 | §D.x | intervals_test INVERTED semantics (folded into P2-T5) | — |
| Decision 20 | new §x | Convention-with-application landing pattern | ~10 |
| Change log | §H.2 | v1.2.0 entry | ~10 |

**P-2 total: ~219 LOC** (touchpoints + new codifications + change log).

## P-3 (parity_empirical_findings.md) — touchpoints + new codifications

| ID | Section | Issue / Edit | LOC |
|---|---|---|---|
| P3-T1 | new §3.4.x | Phase 4 S5 BVAR DD finding (first DD outcome in TSL parity history) | ~25 |
| P3-T2 | §3.4.x sibling | Phase 4 S6 stochvol partial A.2 finding | ~20 |
| P3-T3 | §6.6 | Stale framing (DD verdict reservation NOW triggered at Phase 4 S5; classification recipe instance landed) | ~5 |
| P3-T4 | §7 (carry-forward) | All 3 items now closed (P4-1 at S7+S8+S9; P4-2 at S2; P4-3 at S3); add closure dispositions | ~15 |
| P3-T5 | new §6.10 | Phase 4 cycle close consolidation (13 inheritance items dispositioned: 12 closed + 1 OPEN forward-banked items B-Phase4-S7-1 + B-Phase4-S10-3) | ~20 |
| **P3-T6** | §8 + subsections | **§8 numbering fix per Disposition 1** — `## 8.` subsections currently numbered `### 7.1`, `### 7.2`, `### 7.3` (pre-existing v1.1.0 amendment artifact); fix to `### 8.1`, `### 8.2`, `### 8.3` | ~3 |
| B-Phase4-S6-1 | §3.4.x | Auto-DD pattern codification (cross-doc reuse with P-2 per Disposition 3) | ~10 |
| Change log | §10.1 | v1.2.0 entry | ~15 |

**P-3 total: ~113 LOC** (touchpoints + new codifications + change log).

**Disposition 1 honored:** P3-T6 §8 numbering fix elevated from "out of scope per S12 framing" to declared touchpoint per Chat exchange.

## Combined LOC totals + Option C four-way split (Disposition 2)

| Doc | Touchpoint LOC | New-codification LOC | Change log | Total |
|---|---|---|---|---|
| P-1 | ~49 | ~27 | ~10 | **~86** |
| P-2 | ~109 | ~100 | ~10 | **~219** |
| P-3 | ~88 | ~10 | ~15 | **~113** |
| **Sum** | **~246** | **~137** | **~35** | **~418** |

§13.4 spill check on combined v1.2.0 issuance: ~418 LOC =
+218 LOC over §13.1 default (109% over). §13.2 bundled-
category exception fails on per-category criterion (P-2
alone at ~219 LOC). **S12a/S12b/S12c split required as
anticipated by §11.11 trigger; Option C subsplits P-2 per
Chat disposition.**

### Recommended split (Disposition 2 — Option C four-way):

| Sub-session | Scope | LOC |
|---|---|---|
| **S12a** | P-1 v1.2.0 (touchpoints + new codifications + change log) | ~86 |
| **S12b-1** | P-2 §B + §C amendments (coherence + BVAR/Minnesota/stochvol entries + auto-DD + Pattern A.2/A.3 differentiation + sampler correction) | ~155 |
| **S12b-2** | P-2 §D registry expansion + new codifications (registry table update + Step 3 table + audit-side declaration table + O-2 event + intervals_test INVERTED + S7-4 registry-expansion-test-coordination + S8-1 trace_rank + Decision 20 + change log) | ~75 (includes change log) |
| **S12c** | P-3 v1.2.0 (touchpoints + new codifications + change log) | ~113 |

All four sub-sessions clean under §13.1 default 200 LOC
(largest is S12b-1 at ~155 LOC; ~45 LOC headroom). Per
Disposition 4: NO pre-split for hypothetical S12c overshoot
(landing within projection); §13.4 spill protocol applies
in real-time if any sub-session crosses threshold.

## Banked observations register reconciliation (~53 entries)

| Category | Count | Disposition |
|---|---|---|
| **Codified at S12** | **15** | Land at v1.2.0 issuance per touchpoint enumeration above |
| P-1 codifications | 6 | Decisions 18, 21; B-Phase4-S10-1, S10-2, S11b-3-2, S11c-1-2 |
| P-2 codifications | 8 | B-Phase4-S5-3, S6-1, S6-4, S6-5, S7-4, S8-1, S9-3; Decision 20 |
| P-3 codifications | 1 | B-Phase4-S6-1 (cross-doc reuse per Disposition 3) |
| **Closed at Phase 4** | **22** | Cycle work; do not need codification |
| 13-item inheritance register | 13 | P4-1, P4-2, P4-3, BYF #1-#10 |
| BYF Mod-2 banked observations | 2 | O-1, O-2 |
| Phase 4 institutional decisions | 7 | Decision 3, A, 14, 15, 16C, 17, 19A |
| **Deferred to Phase 4.5+** | **2** | Forward-banked |
| Forward-banked items | 2 | B-Phase4-S7-1 (None-handling bug); B-Phase4-S10-3 (smoke-test n_draws insufficiency) |
| **Cycle-internal operational** | **14** | No codification needed |
| S11a-* internal | 6 | B-Phase4-S11a1-1, S11a21-1, S11a21-2, S11a-2-2-1, S11a-2-2-2, S11a-3-1 |
| S11b-* internal | 5 | B-Phase4-S11b-1-1 (corrected), S11b-1-2, S11b-1-3, S11b-2-2, S11b-3-1 |
| S11c-* internal | 3 | B-Phase4-S11c-1-1, S11c-2-1, S11c-2-2 |
| **Total banked across Phase 4** | **53** | |

## Disposition outcomes (Chat exchange disposition record)

1. **Disposition 1:** §8 numbering fix elevated from out-of-scope to declared touchpoint P3-T6 ✓
2. **Disposition 2:** Option C four-way split (S12a / S12b-1 / S12b-2 / S12c) per recommended structure above ✓
3. **Disposition 3:** B-Phase4-S6-1 lands at both P-2 (auto-DD pattern codification) and P-3 (auto-DD finding cross-doc reuse) ✓
4. **Disposition 4:** No pre-split for hypothetical sub-session overshoot; §13.4 spill protocol applies in real-time at sub-session execution if threshold crossed ✓
5. **Disposition 5:** Phase 1 findings doc landed as standalone commit (this commit; no P-x edits) ✓

## §13.4 spill compliance

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| **S12 Phase 1 actual** | **+~210 LOC** (this findings doc; expected at trigger projection) |
| Position vs default | UNDER by ~10 LOC if estimate holds |
| §13.4 marginal-tolerance band | 5-10% (200-220 LOC) |

This commit ships the findings doc only. No P-x doc edits.
Per Decision 17 / S11b-1 ORIGINAL precedent: if actual LOC
exceeds 220 (marginal-tolerance upper bound), surface to
Chat for split disposition rather than codify content-density
as measurement-variance.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | n/a (no engine code touched; pytest unaffected) |
| `parity-fast --check-environment` clean | n/a (no MANIFEST drift) |
| Validation script live state (P-1 §8.5 gate) | n/a (no install-matrix changes) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

## Next sub-session

**S12a — P-1 v1.2.0 issuance** (~86 LOC; first of four
sub-sessions per Disposition 2). Trigger: ready to fire
after S12 Phase 1 findings doc CI confirms green.

S12 sub-session topology:
- ⏳ **S12a** — P-1 v1.2.0 (~86 LOC)
- ⏳ **S12b-1** — P-2 §B + §C amendments (~155 LOC)
- ⏳ **S12b-2** — P-2 §D registry expansion + new codifications (~75 LOC)
- ⏳ **S12c** — P-3 v1.2.0 (~113 LOC)
- ⏳ **S13** — P-4 v1.2.0 + Phase 4 cycle close (post-S12)
