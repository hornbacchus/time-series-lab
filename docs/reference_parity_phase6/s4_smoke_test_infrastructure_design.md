# Phase 6+ S4 — sub-domain (ii) S6 smoke-test infrastructure design (BYF-disposition-anchored scope; keep-dormant; sub-domain (ii) closes at S6)

**Date:** 2026-05-09
**Scope:** Master plan §15 sub-domain (ii) S6 activation per
v1.3 settled framework. BYF-disposition-anchored scope with
consolidation + forward-looking framing per Chat ratification.
Closes B-Phase4-S10-3 forward-banked concern via keep-dormant
disposition (design-intent-preserved, not concern-resolved-by-fix).
**Class:** novel-substantive design-doc; per v1.3 §19.1 first
sub-domain (ii) activation. No implementation work per
CONSTRAINT 1.
**Status:** S6 COMPLETE; sub-domain (ii) closes at S6 per S7
trigger NOT MET.

## §1 Pre-flight scope determination outcome

Code's empirical re-audit at S6 pre-flight (per S3 + S6 second
substance-class application of pre-flight scope determination
protocol) found:
- 8-wrapper allowlist tolerance bands all empirically grounded
  per Phase 5 + Phase 6+ S1 + S3 verification
- BYF (`p3_bond_yield_forecast`) `_AUDIT_N_DRAWS = 2000`
  (DOUBLED from B-Phase4-S10-3 banking n_draws=1000;
  intervening Phase 4-5 work uncross-referenced — see §6
  banking footer pattern graduation)
- BYF NOT in `_INVARIANTS_DISPATCH_ALLOWLIST` (`runner.py`
  lines 109-118); `mcmc_convergence` declaration DORMANT
- Phase 6+ S1 parameter-aware exclusion mechanism does NOT
  apply to BVAR-SV parameter set (different from 2b/2c
  sigma_eta/nu non-gating pattern)

S6 scope contracted from master plan §15 broad framing per
Ratification 3 (codified §3 below). Three scope items:
(a) BYF disposition · (b) tolerance band consolidation ·
(c) sample-size forward-looking guidance.

## §2 BYF disposition (load-bearing)

**Disposition: KEEP DORMANT + ACCEPT BLOCK as known scope-
limitation.**

**Framing per Ratification 2:** This is **design-intent-
preserved, NOT concern-resolved-by-fix.** B-Phase4-S10-3
remains substantively true at S6 close: BYF chain length
insufficiency would surface as omnibus BLOCK on
`mcmc_convergence` if BYF were allowlisted. Keep-dormant
chooses to NOT activate the wrapper rather than fix the
underlying ess insufficiency.

**Future activation inheritance:** Future Phase 6+ sub-session
that activates BYF in allowlist inherits "concern UNRESOLVED;
activation path required" — NOT "concern closed at S6." S6
preserves the dormant declaration as a documented design
intent without operational cost; revisits at later sub-session
if BYF allowlisting becomes priority.

**4 activation paths surfaced for posterity** (chosen path =
1; alternates documented for future activation reference):

| Path | Description | Scope class | S7+ work |
|---|---|---|---|
| **1 (CHOSEN)** | Keep dormant + accept BLOCK | Banking-class | NONE (S6 closes) |
| 2 | Activate at higher n_draws (e.g., 5000-10000) | Engine-touch | Sub-domain (iv) reserve scope; engine retuning + chain length validation |
| 3 | Activate with parameter-aware exclusion mechanism extension to BVAR-SV parameter set | Mechanism + master plan amendment | S1 mechanism extended to BVAR-SV; per-parameter audit of which BVAR-SV parameters are non-gating; tests + master plan §15 amendment per S1 precedent |
| 4 | Accept BLOCK with allowlisting | Banking + acceptance | Allowlist BYF; document BLOCK as known issue; cycle-architecture amendment to §19.6 framing for "accepted-BLOCK" status class |

**Rationale for Path 1 (keep-dormant):**
- BYF is the only "closure cycle" wrapper outside the 8-wrapper
  allowlist (per master plan §15 S5 separate framing); not in
  Phase 5 sub-domain (i) integration scope
- Paths 2-4 each substantially exceed S6 design scope:
  - Path 2: engine-touch (sub-domain (iv) reserve)
  - Path 3: mechanism + master plan amendment (S1 precedent
    scope; novel-substantive multi-commit work)
  - Path 4: cycle-architecture amendment to status class
    framing (§19.6 amendment scope)
- Path 1 preserves declaration as documented design intent
  without operational cost; lowest-blast-radius option

## §3 Scope contraction from master plan §15 (per Ratification 3)

**Master plan §15 sub-domain (ii) S6 framing scope-contracted
at S6 activation.** Original framing covered "n_draws
calibration; sample-size requirements; tolerance band review
across the 9 wrappers; B-Phase4-S10-3 specific concern
addressed" with "~80-120 LOC design doc" projection.

**Scope contraction rationale:**
- Phase 5 sub-domain (i) work (allowlist construction +
  per-wrapper tolerance band ratification across 8 wrappers
  at S2 + S3 + S4) substantially addressed tolerance band
  axis: all 8 allowlist wrappers empirically grounded with
  PASS on real fixtures
- Phase 6+ S1 architectural amendment (parameter-aware
  exclusion mechanism on `_check_mcmc_convergence`) addressed
  the "ess breach + non-gating parameter" axis for 2b/2c MCMC
  SV (sigma_eta + nu)
- Phase 6+ S3 sub-domain (iii) None-handling fix +
  defense-in-depth confirmation (check_base.py L1 + structural_invariants.py
  L2) addressed adjacent dispatch + lifecycle robustness
- Residual scope at S6 activation: BYF-targeted (single
  wrapper concern) + consolidation/verification (no changes
  proposed) + forward-looking guidance (no per-wrapper
  changes)
- LOC projection scope-contracted: ~70-100 (vs master plan
  ~80-120) reflects intervening-work-already-addressed status

**§15 amendment candidate at next recalibration moment:**
Master plan §15 sub-domain (ii) S6 framing predates Phase 5 +
Phase 6+ S1 + S3 work; scope was authored assuming all three
axes (n_draws + sample-size + tolerance band) required design
work. Empirical state at Phase 6+ S6 activation is
substantially narrower. §15 sub-domain (ii) framing is candidate
for amendment-in-place at next recalibration moment via §19.4
living calibration baseline file (NOT inline at this commit
per CONSTRAINT 1 master-plan-amendment exclusion).

## §4 Tolerance band review (consolidation; no changes proposed)

8-wrapper allowlist tolerance bands verified empirically
grounded post Phase 6+ S1 + S3:

| # | Wrapper | Invariant | Tolerance | Empirical grounding |
|---|---|---|---|---|
| 1 | `kalman_filter` | `kalman_covariance_ordering` | 1e-6 abs | PSD-ordering numerical-noise floor; PASS on real fixtures |
| 2 | `johansen_bartlett` | `vecm_cointegration_rank` | 0.0 abs | Strict integer match; PASS |
| 3 | `evt_ferro_segers` | `evt_extremal_index` | 0.01 abs | Slack outside [0,1]; PASS (theta=0.6184 typical) |
| 4 | `mcmc_sv_gaussian` | `mcmc_convergence` (200 ESS) + non_gating sigma_eta | 200.0 abs | Phase 1 audit 2b precedent + S1 + S1-FU empirical (parity-slow `25606689880` PASS via sigma_eta exclusion) |
| 5 | `mcmc_sv_student_t` | `mcmc_convergence` (200 ESS) + non_gating (sigma_eta, nu) | 200.0 abs | Phase 1 audit 2c precedent + S1 + S1-FU empirical (PASS via sigma_eta + nu exclusion) |
| 6 | `mint_family` | `mint_coherence` | 1e-10 abs | Closed-form-safe floor; PASS (residual = 0.0 exactly) |
| 7 | `transformer_attention` | `attention_normalization` | 1e-6 abs | Float32 row-sum noise floor; PASS (max_dev = 3.65e-08) |
| 8 | `caviar_sav` | `intervals_test` | 0.05 abs (INVERTED) | Standard 5% p-value floor; PASS (chris_pvalue = 1.0000) |

**Verification finding:** ZERO changes proposed. All 8
allowlist tolerance bands empirically grounded; no
recalibration warranted at S6.

## §5 Sample-size + n_draws forward-looking guidance

For future MCMC-class wrapper additions to the allowlist,
chain-length sufficiency criteria distinguish two analytical
sub-classes:

**SV-class (single-variate stochastic volatility):**
- Pattern: 1-variable SV with mu + phi + sigma_eta (+ nu for
  Student-t variant) parameter set
- Empirical chain-length adequacy at engine default produces
  ess_min ~28-33 on prior-divergence-driven parameters
  (sigma_eta, nu)
- mu/phi parameters mix well at engine default; ess > 200
- Recommendation: declare `non_gating_params` for prior-
  divergence-driven parameters per S1 precedent; engine
  default chain length sufficient

**BVAR-SV-class (high-dim BVAR with stochastic volatility):**
- Pattern: K-variable BVAR-SV with mu/phi/sigma blocks per
  variable + cross-equation covariance (~K² parameters at
  K=6 BYF empirical)
- Empirical chain-length insufficiency at n_draws=1000
  (ess_min=7.4) and n_draws=2000 (extrapolated ess_min~15-20);
  insufficient for omnibus PASS at threshold=200
- Multiple parameters likely below threshold (not single
  prior-divergence-driven parameter); parameter-aware
  exclusion mechanism alone insufficient
- Recommendation: BVAR-SV-class wrappers require either
  (a) substantially higher n_draws (5000-10000+) OR
  (b) separate convergence checker class per analytical
  pattern OR (c) accept BLOCK as known scope-limitation

**Forward guidance for future MCMC wrapper additions:**
1. Pre-flight empirical audit of ess profile at engine
   default chain length per Phase 6+ S6 + S3 pre-flight
   discipline pattern
2. Classify wrapper into SV-class / BVAR-SV-class /
   other-class
3. Apply per-class sufficiency criteria
4. If insufficiency surfaces, consider Path 2/3/4 from §2
   table (engine retuning / mechanism extension / accept
   BLOCK) at activation sub-session

## §6 S7 trigger evaluation

**S7 trigger: NOT MET.** Sub-domain (ii) closes at S6 per
keep-dormant + accept-BLOCK disposition (Ratification 2).
Master plan §15 sub-domain (ii) S7 ("Smoke-test infrastructure
implementation + validation") would activate IF S6 ratified
implementation path; keep-dormant path produces no
implementation work.

**Future S7 activation conditions:**
- BYF allowlisting becomes priority (Phase 6+ S5+ disposition
  required)
- New BVAR-SV-class wrapper enters allowlist scope (would
  trigger Path 2/3/4 evaluation per §5 forward guidance)
- Cycle-architecture amendment shifts BYF status class
  framing (Path 4 activation)

## Banking footer

**B-Phase6-S6-SUB-DOMAIN-ii-CLOSE codification (inline per
v1.3 §19.1 banking-class single-commit; no separate banking
entry per CONSTRAINT 2 + Ratification 5).**

**BYF disposition codification:** Keep-dormant + accept-BLOCK
chosen at S6. **Design-intent-preserved framing (Ratification
2):** B-Phase4-S10-3 concern remains substantively true; choice
to not activate wrapper rather than fix ess insufficiency.
Future activation sub-session inherits "concern unresolved;
activation path required" — NOT "concern closed at S6."

**Scope contraction codification (Ratification 3):** Master
plan §15 sub-domain (ii) S6 framing scope-contracted at S6
activation. Original framing predates Phase 5 + Phase 6+ S1 +
S3 intervening work. Residual scope at S6 = BYF-targeted +
consolidation + forward-looking. **§15 amendment candidate at
next recalibration moment via §19.4 living calibration
baseline file** (NOT inline at this commit).

**Soft-estimate-vs-empirical pattern GRADUATION (anecdote →
pattern; Ratification 6):**

| Observation | Sub-session | Banking entry | Stale claim | Empirical at activation |
|---|---|---|---|---|
| First | S3 | B-Phase4-S7-1 | "6 checkers / S6/8/9" | 5 functions / 7 sites; cross-batch (S7 + S13 included) |
| Second | S6 | B-Phase4-S10-3 | "n_draws=1000" | n_draws=2000 (intervening Phase 4-5 work uncross-referenced) |

**Pattern (graduated from anecdote at S6):** Phase-N-cycle
banking entries become stale at Phase-(N+1)+ activation when
intervening work is uncross-referenced. Banking entries should
include "verify state at activation time" protocol; Phase-N
banking should empirically re-check state at Phase-(N+1)+
activation.

**v1.3 §19 amendment candidate at next recalibration moment
via §19.4 living calibration baseline file** (extends S3
banking forward-looking guidance precedent: empirical-
enumeration-over-soft-estimate AND verify-state-at-activation
protocols).

**Forward instrumentation:** track at next sub-domain
activation (sub-domain (iv) if activated; or future
substance-class activation) whether pattern continues. Three
observations would solidify pattern; one falsifying observation
(banking entry remained current at activation) would weaken.

**Distinct from Reading B documentation-density observation
track** — separate observation; do not conflate. Reading B
status preserved at ANECDOTE per v1.3 §19.6 + S3 closeout
instrumentation.

**Cross-references** (compressed):
- B-Phase4-S10-3 origin (master plan §3.1 + §15 sub-domain
  (ii) S6 framing)
- Empirical origin: `../reference_parity_phase4/session_9_findings.md`
  lines 20-29 (BYF n_draws=1000 → ess_min=7.4)
- v1.3 §15 sub-domain (i) extension at master plan
  (architectural pattern locus; Path 3 alternate)
- v1.3 §19.1 sub-session class taxonomy (compliance:
  novel-substantive design-doc class)
- B-Phase6-KICKOFF-ARC-CLOSE at
  `kickoff_arc_close_banking.md` (post-arc-close first
  activation)
- S3 banking forward-looking guidance precedent at
  `s3_banking.md` (first observation of soft-estimate pattern)

## Disposition

Sub-domain (ii) S6 COMPLETE at this commit. BYF disposition =
keep-dormant + accept-BLOCK (design-intent-preserved framing).
S7 trigger NOT MET; sub-domain (ii) closes at S6 with
scope-narrower-than-master-plan-S7 close. B-Phase4-S10-3
forward-banked concern dispositioned (NOT resolved). Soft-
estimate-vs-empirical pattern graduated from anecdote to
pattern at S6 (S3 first + S6 second observations). §15 +
§19.4 amendment candidates surfaced for next recalibration
moment.
