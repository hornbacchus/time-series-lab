# Phase 7+ S6 — scope re-framing: Phase 7+ work program parameters per (C) operational standard + Path α expert review + comprehensive Q3b coverage

**Date:** 2026-05-10
**Master HEAD at authoring:** `68982a3`
**Class:** novel-substantive scope-re-framing class; banking-class
artifact establishing Phase 7+ work program parameters.
**Banking locus:** establishes new `docs/reference_parity_phase7/`
directory as Phase 7+ banking locus per S6 trigger CONSTRAINT 1
+ Chat ratification 6.

## §1 Premise correction

**S8 trust inventory premise materially incorrect per S5
archaeology.** S8 framing at `docs/reference_parity_phase6/tsl_trust_inventory_techniques.md`
lines 398-402 (verbatim):

> "**Status framing for ALL entries below:** available via
> `TSL_RUN_THR("<technique_id>", …)`; **no reference parity
> validation; not currently recommended for published output
> without expert review of underlying technique implementation
> and/or extending reference-parity coverage to the technique.**"

**Empirical reality at HEAD `68982a3` per S5 archaeology:**

Phase 3 reference parity work is fully documented in formal v1.0.0
(later v1.2.0) doc-set at `docs/engineering/` per
`docs/calibration_audit_status.md` (verbatim, lines 30-43):

> "**Parity-verification discipline (Phase 3 reference-parity,
> closed at Session 18 — 2026-04-29):**
> - **P-1: Parity Standard** v1.0.0 — directive ("must");
>   binding for new wrapper PRs (parity dimension)
> - **P-2: Parity Diagnostic Reference** v1.0.0 — descriptive
>   reference / playbook (Pattern J catalog, Pattern A taxonomy,
>   structural-invariants registry, DSCD diagnostic axes)
> - **P-3: Parity Empirical Findings** v1.0.0 — descriptive
>   narrative (Phase 3 batch-execution + doc phase synthesis;
>   **70/70 wrappers covered; 0 BLOCK**)
> - **P-4: Per-Wrapper Status Tracker** v1.0.0 — authoritative
>   coverage data tracker."

P-3 v1.2.0 §1 numbers table (verbatim, `docs/engineering/parity_empirical_findings.md`
lines 41-71):

> "| Wrappers in scope (master plan §15) | 70 |
> | Wrappers covered (Phase 3 close) | **70 (100%)** |
> | BLOCK outcomes | **0** |
> | PASS verdicts | **65 (93%)** |
> | CAVEAT verdicts | 5 (7%) |
> | SKIP-graceful (Tier C runtime) | 1 |
> | Pattern A wrappers (bit-exact / near-machine-precision) | **46 (66%)** |
> | Pattern A.1 same-library sub-class | **18** (locked at scale) |
> | Pattern A.2 cross-package bit-exact | ~12 |
> | Pattern A.3 self-parity / paper-formula | ~10 |"

**Pattern characterization (S5 §5 synthesis):** systematic scope
omission at S8 trust inventory authoring time, NOT deliberate
framing-out with rationale. S8 enumeration premise (structural-
invariants dispatch allowlist = 8 wrappers + BYF dormant) was
mistakenly treated as the complete validation tier set; the
parallel Phase 3 doc-set (P-1/P-2/P-3/P-4) was not cross-walked
at S8 authoring. Scope drift across documentation areas
(`docs/engineering/` Phase 3 doc-set vs `docs/reference_parity_phase5/` +
`phase6/` Phase 5+ banking corpus); two parallel documentation
streams that weren't cross-referenced at S8 authoring time.

This is materially distinct from prior 5 A2 ESTABLISHED
observations: those were narrative-claim drift (banking entries
becoming stale; CLAUDE.md memory becoming stale; counts diverging
from empirical). The S8 omission is **scope drift** — the
validation tier set was narrowed implicitly through Phase 5/6+
scope-narrowing without explicit "what tiers exist" enumeration.

**Sixth A2 observation status:** STRENGTHENED to blocking-
checkpoint candidate per Chat ratification at S5 disposition.
Verify-state-at-narration discipline promoted from preliminary
(per S6 trigger §2 ratification) to BLOCKING for any artifact
making validation-state claims; codification at Workstream B
disposition 2 artifact pending.

## §2 Validation tier taxonomy (codification)

Per S5 archaeology + P-3 v1.2.0 §1 numbers + Pattern J / A.1 /
A.2 / A.3 distinctions documented in P-2 v1.2.0:

**Tier I — Structural-invariants dispatch validated.** 8-wrapper
allowlist (`_INVARIANTS_DISPATCH_ALLOWLIST` at `tools/reference_parity/harness/runner.py`
lines 109-118) + BYF dormant (`p3_bond_yield_forecast`
declaration). 9 catalog technique entries. Validated at structural-
invariants dispatch layer + reference parity layer.

**Tier I.partial — Phase 1/2 sub-component validated; remainder
uncovered (Phase 7+ S9 in-place §2 amendment per S8 first-
consumption empirical re-verification + Disposition 3
ratification).** Phase 1/2 wrapper validates a sub-component of
the full catalog technique; remainder of technique scope NOT
covered by parity infrastructure. Documented per technique with
both validated and unvalidated components named explicitly.

**Worked example — `bvar`:**
- **Validated:** IRF/FEVD-given-coefs (Phase 1/2 `bvar.py` audit
  `1c_bvar_irf_fevd`; Pattern A bit-exact 4.58e-16 abs per
  phase3_cross_batch_findings.md S6 Pattern A table line 20
  (S9 fresh re-Read at HEAD `5205779` verbatim); reference R
  `vars` per P-4 status tracker line 46 Phase 1 audit citation)
- **Unvalidated:** Bayesian estimation step (priors → posterior
  coefs); Q2 scope per S6 §3 + Disposition 3 ratified Q2
  estimate revision

**Cross-reference S8 first-consumption empirical re-verification
+ S9 in-place §2 amendment.**

**Tier II split into Tier II.bit-exact + Tier II.mle-band sub-
classes (Phase 7+ S9 in-place §2 amendment per S8 first-
consumption empirical re-verification + Disposition 2
ratification).** Original Tier II label deprecated. Suffix
labeling (".bit-exact" / ".mle-band") carries precision
distinction semantically; sub-classes parallel not ordinal
hierarchy.

**Tier II.bit-exact — Phase 3 cross-package bit-exact parity
validated (Pattern A.2).** **12 wrappers / 14 catalog
techniques** (p3_ccf multi-maps to 3 catalog IDs per
Disposition 4). TSL output validated bit-exact against
independent-package reference (R `urca::ur.df`, R `vars::VAR`,
numpy.fft, etc.). Empirical wrapper enumeration per S8
empirical re-verification: p3_adf, p3_ccf (covers
cross_correlation_lag + prewhitened_ccf_lag + rolling_ccf_lag),
p3_classical_decompose, p3_denton_chowlin, p3_dtw,
p3_fft_spectrum, p3_granger, p3_kpss, p3_pca,
p3_robust_estimators, p3_var, p3_vecm.

**Tier II.mle-band — Phase 3 cross-package PASS at MLE-fit
band tolerance.** **13 wrappers per S8 empirical surfacing.**
Cross-package PASSes against R references at MLE-fit band
tolerances (typically 1e-2 to 1e-1 abs); operational R reference
comparison; **NOT bit-exact at machine precision**. Empirical
wrapper enumeration per S8: p3_arima, p3_sarima,
p3_arimax_sarimax, p3_ets, p3_theta, p3_intervention_analysis,
p3_dfm, p3_hmm, p3_markov_switching, p3_sgarch, p3_gjr_garch,
p3_egarch, p3_tar_setar.

**S4 spot-check classification consistency check:** sgarch +
markov_switching now classified Tier II.mle-band per Disposition
2; Pattern H DSCD distinction per S4 finding preserved within
Tier II.mle-band sub-class.

**Cross-reference S8 first-consumption empirical re-verification
+ S4 spot-check classification ambiguity findings.**

**Tier III — Phase 3 same-library self-parity validated
(Pattern A.1).** **18 wrappers** per P-3 v1.2.0 §1 (locked at
scale). TSL output validated bit-exact against direct in-process
invocation of same underlying library. **Verifies wrapper-
integrity claim only** (preprocessing, parameter resolution,
audit-field rounding); does NOT validate against independent
implementation.

**Tier IV — Phase 3 self-parity / paper-formula validated
(Pattern A.3).** ~10 wrappers per P-3 v1.2.0 §1 estimate. TSL
output validated against from-scratch reimplementation of
paper-defined recursion. Pattern K → Pattern A path (per
`tools/reference_parity/reports/phase3_cross_batch_findings.md`
S10 cross-batch finding): 5 wrappers — `p3_bocpd`,
`p3_cusum_page_hinkley`, `p3_stl_esd` (S10 / Batch 6) +
`p3_wavelet_coherence`, `p3_ssa` (S11 / Batch 7). Specific
full Tier IV technique enumeration empirical re-verification
deferred to S6+1 first-step-of-Q1.

**Tier V — Phase 3 PASS with documented divergence (Pattern D /
Pattern J caveat; non-blocking).** Documented methodology
divergences per `tools/reference_parity/reports/phase3_cross_batch_findings.md`
cross-batch + Pattern J catalog launched at S12: AIC scale
offset (Pattern D) for `p3_ets` (S3 / Batch 1) + `p3_var`
(S7 / Batch 3 per S4 spot-check verification); ARCH/RUGARCH
alpha-vs-gamma naming swap for `p3_egarch` (S6 / Batch 2;
Pattern J B.2 internal-default divergence); scipy/astropy
normalization convention for `p3_lomb_scargle` (S11 / Batch 7;
Pattern J B.3 alignment-via-metric resolution). Verdict PASS
at primary-tier; secondary-tier or per-metric documented
divergence non-blocking.

**Tier VI — Phase 3 CAVEAT.** 5 wrappers per P-3 v1.2.0 §1:
`p3_emd_hht`, `p3_mstl`, `p3_nar_narx`, `p3_star`, `p3_stl`.
Matches except in stated regime (boundary, near-singular,
iterative LOESS divergence, Tier C reference convergence
failure).

**Tier VII — No Phase 3 parity infrastructure (Phase 7+ S9
in-place §2 amendment per S8 first-consumption empirical
re-verification + Disposition 1 ratification).** Original
"~3-5" estimate **empirically falsified at S8**. Empirical
reality at HEAD `5205779`: **Tier VII = 1 catalog technique
(auto_arima only)**.

S6 §2 candidates re-classified per S8 empirical findings:
- `auto_arima` → CONFIRMED Tier VII (no p3_*.py wrapper; not
  Phase 1/2 covered)
- `bvar` → COVERED by Phase 1/2 `bvar.py` (IRF/FEVD-given-coefs
  only); re-classified to Tier I.partial per Disposition 3
- `critical_slowing_down` → COVERED by Phase 1/2
  `critical_slowing_down.py` (verdict PASS via `ewstools` 2.1.2
  reference per P-4 status tracker line 48)
- `har_cj` → COVERED by Phase 1/2 `har_cj.py` (From-scratch
  reimpl per ABD 2007 paper; OLS / closed-form; PASS per P-4
  line 51)

**Cross-reference S8 first-consumption empirical re-verification
+ Disposition 3 bvar Tier I.partial characterization.**

### Multi-map catalog↔wrapper handling note (Phase 7+ S9 in-place §2 amendment per Disposition 4)

**p3_ccf empirical multi-map:** single Phase 3 wrapper covers 3
catalog techniques (`cross_correlation_lag` +
`prewhitened_ccf_lag` + `rolling_ccf_lag`).

**Per-catalog characterization at Q1 sub-sessions:** each of
the 3 p3_ccf-covered catalog IDs documented separately in trust
inventory amendment with cross-reference to shared p3_ccf
wrapper. Per-wrapper characterization alone insufficient
because catalog↔wrapper mapping is many-to-one in this case.

**Forward instrumentation:** verify catalog↔wrapper mapping at
each technique characterization at Q1 sub-sessions; do NOT
assume 1:1 mapping; multi-mapping pattern likely recurs beyond
p3_ccf and needs per-technique empirical surfacing analogous to
S8 first-consumption protocol.

**Note on tier composition:** Tiers are **not strictly ordered**;
a technique can be in MULTIPLE tiers simultaneously (e.g.,
`bond_yield_forecast` is Tier I AND Tier IV; structural-
invariants dispatch validated AND Pattern A.1 self-parity +
Pattern F structural invariants). Tiers represent different
KINDS of validation evidence not different STRENGTHS.

**Sum check:** Tier II ~12 + Tier III 18 + Tier IV ~10 + Tier V
(distributed across other tiers as overlay) + Tier VI 5 = ~45-50
distinct wrappers + Tier VII ~3-5 + Tier I overlap (9 catalog
entries; 8 mostly within Tier II/III/IV via p3_*) ≈ 70 Phase 3
in-scope per master plan §15. P-3 §1 tier counts are
approximate per source artifact; empirical re-verification of
per-tier exact counts is Q1 first-step work.

## §3 Phase 7+ work program scope (re-framed)

Per Chat ratifications 1-2-3-5: comprehensive coverage of all
84 catalog techniques; (C) operational standard (single-fixture
parity baseline + cross-package extension where feasible +
parameter-sensitivity for all techniques where operationally
meaningful); Path α end-of-work-program expert review.

### Thread Q1 — Trust documentation remediation

S8 inventory amended OR deprecated; per-technique characterization
against §2 tier taxonomy. Verify-state-at-narration discipline
applied at full force per CONSTRAINT 4 BLOCKING; per-technique
tier characterization empirically verified against Phase 3 doc-set
(P-3, P-4) + per-wrapper `p3_*_audit.md` source artifacts at
authoring time, not extracted from prior conversation context.

**Estimated:** 3-5 sub-sessions (depends on S8 amendment scope vs
deprecation-and-rewrite scope; Q1 first sub-session disposition).

### Thread Q2 — Genuinely uncovered techniques (Phase 7+ S9 revision per Dispositions 1 + 3 combined)

**Original "~3-5 catalog techniques" estimate empirically
falsified at S8 first-consumption empirical re-verification.**
Revised Q2 scope per S8 Dispositions 1 + 3 ratifications:

(a) `auto_arima` — full new validation work (Disposition 1
ratified Tier VII = 1 catalog technique only)
(b) `bvar` Bayesian estimation step uncovered-portion
validation (Disposition 3 Tier I.partial framing; bvar IRF/FEVD
already validated via Phase 1/2 `bvar.py`; Bayesian estimation
step priors → posterior coefs uncovered)

Per-technique workflow Steps 1-6 as originally framed in S9
handoff §3 + Phase 7+ scope re-framing §3:
1. Chat proposes upstream decisions with provenance metadata
2. User ratifies or contests
3. If contested, Chat redrafts; iterate to ratification
4. Code executes parity work (or blended validation if parity
   not feasible)
5. Validation output documented with provenance metadata
6. Technique enters validated-pre-expert-review status

**Revised estimate: 3-5 sub-sessions** (NOT 1-2; bvar Bayesian
estimation step is non-trivial validation; NOT 5-8 per S6 §3
inflated estimate).

**Total work program estimate** revises modestly downward per
this Q2 scope contraction; S6 §3 18-30 month total range
preserved with Q2 narrowing absorbed by other thread variance.

### Thread Q3a — Cross-package extension

Per-technique judgment on Pattern A.1 (Tier III) same-library
cases: does independent reference implementation exist + does
cross-package parity add meaningful evidence beyond same-library
self-parity?

**14 ML/DL block techniques** (per S8 inventory §3 enumeration):
typically NO meaningful independent reference (analogous to S4
spot-check finding for `random_forest_forecast`,
`gaussian_process_forecast` per Pattern A.1 sub-class); Tier III
same-library self-parity remains best available evidence; Q3a
**SKIP for these with documented rationale per technique**.

Non-ML/DL same-library cases (e.g., `pelt_change_points` Tier III
per S4 spot-check): Q3a candidate; per-technique evaluation.
Reference availability may be weaker (analogous to bocpd's
"weaker reference package landscape" per S4 swap rationale).

**Estimated:** 5-15 sub-sessions depending on Q3a candidate count
(empirically calibrated as Tier III enumeration completes at Q1).

### Thread Q3b — Parameter-sensitivity coverage

**Comprehensive per Chat ratification 2:** every catalog technique
where parameter sensitivity is operationally meaningful. No
frequency-weighting triage; no publication-impact narrowing.

Multi-fixture parameter sweeps + reference computation across
parameter space + tolerance band specification per fixture point
+ verdict aggregation. Per-technique Q3b decisions: **Tier 3
second-opinion architecture MANDATORY** per Chat ratification 4
(not optional; not first-of-class only); Chat critiques own
proposal before user sees it.

Operational definition of "operationally meaningful" parameter
dimensions: pinned at first-technique Q3b activation; not
pre-specified.

**Estimated:** 30-60 sub-sessions; could exceed depending on
per-technique parameter dimensionality.

### Total work program

**Estimated total: 18-30 months realistic at typical sub-session
cadence;** exceeds prior Phase 7+ scope estimate (S9 handoff §3
implicit). User explicit acknowledgment per Chat ratification 5:
scope is largest available configuration; runway 18-30 months
realistic; published-research exposure during work program window
with retroactive correction risk; **ratified consciously under
user authority**.

## §4 Expert review timing (Path α)

Per Chat ratification 3:

**Path α end-of-work-program review.** Single expert engagement
covers entire program (Q1 + Q2 + Q3a + Q3b complete).

**Expert resource (per S9 handoff §5 Tier 2 framing):** Morgan
Stanley quant colleague / external consultant / academic
collaborator. User commits to recruitment.

**Methodology disclosure during work program window covers ALL
validated tiers** per §2 tier taxonomy. Each disclosure template
(Workstream B disposition 2 artifact, drafting unpaused post-S6)
states: which tier evidence backed validation + AI-assisted
upstream decisions with web-search support + user ratification +
pre-expert-review status + expected expert review completion
timeline.

**Retroactive correction risk** during work program window: outputs
published may require correction if expert review surfaces
upstream decision errors. **User conscious acknowledgment** per
Chat ratification 5.

## §5 Operational discipline carry-forward from Phase 6+ + Phase 7+ S1-S5

**Verify-state-at-narration discipline** PROMOTED to blocking
checkpoint for any artifact making validation-state claims per
S6 trigger §2 ratification + sixth A2 observation strengthening.
Codification at Workstream B disposition 2 artifact pending
(unpaused post-S6).

**Layered smooth-ratification countermeasures:**
- Tier 1 "wrong if X" (Chat self-skepticism in upstream proposals)
- Tier 2 devil's-advocate (Chat presents alternative position)
- Tier 3 second-opinion (Chat critiques own proposal before user
  sees it) — MANDATORY for all Q3b parameter-sensitivity decisions
  per Chat ratification 4

**Validation provenance audit checklist per technique close**
(codified in Workstream B disposition 2 artifact pending).

**Per-cohort STOP-AND-CONFIRM precedent at major thread
transitions:** Q1 close → Q2 activation; Q2 close → Q3a
activation; Q3a close → Q3b activation; Q3b close → Path α
expert review activation.

**Master plan v1.3 + §19.4 living baseline + §19.1 sub-session
taxonomy + §19.2 routine-targeted-patch gate + §19.3 contested-
decision threshold + §19.4 A1+A2 ESTABLISHED+A3+A4 active +
absorption-timing forward instrumentation note** all carry
forward operational at Phase 7+.

## §6 Forward instrumentation

**Sixth A2 observation (S3 finding) + scope drift pattern (S5
archaeology)** STRENGTHENS verify-state-at-narration amendment
candidate to blocking-checkpoint status. v1.4+ master plan
amendment scope at next major recalibration moment.

**Q3b first-technique activation will calibrate Tier 3 second-
opinion architecture operational form.** Concrete questions to
resolve: how Chat critique is rendered (separate document
section vs inline annotations); how user reviews critique vs
original proposal; what disposition options exist (accept
critique / reject critique / hybrid).

**Audit/archaeology class threshold:** S4 ~700 LOC + S5 ~700 LOC =
n=2 baseline. Class informally ESTABLISHED above current §19.4
A3 calibration. Amendment candidate at next §19.4 recalibration:
audit/archaeology class projection 600-900 LOC; surface
threshold 1100 LOC (loose; tighten with more observations).

**Q1 first-technique activation** will calibrate trust
documentation remediation sub-session class baseline.

**Q2 first-technique activation** will calibrate per-technique
workflow Steps 1-6 as originally framed. The granger_causality
S3 pre-flight is on hold; per S3 empirical finding (`p3_granger`
PASS verdict against R `lmtest::grangertest`; f_stat abs diff
8.53e-14; date 2026-04-29), granger is Tier II per §2 tier
taxonomy; granger handled at Q1 trust documentation remediation
as Tier II amendment, not Q2 first-technique.

**Workstream B disposition 2 artifact UNPAUSED post-S6** with
tier taxonomy known. Methodology disclosure templates draft
against §2 tier taxonomy (validation evidence categories per
template).

### Path A precedent accumulation note (Phase 7+ S9 in-place §6 amendment per Adjustment 1 + 2)

**Path A precedent accumulation: S1 + S7 + S9 = THIRD instance.**
Per S7 §4 absorption-timing forward instrumentation cross-
reference: "if Path A becomes dominant operational mode across
3+ absorption sub-sessions, **§19.4 disposition 5 amendment
candidate** can lock Path A as canonical interpretation." S9
crosses 3-instance threshold; **disposition-5 lock candidate
ELEVATED to ACTIVE candidate status**. Next §19.4 amendment
cycle absorbs disposition-5 lock per amendment density
criterion.

**Two-pattern characterization per Adjustment 2:**
- **Path A elevation-candidate-absorption (S1 + S7):** absorbs
  elevation candidates from sub-session banking footers /
  handoff documents into baseline file in-place; S1 absorbed
  S8 elevation events (A2 graduation + A4 elevation); S7
  absorbed 5 candidates from S1-S6 arc surfacing
- **Path A first-consumption-correction (S9):** corrects
  taxonomy claims that didn't survive empirical first-
  consumption at downstream re-verification step; S8 first-
  consumption surfaced 4 substantive issues with S6 §2
  taxonomy; S9 amends in-place

Both warrant Path A (immediate-on-discovery rather than
deferred-to-recalibration); underlying mechanisms structurally
distinct. Disposition-5 lock at next §19.4 amendment cycle
clarifies whether these are unified disposition-5 (single Path
A pattern with multiple sub-mechanisms) or parallel
dispositions (two related but distinct dispositions).

### Verify-state-at-first-consumption forward instrumentation (Phase 7+ S9 in-place §6 amendment per Adjustment 3)

**Discipline shape: synthesis claims require empirical
re-verification at first downstream consumption, not just
authoring-time citation re-verification.**

**Pattern observation per S8 first-consumption empirical
re-verification:** A6 verify-state-at-narration as currently
codified at §19.4 living baseline covers narrative claims about
codebase state at narration moment; does NOT cover taxonomic
claims that synthesize across codebase state. S6 §2 taxonomy
is first concrete instance; S8 first-consumption empirical
re-verification surfaced 4 substantive issues authoring-time
discipline could not catch (Tier VII material divergence
~3-5 → 1; Tier II classification ambiguity requiring split;
bvar partial coverage requiring Tier I.partial; multi-map
catalog↔wrapper requiring per-catalog characterization).

**Operational implication:** any taxonomy or synthesis artifact
requires empirical re-verification at first downstream
consumption (Workstream B template authoring, Q1 trust
documentation per-technique characterization, etc.) — not just
authoring-time citation re-verification.

**This discipline shape is more substantively important than
the taxonomy corrections themselves**, because it identifies a
gap in the discipline architecture that would otherwise
propagate forward into Workstream B and Q1 work.

**Codification path:** folding into Workstream B disposition 2
artifact §4 verify-state-at-narration discipline operational
spec; future §19.4 amendment cycle codifies. Sub-discipline-of-
A6 vs new-amendment framing decision deferred to that cycle.

## §7 Banking footer

**Phase 7+ banking locus ESTABLISHED at this commit:**
`docs/reference_parity_phase7/`. First entry: this artifact
(`scope_reframing_s6_banking.md`).

**Cross-references:**
- S5 archaeology report (Phase 7+ S5; in conversation; not
  committed; verbatim S5 findings preserved at §1 of THIS
  artifact)
- S4 verdict spot-check (Phase 7+ S4; in conversation; not
  committed; verbatim S4 findings preserved at §2 tier taxonomy
  derivation)
- §19.4 living baseline post-S1 absorption state (4 active
  amendments + absorption-timing forward instrumentation note
  at `docs/reference_parity_phase6/calibration_baseline.md`)
- Phase 6+ banking locus 10 entries (`docs/reference_parity_phase6/`)
- Phase 3 doc-set authoritative source: P-1 + P-2 + P-3 + P-4
  v1.2.0 at `docs/engineering/parity_standard.md` +
  `docs/engineering/parity_diagnostic_reference.md` +
  `docs/engineering/parity_empirical_findings.md` +
  `docs/reference_parity_status.md`
- S8 trust inventory (premise corrected at §1; amendment scope
  Q1 first-sub-session disposition) at
  `docs/reference_parity_phase6/tsl_trust_inventory_techniques.md`
- Master plan v1.3 §15 + §19 + §19.4 living baseline at
  `plans/reference_parity_phase5_master_plan.md`

**Forward state:**
- Workstream B unpause (Chat-side; methodology disclosure
  templates draft against §2 tier taxonomy)
- S7 candidate: Q1 first-technique activation (trust
  documentation remediation entry point) — empirical re-
  verification of Tier II ~12 wrappers + Tier VII ~3-5 wrappers
  per S6+1 first-step

## Disposition

Phase 7+ scope re-framing committed. Validation tier taxonomy (7
tiers) codified. Work program scope (Q1 + Q2 + Q3a + Q3b)
codified with effort estimates totaling 18-30 months. Path α
expert review timing codified with conscious user-acknowledged
exposure. Operational discipline carry-forward documented.
Phase 7+ banking locus ESTABLISHED. Workstream B unpause cleared.
S7 candidate: Q1 first-technique activation per S6+1 first-step
empirical re-verification.
