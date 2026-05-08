# Phase 5 Session 5 [PRE-FLIGHT] — cross-wrapper acceptance scope audit + sub-domain (i) closure marker

**Date:** 2026-05-08
**Scope:** First cross-wrapper acceptance pre-flight per Q-S5-1=
(α) + Q-S5-2=(γ) (mit-iii) drift-evidence-driven activation +
Q-S5-3=(δ) reserve sub-domain deferral. Pre-flight prospective
discipline extended from per-wrapper sub-session scope to
cross-wrapper acceptance scope. Sub-domain (i) per-wrapper
integration COMPLETE post-S4-γ (`8526ee0`); 8-wrapper allowlist
active across 3 invariant classes. Mitigation paths (mit-ii) +
(mit-iv) applied at authoring per
B-Phase5-PRE-FLIGHT-MITIGATION-PATH-ACTIVATION at `75e9fcf`.
S5 pre-flight serves as both substantive cross-wrapper scope
investigation + (mit-iii) activation criteria empirical
measurement.
**Status:** COMPLETE.

## §1 Cross-wrapper test infrastructure audit (Category 1)

**Existing test infrastructure** (per S2-β-redux + S3
establishment; brief mentions per (mit-ii)):
- `_test_s2_alpha_invariants_dispatch.py` (12 dispatch tests
  including 8 per-wrapper smoke tests + 1 allowlist gating +
  1 BLOCK propagation + 2 per-class cross-wrapper acceptance
  tests)
- `test_cross_wrapper_acceptance` (lines 228-271): 3-wrapper
  closed-form trio (kalman+johansen+evt); asserts aggregate=PASS
- `test_cross_wrapper_acceptance_mcmc_sv` (S3 addition):
  2-wrapper MCMC SV pair; asserts aggregate in valid statuses
  (loose-assertion per S3 banking)
- `aggregate_outcomes` from `reference_parity.harness.base`
  provides aggregation ranking (PASS < CAVEAT < BLOCK < ERROR)

**Coverage gaps for sub-domain (i) closure:**
- mint_family + transformer_attention + caviar_sav NOT covered
  by existing 3-wrapper closed-form test (post-S4 additions
  not retrofitted)
- No omnibus 8-wrapper acceptance test exercising full
  sub-domain (i) coverage
- INVERTED tolerance class not represented in cross-wrapper
  test (only S4-γ per-wrapper smoke covers caviar_sav)

**Test infrastructure scales to 8-wrapper coverage** without
architectural changes; existing patterns extend cleanly.

## §2 Cross-wrapper aggregation logic verification (Category 2)

**Three structural options for S5 execution:**

- **Option A: Single 8-wrapper omnibus acceptance test** —
  exercise all 8 wrappers; aggregate via `aggregate_outcomes`.
  MCMC SV BLOCK outcomes (per S3 banking) propagate to
  aggregate=BLOCK; closed-form + INVERTED PASS contribute. Per
  current MCMC SV BLOCK reality, omnibus aggregate would be
  BLOCK; assertion needs loose-assertion semantic at omnibus
  scope.
- **Option B: Three per-class tests** — extend existing
  `test_cross_wrapper_acceptance` to 5-wrapper closed-form
  scope (add mint+transformer+caviar); preserve
  `test_cross_wrapper_acceptance_mcmc_sv` 2-wrapper scope; add
  new `test_cross_wrapper_acceptance_inverted` 1-wrapper scope.
  Per-class assertion semantics preserved (closed-form
  PASS-deterministic; MCMC loose; INVERTED PASS-deterministic).
- **Option C: Mixed** — preserve existing per-class tests +
  add omnibus 8-wrapper test with loose-assertion semantic at
  omnibus scope. Maximizes test coverage.

**Code's recommendation: Option B (three per-class tests).**
Reasoning: per-class semantic clarity preserved; aggregation
logic each test exercises a single semantic class; omnibus
test would muddy per-class semantics without adding
architectural verification (aggregation logic is the same
function across all tests).

**Architectural decision (deferred to S5 execution-time
authoring):** structural choice between A/B/C per Code's
structural judgment + Chat disposition if surface warrants.

## §3 Allowlist gating preservation verification scope (Category 3)

**Existing coverage:** `test_allowlist_gating` (lines 132-180)
verifies 8-wrapper allowlist state + non-allowlist exclusion
(`p3_arima` test). Updated at S4-γ to verify 8-wrapper state.

**S5 scope addition:** none required at test-infrastructure
level. `test_allowlist_gating` continues to be the canonical
allowlist gating verification; preserved across cross-wrapper
acceptance scope expansion.

**Parity-fast tier integration:** local parity-fast tier sweep
+ CI workflow already exercise allowlist gating in production
context (only allowlisted wrappers fire dispatch step 4.5;
non-allowlist wrappers complete parity-fast without dispatch).
Empirically verified at every Phase 5 sub-session local +
CI run.

## §4 Sub-domain (i) closure marker (Category 4)

**Sub-domain (i) per-wrapper integration COMPLETE confirmed.**
8-wrapper allowlist final state per S4-γ commit `8526ee0`:

| Wrapper ID | Class | Case |
|---|---|---|
| 2a_kalman_filter_smoother | closed-form deterministic | (iii) |
| 3d_johansen_bartlett | closed-form deterministic | (iii) |
| 3c_evt_ferro_segers | closed-form deterministic | (iii) |
| 2b_mcmc_sv_gaussian | MCMC stochastic | 0 |
| 2c_mcmc_sv_student_t | MCMC stochastic | 0 |
| 3e_mint_family | closed-form deterministic | (i) |
| 3f_transformer_attention | closed-form deterministic | (i) |
| 3a_caviar_sav | INVERTED tolerance | (i) variant |

**3 invariant classes empirically covered:**
- Closed-form deterministic (5 wrappers): kalman + johansen +
  evt + mint + transformer
- MCMC stochastic (2 wrappers): gaussian + student_t
- INVERTED tolerance (1 wrapper): caviar_sav

**Phase 5 cycle position post-S5:** S5 closes sub-domain (i);
sub-domains (ii) + (iii) + (iv) reserve per Q-S5-3=(δ)
deferral; Phase 5 close OR reserve sub-domain trigger per
Chat disposition post-S5.

## §5 S5 execution scope determination (Category 5)

**S5 envelope projection** under existing test infrastructure
+ Option B recommended (per §2):

| Class | Projection |
|---|---|
| Implementation | 0 LOC (no engine; no wrapper modifications) |
| Tests | ~50-80 LOC (extend existing closed-form acceptance test from 3 to 5 wrappers + new 1-wrapper INVERTED test + main() updates) |
| Findings doc | ~50-90 LOC |
| Banking | 0-100 LOC (sub-domain (i) closure milestone candidate per Q-banking-categorical strict) |

**Combined estimate: ~100-270 LOC** — clean per §13.1 default
200 LOC at lower bound; engages marginal-tolerance band at
upper bound; cascading split pre-authorized per (mit-i)
standing.

**Architectural decisions pending S5 execution:**
- Aggregation structure choice (Option A/B/C per §2)
- Sub-domain (i) closure banking entry (Code's structural
  judgment per Q-banking-categorical strict; closure milestone
  candidate)

## Disposition

S5 [PRE-FLIGHT] audit COMPLETE. Investigation surfaced:
- Cross-wrapper test infrastructure pre-existing; scales to
  8-wrapper coverage without architectural changes
- Aggregation logic verified; three structural options for
  cross-wrapper test scope (Option B recommended for per-class
  semantic clarity)
- Allowlist gating preservation already covered by existing
  `test_allowlist_gating`; no new infrastructure needed
- Sub-domain (i) per-wrapper integration COMPLETE confirmed;
  8-wrapper allowlist + 3 invariant class diversity documented
- S5 execution scope ~100-270 LOC; cascading split
  pre-authorized at marginal-tolerance band

**(mit-iii) activation criteria empirical measurement per Q-S5-
2=(γ):** S5 pre-flight findings doc landed at **180 LOC**
(actual at staging) — well within reduced scope vs
recalibration V2 baseline ~250-310 LOC. Clean per §13.1
default 200 LOC by ~10% headroom. **Mitigation activation
EFFECTIVE at cross-wrapper scope; (mit-iii) NOT activated at
S5; deferred to Phase 5 close per (mit-v) implicit fallback.**
Single commit per Q3=a single-commit-when-possible. Drift
evidence INSUFFICIENT per Q-S5-2=(γ) thresholds.

S5 execution trigger ahead per Chat dispositions pending
post-pre-flight closure. After S5 execution closes + CI green,
**sub-domain (i) closed per master plan v1.2 §15 S5 framing.**
Phase 5 close OR reserve sub-domain trigger per Chat
disposition; Q-S5-3=(δ) reserve sub-domain disposition deferred
entirely per disposition.

**§13.4 compliance:** Pre-flight commit delta verified at
staging time per Code's chunking judgment.
