"""
Shared helpers for Prompt C7 Tree-based forecaster specs.

Used by `random_forest_forecast`, `xgboost_forecast`, `lightgbm_forecast`,
and `gradient_boosting_forecast`. Hosts the common rendering logic for
the point-forecaster-with-feature-importance Tier 1 shape plus the
tree-specific Tier 3 triggers (Decisions D3 backend-fallback, D11
overfitting, D15 time-index-dominance).

Leading-underscore filename marks this as spec-internal (not a
registered spec).
"""

from typing import Optional

from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)


TREE_EXTRAPOLATION_CAVEAT_HORIZON = 6
OVERFITTING_RATIO_THRESHOLD = 2.0
INSUFFICIENT_TRAINING_THRESHOLD = 100


def render_top_features(results: dict, k: int = 5) -> str:
    """Render top-K features as a compact string.

    Falls back to the wrapper's single `top_feature` field when the
    full top_features list is unavailable.
    """
    top_features = results.get("top_features") or []
    if not top_features:
        tf = results.get("top_feature")
        return f"dominant feature: {tf}" if tf else "feature importances unavailable"
    parts = []
    for entry in top_features[:k]:
        try:
            name = entry.get("name")
            imp = entry.get("importance")
            if name is None or imp is None:
                continue
            parts.append(f"{name}={FMT_COEF_UNSIGNED.format(float(imp))}")
        except Exception:
            continue
    if not parts:
        return "feature importances unavailable"
    return "top features: " + ", ".join(parts)


def render_tree_tier1(
    technique_label: str,
    technique_id: str,
    results: dict,
    preferred_backend: Optional[str] = None,
    extra_tier1_note: str = "",
) -> str:
    """Render the shared Tier 1 template for tree-based forecasters.

    The template cites: series name + n_obs + horizon + train/CV RMSEs
    with overfitting ratio + n_estimators / max_depth + dominant feature.
    """
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    n_train = int(results.get("n_train", 0))
    n_estimators = int(results.get("n_estimators", 0) or 0)
    max_depth = results.get("max_depth")
    train_rmse = results.get("train_rmse")
    cv_rmse = results.get("cv_rmse")
    backend = str(results.get("backend") or "")

    train_str = format_scale_aware(float(train_rmse)) if train_rmse is not None else "n/a"
    cv_str = format_scale_aware(float(cv_rmse)) if cv_rmse is not None else "n/a"
    try:
        ratio = float(cv_rmse) / float(train_rmse) if train_rmse and float(train_rmse) > 0 else None
        ratio_str = f"ratio {ratio:.2f}×" if ratio is not None else ""
        if ratio is not None and ratio >= OVERFITTING_RATIO_THRESHOLD:
            ratio_str += " — substantial overfitting indicated"
    except Exception:
        ratio_str = ""
    depth_str = f"max_depth={max_depth}" if max_depth is not None else ""

    backend_clause = ""
    if preferred_backend and backend and backend != preferred_backend:
        backend_clause = (
            f" **Running on {backend} fallback backend** — the "
            f"{preferred_backend} library is not installed in this "
            f"environment so results are approximate."
        )

    top_features_clause = render_top_features(results)

    return (
        f"{technique_label} forecast of {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods."
        f"{backend_clause} Fit RMSE {train_str} on {n_train} training "
        f"samples; 3-fold CV RMSE {cv_str}"
        + (f" ({ratio_str})" if ratio_str else "")
        + f". Ensemble of {n_estimators} trees"
        + (f" with {depth_str}" if depth_str else "")
        + f". {top_features_clause.capitalize()}."
        + (f" {extra_tier1_note}" if extra_tier1_note else "")
    )


def trigger_overfitting_short_series(results: dict) -> Optional[str]:
    """D11 — tree overfitting: CV RMSE / train RMSE > 2."""
    train = results.get("train_rmse")
    cv = results.get("cv_rmse")
    if train is None or cv is None:
        return None
    try:
        tv = float(train)
        cv_v = float(cv)
        if tv <= 0 or cv_v / tv < OVERFITTING_RATIO_THRESHOLD:
            return None
        ratio = cv_v / tv
    except Exception:
        return None
    n_train = int(results.get("n_train", 0) or 0)
    return (
        f"CV RMSE {format_scale_aware(cv_v)} is {ratio:.2f}× train RMSE "
        f"{format_scale_aware(tv)}, a strong signal of overfitting on "
        f"{n_train} training samples. Consider reducing n_estimators, "
        f"increasing min_samples_leaf, or using fewer lag features."
    )


def trigger_insufficient_training_data(results: dict) -> Optional[str]:
    """D11 — fires when n_train < 100."""
    n_train = int(results.get("n_train", 0) or 0)
    if n_train >= INSUFFICIENT_TRAINING_THRESHOLD:
        return None
    return (
        f"Training sample count {n_train} is below the {INSUFFICIENT_TRAINING_THRESHOLD}-"
        f"observation rule of thumb for tree-ensemble stability. "
        f"Feature importances and forecasts may be unreliable; obtain "
        f"more data or reduce lag-feature count."
    )


def trigger_tree_extrapolation_warning(results: dict) -> Optional[str]:
    """Always-fires for tree forecasters with horizon > 6.

    Tree-based models cannot extrapolate beyond the training-sample
    value range; long-horizon forecasts drift toward training mean."""
    horizon = int(results.get("horizon", 0) or 0)
    if horizon <= TREE_EXTRAPOLATION_CAVEAT_HORIZON:
        return None
    return (
        f"Tree-based forecasters cannot extrapolate beyond the "
        f"training-sample value range. Horizon {horizon} extends "
        f"beyond short-horizon reliability; forecasts beyond 3-6 "
        f"steps should be treated cautiously."
    )


def trigger_backend_fallback(
    results: dict, preferred: str
) -> Optional[str]:
    """D3 — fires when the wrapper's backend differs from the
    preferred library (i.e., a fallback is in use)."""
    backend = str(results.get("backend") or "")
    if not backend or backend == preferred:
        return None
    return (
        f"Preferred backend `{preferred}` is not installed; running on "
        f"`{backend}` fallback. The two are not equivalent — defaults, "
        f"optimization, and importance-metric conventions differ. "
        f"For production use, install `{preferred}` and re-run to "
        f"compare results."
    )


def trigger_time_index_dominance(results: dict) -> Optional[str]:
    """D15 — fires when top_feature == 'time_index'.

    Time-index dominance means the model learned a near-deterministic
    positional mapping rather than temporal dynamics; forecasts
    extrapolate from memorization, not structure."""
    top = str(results.get("top_feature") or "").lower()
    if top != "time_index":
        return None
    return (
        "The `time_index` feature dominates the importance ranking — "
        "the model has learned a near-deterministic function of "
        "position rather than temporal dynamics. Forecasts beyond the "
        "training horizon will extrapolate from memorization, not "
        "from learned dynamics. Consider removing time_index from "
        "the feature set or using a model with explicit temporal "
        "structure (ARIMA, Holt-Winters, Prophet)."
    )


def render_tree_tier2_common(results: dict, algorithm_label: str) -> str:
    """Shared Tier 2 opener: discloses backend, hyperparameters,
    recursive-horizon mechanism, and interpretability axis."""
    n_train = int(results.get("n_train", 0))
    backend = str(results.get("backend") or "sklearn")
    n_estimators = int(results.get("n_estimators", 0) or 0)
    max_depth = results.get("max_depth")
    lr = results.get("learning_rate")
    hp_parts = [f"{n_estimators} trees"]
    if max_depth is not None:
        hp_parts.append(f"max_depth={max_depth}")
    if lr is not None:
        hp_parts.append(f"learning_rate={lr}")
    num_leaves = results.get("num_leaves")
    if num_leaves is not None:
        hp_parts.append(f"num_leaves={num_leaves}")
    subsample = results.get("subsample")
    if subsample is not None:
        hp_parts.append(f"subsample={subsample}")
    hp_str = ", ".join(hp_parts)
    return (
        f"{algorithm_label} (backend: {backend}) with {hp_str}. "
        f"Lag features + rolling-mean statistics → "
        f"{int(results.get('n_features', 0))} total features. Multi-"
        f"step forecast via recursive 1-step feed-forward — "
        f"uncertainty grows non-linearly with horizon. "
        f"TimeSeriesSplit 3-fold CV provides the out-of-sample RMSE "
        f"on {n_train} training samples. Feature importances "
        f"(gain / split-based) expose which engineered features matter "
        f"most; top-5 in the data tables. No SHAP or partial-dependence "
        f"plots generated at the wrapper level."
    )
