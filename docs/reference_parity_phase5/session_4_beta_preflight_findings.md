# Phase 5 Session 4-β [PRE-FLIGHT] Synthesis — transformer_attention smoke semantic + allowlist context + execution scope (Categories 5-7 + disposition)

**Date:** 2026-05-07
**Scope:** Pre-flight synthesis findings (Categories 5-7 +
disposition) per Q-S4-β-preflight-overshoot=(γ) cascading
2-commit split + Q-S4-β-preflight-overshoot-split=(split-α)
§1-§4 / §5-§7+disposition categorical seam. Investigation
findings (Categories 1-4) co-located at companion investigation
doc `session_4_beta_preflight_investigation.md`. Synthesis
references investigation findings; reader should consult both
docs for complete pre-flight scope.
**Status:** COMPLETE.

## §5 Smoke test semantic determination (Category 5)

Per B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE:

`transformer_attention` `verdict_class = "dl_seed_pinned"` —
this is the PARITY verdict class (TSL vs reference). The
STRUCTURAL INVARIANT `attention_normalization` is a separate
check on softmax-output mathematical properties (row-sums = 1.0
by softmax definition; value range [0, 1]). Closed-form
deterministic given model + input + frozen weights +
`model.eval()`.

Empirical investigation (companion investigation doc §2)
confirms both layers produce row-sum dev ~3-5e-08 (well below
1e-6); deterministic per softmax math.

**Smoke test semantic for structural invariant: closed-form
deterministic.** PASS-deterministic assertion appropriate per
S2-redux closed-form trio + S4-α mint_family pattern. Distinct
from S3 MCMC SV stochastic loose-assertion pattern. Note: the
parity-side `verdict_class = "dl_seed_pinned"` reflects the
parity comparison (TSL attention capture vs native MHA bit-
exact); orthogonal to the structural invariant assertion
semantic.

## §6 Allowlist addition decision context (Category 6)

Context for S4-β execution allowlist addition decision:
- **Field availability:** Case (i); harness wrapper expansion
  ~5-15 LOC required (compute representative layer's attention
  matrix; expose at run_tsl top level)
- **Tier classification:** fast-tier; direct CI parity-fast
  impact (mirrors S4-α mint_family)
- **Field VALUE satisfaction:** verified empirically (both
  layers PASS at 3-5e-08 row dev; well below 1e-6 threshold)
- **Smoke test semantic:** PASS-deterministic per closed-form
  invariant class
- **INVERTED tolerance:** N/A (STANDARD)
- **Architectural decision pending:** representative layer choice
  for `attention_matrix` exposure (Code recommends layer 0 per
  simplest convention + S4-α single-element representative
  pattern)

## §7 S4-β execution scope determination (Category 7)

**S4-β envelope projection** under no-engine-work scope + Case (i)
harness expansion:

| Class | Projection |
|---|---|
| Implementation (allowlist + harness expansion) | ~6-16 LOC |
| Tests (per-wrapper smoke + 7-wrapper allowlist gating update) | ~25-30 LOC (closed-form PASS-deterministic per S2-redux + S4-α baseline) |
| Findings doc | ~30-50 LOC |
| Banking (per Q-banking-categorical strict) | 0-50 LOC depending on surfacings |

**Combined estimate: ~60-145 LOC** — clean per §13.1 default
200 LOC by 27-70% headroom.

**Critical empirical-validation envelope assessment:** S2-redux
+ S3 + S4-α sequence empirical record (10/10 prior-session
commits clean with cascading-split discipline at marginal-
tolerance band engagement; per-wrapper field-availability
protocol validated at trio + pair + single-wrapper scope across
Cases 0/(i)/(iii)) supports S4-β projection accuracy. No
architectural ambiguities surfaced beyond representative-layer
choice (deferred to S4-β execution authoring; empirically
benign per equivalent PASS outcomes across layers).

**Per-wrapper default applies:** S4-β single sub-session per
transformer_attention; caviar_sav at S4-γ per Q-S4-2=(α)
sequential disposition.

**§13.4 compliance:** Synthesis commit delta verified at
staging time per Code's chunking judgment (3-commit cascading
split per Q-S4-β-preflight-overshoot=(γ) disposition).

## Disposition

S4-β [PRE-FLIGHT] audit COMPLETE (investigation + synthesis +
recalibration banking across 3 commits). Investigation surfaced:
- Engine work scope: 0 LOC (engine capture infrastructure
  pre-existing per Phase 4 codification; harness uses directly
  via `_patch_sa_blocks_for_capture` + `_restore_sa_blocks`)
- Harness wrapper expansion: Case (i); ~5-15 LOC to expose
  `attention_matrix` at run_tsl top level via representative
  layer (Code recommends layer 0)
- Field VALUE satisfies invariant tolerance trivially
  (closed-form softmax math; both layers PASS at 3-5e-08 row
  dev; well below 1e-6 threshold)
- Tier classification: fast-tier; direct CI parity-fast impact
  (mirrors S4-α mint_family scenario)
- Smoke test semantic: PASS-deterministic per closed-form
  structural invariant class
- INVERTED tolerance: STANDARD confirmed
- Architectural decision pending S4-β execution: representative
  layer choice for `attention_matrix` exposure (Code recommends
  layer 0 per simplest convention)
- Second Case (i) observation in Phase 5 sequence (first at
  S4-α mint_family); Q-S4-β-preflight-3=(α) "genuinely novel"
  threshold NOT met for banking codification at pre-flight
  proper (per S3 + S4-α pre-flight precedent of no banking
  despite substantive findings; Case (i) repeat is empirical
  pattern validation, not novel)

S4-β execution trigger ahead per Chat dispositions pending
post-pre-flight closure per established discipline. Cycle-wide
parity-fast tier verification + CI verification protocol both
standing apply.

S4-γ caviar_sav pre-flight follows S4-β execution closure +
CI verification per Q-S4-2=(α) sequential standing.
