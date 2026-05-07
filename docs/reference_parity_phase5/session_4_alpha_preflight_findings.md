# Phase 5 Session 4-α [PRE-FLIGHT] — mint_family scope audit per heterogeneous group per-wrapper sub-session standing discipline

**Date:** 2026-05-07
**Scope:** Pre-flight design-class audit per Q-S4-1=(α) S4-α
pre-flight + Q-S4-α-preflight-1=(γ) per-sub-session pre-flight
+ Q-S4-α-preflight-2=(α) doc-only pre-flight per S3 pre-flight
precedent. First per-wrapper sub-session of heterogeneous group
(S4-β + S4-γ investigated at respective pre-flights when
triggered). 3-criteria gate Criterion 1 NOT satisfied across
group (no analytical-class cohesion); per-wrapper default
applies. Pre-flight investigates mint_family-specific dimensions
to surface architectural concerns before S4-α execution scope
determined.
**Status:** COMPLETE.

## §1 Engine state audit (Category 1)

**Engine module located:** `engine/techniques/forecast_reconciliation.py`
(imported by harness wrapper as `fr`).

**Engine-side state audit:** Engine wrapper exposes
`coherence_post_reconciliation_L2` + `coherence_post_reconciliation_max`
fields in `audit_fields` dict (lines 704-711) per Phase 4
codification. Values rounded to 6 decimals (round(value, 6)).
Engine also exposes pre-reconciliation coherence (lines 696-703).

**Harness wrapper engine-call pattern:** Harness wrapper bypasses
engine wrapper's `run()` method entirely; calls helper functions
directly (`fr._estimate_W_matrix()` + `fr._mint_reconcile()` per
4 methods at lines 154-155 of `mint_family.py`). Therefore does
NOT extract from engine `audit_fields`.

**Engine work scope for S4-α: ~0 LOC.** No engine modifications
required. S4-α scope reduces to harness wrapper expansion +
allowlist addition + per-wrapper smoke test.

**No blocking issues** identified. Engine implementation
production-ready; reference triangulation (R `hts::MinT` + Python
`hierarchicalforecast.MinTrace`) integrated at harness; fixture
data (`3e_mint`) extant per Phase 1 + Phase 3 codification.

## §2 Harness wrapper field-availability investigation (Category 2)

**Harness wrapper located:** `tools/reference_parity/harness/checks/mint_family.py`
(`MintFamilyParity` class at line 89; `technique_id = "3e_mint_family"`;
`fixture_id = "3e_mint"`; `tier = "fast"`).

**`structural_invariants` declaration** (Phase 4 S9 dormant
declaration extant per P4-1.3 codification at lines 114-121):
- `mint_coherence` invariant; `tolerance=1e-10`; `tolerance_type="absolute"`

**`_check_mint_coherence` checker (single-side per
`structural_invariants.py` line 933):** Consumes `tsl["coherence_residual"]`
(float, required; BLOCK if missing). PASS if `abs(residual) <= 1e-10`;
CAVEAT if `<= 10e-10`; BLOCK otherwise.

**Field-availability investigation per S2-redux protocol:**

`run_tsl()` (lines 174-177) currently returns
`{"per_method": ..., "lambda_shrinkage": ...}`. **Required field
`coherence_residual` NOT exposed at top level.**

**Empirical investigation on real fixture (read-only execution):**
Computed coherence violation L2 norm per method against
`y_tilde[:n_top] - S[:n_top] @ y_tilde[n_top:]`:

| Method | L2 | max_abs | Disposition |
|---|---|---|---|
| ols | 0.000e+00 | 0.000e+00 | PASS @ 1e-10 |
| wls_variance | 0.000e+00 | 0.000e+00 | PASS @ 1e-10 |
| mint_shrinkage | 0.000e+00 | 0.000e+00 | PASS @ 1e-10 |
| mint_sample | FAILED | — | RankDeficientWMatrixError (B1 guard fires) |

**Case determination:** Case (i) — required field NOT exposed at
top level; harness wrapper expansion required (~5-10 LOC;
compute L2 norm post-reconciliation per representative method).

**Architectural decision (deferred to S4-α execution-time
authoring):** which method's `coherence_residual` to expose at
top level. Three options:
- Option A: `mint_shrinkage` (Phase 1 audit precedent at 4.66e-15;
  most commonly cited MinT variant; single canonical value)
- Option B: max across methods (defensive worst-case)
- Option C: per-method nested (requires multi-coherence invariant
  not currently supported)

Empirical evidence supports Option A (mint_shrinkage); 3/4
methods produce L2=0.0 exactly on fixture; mint_sample fails via
B1 rank-deficient guard (engine fallback would activate at full
engine path; bypassed at harness direct-helper path). Pre-flight
finding: field VALUE satisfies invariant tolerance trivially
(deterministic 0.0 on closed-form math) per Q-S3-MCMC-SV-ESS-
EMPIRICAL-FINDING surface refinement (audit field VALUE behavior
at pre-flight when feasible).

## §3 Tier classification + parity-slow latent risk (Category 3)

**Tier classification:** `tier = "fast"` (line 93 of mint_family.py).
Direct CI parity-fast impact upon allowlist addition.

**Parity-slow latent risk per B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-
LATENT-RISK:** N/A for fast-tier wrapper. Fast-tier allowlist-active
dispatch produces direct parity-fast CI impact (not parity-slow
latent). Field VALUE satisfaction MUST be verified pre-allowlist-
add — verified per §2 (3/4 methods produce L2=0.0; closed-form
deterministic; PASS @ 1e-10 trivially).

**No latent CI risk identified.** Fast-tier allowlist addition
safe given empirical field VALUE satisfaction.

## §4 INVERTED tolerance verification (Category 4)

Per B-Phase4-S9-3 codification: INVERTED tolerance applies ONLY
to caviar_sav (S4-γ scope). mint_family `_check_mint_coherence`
checker at `structural_invariants.py` lines 952-970:
`status = "PASS" if residual_f <= threshold` — STANDARD tolerance
semantic (smaller values are better).

**mint_family confirmed STANDARD (not INVERTED).** No B-Phase4-
S9-3 codification revisit required.

## §5 Smoke test semantic determination (Category 5)

Per B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE:

`mint_family` `verdict_class = "closed_form"` (line 97);
`verdict_class_rationale` cites Phase 1 audit at 4.66e-15 abs vs
hts on mint_shrinkage (closed-form matrix algebra deterministic
on well-behaved fixtures). Empirical investigation §2 confirms
3/4 methods produce L2=0.0 exactly.

**Smoke test semantic: closed-form deterministic.** PASS-deterministic
assertion appropriate per S2-redux closed-form trio pattern (kalman
+ johansen + evt). Distinct from S3 MCMC SV stochastic status-
variable pattern (loose assertion).

## §6 Allowlist addition decision context (Category 6)

Context for S4-α execution allowlist addition decision:
- **Field availability:** Case (i); harness wrapper expansion
  ~5-10 LOC required (compute L2 norm + expose `coherence_residual`
  at run_tsl top level)
- **Tier classification:** fast-tier; direct CI parity-fast impact
- **Field VALUE satisfaction:** verified empirically (3/4 methods
  L2=0.0; mint_sample fails via B1 guard but mint_shrinkage chosen
  as canonical representative)
- **Smoke test semantic:** PASS-deterministic per closed-form class
- **INVERTED tolerance:** N/A (STANDARD)
- **Architectural decision pending:** representative method choice
  for `coherence_residual` exposure (Code recommends mint_shrinkage
  per Phase 1 audit precedent + empirical 0.0 outcome)

## §7 S4-α execution scope determination (Category 7)

**S4-α envelope projection** under no-engine-work scope + Case (i)
harness expansion:

| Class | Projection |
|---|---|
| Implementation (allowlist + harness expansion) | ~10-15 LOC |
| Tests (per-wrapper smoke) | ~25-35 LOC (closed-form PASS-deterministic per S2-redux baseline) |
| Findings doc | ~30-50 LOC |
| Banking (per Q-banking-categorical strict) | 0-50 LOC depending on surfacings |

**Combined estimate: ~65-150 LOC** — clean per §13.1 default
200 LOC by 25-67% headroom.

**Critical empirical-validation envelope assessment:** S2-redux +
S3 sequence empirical record (8/8 prior-session commits clean
with cascading-split discipline at calibration-error events;
per-wrapper field-availability protocol validated at trio + pair
scope) supports S4-α projection accuracy. No architectural
ambiguities surfaced beyond representative-method choice (deferred
to S4-α execution authoring).

**Per-wrapper default applies:** S4-α single sub-session per
mint_family; transformer_attention + caviar_sav at S4-β + S4-γ
respectively per Q-S4-1=(α) per-wrapper sub-session disposition.

**§13.4 compliance:** Pre-flight commit delta verified at staging
time per Code's chunking judgment.

## Disposition

S4-α [PRE-FLIGHT] audit COMPLETE. Investigation surfaced:
- Engine work scope: 0 LOC (engine elevation pre-existing per
  Phase 4 codification; harness bypasses engine `run()` method)
- Harness wrapper expansion: Case (i); ~5-10 LOC to compute
  + expose `coherence_residual` at run_tsl top level
- Field VALUE satisfies invariant tolerance trivially
  (closed-form deterministic 0.0 on 3/4 methods)
- Tier classification: fast-tier; direct CI parity-fast impact
- Smoke test semantic: PASS-deterministic per closed-form class
- INVERTED tolerance: STANDARD confirmed
- Architectural decision pending S4-α execution: representative
  method choice (Code recommends mint_shrinkage per Phase 1
  precedent)

S4-α execution trigger ahead per Q-S4-2 + Q-S4-3 dispositions
pending Chat surfacing post-pre-flight closure per established
discipline. Cycle-wide parity-fast tier verification + CI
verification protocol both standing apply.
