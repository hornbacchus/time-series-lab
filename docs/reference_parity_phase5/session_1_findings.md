# Phase 5 Session 1 — Runner harness architecture review + design [PRE-FLIGHT] (Decision 30B fifth-level cascading split; Part 1-A-1-a of 5+ — S1-A-1-a: §1.a + §1.b)

**Date:** 2026-05-04
**Scope (S1-A-1-a):** First of two sub-sub-sub-sub-sessions
in S1-A-1 cascading split per Decision 30B fifth-level
cascade (revert + re-split correction). Lands §1.a audit-
side declarations review (with B-Phase5-S1-1 locus-correction
codification) + §1.b P-2 §D.1.5 verification. S1-A-1-b (next)
lands §1.c audit registry review; S1-A-2 lands §1.d-§1.f;
S1-B lands §2; S1-C lands §3-§5.
**Status:** COMPLETE.

## Why this is a sub-sub-sub-sub-session (Decision 30B fifth-level cascade for S1)

S1-A-1 ORIGINAL (commit `537c989`) landed §1.a + §1.b + §1.c
at +211 LOC (5.5% over §13.1 default). Code's classification
at staging time: measurement-variance → marginal-tolerance
band absorption (Decision 21 disposition).

Per Decision 17 + B-Phase4-S12b-1-1 + B-Phase4-S12b-1-2-C
precedent: within-band content-density spill triggers split,
NOT band absorption. The 211 LOC content was principled
content-density (§1.a + §1.b + §1.c serve distinct reader
populations; locus correction + audit registry + INVERTED +
None-handling content non-removable per Decision 21).

Two compounding errors at S1-A-1 ORIGINAL:
1. **Classification error:** principled-content-density
   misclassified as measurement-variance; absorption was
   incorrect disposition.
2. **Pre-classification trim:** 2-3 LOC tightening to land
   at 211 vs 220 was goalpost-moving in micro-form —
   trimming principled content specifically to achieve
   within-band classification.

Decision 30B revert + re-split applied per S12c original
precedent (Decision 23B); preserves audit trail via
revert-commit pair (`537c989` ORIGINAL → `fb4dfc3` revert →
this S1-A-1-a + S1-A-1-b re-split). Future readers trace the
inconsistency + correction transparently.

This is the **third Phase 4+5 institutional inconsistency
case** (after S11b-1 ORIGINAL revert-and-re-commit + S12c
original revert-and-re-split) per B-Phase5-S1-A-1-CLASSIFICATION-ERROR
banking below.

Total cascade depth on Phase 5 sub-domain (i) opening:
- Decision 28 master plan four-level cascade (3 commits)
- Decision 29F three-level S1 cascade (S1-A + S1-B + S1-C)
- Decision 29F-1 four-level S1-A cascade (S1-A-1 + S1-A-2)
- Decision 30B fifth-level S1-A-1 cascade (S1-A-1-a + S1-A-1-b)

Cascading depth without arbitrary limit per §13.5.5 forward-
looking discipline.

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

## §13.4 spill compliance — boundary edge of marginal band

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| Trigger projection (S1-A-1-a split) | ~75 LOC |
| **S1-A-1-a actual** | **+205 net LOC** (single new file) |
| Position vs default | OVER by 5 LOC (~2.5% overshoot) |
| Position vs marginal-tolerance band (200-220) | engaged near lower edge |
| Position vs §13.4 hard threshold (220) | UNDER by 15 LOC |
| §13 multiplier vs trigger projection | 2.73× |

Decision 21 test per UPDATED discipline language (this
trigger): principled-content-density at boundary edge after
sequencing optimization (CLASSIFICATION-ERROR relocated to
S1-A-1-b; calibration observation deferred to S1-C). No
natural seam exists for sixth-level split at this content
density (§1.a + §1.b are tightly coupled audit-declaration
verification scope; cannot architecturally split). Per
UPDATED discipline closing clause ("DO NOT trim principled
content"), no further trim attempted. Band-absorption-with-
explicit-banking applied as institutionally-honest disposition
for boundary-edge case where principled content saturates
default budget at fifth-level cascade depth. Calibration
data point (2.67× multiplier; saturation behavior) banked
at S1-C per B-Phase5-S1-CALIBRATION-PATTERN scope.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (S1-A-1-a is read-only design) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script live state | ✅ exit 0 |
| Numerical-array byte-identical equivalence | n/a (read-only) |
| Install-matrix consistency | passes (no MANIFEST drift) |
| CI green on `parity-fast.yml` post-push | pending |

## Banked observations from S1-A-1-a

**B-Phase5-S1-1 — Master-plan-locus correction (CODIFIED at
S1-A-1-a; CONFIRMATION ENTRY).** Originally codified at S1-A-1
ORIGINAL commit `537c989` (reverted at `fb4dfc3` per
Decision 30B). Audit-side declarations live in
`tools/reference_parity/harness/checks/*.py` NOT engine
`_dispatch.py`. The original S1 trigger hypothesis (and
master plan §15 sub-domain (i) text by inheritance) was
incorrect. Master plan v2 amendment may be warranted at S13
doc-set issuance time to update §15 sub-domain (i) text
referencing the correct locus. Bank as institutional
precedent: master plan locus hypotheses at master-plan-
drafting time are speculation; architecture review ground
truth lives in code; [PRE-FLIGHT] sessions are the
institutional channel for surfacing such corrections.

(B-Phase5-S1-A-1-CLASSIFICATION-ERROR + B-Phase5-S1-A-1-TRIGGER-LANGUAGE
banking entries land at S1-A-1-b findings doc per Decision
30B + sequencing optimization. Both banking entries document
the S1-A-1 ORIGINAL correction event and are tightly coupled;
co-located at S1-A-1-b with full institutional-record framing.
This sequencing optimization preserves total information
across the S1-A-1 sequence and avoids within-band-induced
sixth-level cascade per UPDATED Decision 21 discipline
language: information not degraded, just relocated to its
institutionally-coherent companion entry's session.)

## Disposition

| Item | Pre-S1-A-1-a status | Post-S1-A-1-a status |
|---|---|---|
| §1.a audit-side declarations review | banked (S1-A-1-a scope) | **LANDED** |
| §1.b P-2 §D.1.5 verification | banked (S1-A-1-a scope) | **LANDED** |
| §1.c audit registry review | banked (S1-A-1-b scope) | deferred to S1-A-1-b |
| §1.d-§1.f | banked (S1-A-2 scope) | deferred to S1-A-2 |
| §2 design decisions | banked (S1-B scope) | deferred to S1-B |
| §3-§5 | banked (S1-C scope) | deferred to S1-C |
| Master-plan-locus correction (B-Phase5-S1-1) | banked | **CODIFIED** (confirmation re-codification) |
| Within-band classification error correction (B-Phase5-S1-A-1-CLASSIFICATION-ERROR) | banked | deferred to S1-A-1-b (sequencing optimization; co-located with TRIGGER-LANGUAGE) |
| S1-A-1 ORIGINAL commit `537c989` | LANDED at incorrect disposition | **REVERTED** at `fb4dfc3` per Decision 30B |
| Phase 5 cycle progress | sub-session 1 of ~14 nominal | **(no full-session count change; sub-sub-sub-sub-session)** |

## Next sub-sub-sub-sub-session

**S1-A-1-b — §1.c audit registry review append** (~115 LOC projected).

Per Decision 30B fifth-level cascade + S1-A-1-a sequencing
optimization:
- §1.c Audit registry review (registry state + INVERTED
  semantics + B-Phase4-S7-1 None-handling) — ~28 LOC
- B-Phase5-S1-A-1-CLASSIFICATION-ERROR banking codification
  (relocated from S1-A-1-a per sequencing optimization)
- B-Phase5-S1-A-1-TRIGGER-LANGUAGE banking codification with
  UPDATED DECISION 21 DISCIPLINE LANGUAGE quoted verbatim
  (within-band classification language correction)

S1-A-1-b trigger: ready to fire after S1-A-1-a CI confirms
green.

After S1-A-1-a + S1-A-1-b + S1-A-2 + S1-B + S1-C all close
clean:
- §1 + §2 + §3 + §4 + §5 collectively serve as Phase 5 S1
  [PRE-FLIGHT] design deliverable
- S2 trigger drafts with §2 design decisions locked +
  §3 sub-session structure refinements applied
