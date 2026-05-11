# Phase 7+ disposition 2 — operational disciplines: validation provenance audit checklist + layered smooth-ratification countermeasures + methodology disclosure templates + verify-state-at-narration operational spec

**Date:** 2026-05-10
**Master HEAD at authoring:** `be5e40a`
**Class:** novel-substantive banking-class artifact establishing
Phase 7+ operational disciplines for Q1+Q2+Q3a+Q3b work program
execution.
**Banking locus:** second entry at `docs/reference_parity_phase7/`;
follows `scope_reframing_s6_banking.md` (S6 + S9 amendments).

## §1 Validation provenance audit checklist

Per Chat handoff §6 + S6 §5 operational discipline carry-forward:
codified four-question checklist applied per technique close at
Q1+Q2+Q3a+Q3b sub-sessions. Codification rather than informal
application produces auditable trail for Path α end-of-work-program
expert review and creates structural friction against smooth
ratification.

### §1.1 The four checklist questions

For each technique closing under Phase 7+ work program:

**Q-A: Was upstream decision substance produced through extracted/
cited evidence or through inferred reasoning?**

- Extracted/cited evidence: reference selection from MANIFEST.toml +
  audit reports; tolerance bands from `tolerances.py` ladder;
  fixture characteristics from existing audit fixture data;
  Pattern classification from audit reports
- Inferred reasoning: web-search-informed proposals not directly
  citable to source artifact; analogy from one technique to another
  without explicit precedent; tolerance band rationale from
  general-purpose principles vs technique-specific evidence

If decision substance is predominantly inferred reasoning rather
than extracted/cited evidence, the technique closing should be
flagged as "validation-pre-expert-review with elevated upstream-
decision risk"; methodology disclosure template adds explicit
language acknowledging this elevation.

**Q-B: Did the user genuinely consider contesting reference
selection / tolerance specification / fixture characteristics, or
did the user default to ratifying?**

- Genuine contestation: user surfaced specific operational concern;
  user requested alternative reference candidate consideration;
  user pushed back on tolerance band rationale; user added
  fixture characteristic
- Default ratification: user accepted Chat's proposed upstream
  decisions without specific operational engagement

Per smooth-ratification failure mode (codified at §2 below): user's
explicit statement that they cannot evaluate quantitative
correctness independently means many ratifications are pro-forma.
Q-B is calibrated to detect when ratification crossed from pro-forma
to substantive.

If ratification was pro-forma across all upstream decisions for a
technique, the technique closing should be flagged as "validation-
pre-expert-review with smooth-ratification exposure"; methodology
disclosure template adds language acknowledging this exposure.

**Q-C: For this technique specifically: am I (Chat) confident enough
in validation that the user could publish from it tomorrow with
disclosure as drafted?**

This is the gut-check question. Confidence is not "the audit
verdict was PASS" — that's a prerequisite, not a confidence
statement. Confidence is "given everything I know about this
technique's validation evidence, this technique's idiosyncrasies,
this technique's parameter dimensions, the tolerance band justification,
the user's published-research use cases, I am confident the user
publishing from this technique tomorrow under the drafted disclosure
would be defensible to (a) the user's published audience, (b)
Morgan Stanley compliance review if applicable, and (c) the
external expert reviewer at Path α close."

If confidence is below "yes, defensible to all three audiences,"
the technique closing should fall to one of:
- Blended validation status (parity + structural invariants +
  narrative review) instead of parity-validated stamp
- Expert-review-required-pre-publication status (publication paused
  for this technique until Path α close)
- Q3a/Q3b extension required before publication-ready status

**Q-D: If expert review later found this validation inadequate, what
would published-output retraction look like?**

The retrospective stress test. Imagine Path α expert review surfaces
a substantive upstream-decision error on this technique (wrong
reference selected; tolerance band too generous; fixture
characteristics insufficient for parameter-sensitivity claim;
something missed). What's the retraction surface?

- Single research note with single retraction: low retraction surface
- Multiple research notes referencing the technique: medium
  retraction surface
- Strategic recommendation that drove client positioning:
  high retraction surface
- Public commentary (Bloomberg TV, CNBC) referencing the technique:
  highest retraction surface

The retraction-surface estimate informs whether the technique should
proceed to publication during work program window or whether
publication should be paused until Path α close. **Higher retraction
surface = higher bar for Q-C confidence + more conservative
publication pacing during work program window.**

### §1.2 Application protocol

The four questions are asked by Chat at technique close. Honest
answers documented at per-technique banking entry. User reviews
checklist application; user can contest Chat's self-assessment if
they have operational reason to disagree.

The checklist is applied **before** technique enters validated-pre-
expert-review status. If any question surfaces concern that
warrants pause, the technique does not enter validated-pre-expert-
review status; instead enters appropriate fallback status (blended
validation; expert-review-required-pre-publication; Q3a/Q3b
extension required).

### §1.3 Fall-to-blended-validation triggers

The following checklist outcomes trigger automatic fall-to-blended-
validation status (technique does NOT enter parity-validated status;
instead validated via combination of parity + structural invariants
+ narrative methodology review):

- Q-A: predominantly inferred reasoning AND
- Q-C: confidence below "yes, defensible to all three audiences" OR
- Q-D: high or highest retraction surface

The combination signals that single-fixture parity validation
alone insufficient grounds for publication-ready status; multiple
validation evidence streams required.

## §2 Layered smooth-ratification countermeasures

Per S9 handoff §6 + S6 §5 operational discipline carry-forward.
Graduated friction architecture applied per upstream decision based
on decision stakes. Three tiers; not single discipline applied
uniformly.

### §2.1 Tier 1 — "Wrong if X" one-line acknowledgment

**Applies to: ALL upstream decisions.**

Per upstream decision, Chat surfaces "this decision would be wrong
if [condition X]" as one-line acknowledgment alongside the proposal.

For low-stakes decisions, X is often "if [edge case condition], which
the available evidence suggests is unlikely." For high-stakes
decisions, X requires substantive content articulating the failure
mode the decision is exposed to.

Example (low-stakes):
> "Reference: R `urca::ur.df` (urca 1.3.4). Wrong if `urca` package
> has bug in tau statistic computation, which is unlikely given
> 20+ year package maturity and widespread use."

Example (high-stakes):
> "Tolerance band: 1e-2 abs / 1e-2 rel. Wrong if MLE fit
> hyperparameter sensitivity produces parameter estimate divergence
> at this tolerance for fixture-similar configurations the user
> publishes from; tolerance band stress-test against 3 alternative
> seeds at Q3b activation would surface this; not yet performed."

Tier 1 surfaces explicit failure-mode awareness in every upstream
decision; user can accept the failure mode framing or push back
on whether X is correctly characterized.

### §2.2 Tier 2 — Devil's-advocate case-against

**Applies to: decisions with multiple candidates OR decisions where
Chat's confidence is below high.**

Per such decision, Chat proposes a primary recommendation AND a
case-against the recommendation. User ratifies after acknowledging
the case-against was considered.

Threshold for application: any decision where Chat's web search
surfaces multiple candidates (e.g., R reference candidates: `urca`,
`tseries`, `aTSA`); any decision where Chat's confidence assessment
is "moderate" or below.

Example:
> "Recommendation: R `urca::ur.df` for ADF reference. Case-against:
> `tseries::adf.test` is more commonly cited in econometrics
> literature; `urca` selected because (a) supports trend
> specification matching TSL implementation; (b) returns
> regression diagnostics TSL surface uses for downstream invariants;
> (c) `tseries::adf.test` p-value interpolation differs from
> MacKinnon table TSL uses. The case-against is not zero — `tseries`
> is operationally familiar to economists; `urca` is statistically
> equivalent but less canonical in applied work."

Tier 2 surfaces the alternative-not-chosen and the reasons for
rejection; user can accept or push back on the rejection rationale.

### §2.3 Tier 3 — Second-opinion architecture

**Applies to: first-of-class decisions / conflicting-evidence
decisions / multi-downstream decisions / ALL Q3b decisions.**

Per such decision, Chat drafts upstream decision; Chat then
explicitly critiques its own decision; user sees both proposal +
critique simultaneously.

The "second opinion" is Chat playing the role of a more skeptical
reviewer of its own work. The output structure:

```
PROPOSAL: [decision substance]
CRITIQUE OF PROPOSAL: [3-5 substantive concerns Chat would raise
                       if reviewing this proposal as second opinion]
RESOLUTION: [how proposal stands or revises in light of critique]
```

The user reviews proposal + critique + resolution. Disposition
options:
- Accept proposal as-stated (critique noted but rejected)
- Accept resolution (proposal revised per critique)
- Reject proposal (case-against in critique sufficiently strong;
  rework needed)
- Hybrid (specific elements of critique addressed; specific
  elements of proposal retained)

Tier 3 is heaviest discipline; reserved for highest-stakes
decisions. Per S6 §5 + Chat ratification 4 at S6: **Tier 3 is
MANDATORY for all Q3b parameter-sensitivity decisions.** Q3b
decisions are highest-stakes upstream decisions in the work program
because they determine validation evidence breadth across parameter
space; failure-mode exposure is highest there.

### §2.4 Streamlining-vs-apparatus tension explicit

Per Phase 7+ S2-S3 user disposition (Path 3 streamlined start):
user has explicit authority to override apparatus discipline at
specific decisions or specific sub-sessions.

When user explicitly elects streamlining over codified friction,
Chat:

1. **Documents the override** in the per-technique banking entry
   with explicit user disposition reference (e.g., "User elected
   Path 3 streamlining at S2; bypass of Disposition 3 + 5 logged")
2. **Does not re-litigate** the streamlining election in subsequent
   sub-sessions
3. **Continues forward instrumentation** for downstream consequences
   of the streamlining (e.g., if streamlining bypassed Tier review,
   Chat surfaces at next consumption step that Tier judgment was
   user-bypassed, not user-verified)

The codification matters because it distinguishes "user overrode
friction consciously" from "friction eroded passively." Those are
different failure modes and need different countermeasures. Conscious
override is user authority operating; passive erosion is the smooth-
ratification failure mode the apparatus exists to catch.

Forward instrumentation for streamlining-vs-apparatus tension:
- Track per-technique whether streamlining was elected at any
  upstream decision
- At Q1 close per thread (Q1 close, Q2 close, Q3a close, Q3b close)
  surface aggregate streamlining election count
- At Path α expert review preparation, surface streamlining election
  history per technique for expert reviewer awareness

## §3 Methodology disclosure templates

Per S6 §3 publication policy + S9 §2 ratified tier taxonomy + S6 §4
Path α expert review timing. Templates per validation tier × per
disclosure pattern. Disclosure language calibrated against actual
tier taxonomy with explicit acknowledgment of validation evidence
type and pre-expert-review status.

### §3.1 Disclosure pattern catalog

Four disclosure patterns per S6 §3 framing:

**Pattern (i) — Research note footnote.** Brief 1-2 sentence
disclosure embedded as footnote on first reference to the
technique in a research note.

**Pattern (ii) — Technical appendix.** Paragraph-length disclosure
in technical appendix or methodology section of research note;
applies when technique is methodologically central or when
appendix exists.

**Pattern (iii) — Risk model documentation.** Precise compliance-
oriented disclosure for risk model documentation contexts (Morgan
Stanley internal risk model registers; client-facing risk
attribution).

**Pattern (iv) — Internal use disclosure.** Disclosure for
internal-only use cases (internal trading desk reference;
internal research that does not get published externally).

### §3.2 Tier × pattern matrix

#### Tier I — Structural-invariants dispatch validated (9 catalog techniques: 8-wrapper allowlist + BYF dormant)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], structural-
> invariants validated per TSL Phase 5+ infrastructure. Pre-Path
> α expert review status; full validation evidence per Phase 5+
> technique inventory.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] is structural-
> invariants validated per Phase 5+ wrapper integration
> (8-wrapper allowlist + BYF). Validation evidence includes
> [list specific structural invariants verified for this
> technique, e.g., for kalman_filter: state-space-recursion
> identity, covariance-matrix-symmetry-preservation,
> innovation-orthogonality]. Pre-Path α expert review status;
> reference selection AI-assisted with user ratification.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier I (structural-invariants
> dispatch validated) per `tools/reference_parity/harness/runner.py`
> `_INVARIANTS_DISPATCH_ALLOWLIST` (lines 109-118). Phase 5+ integration
> validated [date of Phase 5+ commit]. Pre-Path α expert review status.
> External expert review pending [date]; methodology disclosure
> updates retroactively if expert review surfaces upstream errors.

**Pattern (iv) Internal use disclosure:**
> [technique_id] is structural-invariants validated. Pre-Path α
> expert review.

#### Tier I.partial — Phase 1/2 sub-component validated; remainder uncovered

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id]; [validated
> sub-component] validated per Phase 1/2 infrastructure;
> [unvalidated sub-component] pending Q2 work program. Pre-Path
> α expert review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validation is
> partial. **Validated sub-component:** [specific component;
> e.g., for bvar: IRF/FEVD-given-coefs] per Phase 1/2 audit
> [audit_id]; bit-exact against [reference; e.g., R `vars`].
> **Unvalidated sub-component:** [specific component; e.g., for
> bvar: Bayesian estimation step priors → posterior coefs];
> Q2 work program scope. Published research using [technique_id]
> may rely on validated sub-component output OR may rely on full
> pipeline including unvalidated sub-component; specify which
> per analysis. Pre-Path α expert review status.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier I.partial. Validated:
> [validated sub-component] per `tools/reference_parity/harness/checks/
> [wrapper].py` audit [audit_id]; bit-exact verdict [date].
> Unvalidated: [unvalidated sub-component]; Q2 scope;
> validation pending. Risk attribution from this analysis
> conditional on unvalidated sub-component being correctly
> implemented; if not, attribution requires retroactive
> revision. Pre-Path α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] partial validation; [validated sub-component]
> validated; [unvalidated sub-component] pending.

#### Tier II.bit-exact — Phase 3 cross-package bit-exact parity validated (12 wrappers / 14 catalog techniques)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], cross-package
> bit-exact parity validated against [reference package + version]
> per Phase 3 audit dated [date]. Pre-Path α expert review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validated per Phase 3
> reference parity infrastructure. **Reference:** [package + version;
> e.g., R `urca::ur.df` (urca 1.3.4)]. **Verdict:** PASS Pattern A.2
> bit-exact at machine precision; abs diff [specific value or
> "see audit"]. **Audit date:** [date]. **Fixture:** seeded single-
> fixture configuration; parameter-sensitivity coverage NOT
> established at this validation tier; Q3b extension pending.
> Reference selection + tolerance specification AI-assisted with
> user ratification. Pre-Path α expert review status; expert review
> pending [target date].

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier II.bit-exact. Reference:
> [reference package + version]. Audit: `tools/reference_parity/
> reports/p3_[wrapper]_audit.md` dated [date]. Verdict: PASS
> Pattern A.2 bit-exact at machine precision. Fixture:
> single-seeded; parameter-sensitivity coverage NOT established;
> Q3b extension scope. Risk attribution conditional on parameter
> configurations matching fixture-similar conditions. Pre-Path
> α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] cross-package bit-exact validated against
> [reference]; pre-Path α.

#### Tier II.mle-band — Phase 3 cross-package PASS at MLE-fit band tolerance (13 wrappers)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], cross-package
> MLE-fit band parity validated against [reference + version]
> per Phase 3 audit dated [date]; tolerance band 1e-2 to 1e-1
> abs typical for this technique class. Pre-Path α expert
> review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validated per Phase 3
> reference parity infrastructure. **Reference:** [package + version;
> e.g., R `rugarch` for sgarch family]. **Verdict:** PASS at MLE-fit
> band tolerance (Pattern A primary tier; tolerance class
> mle_fit). NOT bit-exact at machine precision; tolerance band
> 1e-2 to 1e-1 abs typical reflects MLE optimization local-optima
> sensitivity + EM-stochastic widened band where applicable. **Audit
> date:** [date]. **Methodology resolutions documented:** [if any
> DSCD pattern instances per audit; e.g., for sgarch: rugarch
> default solver landed at boundary local optimum, gosolnp solver
> with seeded restarts required for clean comparison]. **Fixture:**
> seeded single-fixture; parameter-sensitivity coverage NOT
> established. Pre-Path α expert review status.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier II.mle-band. Reference:
> [reference]. Audit: `p3_[wrapper]_audit.md` dated [date].
> Verdict: PASS at MLE-fit band tolerance (1e-2 to 1e-1 abs
> typical). Documented methodology resolutions: [list DSCD or
> Pattern J resolutions]. Risk attribution NOT bit-exact;
> conditional on tolerance band being acceptable for risk
> measurement granularity. Pre-Path α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] cross-package PASS at MLE-band; not bit-exact;
> pre-Path α.

#### Tier III — Phase 3 same-library self-parity validated (Pattern A.1; 18 wrappers)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], same-library
> wrapper-integrity validated against [library + version];
> independent-implementation cross-package validation NOT
> established (typical for this technique class). Pre-Path α
> expert review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validation is
> wrapper-integrity-only (Tier III; Pattern A.1 same-library
> self-parity). **Library:** [library + version; e.g., sklearn
> 1.8.0 for ML/DL block techniques]. **Verdict:** PASS bit-exact
> 0.0 abs diff against direct in-process invocation. **Validation
> claim scope:** wrapper preprocessing + parameter resolution +
> audit-field round-trip without bugs. **Validation claim
> exclusion:** independent-implementation correctness; this tier
> does NOT validate against an alternative library or
> implementation. **Independent reference availability for this
> technique class:** [typically described — e.g., for sklearn ML/DL:
> "no meaningful independent reference exists; same-library
> self-parity is best available evidence"]. Pre-Path α expert
> review status; Q3a cross-package extension considered but
> [SKIP rationale or PURSUED rationale per Q3a per-technique
> decision].

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier III (same-library self-
> parity). Library: [library + version]. Wrapper integrity
> validated; independent implementation correctness NOT
> validated at this tier. Risk attribution conditional on
> [library] being correctly implemented. Pre-Path α expert
> review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] same-library wrapper-integrity validated;
> independent implementation NOT validated; pre-Path α.

#### Tier IV — Phase 3 self-parity / paper-formula validated (Pattern A.3; ~10 wrappers)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], paper-formula
> from-scratch reimplementation validated per Phase 3 audit
> dated [date]; closed-form recursion comparison. Pre-Path α
> expert review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validated against
> from-scratch reimplementation of paper-defined recursion;
> Pattern A.3 self-parity. **Paper reference:** [paper citation,
> if documented; e.g., for Pattern K → Pattern A path BOCPD:
> Adams & MacKay 2007 BOCPD recursion]. **Verdict:** PASS
> closed-form bit-exact or near-bit-exact at machine precision.
> **Validation claim scope:** TSL implementation matches paper-
> defined recursion; paper-defined recursion is itself the
> reference. **Validation claim exclusion:** if paper recursion
> is itself incorrect or under-specified, parity does not catch
> it. Pre-Path α expert review status.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier IV (paper-formula self-
> parity). Paper reference: [citation]. Validated against from-
> scratch reimplementation; paper recursion is reference.
> Pre-Path α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] paper-formula self-parity validated; pre-Path α.

#### Tier V — Phase 3 PASS with documented divergence (Pattern D / Pattern J caveat overlay)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], parity
> validated with documented methodology divergence
> ([divergence_summary; e.g., for VAR: AIC scale offset]);
> primary-tier verdict PASS; secondary-tier divergence
> non-blocking per Phase 3 audit dated [date]. Pre-Path α
> expert review status.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] validated per
> Phase 3 reference parity infrastructure with documented
> methodology divergence on specific outputs. **Reference:**
> [package + version]. **Primary-tier verdict:** PASS [specify
> outputs]. **Secondary-tier divergence:** [specify divergence;
> e.g., for VAR: AIC scale offset; for EGARCH: alpha vs gamma
> naming swap; for Lomb-Scargle: scipy vs astropy normalization
> convention]. **Divergence rationale:** [reference vs TSL
> methodology choice difference; non-bug; non-blocking].
> Published-research output relying on [primary-tier output]
> covered by parity validation; published-research output
> relying on [divergent output] requires per-output rationale.
> Pre-Path α expert review status.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier V (parity with documented
> divergence). Primary outputs: PASS. Divergent outputs: [list].
> Risk attribution from primary outputs covered; risk
> attribution from divergent outputs requires per-divergence
> rationale. Pre-Path α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] parity-validated with documented divergence on
> [outputs]; pre-Path α.

#### Tier VI — Phase 3 CAVEAT (5 wrappers: emd_hht, mstl, nar_narx, star, stl)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id], parity
> validated with caveat ([caveat_summary]); use within
> documented validity regime. Pre-Path α expert review
> status; CAVEAT may revise to PASS or expand under Q3b
> parameter-sensitivity coverage.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] Phase 3 audit
> verdict CAVEAT. **Reference:** [package]. **Caveat
> specification:** [specific caveat per audit; e.g., for
> emd_hht: boundary effects in mode-mixing detection;
> for mstl: iterative LOESS divergence in seasonal
> decomposition under specific period configurations].
> **Validity regime:** [specific configuration ranges where
> caveat applies vs ranges where it does not]. **Published-
> research use guidance:** within validity regime, parity
> evidence applies; outside validity regime, this technique
> requires Q3b extension or expert-review-pre-publication
> per per-application judgment. Pre-Path α expert review
> status.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier VI (CAVEAT). Caveat:
> [specific caveat]. Validity regime: [specification].
> Risk attribution conditional on application within
> validity regime; outside regime requires per-application
> validation. Pre-Path α expert review status.

**Pattern (iv) Internal use disclosure:**
> [technique_id] parity-validated with caveat: [caveat
> summary]; use within validity regime; pre-Path α.

#### Tier VII — No Phase 3 parity infrastructure (1 catalog technique: auto_arima)

**Pattern (i) Research note footnote:**
> This analysis uses TSL technique [technique_id]; reference
> parity validation pending per Phase 7+ Q2 work program;
> use NOT recommended for published output without expert
> review of underlying technique implementation.

**Pattern (ii) Technical appendix:**
> Methodology: TSL technique [technique_id] does NOT have
> Phase 3 reference parity infrastructure. Q2 work program
> scope; net-new validation pending. **Pre-validation
> mitigation for current use:** [if any specific mitigation;
> e.g., narrative methodology review by Chat against
> alternative implementations; cross-check against simpler
> benchmark]. **Use guidance:** technique should NOT back
> published output during pre-validation window without
> expert review of underlying implementation; if used, per-
> use disclosure must explicit-flag the unvalidated state.

**Pattern (iii) Risk model documentation:**
> [technique_id] validation: TSL Tier VII (no parity
> infrastructure). Q2 work program scope; pre-validation.
> Risk attribution from this technique NOT recommended at
> standard granularity; if used, manual review of underlying
> implementation required per use case.

**Pattern (iv) Internal use disclosure:**
> [technique_id] NOT validated; use only with expert review
> of underlying implementation per use case.

### §3.3 Multi-map catalog↔wrapper handling

Per S9 §2 amendment Disposition 4: catalog↔wrapper mapping is not
necessarily 1:1. Multi-map cases (e.g., p3_ccf covers cross_correlation_lag
+ prewhitened_ccf_lag + rolling_ccf_lag) require per-catalog disclosure
even though wrapper validation is shared.

For multi-map cases, disclosure templates above apply per catalog
ID with reference to shared wrapper:

> [catalog_id] is one of [N] catalog techniques covered by shared
> Phase 3 wrapper [shared_wrapper]; validation evidence per
> [shared_wrapper] audit applies; per-catalog interpretation
> per technique-specific output mapping.

Forward instrumentation per S9 §2 Disposition 4: Q1 sub-sessions
verify catalog↔wrapper mapping at each technique characterization;
do NOT assume 1:1 mapping; multi-mapping pattern likely recurs.

### §3.4 Path α retroactive correction risk language

Per S6 §4 ratification 5 + Path α expert review timing: outputs
published during work program window may require retroactive
correction if expert review surfaces upstream errors. All
disclosure templates explicit-flag this with "Pre-Path α expert
review status" + "[methodology updates retroactively if expert
review surfaces upstream errors]" language.

The retroactive correction risk is the institutional cost the user
explicitly ratified consciously at S6. Disclosure templates make the
exposure transparent to the published-research audience without
overclaiming validation strength.

## §4 Verify-state-at-narration discipline operational spec

Per A6 amendment codified at Phase 7+ S7 (`calibration_baseline.md`
post-S7 absorption state) + verify-state-at-first-consumption
extension per S9 §6 forward instrumentation. This section is the
canonical operational spec; A6 cross-references this section.

### §4.1 Discipline shape

**Verify-state-at-narration:** Any artifact making claims about
codebase state must empirically re-verify those claims against
authoritative source artifacts at narration time, not propagate
from prior context.

**Verify-state-at-first-consumption:** Any artifact making synthesis
claims (taxonomic; cross-cutting; multi-source-derived) must
empirically re-verify those claims at first downstream consumption,
not just at authoring time. Authoring-time citation re-verification
covers verbatim-quote claims; first-consumption re-verification
covers synthesis claims that authoring-time discipline cannot catch.

### §4.2 Boundary conditions

Empirical re-verification is bounded by:

**(a) HEAD-stability:** Re-verification at unchanged HEAD = same
empirical reality. If HEAD has not changed since prior empirical
verification, propagation from that prior verification is acceptable.

**(b) Prior-step-discipline:** Re-verification of content that was
itself empirically extracted under verify-state-at-narration
discipline at a prior sub-session is acceptable propagation;
discipline cascades across sub-sessions via prior empirical
extraction.

**(c) Marginal-returns judgment:** Re-verification has marginal
returns; at some point repeating empirical extraction adds no
new evidence. The boundary is operational judgment: when content
was already empirically verified at recent prior step + HEAD
unchanged + no contradicting evidence, re-verification is apparatus
inflation.

**The three boundaries combine:** propagation acceptable when
HEAD-stability + prior-step-discipline + marginal-returns judgment
all hold. Failure of any one warrants fresh empirical re-verification.

### §4.3 Worked examples

**(α) S7 trigger imprecision case (cross-cycle scale):**

Phase 7+ S7 trigger drafted by Chat to absorb 5 amendment candidates.
Trigger framing said "5 observations" of A2 narrative drift pattern
while enumerating 6 distinct items. Code applied A6 verify-state-at-
narration recursive application during S7 amendment authoring; caught
the framing-vs-enumeration mismatch; codified as "6 distinct
observations across 5 sub-sessions" with explicit "Chat trigger
imprecision corrected to empirical enumeration" attribution.

**Discipline shape illustrated:** A6 applied recursively at codification
of A6 itself; Chat-side trigger imprecision caught at Code-side
codification step; explicit attribution preserves source-fidelity.

**(β) S8 first-consumption taxonomy correction (artifact-level scale):**

Phase 7+ S6 §2 codified validation tier taxonomy under verify-state-
at-narration discipline at S6 authoring time. Code's CONSTRAINT 4 re-
verification confirmed verbatim citations at authoring time. Chat-side
verbatim-fidelity verification at STOP 1.5 confirmed three localized
citation accuracy issues but did not stress-test the synthesis claims
themselves.

S8 empirical re-verification at first downstream consumption (Q1
first-step empirical re-verification of Tier II + Tier VII counts)
surfaced 4 substantive issues with S6 §2 taxonomy:
- Tier VII estimate ~3-5 empirically falsified to 1
- Tier II classification missed ~13 wrappers at MLE-fit band
- bvar partial coverage didn't fit existing taxonomy (Tier I.partial
  introduced)
- Multi-map catalog↔wrapper broke per-technique characterization
  assumption

**Discipline shape illustrated:** Authoring-time discipline (verify-
state-at-narration as codified at A6) covers verbatim-citation claims;
synthesis claims that combine across codebase state require first-
consumption empirical re-verification. The 4 S8 surfaced issues were
synthesis claims that authoring-time discipline structurally could
not catch.

**(γ) S9 STOP 1.5 fresh re-Read (micro-iteration scale):**

Phase 7+ S9 in-place amendment to scope re-framing artifact per S8
dispositions. Code drafted bvar Tier I.partial worked example with
specific number (4.58e-16 abs diff) propagated from S5 archaeology
context. Chat STOP 1 surfaced Issue 2: number's extraction history
was prior-step-discipline propagation, not S9 fresh re-Read.

Code's response: "Doing fresh re-Read NOW to satisfy CONSTRAINT 4
honestly." Fresh re-Read of `phase3_cross_batch_findings.md` line 20
at HEAD `5205779` confirmed 4.58e-16 verbatim. Honest dual attribution
applied: S9 fresh re-Read for the number + S5/P-4 propagation for the
R `vars` reference name.

**Discipline shape illustrated:** Verify-state-at-first-consumption
caught its own first operational instance within S9 STOP 1.5 cycle
itself. The discipline being codified at §4 of THIS artifact and at §6
of the scope re-framing artifact validated its own value during its
own authoring sub-session. Recursive self-validation; cleanest possible
empirical grounding.

### §4.4 Operational application protocol

Per per-sub-session execution:

**At authoring time (verify-state-at-narration):**
- Verbatim citations re-verified against source artifacts at HEAD
  unchanged from extraction
- "NOT DOCUMENTED" markings where source data absent
- Source-fidelity attribution explicit (which source; which line; which
  HEAD)

**At first downstream consumption (verify-state-at-first-consumption):**
- Synthesis claims re-verified empirically against codebase state
- Claims that don't survive re-verification surfaced as material
  divergence requiring disposition (analogous to S8 STOP 2 cycle)
- Discipline applied recursively if revision-cycle surfaces additional
  synthesis claims (analogous to S9 STOP 1.5 fresh re-Read pattern)

**Across propagation steps:**
- Prior-step-discipline + HEAD-stability + marginal-returns judgment
  define propagation acceptability
- Failure of any boundary condition warrants fresh empirical re-
  verification

### §4.5 Forward codification path

Per S9 §6 amendment: future §19.4 amendment cycle codifies verify-
state-at-first-consumption as additional A6 sub-discipline OR new
amendment. Sub-discipline-of-A6 vs new-amendment framing decision
deferred to that cycle.

This artifact (Workstream B disposition 2) is the operational spec;
§19.4 baseline absorption authoritative-state codification follows.

## §5 Operating context preservation

Three preservation marks for forward auditability. Future readers
of Phase 7+ work program (Chat instances; expert reviewer at Path
α close; user retrospective review) need to understand the
operating context Phase 7+ entered under to interpret per-technique
work program decisions correctly.

### §5.1 Mark 1 — Largest-scope ratification under explicit pushback

Per Phase 7+ scope re-framing arc S5-S6: Q-Matt-A "every technique
gets parameter-sensitivity coverage" + Q-Matt-B "Path α end-of-work-
program review" + Q-Matt-C "Q3b friction acknowledged" was ratified
by user as the largest-scope, longest-runway, highest-published-
research-exposure version of Phase 7+ available.

Chat surfaced explicit pushback: "uncomfortable but proceeding under
user authority" was Chat's stated disposition. User ratified
consciously under pushback per Chat ratification 5 at S6.

Forward auditability requires preserving this ratification context.
Future readers should understand Phase 7+ work program operates
under user-elected maximum-exposure configuration; per-technique
work program decisions inherit this context.

### §5.2 Mark 2 — Institutional-grade standard

Per Phase 7+ S8 disposition turn: user affirmed "we're going to
institutional grade/top-of-the-line outcomes" as operating standard.

Chat surfaced four operational implications:
1. Speed yields to correctness
2. Disclosure language is load-bearing reputation infrastructure
3. 7-tier validation taxonomy must be technically defensible
4. Q3b ~30-60 sub-session estimate is a floor, not a target

These four implications are operative across the work program;
future readers should interpret per-technique work program decisions
against this standard, not against efficiency-optimization standard.

### §5.3 Mark 3 — Efficient-ratification observation

Per Phase 7+ S9-post-close turn: user agreed efficiently to Chat's
recommended sequencing (Workstream B ship → §19.4 absorption → S10
Q1 first-technique activation; defer retrospective).

Chat marked the efficient ratification as itself the smooth-
ratification pattern the prior Chat instance flagged ("ratifications
can become smoother as work proceeds"). Chat stated proceeding under
apparatus discipline rather than momentum-driven smoothness; STOP 1
verbatim-fidelity verification standard preserved at full force for
this artifact.

Forward auditability requires preserving this self-observation.
Future readers should understand: efficient-ratification pattern was
explicitly noted; Chat-side discipline was preserved against
momentum; the pattern recurrence is itself instrumentation data for
forward smooth-ratification countermeasure calibration.

## §6 Banking footer

**Phase 7+ banking locus state at this commit:** second entry at
`docs/reference_parity_phase7/`. First entry: `scope_reframing_s6_banking.md`
(S6 + S9 amendments; tier taxonomy + work program scope authority).
Second entry: this artifact (Workstream B disposition 2; operational
disciplines authority).

**Cross-references:**
- S6 scope re-framing artifact (S6 + S9 amendments) at
  `docs/reference_parity_phase7/scope_reframing_s6_banking.md`;
  tier taxonomy authority + work program scope authority
- §19.4 living calibration baseline post-S7 absorption state at
  `docs/reference_parity_phase6/calibration_baseline.md`; A1+A2
  ESTABLISHED+A3+A4+A5+A6+A7+A8 active amendments
- Phase 6+ banking locus 10 entries at
  `docs/reference_parity_phase6/`; pre-Phase 7+ apparatus
- Master plan v1.3 §15 + §19 + §19.4 at
  `plans/reference_parity_phase5_master_plan.md`
- Chat handoff §6 at conversation context (validation provenance
  audit checklist origin)
- S8 trust inventory (premise corrected at S6 §1) at
  `docs/reference_parity_phase6/tsl_trust_inventory_techniques.md`;
  Q1 trust documentation remediation scope

**Forward state:**
- §19.4 next absorption sub-session candidate to absorb disposition-5
  Path A canonical lock + verify-state-at-first-consumption
  codification + A5 sub-mechanism refinement
- S10+ Q1 first-technique activation entry point: trust documentation
  remediation per technique against ratified tier taxonomy with
  disclosure templates + audit checklist + layered-discipline spec +
  verify-state-at-narration + verify-state-at-first-consumption
  available
- Path α expert review preparation at end-of-work-program:
  per-technique audit checklist applications + disclosure templates
  + streamlining election history per Mark 1+2+3 preservation +
  validation provenance audit trail aggregate

## Disposition

Phase 7+ disposition 2 operational disciplines artifact committed.
Validation provenance audit checklist (4 questions per technique
close) codified. Layered smooth-ratification countermeasures (Tier
1 / Tier 2 / Tier 3 mandatory for Q3b) codified. Methodology
disclosure templates (9 tiers × 4 patterns) codified with multi-
map handling + Path α retroactive correction risk language.
Verify-state-at-narration + verify-state-at-first-consumption
discipline operational spec codified with 3 worked examples at
3 scales (cross-cycle / artifact-level / micro-iteration).
Operating context preservation (Mark 1+2+3) codified for forward
auditability. Phase 7+ banking locus second entry established.
S10+ Q1 first-technique activation cleared to proceed after
§19.4 absorption sub-session.
