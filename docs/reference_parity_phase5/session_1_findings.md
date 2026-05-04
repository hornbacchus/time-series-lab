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
gap (S1-A-2 §1.f scope); becomes empirical once invariants
fire.

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

**§13.4 compliance:** S1-A-1-b +51 net LOC (72 insertions,
21 deletions); 74.5% headroom under §13.1 default 200;
clean per §13.1 default; no marginal-tolerance band
engagement. Doc cumulative: 126 LOC.

## Disposition

§1.a + §1.b + §1.c LANDED across S1-A-1-a-CORRECTED + S1-A-1-b
sequence. All 5 banking entries (B-Phase5-S1-1 +
B-Phase5-S1-A-1-CLASSIFICATION-ERROR +
B-Phase5-S1-A-1-TRIGGER-LANGUAGE +
B-Phase5-S1-A-1-a-SECOND-CLASSIFICATION-ERROR +
B-Phase5-S1-A-1-a-OVERHEAD-EXPANSION) deferred to S1-A-1-c
combined codification per Decision 30D + Option β
sequencing. §1.d-§1.f deferred to S1-A-2; §2 to S1-B;
§3-§5 + B-Phase5-S1-CALIBRATION-PATTERN to S1-C.
