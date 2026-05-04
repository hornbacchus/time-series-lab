# Phase 5 Session 1 (S1-A-1-a-CORRECTED) — §1.a + §1.b (Decision 30D revert + re-execute; framing-vs-content constraints)

**Date:** 2026-05-04
**Scope:** Re-execute S1-A-1-a per Decision 30D after S1-A-1-a
(commit `99bb534`) reverted at `8798624`. Constraints pre-
specified: framing minimum + banking deferral. §1.a + §1.b
content preserved verbatim from S1-A-1 ORIGINAL.
**Status:** COMPLETE.

S1-A-1-a (commit `99bb534`) landed at 205 LOC under
"saturation framing" band-absorption disposition — repeat
institutional-inconsistency pattern. Decision 30D revert +
re-execute with framing-vs-content distinction pre-specified;
all banking entries deferred to S1-A-1-b combined codification.
Two-revert sequence on same logical session banked at S1-C
per Decision 29F sequencing.

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
to S1-A-1-b per Decision 30D sequencing).

### §1.b P-2 §D.1.5 audit-side wrapper-declaration table verification

P-2 §D.1.5 audit-side declaration table coherence verified
against `ff403dd` commit message; no drift. Tolerance values
in §1.a table match P-2 §D.1.5 table exactly. INVERTED
semantics for `caviar_sav` codified at P-2 §D per
B-Phase4-S9-3.

**§13.4 compliance:** S1-A-1-a-CORRECTED +74 net LOC; 63%
headroom under §13.1 default 200; clean per §13.1 default;
no marginal-tolerance band engagement.

## Disposition

§1.c deferred to S1-A-1-b. Banking entries (B-Phase5-S1-1 +
B-Phase5-S1-A-1-CLASSIFICATION-ERROR + B-Phase5-S1-A-1-TRIGGER-LANGUAGE
+ B-Phase5-S1-A-1-a-SECOND-CLASSIFICATION-ERROR +
B-Phase5-S1-A-1-a-OVERHEAD-EXPANSION) deferred to S1-A-1-b
combined codification per Decision 30D sequencing.
