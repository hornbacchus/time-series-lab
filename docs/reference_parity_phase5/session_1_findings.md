# Phase 5 Session 1 (S1-A-1-a-CORRECTED + S1-A-1-b) — §1.a + §1.b + §1.c (Decision 30D + Option β cascade)

**Date:** 2026-05-04
**Scope (S1-A-1-b):** Append §1.c audit registry review +
cascading-split institutional record note to existing
findings doc (§1.a + §1.b at S1-A-1-a-CORRECTED commit
`5d27a39`). Constraints pre-specified per Decision 30D
pattern; banking entries deferred to S1-A-1-c per Option β.
**Status:** COMPLETE.

S1-A-1-a-CORRECTED (commit `5d27a39`) landed at 75 LOC after
two prior reverts (S1-A-1 ORIGINAL `537c989` per Decision
30B; S1-A-1-a `99bb534` per Decision 30D). Constraint-
specification fix validated empirically (1.07× projection
multiplier; clean under §13.1 default by 62.5% headroom).
S1-A-1-b applies same constraint pattern + Option β natural
seam (§1.c at this commit; all 5 banking entries at S1-A-1-c).

## §1 Architecture review (current-state inventory)

### §1.a Audit-side declarations review — master-plan-locus correction

**Critical correction:** Master plan §15 sub-domain (i) S1
specification hypothesised audit-side declarations live in
engine `_dispatch.py`. Architecture review verified
declarations live in `tools/reference_parity/harness/checks/*.py`
audit scripts (NOT engine-side).

Phase 4 S9 commit `ff403dd` (master plan §3.2 dormant table
source) landed declarations as `structural_invariants = (...)`
class attributes on each `P3ParityCheck` subclass, not in
engine code. The 9 inherited-wrapper declarations + p3_bond_yield_forecast,
all confirmed extant at `ff403dd`:

| Audit script | invariant_type | tolerance |
|---|---|---|
| `kalman_filter.py:KalmanFilterParity` | `kalman_covariance_ordering` | 1e-6 abs |
| `johansen_bartlett.py:JohansenBartlettParity` | `vecm_cointegration_rank` | 0 abs (strict) |
| `mcmc_sv_gaussian.py:McmcSvGaussianParity` | `mcmc_convergence` | 200 ESS_min |
| `mcmc_sv_student_t.py:McmcSvStudentTParity` | `mcmc_convergence` | 200 ESS_min |
| `evt_ferro_segers.py:EvtFerroSegersParity` | `evt_extremal_index` | 0.01 abs slack |
| `mint_family.py:MintFamilyParity` | `mint_coherence` | 1e-10 abs |
| `transformer_attention.py:TransformerAttentionParity` | `attention_normalization` | 1e-6 abs |
| `caviar_sav.py:CaviarSavParity` | `intervals_test` | 0.05 p-value floor |
| `p3_bond_yield_forecast.py:BondYieldForecastParity` | `mcmc_convergence` | 200 ESS_min |

Plus 6 sibling wrapper classes also declare invariants per
post-S9 batch fill-in (`p3_hmm`, `p3_vecm`, `p3_local_level`,
`p3_var`, `p3_egarch`, `p3_gjr_garch`, `p3_sgarch`); 16
total wrappers per Grep audit. Sub-domain (i) Phase 5 scope
is the 9 inherited wrappers from the master plan §3.2
dormant table.

The locus correction is critical for S2 implementation
trigger drafting (B-Phase5-S1-1 banking codification deferred
to S1-A-1-c per Decision 30D + Option β sequencing).

### §1.b P-2 §D.1.5 audit-side wrapper-declaration table verification

P-2 §D.1.5 audit-side declaration table coherence verified
against `ff403dd` commit message; no drift. Tolerance values
in §1.a table match P-2 §D.1.5 table exactly. INVERTED
semantics for `caviar_sav` codified at P-2 §D per
B-Phase4-S9-3.

### §1.c Audit registry review (concrete checker implementations)

`tools/reference_parity/harness/structural_invariants.py`
registers **23 invariant types** (4 stubs + 19 concrete) per
the unit test's `test_registry_enumeration`. All 5 Phase 4
S7 new types (`mcmc_convergence`, `evt_extremal_index`,
`mint_coherence`, `attention_normalization`, `intervals_test`)
are concrete. The 9 invariants declared by the inherited
wrappers all map to concrete (non-stub) checkers.

**INVERTED semantics handling for caviar_sav:** the
`_check_intervals_test` checker (lines 1040-1093 of
`structural_invariants.py`) handles INVERTED semantics
internally — PASS if `pvalue > floor` (opposite of typical
"smaller residual = PASS" interpretation). Wrapper just
supplies `tolerance=0.05` (the floor); checker's internal
math handles the inversion. **No special runner-side
handling needed.**

**B-Phase4-S7-1 None-handling surface (latent):** 6 concrete
checkers raise TypeError on missing audit-field input
(instead of returning a clean BLOCK dict). Three explicitly
named in `_test_structural_invariants.py:test_checker_dispatch`
docstring (lines 129-208): `var_eigenvalues` (line 193),
`garch_conditional_variance` (line 289), `hmm_row_sums`
(line 519). Other 3 are similarly-shaped
`np.asarray(tsl.get(field), dtype=np.float64)` calls without
None pre-check. Currently masked by the runner integration
gap (§1.f below); becomes empirical once invariants fire.

### §1.d Existing test infrastructure inventory

`tools/reference_parity/harness/_test_structural_invariants.py`
(485 LOC) covers 7 test functions:

1. `test_dataclass_instantiation` — `StructuralInvariant`
   field semantics
2. `test_registry_enumeration` — 23 types discoverable
3. `test_checker_dispatch` — both stub-raise + concrete-BLOCK
   + concrete-raise (B-Phase4-S7-1) paths accepted
4. `test_s7_new_checkers_pass_on_valid_inputs` — 5 S7 types
   PASS on satisfying inputs
5. `test_s7_new_checkers_block_on_violation` — 5 S7 types
   BLOCK on violating inputs
6. `test_unregistered_type_raises_keyerror` — registry
   lookup safety
7. `test_s9_inherited_wrapper_declarations` — 9 inherited
   wrapper classes have valid `structural_invariants` tuples
   resolving to registered checkers

**Coverage gap:** no test exercises the runner-side dispatch
of `check_invariants` against actual `run_tsl` outputs (test
7 docstring confirms: "Declarations are dormant at S9 — the
harness's check_invariants lifecycle method is not yet wired
into the runner"). S2 introduces
`_test_runner_invariants_dispatch.py` to close this gap.

### §1.e Smoke-test infrastructure entry points (B-Phase4-S10-3 context)

The harness `tools/reference_parity/harness/checks/_smoke.py`
smoke-test is a generic numpy-vs-R mean probe (1-second
harness validator); **unrelated** to B-Phase4-S10-3.

B-Phase4-S10-3 concerns the **wrapper-fixture n_draws
calibration** for the MCMC SV wrappers
(`mcmc_sv_gaussian`, `mcmc_sv_student_t`,
`p3_bond_yield_forecast`). At BYF integration time, smoke
runs at `n_draws=1000` produced ESS_min < 200 →
`mcmc_convergence` omnibus BLOCK once runner integration
lands. Fix surface is fixture metadata + per-wrapper
`setup_fixture` n_draws parameter, not the harness runner
itself. Sub-domain (ii) S6+S7 owns this scope.

### §1.f Runner integration gap + outcome-ladder current state (the core S1 finding)

`tools/reference_parity/harness/runner.py:run_check` (lines
112-263) has **4 lifecycle steps**:

1. Load fixture (with hash verify; lines 134-145)
2. `check.run_tsl(fixture)` (line 154)
3. `check.run_reference(fixture)` (line 166)
4. `first_result = check.compare(tsl_out, ref_out)` (line 190)

Plus a CAVEAT-reroll branch (lines 200-239) and exception
mapping to ParityResult outcomes.

**There is NO `check_invariants` step.** The base
`ParityCheck` ABC (`base.py` lines 134-212) declares only
the 4 abstract methods; `P3ParityCheck` (`check_base.py`
lines 91-166) extends with mandatory `verdict_class` /
`verdict_class_rationale` attributes + `reroll_on_caveat`
default flip + `structural_invariants : tuple = ()`
declaration attribute, but adds NO new lifecycle method.

**Outcome-ladder current state:** `aggregate_outcomes`
(`base.py` lines 68-79) handles multi-check aggregation via
`_OUTCOME_PRIORITY` ranking (BLOCK > ERROR > DOCUMENTED-
DIVERGENCE > CAVEAT > PASS > SKIP). Intra-check sub-result
aggregation (e.g., compare-status vs invariants-status)
within a single ParityResult is NOT currently handled — the
runner just returns `compare`'s ParityResult verbatim.
Design question for S1-B: should structural-invariants
status integrate via the same ranking?

The `_test_structural_invariants.py:test_s9_inherited_wrapper_declarations`
docstring (line 358) confirms the gap explicitly:

> "Declarations are dormant at S9 — declared invariants are
> discoverable via class introspection but do not fire
> during normal audit runs."

## Cascading-split institutional record

S1 sub-session sequence depth: Decision 28 four-level master
plan cascade + Decision 29F three-level S1 cascade + Decision
29F-1 four-level S1-A cascade + Decision 30B fifth-level
S1-A-1 cascade + Decision 30D revert-and-re-execute with
constraint specification + Option β natural seam (§1.c at
S1-A-1-b vs banking at S1-A-1-c). Two-revert sequence
(S1-A-1 ORIGINAL + S1-A-1-a) on same logical session;
institutional-inconsistency cases corrected via revert-and-
re-execute discipline preserved through audit trail.
Detailed banking + calibration-pattern analysis at S1-A-1-c
+ S1-C per Decision 30D + 29F sequencing.

## Banked observations from S1-A-1-c (consolidated S1-A-1 sequence corrections)

**B-Phase5-S1-1 — Master-plan-locus correction.** Audit-side
declarations live in `tools/reference_parity/harness/checks/*.py`
NOT engine `_dispatch.py`. Original S1 trigger hypothesis +
master plan §15 sub-domain (i) text by inheritance referenced
incorrect locus; architecture review at S1 verified declarations
landed as `structural_invariants = (...)` class attributes per
Phase 4 S9 commit `ff403dd`. Cross-reference: master plan §3.2
dormant table; P-2 §D.1.5 audit-side declaration table (no
drift). Forward-looking: master plan v2 amendment may be
warranted at S13 doc-set issuance time; future cycle authors
should consult `harness/checks/*.py` for declaration locus,
not engine code.

**B-Phase5-S1-A-1-CLASSIFICATION-ERROR — S1-A-1 ORIGINAL
band-absorption misclassification.** S1-A-1 ORIGINAL commit
`537c989` at 211 LOC classified within-band principled-content-
density as measurement-variance, applied band absorption.
Per Decision 17 + B-Phase4-S12b-1-1 + B-Phase4-S12b-1-2-C
precedent, within-band principled-content-density triggers
split, NOT band absorption; only measurement-variance overshoot
(formatting noise / edit-vs-replace LOC accounting) absorbs.
Cross-reference: S11b-1 ORIGINAL (Decision 17 Path B revert
precedent); reverted at `fb4dfc3` per Decision 30B. Forward-
looking: marginal-tolerance band absorption requires explicit
measurement-variance classification with documented rationale;
default disposition for principled content in band is split.

**B-Phase5-S1-A-1-TRIGGER-LANGUAGE — Decision 21 trigger
language insufficiency at within-band landing zones.**
UPDATED Decision 21 discipline at Decision 30B trigger
specified content-vs-measurement dichotomy but did NOT pre-
reject novel exception paths (e.g., "saturation at cascade
depth" framing); permitted institutional-inconsistency repeat
at S1-A-1-a. Cross-reference: B-Phase4-S12c-3 trigger-drafting
discipline analog at band-edge scope; master plan §4.2
standing language. Forward-looking: trigger language at
within-band landing zones must explicitly reject novel
exception paths, not just specify the content-vs-measurement
classification dichotomy; pre-rejection list is load-bearing.

**B-Phase5-S1-A-1-a-SECOND-CLASSIFICATION-ERROR — S1-A-1-a
band-absorption-via-saturation-framing repeat.** S1-A-1-a
commit `99bb534` at 205 LOC re-attempted band absorption
under "saturation at fifth-level cascade depth" framing; same
error class as S1-A-1 ORIGINAL (Decision 30B target) via
different framing. Cross-reference: reverted at `8798624` per
Decision 30D; this is the third Phase 4+5 institutional-
inconsistency case after S11b-1 ORIGINAL revert-and-re-commit
(Decision 17 Path B) + S12c original revert-and-re-split
(Decision 23B). Forward-looking: correction discipline must
address root cause (trigger drafting), not just same-
disposition-with-different-trigger; revert-and-re-execute
at same trigger generality is insufficient.

**B-Phase5-S1-A-1-a-OVERHEAD-EXPANSION — Cascade-depth spill
source identification.** S1-A-1 + S1-A-1-a spill source was
Code-authored overhead expansion (framing + tables + banking
codifications + disposition footer ~165 LOC); principled
content (§1.a + §1.b raw at ~40 LOC) was NOT the overshoot
source. Decision 30D constraint specification (per-section
LOC cap; banking deferral; minimum overhead specification)
removed the overhead expansion vector. S1-A-1-a-CORRECTED
(commit `5d27a39`; 1.07× multiplier) + S1-A-1-b (commit
`4e4317a`; 1.02× multiplier) empirically validated content-
density-bounded behavior at fifth-level cascade depth when
overhead constrained. Forward-looking: constraint-specification
trigger discipline is the cascade-depth lever for codification-
density-class artifacts; future Phase 5 trigger drafting at
deep-cascade scope must include explicit overhead minimums +
banking-deferral pathways. Bank as Phase 5 institutional
precedent for cascade-depth trigger calibration.

**§13.4 compliance:** S1-A-2 +80 net LOC commit delta (95
insertions, 15 deletions); 60% headroom under §13.1 default
200; clean per §13.1 default; no marginal-tolerance band
engagement. Trigger projection ~95-115 LOC; actual 0.84×
(under lower-bound) — constraint-specification fix continues
generalizing. Doc cumulative: 281 LOC across S1-A-1-a-CORRECTED
+ S1-A-1-b + S1-A-1-c + S1-A-2.

## Disposition

§1.a + §1.b + §1.c + §1.d + §1.e + §1.f + 5 banking entries
LANDED across S1-A-1-a-CORRECTED + S1-A-1-b + S1-A-1-c +
S1-A-2 sequence. **§1 Architecture review structurally
complete; S1-A sub-section CLOSED at S1-A-2.** §2 deferred
to S1-B; §3-§5 + B-Phase5-S1-CALIBRATION-PATTERN +
B-Phase5-S1-A-1-b-CONSTRAINT-VALIDATION +
B-Phase5-S1-A-1-c-GENERALIZATION-VALIDATION to S1-C.
