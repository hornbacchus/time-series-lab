"""
InterpretationSpec for nbeats_forecast (neural decomposition cohort).

N-BEATS uses architectural basis expansion via stacked residual blocks
for direct multi-horizon forecasting. D20: Tier 3 fires when stack
configuration is ['generic'] — the decomposition-interpretable variants
require `stack_types=['trend', 'seasonality']`.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.primitives import format_scale_aware
from interpretation.specs._neural_decomposition_common import (
    render_decomposition_tier1,
)
from interpretation.specs._neural_sequence_common import (
    trigger_insufficient_neural_training,
    trigger_neural_convergence_not_reached,
    trigger_backend_fallback_neural,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    stack_types = results.get("stack_types") or []
    n_blocks = int(results.get("n_blocks", 0) or 0)
    hidden = int(results.get("hidden_size", 0) or 0)
    stacks_str = ", ".join(str(s) for s in stack_types) if stack_types else "unavailable"
    arch_desc = (
        f"Stack types: [{stacks_str}], {n_blocks} blocks per stack, "
        f"hidden size {hidden}"
    )
    return render_decomposition_tier1("N-BEATS", results, arch_desc)


def _tier2(results: dict) -> str:
    backend = str(results.get("backend") or "")
    stack_types = results.get("stack_types") or []
    final_loss = results.get("final_loss")
    final_str = format_scale_aware(float(final_loss)) if final_loss is not None else "n/a"
    generic_note = ""
    if list(stack_types) == ["generic"]:
        generic_note = (
            " Stack configuration is ['generic'] — architecturally-"
            "enforced decomposition into trend / seasonality / residual "
            "is NOT active. For interpretable decomposition, use the "
            "Thorough preset with stack_types=['trend', 'seasonality']."
        )
    fallback_note = ""
    if backend and backend != "pytorch":
        fallback_note = (
            f" **Backend fallback:** {backend} used (PyTorch not "
            f"available). The ensemble fallback approximates N-BEATS "
            f"via Ridge + GBR + MLP on flat features; the architectural "
            f"residual-stacking structure is NOT emulated. For exact "
            f"N-BEATS semantics, install `pytorch`."
        )
    return (
        f"N-BEATS (Neural Basis Expansion Analysis for Time Series). "
        f"Direct multi-horizon training: the wrapper trains on multi-"
        f"step sequences (input → h-step output in one pass), avoiding "
        f"recursive error accumulation but requiring more data. Stack "
        f"types [{', '.join(str(s) for s in stack_types) if stack_types else 'unavailable'}] "
        f"determine the functional basis per stack; generic basis is "
        f"non-interpretable, trend/seasonality bases carry semantic "
        f"meaning. Final training loss {final_str}. Per-stack variance "
        f"contribution not exposed by the wrapper — dominant stack "
        f"cannot be identified from available output.{generic_note}"
        f"{fallback_note}"
    )


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


def _trigger_generic_stack(results: dict) -> Optional[str]:
    """D20 — fires when stack configuration is ['generic']."""
    stacks = results.get("stack_types") or []
    if list(stacks) != ["generic"]:
        return None
    return (
        "Stack configuration is ['generic'] — architecturally-enforced "
        "decomposition into trend / seasonality / residual is NOT "
        "active. The generic basis is non-interpretable. For "
        "interpretable decomposition, switch to stack_types=['trend', "
        "'seasonality'] (Thorough preset)."
    )


SPEC = InterpretationSpec(
    technique_id="nbeats_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        _trigger_generic_stack,
        trigger_insufficient_neural_training,
        trigger_neural_convergence_not_reached,
    ),
    mode_aware=False,
)

register(SPEC)
