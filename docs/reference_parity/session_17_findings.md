# Phase 3 Session 17 — Documentation phase: P-3 empirical findings synthesis

**Date:** 2026-04-29
**Master plan reference:** §15.13 + Appendix C
**Deliverable:** `docs/engineering/parity_empirical_findings.md` v1.0.0
**Scope:** Single-session — completed in 1 session as planned.

## Summary

Phase 3 documentation phase Session 17 issues the **P-3
empirical findings** as the third and final documentation
deliverable. P-3 is descriptive narrative — the story of
Phase 3 told through cumulative cross-batch patterns.
Distinct from P-1 (directive) and P-2 (reference / playbook).

This session **closes the Phase 3 documentation phase**.
Session 18 proceeds to closeout (CI workflow finalization
+ P-4 status tracker finalization + Phase 3 closeout
commit).

## Document structure (9 sections)

| § | Topic |
|---|---|
| 1 | The numbers — Phase 3 totals (70/70 covered, 65 PASS / 5 CAVEAT / 0 BLOCK / 1 SKIP; 17 sessions vs 18-22 budget) |
| 2 | What made Phase 3 work — Pattern A.1 unlock, harness abstraction held, CI green discipline locked early |
| 3 | Empirical patterns the harness exposed — Pattern J durable knowledge; Pattern F wrapper-class infrastructure; DSCD as real phenomenon |
| 4 | Surprises and reversals — DL non-determinism budget wrong by 30pp; p3_var headroom 8.1 orders; alignment-via-metric cleaner than tolerance widening; self-parity more powerful than originally framed; Item 13 budget revision empirically locked |
| 5 | The CAVEAT taxonomy in practice — 5 CAVEATs span 4 distinct regimes; no CAVEAT was a tolerance-tuning failure |
| 6 | Phase 3.5 candidates banked — single_impl_mle band tightening, per-metric em_stochastic bands, X-13 binary on Linux CI, manifest re-pin cadence, DOCUMENTED-DIVERGENCE first-instance |
| 7 | What Phase 3 tells us about audit-engineering — reference selection is hardest decision; harness scaffolding pays for itself; documentation-as-you-go beats documentation-at-end |
| 8 | The TSL parity discipline going forward — pre-merge checklist for new wrapper authors; Phase 3.5+ planner heuristics |
| 9 | Document maintenance + change log |

## Banked items closed at P-3 venue (4 of remaining items)

| Item | Status | P-3 venue |
|---|---|---|
| #6 Cross-batch findings doc design refinements | **CLOSED** | §6.3 banked for Phase 3.5 P-3 v1.1 structural pass |
| #7 Broader cross-batch findings synthesis | **CLOSED** | Synthesized across §2-7 of P-3 narrative |
| #9 p3_var / p3_vecm / p3_pca tightening candidates | **CLOSED** | §4.2 details the 13-orders-of-magnitude headroom; §6.1 banks `single_impl_mle` Phase 3.5 candidate |
| #10 EM-stochastic per-metric band tightening | **CLOSED** | §6.2 details the per-metric divergence (HMM means 1e-5 vs transmat 0.05-0.25); banks Phase 3.5 candidate |

## All 13 evidence-complete banked items now closed

Cumulative banked items disposition across all 3 documentation
sessions:

| Item | Closed at | Venue |
|---|---|---|
| #1 Pattern I formalization (sign/scale) | S16 | P-2 §E |
| #2 verdict_class enum split candidates | S15 | P-1 §5.1 (candidate documented) |
| #3 Per-metric em_stochastic bands | S15 | P-1 §5.1 (HMM transmat example) |
| #4 DSCD diagnostic-axis registry | S16 | P-2 §F |
| #6 Cross-batch findings doc design | S17 | P-3 §6.3 |
| #7 Broader cross-batch synthesis | S17 | P-3 §2-7 |
| #8 Infrastructure-fix discipline (Triggers 8/9) | S15 | P-1 §11 |
| #9 p3_var / p3_vecm / p3_pca tightening | S17 | P-3 §4.2 + §6.1 |
| #10 EM-stochastic band tightening | S17 | P-3 §6.2 |
| #11 Pattern J alignment-via-metric (J.C) | S16 | P-2 §G |
| #14 §10.3 criterion 2 wording | S15 | P-1 §5.2 |
| #18 Pattern F wavelet-mode interaction | S16 | P-2 §D.2 |
| #20 Pattern A.1 vs A.2 sub-pattern | S16 | P-2 §C |

**13 of 13 banked items closed at documentation venues.**
The remaining banked items (#5, #13, #15, #16, #17) were
RESOLVED during batch execution at S12-S13:

- #5 (Item 12 verdict-runtime alignment) — resolved S13
- #13 (Item 13 budget revision) — locked S13 at 17 sessions
- #15 (Pattern J catalog launch) — launched S12
- #16 (§10.3 criterion 2 split lock) — applied S12
- #17 (PyBridge isolate=False shim retire) — executed S13

## Empirical evidence summary covered in P-3

The narrative covers all major Phase 3 quantitative findings:

- 70/70 wrappers covered (100%)
- 0 BLOCK; 65 PASS (93%); 5 CAVEAT (7%); 1 SKIP-graceful
- Pattern A → 46 wrappers (66%) with sub-pattern breakdown
- Pattern A.1 → 18 wrappers locked at scale
- Pattern F → 14 concrete invariants
- Pattern J → 11 catalog entries, 6 sub-sections, 3 resolution sub-patterns
- Pattern I → 6 instances of sign/scale canonicalization
- DSCD → 4 instances across 3 sub-classes
- 5 sessions saved vs original 18-22 budget (Item 13 lock)
- 13 batch-execution sessions + 3 documentation + 1 closeout = 17 total

## Cross-document consistency verified

- P-3 §1 numbers match P-2 §A, §C, §F totals + P-4 (status
  tracker) aggregate progress section
- P-3 §6.1-6.5 banked Phase 3.5 candidates align with P-1
  §5.1 banked split candidate + P-2 §A.10/A.11
- P-3 §7 meta-lessons reference P-1 §10 empirical additions

## Verification

- File created: `docs/engineering/parity_empirical_findings.md`
  (P-3 v1.0.0; 9 sections; ~530 lines).
- All quantitative claims cross-checked against batch
  summaries + cross-batch findings doc + P-2 totals.
- No engine code changes (docs-only commit).
- No CI workflow changes.

## Phase 3 documentation phase complete

P-1 (S15), P-2 (S16), P-3 (S17) all issued at v1.0.0 with
mutually consistent cross-references. The three documents
form the complete Phase 3 documentation set:

| Document | Type | Audience |
|---|---|---|
| P-1 parity standard | Directive ("must") | New wrapper authors; PR reviewers |
| P-2 diagnostic reference | Descriptive reference / playbook | Engineers matching new wrappers against established patterns |
| P-3 empirical findings | Descriptive narrative | TSL maintainers; Phase 3.5+ planners; future engineers onboarding to TSL parity discipline |
| P-4 status tracker | Authoritative coverage data | Anyone needing per-wrapper status |

P-4 (`docs/reference_parity_status.md`) finalization
happens at Session 18 closeout.

## Next session

Session 18 — Phase 3 closeout. Single-session target.
Scope:

1. **CI workflow finalization** — verify
   `parity-fast.yml` and `parity-slow.yml` are in their
   final form (CAVEAT exit-code policy in place; install
   matrix complete; documentation-comments cleaned up).
2. **P-4 status tracker finalization** — final pass on
   `docs/reference_parity_status.md` to lock the Phase 3
   close state (cumulative tally, sessions used, pace,
   pattern catalog totals; remove "PENDING" placeholders).
3. **Phase 3 closeout commit** — single commit summarizing
   the Phase 3 close.
4. **CI green verification** on the closeout commit.
5. **Optional:** mark relevant `plans/reference_parity_phase3_master_plan.md`
   sections as "Phase 3 closed" (out-of-scope for closeout
   if it requires retro-edits to plan content).
