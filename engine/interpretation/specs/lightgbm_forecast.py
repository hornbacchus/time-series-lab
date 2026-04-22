"""
InterpretationSpec for lightgbm_forecast (tree cohort).

Inherits the shared `_tree_common` helpers. LightGBM-specific: leaf-
wise growth via num_leaves (distinct from depth-wise convention); falls
back to sklearn.GradientBoostingRegressor when the lightgbm library
is not installed.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.specs._tree_common import (
    render_tree_tier1,
    render_tree_tier2_common,
    trigger_overfitting_short_series,
    trigger_insufficient_training_data,
    trigger_tree_extrapolation_warning,
    trigger_time_index_dominance,
    trigger_backend_fallback,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    return render_tree_tier1(
        technique_label="LightGBM",
        technique_id="lightgbm_forecast",
        results=results,
        preferred_backend="lightgbm",
    )


def _tier2(results: dict) -> str:
    body = render_tree_tier2_common(results, "LightGBM gradient-boosted ensemble")
    num_leaves = results.get("num_leaves")
    leaf_wise_note = ""
    if num_leaves is not None:
        leaf_wise_note = (
            f" Leaf-wise growth (num_leaves={num_leaves}) is more "
            "aggressive than depth-wise and typically overfits faster "
            "on short series."
        )
    backend = str(results.get("backend") or "")
    fallback_note = ""
    if backend and backend != "lightgbm":
        fallback_note = (
            " **Backend fallback:** lightgbm not available; "
            "sklearn.GradientBoostingRegressor used instead — this is "
            "depth-wise (num_leaves inactive), uses different loss / "
            "regularizer defaults, and reports feature importances in "
            "sklearn's gain convention (not LightGBM's renormalized "
            "convention). For exact LightGBM semantics, install "
            "`lightgbm`."
        )
    return body + leaf_wise_note + fallback_note


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback(results, "lightgbm")


def _trigger_leaf_wise_on_short_series(results: dict) -> Optional[str]:
    num_leaves = results.get("num_leaves")
    n_train = results.get("n_train")
    if num_leaves is None or n_train is None:
        return None
    try:
        nl = int(num_leaves)
        nt = int(n_train)
        if nl * 10 < nt:
            return None
    except Exception:
        return None
    return (
        f"num_leaves={num_leaves} on {n_train} training samples — "
        f"leaf-wise growth can overfit faster than depth-wise on short "
        f"series. Consider reducing num_leaves or increasing "
        f"min_child_samples."
    )


SPEC = InterpretationSpec(
    technique_id="lightgbm_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        trigger_overfitting_short_series,
        trigger_insufficient_training_data,
        trigger_tree_extrapolation_warning,
        trigger_time_index_dominance,
        _trigger_leaf_wise_on_short_series,
    ),
    mode_aware=False,
)

register(SPEC)
