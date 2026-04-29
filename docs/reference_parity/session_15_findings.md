# Phase 3 Session 15 — Documentation phase entry: P-1 parity standard

**Date:** 2026-04-29
**Master plan reference:** §15.13 + Appendix C
**Deliverable:** `docs/engineering/parity_standard.md` v1.0.0
**Scope:** Single-session — completed in 1 session as planned.

## Summary

Phase 3 documentation phase Session 15 issues the **P-1
parity standard** as a binding directive for any new
wrapper PR that surfaces numerical output. Distilled from
Phase 3 batch-execution evidence (Sessions S2-S14, 70/70
wrappers, 0 BLOCK).

## Document structure (11 sections)

1. **Purpose and scope** — applies to parity checks under
   `tools/reference_parity/harness/checks/`; B/A tier split
   matching `wrapper_development_standard.md`.
2. **Four-verdict closure rule** — PASS / CAVEAT /
   DOCUMENTED-DIVERGENCE / NO-REFERENCE per master plan
   §3.1. Empirical note: DOCUMENTED-DIVERGENCE not
   encountered as distinct outcome in Phase 3; CAVEAT
   absorbed all methodology-equivalent divergences. SKIP-
   graceful runtime convention formalized for Tier C
   binary-dependency cases (p3_x13 precedent S14).
3. **Output-surface discipline** — Primary / Secondary /
   Diagnostic three-tier per master plan §4. Tier
   propagation rules.
4. **Reference availability tier policy** — Tier A
   canonical / Tier B paper-formula reimplementation /
   Tier C NO-REFERENCE. **Self-parity audit pattern
   formalized** as a Tier B sub-pattern with empirical
   validation (5+ wrappers).
5. **Tolerance bands per class** — 11-class verdict_class
   taxonomy locked at Session 14. §10.3 criterion 2
   three-sub-criteria split (2a/2b/2c) locked at Session
   12; empirically validated across 5 consecutive batches.
6. **CI tier classification** — fast/slow/skip-CI per
   master plan §12. Exit-code policy (CAVEAT exit 2 → CI
   green) formalized.
7. **Reference-version pinning protocol** — MANIFEST.toml
   authoritative; new dep pins ship in audit-creation
   commits per locked discipline (Sessions 4-6 hardening).
   Quarterly re-pin cadence noted as banked for Phase 3.5.
8. **Pre-merge checklist (binding)** — required artifacts
   (parity check class + verdict_class + tolerance ladder
   + structural_invariants if applicable), required docs
   (per-wrapper audit report + status tracker entry +
   batch summary), required CI state (CAVEAT permitted;
   BLOCK NOT permitted), required cross-references
   (Pattern J catalog + wrapper development standard).
9. **Cross-reference to wrapper development standard
   (C-1)** — engine-side and parity-side standards are
   orthogonal + additive.
10. **Empirical additions Phase 3 surfaced** —
    - Pattern A.1 (same-library) as new-wrapper default
      with 18 wrappers empirical foundation
    - Self-parity pattern with 5+ wrappers empirical
      foundation
    - PyBridge subprocess-isolation only post-S13 retire
    - CAVEAT exit-code policy
11. **Trigger candidates** — Trigger 8 (CI failure on
    previously-passing local check) and Trigger 9 (CI
    failing across multiple consecutive sessions); both
    formalized this session, with Sessions 4-6 retro
    cited as empirical foundation.

Plus document-maintenance section + change log.

## Items addressed from check-in 2 disposition

Per session prompt carry-forward:

- **Item 6** (Cross-batch findings doc design refinements)
  — out-of-scope for P-1; defer to P-3 (Session 17).
- **Item 17** (PyBridge isolate=False shim retire — RESOLVED
  at S13) — referenced in §10.3.
- **Item 19** (resolved S13) — referenced in §10.4 (CAVEAT
  exit-code policy).
- **Pattern A.1 vs A.2 split** — A.1 formalized in §10.1
  with empirical foundation. A.2 (cross-package bit-exact)
  is implicit in §4.1 Tier A; explicit naming deferred to
  P-2.

## Documentation venue assignments confirmed

Of the 13 evidence-complete banked items, P-1 covers:

- **Item #14** — §10.3 criterion 2 wording revision
  (locked sub-criteria 2a/2b/2c at §5.2)
- **Item #2** — verdict_class enum split candidates
  (mle_fit vs single_impl_mle vs optimizer_divergent_mle;
  documented at §5.1 as a candidate refinement, not yet
  locked)
- **Item #3** — per-metric bands within em_stochastic
  (referenced at §5.1 with the HMM transmat 0.3 / 1.0
  widening as concrete example)
- **Item #8** — infrastructure-fix discipline track
  (Trigger 8/9 §11)
- **Item #10** — EM-stochastic per-metric band tightening
  (§5.1 covers the canonical bands; tightening discussion
  defers to P-3 empirical findings)

P-1 closes 5 of the 13 evidence-complete items at the
documentation level. Remaining 8 items distribute across
P-2 (Session 16) and P-3 (Session 17) per the locked
schedule.

## Verification

- File created: `docs/engineering/parity_standard.md`
  (1006 lines, 11 sections, change log v1.0.0).
- Cross-reference to
  `docs/engineering/wrapper_development_standard.md`
  established at §9.
- No engine code changes (docs-only commit).
- No CI workflow changes.
- Status tracker updated to mark Session 15 complete.

## Next session

Session 16 — P-2 diagnostic reference. Already partially
populated at `docs/engineering/parity_diagnostic_reference.md`
(Pattern J catalog Appendices B.1-B.6 across 11 entries;
Pattern F invariants registry documentation in Section D).
Session 16 will:

1. Add Section A — tolerance class taxonomy (deferred from
   S14 placeholder).
2. Expand Section C — Pattern A taxonomy formalization
   (A.1 same-library, A.2 cross-package bit-exact, A.3
   self-parity; locked at 27+18+10 wrappers respectively).
3. Add structural-invariants playbook for new wrapper
   classes (extend the 14 concrete invariants with usage
   patterns).
4. Resolve banked items #1, #4, #11, #18, #20.

## Items banked

- Trigger 8/9 formalization could escalate to master plan
  §11 update at Phase 3.5; for now documented in P-1
  §11.
- Quarterly re-pin cadence note (P-1 §7.3) banked for
  Phase 3.5 maintenance.
