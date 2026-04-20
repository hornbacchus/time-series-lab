"""
InterpretationSpec for forecast_combination.

Per Decision A: Tier 1 option (b) implemented — ensemble-vs-best
constituent with delta percentage. Per S3: Tier 2 weights sentence
restructured to avoid "0.72 × MSE 168" rendering.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    FMT_PROBABILITY,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


# In-spec weight-dominance bands (per Decision 4).
# TODO: promote to a C.7 primitive if a second spec in C2-C7 needs
# the same banding logic.
def _weight_dominance_band(weight: float, k: int) -> str:
    w = float(weight)
    equal_weight = 1.0 / max(k, 1)
    if w < equal_weight:
        return "dominated"
    if w < 0.5:
        return "balanced"
    if w < 0.9:
        return "dominant"
    return "near-single"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    horizon = int(results.get("horizon", 0))
    n_models = int(results.get("n_models", 0))
    model_names = list(results.get("model_names") or [])
    weights = list(results.get("weights") or [])
    ensemble_mse = results.get("ensemble_holdout_mse")
    dominant_name = results.get("dominant_model_name")
    dominant_weight = results.get("dominant_model_weight")
    dominant_mse = results.get("dominant_model_mse")
    method_name = str(results.get("combination_method", "inverse-MSE"))
    models_clause = (
        ", ".join(model_names) if model_names else f"{n_models} constituents"
    )
    dominant_clause = ""
    if dominant_name and dominant_weight is not None:
        band = _weight_dominance_band(float(dominant_weight), n_models)
        dominant_clause = (
            f" {method_name} weights: {dominant_name} receives "
            f"{FMT_PROBABILITY.format(float(dominant_weight))} ({band})"
        )
        # Append the other weights inline
        if weights and model_names and len(weights) == len(model_names):
            pairs = sorted(zip(model_names, weights), key=lambda p: -float(p[1]))
            others = [
                f"{m} {FMT_PROBABILITY.format(float(w))}"
                for m, w in pairs if m != dominant_name
            ]
            if others:
                dominant_clause += ", " + ", ".join(others)
        dominant_clause += "."
    comparison_clause = ""
    if (
        ensemble_mse is not None and dominant_mse is not None
        and float(dominant_mse) > 0
    ):
        delta_pct = 100.0 * (float(dominant_mse) - float(ensemble_mse)) / float(dominant_mse)
        if delta_pct > 0:
            comparison_clause = (
                f" Ensemble holdout MSE "
                f"{FMT_COEF_UNSIGNED.format(float(ensemble_mse))} vs "
                f"{dominant_name} alone "
                f"{FMT_COEF_UNSIGNED.format(float(dominant_mse))} — "
                f"ensemble adds {delta_pct:.1f}% MSE reduction over "
                f"the single best constituent, justifying the weighting."
            )
        else:
            comparison_clause = (
                f" Ensemble holdout MSE "
                f"{FMT_COEF_UNSIGNED.format(float(ensemble_mse))} "
                f"exceeds {dominant_name} alone "
                f"{FMT_COEF_UNSIGNED.format(float(dominant_mse))} by "
                f"{abs(delta_pct):.1f}% — ensemble does not improve "
                f"over the best constituent."
            )
    return (
        f"{n_models}-model ensemble ({models_clause}) of "
        f"{format_series_reference(name)} {horizon}-step forecast."
        f"{dominant_clause}{comparison_clause}"
    )


def _tier2(results: dict) -> str:
    method_name = str(results.get("combination_method", "inverse-MSE"))
    holdout_length = results.get("holdout_length")
    equal_weight_mse = results.get("equal_weight_holdout_mse")
    ensemble_mse = results.get("ensemble_holdout_mse")
    weights = list(results.get("weights") or [])
    model_names = list(results.get("model_names") or [])
    per_model_mse = list(results.get("per_model_holdout_mse") or [])
    holdout_clause = (
        f"on a {int(holdout_length)}-period holdout set"
        if holdout_length is not None else "on the configured holdout"
    )
    weights_sentence = ""
    if weights and model_names and per_model_mse and len(weights) == len(model_names) == len(per_model_mse):
        pairs = []
        for m, w, mse in zip(model_names, weights, per_model_mse):
            pairs.append(
                f"{m} receives {FMT_PROBABILITY.format(float(w))} "
                f"(MSE={FMT_COEF_UNSIGNED.format(float(mse))})"
            )
        weights_sentence = (
            f"Weights assigned by {method_name}: " + "; ".join(pairs) + "."
        )
    equal_sentence = ""
    if equal_weight_mse is not None and ensemble_mse is not None:
        equal_sentence = (
            f" Equal-weight baseline MSE "
            f"{FMT_COEF_UNSIGNED.format(float(equal_weight_mse))}."
        )
    return (
        f"Weights determined via {method_name} {holdout_clause}. "
        f"{weights_sentence}{equal_sentence} The ensemble combines "
        f"per-model forecasts into a weighted consensus; the dominant "
        f"weight signals high confidence in one constituent while "
        f"non-zero weights on the others add diversification value "
        f"when their errors are imperfectly correlated."
    )


def _trigger_near_single(results: dict) -> Optional[str]:
    dominant_weight = results.get("dominant_model_weight")
    dominant_name = results.get("dominant_model_name")
    if dominant_weight is None or dominant_name is None:
        return None
    if float(dominant_weight) <= 0.9:
        return None
    return (
        f"Dominant weight {FMT_PROBABILITY.format(float(dominant_weight))} "
        f"on {dominant_name} exceeds 0.9 — this is a near-single-model "
        f"ensemble. Using {dominant_name} alone would give nearly the "
        f"same forecast at lower operational complexity."
    )


def _trigger_ensemble_hurts(results: dict) -> Optional[str]:
    ensemble_mse = results.get("ensemble_holdout_mse")
    dominant_mse = results.get("dominant_model_mse")
    if ensemble_mse is None or dominant_mse is None:
        return None
    if float(ensemble_mse) <= float(dominant_mse):
        return None
    return (
        f"Ensemble holdout MSE "
        f"{FMT_COEF_UNSIGNED.format(float(ensemble_mse))} exceeds the "
        f"best single constituent's "
        f"{FMT_COEF_UNSIGNED.format(float(dominant_mse))}. Ensemble "
        f"hurts; use the best constituent alone."
    )


def _trigger_equal_weights(results: dict) -> Optional[str]:
    weights = list(results.get("weights") or [])
    if not weights:
        return None
    k = len(weights)
    equal_weight = 1.0 / k
    if all(abs(float(w) - equal_weight) < 0.1 * equal_weight for w in weights):
        return (
            "All weights are within 10% of 1/k — the "
            f"{str(results.get('combination_method', ''))} method-"
            f"dependent preference is weak. Simple averaging would "
            f"give essentially the same ensemble; prefer simple "
            f"averaging for transparency."
        )
    return None


SPEC = InterpretationSpec(
    technique_id="forecast_combination",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_near_single,
        _trigger_ensemble_hurts,
        _trigger_equal_weights,
    ),
    mode_aware=False,
)

register(SPEC)
