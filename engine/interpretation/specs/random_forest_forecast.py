"""
InterpretationSpec for random_forest_forecast (tree cohort).

Inherits the shared `_tree_common` helpers for Tier 1 rendering,
Tier 2 opener, and Tier 3 triggers (overfitting, insufficient data,
tree extrapolation, time-index dominance). RF is algorithmically
orthogonal to boosting methods — this spec emphasizes the bagging
structure in Tier 2.
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
        technique_label="Random forest",
        technique_id="random_forest_forecast",
        results=results,
    )


def _tier2(results: dict) -> str:
    body = render_tree_tier2_common(results, "Random Forest (scikit-learn)")
    # RF-specific: bagging, no learning rate, parallel ensemble.
    return (
        body
        + " Random Forest is a **bagging ensemble** — each tree is "
        "trained on a bootstrap sample of the training set with a "
        "random subset of features at each split. Predictions are "
        "averaged across trees. This structure is algorithmically "
        "orthogonal to boosting (XGBoost / LightGBM / gradient "
        "boosting) and tends to underfit rather than overfit with "
        "sufficient trees."
    )


SPEC = InterpretationSpec(
    technique_id="random_forest_forecast",
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
