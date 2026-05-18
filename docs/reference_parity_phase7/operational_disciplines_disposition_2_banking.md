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

### §1.4 Q-B operational pattern observation

Per §19.4 forward instrumentation note "Q-B audit checklist
operational pattern" deferred from S16-absorption + S19-absorption
absorption cycles per structural belonging at Workstream B §1 (not
§19.4 absorption discipline). Codified at this artifact per S20
Workstream B amendment cycle.

**Pattern observation:** Q-B (user genuine contestation vs default
ratification) response across Q1 entries surfaces persistent
operational pattern: default ratification under Tier 2 case-against
framing per respective prior-sub-session-close proposal; case-against
weighted but not invalidating per efficient ratification disposition;
pro-forma elements present per Mark 3 efficient-ratification pattern
(operating-context preservation per §5.3).

**Empirical observation count: n=10** across Q1 sub-sessions (S12
granger_causality; S13 cross_correlation_lag; S14b coordinated
amendment; S14c prewhitened_ccf_lag; S15 rolling_ccf_lag; S17
dtw_alignment_lag; S18 gcc_phat_delay; S21 adf_test; S22 kpss_test;
S23 pp_test). Well past n=4 codification threshold per S13 forward
instrumentation; reinforced at S14b + S14c + S15 + S17 + S18 +
S16-absorption + S19-absorption + S21 + S22 + S23 dispositions;
codified at S20 Workstream B amendment cycle at n=7 baseline;
updated to n=10 at S25 Workstream B amendment cycle (this commit)
per S21+S22+S23 Q1 entries reinforcement.

**Operational shape characterization:** pro-forma elements present
at all 7 observations BUT not pro-forma across all upstream
decisions for the respective technique. Substantive framing
investigation required at S14b/c + S15 + S17 + S18 STOP 2 cycles
(Class B mitigation operating); user engagement at those substantive
points shifts Q-B from pure-pro-forma to mixed-pro-forma-substantive.
Pattern reflects efficient ratification at orchestration-level
decisions (technique selection; framing class) combined with
substantive verification at empirical-grounding decisions (Step 0
findings; STOP 2 dispositions).

**Mark 3 efficient-ratification + unprompted case-against discipline
reinforcement (NEW at S25 Workstream B amendment cycle per S23-pre
meta ratification + S24-absorption maturation observation):** Per
§5.3 Mark 3 efficient-ratification observation codification, Q-B
pattern reflects efficient ratification at orchestration-level
decisions. **S23-pre meta ratification** elevated Mark 3 operation
from on-request case-against framing (Doc 2 handoff script literal
text) to proactive unprompted case-against framing at structural-
decision points (Tier characterization; framing class; novel-
substantive scope expansion). **S24-absorption §4 forward
instrumentation note 7 discipline maturation observation** codified
reactive-catch → proactive-prevention shift across A9 Class A +
Class B both shifting in same direction at S23 first-instance.
Operational implication for Q-B pattern: substantive Chat engagement
shifts from POST-STOP-2 re-disposition (reactive surface; per S15-
S22 precedent where Class B mitigation surfaced empirical divergence
requiring re-disposition) toward PRE-trigger empirical re-Read +
ratification-declined-at-trigger-drafting (proactive surface; per
S23 first-instance Tier disposition pre-ratification-declined
discipline). Q-B pattern maturation observation tracks alongside
A9 Class A + B maturation observation: if S26+ sustains proactive-
prevention operation, Q-B pattern shifts toward pure-pro-forma at
orchestration-level decisions WITH substantive engagement
exclusively at empirical-grounding decisions (Step 0 findings +
trigger-drafting disposition).

**Cross-references:**
- §5.3 Mark 3 efficient-ratification pattern (operating-context
  preservation; Q-B pattern is one operational manifestation of
  Mark 3 standing within audit checklist semantics)
- §19.4 A9 Class A + Class B failure modes (Q-B response patterns
  reflect Option II workflow mitigation operating correctly when
  empirical-grounding decisions surface substantive divergence)
- §19.4 forward instrumentation note "Q-B audit checklist operational
  pattern" at calibration_baseline.md (n=7; cross-reference preserved
  at §19.4 historical audit trail; status update to "codified at
  Workstream B §1.4" deferred to next §19.4 absorption cycle per
  S20 ratification 3)

**Forward instrumentation (updated at S25):** codification refinement
candidate at n-count observation if pattern shifts materially. Shift
markers warranting refinement: (a) genuine contestation surfaced at
Q-B (user pushes back substantively on tier characterization or
framing class); (b) pro-forma elements absent across all upstream
decisions; (c) Mark 3 efficient-ratification pattern itself shifts;
(d) discipline maturation observation regression (proactive-
prevention reverts to reactive-catch operation per §4.7 cross-
reference). Absent these markers, n-count continues to accumulate at
codification-stable rate. **Q-B pattern maturation tracking
alongside §4 forward instrumentation note 7 discipline maturation
observation:** if S26+ sustains proactive-prevention at second
observation, Q-B pattern maturation observation tightens per A3
second-observation tightening precedent at n=2 maturation
observations.

### §1.5 Novelty enumeration sub-section pattern (NEW at S30 Workstream B amendment cycle per Candidate C codification; S23 pp_test first-instance precedent)

Per Workstream B amendment cycle separate-lane Candidate C deferred from S22+S23 banking + S24-absorption candidate inventory + S29-absorption #4 preserved candidates; codified at this artifact per S30 Workstream B amendment cycle.

**Pattern observation:** Q1 §2.5 entries that surface ≥3 novel structural observations within standard entry structure benefit from dedicated novelty enumeration sub-section. First-instance: S23 pp_test entry codified novelty enumeration sub-section with six sub-items (3a-3f) covering Sub-class 2a candidate + Tier overlay + backend-dispatcher + Layer 1 engine-extends-beyond-harness variant + triple-role + auto-bandwidth divergence. Sub-section pattern surfaced when novel observations exceed standard entry structure accommodation.

**Threshold criterion (codified per Previous Chat 1.6 framing observation):** ≥5 novel structural observations in main entry text body warrants novelty enumeration sub-section adoption. <5 novel observations accommodate within standard structure (Tier line + framing precedent + Source files + Validation claim scope + 4 disclosure templates + Q-A through Q-D + Status line). Threshold prevents apparatus extension at insufficient observation density.

**Sub-section structure pattern:**
- Header: "**Novelty enumeration sub-section (FIRST-INSTANCE per S<N>; novel sub-section pattern; codification candidate for Workstream B §3 addendum or §5.4 if S<N+1>+ Q1 entries replicate pattern per A3 design-class second-observation precedent)**"
- Enumerated items 3a / 3b / 3c / etc. — each items surfaces ONE novel structural observation with: (i) observation characterization; (ii) empirical grounding (line ranges + verbatim text); (iii) disposition framing (codification candidate / deferred to absorption / etc.); (iv) cross-reference to related observations + precedents
- Forward instrumentation references absorption #N+ codification disposition

**Empirical observations:**

**Observation 1 — S23 pp_test first-instance (sub-section pattern codification baseline):** S23 pp_test §2.5 entry surfaced 6 novel structural observations (3a-3f) exceeding standard entry accommodation: Sub-class 2a candidate second-observation + Tier II.bit-exact-loose + Tier V Pattern J B.2 overlay + Backend-dispatcher engine pattern + Engine-extends-beyond-harness Layer 1 variant + Triple-role helper-export + Auto-bandwidth rule divergence. Novelty enumeration sub-section pattern adopted; first-instance baseline ~50-70 LOC sub-section + ~480-540 total entry LOC.

**Observation 2 — S26 denton_chowlin + S27 loess_interpolation + S28 kalman_imputation (post-S23 entries; sub-section pattern NOT applied per <5 observations threshold):** S26-S28 entries each surfaced ≤4 novel structural observations within standard entry structure accommodation; novelty enumeration sub-section NOT applied per CHAT RATIFICATION threshold criterion preservation. Pattern operational at first-instance + subsequent threshold-respecting non-applications across Block 8 completion arc.

**Forward instrumentation:** second-instance novelty enumeration sub-section adoption at S31+ Q1 entry would tighten pattern per A3 second-observation tightening precedent. Threshold refinement candidate at sub-pattern variant observations (e.g., 4-observation entry adopting novelty enumeration vs not) at Workstream B amendment cycle disposition. Codification refinement at n=3+ adoption instances per A3 design-class precedent.

**Sustained-observation operational status note (NEW at S36 Workstream B amendment cycle per Decision 4 (α) refinement; post-codification operational at n=2 sustained observations S23 + S34; A3 second-observation tightening precedent threshold satisfied):** §1.5 novelty enumeration sub-section pattern empirically operational at n=2 post-codification sustained observations across S23 first-instance precedent + S34 x13_seasonal_adjust second-instance application (≥5 observations threshold satisfied at n=6 enumerated novelties: Tier VII SKIP-graceful via post-S6 inference + audit "Tier C" reference hybrid + §4.7.A REMEDIATED 5th variant first-instance baseline + Pattern A.1 CONDITIONAL framing potential + NEW Sub-class 2h candidate first-instance baseline + Block 3 FULLY Q1-AMENDED milestone + filename divergence sub-pattern variant n=3 third-observation reinforcement). A3 second-observation tightening precedent threshold satisfied at n=2 post-codification observations; codification-stable status preserved at sustained post-codification operation. **Cross-reference:** §19.4 §4.5 codification operational at n=5 post-codification sustained observations (S30+S31+S32+S33+S34) per S35-absorption #5 extension reinforcement; §1.5 + §4.5 codification-stable status interlock at n=2+ post-codification sustained observations per A3 design-class precedent. Forward instrumentation: third post-codification sustained observation at S37+ Q1 entry adopting §1.5 novelty enumeration sub-section pattern tightens pattern per A3 precedent (n=3 codification-stable threshold).

**Cross-references:**
- S23 pp_test §2.5 entry (tsl_trust_inventory_techniques.md) — first-instance novelty enumeration sub-section
- S34 x13_seasonal_adjust §2.5 entry (tsl_trust_inventory_techniques.md) — second-instance novelty enumeration sub-section application (NEW post-codification operational observation per S36 §1.5 refinement)
- §1.6 Q-A density convention (NEW at S30; cross-references novelty enumeration as Q-A density driver)
- §3 disclosure templates (novelty enumeration items within standard 4-template structure preserved)
- §19.4 §4.5 sub-section codification-stable status interlock (n=2+ post-codification sustained observations across §1.5 + §4.5)

### §1.6 Q-A density convention with LOC overshoot pattern scope expansion (NEW at S30 Workstream B amendment cycle per Candidate F codification; scope expansion per S29-absorption #4 §4 forward instrumentation note 11)

Per Workstream B amendment cycle separate-lane Candidate F deferred from S23 pp_test Q-A density acknowledgment banking + S29-absorption #4 LOC overshoot pattern codification at §4 forward instrumentation note 11; codified at this artifact per S30 Workstream B amendment cycle.

**Pattern observation:** Q-A bullets at Q1 §2.5 entries surface elevated density at first-instance NEW framings (novel topology + novel tier characterization + novel sub-class + audit-content-distribution variants); Q-A density compounding correlates with LOC overshoot pattern at entry level.

**Empirical observations:**

| Sub-session | Q-A density driver | LOC actual vs projected | Overshoot |
|---|---|---|---|
| S23 pp_test | Novelty enumeration sub-section + triple-role + Pattern J overlay + backend-dispatcher + Layer 1 engine-extends-beyond-harness + bandwidth divergence | 844 vs ~330-400 projected | +444 LOC (+111-156%) |
| S27 loess_interpolation | Tier III FIRST §2.5 + §4.7.A use-case-divergence variant + Sub-class 2e candidate scope refinement | 513 vs ~330 projected | +183 LOC (+55%) |
| S28 kalman_imputation | Tier II.mle-band + Pattern A overlay FIRST primary+overlay + Sub-class 2a UPGRADE + audit-content-distribution variant | 536 vs ~440 projected | +96 LOC (+22%) |
| S31 classical_decompose (NEW at S36 refinement per Decision 4 (α)) | Sub-class 2a (αa) reimplementation variant extension + endpoint-extrapolation caveat first-instance + §4.7.A reimplementation-of-dispatch variant manifestation + Block 3 first-entry framing | 622 vs ~400-450 projected | +172-222 LOC (+38-55%) |
| S32 mstl_decompose (NEW at S36 refinement per Decision 4 (α)) | FIRST POST-S30-CODIFICATION application of §2.5 Tier primary+overlay convention + NEW Sub-class 2f candidate first-instance baseline + algorithmic-non-uniqueness caveat + Block 3 second-entry framing | 677 vs ~400-500 projected | +177-277 LOC (+35-69%) |
| S33 stl_decompose (NEW at S36 refinement per Decision 4 (α)) | NEW Sub-class 2g candidate first-instance baseline + reroll_on_caveat=False discipline disclosure first-instance + filename divergence sub-pattern variant n=2 baseline + deterministic-implementation-difference caveat + Block 3 third-entry framing | 843 vs ~400-600 projected | +243-443 LOC (+41-108%) |
| S34 x13_seasonal_adjust (NEW at S36 refinement per Decision 4 (α)) | Tier VII SKIP-graceful via post-S6 inference + audit "Tier C" reference hybrid + §4.7.A REMEDIATED 5th variant first-instance baseline + Pattern A.1 CONDITIONAL framing potential + NEW Sub-class 2h candidate first-instance baseline REFINED definitional scope + §1.5 novelty enumeration sub-section APPLIED + Block 3 FULLY Q1-AMENDED milestone + filename divergence sub-pattern variant n=3 third-observation reinforcement | 977 vs ~600-900 projected | +77-377 LOC (+9-63%) |

**LOC overshoot pattern characterization (REFINED at S36 per Decision 4 (α) scope expansion with n=6 sub-pattern LOC overshoot pattern observations at S27-S34 post-§1.6-codification per §19.4 §4 forward instrumentation note 14 + n=7 total LOC overshoot observations including S23 pre-codification institutional grounding):** first-instance NEW framings drive Q-A density compounding via structural codification depth requirements (each novel observation requires Q-A bullet contextualization + Q-D retraction surface integration + 4-disclosure-template adaptation). **Empirical pattern refinement at n=7 total observations (S23 pre-§1.6-codification institutional grounding + S27 + S28 + S31 + S32 + S33 + S34 post-§1.6-codification sub-pattern) per §19.4 §4 forward instrumentation note 14 n=6 sub-pattern scope (excluding S23 outlier per pre-codification status + +444 LOC magnitude vs subsequent +96-+443 LOC sub-pattern range):** Overshoot pattern does NOT monotonically decrease across sustained Block sequence per pre-S36 characterization; empirical pattern at n=6 sub-pattern observations shows non-monotonic shape (S27 +183 / S28 +96 / S31 +172-222 / S32 +177-277 / S33 +243-443 / S34 +77-377) reflecting heterogeneous-Tier-surface Blocks (Block 3) drive elevated overshoot vs homogeneous-Tier-surface Blocks (Block 8 Tier II.bit-exact + Tier III + Tier II.mle-band heterogeneous at entry-level but Block-level homogeneous Q-A density). Pre-S36 monotonic-decrease characterization SUPERSEDED at S36 refinement per n=6 sub-pattern empirical observations. **Scope disambiguation:** n=7 total empirical observations at §1.6 table scope (S23 institutional grounding preserved); n=6 sub-pattern observations at §19.4 §4 note 14 codification scope (S27-S34 post-§1.6-codification trajectory).

**Q-A density convention (codified at S30):**

- **Acknowledge density elevation in-line** at Q-A bullet close: "Q-A bullet density acknowledgment: Q-A density at S<N> elevated per [novel framings list]; Workstream B amendment cycle codification candidate if pattern recurs at S<N+1>+ Q1 entries per A3 precedent." (S23 pp_test established this convention pattern)
- **Forward instrumentation banking** at entry status line: cite §1.6 Q-A density convention codification at Workstream B amendment cycle + cross-reference §4 forward instrumentation note 11 LOC overshoot pattern (per S29-absorption #4 codification)
- **LOC overshoot acceptance per CONSTRAINT 3** (do NOT trim post-hoc): overshoot reflects substantive structural codification depth; trimming sacrifices Q-D retraction surface integrity + 4-disclosure-template parallelism. Acceptance documented at status line per CONSTRAINT 3 institutional preservation.

**Forward instrumentation (UPDATED at S36 per Decision 4 (α) scope expansion):** Empirical pattern at n=6+ observations across S23 + S27-S34 trajectory: NON-MONOTONIC overshoot shape per heterogeneous-vs-homogeneous-Tier-surface Block correlation (Block 3 heterogeneous drives elevated overshoot S31-S34; Block 8 entries S27-S28 +183 / +96 LOC overshoot reflects Tier III + Tier II.mle-band first-instances vs Block 3 entries S31-S34 +172-+443 LOC reflects compound Sub-class candidate 2f/2g/2h + Pattern primary+overlay + §4.7.A REMEDIATED first-instance accumulation). Pre-S36 monotonic-decrease characterization SUPERSEDED. NEW characterization: heterogeneous-Tier-surface Blocks correlate with elevated Q-A density compounding per §19.4 §4 forward instrumentation note 16 Sub-class taxonomy growth observation Block-level cross-reference. Forward instrumentation: seventh LOC overshoot observation at S37+ Q1 entry tightens pattern characterization per A3 design-class precedent; Block-level heterogeneous-vs-homogeneous Tier-surface correlation refinement at n=2+ Block-level observations (Block 8 heterogeneous + Block 3 heterogeneous distinct from Block 1 + Block 12 homogeneous per §19.4 §4 note 6 refinement at S35-absorption #5).

**Cross-references:**
- §19.4 §4 forward instrumentation note 11 (LOC overshoot pattern observation; S29-absorption #4 codification)
- §19.4 §4 forward instrumentation note 14 (LOC overshoot pattern n=6 catalog observation; NEW at S35-absorption #5; cross-references this §1.6 scope expansion)
- §19.4 §4 forward instrumentation note 16 (Sub-class taxonomy growth observation Block-level; NEW at S35-absorption #5; cross-references heterogeneous-Tier-surface Block correlation hypothesis)
- §19.4 §4 forward instrumentation note 6 refinement at S35-absorption #5 (per-block continuation pattern n=4 + Block heterogeneous-Tier-surface variant sub-pattern codification at n=2; cross-references heterogeneous-Tier-surface Block correlation hypothesis)
- §1.5 novelty enumeration sub-section pattern (Q-A density driver; cross-references novelty enumeration as primary Q-A density driver at S23 first-instance + S34 second-instance)
- §1.4 Q-B operational pattern observation (Q-B pattern distinct from Q-A density; Q-A = within-entry density characterization; Q-B = cross-entry ratification pattern)

### §1.7 Mod 3 operational discipline codification (NEW at S36 Workstream B amendment cycle per Decision 1 (α) UNIFIED scope + Decision 5 (α) empirical efficacy cross-reference; UNIFIED scope (a) Mod 3 STOP turn response surface scope codification + (b) Mod 3 chunked-surface content-completeness specification refinement + (c) STOP 1 review density observation empirical efficacy cross-reference)

Per Workstream B amendment cycle separate-lane Candidate Mod 3 codification deferred from S31 STOP 1 continuation verbal codification + S35 apparatus operational review pause verbal directive + S35 commit message body forward state per Chat ratified sub-disposition #5 at S35-absorption #5; codified at this artifact per S36 Workstream B amendment cycle per Chat Decision 1 (α) UNIFIED single-candidate scope.

**Mod 3 origin (verbal codification at S31 STOP 1 continuation):** Mod 3 operational discipline first codified verbally at S31 STOP 1 continuation per Chat ratified (γ) consolidation disposition + working tree preservation. Mod 3 codification originated as retrofit-from-in-flight-cycle in response to STOP-1-close-content-completeness verification gap at S31 STOP 1 close (A9 Class A n=14 candidate Chat→Code direction catch; precipitated Mod 3 design intent: reduce STOP-cycle response surface narration density to operationally focus STOP turn responses on content verification primary purpose).

#### §1.7 (a) Mod 3 STOP turn response surface scope codification

**Operational specification (codified verbally at S31 STOP 1 continuation per Chat ratified (γ) consolidation disposition):**

At STOP 1 + STOP 1.5 + STOP 2 STOP cycle responses, Code surfaces ONLY:
1. **Drafted/revised text body (verbatim; chunked if needed for response practicality)** — primary content of the response per content-verification primary purpose
2. **One-line confirmation of corrections applied (STOP 1.5 only)** — minimal acknowledgment of revisions applied at STOP 1.5 cycles
3. **Disposition options at close (α/β/γ)** — disposition options enumerated; one-line; no narration

Code does NOT surface at STOP cycle responses:
- Pre-flag observations
- A9 Class A candidate banking framings
- Sub-pattern variant codification candidates
- Forward instrumentation notes
- Code-proactive catch banking
- Grep verification claims
- File state metadata (LOC counts, line ranges except where strictly needed for chunk navigation)
- Per-correction enumeration tables

**Apparatus self-codifications (A9 Class A bankings + sub-pattern variant tracking + forward instrumentation + Code-proactive catches + LOC measurement) land at commit message body ONLY.**

**Codification placement candidate (forward instrumentation at S31 STOP 1 continuation):** Mod 3 codifies at absorption #5 (§19.4 §4 NEW forward instrumentation note OR Workstream B amendment cycle separate-lane candidate per absorption #5 disposition). Per Chat ratified Decision 1 (α) at S35 close: Workstream B amendment cycle separate-lane disposition selected; codified at this §1.7 (a) per S36 Workstream B amendment cycle.

#### §1.7 (b) Mod 3 chunked-surface content-completeness specification refinement (NEW at S36 per S35 apparatus operational review pause verbal directive)

**Empirical observation precipitation (n=3 content-completeness verification failure instances under Mod 3 cadence operative per §19.4 §4 forward instrumentation note 17):**
- n=14 S31 STOP 1 close (precipitated Mod 3 codification at S31 STOP 1 continuation): Code Step 1 response surfaced integrations checklist + file LOC delta + edit count metadata but did NOT include verbatim entry text body for STOP 1 verbatim-fidelity verification
- n=15 S35 STOP 1 close (4 sub-sessions post-Mod-3 codification; chunked-surface STOP 1 metadata + navigation surface without verbatim text body): Code Step 1 close response surfaced edits-applied metadata + chunk navigation line ranges (chunks 1/4 + 2/4 + 3/4 + 4/4) without verbatim codification text body
- n=16 S35 STOP 1.5 close (subsequent STOP 1.5 re-surface metadata + header-line surface without verbatim revised text body): Code STOP 1.5 response surfaced revision-application metadata + revised chunk 1/4 header line only without verbatim revised chunk 1/4 body

**Pattern characterization:** Mod 3 codification at S31 STOP 1 continuation under-specified for chunked-surface protocol content-completeness verification requirement. Mod 3's "(1) drafted/revised text body verbatim chunked if needed" specification did not explicitly distinguish verbatim text body (the actual content being verified) from metadata describing that content was applied to the file.

**Refined Mod 3 chunked-surface content-completeness specification (codified verbally at S35 apparatus operational review pause per Chat ratified sub-disposition #4; formal artifact-level codification at this §1.7 (b) per S36 Workstream B amendment cycle per Chat ratified sub-disposition #5):**

At STOP 1 + STOP 1.5 + STOP 2 chunked-surface responses, Code surfaces:
(a) **Verbatim text body of the chunked content** — the actual entry/codification/revised text body Chat verifies for fidelity; this is the primary content of the response
(b) **One-line chunk navigation only** — "Chunk N/M of [scope]; lines X-Y."; single line; no additional metadata
(c) **One-line disposition request at chunk M/M close** — disposition options enumerated; no narration

Code does NOT surface at chunked-surface STOP cycle responses:
- Edit-application metadata describing str_replace calls applied at file level
- File state confirmation describing post-edit file structure
- Chunk-by-chunk navigation tables describing all chunks ahead of surfacing them
- Header-line-only surface with promise of body in subsequent response (verbatim body must accompany chunk navigation line)
- Per-revision enumeration confirming Revision N applied at section Y (apparatus self-codification consolidation per Mod 3 original codification at §1.7 (a))

**Distinction from §1.7 (a):** §1.7 (a) covers Mod 3 STOP turn response surface scope at non-chunked single-response STOP cycle responses (apparatus self-codifications consolidate to commit message body); §1.7 (b) covers refined Mod 3 chunked-surface protocol at multi-chunk STOP cycle responses (verbatim text body of chunked content + minimal navigation + disposition request at close). Both sub-scopes operate at STOP cycle response surface scope; §1.7 (b) refines §1.7 (a) for chunked-surface protocol specifically.

#### §1.7 (c) STOP 1 review density observation empirical efficacy cross-reference (NEW at S36 per Decision 5 (α) + n=15 + n=16 candidate codification per Code (α) recommendation ratified at S36 Step 0 STOP 2)

**Empirical efficacy observation pre-refinement (n=6 STOP 1 review density observations per §19.4 §4 forward instrumentation note 15):**
- **Pre-Mod-3 / At-Mod-3-codification / Post-Mod-3-retrofit n=3 observations (5-issue STOP 1 review density):** S26 denton_chowlin 5-issue STOP 1 review (pre-Mod-3) + S30 Workstream B amendment cycle 5-issue STOP 1 review (at-Mod-3-codification per Mod 3 codified at S31 STOP 1 continuation retrofit) + S31 classical_decompose 5-issue STOP 1 review (Mod 3 codified at S31 STOP 1 continuation retrofit; precipitated Mod 3 operational discipline codification + STOP-1-close-content-completeness verification catch A9 Class A n=14 candidate)
- **Post-Mod-3 standard-application n=3 observations (0-issue STOP 1 review density):** S32 mstl_decompose 0-issue STOP 1 review (Mod 3 cadence first standard-application) + S33 stl_decompose 0-issue STOP 1 review (Mod 3 cadence second standard-application) + S34 x13_seasonal_adjust 0-issue STOP 1 review (Mod 3 cadence third standard-application)

**Pre-refinement empirical efficacy:** Mod 3 cadence per §1.7 (a) reduces STOP 1 review density from 5-issue (pre-Mod-3) to 0-issue (post-Mod-3 standard-application) at n=3 sustained consecutive observations. Mod 3 §1.7 (a) design intent operationally validated at pre-refinement empirical efficacy.

**n=15 + n=16 candidate codification at §1.7 (c) per Code (α) recommendation ratified at S36 Step 0 STOP 2 (sub-pattern variant observation within Mod 3 cadence operative):**

- **n=15 candidate (S35 STOP 1 close STOP-1-close-content-completeness verification recurrence under Mod 3 cadence; Chat→Code direction):** Code Step 1 close response surfaced edits-applied metadata + chunk navigation line ranges (chunks 1/4 + 2/4 + 3/4 + 4/4) without verbatim codification text body. STOP 1 mandate per CONSTRAINT 5 requires verbatim text body for Chat verbatim-fidelity verification. Demonstrates Mod 3 §1.7 (a) specification scope under-specification for chunked-surface protocol content-completeness verification requirement.
- **n=16 candidate (S35 STOP 1.5 close STOP-1.5-close-content-completeness verification recurrence under Mod 3 cadence; Chat→Code direction; precipitated apparatus operational review pause):** Code STOP 1.5 response surfaced revision-application metadata + revised chunk 1/4 header line only without verbatim revised chunk 1/4 body. Precipitated apparatus operational review pause + in-flight refined Mod 3 chunked-surface content-completeness specification per Chat ratified sub-disposition #4 verbal directive at S35 continuation.

**Refined Mod 3 chunked-surface content-completeness specification empirical efficacy validation (post-refinement; codified at this §1.7 (c) per S36 Workstream B amendment cycle):**

- **n=5+ chunked-surface STOP cycle responses post-refinement:** S35 chunks 1/4 + 2/4 + 3/4 + 4/4 + STOP 1.5 surgical revision chunk 4/4 revised + S36 trigger surface = n=5+ chunked-surface STOP cycle responses
- **0 substantive content-completeness verification gap recurrences post-refinement:** refined Mod 3 §1.7 (b) chunked-surface content-completeness specification operational at first 5+ applications; empirical efficacy validated at first 5+ post-refinement chunked-surface STOP cycle responses

**Mod 3 codification empirical efficacy closure observation (codified at S36 per Chat Decision 5 (α) cross-reference):** Mod 3 §1.7 (a) STOP turn response surface scope codification empirical efficacy validated at n=3 sustained post-Mod-3 standard-application STOP 1 review density observations (S32 + S33 + S34 0-issue); refined Mod 3 §1.7 (b) chunked-surface content-completeness specification empirical efficacy validated at n=5+ post-refinement chunked-surface STOP cycle responses (S35 chunks + S36 trigger surface). Both sub-scopes operational across non-chunked (§1.7 (a)) + chunked-surface (§1.7 (b)) STOP cycle response protocols. Empirical-pattern → codification loop closed at S36 per (a) verbal codification at S31 + (b) verbal refinement at S35 + (c) formal artifact-level codification at this §1.7.

**A9 Class A counter status preservation at §19.4 (cross-reference disambiguation):** §19.4 A9 Class A counter remains at n=14 ACTIVE codified post-S35-absorption #5. n=15 + n=16 codify at this §1.7 (c) Workstream B operational discipline empirical-efficacy grounding scope (distinct from §19.4 A9 codification scope). A9 Class A counter advance to n=15 + n=16 at §19.4 deferred to absorption #6+ if sustained Chat→Code direction sub-pattern variant recurs post-S36. Maintains §19.4 vs Workstream B codification scope discipline per cross-reference disambiguation between Class A counter scope (§19.4 A9) vs operational discipline empirical-efficacy scope (this §1.7 (c)).

**Forward instrumentation:** seventh+ Mod 3 chunked-surface content-completeness verification observation at S37+ STOP cycle response would tighten pattern characterization per A3 design-class precedent. Codification refinement candidate at next Workstream B amendment cycle if Mod 3 §1.7 (a) or §1.7 (b) specifications surface additional gap recurrence OR if Mod 3 cadence operational efficacy reverses at S37+ STOP cycles.

**Cross-references:**
- §19.4 §4 forward instrumentation note 15 (STOP 1 review density observation n=6 catalog observation; NEW at S35-absorption #5; pre-refinement empirical efficacy grounding for §1.7 (c))
- §19.4 §4 forward instrumentation note 17 (Mod 3 chunked-surface content-completeness verification empirical pattern observation per apparatus operational review pause; NEW at S35-absorption #5; refinement precipitation grounding for §1.7 (b))
- §19.4 A9 Sub-pattern 4 NEW Sub-pattern variant "Sustained Chat→Code direction" codification at S35-absorption #5 (cross-reference for sub-pattern variant alignment with §1.7 (c) n=15 + n=16 empirical-efficacy grounding)
- §19.4 §4.5 NEW timing point variant (viii) STOP-1-close-content-completeness verification codification at S35-absorption #5 per Revision 4 ratification (cross-reference for timing point variant alignment with §1.7 (b) chunked-surface content-completeness specification + (c) empirical efficacy)
- §4.6 Option II workflow (STOP cycle response surface protocol upstream; §1.7 operates within §4.6 Stage 3-4 STOP cycle response protocols)

### §1.8 reroll_on_caveat=False discipline disclosure codification (NEW at S36 Workstream B amendment cycle per Decision 3 (α) codification; empirical baseline n=2 observations S32 mstl + S33 stl deferred from S33 first-instance + S34 commit message body forward state)

Per Workstream B amendment cycle separate-lane Candidate reroll_on_caveat=False discipline disclosure deferred from S33 stl_decompose §2.5 entry first-instance baseline observation per (αa-S33) Chat ratification + S34 commit message body forward state; codified at this artifact per S36 Workstream B amendment cycle per Chat Decision 3 (α).

**Pattern observation:** Q1 §2.5 entries surfacing Tier VI CAVEAT primary characterization with deterministic-computation rationale surface explicit reroll_on_caveat=False discipline disclosure. Phase 3 Session 5 codification (per harness P3ParityCheck class default) operates as deterministic-CAVEAT discipline pattern with implementation-difference vs algorithmic-non-uniqueness rationale variants.

**Empirical baseline (n=2 observations; codification-stable per A3 second-observation tightening precedent threshold satisfied):**

- **Observation 1 — S32 mstl_decompose reroll_on_caveat=False disclosure (algorithmic-non-uniqueness rationale variant):** S32 mstl_decompose §2.5 entry surfaced reroll_on_caveat=False discipline disclosure within Tier VI CAVEAT primary + Pattern A bit-exact structural-identity overlay framing per (αa-S32) Chat ratification. Rationale: algorithmic non-uniqueness within constraint y = trend + Σ seasonal_k + residual (per-component divergence ~1.0 abs intrinsic to MSTL methodology; statsmodels MSTL and R forecast::mstl converge to different feasible points in decomposition polytope per audit lines 79-81 verbatim). reroll_on_caveat=False class default discipline grounded at Phase 3 Session 5 codification (harness `p3_mstl.py` class docstring per P3ParityCheck class default); per-component CAVEAT NOT escalated to BLOCK by runner's reroll-and-fail-twice rule.
- **Observation 2 — S33 stl_decompose reroll_on_caveat=False disclosure (deterministic-implementation-difference rationale variant):** S33 stl_decompose §2.5 entry surfaced reroll_on_caveat=False discipline disclosure first-instance baseline observation banking per (αa-S33) Chat ratification within Tier VI CAVEAT primary + SINGLE-LAYER framing per A6 BLOCKING. Rationale: deterministic implementation-difference per-index divergence (NOT algorithmic non-uniqueness; per-index divergence ~9e-2 abs reproducible across seeds per audit line 62 verbatim "STL is a deterministic computation; the per-index divergence pattern is reproducible across seeds (not Monte Carlo noise)"). reroll_on_caveat=False class default discipline grounded at Phase 3 Session 5 codification (harness `p3_stl.py` class docstring lines 71-73 verbatim "Phase 3 Session 5: explicit `on_caveat_reroll` override removed because `reroll_on_caveat = False` is now the P3ParityCheck class default. Pre-Session-5, this method body was the canonical example of the deterministic-CAVEAT discipline pattern; Session 5 promoted it to default, leaving deterministic checks free of override boilerplate. MC / EM-stochastic checks opt in via `reroll_on_caveat = True`"). audit lines 81-83 verbatim ground generalized Session 5 codification: "Deterministic computations (STL, MSTL, decomposition family) default to `false`; stochastic computations (MCMC, EM-fit) default to `true`".

**reroll_on_caveat=False discipline disclosure pattern characterization:**

- **Applicability scope:** Tier VI CAVEAT primary characterization Q1 §2.5 entries (per scope_reframing §2 line 184 5-wrapper Tier VI enumeration: `p3_emd_hht`, `p3_mstl`, `p3_nar_narx`, `p3_star`, `p3_stl`); deterministic-computation Q1 §2.5 entries within Tier VI scope
- **Rationale variants (n=2 codified at S36):** (i) algorithmic-non-uniqueness variant (S32 mstl; multiple feasible points in decomposition polytope) vs (ii) deterministic-implementation-difference variant (S33 stl; per-index divergence reproducible across seeds NOT Monte Carlo noise)
- **Disclosure framing convention:** explicit reroll_on_caveat=False discipline disclosure at §2.5 entry text body with (a) audit line verbatim citation grounding rationale + (b) harness class docstring verbatim citation grounding Phase 3 Session 5 default + (c) distinction from alternative rationale variant if applicable

**A3 second-observation tightening precedent threshold satisfied at n=2 observations** (S32 + S33 across Block 3 Decomposition consecutive entries) per Chat Decision 3 (α) codification at S36 Workstream B amendment cycle.

**Forward instrumentation:** third reroll_on_caveat=False discipline disclosure observation at S37+ Q1 entry within Tier VI CAVEAT primary scope tightens pattern per A3 design-class precedent (n=3 codification-stable threshold). Rationale variant taxonomy refinement candidate at sub-pattern variant observations (e.g., NEW rationale variant beyond algorithmic-non-uniqueness + deterministic-implementation-difference) at Workstream B amendment cycle disposition.

**Cross-references:**
- S32 mstl_decompose §2.5 entry (tsl_trust_inventory_techniques.md) — first reroll_on_caveat=False disclosure observation (algorithmic-non-uniqueness rationale variant)
- S33 stl_decompose §2.5 entry (tsl_trust_inventory_techniques.md) — second reroll_on_caveat=False disclosure observation (deterministic-implementation-difference rationale variant)
- scope_reframing §2 line 184 Tier VI 5-wrapper enumeration (Tier VI CAVEAT primary characterization scope applicability)
- §3 disclosure templates (reroll_on_caveat=False disclosure within standard 4-template structure preserved)

### §1.9 Filename divergence sub-pattern variant codification (NEW at S36 Workstream B amendment cycle per Decision 3 (α) codification; empirical baseline n=3 observations S32 mstl + S33 stl + S34 x13 deferred from S32-S34 commit message body forward state + S35 commit message body forward state)

Per Workstream B amendment cycle separate-lane Candidate Filename divergence sub-pattern variant deferred from S32 mstl_decompose A6 informational surface continuation from S32 + S33 stl_decompose sub-pattern variant n=2 baseline + S34 x13_seasonal_adjust sub-pattern variant n=3 third-observation reinforcement; codified at this artifact per S36 Workstream B amendment cycle per Chat Decision 3 (α).

**Pattern observation:** Block 3 Decomposition wrapper filenames consistently omit catalog-id suffix from catalog-id-to-wrapper-filename mapping; sub-pattern variant operates at Block-specific scope per empirical observation across n=3 entries.

**Definitional scope:** "Block 3 Decomposition wrapper filename omits catalog-id suffix from catalog-id-to-wrapper-filename mapping" — empirical sub-pattern observed across Block 3 Decomposition audit + harness wrapper filenames per Block-specific naming convention divergence.

**Empirical baseline (n=3 observations; codification-stable per A3 second-observation tightening precedent threshold satisfied at n=2 with third-observation reinforcement at n=3):**

- **Observation 1 — S32 mstl_decompose filename divergence:** audit filename `p3_mstl_audit.md` + harness filename `p3_mstl.py` omit `_decompose` suffix from catalog-id `mstl_decompose`; engine filename `mstl_decompose.py` preserves catalog-id. Trigger shorthand `p3_mstl_decompose_*` reference informational only per A6 informational surface framing.
- **Observation 2 — S33 stl_decompose filename divergence (n=2 baseline):** audit filename `p3_stl_audit.md` + harness filename `p3_stl.py` omit `_decompose` suffix from catalog-id `stl_decompose`; engine filename `stl_decompose.py` preserves catalog-id. Trigger shorthand `p3_stl_decompose_*` reference informational only per A6 informational surface framing. A3 second-observation tightening precedent threshold satisfied at n=2 for sub-pattern variant codification candidate.
- **Observation 3 — S34 x13_seasonal_adjust filename divergence (n=3 third-observation reinforcement):** audit filename `p3_x13_audit.md` + harness filename `p3_x13.py` omit `_seasonal_adjust` suffix from catalog-id `x13_seasonal_adjust`; engine filename `x13_seasonal_adjust.py` preserves catalog-id. Trigger shorthand `p3_x13_seasonal_adjust_*` reference informational only per A6 informational surface framing. n=3 third-observation reinforcement at Block 3 completion provides codification-ready candidate per A3 precedent.

**Filename divergence sub-pattern variant characterization:**

- **Block-specific scope:** sub-pattern observed at Block 3 Decomposition (4 entries) wrapper filenames; cross-block extension scope at S37+ FIFTH catalog block transition empirically unknown (would require empirical observation across additional Blocks)
- **Filename component pattern:** audit + harness filenames omit catalog-id suffix component (`_decompose` at mstl/stl; `_seasonal_adjust` at x13); engine filenames preserve catalog-id; trigger shorthand references propagate suffix-omitted form per A6 informational surface
- **A6 informational surface framing:** filename divergence is naming convention shorthand vs material content misattribution distinction; A6 BLOCKING discipline operating as designed at empirical re-Read per S32 + S33 + S34 Step 0 ratifications; NOT A9 Class A counter increment per naming shorthand vs material content distinction
- **Sub-pattern variant operational implication:** Block-specific naming convention divergence requires empirical verification at trigger-execution Step 0 per S32 + S33 + S34 lessons; trigger shorthand `p3_<technique>_*` reference informational only at Block 3 Decomposition scope

**A3 third-observation tightening reinforcement at n=3 + Block 3 completion** provides codification-ready candidate per Chat Decision 3 (α) codification at S36 Workstream B amendment cycle. Codification placement disposition: §1.9 NEW Workstream B sub-section per Decision 6 §1.7+ §1.8+ §1.9 continuation per S30 §1.5+ §1.6 precedent.

**Forward instrumentation:** fourth filename divergence sub-pattern variant observation at S37+ Q1 entry (FIFTH catalog block transition) would tighten pattern characterization per A3 design-class precedent; cross-block extension empirical surface at next catalog block. Sub-pattern variant scope expansion candidate (e.g., Block-specific vs cross-block scope refinement) at Workstream B amendment cycle disposition based on n=4+ observation across next catalog block.

**Cross-references:**
- S32 mstl_decompose §2.5 entry (tsl_trust_inventory_techniques.md) — first filename divergence observation
- S33 stl_decompose §2.5 entry (tsl_trust_inventory_techniques.md) — second filename divergence observation (n=2 baseline)
- S34 x13_seasonal_adjust §2.5 entry (tsl_trust_inventory_techniques.md) — third filename divergence observation (n=3 third-observation reinforcement)
- A6 verify-state-at-narration BLOCKING (sub-pattern variant operates within A6 informational surface framing; NOT A9 Class A counter increment per naming shorthand distinction)
- §1.7 (b) refined Mod 3 chunked-surface content-completeness specification (cross-reference for empirical re-Read discipline at Step 0 trigger-execution-time)

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

### §2.5 Tier primary+overlay framing convention (NEW at S30 Workstream B amendment cycle per Candidate H codification; A3 second-observation tightening precedent threshold satisfied at n=2 empirical observations S23 + S28)

Per Workstream B amendment cycle separate-lane Candidate H surfaced at S28 close banking + S29-absorption #4 candidate inventory; codified at this artifact per S30 Workstream B amendment cycle.

**Pattern observation:** Q1 §2.5 entries where empirical Tier characterization spans MULTIPLE codified Tier definitions can adopt primary+overlay framing convention: primary Tier characterization + secondary Tier overlay characterization. Convention emerged at S23 pp_test first-instance and reinforced at S28 kalman_imputation second observation per A3 precedent.

**Empirical observations (n=2 empirical baseline; codification-stable per A3 second-observation tightening precedent):**

**Observation 1 — S23 pp_test (first-instance precedent):** Tier characterization at "Tier II.bit-exact-loose + Tier V Pattern J B.2 overlay":
- Primary: Tier II.bit-exact-loose per closed_form tolerance class + abs diff 2.09e-06 within ladder accommodating Pattern J widening
- Overlay: Tier V Pattern J B.2 (internal-default divergence per scope_reframing §2 line 176-177) per audit Pattern J observation
- Overlay treatment per scope_reframing §2 line 236-237 ("distributed across other tiers as overlay")
- Empirical structure surfaces dual-tier characterization where verdict_class semantic AND Pattern J widening accommodation both apply

**Observation 2 — S28 kalman_imputation (second observation; codification-stable per A3 precedent):** Tier characterization at "Tier II.mle-band primary + Pattern A conditional-on-MLE-alignment overlay":
- Primary: Tier II.mle-band per verdict_class "mle_fit" + MLE-fit-band tolerance scope per scope_reframing §2 lines 134-137
- Overlay: Pattern A conditional-on-MLE-alignment per p3_batch_5_summary Pattern A characterization + phase3_cross_batch_findings cross-batch Pattern A list
- Empirical structure surfaces dual-tier characterization where verdict_class semantic AND Pattern A regime alignment both apply
- Analogous structural framing to S23 (primary tier + overlay characterization); A3 second-observation tightening precedent satisfied

**Convention codification (per n=2 observation tightening):**

- **Primary tier characterization:** dominant Tier classification per scope_reframing §2 definitional scope (Tier II.bit-exact / Tier II.mle-band / Tier III / Tier IV / etc.); empirically grounded at verdict_class semantic OR audit verdict structural classification
- **Overlay tier characterization:** secondary Tier (Tier V Pattern J variant OR Pattern A regime characterization OR analogous) per audit-content-distribution OR cross-batch findings OR scope_reframing §2 line 236-237 overlay permission
- **Cross-reference structure:** primary+overlay framing codified at Tier line + Validation claim scope + 4 disclosure templates + Q-A + Q-D; cross-reference scope_reframing §2 line(s) for primary AND overlay characterization
- **A3 second-observation tightening precedent satisfied at n=2;** third primary+overlay observation at S31+ Q1 entry tightens convention per A3 precedent

**Forward instrumentation:** third primary+overlay observation at S31+ Q1 entry would extend convention codification with additional empirical examples + potential sub-class variant emergence (novel primary+overlay combinations beyond Tier II.bit-exact-loose + Pattern J B.2 + Tier II.mle-band + Pattern A as observed at S23 + S28). Convention refinement candidate at Workstream B amendment cycle if pattern shifts.

**Cross-references:**
- scope_reframing §2 line 236-237 (Tier V overlay permission: "distributed across other tiers as overlay")
- scope_reframing §2 line 176-177 (Pattern J B.2 sub-class: internal-default divergence; p3_egarch exemplar)
- scope_reframing §2 lines 134-137 (Tier II.mle-band definitional scope)
- S23 pp_test §2.5 entry (tsl_trust_inventory_techniques.md) — first-instance primary+overlay precedent
- S28 kalman_imputation §2.5 entry — second-observation primary+overlay precedent

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

### §4.6 Option II workflow

Per §19.4 forward instrumentation note "Option II workflow
codification" deferred from S16-absorption + S19-absorption absorption
cycles per structural belonging at Workstream B §1 + §4 (Option II
operationalizes verify-state-at-narration discipline at trigger-
execution-time empirical re-Read). Codified at this artifact per
S20 Workstream B amendment cycle.

**Workflow operational protocol (4-stage):**

1. **Chat trigger drafts under Code Step 0 empirical re-Read
   expectation:** Chat trigger surfaces directives + scope expectations
   under operational assumption that Code performs Step 0 empirical
   re-Read at trigger-execution time. Chat trigger drafting does NOT
   assume Chat-side baseline-state assertion correctness; relies on
   Code Step 0 to catch divergence.
2. **Code Step 0 empirical re-Read at trigger-execution time per
   CONSTRAINT 4 BLOCKING:** Code reads authoritative source artifacts
   at HEAD before any drafting/editing action. Step 0 scope per
   sub-session class. Verbatim citations from source artifacts; no
   propagation of Chat-side assumptions.
3. **STOP 2 mandatory if divergence surfaces:** if Step 0 surfaces
   empirical divergence from Chat trigger framing assumptions (A9
   Class A baseline-state or A9 Class B empirical-complexity
   sub-classes), Code STOPs immediately and surfaces findings + 3+
   disposition options to Chat. Code does NOT proceed to drafting
   under wrong framing.
4. **Chat re-disposition trigger ratifies correct framing; Code
   proceeds under corrected scope:** Chat reviews STOP 2 findings +
   disposition options; selects framing class; ratifies for
   re-activation. Code proceeds under ratified framing with Step 0
   findings already grounded.

**Workflow operates as primary structural mitigation** for A9 Class A
(Chat-trigger baseline-state assertion failure) + Class B (Chat-
trigger empirical-complexity assumption failure) sub-classes per
§19.4 codification. Trigger-drafting-time discipline (Chat-side
empirical re-Read at trigger drafting) is NOT required when Option
II workflow operates correctly; Code Step 0 re-Read provides
equivalent mitigation at trigger-execution time.

**Empirical validation across sub-sessions:**

| Sub-session | Empirical context | Option II outcome |
|---|---|---|
| S13 cross_correlation_lag | first multi-map two-layer (Tier II.bit-exact) | clean Step 0 match; entry drafted under ratified framing |
| S14a investigation | harness-vs-engine code path divergence at p3_ccf scope | Step 0 + Step 5 contextual sampling surfaced outlier |
| S14b coordinated amendment | 2-entry amendment | clean Step 0 match; amendments drafted under ratified framing |
| S14c prewhitened_ccf_lag | three-layer-upstream | clean Step 0 match |
| S15 rolling_ccf_lag | two-layer assumption falsified at Step 0 | STOP 2 triggered; α three-layer-downstream ratified; A9 Class B 1st instance |
| S17 dtw_alignment_lag | 1:1 simple-case assumption falsified at Step 0 | STOP 2 triggered; α three-layer-downstream ratified; A9 Class B 2nd instance |
| S18 gcc_phat_delay | Tier II.bit-exact assumption falsified at Step 0 | STOP 2 triggered; β Tier IV three-layer-downstream ratified; A9 Class A 5th instance |
| S11 pre-STOP-1 | A5 schema misattribution catch | pre-STOP-1 caught Class A 2nd instance |
| S12 Step 0 | granger_causality entry presupposition | Step 0 caught Class A 3rd instance |
| S16-absorption pre-STOP-1 | A5 schema misattribution recurrence | pre-STOP-1 caught Class A 4th instance |
| S19-absorption Step 0 | no divergence (revised default operating) | clean Step 0 match per Class B revised default |

**Cross-references:**
- §19.4 A9 Class A + Class B failure modes (Option II workflow is
  primary structural mitigation; cross-codified at A9 sub-class
  refinement per S19-absorption)
- §19.4 forward instrumentation note "Option II workflow codification"
  at calibration_baseline.md (cross-reference preserved at §19.4
  historical audit trail; status update to "codified at Workstream B
  §4.6" deferred to next §19.4 absorption cycle)
- §4.4 Operational application protocol (Option II operationalizes
  verify-state-at-narration at trigger-execution time; complements
  §4.4 narration-time application)
- §4.5 Forward codification path (verify-state-at-first-consumption
  sub-discipline at A6 codifies synthesis-claim refinement; §4.6
  Option II workflow operationalizes trigger-drafting-vs-trigger-
  execution discipline boundary)
- §1.1 Q-A (Step 0 empirical re-Read is Q-A foundation; Option II
  workflow ensures Q-A is empirically grounded rather than asserted)

**Forward instrumentation:** workflow performance metric observation
candidates: (a) STOP 2 catch rate (proportion of sub-sessions where
Step 0 surfaces divergence; currently ~50% across Q1 entries); (b)
Chat re-disposition cycle time (1 cycle per STOP 2 currently); (c)
LOC overshoot rate (variable per framing complexity). Codification
refinement at empirical metric accumulation per A3 design-class
precedent.

### §4.7 Forward Q1 Step 0 discipline — harness-vs-engine pattern observations (dual-pattern codification REFINED at S30 Workstream B amendment cycle per Candidate G.1 generalized definitional scope per A10 Sub-class 2e codification alignment at S29-absorption #4: §4.7.A harness-uses-different-code-path-from-engine (reimplementation + use-case-divergence variants) + §4.7.B engine-extends-beyond-harness with sub-scale variant taxonomy per Candidate G.2)

Per §19.4 forward instrumentation note "Forward Q1 Step 0 discipline"
deferred from S16-absorption + S19-absorption absorption cycles per
codification threshold reached at n=2 informal observations per A3
design-class precedent. Codified at this artifact per S20 Workstream B
amendment cycle.

**Discipline shape:** Step 0 sub-step for techniques where harness-
vs-engine code path alignment matters for layered framing
characterization. TWO empirical questions requiring verification at
Step 0: (i) does the harness wrapper invoke the same code path as
the engine module's main computation? (harness-bypasses-engine
pattern); (ii) does the engine module extend beyond what harness
exercises, and if so at what scale? (engine-extends-beyond-harness
pattern). Patterns are operationally distinct (different mitigation
surfaces) and concurrently operative (a single technique may exhibit
both — e.g., S23 pp_test exhibits engine-uses-same-function Layer 1
alignment AND backend-dispatcher engine extension beyond harness
fixed-implementation invocation).

#### §4.7.A Harness-uses-different-code-path-from-engine pattern (REFINED at S30 Workstream B amendment cycle per Candidate G.1 generalized definitional scope per A10 Sub-class 2e codification alignment at S29-absorption #4; n=4 observations across structural mechanism variants: harness-bypasses-engine + harness-reimplements-engine-math + harness-validates-different-use-case-of-same-library-function)

**Generalized definitional scope (REFINED at S30 per A10 Sub-class 2e codification alignment at S29-absorption #4):** §4.7.A pattern definitional scope generalizes from "harness-bypasses-engine" (S25 codification baseline) to "harness-uses-different-code-path-from-engine" — covering all structural mechanisms where harness validates DIFFERENT code path than engine module's primary computation, regardless of bypass mechanism. Generalized scope covers:

1. **Harness-imports-library-directly variant** (S14a p3_ccf): harness imports library function directly while engine module uses custom implementation
2. **Harness-defines-internal-reference-function variant** (S18 p3_gcc_phat): harness defines harness-internal reference function while engine module is materially more complex
3. **Harness-reimplements-engine-math variant** (S26 p3_denton_chowlin): harness REIMPLEMENTS engine math directly (numpy KKT vs engine `_denton_proportional`); SAME use case, DIFFERENT code paths
4. **Harness-validates-different-use-case-of-same-library-function variant** (S27 p3_loess): harness AND engine import SAME library function BUT use for DIFFERENT purposes (harness: smoothing self-parity; engine: interpolation of missing values)

**REMEDIATED 5th variant status dimension extension (NEW at S36 Workstream B amendment cycle per Decision 2 (α); orthogonal to mechanism variant dimension per S30 (G.1) generalized definitional scope codification):**

§4.7.A pattern operates across TWO orthogonal dimensions per S36 Workstream B amendment cycle refinement:

- **Mechanism variant dimension (codified at S30; n=4 variants):** characterizes HOW harness uses different code path from engine — variants 1-4 above (harness-imports-library-directly + harness-defines-internal-reference-function + harness-reimplements-engine-math + harness-validates-different-use-case-of-same-library-function)
- **Status dimension (NEW at S36 per Decision 2 (α)):** characterizes WHETHER §4.7.A pattern is currently PRESENT (active divergence) vs REMEDIATED (divergence remediated via harness modification to invoke engine module directly via dispatch entry); status dimension applies orthogonally across all mechanism variants

**Status dimension values (n=2 codified at S36):**

- **PRESENT status (n=7 observations across §2.5 entries post-S35):** S14a granger + S18 gcc_phat + S26 denton_chowlin + S27 loess + S31 classical_decompose + S32 mstl_decompose + S33 stl_decompose — harness uses different code path from engine; §4.7.A pattern actively manifesting at HEAD verification time
- **REMEDIATED status (n=1 first-instance baseline observation at S34 x13_seasonal_adjust per S35-absorption #5 codification):** harness was previously §4.7.A PRESENT (pre-Phase 4 Session 2 2026-05-01); REMEDIATED via Phase 4 Session 2 (P4-2 pathway (c) closure) when ``run_tsl`` was modified to invoke ``engine/techniques/x13_seasonal_adjust.py:run`` directly via dispatch entry rather than calling ``statsmodels.x13_arima_analysis`` directly; per harness ``p3_x13.py`` docstring lines 9-30 verbatim documentation of P4-2 closure mechanism; A3 first-instance precedent n=1 baseline; NOT codification-stable

**REMEDIATED status dimension definitional scope:** §4.7.A REMEDIATED status indicates harness has been modified to invoke engine module ``run()`` entry point directly via dispatch (eliminating §4.7.A code-path divergence at runtime) while retaining historical mechanism variant characterization (the REMEDIATION addresses the code-path divergence but the mechanism variant historical observation remains accurate per HEAD state preservation). REMEDIATED status is NOT a new mechanism variant; it is a status dimension orthogonal to mechanism variant dimension — a wrapper may be REMEDIATED at status dimension AND classified at any of mechanism variants 1-4 at mechanism variant dimension per historical pre-REMEDIATION characterization.

**Empirical evidence (S34 x13_seasonal_adjust first-instance baseline observation per S35-absorption #5):**
- Harness `tools/reference_parity/harness/checks/p3_x13.py` docstring lines 9-30 verbatim: "**Phase 4 Session 2 (2026-05-01) — P4-2 pathway (c) closure:** ``run_tsl`` now invokes TSL's actual wrapper (``engine/techniques/x13_seasonal_adjust.py:run``) via the dispatch entry point rather than calling ``statsmodels.x13_arima_analysis`` directly. The pre-S2 implementation called statsmodels because it produced the seasadj+trend output in a single library call; that path fails on Linux CI because statsmodels' temp-file naming convention is incompatible with the ``x13ashtml`` binary's output convention. TSL's wrapper does direct binary invocation + .d10/.d11/.d12/.d13 parsing, which is fully x13ashtml-compatible. Linux CI now PASSes ``p3_x13`` (was SKIP-graceful). Windows CI behavior unchanged — the wrapper still SKIPs gracefully via ImportError when no binary is found locally."
- Harness `p3_x13.py` line 89 verbatim: `from techniques.x13_seasonal_adjust import run as tsl_x13_run`
- Harness `p3_x13.py` line 125 verbatim: `res = tsl_x13_run(ctx, lambda *a, **k: None)`

**Mechanism variant classification at S34 x13_seasonal_adjust (pre-REMEDIATION historical characterization):** Pre-Phase 4 Session 2 (pre-2026-05-01), §4.7.A PRESENT at variant 1 "Harness-imports-library-directly" (harness imported `statsmodels.tsa.x13.x13_arima_analysis` directly while engine module `engine/techniques/x13_seasonal_adjust.py` did direct binary invocation + .d10/.d11/.d12/.d13 parsing). Post-Phase 4 Session 2, status dimension transitions PRESENT → REMEDIATED while mechanism variant 1 historical characterization preserved at pre-REMEDIATION reference per HEAD state preservation.

**Forward instrumentation:** second REMEDIATED status observation at S37+ Q1 entry would tighten REMEDIATED status dimension codification per A3 second-observation tightening precedent (n=2 codification-stable threshold). Codification refinement candidate at next Workstream B amendment cycle if (a) second REMEDIATION instance surfaces OR (b) REMEDIATION mechanism varies (e.g., REMEDIATED via mechanism other than dispatch-entry invocation; alternative remediation patterns).

**§19.4 cross-reference disambiguation (Class A counter scope vs status dimension scope):** A9 Class A counter scope at §19.4 covers Chat-trigger empirical-state-assumption failure mode (Class A counter currently n=14 ACTIVE post-S35-absorption #5); REMEDIATED status dimension at §4.7.A scope covers wrapper code-path divergence remediation status (n=1 first-instance baseline observation at S34 x13). Distinct empirical phenomena; cross-reference disambiguation preserves apparatus location scope discipline per §19.4 vs Workstream B codification separation.

**Cross-class alignment per A10 Sub-class 2e codification at S29-absorption #4:** Sub-class 2e (αa) reimplementation variant (S26) + (αb) use-case-divergence variant (S27) at A10 Sub-class taxonomy aligns with §4.7.A variants 3 + 4 at Workstream B §4.7.A operational discipline scope. Both apparatus locations (§19.4 A10 + Workstream B §4.7.A) characterize same empirical phenomenon at different abstraction levels: A10 = sub-session class taxonomy; §4.7.A = operational discipline structural mechanism. Generalized definitional scope at S30 codification removes cross-class label divergence (S25 §4.7.A "harness-bypasses-engine" semantic narrower than A10 Sub-class 2e generalized scope; S30 refinement aligns labels).

**Historical S25 codification baseline (preserved per R3 audit trail):**

**Empirical observations:**

**Observation 1 — S14a Step 5 contextual sampling (p3_ccf outlier):**
4 of 5 sampled harnesses (p3_kpss + p3_adf + p3_var + p3_granger
sample) follow clean engine-uses-same-function convention (harness
invokes the same statsmodels function the engine module uses).
**p3_ccf is outlier:** harness validates `statsmodels.tsa.stattools.ccf`
while engine modules (cross_correlation_lag, prewhitened_ccf_lag,
rolling_ccf_lag) use custom numpy CCF implementation. Surfaced as
S14a investigation outcome; informed S14b layered framing amendment
+ S14c + S15 three-layer framing for p3_ccf-covered triple.

**Observation 2 — S18 Step 0 (p3_gcc_phat second observation):**
p3_gcc_phat harness defines own `_gcc_phat` reference function inside
p3_gcc_phat.py (literal-identity self-parity; both run_tsl and
run_reference call same harness-internal `_gcc_phat`). Harness comment
"mirrors TSL's custom impl" but engine module 386 LOC is materially
more complex than harness's 12-LOC `_gcc_phat` (engine has 4 weighting
variants + interpolation + zero-mean normalization + 6 post-processing
sub-components vs harness's plain Knapp-Carter 1976 formula). Harness-
bypasses-engine pattern recurring at second observation.

**Pattern characterization:** harness-bypasses-engine pattern
operates via multiple structural mechanisms:
- Harness imports library function directly (e.g., p3_ccf imports
  statsmodels.ccf) while engine module uses custom implementation
- Harness defines harness-internal reference function (e.g., p3_dtw
  + p3_gcc_phat define `_dtw_distance` / `_gcc_phat` inside harness
  file) while engine module is materially more complex
- Combinations of above

Alignment between harness and engine code paths is empirical question
requiring Step 0 verification per technique; cannot be inferred from
audit Reference field or wrapper engine path citation alone.

#### §4.7.B Engine-extends-beyond-harness pattern (REFINED at S30 Workstream B amendment cycle per Candidate G.2 sub-scale variant taxonomy codification; n=5 observations across sub-scale variants: Layer 2 orchestration + Layer 2 method-extension + Layer 1E use-case-extension; codification triad EMPIRICALLY COMPLETE at n=3 base layers extended with sub-scale variants per S25+S26+S27 observations)

**Sub-scale variant taxonomy (NEW codification at S30 Workstream B amendment cycle per Candidate G.2):**

Engine-extends-beyond-harness pattern operates at multiple sub-scales within Layer characterization (Layer 1 / Layer 2 / Layer 3); sub-scale variant taxonomy distinguishes operational granularity within Layer base categorization:

- **Layer 2 orchestration sub-scale (S21 + S22 + S23 triad baseline; codified at S25):** engine extends Layer 2 beyond harness via orchestration only (allowlist gating + NaN handling + per-series loop + significance disclosure + interpretation); no NEW math function added at Layer 1E (engine uses same Layer 1 math function as harness)
- **Layer 2 method-extension sub-scale (S26 denton_chowlin variant; NEW codification per S30):** engine extends Layer 2 via NEW math function addition (engine `_chowlin` Chow-Lin GLS regression + `_estimate_rho` ML grid search alongside Denton method); engine adds Layer 1E math function NOT in harness audit scope; Layer 2 method dispatch (allowlist + selection) added orchestration
- **Layer 1E use-case-extension sub-scale (S27 loess_interpolation variant; NEW codification per S30):** engine extends Layer 1E use case of SAME library function (statsmodels.lowess) from harness audit scope (smoothing self-parity) to NEW use case (interpolation of missing values); no NEW math function added (same library function); use case divergence with associated Layer 2 orchestration scope expansion

**Empirical sub-scale variant distribution (n=5 observations across 3 sub-scales):**
- Layer 2 orchestration sub-scale: n=3 (S21 + S22 + S23 triad)
- Layer 2 method-extension sub-scale: n=1 (S26 denton_chowlin Chow-Lin extension)
- Layer 1E use-case-extension sub-scale: n=1 (S27 loess_interpolation smoothing-to-interpolation extension)

**Forward instrumentation (UPDATED at S30):**
- Codification refinement triad EMPIRICALLY COMPLETE at n=3 Layer scales (Layer 1 / Layer 2 / Layer 3) per A3 second-observation tightening precedent threshold satisfied at S26+S27 sub-scale variant codification
- Sub-scale variant taxonomy tightens at second observation per sub-scale: Layer 2 method-extension second observation at S31+ Q1 entry; Layer 1E use-case-extension second observation at S31+ Q1 entry
- Cross-class alignment with A10 Sub-class taxonomy at §19.4 codification per S30 Candidate G refinement scope (G.1 generalized §4.7.A + G.2 §4.7.B sub-scale variant taxonomy)

**Historical S25 codification baseline (preserved per R3 audit trail):**

**Discipline shape (Pattern 2-specific):** engine module uses SAME
underlying function/library as harness validates at Layer 1 math
(clean engine-uses-same-function convention; distinct from §4.7.A
harness-bypasses-engine pattern) AND extends substantially beyond
harness invocation scope via additional engine-specific computation
layers. Empirical question requiring verification at Step 0: when
engine uses same Layer 1 math function as harness, at what scale
does engine extend beyond harness exercise (Layer 1 / Layer 2 /
Layer 3)?

**Empirical observations (n=3 triad; codification EMPIRICALLY
COMPLETE at A3 second-observation tightening precedent threshold):**

**Observation 1 — S21 Layer 3 extension scale (adf_test):** Engine
module `engine/techniques/adf_test.py` uses SAME
`statsmodels.tsa.stattools.adfuller` function harness validates at
Layer 1 math (clean engine-uses-same-function pattern). Engine
extends DRAMATICALLY beyond harness via Layer 3 joint triage sub-
system (`_run_triage` lines 506-714 + `_joint_verdict` lines 200-228
+ PP tie-breaker lines 559-565); entirely new computational sub-
system invoking parallel KPSS + PP test invocations + computing
four-outcome verdict heuristic. Layer 3 NOT exercised by harness;
engine-specific operational distinctive drives adf_test ribbon-
default publication output per `_is_triage_mode` dispatch.

**Observation 2 — S22 Layer 2 extension scale (kpss_test):** Engine
module `engine/techniques/kpss_test.py` uses SAME
`statsmodels.tsa.stattools.kpss` function harness validates at Layer
1 math. Engine extends MODERATELY beyond harness via Layer 2
orchestration only (regression/nlags allowlist gating per CAI Phase
2 Session 17 fix + NaN handling via `_prepare_series` + per-series
loop + significance disclosure + interpretation); NO Layer 3 of its
own (joint triage mode is OWNED BY adf_test.py NOT kpss_test.py).
Engine module dual-role: standalone-technique role + helper-export
role via `_run_kpss_single` to adf_test triage Layer 3 sub-component
3b.

**Observation 3 — S23 Layer 1 backend-dispatcher extension scale
(pp_test):** Engine module `engine/techniques/pp_test.py` uses SAME
`arch.unitroot.PhillipsPerron` function harness validates at base
config (audit-time backend was arch path). Engine extends Layer 1
dimension via BACKEND-DISPATCHER variant — 3-tier fallback chain
across THREE underlying library implementations
(statsmodels.tsa.stattools.phillips_perron → arch.unitroot.PhillipsPerron
→ `_manual_pp` 64 LOC Newey-West Bartlett kernel implementation);
harness validates arch path specifically; statsmodels-path +
manual-path NOT audit-validated. Engine module triple-role:
standalone-technique role + helper-export to adf_test triage 3b
parallel-test invocation + helper-export to adf_test triage 3d
CONFLICTING tie-breaker.

**Pattern characterization (scale-of-extension variation across
Layer 1 / Layer 2 / Layer 3):** engine-extends-beyond-harness
pattern operates with three operationally distinct scale-of-
extension variations:
- **Layer 3 extension scale (S21 adf_test):** DRAMATIC extension via
  entirely new computational sub-system (joint triage parallel-tests
  + verdict heuristic + tie-breaker logic); engine-specific Layer 3
  computation NOT exercised by harness; ribbon publication output
  drives Layer 3 publication context
- **Layer 2 extension scale (S22 kpss_test):** MODERATE extension
  via orchestration only (allowlist gating + NaN handling + per-
  series loop + significance disclosure + interpretation); engine
  Layer 2 NOT parity-validated; helper-export coupling extends
  retraction surface to adf_test triage publication context
- **Layer 1 backend-dispatcher extension scale (S23 pp_test):**
  BACKEND-DISPATCHER variant via fallback chain across underlying
  implementations; engine Layer 1 alternative paths NOT audit-
  validated (statsmodels-path + manual-path); runtime backend
  selection drives published output; helper-export triple-role
  coupling extends retraction surface to adf_test triage at TWO
  sub-component coupling points (3b + 3d)

**Pattern characterization sub-observation (orthogonal axis to scale-
of-extension; forward observation NOT load-bearing claim at n=3
codification baseline):** helper-export-role-presence is empirically
orthogonal to scale-of-extension at n=3 observations. Layer 3
extension (S21 adf_test) is the CONSUMER of helper-exports from
Layer 2 + Layer 1 engines (Sub-class 2d cross-class coupling per
§19.4 A10 codification); Layer 2 (S22 kpss_test) is dual-role
helper-export to Layer 3 consumer; Layer 1 (S23 pp_test) is triple-
role helper-export to Layer 3 consumer at TWO sub-component coupling
points (3b + 3d). Helper-export-role-presence + role-count (none /
dual / triple) operates as orthogonal characterization axis to
scale-of-extension; informs Q-D retraction surface compounding per
S23 pp_test entry MEDIUM-HIGH-CRITICAL triple-role compounding
observation. Forward instrumentation: if S26+ surfaces engine-
extends-beyond-harness observation at any Layer scale WITHOUT
helper-export role, axis decoupling confirms; if pattern only
observes WITH helper-export role at Q1 entries, axes may be
empirically correlated rather than orthogonal. Per Previous Chat
1.4 walkback honest mark: "Helper-export-role-presence is better
candidate variable than Layer-scale-of-extension" — surfaced as
forward observation pending S26+ empirical disambiguation; NOT
elevated to load-bearing variable at S25 codification baseline.

#### §4.7.C Operational application (Q1 sub-session Step 0 sub-step; both patterns)

For each Q1 technique under layered framing characterization, Step
0 verifies (acknowledging step lettering convention varies across
sub-sessions per Step 0 scope; (e)/(f)/(g) reference below is
canonical-convention placeholder for audit + harness + engine sub-
steps per S15-S22 §2.5 entry precedent; S23 + S23-pre + S24+ apply
variant lettering per per-sub-session Step 0 scope): audit reference
+ verdict + numerics (canonical (e)); harness wrapper run_tsl +
run_reference code paths (canonical (f); specific to §4.7.A harness-
bypasses-engine alignment verification); engine module computation
+ post-processing complexity (canonical (g); specific to §4.7.B
engine-extends-beyond-harness alignment verification). Canonical
(f) specifically establishes harness code path; canonical (g)
specifically establishes engine extension scale; comparison against
canonical (g) engine code path surfaces alignment OR divergence per
BOTH patterns concurrently. Divergence informs layered framing
class determination (single-layer applies only when harness invokes
same code path as engine AND engine does NOT extend substantially
beyond harness; layered framing applies otherwise per A9 Class B
revised default discipline).

#### §4.7.D Cross-references (dual-pattern; both §4.7.A + §4.7.B)

- §1.1 Q-A (Step 0 empirical re-Read is Q-A foundation; harness-vs-
  engine alignment AND engine-extends-beyond-harness scale are both
  Q-A sub-questions)
- §4.6 Option II workflow (Step 0 (f)/(g) harness-vs-engine
  alignment + engine-extends-beyond-harness scale verification are
  operational steps within Option II Step 0 empirical re-Read)
- §19.4 A9 Class A + Class B failure modes (harness-vs-engine
  alignment + engine-extends-beyond-harness verification are
  mitigation surfaces for Class B empirical-complexity assumption
  failures)
- §19.4 forward instrumentation note "Forward Q1 Step 0 discipline"
  at calibration_baseline.md (cross-reference preserved at §19.4
  historical audit trail; status update to "codified at Workstream B
  §4.7" deferred to next §19.4 absorption cycle)
- §19.4 §4 forward instrumentation note 6 Block 1 + Block 12 milestone
  refinement at S24-absorption (per-block continuation pattern at
  n=2 catalog block observations; per-entry LOC elevation reflects
  novelty enumeration + triple-role + dual-tier framing scope)

#### §4.7.E Forward instrumentation (updated at S25 Workstream B amendment cycle)

**§4.7.A Harness-bypasses-engine pattern forward instrumentation:**
codification refinement candidate at third analogous outlier
observation per A3 design-class precedent. Refinement markers: (a)
third outlier pattern surfacing; (b) pattern variant surfacing (new
harness-vs-engine alignment failure mode not anticipated by n=2
baseline); (c) codification of harness-engine alignment as gate
rather than Step 0 sub-step if pattern materially affects publication
confidence.

**§4.7.B Engine-extends-beyond-harness pattern forward instrumentation
(NEW at S25):** codification refinement triad EMPIRICALLY COMPLETE
at n=3 observations per A3 second-observation tightening precedent
threshold satisfied (Layer 1 backend-dispatcher S23 + Layer 2 S22 +
Layer 3 S21). Refinement markers for next codification cycle: (a)
fourth Layer-scale-variation observation surfacing (e.g., NEW Layer
0 extension scale or Layer 4 extension scale at S26+ Q1 entries);
(b) pattern interaction with §4.7.A harness-bypasses-engine pattern
(e.g., technique exhibiting BOTH patterns surfaces compound
operational distinctive); (c) codification of engine-extends-beyond-
harness scale-of-extension variation as Tier characterization
sub-class candidate (analogous to scope_reframing §2 Tier II split
precedent at S9 in-place §2 amendment).

**Pattern relationship (NEW at S25):** §4.7.A + §4.7.B are
operationally distinct patterns; technique may exhibit ONE pattern
only, BOTH patterns concurrently, or NEITHER pattern (clean engine-
uses-same-function with no Layer 2/3 extension). Step 0 sub-step
verifies both patterns concurrently; mitigation surface differs per
pattern: §4.7.A mitigation = layered framing class determination at
Step 0 disposition; §4.7.B mitigation = scale-of-extension
disclosure at Q-A bullet + Q-D retraction surface compounding
characterization. Discipline maturation observation cross-reference:
A9 Class A + B reactive-catch → proactive-prevention shift codified
at §19.4 §4 forward instrumentation note 7 at S24-absorption;
applies symmetrically across both §4.7 pattern observation timing
points; second-observation tightening confirmed at S25 Workstream B
amendment cycle Step 0 anchors empirically CONFIRMED per CHAT
RATIFICATION #8 disposition.

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

### §5.4 Operational permission grants — β grant scope discipline (NEW at S25 Workstream B amendment cycle per Candidate D bounded β grant disposition)

**Codification scope distinction from Mark 1/2/3:** §5.1 Mark 1 +
§5.2 Mark 2 + §5.3 Mark 3 codify operating-context preservation
observations (empirical preservations that emerged at Phase 5/Phase
6+ work program). §5.4 codifies operational permission grant scope
discipline; NOT a "Mark 4" candidate per S24-absorption discipline
maturation observation framing distinction (institutional discipline
observation vs operating-context preservation). β grant is a
specific operational permission (harness allowing direct push to
master bypassing PR review) with scope-aware ratification discipline.

**β grant operational origin:** Phase 7+ S21-push sub-session
surfaced harness gate denial on `git push origin master` ("Push to
master (default branch) bypasses pull request review"). Chat
ratified (β) grant per S21-push trigger Step 1 disposition; granted
direct-push permission active for S21+ commits. Empirical operation:
S21 + S22 + S23 + S24-absorption commits all pushed direct to master
under β grant operative without re-ratification.

**β grant scope-tightening (codified at S25 per Candidate D bounded
β grant disposition):** β grant scope is **bounded to Phase 7+ Q1
work program**. Revocation triggers (either-or):
- Phase 7+ Q1 work program close (work program completion event;
  empirical milestone; absorption #N if applicable)
- Path α expert review handoff (work program transition event;
  empirical milestone)

Either trigger event occurs → β grant scope expires → next
direct-push attempt requires fresh ratification (e.g., extending
grant to Q2 OR Q3 OR Q3b scope per work program continuation; OR
transitioning to PR-review workflow per institutional standard at
Path α close).

**Operational implications during bounded scope (S21-current
operative; will remain operative through Phase 7+ Q1 close):**
- Direct push to master permitted for Phase 7+ Q1 work program
  commits (per-technique §2.5 entries + §19.4 absorption commits +
  Workstream B amendment cycle commits + Q1 work program close
  artifact commits if applicable)
- No re-ratification per commit; β grant operative as standing
  permission during bounded scope
- Scope boundary at Q1 close: fresh Chat ratification required for
  Q2 / Q3 / Q3b / Path α handoff direct-push permissions if
  operational continuity warrants

**Forward instrumentation:** β grant scope-tightening codification
serves Path α expert review preparation discipline + multi-cycle
work program operational hygiene. If Phase 7+ work program extends
beyond Q1 without explicit Q1-close ratification event, β grant
implicit-extension risk surfaces — operational discipline candidate
for re-ratification trigger codification at S26+ if Q2/Q3 work
program activates without explicit Q1 close. Revocation event
codification candidate at A11 NEW amendment OR §19.4 absorption
#4+ if operational permission scope discipline warrants amendment-
class status per A3 second-observation precedent.

**Cross-references:**
- S21-push sub-session β grant origin (in conversation; not
  committed; surfaced at S21-push VERIFY AT CLOSE)
- S22 + S23 + S24-absorption commits push operations (empirical
  operation under β grant operative without re-ratification)
- §1.4 Q-B operational pattern (Q-B pattern operates within bounded
  ratification scope; β grant is one operational permission scope
  within broader work program ratification discipline)
- §4 verify-state-at-narration discipline (β grant operates within
  CONSTRAINT 4 A6 BLOCKING + verify-state-at-first-consumption
  sub-discipline; grant scope-tightening preserves discipline
  operation at scope boundaries)

### §5.5 Forward-instrumentation hygiene — predictive-claim-expiration discipline (NEW at S30 Workstream B amendment cycle per Candidate E codification; extends §5.4 operating-context preservation precedent)

Per Workstream B amendment cycle separate-lane Candidate E deferred from S24-absorption NEW Finding 1 stale text removal observation + S29-absorption #4 candidate inventory; codified at this artifact per S30 Workstream B amendment cycle.

**Codification scope distinction from Mark 1/2/3 + §5.4 β grant:** §5.1 Mark 1 + §5.2 Mark 2 + §5.3 Mark 3 codify operating-context preservation observations; §5.4 codifies operational permission grant scope discipline (S25 codification); §5.5 codifies forward-instrumentation hygiene discipline — operating-context-aware narrative maintenance pattern. Discipline operates alongside Mark 1/2/3 + §5.4 within §5 "operating context preservation" semantic scope.

**Pattern observation:** Forward-instrumentation notes in §19.4 baseline + Workstream B artifact often contain predictive operational claims (e.g., "3rd instance would reinforce codification" + "second observation tightens variant baseline" + "codification candidate at next absorption cycle"). Predictive claims represent operational expectations contingent on future empirical state. When prediction is empirically settled (observation occurs OR doesn't), forward-instrumentation note text should expire OR transition to status-update characterization per R3 maintenance protocol audit trail discipline.

**Empirical observation (first-instance baseline):**

**Observation 1 — S24-absorption NEW Finding 1 stale text removal (S24-absorption codification baseline):** §19.4 A9 forward instrumentation note text "Class B pattern codified at n=2 ACTIVE; revised default assumption empirically operative; 3rd instance would reinforce codification." (S19-absorption codification) became stale at S21+S22 (Class B n=3+n=4 observations triggered "3rd instance would reinforce" prediction). NEW Finding 1 at S24-absorption codified text supersession + n=4 codification + maturation observation cross-reference. Predictive claim ("3rd instance would reinforce") expired when prediction empirically settled at S21 Class B Instance #3; text transitioned to status-update characterization at S24-absorption.

**Forward-instrumentation hygiene discipline (codified at S30):**

- **Predictive-claim-expiration triggers:** when forward-instrumentation note contains predictive operational claim AND prediction is empirically settled, note text should transition per R3 maintenance protocol audit trail discipline:
  - (i) Status update: replace predictive claim with empirical-state characterization (e.g., "3rd instance would reinforce" → "3rd instance occurred at S21; pattern reinforced at n=3")
  - (ii) Supersession: mark text SUPERSEDED + preserve per R3 audit trail + add cross-reference to current codification location (e.g., S29-absorption §4 forward instrumentation note 7 SUPERSEDED → §4.5 NEW sub-section)
  - (iii) Closure: mark text CLOSED + preserve per R3 audit trail + reference completion event (e.g., absorption cycle completion + amendment closure status)
- **Avoid stale narrative persistence:** predictive claims should NOT persist beyond empirical settlement; persistence creates downstream audit overhead at inheritor activation time + risks inheritor following stale soft-estimate as authoritative scope (analogous to A2 narrative drift sub-pattern observations)
- **Maintenance discipline operational application:** forward-instrumentation note review at absorption cycle close OR Workstream B amendment cycle close per CONSTRAINT 2 banking discipline; stale predictive claims surface during absorption candidate accumulation

**Cross-reference to A2 narrative drift sub-pattern:** §5.5 forward-instrumentation hygiene discipline shares root pattern with A2 narrative drift sub-pattern (banking entries / memory / counts diverging from empirical state via narrative-claim propagation across Chat boundaries). A2 codifies CROSS-CYCLE staleness; §5.5 codifies WITHIN-CYCLE forward-instrumentation note staleness; both operate per verify-state-at-activation protocol discipline.

**Forward instrumentation:** second predictive-claim-expiration observation at S31+ would tighten pattern per A3 second-observation tightening precedent. Codification refinement candidate at Workstream B amendment cycle if pattern surfaces additional structural variants (e.g., predictive claim expiring at non-absorption sub-session vs predictive claim transitioning to status-update across multiple absorptions).

**Cross-references:**
- §19.4 A2 amendment (narrative drift sub-pattern observations)
- §19.4 §4 maintenance protocol (R3 amendment supersession discipline)
- §5.3 Mark 3 efficient-ratification (operating-context preservation precedent)
- §5.4 operational permission grants — β grant scope discipline (S25 codification; sub-section-within-§5 precedent)
- §19.4 §4 forward instrumentation note 7 [SUPERSEDED at S29-absorption #4] (predictive-claim-expiration via supersession example)

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
