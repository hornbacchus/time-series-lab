# Phase 5 Session 4-α — mint_family allowlist addition + harness wrapper expansion per per-wrapper field-availability protocol Case (i)

**Date:** 2026-05-07
**Scope:** First per-wrapper sub-session of heterogeneous group
(S4 = mint_family + transformer_attention + caviar_sav per
master plan v1.2 §15 S4); first Phase 5 sub-session adding
fast-tier wrapper to allowlist with empirical field VALUE
pre-verified per S4-α [PRE-FLIGHT] commit `d7e4cf7`. Per
Q-S4-α-rep-method=(α) mint_shrinkage representative method +
Q-S4-2=(α) sequential sub-session pattern + Q-S4-3=(α) standard
per-wrapper protocol. Per-wrapper field-availability protocol
**Case (i)** outcome (required field NOT exposed at run_tsl top
level pre-S4-α; harness wrapper expansion required).
**Status:** COMPLETE.

## §1 Implementation summary

**Harness wrapper expansion (`mint_family.py`):**
`run_tsl()` extended to compute `coherence_residual` via
mint_shrinkage representative method. Per S4-α [PRE-FLIGHT]
empirical investigation: mint_shrinkage produces
`y_tilde[:n_top] - S[:n_top] @ y_tilde[n_top:]` L2 norm = 0.0
exactly on real fixture (well within tolerance=1e-10).
Implementation reads mint_shrinkage `y_tilde` from
`per_method["mint_shrinkage"]` (already computed in
existing reconciliation loop), computes summing-constraint
violation L2 norm, exposes at top level. ~13 LOC harness
expansion (Case (i) handling per per-wrapper field-availability
protocol). Per Q-Field-α-2=(b) per-session scope discipline:
expose ONLY `coherence_residual`; per Q-Field-α-3=(b) NO
try/except defensive wrapper.

**Allowlist extension (`runner.py`):**
`_INVARIANTS_DISPATCH_ALLOWLIST` extends from 6-tuple (S2 trio
+ S3 MCMC SV pair) to 7-tuple including `3e_mint_family`. NO
check_base.py modification (S2-α-2-redux + S3 state preserved).

**Test extensions (`_test_s2_alpha_invariants_dispatch.py`):**
- `test_mint_family_real_dispatch` — real run_tsl; dispatch
  fires; `mint_coherence` checker returns PASS-deterministic
  (closed-form invariant class per S2-redux closed-form trio
  pattern; distinct from S3 MCMC SV stochastic loose-assertion
  pattern)
- `test_allowlist_gating` updated to verify 6-wrapper state
  (S2 trio + S3 MCMC SV pair + S4-α mint_family in;
  non-allowlist wrappers excluded)

## §2 Test summary

All 10 dispatch tests PASS:
- 3 S2 closed-form-numerical wrappers PASS-deterministic
- Allowlist gating verified at 6-wrapper state
- Cross-wrapper acceptance for S2 trio aggregate=PASS
- Dispatch BLOCK propagation verified
- 2 S3 MCMC SV smoke tests dispatch infrastructure verified
  (loose assertion; both BLOCK on real fixtures per S3 banking)
- Cross-wrapper acceptance for 2-wrapper MCMC SV class
- 1 S4-α mint_family smoke test PASS-deterministic
  (`coherence_residual=0.000e+00`; PASS @ 1e-10 tolerance)

**Local parity-fast tier verification** (cycle-wide standing
protocol per Q-S2-α-2-redux-followup-3=(a)): exit code 2
(CAVEAT; CI green per workflow YAML mapping). 5 pre-existing
CAVEATs preserved (`p3_emd_hht`, `p3_mstl`, `p3_nar_narx`,
`p3_star`, `p3_stl`); NO BLOCK; NO regressions. **`3e_mint_family`
PASS with `mint_coherence` invariant firing**:
`{'status': 'PASS', 'coherence_residual': 0.0, 'threshold': 1e-10}`.
Allowlist gating preserved for non-allowlist wrappers.

**§13.4 compliance:** S4-α commit delta verified at staging
time per Code's chunking judgment (single commit per Q3=a
single-commit-when-possible).

## §3 Banking entry — first Case (i) empirical observation

**B-Phase5-S4-α-CASE-i-FIRST-EMPIRICAL-OBSERVATION** — First
empirical Case (i) outcome per per-wrapper field-availability
protocol. At S4-α execution, Case (i) outcome empirically
observed (required field `coherence_residual` NOT exposed at
run_tsl top level pre-S4-α; harness wrapper expansion
required). First Case (i) observation in Phase 5 sequence:
S2-redux trio was Case (iii) (engine `audit_fields` exposed but
harness needed extraction); S3 MCMC SV pair was Case 0 (already
exposed at top level via prior elevation). Case (i) handling at
S4-α: representative method choice per Q-S4-α-rep-method=(α)
mint_shrinkage; pre-flight empirical field VALUE investigation
per S3 banking forward-looking refined the protocol scope
before execution-time authoring (verified deterministic 0.0
output on closed-form math; PASS @ 1e-10 tolerance trivially).
Cross-references:
B-Phase5-S2-α-1-redux-HARNESS-VS-ENGINE-EXPANSION (original
Case enumeration);
B-Phase5-PER-WRAPPER-PROTOCOL-CASE-0-EXTENSION at
`s3_amendment_banking.md` (Case 0 extension);
B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING (pre-flight
refinement origin);
S4-α [PRE-FLIGHT] commit `d7e4cf7`.
**Forward-looking:** Case enumeration empirically validated at
Cases 0 + (i) + (iii) across Phase 5 sequence; (ii) + (iv)
remain unobserved. Per-wrapper field-availability protocol
empirically robust to multiple Case outcomes. Future cycle
authors recognize Case (i) handling pattern: harness wrapper
expansion + representative method choice per pre-flight
empirical investigation. Pre-flight scope refinement (audit
field VALUE on standard fixtures when feasible) per S3 banking
forward-looking confirmed standing discipline at S4-α
execution.

## Disposition

S4-α first per-wrapper sub-session of heterogeneous group
COMPLETE under master plan v1.2 §15 S4 framing. **First Phase 5
sub-session adding fast-tier wrapper to allowlist with empirical
field VALUE pre-verified.** Per-wrapper field-availability
protocol Case (i) empirically observed + handled cleanly via
mint_shrinkage representative method. Banking entry codifies
first Case (i) empirical observation per Q-banking-categorical
strict.

S4-β transformer_attention pre-flight ahead per Q-S4-2=(α)
sequential pattern; pre-flight trigger drafting follows S4-α
execution closure + CI verification per established cycle-wide
protocol.
