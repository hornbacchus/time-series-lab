# The 5-Phase Follow-up Workflow

## Overview

This document codifies the workflow used for shipping technique
follow-ups in this repository. It is **descriptive** — it
captures the convention that emerged through Phase 1's
retrospective audit, the B6/B1/B7 follow-up commits, and the
Phase 2 reference-parity harness arc — rather than imposing a
new mandate.

The workflow has five phases plus a mandatory disclosure step
(Phase 4.5) for follow-ups that touch numerical wrappers:

1. **Phase 1 — Audit/Design.** Identify the change, scope it,
   design the implementation before writing code.
2. **Phase 2 — Plan.** Detailed implementation sketches per file.
3. **Phase 3 — Apply.** Execute the implementation.
4. **Phase 4 — Test invariants.** Run pytest; ensure T14/T15
   invariants pass.
5. **Phase 4.5 — Reference parity check.** Mandatory disclosure
   in commit message; see the dedicated section below.
6. **Phase 5 — Canonicals.** Run the technique's canonical
   regression scripts.

For adding new harness checks (the Phase 4.5 infrastructure
itself), see the sibling document
[`reference_parity_contributor_guide.md`](reference_parity_contributor_guide.md).

## Phase 1 — Audit/Design

**Purpose:** identify the change, scope it, design the
implementation before writing code.

**Deliverable:** a design audit document covering the standard
sections:

1. **Current state.** What does the wrapper / spec / fixture
   look like today? Cite line numbers, function names, fixture
   IDs.
2. **Probe / detection strategy.** If the follow-up adds a
   guard, fallback, or auto-detection: how does it probe? What
   does it return? What is the cost?
3. **Cascade design.** If the follow-up modifies an existing
   fallback cascade or introduces one: what triggers each
   branch? What `fallback_reason` populates? What wins on
   ambiguity?
4. **Audit-field additions.** What new fields appear in
   `audit_fields`? What types? What defaults on the non-MCMC /
   non-applicable paths?
5. **Spec / Tier 3 trigger consideration.** Is a new D-trigger
   needed? Or does an existing trigger cover the case?
6. **Canonical design.** What new canonicals are added? What
   existing canonicals must regression-pass? What is the
   skip-tolerant posture?
7. **File topology.** Table of every file the follow-up will
   touch with LOC estimate, plus a total LOC estimate.

**Review gate:** the design audit is reviewed by the user
before Phase 2 begins.

**Examples** of good Phase 1 design audits in repository
history:

- B6 (PyMC NUTS g++ auto-downgrade) — cascade design + new
  D-trigger + audit-field additions.
- B1 (mint_sample rank-deficient W guard) — probe + cascade
  integration + no new D-trigger.
- B7 (latent log-volatility posterior exposure) — capability
  addition with memory-strategy decision (Welford
  accumulators).

## Phase 2 — Plan

**Purpose:** write detailed implementation sketches for every
file the follow-up will touch.

**Deliverable:** an implementation plan with code sketches per
file. Per-file LOC estimates plus total estimate.

**Review gate:** implementation plan reviewed before Phase 3.

The plan should be specific enough that Phase 3 execution is
mechanical — Phase 3 should not require new design decisions.

## Phase 3 — Apply

**Purpose:** execute the implementation per the Phase 2 plan.

**Deliverable:** code changes per the plan.

There is no formal review gate within Phase 3; the reviewer
sees the result at Phase 5.

## Phase 4 — Test invariants

**Purpose:** ensure pytest invariants T14 (audit-field schema)
and T15 (disclosure-prose token allowlist) still pass.

- **Adding new audit fields:** update `T14` `_MINIMAL_INPUT`
  fixture to include the new keys with `None` defaults so the
  spec's null-guards via `.get()` don't crash.
- **Adding new programmatic tokens to disclosure prose:** add
  them to the `T15` `_PROGRAMMATIC_TOKEN_ALLOWLIST` so they
  don't trip the leakage detector.

**Deliverable:** pytest passing.

**Standard disclosure in commit message:**

```
Tests: 96/96 passing.
```

or

```
Tests: 96/96 passing unchanged.
```

## Phase 4.5 — Reference parity check (MANDATORY DISCLOSURE)

**Purpose:** verify that follow-ups don't silently break
numerical correctness against external references (R `hts`,
`stochvol`, `urca`, `extRemes`; PyTorch native MHA; from-scratch
paper-derived reimplementations).

**Mandatory disclosure rule:** every follow-up commit touching
`engine/techniques/` MUST state either a Phase 4.5 result OR
"Phase 4.5 N/A: <reason>" in the commit message.

### When Phase 4.5 applies

**Mandatory** if the follow-up modifies the numerical output
of a wrapper that has harness coverage. Examples:

- Changing a numerical algorithm (B6: cascade selection
  changes which sampler runs and therefore what posterior
  values are produced).
- Changing a fallback target (B1's cascade falls to
  mint_shrinkage which is the validated parity target — but
  if a follow-up changed mint_shrinkage's math, Phase 4.5
  would apply).
- Exposing a new derived quantity (B7: new `h_posterior_mean`
  audit field requires a parity check against
  `stochvol::svsample`'s `$latent`).

**N/A acceptable** if the change is:

- **Non-numerical** (HD-prose updates, comment-only changes,
  refactoring with no behavioral impact).
- **Audit-field exposure of already-computed values** (no
  numerical change).
- **Structural guard** (rank checks, error handlers) that
  trigger fallbacks already validated by parity tests.
- The wrapper has **no harness coverage yet** (in which case
  the disclosure should also flag adding coverage as a
  follow-up opportunity).

### How to determine which harness check applies

1. Run `python tools/follow_up_phase_check.py` (see Tooling
   section). The script takes `git diff` against
   `origin/master`, identifies modified wrappers, and prints
   the mapping.
2. Or consult [`docs/follow_up_check_coverage.md`](follow_up_check_coverage.md)
   directly.
3. If the wrapper has no harness coverage, the disclosure
   should state: `Phase 4.5 N/A: no harness check covers
   <wrapper>.` Optionally flag in the commit message that
   adding coverage is a follow-up opportunity.

### How to run the parity check

```
python -m reference_parity --technique <id>
python -m reference_parity --technique <id> --json
python -m reference_parity --tier fast --json
python -m reference_parity --tier slow --json
```

For full harness invocation reference, see
[`reference_parity_contributor_guide.md`](reference_parity_contributor_guide.md).

### Three-outcome ladder

The harness reports outcomes per the ladder codified by B6 /
B7 / Session 4:

**Outcome 1 — PASS first-run.**
All gating metrics under PASS thresholds. Disclose per
**Template A**. Commit-ready.

**Outcome 2 — CAVEAT first-run, PASS after seed+1 reroll.**
At least one gating metric in CAVEAT band on first run. The
runner re-runs automatically with `seed+1`; the second run
lands all metrics under PASS. Disclose per **Template B**.
Commit-ready.

**Outcome 3 — BLOCK.**
Either initial BLOCK on any gating metric, or CAVEAT remains
CAVEAT after the seed+1 reroll. **Do NOT commit until cause
is understood.**

Three diagnosis branches:

- **(a) Real bug in the follow-up** → fix and re-run. Don't
  ship.
- **(b) Tolerance miscalibration** (the metric is sensitive to
  a methodology choice the tolerance ladder didn't anticipate)
  → revisit tolerance ladder design **in a separate commit**.
  Do NOT loosen tolerances inside the follow-up commit; that
  conflates "follow-up changes behavior" with "we decided the
  old check was wrong."
- **(c) Methodology divergence** (TSL and reference
  implementations differ in a documented, acceptable way that
  the existing tolerance didn't capture) → document the
  divergence in honest-disclosure spec text; either widen
  tolerance with citation **in a separate commit**, or accept
  BLOCK as the final state and document why this wrapper
  falls outside parity coverage.

### Commit-message templates (codified verbatim from B6 / B7 / Session 4 precedent)

**Template A — PASS first-run.**

> Phase 4.5 reference parity vs `<reference>` on `<fixture>`:
> `<metric1> <value1>`, `<metric2> <value2>`, ...
> Outcome 1 PASS first run.

Real example, from commit `2c864ed` (B6):

> Reference parity vs stochvol Gibbs on 2b audit fixture: mu
> rel_diff 1.08%, phi rel_diff 6.77%, sigma_eta record-only
> (prior-driven divergence). Outcome 1 PASS first run.

**Template B — CAVEAT-then-PASS.**

> Phase 4.5 reference parity vs `<reference>`: first-run
> CAVEAT (`<metric> <value>`, in CAVEAT band [`<low>`,
> `<high>`]), seed+1 reroll PASS (`<metric> <value>`).
> Outcome 2, attributed to MC noise.

Real example, from commit `75aa182` (Session 4, 2c
Student-t):

> 2c MCMC SV Student-t parity vs stochvol::svtsample:
> first-run nu rel_diff in CAVEAT band (~13%), seed+1 reroll
> PASS (nu rel_diff 6.63%). Outcome 2 attributed to MCMC
> sampling variance.

**Template C — N/A with rationale.**

> Phase 4.5 N/A: `<rationale citing what was previously
> validated and why this follow-up doesn't change that
> numerical surface>`.

Real example, from commit `928ad81` (B1):

> Phase 4.5 N/A: 3e audit already validated the fallback
> target (mint_shrinkage) at 4.66e-15 vs R-hts. B1 is a guard
> against numerical instability on a previously-undetected
> pathological input, not a numerical change to currently-
> passing methods.

## Phase 5 — Canonicals

**Purpose:** run the technique's canonical regression scripts
(typically `tools/validate_<technique>_canonicals.py`).
Existing canonicals must regression-pass byte-identically; new
canonicals introduced by the follow-up must PASS.

**Deliverable:** canonical runs documented per case
(PASS / SKIP / BLOCK with reason).

**Standard disclosure in commit message** (form varies by
follow-up; common pattern is a per-canonical sentence with
explicit "regression-pass unchanged" for prior canonicals):

> C7 canonical verifies cascade fires correctly on
> noise_on_top=False fixture (matches 3e audit pattern):
> applied transitions mint_sample → mint_shrinkage,
> fallback_reason populated, coherence post-L2 at machine
> zero, D1 trigger fires with rank-deficient explanation.
> Existing C1-C6 MinT canonicals regression-pass unchanged.

**Examples** from repository history:

- **B6** (commit `2c864ed`): 4 new canonicals (3 PASS + 1
  documented SKIP) + 6 existing SV MCMC + 6 existing
  Student-t SV regression-pass.
- **B1** (commit `928ad81`): 1 new canonical (C7) + 6 existing
  MinT (C1-C6) regression-pass.
- **B7** (commit `09dde01`): 3 new canonicals (C-h-1 Gibbs,
  C-h-2 NUTS-skip-tolerant, C-h-3 quasi-ML) + 4 existing
  canonical suites regression-pass.

## Tooling

### `tools/follow_up_phase_check.py`

Optional helper. Takes `git diff` against `origin/master`,
identifies modified files in `engine/techniques/`, looks up
coverage in `docs/follow_up_check_coverage.md`, prints
suggested Phase 4.5 actions per modified wrapper.

**Usage:**

```
python tools/follow_up_phase_check.py
python tools/follow_up_phase_check.py --base origin/master
python tools/follow_up_phase_check.py --base 75aa182
```

**Output format:**

```
Modified wrappers vs origin/master:
  engine/techniques/stochastic_volatility.py
    → 2b_mcmc_sv_gaussian (tier: slow)
      run: python -m reference_parity --technique 2b_mcmc_sv_gaussian
    → 2c_mcmc_sv_student_t (tier: slow)
      run: python -m reference_parity --technique 2c_mcmc_sv_student_t
  engine/techniques/some_other_wrapper.py
    → No harness coverage.
      Phase 4.5 disclosure: 'N/A: no harness check exists for this wrapper.'
```

The script is a soft aid. The workflow doesn't depend on it;
authors can consult `docs/follow_up_check_coverage.md`
directly.

### `docs/follow_up_check_coverage.md`

Static mapping table from TSL wrappers to harness checks. See
the sibling document.

### Updating the mapping table

When a new harness check is added (per
[`reference_parity_contributor_guide.md`](reference_parity_contributor_guide.md)),
update `docs/follow_up_check_coverage.md` in the same commit.
A stale check-coverage table would silently weaken Phase 4.5
enforcement.

## Worked example

Hypothetical follow-up **B11** — *expose Kalman smoother
posterior std bands in `audit_fields`*. Walk through the full
workflow:

### Phase 1: Design audit

- **Current state.** `engine/techniques/kalman_smoother.py`
  exposes `smoothed_state` (length-T mean trajectory) but not
  the corresponding posterior std band.
- **Probe / detection strategy.** N/A (capability addition,
  not auto-detection).
- **Cascade design.** N/A (no fallback; smoother always runs
  when invoked).
- **Audit-field additions.** `smoothed_state_std` (length-T
  list of floats) and optionally `smoothed_state_var` (length-T
  list of floats, for users who prefer variance scale).
- **Spec / Tier 3 trigger consideration.** No new D-trigger;
  the new fields are informational, not diagnostic. Tier 2
  prose gains a one-sentence disclosure when the smoother
  populates them.
- **Canonical design.** `C-k-1` validates the new fields are
  populated, are length-T, and have all-positive finite values.
  Existing Kalman canonicals must regression-pass.
- **File topology.**
  - `engine/techniques/kalman_smoother.py` — Welford-style or
    direct `P_smoothed[t][0,0]` extraction (~25 LOC).
  - `engine/interpretation/specs/kalman_smoother.py` — Tier 2
    one-liner (~5 LOC).
  - `engine/tests/test_interpretation_contract.py` — T14: 1
    None-default key (~3 LOC).
  - `tools/validate_kalman_smoother_canonicals.py` — C-k-1
    (~50 LOC).
  - **Total estimate: ~85 LOC.**

### Phase 2: Plan

Detailed code sketches per file. Verify state-cov extraction
math against statsmodels' KalmanSmoother documentation. Decide
whether to expose `smoothed_state_var` alongside or skip.

### Phase 3: Apply

Execute per plan. Mechanical at this point.

### Phase 4: Test invariants

Add `smoothed_state_std: None` to T14 `_MINIMAL_INPUT`
kalman-smoother section. Defensive token allowlist for `T15`
if the new prose introduces any chained-underscore identifiers
(probably none; `smoothed_state_std` is fine on the regex but
defensive listing keeps intent explicit).

`pytest engine/tests/`. Expect 96/96.

### Phase 4.5: Reference parity

Run `python tools/follow_up_phase_check.py`. Expected output:

```
Modified wrappers vs origin/master:
  engine/techniques/kalman_smoother.py
    → 2a_kalman_filter_smoother (tier: fast)
      run: python -m reference_parity --technique 2a_kalman_filter_smoother
```

Run `python -m reference_parity --technique 2a_kalman_filter_smoother`.
Expected outcome: PASS first-run (the new field doesn't
change the existing smoothed-state mean computation; only
adds a parallel std-extraction).

Disclosure (Template A):

> Phase 4.5 reference parity vs R dlm + KFAS on Phase 1
> fixture: filtered_states max_abs_diff 3.5e-6, smoothed_states
> max_abs_diff 7.8e-7, log_likelihood_vs_kfas abs_diff 3.6e-7.
> Outcome 1 PASS first run.

### Phase 5: Canonicals

Run `python tools/validate_kalman_smoother_canonicals.py`.
Existing canonicals regression-pass byte-identically; C-k-1
new canonical PASSes (validates length-T shape and all-positive
finite values).

### Resulting commit message

```
Expose Kalman smoother posterior std bands in audit_fields (follow-up B11)

Closes the capability gap surfaced during Phase 4.5 review of
2a_kalman_filter_smoother: the smoother exposed the mean
trajectory in audit_fields but not the corresponding posterior
std band. Downstream uncertainty visualizations consume the
±2σ bands.

Now exposes smoothed_state_std as a length-T list of floats in
audit_fields. The std is extracted from the smoother's
P_smoothed covariance trajectory at each timepoint. Default to
None on the non-smoothed paths.

Tier 2 disclosure gains a one-sentence note about the new field
when the smoother populated it. No new D-trigger; the new field
is informational, not diagnostic.

Tests: 96/96 passing.

Phase 4.5: Reference parity vs R dlm + KFAS on Phase 1 fixture:
filtered_states max_abs_diff 3.5e-6, smoothed_states
max_abs_diff 7.8e-7, log_likelihood_vs_kfas abs_diff 3.6e-7.
Outcome 1 PASS first run.

Phase 5: C-k-1 new canonical validates length-T shape and
all-positive finite values. Existing Kalman canonicals
regression-pass unchanged.
```

## When to deviate

The 5-phase workflow is a default, not a strict requirement.
Deviations are acceptable when:

- **The change is trivial** (typo fix, comment addition,
  single-line refactor with no behavioral impact). Phases 1-2
  collapse to the commit message itself.
- **The change is exploratory** (proof-of-concept branch). The
  workflow applies when merging to master, not during
  exploration.
- **The change is infrastructure** (build scripts, CI config,
  docs-only). Phases 4 and 4.5 are typically N/A.

Deviations should be disclosed in the commit message, e.g.:

> Workflow deviation: Phase 1 audit abbreviated to a single
> paragraph because the change is a one-line cosmetic fix.
