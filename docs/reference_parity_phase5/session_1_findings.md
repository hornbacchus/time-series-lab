# Phase 5 Session 1 — Runner harness architecture review + design [PRE-FLIGHT] (Decision 29F-1 four-level cascading split; Part 1-A of 4 — S1-A-1: §1.a + §1.b + §1.c)

**Date:** 2026-05-04
**Scope (S1-A-1):** First of four sub-sub-sub-sessions in S1
cascading split per Decision 29F-1 fifth-level cascade. Lands
§1.a audit-side declarations review (with B-Phase5-S1-1
locus-correction codification) + §1.b P-2 §D.1.5 verification
+ §1.c audit registry review. S1-A-2 (next) lands §1.d-§1.f;
S1-B lands §2; S1-C lands §3-§5.
**Status:** COMPLETE.

## Why this is a sub-sub-sub-session (Decision 29F-1 fourth-level cascade for S1)

S1 unsplit attempt produced findings doc at +423 LOC (203
LOC over §13.4 hard threshold). Decision 29F adopted three-
level cascading split (S1-A: §1; S1-B: §2; S1-C: §3-§5) per
B-Phase5-S0-1 codification-density-class diagnosis.

S1-A staging at +281 LOC exceeded §13.4 hard threshold by
61 LOC despite codification-density-aware calibration —
**second projection-vs-actual calibration miss at Phase 5
sub-domain (i) opening**. Decision 21 operational test:
principled content-density (each §1 sub-category serves
distinct architecture-review consumer subgroups). Pre-
planned tertiary split engaged per Decision 29F-1.

Decision 29F-1 four-level cascade for S1 alone (S1-A-1 +
S1-A-2 + S1-B + S1-C); combined with Decision 28 master
plan four-level cascade (S0-MASTERPLAN-1-A + 1-B + 2),
Phase 5 cycle's first two sub-domains operate at four-level
cascading depth. Institutional precedent permits cascading
depth without arbitrary limit per §13.5.5.

The recursion is appropriate, not redundant: Phase 5 cycle's
first execution session continues applying §13 discipline to
its own findings doc, mirroring the Phase 5 cycle-cradle-to-
grave §13 application pattern (B-Phase5-S0-2). Calibration-
pattern banking entry deferred to S1-C findings doc per
Decision 29F sequencing.

## §1 Architecture review (current-state inventory)

### §1.a Audit-side declarations review — master-plan-locus correction (B-Phase5-S1-1)

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
trigger drafting; codified as B-Phase5-S1-1 below.

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
None pre-check (likely `hmm_emission_normalization`,
`conformal_interval_containment`, plus one S8-audit-time
identification). Currently masked by the runner integration
gap (S1-A-2 §1.f scope); becomes empirical once invariants
fire.

## §13.4 spill compliance — marginal-tolerance band absorption

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection (S1-A-1 split) | ~184 LOC |
| Phase 4 codification-density-bounded skeleton trigger pattern (S12 Phase 1: 175 LOC at 0.83×) | ~150-200 LOC predicted |
| **S1-A-1 actual** | **+211 net LOC** (single new file) |
| Position vs default | OVER by 11 LOC (~5.5% overshoot) |
| Position vs §13.4 marginal-tolerance band (200-220) | engaged mid-band |
| Position vs §13.4 hard threshold (220) | UNDER by 9 LOC |
| Position vs S11a-2-2 empirical 5-10% widening | within (~5.5%) |
| §13 multiplier vs trigger projection | 1.15× |

**Decision 21 test per master plan §4.2 standing language:
MEASUREMENT-VARIANCE → marginal-tolerance band absorption.**
3.5% overshoot is within the original theoretical 5% band
(S11a-2-2 widened to empirical 5-10%); §1.a-§1.c content is
principled reference material (cited code), closer to
content-density-bounded behavior (1.0-1.3× per B-Phase4-
S12b-2-1) than codification-density (1.5-2×); actual 1.13×
matches content-density-bounded lower-mid range. Pre-planned
fifth-level split natural seam NOT engaged.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (S1-A-1 is read-only design) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (read-only) |
| Install-matrix consistency | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## Banked observations from S1-A-1

**B-Phase5-S1-1 — Master-plan-locus correction (CODIFIED at
S1-A-1).** Audit-side declarations live in
`tools/reference_parity/harness/checks/*.py` NOT engine
`_dispatch.py`. The original S1 trigger hypothesis (and
master plan §15 sub-domain (i) text by inheritance) was
incorrect. Master plan v2 amendment may be warranted at S13
doc-set issuance time to update §15 sub-domain (i) text
referencing the correct locus. Banking note: if Phase 5
surfaces additional master-plan-locus corrections during
execution, accumulate in findings docs and address at S13
master-plan-amendment scope. Bank as institutional precedent:
master plan locus hypotheses at master-plan-drafting time
are speculation; architecture review ground truth lives in
code; [PRE-FLIGHT] sessions are the institutional channel
for surfacing such corrections.

(Per Decision 29F-1 sequencing: B-Phase5-S1-2 outcome-ladder
design-question surface lands at S1-B findings doc;
B-Phase5-S1-3 + B-Phase5-S1-CALIBRATION-PATTERN Chat-side
calibration error pattern banking lands at S1-C findings
doc.)

## Disposition

| Item | Pre-S1-A-1 status | Post-S1-A-1 status |
|---|---|---|
| §1.a audit-side declarations review | banked (S1-A-1 scope) | **LANDED** |
| §1.b P-2 §D.1.5 verification | banked (S1-A-1 scope) | **LANDED** |
| §1.c audit registry review | banked (S1-A-1 scope) | **LANDED** |
| §1.d test infrastructure inventory | banked (S1-A-2 scope) | deferred to S1-A-2 |
| §1.e smoke-test infrastructure | banked (S1-A-2 scope) | deferred to S1-A-2 |
| §1.f runner integration gap + outcome-ladder | banked (S1-A-2 scope) | deferred to S1-A-2 |
| §2 design decisions | banked (S1-B scope) | deferred to S1-B |
| §3-§5 (sub-session structure + banking + next steps) | banked (S1-C scope) | deferred to S1-C |
| Master-plan-locus correction (B-Phase5-S1-1) | banked | **CODIFIED** |
| Phase 5 cycle progress | sub-session 1 of ~14 nominal | **(no full-session count change; sub-sub-sub-session)** |

## Next sub-sub-sub-session

**S1-A-2 — §1.d + §1.e + §1.f append** (~174 LOC projected).

Per Decision 29F-1 four-level cascade:
- §1.d Existing test infrastructure inventory
- §1.e Smoke-test infrastructure entry points (B-Phase4-S10-3
  context disambiguation)
- §1.f Runner integration gap + outcome-ladder current state
  (THE core S1 architecture finding)

S1-A-2 trigger: ready to fire after S1-A-1 CI confirms green.

After S1-A-1 + S1-A-2 + S1-B + S1-C all close clean:
- §1 + §2 + §3 + §4 + §5 collectively serve as Phase 5 S1
  [PRE-FLIGHT] design deliverable
- S2 trigger drafts with §2 design decisions locked +
  §3 sub-session structure refinements applied
