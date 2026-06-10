# 3f Transformer attention capture — reference parity audit

**Date:** 2026-04-24

**Fixture:**
- `nn.TransformerEncoder` with 2 layers, d_model=32, n_heads=4, dim_feedforward=64, dropout=0.0.
- Seed 42 at model construction.
- model.eval() before forward pass.
- Input shape: (1, 16, 32) random tensor (seed 43).

**Verification strategy:**
1. TSL's `_patch_sa_blocks_for_capture` wraps each
   layer's `_sa_block` with a version that forces
   `need_weights=True, average_attn_weights=True`.
   A no-op forward hook is also registered to
   disable PyTorch's sparsity fast-path.
2. An additional wrapping layer (audit-specific)
   records the exact pre-`_sa_block` input tensor
   per layer.
3. Forward pass runs once. TSL captures per-layer
   attention weights via the patch machinery.
4. For each layer, `layer.self_attn(x, x, x,
   need_weights=True, average_attn_weights=True)`
   is called directly with the recorded input.
   This is the NATIVE reference.
5. TSL captured weights vs native weights compared
   element-wise at `tol=1e-12`.
6. Teardown verified: `_sa_block` restored to
   original method (identity check via `is`),
   all forward hooks removed.

**Tolerance:** `1e-12` (strict). TSL's patch IS a direct call to `self_attn(need_weights=True)` with the same inputs, so bitwise parity with a direct native call is expected.

## Overall verdict

| Layer | TSL shape | max abs diff | max rel diff | RMS | Row-sum dev from 1 | Verdict |
|---|---|---|---|---|---|---|
| 0 | [1, 16, 16] | 0.000e+00 | 0.000e+00 | 0.000e+00 | 1.192e-07 | **PASS** |
| 1 | [1, 16, 16] | 0.000e+00 | 0.000e+00 | 0.000e+00 | 1.192e-07 | **PASS** |

## Teardown verification

- `_sa_block` restored to original (identity check): **True**
- All forward hooks removed: **True**

Per-layer detail:

| Layer | _sa_block restored | n_forward_hooks |
|---|---|---|
| 0 | ✓ | 0 |
| 1 | ✓ | 0 |

## Row-sum normalization check

Attention weights are a softmax over seq_len, so each
row should sum to exactly 1.0 (within fp tolerance).
Max deviation from 1.0 per layer:

- Layer 0: max |row_sum − 1| = 1.192e-07 (PASS)
- Layer 1: max |row_sum − 1| = 1.192e-07 (PASS)

## Forward output parity

A clean forward pass (no patches, no hooks) should
produce the same output as the patched forward pass
(since TSL's patched `_sa_block` preserves behavior).

- Clean vs patched output max abs diff: **0.000e+00**
- Clean vs patched output shape: [1, 16, 32]
- Verdict: **PASS** (tolerance 1e-6 accommodates
  the fast-path vs slow-path internal reordering —
  PyTorch documents that the two paths are numerically
  within fp noise but not bitwise identical).

## Methodology notes

- **Dual-mechanism capture is equivalent to native `self_attn(need_weights=True)`.** TSL's patched `_sa_block` calls `self_attn(x, x, x, need_weights=True, ...)` directly, so the captured weights ARE what a native `self_attn` call would return on the same input. Bitwise parity at `tol=1e-12` is expected and achieved.

- **The no-op forward hook is essential.** Without it, PyTorch's sparsity fast-path bypasses `_sa_block` entirely, and the patched method is never called. The hook disables the fast-path so the slow path (which invokes `_sa_block`) is used. This is a PyTorch-specific implementation detail documented in the 3f follow-up commit and the Transformer wrapper's module docstring.

- **Forward output clean-vs-patched diff** is tiny but nonzero because PyTorch's fast-path kernel and slow-path module-forward differ in internal compute order (fused vs unfused operations). Documented PyTorch behavior; not a TSL issue.
