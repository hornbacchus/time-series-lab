# Phase 5 Session 3 [PRE-FLIGHT] — S3-α scope audit + 3-criteria gate Criterion 3 prospective evaluation

**Date:** 2026-05-05
**Scope:** Pre-flight design-class audit per Q-S3-1=(b) +
Q-S3-2=(β) engine+first-wrapper / second-wrapper+cross-wrapper
decomposition + Q-S3-3=(a) Q-banking-categorical strict.
First prospective application of master plan v1.1 standing
discipline 3-criteria gate. Output: findings doc only;
NO code commits per pre-flight scope discipline.
**Status:** COMPLETE.

## §1 Engine Path A elevation scope audit (Category 1)

**Engine modules located** per master plan v1.1 §15 S3 framing:
- `engine/techniques/stochastic_volatility.py` — main wrapper
- `engine/techniques/_sv_mcmc.py` — PyMC NUTS MCMC implementation
- `engine/techniques/_sv_mcmc_gibbs.py` — Gibbs sampler

**Engine-side state audit:** `_sv_mcmc.py` result dict (lines
311-321) ALREADY exposes `rhat_max`, `rhat_max_param`,
`ess_min`, `ess_min_param`. `stochastic_volatility.py` engine
wrapper (lines 647-650) ALREADY elevates these to
`audit_fields` per BYF Decision 12 pattern.

**Major audit finding:** Engine Path A elevation is **ALREADY
COMPLETE** per Phase 4 S8 P4-1.2 codification (reflected in
commit `ff403dd` lineage; cross-referenced by master plan v1.1
§15 S8 wrapper grouping). The master plan v1.1 §15 S3
expectation of "Path A audit-field elevation in `_sv_mcmc.py`"
was based on pre-Phase-4 state hypothesis. Phase 4 S8 already
landed this elevation.

**Engine work scope for S3-α: ~0 LOC.** No engine modifications
required. S3-α scope reduces to harness allowlist addition +
per-wrapper smoke test for mcmc_sv_gaussian.

**No blocking issues** identified. Engine implementation
production-ready; reference implementation
(R `stochvol::svsample`) integrated at harness level; fixture
data (`2b_sv_gaussian` + `2c_sv_student_t`) extant per Phase 1
+ Phase 3 codification.

## §2 Harness wrapper field-availability investigation (Category 2)

**Harness wrappers located:**
- `tools/reference_parity/harness/checks/mcmc_sv_gaussian.py`
  (technique_id `2b_mcmc_sv_gaussian`; fixture `2b_sv_gaussian`)
- `tools/reference_parity/harness/checks/mcmc_sv_student_t.py`
  (technique_id `2c_mcmc_sv_student_t`; fixture `2c_sv_student_t`)

**`structural_invariants` declarations** (Phase 4 S9 dormant
declarations extant):
- gaussian: `mcmc_convergence` invariant; tolerance=200 (ESS_min
  PASS threshold)
- student_t: `mcmc_convergence` invariant; tolerance=200

**Field-availability investigation per S2-redux protocol:**

`_check_mcmc_convergence` checker is **single-side** (consumes
`tsl.get(field)` only; no ref needed). Required + optional
fields:
- **Required:** `ess_min` (BLOCK if missing)
- **Optional:** `rhat_max` (PASS if missing per checker default)
- **Optional:** `geweke_max_abs_z` (PASS if missing per checker default)

Both harness wrappers' `run_tsl()` (lines 259-269 gaussian;
lines 182-193 student_t) ALREADY return `ess_min` at top level
extracted from engine `audit_fields["ess_min"]`. Required-field
exposure: **ALREADY MET** for both wrappers.

**Case beyond i/ii/iii/iv from S2-redux protocol surfaced:**
"Case 0 — required field already exposed at top level; no
expansion needed." Both MCMC SV wrappers fall into this case.
Optional fields (`rhat_max`, `geweke_max_abs_z`) NOT exposed
but checker handles None gracefully.

**Optional refinement (NOT required for invariant dispatch):**
expose `rhat_max` at top level (~3 LOC per wrapper) for
stronger PASS validation. Decision deferred to S3-α/S3-β
authoring.

**Harness work scope per wrapper:**
- gaussian: ~1 LOC allowlist + 0 LOC required-field
  (already exposed); ~25 LOC per-wrapper smoke test;
  optional ~3 LOC rhat_max exposure
- student_t: ~1 LOC allowlist + 0 LOC required-field
  (already exposed); ~25 LOC per-wrapper smoke test;
  optional ~3 LOC rhat_max exposure

## §3 3-criteria gate Criterion 3 evaluation (Category 3)

**S3-α envelope** (engine Path A + gaussian + smoke):
- Engine work: 0 LOC (Phase 4 S8 already complete)
- Harness gaussian: ~30 LOC (allowlist + optional rhat_max +
  smoke test)
- Findings doc + banking (per Q-banking-categorical strict
  for any architectural surfacing): ~50-80 LOC
- **Combined estimate: ~80-110 LOC** — clean per §13.1
  default 200 LOC by 45-60% headroom

**S3-β envelope** (student-t + cross-wrapper acceptance):
- Harness student-t: ~30 LOC
- Cross-wrapper acceptance test extension (mirrors S2-β-redux
  pattern): ~30-50 LOC
- Findings doc + banking: ~30-50 LOC
- **Combined estimate: ~90-130 LOC** — clean per §13.1
  default by 35-55% headroom

**Envelope assessment per 3-criteria gate Criterion 3
(empirical-validation envelope based on S2 sequence outcome
+ engine-work-already-done finding):**

3-criteria gate Criterion 3 **SATISFIED** for (β) decomposition:
- Both S3-α + S3-β under §13.1 default 200 LOC by substantial
  headroom (≥35%)
- S2 sequence empirical record (5/5 redux commits clean; per-
  wrapper field-availability protocol validated at trio scope;
  verified-via-CI) supports envelope projection accuracy
- No architectural ambiguities or blocking issues surfaced

(β) decomposition envelope-clean; S3-α + S3-β triggers proceed
per established structure.

## §4 S3-α + S3-β trigger structure determination

**S3-α — gaussian wrapper integration** (engine work
demonstrably 0 LOC; harness allowlist addition + per-wrapper
smoke test only):
- Allowlist: extend `_INVARIANTS_DISPATCH_ALLOWLIST` from
  3-tuple (S2 trio) to 4-tuple including
  `"2b_mcmc_sv_gaussian"`
- Required-fields map: extend `_INVARIANT_REQUIRED_FIELDS` to
  include `mcmc_convergence → ("ess_min",)`
- Per-wrapper smoke test exercising real `run_tsl` output;
  verifies dispatch + invariant PASS
- Optional: surface `rhat_max` at top level (~3 LOC; non-
  required but stronger PASS validation)
- Findings doc with banking entries per Q-banking-categorical
  strict (architectural surfacings during execution; routine
  Case-0 application unlikely to warrant banking)

**S3-β — student-t wrapper integration + cross-wrapper
acceptance:**
- Allowlist: extend to 5-tuple including
  `"2c_mcmc_sv_student_t"`
- Per-wrapper smoke test mirrors gaussian pattern
- Cross-wrapper acceptance test extends existing pattern from
  S2-β-redux to include MCMC SV pair
- Optional rhat_max exposure (mirrors S3-α optional decision)

**Engine work surfacing:** S3-α trigger should explicitly
acknowledge "engine Path A elevation already complete" finding
+ note master plan v1.1 §15 S3 framing predates Phase 4 S8
codification. May warrant banking entry per Q-banking-
categorical strict (architectural framing reconciliation
between v1 master plan + Phase 4 S8 codification + v1.1 master
plan).

**§13.4 compliance:** Pre-flight commit delta verified at
staging time per Code's chunking judgment.

## Disposition

S3 [PRE-FLIGHT] audit COMPLETE. 3-criteria gate Criterion 3
SATISFIED for (β) decomposition; S3-α + S3-β triggers proceed
per established structure. Major finding: engine Path A
elevation ALREADY COMPLETE (Phase 4 S8 codification). S3-α
execution trigger ahead per Q-S3-2=(β) decomposition;
Q-banking-categorical strict applies; per-wrapper field-
availability protocol + cycle-wide parity-fast tier
verification + CI verification protocol all standing.
