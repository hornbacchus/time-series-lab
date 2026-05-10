# Phase 6+ S6 — sub-domain (iv) audit-driven scope determination; Outcome C deferred-activation codification (zero substantive engine-touch concerns; reserve concept validated)

**Date:** 2026-05-10
**Master HEAD:** `024440f` (Phase 6+ S5 §19.4 living baseline activation)
**Class:** banking-class single commit per CONSTRAINT 2 + §19.4 A3
banking class (80-180/210 thresholds). Codifies first audit-driven
sub-domain (iv) activation outcome per master plan §15 reserve-
for-emergent-work design.

## B-Phase6-S6-SUBDOMAIN-IV-DEFERRED-ACTIVATION — sub-domain (iv) first audit-driven activation; Outcome C deferred-activation; reserve concept validated; three activation criteria codified for future surfacing

### §1 Pre-flight scope determination outcome (Steps 1-4)

Per audit-driven Code-side scope determination protocol Steps 1-4
at master HEAD `024440f`:

**7-item audit classification table:**

| # | Item | Class | Status |
|---|---|---|---|
| A | MCMC ess BLOCK (2b/2c) | Originally engine-modification; CLOSED at harness layer S1+S1-FU via parameter-aware exclusion mechanism | CLOSED |
| B | BYF Path 2 (engine config bump n_draws to 5000-10000) | Engine-touch (chain length retuning) | DEFERRED per S6 keep-dormant ratification |
| B' | BYF Path 3 (parameter-aware exclusion mechanism extension to BVAR-SV) | Mechanism + master plan amendment (NOT engine-touch) | DEFERRED per S6 keep-dormant ratification |
| C | Parity-side None-handling (S3 Interpretation C) | Doc-class audit | NOT OUTSTANDING (audit-clean per re-verification at this audit) |
| D | `framework_reference.md` §2.4 forward-reference | Doc-class cleanup | DEFERRED to S13/cleanup sub-session per master plan §15 doc-side fold framing |
| E | Parity-slow workflow provisioning fragility | CI infrastructure (workflow YAML class) | Banked B-Phase5-POST-CLOSE; out-of-scope |
| F | Substance tests A3 candidate | Doc-class threshold | §19.4 future amendment candidate |
| G | A1 + A2 amendments | Cycle-architecture amendment | §19.4 deferred to v1.4+ master plan amendment scope |

**Audit verification protocol applied (§19.4 A2 operational
evidence):** Re-verification of S3 Interpretation C parity-side
checks (`tools/reference_parity/harness/checks/*.py`) confirmed
ZERO analogous bugs to S3 structural_invariants.py fix pattern;
parity-side checks use guards/defaults (not bare `np.asarray(
tsl.get(field), dtype=np.float64)` pattern). Re-verification of
engine-side TODO/FIXME markers at `engine/techniques/stochastic_volatility.py`
confirmed ZERO outstanding deferred markers. A2 verify-state-at-
activation protocol applied during this audit; banking-class A2-
evidence accumulation candidate (informational; not separate
observation track).

### §2 Zero-substantive-concerns finding

**Engine-touch class items currently outstanding for (iv) scope:
ZERO.**

Item B (BYF Path 2) is engine-touch class but explicitly DEFERRED
per S6 keep-dormant ratification. Activating B at this sub-session
would REVERSE S6 disposition; not appropriate without explicit
Chat trigger to revisit S6.

All other 7-item-table items either CLOSED (A, C audit-clean),
deferred to alternative loci (D doc cleanup, E CI infrastructure,
F+G §19.4 future amendment), or non-engine-touch class
(B' mechanism + master plan amendment).

### §3 Deferred-activation rationale + reserve-validation framing

Sub-domain (iv) genuinely awaiting surfacing event per master
plan §15 reserve-for-emergent-work design:

> "Sub-domain (iv) — Surface-during-integration concerns
> (engine-touch reserved). S10-S12 — Reserve allocation for
> surface-during-integration scope. Specific session content
> determined as integration progresses; engine-touch class per
> Domain 5 disposition."

> "If integration surfaces purely doc-side learnings, those
> fold into S13 issuance scope rather than consuming sub-domain
> (iv) reserve."

**Reserve concept validates as designed at first audit-driven
activation.** This is a CLEAN OUTCOME — pre-flight protocol earns
its keep at first activation regardless of outcome. Master plan
§15 (iv) "reserve for emergent work" worked correctly: no
surfacing event yet → no activation → reserve preserved for
genuine emergent need.

Pre-flight protocol earned its keep beyond outcome determination:
- Re-verified S3 Interpretation C audit-clean (vs assuming
  prior banking finding remains current)
- Re-verified engine-side state has no deferred TODO/FIXME
  markers (vs assuming prior engine-touch closure complete)
- Classified 7 candidate items across banking sources with
  explicit Domain 5 engine-touch criteria
- Validates §19.4 A2 verify-state-at-activation protocol in
  operational practice (S6 second observation already shipped;
  this is third operational application)

### §4 Three activation criteria for future (iv) activation

Per Chat ratification refinement, three criteria for future
sub-domain (iv) activation:

**Criterion 1 — Surfacing event from sub-domain (i)/(ii)/(iii)
integration.** Future Phase 6+ work that surfaces engine-touch
class concern during sub-domain (i) wrapper integration,
sub-domain (ii) smoke-test infrastructure work, or sub-domain
(iii) None-handling extension scope constitutes (iv) activation
trigger.

**Criterion 2 — Explicit Chat trigger to revisit Item B (S6
keep-dormant reversal disposition).** BYF Path 2 (engine config
bump n_draws) is engine-touch class but currently deferred per
S6 keep-dormant ratification. Future Chat trigger explicitly
reversing S6 keep-dormant disposition (e.g., BYF allowlisting
becomes priority; engine-touch path chosen over harness-layer
mechanism extension) constitutes (iv) activation trigger.
Reactivation requires explicit Chat redisposition; not implicit
via (iv) audit.

**Criterion 3 — Per-wrapper field-availability protocol Cases
(ii)/(iv) first empirical observation OR new wrapper integration
revealing engine-touch concern.** Per master plan §15 sub-domain
(i) extension framing, per-wrapper field-availability protocol
Cases (ii)/(iv) are reserved for future empirical observation
per Phase 5 banking. If either Cases (ii) or (iv) surfaces
during future wrapper integration work (sub-domain (i) extension
scope or new wrapper additions beyond 8-wrapper allowlist), that
constitutes engine-touch class trigger for sub-domain (iv)
activation.

### §5 Sub-domain (iv) status

**Status: AWAITING per master plan §15 reserve framing.**

Sub-domain (iv) preserved as reserve allocation for surface-
during-integration scope; no active session content; no
deferred-activation register at this banking entry (none of the
3 criteria currently satisfied). Future activation per any of
the 3 criteria above triggers next (iv) sub-session per Code+Chat
trigger drafting.

**Phase 5 bridge handoff disposition (1) status update:**
- Sub-domain (iii): CLOSED at S3 (S8 None-handling fix)
- Sub-domain (ii): CLOSED at S6 (BYF keep-dormant; scope-
  contracted-S7-close)
- Sub-domain (iv): AWAITING per first audit-driven activation;
  reserve concept validated; activation criteria codified

**Disposition (1) substantially closed across (ii) + (iii);
(iv) remains as designed reserve.**

### §6 Cross-references (compressed)

- Master plan §15 sub-domain (iv) framing at
  `plans/reference_parity_phase5_master_plan.md` lines 561-572
- B-Phase6-KICKOFF-ARC-CLOSE at `kickoff_arc_close_banking.md`
  (post-arc-close framing; (iv) deferred-status reference)
- §19.4 living calibration baseline at `calibration_baseline.md`
  (A2 verify-state-at-activation protocol operational evidence
  + A3 banking class threshold compliance)
- S6 design BYF disposition at
  `s4_smoke_test_infrastructure_design.md` §2 4-paths table
  (Item B + B' context)
- S3 banking at `s3_banking.md` (Interpretation C re-verification
  source)
- Per-wrapper field-availability protocol framing at master plan
  §15 sub-domain (i) extension (Cases (ii)/(iv) reserved future
  empirical observation per Phase 5 banking)

## Disposition

Sub-domain (iv) audit-driven first activation COMPLETE at this
commit. Outcome C deferred-activation codified per Chat
ratification + 3-criterion refinement. Reserve concept validated
at first activation. Phase 5 bridge handoff disposition (1)
substantially closed across (ii) + (iii); (iv) AWAITING per
designed reserve framing. §19.4 A2 verify-state-at-activation
protocol applied operationally during audit (third operational
application; banking-class A2-evidence accumulation
informational).
