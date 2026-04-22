"""
InterpretationSpec for nhits_forecast (neural decomposition cohort).

N-HiTS extends N-BEATS with hierarchical interpolation via multi-rate
pooling. D19: when running on the sklearn ensemble fallback, NHITS
collapses to NBEATS (identical output) because the multi-rate pooling
that distinguishes NHITS requires PyTorch.
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
    n_stacks = int(results.get("n_stacks", 0) or 0)
    n_blocks = int(results.get("n_blocks", 0) or 0)
    hidden = int(results.get("hidden_size", 0) or 0)
    pooling = results.get("pooling_sizes") or []
    arch_desc = (
        f"{n_stacks} stacks × {n_blocks} blocks, hidden size {hidden}, "
        f"multi-rate pooling {list(pooling)} (finer resolution at later "
        f"stacks)"
    )
    return render_decomposition_tier1("N-HiTS", results, arch_desc)


def _tier2(results: dict) -> str:
    backend = str(results.get("backend") or "")
    pooling = results.get("pooling_sizes") or []
    final_loss = results.get("final_loss")
    final_str = format_scale_aware(float(final_loss)) if final_loss is not None else "n/a"
    collapse_note = ""
    if backend == "sklearn_ensemble":
        collapse_note = (
            " **NHITS collapses to NBEATS under fallback:** the "
            "multi-rate pooling that distinguishes N-HiTS from N-BEATS "
            "requires PyTorch. Under sklearn_ensemble fallback, the "
            "two wrappers produce identical output — both map to the "
            "same Ridge + GBR + MLP ensemble on flat features."
        )
    return (
        f"N-HiTS (Neural Hierarchical Interpolation for Time Series). "
        f"Extends N-BEATS with hierarchical-interpolation pooling for "
        f"multi-rate decomposition — each stack operates at a "
        f"different temporal resolution (pooling sizes {list(pooling)}). "
        f"With PyTorch available, this means the first stack captures "
        f"low-frequency structure (coarser resolution) and later "
        f"stacks add higher-frequency detail. Direct multi-horizon "
        f"training like N-BEATS. Final training loss {final_str}."
        f"{collapse_note}"
    )


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


def _trigger_fallback_collapse(results: dict) -> Optional[str]:
    """D19 — always-fires when NHITS runs on sklearn_ensemble fallback."""
    if str(results.get("backend") or "") != "sklearn_ensemble":
        return None
    return (
        "Under sklearn_ensemble fallback, N-HiTS and N-BEATS produce "
        "identical output — the multi-rate pooling that distinguishes "
        "NHITS requires PyTorch. Install `pytorch` to access NHITS-"
        "specific hierarchical-interpolation dynamics."
    )


SPEC = InterpretationSpec(
    technique_id="nhits_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        _trigger_fallback_collapse,
        trigger_insufficient_neural_training,
        trigger_neural_convergence_not_reached,
    ),
    mode_aware=False,
)

register(SPEC)
