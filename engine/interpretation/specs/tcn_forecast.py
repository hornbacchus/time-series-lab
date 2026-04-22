"""
InterpretationSpec for tcn_forecast (neural sequence cohort).

Temporal Convolutional Network — dilated 1D convolutions with a fixed
receptive field. Tier 2 emphasizes the receptive-field interpretability
axis (the TCN's "memory span" is given by receptive_field).
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
    n_channels = results.get("n_channels") or []
    kernel = int(results.get("kernel_size", 0) or 0)
    rf = int(results.get("receptive_field", 0) or 0)
    epochs = int(results.get("epochs", 0) or 0)
    arch_desc = (
        f"Temporal Convolutional Network with dilated channels "
        f"{list(n_channels)}, kernel size {kernel}, receptive field "
        f"{rf} timesteps, {epochs} training epochs"
    )
    return render_neural_tier1("TCN", results, arch_desc)


def _tier2(results: dict) -> str:
    rf = results.get("receptive_field")
    arch_note = (
        f"TCN uses dilated 1D convolutions to cover a receptive field "
        f"of {rf} timesteps — the model's memory span. Dilation "
        f"geometrically expands receptive field with depth, making "
        f"TCN efficient for long-range dependencies at shallow depths."
    )
    return render_neural_tier2_common(results, "Temporal Convolutional Network", arch_note)


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


SPEC = InterpretationSpec(
    technique_id="tcn_forecast",
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
