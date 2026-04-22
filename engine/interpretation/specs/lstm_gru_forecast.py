"""
InterpretationSpec for lstm_gru_forecast (neural sequence cohort).

Inherits the shared `_neural_sequence_common` helpers. LSTM/GRU
dual-mode: wrapper's `model_type` param selects LSTM vs GRU. Spec
renders the selected variant. PyTorch preferred backend; sklearn MLP
fallback approximates the sequence model via flat-feature regression.
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
    mt = str(results.get("model_type") or "lstm").upper()
    hidden = int(results.get("hidden_size", 0) or 0)
    layers = int(results.get("n_layers", 0) or 0)
    n_lags = int(results.get("n_lags", 0) or 0)
    epochs = int(results.get("epochs", 0) or 0)
    arch_desc = (
        f"Architecture: {layers} layer(s) × {hidden} hidden units, "
        f"sequence length {n_lags}, {epochs} training epochs"
    )
    return render_neural_tier1(mt, results, arch_desc)


def _tier2(results: dict) -> str:
    mt = str(results.get("model_type") or "lstm").upper()
    arch_note = (
        f"{mt} is a recurrent sequence model. With PyTorch available, "
        f"the cell's gate structure (input / forget / output gates for "
        f"LSTM; update / reset gates for GRU) is fit end-to-end via "
        f"backpropagation-through-time."
    )
    return render_neural_tier2_common(results, f"{mt} sequence forecaster", arch_note)


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


SPEC = InterpretationSpec(
    technique_id="lstm_gru_forecast",
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
