# Phase 4 Session 12b-1-1 — P-2 §B + §C touchpoint amendments (Decision 22 split, 1 of 2)

**Date:** 2026-05-03
**Scope:** First of two sub-sub-sessions in S12b-1 split per
Decision 22. Lands the 4 P-2 touchpoint amendments (P2-T1
anchor fix; P2-T2 BVAR DD entry + B-Phase4-S5-3 sampler
correction; P2-T3 Minnesota A.3 entry; P2-T4 stochvol partial
DD entry) + B-Phase4-S8-1 trace_rank deprecation marking.
S12b-1-2 lands the 5 standalone discipline codifications
(B-Phase4-S6-1, S6-4, S6-5, Decision 20, etc.) separately.
**Status:** COMPLETE.

## Why this is a sub-sub-session (Decision 22 split)

S12b-1 trigger projected ~155 LOC; pre-commit §13.4 spill
check returned **+223 net LOC** (3 LOC over codified §13.4
marginal-tolerance band upper bound 220). Per Decision 17 /
S11b-1 ORIGINAL precedent + §13.6 (codified at S12a commit
`c66af23`) operational test for principled-content-density
overshoot: borderline-band breach at 3 LOC over threshold
upper bound is still threshold breach. Honest disposition:
split per trigger pre-planned natural seam.

User Decision 22 disposition: split into S12b-1-1 (4
touchpoints + sampler correction + trace_rank deprecation;
~75 LOC projected) + S12b-1-2 (5 standalone codifications;
~150 LOC projected). Both sub-sub-sessions clean under
§13.1 default 200 LOC.

This is the **third-level cascading split** for Phase 4
cycle (Level 1: master plan §15.1 4-way split per
Disposition 2; Level 2: S12b-1 → S12b-1-1 / S12b-1-2 per
Decision 22). Per §13.4 codified text: "the discipline has
no arbitrary depth limit, only the §13.2 criteria check at
each split-level."

## What changed

### P2-T1 — §B.6.4 cross-reference anchor fix (~1 LOC)

§B.6.4's cross-reference at line 882 was pointing at the
OLD P-3 §3.4 anchor (`#34--pattern-a1-production-locked-...`).
After S11a-1 added P-3 §3.4.1 (O-1 banking) and S11a-3 added
P-3 §3.4.2 (forward-provisioning interval), the correct
target for "Decision 3 forward-provisioning interval" is
the §3.4.2 anchor. Updated to
`#342--documented-divergence-forward-provisioning-interval-phase-4-session-11a-3`.

### P2-T2 — §C.2 BVAR DD entry + B-Phase4-S5-3 sampler correction (~28 LOC)

NEW entry under §C.2 "Phase 4 cycle additions" subsection
documenting `p3_byf_bvar_constant_vol` (Phase 4 S5; BYF
candidate #1) as the first DOCUMENTED-DIVERGENCE outcome in
TSL parity history. Includes:

- Entry framing (TSL `bond_yield_forecast` BVAR-SV with
  `force_constant_h=True` vs R `BVAR::bvar()` Kuschnig &
  Vashold 2021 JSS at matched Minnesota-prior config;
  `max_rel_diff = 1.76` on Minnesota coefficient posterior
  means; methodologically expected divergence from prior-
  framework gap).
- Cross-reference to §B.6.4 (R `bvars` install fragility on
  R 4.5.3 — closer Pattern A.2 reference unavailable).
- **B-Phase4-S5-3 sampler correction** (~6 LOC sub-block):
  the original S5 audit-script + findings-doc verdict text
  characterized the TSL sampler as "TSL NUTS (PyMC)". The
  actual TSL implementation is the **CCM-2019 Gibbs sampler**
  (Carriero-Clark-Marcellino 2019; with KSC-1998 mixture for
  SV; FFBS state sampling). The DD verdict classification
  itself (turns on prior-parameterization gap, not sampler
  choice) is preserved unchanged; only the sampler
  characterization is corrected at v1.2.0 issuance. Original
  S5 audit-script + findings doc remain authoritative for
  "what was authored when"; this correction is integration
  not silent revision.

### P2-T4 — §C.2 stochvol partial DD entry (~16 LOC)

NEW entry under §C.2 Phase 4 additions documenting
`p3_byf_stochvol_partial` (Phase 4 S6; BYF candidate #3) as
the second DOCUMENTED-DIVERGENCE outcome — partial Pattern
A.2 on the SV component only of TSL BVAR-SV. Per-equation
log-volatility posterior means at audit-time mu rel_diff
< 5% (PASS); phi rel_diff in 5-10% range (CAVEAT band);
sigma_eta record-only (prior-parameterization driven).
References the locked tolerance ladder from Phase 1 audit
2b extended at S6 + P-3 §3.4.x BVAR DD finding context.

### P2-T2/P2-T4 closing paragraph — auto-DD pattern forward-reference (~5 LOC)

Closes the §C.2 Phase 4 additions subsection with a
forward-reference to the auto-DD pattern codification
landing at S12b-1-2 (new §C.2.x). Per cascading-split
naming convention; resolves cleanly when §C.2.x lands at
the next sub-sub-session.

### P2-T3 — §C.3 Minnesota A.3 entry (~17 LOC)

NEW entry under §C.3 "Phase 4 cycle additions to §C.3"
subsection documenting `p3_byf_minnesota_dummies` (Phase 4
S4; BYF candidate #2) — partial Pattern A.3 reimplementation
of the Doan-Litterman-Sims 1984 §3 dummy-observation
reformulation of the Minnesota prior. Inline reimpl
(~50 LOC) mirrors TSL `bond_yield_forecast` subpackage's
CCM-2019 inner sampler dummy-observation construction for
posterior-mean coefficient verification. Verdict: PASS
bit-exact (1318/1318 cells matching). Per A.3 expectation
(B-Phase4-S6-5 forward-reference; codification at S12b-1-2):
catches wrapper-level regressions in dummy-observation
construction; does NOT catch TSL-vs-canonical-implementation
methodology bugs in the underlying CCM-2019 sampler (which
`p3_byf_bvar_constant_vol` audit covers under Pattern A.2
with DD).

### B-Phase4-S8-1 — trace_rank deprecation marking (~13 LOC)

In-place sub-bullet addition to the existing §C.2 `p3_vecm`
row (NOT a standalone codification per Decision 22 framing
— structurally a content-amendment-to-existing-row).
Documents the Phase 4 S8 alias additions
(`determined_rank_trace`, `cointegrating_rank`) for naming-
convention bridging + states future code preference for
`cointegrating_rank` (matches registry-checker contract at
P-2 §D.1 `vecm_cointegration_rank`). `trace_rank` retained
unchanged for backward compat; deprecation marking is
documentation-only at v1.2.0 issuance (no code-level
deprecation warning).

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection (S12b-1-1 split) | ~75 LOC |
| **S12b-1-1 actual** | **+84 net LOC** (85 insertions, 1 deletion) |
| Position vs default | UNDER by 116 LOC (~58% headroom) |
| §13.4 marginal-tolerance band | not engaged (well under default) |

Clean commit. The +9 LOC overshoot vs trigger projection
matches Phase 4 empirical 1.1-1.2x near-match pattern for
small targeted sub-sessions (vs the 1.5-2x pattern for
larger batches; B-Phase4-S12a-2).

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 37.03s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S12b-1-1 contributes touchpoint amendments to P-2 v1.2.0
issuance. The full v1.2.0 issuance event lands at S12b-1-2
+ S12b-2 (full P-2 §C + §D coverage); the v1.2.0 change-log
entry at §H.2 lands at S12b-2 (the final P-2 sub-sub-session).

**Cumulative ledger after S12b-1-1:**

| Doc | Status |
|---|---|
| P-1 | v1.2.0 ISSUED (commit `c66af23`) |
| P-2 | v1.2.0 PARTIAL (touchpoints landed at S12b-1-1; codifications at S12b-1-2; §D at S12b-2) |
| P-3 | accumulator (pending S12c) |
| C-1 | v2.0.0 (Phase 4 S10) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_diagnostic_reference.md` | P2-T1 anchor fix; §C.2 Phase 4 additions subsection (BVAR DD + sampler correction + stochvol partial DD); §C.3 Phase 4 additions subsection (Minnesota A.3 entry); B-Phase4-S8-1 trace_rank sub-bullet on `p3_vecm` row | +84 net |
| `docs/reference_parity_phase4/session_12b_1_1_findings.md` | NEW (this file) | ~150 |
| **Total (commit-counted)** | | **+84 LOC** |

## Disposition

| Item | Pre-S12b-1-1 status | Post-S12b-1-1 status |
|---|---|---|
| P-2 §B + §C touchpoint amendments | banked (S12b-1 scope) | **5 of 5 LANDED** (P2-T1, T2, T3, T4, B-Phase4-S8-1) |
| P-2 §B + §C standalone codifications | banked | deferred to S12b-1-2 (5 codifications: B-S6-1, S6-4, S6-5, Decision 20; trace_rank already landed at S12b-1-1) |
| 19 touchpoints across v1.2.0 doc-set | 5 of 19 LANDED post-S12a | **9 of 19 LANDED** (5 P-1 + 4 P-2) |
| 15 new codifications across v1.2.0 doc-set | 6 of 15 LANDED post-S12a | **7 of 15 LANDED** (6 P-1 + B-Phase4-S8-1; remaining 4 P-2 codifications + B-Phase4-S6-1 cross-doc P-3 = 5 to go) |

## Banked observations from S12b-1-1

**B-Phase4-S12b-1-1 — Borderline-band spill discipline.**
S12b-1 actual +223 LOC = 3 LOC over codified §13.4 marginal-
tolerance band upper bound (220). Per trigger explicit
directive + Decision 17 + §13.6 codified framing:
borderline-band overshoot at threshold edge is still
threshold breach. Pre-planned split fired per discipline.
Decision 21 principled-content-density operational test
confirmed all 9 blocks pass reader-population test (not
measurement-variance) — so the disposition is split, not
amendment. Bank as institutional precedent: §13.4 marginal-
tolerance band is bounded; principled content density alone
doesn't extend the band; honest split is the disposition.

This is the strongest possible Decision 17 + §13.6
application: 3-LOC overshoot at threshold edge, with
principled content density, correctly disposed as split
rather than amendment. Future cycle authors will see this
case in the institutional record and understand: §13.4
marginal-tolerance band is a hard threshold, not a soft
target.

**B-Phase4-S12b-1-2 — Cascading-split ordering: touchpoints
before codifications.** When a sub-session splits into
touchpoint-amendments + standalone-codifications, sequence
the touchpoints first. Touchpoints are factual (specific
content additions per Phase 1 enumeration); codifications
reference touchpoint content with cross-references. Landing
touchpoints first means codifications can cleanly
cross-reference newly-landed content without forward-
references that risk rot. Bank as institutional precedent
for future Decision 22-style splits.

## Next sub-sub-session

**S12b-1-2 — 5 standalone codifications (~150 LOC).**

Per Decision 22 split:
- B-Phase4-S6-1: §C.2.x auto-DD pattern codification (~30 LOC)
- B-Phase4-S6-4: §C.2.y auto-DD audit-design discipline (~38 LOC)
- B-Phase4-S6-5: §C.6 Pattern A.2 vs A.3 expectation differentiation (~37 LOC)
- Decision 20: §C.7 convention-with-application landing pattern (~32 LOC)
- Misc cross-reference verification (~13 LOC)

S12b-1-2 reuses the working-tree edits backed out of
S12b-1-1 (the 4 codification blocks I authored before the
split decision). The blocks are conceptually complete; just
need re-application + verification that touchpoint cross-
references resolve cleanly post-S12b-1-1.

Trigger: ready to fire after S12b-1-1 CI confirms green.
