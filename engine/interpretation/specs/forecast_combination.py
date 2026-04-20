"""
InterpretationSpec for forecast_combination.

Per Decision A: Tier 1 option (b) implemented — ensemble-vs-best
constituent with delta percentage. Per S3: Tier 2 weights sentence
restructured to avoid "0.72 × MSE 168" rendering.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_PROBABILITY,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register


# Humanized sentence-start rendering of the programmatic method
# name. FIX 6: "inverse-MSE" lowercased at sentence start. Raw
# ``method_name`` is retained for programmatic branching, but
# user-facing prose uses this label when the word leads a sentence.
_METHOD_LABEL_SENTENCE_START = {
    "inverse-MSE": "Inverse-MSE",
    "inverse_mse": "Inverse-MSE",
    "simple-average": "Simple averaging",
    "simple_average": "Simple averaging",
    "equal-weight": "Equal-weight",
    "equal_weight": "Equal-weight",
}


def _method_sentence_start(method_name: str) -> str:
    return _METHOD_LABEL_SENTENCE_START.get(method_name, str(method_name).capitalize())


# Minimum |delta_pct| (ensemble-vs-best-constituent) at which the
# Tier 1 comparison sentence renders the standard "ensemble adds X%"
# / "ensemble is worse by X%" phrasing. Below this threshold, the
# ensemble and best constituent are treated as indistinguishable
# within rounding — the comparison sentence switches to the
# "matches within rounding" phrasing, and the ensemble_hurts Tier 3
# trigger is suppressed (otherwise a -0.004% gap would fire a false
# "ensemble hurts" verdict).
#
# 0.5% is the chosen threshold: large enough to exclude numerical
# ties at any realistic scale; small enough that genuine
# improvements or regressions still produce the delta sentence.
MEANINGFUL_LIFT_PCT_THRESHOLD = 0.5

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
        # FIX 6: capitalize method name at sentence start.
        dominant_clause = (
            f" {_method_sentence_start(method_name)} weights: "
            f"{dominant_name} receives "
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
        # FIX A (post-eval): when ensemble and best constituent are
        # numerically indistinguishable (|delta_pct| below the
        # meaningful-lift threshold), render a "matches within
        # rounding" sentence rather than two identical integers + a
        # 0.0% delta. Keeps Tier 1 readable and the message honest.
        if abs(delta_pct) < MEANINGFUL_LIFT_PCT_THRESHOLD:
            comparison_clause = (
                f" Ensemble holdout MSE matches the best single "
                f"constituent ({dominant_name}) within rounding — no "
                f"meaningful lift from ensembling."
            )
        elif delta_pct > 0:
            comparison_clause = (
                f" Ensemble holdout MSE "
                f"{format_scale_aware(float(ensemble_mse))} vs "
                f"{dominant_name} alone "
                f"{format_scale_aware(float(dominant_mse))} — "
                f"ensemble adds {delta_pct:.1f}% MSE reduction over "
                f"the single best constituent, justifying the weighting."
            )
        else:
            comparison_clause = (
                f" Ensemble holdout MSE "
                f"{format_scale_aware(float(ensemble_mse))} "
                f"exceeds {dominant_name} alone "
                f"{format_scale_aware(float(dominant_mse))} by "
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
                f"(MSE={format_scale_aware(float(mse))})"
            )
        weights_sentence = (
            f"Weights assigned by {method_name}: " + "; ".join(pairs) + "."
        )
    equal_sentence = ""
    if equal_weight_mse is not None and ensemble_mse is not None:
        equal_sentence = (
            f" Equal-weight baseline MSE "
            f"{format_scale_aware(float(equal_weight_mse))}."
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
    if float(dominant_mse) <= 0:
        return None
    # FIX B (post-eval): require the ensemble to be worse by more
    # than MEANINGFUL_LIFT_PCT_THRESHOLD (0.5%) before firing an
    # "ensemble hurts" verdict. Below that threshold, the Tier 1
    # "matches within rounding" phrasing already communicates the
    # finding; a Tier 3 "ensemble hurts" on a -0.004% gap is too
    # strong.
    ratio = float(ensemble_mse) / float(dominant_mse)
    if ratio <= 1.0 + MEANINGFUL_LIFT_PCT_THRESHOLD / 100.0:
        return None
    return (
        f"Ensemble holdout MSE "
        f"{format_scale_aware(float(ensemble_mse))} exceeds the "
        f"best single constituent's "
        f"{format_scale_aware(float(dominant_mse))}. Ensemble "
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
