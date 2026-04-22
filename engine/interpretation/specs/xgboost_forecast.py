"""
InterpretationSpec for xgboost_forecast (tree cohort).

Inherits the shared `_tree_common` helpers. XGBoost-specific: gradient
boosting with subsample / colsample hyperparameters; falls back to
sklearn.GradientBoostingRegressor when the xgboost library is not
installed.
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
        technique_label="XGBoost",
        technique_id="xgboost_forecast",
        results=results,
        preferred_backend="xgboost",
    )


def _tier2(results: dict) -> str:
    body = render_tree_tier2_common(results, "XGBoost gradient-boosted ensemble")
    backend = str(results.get("backend") or "")
    fallback_note = ""
    if backend and backend != "xgboost":
        fallback_note = (
            " **Backend fallback:** xgboost library not available; "
            "sklearn.GradientBoostingRegressor used instead. The two "
            "are not equivalent — sklearn's loss, regularization "
            "defaults, and tree-construction algorithm differ from "
            "XGBoost's. For exact XGBoost semantics, install `xgboost`."
        )
    return body + fallback_note


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback(results, "xgboost")


SPEC = InterpretationSpec(
    technique_id="xgboost_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        trigger_overfitting_short_series,
        trigger_insufficient_training_data,
        trigger_tree_extrapolation_warning,
        trigger_time_index_dominance,
    ),
    mode_aware=False,
)

register(SPEC)
