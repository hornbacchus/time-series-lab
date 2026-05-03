# Phase 4 Session 12b-2 — P-2 v1.2.0 §D + issuance close (Option C four-way split, 3 of 4)

**Date:** 2026-05-03
**Scope:** Third of four sub-sessions in S12 Option C four-way
split. Lands P-2 §D registry expansion + audit-side declaration
table + B-Phase4-S7-4 codification + P-2 v1.2.0 issuance
close (header bump + comprehensive change-log entry).
Closes P-2 v1.2.0 issuance in full.
**Status:** COMPLETE.

## What changed

### P2-T5 — §D registry table count update (~30 LOC)

§D opening text updated: "14 concrete invariants populated as
of Session 13 close" → "**19 concrete invariants populated as
of Phase 4 Session 7 close** (14 from Phase 3 + 5 from Phase
4 P4-1.1 expansion)". Added 5 new rows for the S7-added
invariants:
- `mcmc_convergence` (omnibus) — MCMC family (SV, BVAR-SV)
- `evt_extremal_index` — EVT POT/GPD
- `mint_coherence` — MinT reconciliation
- `attention_normalization` — Transformer (multi-head)
- `intervals_test` (Christoffersen LR) — CAViaR / VaR backtester

**B-Phase4-S9-3 INVERTED semantics convention call-out**
added inline: `intervals_test` uses INVERTED tolerance
semantic (PASS if Christoffersen LR p-value ≥ floor; default
0.05) vs the other 18 invariants which treat tolerance as an
upper bound. Documented at registry checker
(`structural_invariants.py:1040-1093`) + audit-side
declaration in `caviar_sav.py` with matching framing. Future
inverted-semantics invariants should use the same explicit-
docstring convention.

### P2-T8 — Pattern F threshold-tightening event (~10 LOC)

New paragraph in §D opening documenting Phase 4 S9 tightening
of `var_eigenvalues` PASS threshold from `<0.999` to
`<0.9995` per O-2 corrective action. Early-warning band
(0.9995 to 1.0) provides explicit operational headroom for
near-unit-root macro fixtures. BYF Mod-2 34-mat fixture
landed at 0.9988 with 7e-4 margin. Cross-reference to P-3
§3.4.1 O-1 banking entry.

### P2-T6 — Step 3 output dict shape requirements table (~10 LOC)

5 new rows added to the Step 3 table for S7-added
invariants' required TSL output keys:
- `mcmc_convergence`: ess_min (required); rhat_max (optional;
  None on single-chain Gibbs); geweke_max_abs_z (optional)
- `evt_extremal_index`: theta (Ferro-Segers extremal index in [0, 1])
- `mint_coherence`: coherence_residual (L2 norm of summing-
  constraint violation)
- `attention_normalization`: attention_matrix (2-D or 3-D
  ndarray)
- `intervals_test`: chris_pvalue (Christoffersen LR p-value)

### P2-T7 — §D.1.5 NEW audit-side wrapper-declaration table (~30 LOC)

NEW subsection §D.1.5 documenting the 9 S9 wrapper
declarations:

| Wrapper audit-script | Invariant | Tolerance |
|---|---|---|
| kalman_filter.py | kalman_covariance_ordering | 1e-6 abs |
| johansen_bartlett.py | vecm_cointegration_rank | 0 abs (strict) |
| mcmc_sv_gaussian.py | mcmc_convergence | 200 ESS_min |
| mcmc_sv_student_t.py | mcmc_convergence | 200 ESS_min |
| evt_ferro_segers.py | evt_extremal_index | 0.01 abs slack |
| mint_family.py | mint_coherence | 1e-10 abs |
| transformer_attention.py | attention_normalization | 1e-6 abs |
| caviar_sav.py | intervals_test (INVERTED) | 0.05 p-value floor |
| p3_bond_yield_forecast.py | mcmc_convergence | 200 ESS_min |

Documents the dormant-pending-runner status (B-Phase4-S9-2
banked observation; runner integration deferred to Phase
4.5+). Also references the Phase 4 Check-in #2 deep-
verification probe that confirmed tolerance-value semantic
correctness across all 9 declarations.

### B-Phase4-S7-4 — §D.1.6 NEW registry-expansion-test-coordination discipline (~25 LOC)

NEW subsection §D.1.6 codifying the discipline that surfaced
at Phase 4 S7 P4-1.1 registry expansion. The pre-S7
`_test_structural_invariants.py` test asserted ALL
registered invariants raise `NotImplementedError`; this
contract held only when ALL registered invariants were stubs.
S7's expansion added 5 concrete checkers that broke the
contract.

4-step discipline:
1. Audit existing tests for stub-vs-concrete contract
   assumptions BEFORE adding new invariant types.
2. Update test contract in same commit as registry expansion
   when contract assumption no longer holds.
3. Document test-contract evolution in findings doc + commit
   message.
4. Run full test suite after registry expansion.

Bank as institutional precedent for future Phase 4.5+
registry expansion (HMM-EM extensions, conformal-mondrian
splits).

### P-2 v1.2.0 issuance close — version header bump + change log entry

P-2 header version bumped: `v1.1.0 → v1.2.0` (cites Phase 4
Session 12b-2 issuance date).

Comprehensive change log entry at §H.2 covering all S12b-1-1
+ S12b-1-2 + S12b-2 P-2 amendments — Phase 4 cycle close
amendments organized by section: §B.6.4 NEW; §C.2 Phase 4
additions (BVAR DD + sampler correction + stochvol partial
DD); §C.2.x NEW auto-DD pattern; §C.2.y NEW auto-DD
discipline; §C.2 trace_rank deprecation marking; §C.3 Phase
4 additions (Minnesota A.3); §C.6 NEW A.2-vs-A.3
differentiation; §C.7 NEW convention-with-application
landing; §D registry table 14→19; §D Pattern F threshold-
tightening event; §D Step 3 table updates; §D.1.5 NEW
audit-side declaration table; §D.1.6 NEW registry-expansion-
test-coordination discipline; §B.6.4 cross-reference fix.

End-of-doc footer updated: "End of Parity Diagnostic
Reference P-2 v1.1.0" → "P-2 v1.2.0".

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection | ~78 LOC |
| Phase 4 empirical 1.5-2× pattern | 117-156 LOC predicted |
| **S12b-2 actual** | **+100 net LOC** (109 insertions, 9 deletions) |
| Position vs default | UNDER by 100 LOC (50% headroom) |
| Position vs predicted range | within (1.28× lower estimate; below upper bound) |
| Position vs marginal-tolerance band | not engaged |

Clean commit. The actual landed comfortably between trigger
projection and Phase 4 empirical 1.5-2× upper bound,
matching the lower-bound prediction more closely.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 40.03s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (doc-only) |
| New "Validate install-matrix consistency (P-1 §8.5)" CI step | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

**P-2 v1.2.0 ISSUED.**

**Cumulative ledger after S12b-2:**

| Doc | Status |
|---|---|
| **P-1** | **v1.2.0 ISSUED** (commit `c66af23`) ✅ |
| **P-2** | **v1.2.0 ISSUED** (commit pending push) ✅ |
| P-3 | accumulator (pending S12c) |
| C-1 | v2.0.0 (Phase 4 S10) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_diagnostic_reference.md` | Header bump v1.1.0 → v1.2.0; §D registry table count + 5 new rows + INVERTED semantics call-out + Pattern F threshold-tightening event; §D Step 3 table 5 new rows; §D.1.5 NEW audit-side declaration table; §D.1.6 NEW registry-expansion-test-coordination discipline; §H.2 change log v1.2.0 entry; end-of-doc footer | +100 net |
| `docs/reference_parity_phase4/session_12b_2_findings.md` | NEW (this file) | ~145 |
| **Total (commit-counted)** | | **+100 LOC** |

## Disposition

| Item | Pre-S12b-2 status | Post-S12b-2 status |
|---|---|---|
| P-2 §D amendments | banked (S12b-2 scope) | **4 of 4 LANDED** (P2-T5, T6, T7, T8) |
| P-2 standalone codifications | 6 of 8 LANDED (S12b-1 series) | **8 of 8 LANDED** (B-Phase4-S7-4 + B-Phase4-S9-3 INVERTED semantics added at S12b-2) |
| **P-2 v1.2.0 issuance** | PARTIAL | **ISSUED** ✅ |
| 19 touchpoints across v1.2.0 doc-set | 9 of 19 LANDED | **13 of 19 LANDED** (5 P-1 + 8 P-2; remaining 6 P-3 at S12c) |
| 15 new codifications across v1.2.0 doc-set | 12 of 15 LANDED | **14 of 15 LANDED** (6 P-1 + 8 P-2; remaining 1 P-3 cross-doc reuse at S12c) |
| Phase 4 cycle progress | 12 of 13 sessions | **(no full-session count change; sub-session)** |

## Banked observations from S12b-2

**B-Phase4-S12b-2-1 — P-2 v1.2.0 issuance close achieved
in single sub-session.** S12b-2 was projected at ~78 LOC;
landed at +100 LOC under §13.1 default with 100 LOC
headroom. The full P-2 §D registry expansion + audit-side
declaration table + B-Phase4-S7-4 codification + version
bump + change log entry all fit within a single sub-session
without spill — contrasts with S12b-1's +223 LOC overrun
that required Decision 22 cascading split. Bank as
institutional precedent: when a sub-session's scope is
content-density-bounded (e.g., factual table updates +
single new codification + change log) rather than
codification-density-bounded (multiple new doctrinal
sections), the trigger projection accuracy is higher.

**B-Phase4-S12b-2-2 — Two doc v1.2.0 issuances complete.**
P-1 (S12a) + P-2 (S12b-2) both at v1.2.0 ISSUED. P-3 (S12c)
remains. C-1 already at v2.0.0 (Phase 4 S10 major bump).
v1.2.0 doc-set issuance event will conclude at S12c
landing P-3 v1.2.0; S13 then handles P-4 v1.2.0 + Phase 4
cycle close.

## Next sub-session

**S12c — P-3 v1.2.0 issuance (~113 LOC).**

Per Phase 1 enumeration:
- P3-T1: NEW §3.4.x Phase 4 S5 BVAR DD finding (~25 LOC)
- P3-T2: §3.4.x sibling — Phase 4 S6 stochvol partial A.2 finding (~20 LOC)
- P3-T3: §6.6 stale framing update (~5 LOC)
- P3-T4: §7 carry-forward closure (~15 LOC)
- P3-T5: NEW §6.10 Phase 4 cycle close consolidation (~20 LOC)
- P3-T6: §8 numbering fix per Disposition 1 (~3 LOC)
- B-Phase4-S6-1: §3.4.x auto-DD pattern (cross-doc reuse with P-2 §C.2.x; empirical-findings-side framing) (~10 LOC)
- §10.1 v1.2.0 change-log entry (~15 LOC)
- P-3 header version bump (~3 LOC)

Trigger: ready to fire after S12b-2 CI confirms green.
S12c closes P-3 v1.2.0 issuance + completes the v1.2.0
doc-set issuance event for P-1/P-2/P-3.
