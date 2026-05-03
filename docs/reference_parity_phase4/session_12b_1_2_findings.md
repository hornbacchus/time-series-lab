# Phase 4 Session 12b-1-2 — P-2 §C standalone codifications (Decision 22 split, 2 of 2)

**Date:** 2026-05-03
**Scope:** Second of two sub-sub-sessions in S12b-1 split per
Decision 22. Lands the 5 standalone P-2 §C discipline
codifications (B-Phase4-S6-1 §C.2.x; B-Phase4-S6-4 §C.2.y;
B-Phase4-S6-5 §C.6; Decision 20 §C.7; cross-reference
verification). Closes S12b-1 in full.
**Status:** COMPLETE.

## Why this is a sub-sub-session

S12b-1 was split per Decision 22 into S12b-1-1 (4 touchpoint
amendments + sampler correction + trace_rank deprecation;
+84 net LOC; commit `5e0c93c`, CI PASS 7m16s) and S12b-1-2
(this commit; 5 standalone codifications; ~143 net LOC).
Per B-Phase4-S12b-1-2 institutional precedent: touchpoints
sequenced first so codifications can cross-reference
newly-landed content.

## What changed

### B-Phase4-S6-1 — §C.2.x auto-DD pattern (~30 LOC)

NEW subsection §C.2.x codifying the auto-DD pattern: when
a Pattern A.2 audit selects a reference whose methodological
framework is known a priori to differ from TSL's (different
prior parameterization; different mixture formulation;
different sampler family with non-equivalent posteriors),
the audit's `compare()` logic should:

1. Pre-compute the methodology-equivalence verdict at
   design time (embed DD verdict in compare() return path).
2. Document the methodology gap explicitly
   (`divergence_rationale` field).
3. Preserve numerical-fidelity reporting (max_rel_diff,
   posterior summaries; verdict classification is overlay).
4. Cross-reference the framework gap (link to §B Pattern J
   catalog OR P-3 §3.4.x empirical findings entry).

Cross-references the two motivating cases landed at S12b-1-1:
`p3_byf_bvar_constant_vol` (Phase 4 S5; BYF #1) +
`p3_byf_stochvol_partial` (Phase 4 S6; BYF #3) — both
PASS-A.2 (DOCUMENTED-DIVERGENCE) outcomes that surfaced the
DD forward-provisioned path wired at Phase 3.5 S1 (P-3
§3.4.2 forward-provisioning interval).

Per Disposition 3: B-Phase4-S6-1 lands at BOTH P-2 (this
session, registry-side framing) AND P-3 (deferred to S12c,
empirical-findings-side framing).

### B-Phase4-S6-4 — §C.2.y auto-DD audit-design discipline (~38 LOC)

NEW subsection §C.2.y codifying the discipline that the
auto-DD pattern requires audit-design-time methodology
verification BEFORE tolerance ladder selection. Four-step
discipline:

1. **Pre-flight methodology compatibility check** before
   selecting a Pattern A.2 reference.
2. **If methodology gap exists**: prefer different reference
   (option a) OR accept auto-DD pattern with explicit
   framework-gap documentation (option b; acceptable when
   no closer reference is operationally available).
3. **Pre-flight tolerance band selection**: tolerance band
   documents "methodological noise floor", NOT "passes the
   test".
4. **Audit-report transparency**: auto-DD verdict visible
   as PASS-A.2 (DOCUMENTED-DIVERGENCE), not silently
   downgraded/upgraded.

Bank as institutional precedent for future cross-package
A.2 audit design.

### B-Phase4-S6-5 — §C.6 Pattern A.2 vs A.3 expectation differentiation (~37 LOC)

NEW top-level subsection §C.6 (after existing §C.5)
codifying the expectation gap between Pattern A.2 (cross-
package bit-exact) and Pattern A.3 (self-parity / paper-
formula reimplementation):

- **Pattern A.2 expectation:** bit-exact match within
  closed-form numerical noise (~1e-13 abs typical). DD
  outcome is explicit acknowledgment of methodology gap,
  NOT "good enough" PASS.
- **Pattern A.3 expectation:** regression-sentinel scope
  only. Catches wrapper-level regressions; does NOT catch
  TSL-vs-canonical methodology bugs.

Three failure modes documented in a wrong-attribution table
+ application discipline statement extending §C.5's
decision tree.

### Decision 20 — §C.7 convention-with-application landing pattern (~32 LOC)

NEW top-level subsection §C.7 codifying the institutional
pattern: when codifying a new Pattern A sub-pattern OR
audit-design discipline OR registry-checker contract,
prefer landing the codification with first concrete
applications in the same commit. Two empirical Phase 4
precedents:

- **S11a-2-2** — codified P-1 §13.4 marginal-overshoot
  tolerance in same commit needing it.
- **S11c-1** — codified P-1 §3.4 docstring convention with
  5 audit-field-touched wrapper backfills in same commit.

**Application examples in P-2 §C:** §C.2.x auto-DD pattern
codification (B-Phase4-S6-1, this session) directly motivated
by §C.2's two BVAR-cycle DD entries (landed S12b-1-1). §C.3
Minnesota A.3 entry (S12b-1-1) exemplifies §C.6 A.2-vs-A.3
differentiation principle (this session). The convention-
with-application pattern was honored across the S12b-1 /
S12b-1-1 / S12b-1-2 split despite the cascading-split
sequencing constraint.

### Cross-reference verification (~6 LOC; folded into above)

Removed the placeholder forward-reference text added at
S12b-1-1 ("Both entries reflect a methodology-gap pattern
(auto-DD) that S12b-1-2 codifies at new §C.2.x...") and
replaced with live cross-reference text ("Both entries
reflect the auto-DD pattern codified at §C.2.x + §C.2.y
below.") — clean live link now that §C.2.x exists.

§C-internal cross-references verified post-S12b-1-2:
- §C.2 → §C.2.x: ✅ resolves (live link)
- §C.2.x → §C.2 + P-3 §3.4.2: ✅ resolves
- §C.2.y → §C.2.x: ✅ resolves
- §C.6 → §C.5: ✅ resolves
- §C.7 → §C.2 + §C.3 + §C.6 + P-1 §13.5.2/§13.5.3: ✅ all resolve

§C structure post-S12b-1-2:
- C.1, C.2, C.2.x, C.2.y, C.3, C.4, C.5, C.6, C.7

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~150 LOC |
| **S12b-1-2 actual** | **+143 net LOC** (152 insertions, 9 deletions) |
| Position vs default | UNDER by 57 LOC (~28% headroom) |
| Position vs marginal-tolerance band | not engaged (well under default) |

Clean commit. The -7 LOC delta vs trigger projection (143 vs
~150) reflects content-density convergence as the §C.2.x +
§C.2.y + §C.6 + §C.7 blocks were drafted during the original
S12b-1 attempt; re-applying after the S12b-1-1 split was a
structurally clean operation with the placeholder text
removed.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 29.83s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

**Cumulative ledger after S12b-1-2:**

| Doc | Status |
|---|---|
| P-1 | v1.2.0 ISSUED (commit `c66af23`) |
| P-2 | v1.2.0 PARTIAL (S12b-1 §B + §C complete: touchpoints at S12b-1-1 + codifications at S12b-1-2; remaining §D + change-log issuance at S12b-2) |
| P-3 | accumulator (pending S12c) |
| C-1 | v2.0.0 (Phase 4 S10) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_diagnostic_reference.md` | §C.2.x + §C.2.y NEW (auto-DD pattern + audit-design discipline); §C.6 NEW (Pattern A.2 vs A.3 differentiation); §C.7 NEW (Decision 20 convention-with-application landing pattern); placeholder forward-reference text → live cross-reference | +143 net |
| `docs/reference_parity_phase4/session_12b_1_2_findings.md` | NEW (this file) | ~155 |
| **Total (commit-counted)** | | **+143 LOC** |

## Disposition

| Item | Pre-S12b-1-2 status | Post-S12b-1-2 status |
|---|---|---|
| P-2 §C standalone codifications | banked (S12b-1-2 scope) | **5 of 5 LANDED** (B-Phase4-S6-1, S6-4, S6-5, Decision 20, cross-references) |
| 19 touchpoints across v1.2.0 doc-set | 9 of 19 LANDED post-S12b-1-1 | **9 of 19 LANDED** (no touchpoints in S12b-1-2; this is codifications-only sub-sub-session) |
| 15 new codifications across v1.2.0 doc-set | 7 of 15 LANDED post-S12b-1-1 | **11 of 15 LANDED** (10 P-x + B-Phase4-S6-1 P-2 side; remaining B-Phase4-S7-4 + S6-1 P-3 side + 2 P-2 §D = 4 to go) |

S12b-1 sub-session series CLOSED (both S12b-1-1 + S12b-1-2
complete). P-2 §B + §C amendments fully landed; P-2 §D +
change-log issuance remains for S12b-2.

## Banked observations from S12b-1-2

**B-Phase4-S12b-1-2-A — Decision 22 split executed cleanly
end-to-end.** S12b-1 spilled at +223 LOC (3 LOC over §13.4
upper bound); user disposition was Decision 22 split into
S12b-1-1 (~84 LOC) + S12b-1-2 (~143 LOC). Both sub-sub-
sessions clean under §13.4 default 200 LOC. Cross-references
between sub-sub-sessions resolved cleanly per
B-Phase4-S12b-1-2 sequencing discipline (touchpoints first;
codifications second). Bank as institutional precedent: when
a sub-session spills, the trigger's pre-planned natural seam
typically partitions cleanly into 2 sub-sub-sessions with
distinct architectural concerns; honoring the seam preserves
both LOC discipline AND cross-reference integrity.

**B-Phase4-S12b-1-2-B — Convention-with-application pattern
honored across cascading-split sequencing.** The §C.7
codification documents the convention-with-application
landing pattern empirically. Despite the §C.7 codification
itself landing at S12b-1-2 (separate sub-sub-session from
the §C.2 / §C.3 motivating cases at S12b-1-1), the
convention's spirit was preserved via the sequencing
discipline (touchpoints first, codifications cross-reference
back). Cross-cycle codifications can honor the convention-
with-application pattern across cascading-split boundaries
when the sequencing discipline is honored. Bank as
institutional precedent for future cascading-split codification
sessions.

## Next sub-session

**S12b-2 — P-2 §D registry expansion + new codifications
(~75 LOC).**

Per Phase 1 enumeration:
- P2-T5: §D registry table out-of-date (14 listed; should
  be 19 with S7 P4-1.1 expansion); intervals_test INVERTED
  semantics note (~15 LOC)
- P2-T6: §D Step 3 output dict shape requirements table
  missing 5 S7-added invariants' required keys (~10 LOC)
- P2-T7: NEW §D.x audit-side wrapper-declaration table
  (9 S9 declarations; tolerance values; dormant pending
  runner integration) (~20 LOC)
- P2-T8: §D O-2 Pattern F threshold tightening event
  undocumented (~8 LOC)
- B-Phase4-S7-4: NEW §D.x registry-expansion-test-
  coordination discipline (~15 LOC)
- B-Phase4-S9-3: §D intervals_test INVERTED semantics
  codification (folded into P2-T5)
- §H.2 v1.2.0 change-log entry (~10 LOC)

Trigger: ready to fire after S12b-1-2 CI confirms green.
S12b-2 closes P-2 v1.2.0 in full.
