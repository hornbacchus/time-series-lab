# Phase 5 Session 4-β [PRE-FLIGHT] Investigation — transformer_attention engine + harness + tier + INVERTED audit (Categories 1-4)

**Date:** 2026-05-07
**Scope:** Pre-flight investigation findings (Categories 1-4)
per Q-S4-1=(α) standing + Q-S4-2=(α) sequential + Q-S4-α-preflight-1=
(γ) per-sub-session standing + Q-S4-β-preflight-1=(γ) Code's
structural judgment per Option E + Q-S4-β-preflight-overshoot=
(γ) cascading 2-commit split + Q-S4-β-preflight-overshoot-split=
(split-α) §1-§4 / §5-§7+disposition categorical seam. Second
per-wrapper sub-session of heterogeneous group; per-wrapper
default applies. Synthesis findings (Categories 5-7 + disposition)
co-located at companion synthesis doc
`session_4_beta_preflight_findings.md`.
**Status:** COMPLETE.

## §1 Engine state audit (Category 1)

**Engine module located:** `engine/techniques/transformer_forecast.py`
(harness wrapper imports `_patch_sa_blocks_for_capture` +
`_restore_sa_blocks` for attention capture mechanism).

**Engine-side state audit:** Engine wrapper provides attention
capture infrastructure via `_sa_block` patch mechanism (Phase 4
codification). Captured attention weights surface to harness
via `captured` list mutation. No engine-side audit_fields
elevation analog needed (attention is captured directly during
forward pass, not via post-hoc audit_fields path per BYF
Decision 12 pattern).

**Harness wrapper engine-call pattern:** Harness wrapper at
`tools/reference_parity/harness/checks/transformer_attention.py`
imports engine's capture utilities + clones model with same
weights via `_clone_model_with_same_weights` helper. Calls
forward pass under `torch.no_grad()` + `model.eval()`. Engine
infrastructure complete; harness uses it directly.

**Engine work scope for S4-β: ~0 LOC.** No engine modifications
required. S4-β scope reduces to harness wrapper expansion +
allowlist addition + per-wrapper smoke test.

**No blocking issues** identified. Engine implementation
production-ready; PyTorch dependency already present per
parity-fast.yml install matrix; `.pt` fixture (`3f_transformer_attention`)
extant per Phase 1 codification.

## §2 Harness wrapper field-availability investigation (Category 2)

**Harness wrapper located:** `tools/reference_parity/harness/checks/transformer_attention.py`
(`TransformerAttentionParity` class at line 98; `technique_id = "3f_transformer_attention"`;
`fixture_id = "3f_transformer_attention"`; `tier = "fast"`).

**`structural_invariants` declaration** (Phase 4 S9 dormant
declaration extant per P4-1.3 codification at lines 125-132):
- `attention_normalization` invariant; `tolerance=1e-6`;
  `tolerance_type="absolute"`

**`_check_attention_normalization` checker (single-side per
`structural_invariants.py` line 973):** Consumes
`tsl["attention_matrix"]` (np.ndarray of shape `(n_heads, T_query, T_key)`
or `(T_query, T_key)`; required; BLOCK if missing). PASS if
`max_row_sum_deviation <= 1e-6` AND value range within
`[-10*tol, 1+10*tol]`; CAVEAT at 10× threshold; BLOCK otherwise.

**Field-availability investigation per S2-redux + S4-α protocol:**

`run_tsl()` (lines 182-185) currently returns
`{"attention_per_layer": list, "n_layers": int}`. **Required
field `attention_matrix` NOT exposed at top level.** `attention_per_layer`
is a list of per-layer arrays (analog to mint_family
`per_method` dict pre-S4-α expansion).

**Empirical investigation on real fixture (read-only execution):**
Computed row-sum deviations + value ranges per layer:

| Layer | Shape | max_row_sum_deviation | min_val | max_val | Disposition |
|---|---|---|---|---|---|
| 0 | (1, 16, 16) | 3.654e-08 | 1.371e-06 | 4.924e-01 | PASS @ 1e-6 |
| 1 | (1, 16, 16) | 4.843e-08 | 5.958e-02 | 8.683e-02 | PASS @ 1e-6 |

**Case determination:** Case (i) — required field NOT exposed at
top level; harness wrapper expansion required (~5-15 LOC; expose
representative layer's attention matrix at run_tsl top level).
**Second Case (i) observation in Phase 5 sequence** (first at
S4-α mint_family per B-Phase5-S4-α-CASE-i-FIRST-EMPIRICAL-OBSERVATION).

**Architectural decision (deferred to S4-β execution-time
authoring):** which layer's `attention_matrix` to expose at top
level. Three options analogous to S4-α mint_shrinkage
representative method choice:
- Option A: Layer 0 (first encoder layer; simplest convention;
  representative)
- Option B: Last layer (model output-side attention; common
  Transformer interpretability convention)
- Option C: Worst-case across layers (max row-sum deviation;
  defensive)

Empirical evidence shows both layers PASS deterministically
(~3-5e-08 row dev; well below 1e-6 threshold). Any choice
produces PASS. Code's recommendation: **Option A (layer 0)** —
simplest convention; mirrors S4-α representative-method
single-element pattern. Pre-flight finding: field VALUE
satisfies invariant tolerance trivially (deterministic
softmax math; well below 1e-6 on float32 attention).

## §3 Tier classification + parity-slow latent risk (Category 3)

**Tier classification:** `tier = "fast"` (line 107). Direct CI
parity-fast impact upon allowlist addition (mirrors S4-α
mint_family scenario; distinct from S3 MCMC SV slow-tier).

**Parity-slow latent risk per B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK:**
N/A for fast-tier wrapper. Field VALUE satisfaction MUST be
verified pre-allowlist-add — verified per §2 (both layers PASS
deterministically; closed-form softmax math; well below 1e-6).

**No latent CI risk identified.** Fast-tier allowlist addition
safe given empirical field VALUE satisfaction.

## §4 INVERTED tolerance verification (Category 4)

Per B-Phase4-S9-3 codification: INVERTED tolerance applies ONLY
to caviar_sav (S4-γ scope). transformer_attention
`_check_attention_normalization` at `structural_invariants.py`
lines 1020-1029: `status = "PASS" if max_row_dev <= threshold` —
STANDARD tolerance semantic (smaller deviation is better).

**transformer_attention confirmed STANDARD (not INVERTED).** No
B-Phase4-S9-3 codification revisit required.

**§13.4 compliance:** Investigation commit delta verified at
staging time per Code's chunking judgment (3-commit cascading
split per Q-S4-β-preflight-overshoot=(γ) disposition).
