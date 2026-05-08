# Phase 5 Session 4-β — transformer_attention allowlist addition + harness wrapper expansion per per-wrapper field-availability protocol Case (i) consecutive observation

**Date:** 2026-05-07
**Scope:** Second per-wrapper sub-session of heterogeneous group
(S4 = mint_family + transformer_attention + caviar_sav per
master plan v1.2 §15 S4); second Phase 5 sub-session adding
fast-tier wrapper to allowlist with empirical field VALUE
pre-verified per S4-β [PRE-FLIGHT] commits `e3b55c0` (investigation)
+ `ee6c973` (synthesis) + `cc053fd` (recalibration banking).
Per Q-S4-β-rep-layer=(layer-α) Layer 0 representative layer +
Q-S4-2=(α) sequential sub-session pattern + Q-S4-3=(α) standard
per-wrapper protocol. Per-wrapper field-availability protocol
**Case (i)** outcome (second consecutive Phase 5 observation;
first at S4-α mint_family).
**Status:** COMPLETE.

## §1 Implementation summary

**Harness wrapper expansion (`transformer_attention.py`):**
`run_tsl()` extended to expose `attention_matrix` field at top
level via Layer 0 representative layer. Per S4-β [PRE-FLIGHT]
empirical investigation (commits `e3b55c0` + `ee6c973`),
Layer 0 produces row-sum deviation ~3.65e-08 on real fixture
(well within tolerance=1e-6). Implementation reads
`per_layer[0]` from existing `attention_per_layer` list (already
populated in existing capture loop), exposes at top level. ~17
LOC harness expansion (Case (i) handling per per-wrapper field-
availability protocol; mirrors S4-α mint_family pattern at
analogous scope). Per Q-Field-α-2=(b) per-session scope
discipline: ONLY Layer 0 exposed; aggregation logic across
layers anticipatory-rejected. Per Q-Field-α-3=(b) NO try/except
defensive wrapper.

**Allowlist extension (`runner.py`):**
`_INVARIANTS_DISPATCH_ALLOWLIST` extends from 6-tuple (S2 trio
+ S3 MCMC SV pair + S4-α mint_family) to 7-tuple including
`3f_transformer_attention`. NO check_base.py modification (S2-α-
2-redux + S3 + S4-α state preserved).

**Test extensions (`_test_s2_alpha_invariants_dispatch.py`):**
- `test_transformer_attention_real_dispatch` — real run_tsl;
  dispatch fires; `attention_normalization` checker returns
  PASS-deterministic (closed-form structural invariant class
  per softmax row-sums = 1.0 by definition; Layer 0 empirical
  row-sum dev ~3.65e-08 well below 1e-6 threshold). Loose-
  assertion semantic NOT applied (parity-side
  `verdict_class="dl_seed_pinned"` orthogonal to structural
  invariant assertion semantic).
- `test_allowlist_gating` updated to verify 7-wrapper state
  (S2 trio + S3 MCMC SV pair + S4-α mint_family + S4-β
  transformer_attention in; non-allowlist wrappers excluded).

## §2 Test summary

All 11 dispatch tests PASS:
- 3 S2 closed-form-numerical wrappers PASS-deterministic
- Allowlist gating verified at 7-wrapper state
- Cross-wrapper acceptance for S2 trio aggregate=PASS
- Dispatch BLOCK propagation verified
- 2 S3 MCMC SV smoke tests dispatch infrastructure verified
  (loose assertion; both BLOCK on real fixtures per S3 banking)
- Cross-wrapper acceptance for 2-wrapper MCMC SV class
- 1 S4-α mint_family smoke test PASS-deterministic
  (`coherence_residual=0.000e+00`)
- 1 S4-β transformer_attention smoke test PASS-deterministic
  (`max_row_sum_deviation=3.654e-08`; PASS @ 1e-6 tolerance)

**Local parity-fast tier verification** (cycle-wide standing
protocol per Q-S2-α-2-redux-followup-3=(a)): exit code 2
(CAVEAT; CI green per workflow YAML mapping). 5 pre-existing
CAVEATs preserved; NO BLOCK; NO regressions.
**`3f_transformer_attention` PASS with `attention_normalization`
invariant firing**: `{'status': 'PASS',
'max_row_sum_deviation': 3.654e-08, 'threshold': 1e-6,
'matrix_shape': [1, 16, 16]}`. Allowlist gating preserved.

**§13.4 compliance:** S4-β commit delta verified at staging
time per Code's chunking judgment.

## §3 Banking entry — second consecutive Case (i) observation

**B-Phase5-S4-β-CASE-i-CONSECUTIVE-OBSERVATION** — Second
consecutive Case (i) outcome empirical observation in
heterogeneous group. At S4-β execution, Case (i) outcome
empirically observed for second consecutive time in Phase 5
sequence (S4-α mint_family was first per
B-Phase5-S4-α-CASE-i-FIRST-EMPIRICAL-OBSERVATION at
`session_4_alpha_findings.md`; S4-β transformer_attention is
second). Both wrappers in heterogeneous group required harness
expansion to expose required field at run_tsl top level +
representative method/layer choice (mint_family: mint_shrinkage
representative method per Q-S4-α-rep-method=(α);
transformer_attention: Layer 0 representative layer per
Q-S4-β-rep-layer=(layer-α)). **Pattern emerging: heterogeneous
group default = Case (i) with multi-component representative
choice.**

**Phase 5 Case enumeration coverage:** Cases 0 (S3 MCMC SV
pair) + (i)×2 (S4-α + S4-β) + (iii) (S2-redux trio) empirically
observed. Cases (ii) + (iv) remain unobserved.

**Cross-references:**
B-Phase5-S4-α-CASE-i-FIRST-EMPIRICAL-OBSERVATION at
`session_4_alpha_findings.md`;
B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION (original
Case enumeration);
B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-EXTENSION at
`s3_amendment_banking.md`;
B-Phase5-Q-OVERSHOOT-PREFLIGHT-RECALIBRATION at
`q_overshoot_recalibration_banking.md`;
S4-β [PRE-FLIGHT] commits `e3b55c0` + `ee6c973` + `cc053fd`.

**Forward-looking:** S4-γ caviar_sav pre-flight may surface
third consecutive Case (i) outcome OR different Case outcome
(INVERTED tolerance semantics per B-Phase4-S9-3 may interact
with Case determination). Empirically determined at S4-γ
pre-flight, not assumed. Heterogeneous-group default-Case
hypothesis empirically tested at S4-γ pre-flight per Q-S4-2=(α)
sequential standing. Pattern strengthening: representative-
component choice (method/layer/etc.) is the Case (i) handling
discipline; future Phase 6+ wrapper integrations expect
representative-component pattern when Case (i) outcome
empirically observed.

## Disposition

S4-β second per-wrapper sub-session of heterogeneous group
COMPLETE under master plan v1.2 §15 S4 framing. **Second Phase
5 sub-session adding fast-tier wrapper to allowlist with
empirical field VALUE pre-verified.** Per-wrapper field-
availability protocol Case (i) empirically observed for second
consecutive time + handled cleanly via Layer 0 representative
layer. Banking entry codifies consecutive-observation pattern
+ heterogeneous-group default-Case hypothesis per Q-banking-
categorical strict.

S4-γ caviar_sav pre-flight ahead per Q-S4-2=(α) sequential
pattern + Q-S4-3=(α) standard per-wrapper protocol. S4-γ
pre-flight projects ~200-240 LOC empirical baseline per
B-Phase5-Q-OVERSHOOT-PREFLIGHT-RECALIBRATION; cascading split
pre-authorized at §13.1 marginal-tolerance band engagement.
S4-γ Category 4 INVERTED tolerance check will identify
INVERTED handling per B-Phase4-S9-3 codification.
