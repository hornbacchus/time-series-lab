"""
InterpretationSpec for gradient_boosting_forecast (tree cohort).

Inherits the shared `_tree_common` helpers. Sklearn-native gradient
boosting — no backend fallback (sklearn is always available). Tier 2
notes the shallowest default depth and absence of subsample/colsample
hyperparameters.
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
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    return render_tree_tier1(
        technique_label="Gradient boosting",
        technique_id="gradient_boosting_forecast",
        results=results,
    )


def _tier2(results: dict) -> str:
    body = render_tree_tier2_common(results, "scikit-learn GradientBoostingRegressor")
    return (
        body
        + " Unlike XGBoost / LightGBM, this wrapper has no "
        "`subsample` or `colsample_bytree` hyperparameters exposed; "
        "the sklearn defaults (1.0, i.e. no subsampling) are used. "
        "The shallowest default depth among the tree cohort — "
        "tighter regularization by default. No backend fallback — "
        "sklearn is always available."
    )


SPEC = InterpretationSpec(
    technique_id="gradient_boosting_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        trigger_overfitting_short_series,
        trigger_insufficient_training_data,
        trigger_tree_extrapolation_warning,
        trigger_time_index_dominance,
    ),
    mode_aware=False,
)

register(SPEC)
