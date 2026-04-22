"""
InterpretationSpec for transformer_forecast (neural sequence cohort).

Transformer encoder applied to a lag window. Tier 2 discloses the
attention-weights backlog item — with PyTorch available, the attention
structure could be extracted but is not currently implemented.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.specs._neural_sequence_common import (
    render_neural_tier1,
    render_neural_tier2_common,
    trigger_insufficient_neural_training,
    trigger_neural_convergence_not_reached,
    trigger_params_exceed_training_samples,
    trigger_backend_fallback_neural,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    d_model = int(results.get("d_model", 0) or 0)
    heads = int(results.get("n_heads", 0) or 0)
    enc_layers = int(results.get("n_encoder_layers", 0) or 0)
    dim_ff = int(results.get("dim_feedforward", 0) or 0)
    n_params = results.get("n_params")
    params_note = f", {int(n_params)} total parameters" if n_params else ""
    arch_desc = (
        f"Architecture: d_model={d_model}, {heads} attention head(s), "
        f"{enc_layers} encoder layer(s), feed-forward dim={dim_ff}"
        f"{params_note}"
    )
    return render_neural_tier1("Transformer", results, arch_desc)


def _tier2(results: dict) -> str:
    arch_note = (
        "Transformer encoder applied to a lag window. Self-attention "
        "computes weighted averages of past timesteps via learned "
        "query / key / value projections. Attention weights could be "
        "extracted as an interpretability axis (which past timesteps "
        "drive each forecast) but are not currently exposed at the "
        "wrapper level — backlog for future enhancement."
    )
    return render_neural_tier2_common(results, "Transformer sequence forecaster", arch_note)


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


SPEC = InterpretationSpec(
    technique_id="transformer_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        trigger_insufficient_neural_training,
        trigger_neural_convergence_not_reached,
        trigger_params_exceed_training_samples,
    ),
    mode_aware=False,
)

register(SPEC)
