"""3f Transformer attention capture parity check.

Validates TSL's `_patch_sa_blocks_for_capture` + no-op
forward-hook mechanism against PyTorch native
`nn.MultiheadAttention(need_weights=True,
average_attn_weights=True)`. The two implementations should
produce **bitwise-identical** attention matrices given:

- Identical model weights
- Identical input tensor
- Identical encoder layer architecture
- model.eval() (no dropout, no training-mode effects)

Architectural decisions (locked in Session 3b design):

- **Q1.** Two separate model instances with cloned weights.
  Cleaner state management; failure modes don't depend on TSL's
  `_restore_sa_blocks` working correctly. Helper function
  ``_clone_model_with_same_weights`` constructs a fresh model
  from the fixture config + state_dict.
- **Q2.** **FAILURE = TSL BUG, NOT TOLERANCE QUESTION.** If
  this check BLOCKs, TSL's `_sa_block` patch is producing
  different attention weights than native MHA. Investigate
  before relaxing. The 1e-12 floor is principled (FP precision
  over a chain of identical torch ops); anything larger is
  evidence of a real divergence.
- **Q3.** Per-layer comparison granularity. Loop over
  encoder_layers; compare each layer's attention matrix
  separately; report which layer fails if any. Bug-localization
  > simplicity.
- **Q4.** Custom .pt fixture (PyTorch model state_dict + input
  tensor). Phase 3.3 generalized FixtureLoader to dispatch by
  file extension (.npz, .pt) — this check now uses the standard
  ``fixture_id`` pattern; the runner auto-loads the .pt fixture
  with the harness's standard SHA verification, removing the
  prior bespoke loader.

**Phase 1 audit 3f baseline:** max abs diff 0.000e+00 (bitwise)
on layers 0 and 1 of a small Transformer (d_model=32, n_heads=4,
n_encoder_layers=2). The harness asserts at 1e-12; reproduces
the bitwise baseline with eight orders of magnitude of headroom
for FP-precision drift.
"""

from __future__ import annotations

import pathlib
import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.structural_invariants import StructuralInvariant
from reference_parity.harness.tolerances import get_ladder


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import
    `_build_transformer_model` and the patch helpers."""
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


def _clone_model_with_same_weights(config: dict[str, Any], state_dict):
    """Construct a fresh TimeSeriesTransformer from fixture
    config and load the saved state_dict. The two-instance
    pattern (Q1) keeps TSL and reference paths fully isolated —
    no shared mutable state, no patch-teardown dependencies."""
    _ensure_engine_on_path()
    from techniques.transformer_forecast import _build_transformer_model

    model = _build_transformer_model(
        d_model=config["d_model"],
        n_heads=config["n_heads"],
        n_encoder_layers=config["n_encoder_layers"],
        dim_feedforward=config["dim_feedforward"],
        seq_len=config["seq_len"],
        dropout=config["dropout"],
    )
    model.load_state_dict(state_dict)
    model.eval()
    return model


class TransformerAttentionParity(P3ParityCheck):
    """Transformer attention capture parity vs native MHA.

    See module docstring for the full failure-mode contract:
    a BLOCK from this check is a TSL production bug in the
    `_sa_block` patch mechanism, NOT a parity tolerance issue.
    """

    technique_id = "3f_transformer_attention"
    tier = "fast"

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "PyTorch nn.MultiheadAttention attention-capture vs "
        "native MHA forward-pass with cloned weights and frozen "
        "model.eval(). Both paths invoke the same forward; "
        "bit-exact attention matrices expected. Failure indicates "
        "TSL's _sa_block patch mechanism bug — strict bit-exact "
        "BLOCK-class assertion (not tolerance question)."
    )

    # Phase 4 Session 9 (P4-1.3, 2026-05-02) — declare the
    # attention_normalization structural invariant. The TSL audit
    # surfaces ``attention_matrix`` (n_heads, T, T) per layer; the
    # invariant verifies row-stochasticity + value range [0, 1].
    # tolerance=1e-6 = float32 row-sum-deviation noise floor.
    structural_invariants = (
        StructuralInvariant(
            name="attention_normalization",
            invariant_type="attention_normalization",
            tolerance=1e-6,
            tolerance_type="absolute",
        ),
    )
    # Phase 3.3: standard fixture_id; runner auto-loads the .pt
    # fixture via FixtureLoader's format dispatch. Replaced the
    # prior fixture_id="" + bespoke _load_pt_fixture_with_sha
    # pattern from Session 3b.
    fixture_id = "3f_transformer_attention"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # No supplementary state needed; runner already loaded
        # the .pt fixture (model_state_dict, model_config,
        # input) and merges it into the fixture dict before
        # passing to run_tsl / run_reference.
        return {}

    # -----------------------------------------------------------------
    # TSL side — apply _patch_sa_blocks_for_capture, run forward,
    # collect captured attention weights, restore.
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.transformer_forecast import (
            _patch_sa_blocks_for_capture,
            _restore_sa_blocks,
        )

        model = _clone_model_with_same_weights(
            fixture["model_config"], fixture["model_state_dict"],
        )
        x = fixture["input"]

        captured: list[tuple[int, Any]] = []
        originals = _patch_sa_blocks_for_capture(
            model.encoder, captured,
        )
        try:
            import torch
            with torch.no_grad():
                _ = model(x)
        finally:
            _restore_sa_blocks(originals)

        # captured is a list of (layer_idx, weights_tensor). Sort
        # by layer_idx and convert to numpy for the comparison.
        n_layers = int(fixture["model_config"]["n_encoder_layers"])
        per_layer: list[np.ndarray | None] = [None] * n_layers
        for layer_idx, weights in captured:
            per_layer[layer_idx] = (
                weights.detach().cpu().numpy().astype(np.float64)
            )
        # Phase 5 S4-β — Case (i) handling per Q-S4-β-rep-layer=
        # (layer-α) Layer 0 representative layer choice. Expose
        # `attention_matrix` field at run_tsl top level for
        # `_check_attention_normalization` invariant consumption.
        # Per pre-flight empirical investigation (commits
        # `e3b55c0` + `ee6c973`), Layer 0 produces row-sum
        # deviation ~3-5e-08 on real fixture (well within
        # tolerance=1e-6). Closed-form deterministic per softmax
        # math + frozen weights + model.eval(). Per
        # Q-Field-α-2=(b) per-session scope: ONLY Layer 0
        # exposed; aggregation logic across layers anticipatory-
        # rejected.
        attention_matrix = (
            per_layer[0] if (
                len(per_layer) > 0 and per_layer[0] is not None
            ) else None
        )
        return {
            "attention_per_layer": per_layer,
            "n_layers": n_layers,
            "attention_matrix": attention_matrix,
        }

    # -----------------------------------------------------------------
    # Reference side — clone model with same weights, manually call
    # each layer's self_attn directly with need_weights=True.
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch

        # Two-instance pattern: fresh model, separate state from
        # TSL run. Reproduces Phase 1 audit 3f's reference path.
        model = _clone_model_with_same_weights(
            fixture["model_config"], fixture["model_state_dict"],
        )
        x = fixture["input"]
        n_layers = int(fixture["model_config"]["n_encoder_layers"])

        # The reference path: replicate exactly what TSL's
        # patched _sa_block does, but driven from the harness
        # (no patch + no hook). We need each layer's input as it
        # would be at runtime. Easiest: run the encoder normally
        # while capturing the input to each layer's _sa_block via
        # a forward_pre_hook on each layer; then call self_attn
        # on the captured inputs.
        #
        # Simpler: register pre-hooks on each TransformerEncoderLayer
        # to capture the layer's input tensor, then after a regular
        # forward, call layer.self_attn directly on each captured
        # input. The self_attn invocation matches what TSL's
        # patched _sa_block calls.
        layer_inputs: list[torch.Tensor | None] = [None] * n_layers

        def _make_capture_hook(idx):
            def _hook(_module, inputs):
                # inputs is a tuple; first element is the layer's
                # input tensor.
                if isinstance(inputs, tuple) and len(inputs) > 0:
                    layer_inputs[idx] = inputs[0].detach().clone()
            return _hook

        handles = []
        for i, layer in enumerate(model.encoder.layers):
            handles.append(
                layer.register_forward_pre_hook(_make_capture_hook(i))
            )

        try:
            with torch.no_grad():
                _ = model(x)
        finally:
            for h in handles:
                try:
                    h.remove()
                except Exception:
                    pass

        # Now call each layer's self_attn directly on the captured
        # input. Note: TransformerEncoderLayer's pre-LN convention
        # may apply norm before self_attn (norm_first=True) or
        # after (norm_first=False). Our model uses the default
        # norm_first=False, so layer input is the value passed
        # straight into _sa_block (no pre-norm).
        per_layer: list[np.ndarray | None] = [None] * n_layers
        with torch.no_grad():
            for i, layer in enumerate(model.encoder.layers):
                inp = layer_inputs[i]
                if inp is None:
                    continue
                # In the default norm_first=False configuration of
                # nn.TransformerEncoderLayer, _sa_block receives the
                # layer's raw input (no pre-norm). The patched TSL
                # path calls self_attn(x, x, x, ...). Reproduce
                # that exactly here.
                _, weights = layer.self_attn(
                    inp, inp, inp,
                    need_weights=True,
                    average_attn_weights=True,
                )
                per_layer[i] = (
                    weights.detach().cpu().numpy().astype(np.float64)
                )

        return {
            "attention_per_layer": per_layer,
            "n_layers": n_layers,
            "torch_version": torch.__version__,
        }

    # -----------------------------------------------------------------
    # Compare — per-layer max abs diff at 1e-12 tolerance.
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        per_layer_tol = float(
            ladder["per_layer_attention_consistency"]["abs_tol"]
        )
        agg_tol = float(
            ladder["attention_weights_per_layer_vs_native_mha"]["abs_tol"]
        )

        metrics: dict[str, Any] = {}
        any_block = False

        # Layer count consistency
        n_tsl = int(tsl.get("n_layers", -1))
        n_ref = int(ref.get("n_layers", -1))
        if n_tsl != n_ref:
            metrics["n_layers_mismatch"] = {
                "status": "BLOCK",
                "tsl_n_layers": n_tsl,
                "ref_n_layers": n_ref,
                "note": (
                    "TSL bug: layer count differs between TSL "
                    "and native paths"
                ),
            }
            any_block = True

        layer_diffs: list[float] = []
        for i in range(min(n_tsl, n_ref)):
            tsl_attn = tsl["attention_per_layer"][i]
            ref_attn = ref["attention_per_layer"][i]
            if tsl_attn is None or ref_attn is None:
                metrics[f"layer_{i}_max_abs_diff"] = {
                    "status": "BLOCK",
                    "note": (
                        f"TSL bug: layer {i} attention not "
                        f"captured (tsl={tsl_attn is not None}, "
                        f"ref={ref_attn is not None})"
                    ),
                }
                any_block = True
                continue
            tsl_arr = np.asarray(tsl_attn, dtype=np.float64)
            ref_arr = np.asarray(ref_attn, dtype=np.float64)
            if tsl_arr.shape != ref_arr.shape:
                metrics[f"layer_{i}_max_abs_diff"] = {
                    "status": "BLOCK",
                    "tsl_shape": list(tsl_arr.shape),
                    "ref_shape": list(ref_arr.shape),
                    "note": (
                        f"TSL bug: layer {i} attention shape "
                        f"differs between paths"
                    ),
                }
                any_block = True
                continue
            diff = float(np.max(np.abs(tsl_arr - ref_arr)))
            layer_diffs.append(diff)
            ok = diff <= per_layer_tol
            metric_entry = {
                "status": "PASS" if ok else "BLOCK",
                "max_abs_diff": diff,
                "shape": list(tsl_arr.shape),
            }
            if not ok:
                metric_entry["note"] = (
                    f"TSL _sa_block patch produces different "
                    f"output than native MHA at layer {i}. "
                    f"THIS IS A TSL BUG, not a tolerance "
                    f"question. Do not relax."
                )
                any_block = True
            metrics[f"layer_{i}_max_abs_diff"] = metric_entry

        # Aggregate across layers
        if layer_diffs:
            agg_max = max(layer_diffs)
            agg_ok = agg_max <= agg_tol
            metrics["max_abs_diff_all_layers"] = {
                "status": "PASS" if agg_ok else "BLOCK",
                "max_abs_diff": agg_max,
                "tolerance": agg_tol,
            }
            if not agg_ok:
                any_block = True

        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics={
                "torch_version": ref.get("torch_version", "unknown"),
                "n_layers": min(n_tsl, n_ref),
            },
        )
