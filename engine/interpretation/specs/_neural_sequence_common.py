"""
Shared helpers for Prompt C7 Neural-sequence forecaster specs.

Used by `lstm_gru_forecast`, `tcn_forecast`, and `transformer_forecast`
(and, via a sibling helper, the decomposition-architecture cohort).
Hosts the common rendering logic for the point-forecaster-with-
training-loss-curve Tier 1 shape plus the neural-specific Tier 3
triggers (backend fallback, convergence not reached, params-exceed-
training-samples, insufficient training data).

Leading-underscore filename marks this as spec-internal.
"""

from typing import Optional

import numpy as np

from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)


INSUFFICIENT_NEURAL_TRAINING = 100
PARAMS_OVER_SAMPLES_RATIO = 10.0
NEURAL_CONVERGENCE_FINAL_INITIAL_RATIO = 0.95
NEURAL_CONVERGENCE_FINAL_MID_RATIO = 2.0


def render_neural_tier1(
    technique_label: str,
    results: dict,
    architecture_desc: str,
    preferred_backend: str = "pytorch",
) -> str:
    """Tier 1 for neural sequence forecasters.

    Cites: technique + series name + horizon + RMSE + R² + architecture
    + backend (with fallback disclosure if applicable).
    """
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    rmse = results.get("rmse")
    r2 = results.get("r2")
    backend = str(results.get("backend") or "")
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "n/a"
    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
    # R² verdict
    try:
        r2_f = float(r2) if r2 is not None else None
    except Exception:
        r2_f = None
    verdict = ""
    if r2_f is not None:
        if r2_f >= 0.9:
            verdict = " — strong fit"
        elif r2_f >= 0.7:
            verdict = ""
        elif r2_f >= 0.4:
            verdict = " — moderate fit"
        else:
            verdict = " — weak fit"

    backend_clause = ""
    if backend and backend != preferred_backend:
        backend_clause = f" Running on {backend} fallback — {preferred_backend} not installed."

    return (
        f"{technique_label} forecast of {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. In-sample "
        f"RMSE {rmse_str}, R²={r2_str}{verdict}. {architecture_desc}."
        f"{backend_clause}"
    )


def render_neural_tier2_common(
    results: dict,
    technique_label: str,
    architecture_note: str,
    preferred_backend: str = "pytorch",
) -> str:
    """Shared Tier 2 opener for neural sequence forecasters."""
    backend = str(results.get("backend") or "")
    n_train = int(results.get("n_train", 0) or 0)
    epochs = int(results.get("epochs", 0) or 0)
    final_loss = results.get("final_loss")
    final_str = format_scale_aware(float(final_loss)) if final_loss is not None else "n/a"

    fallback_note = ""
    if backend and backend != preferred_backend:
        fallback_note = (
            f" **Backend fallback:** {preferred_backend} not available; "
            f"{backend} used instead. True sequence recurrence / "
            f"convolution / attention is not emulated in the fallback "
            f"— the sklearn MLP (or ensemble) treats the lag window as "
            f"a flat feature vector. For exact {preferred_backend} "
            f"semantics, install `{preferred_backend}`."
        )

    return (
        f"{technique_label}. {architecture_note} "
        f"Training: {epochs} epochs on {n_train} training samples; "
        f"final training loss {final_str}. Multi-step forecast via "
        f"recursive 1-step feed-forward — the model predicts t+1, "
        f"appends to the sequence, predicts t+2, etc. Uncertainty "
        f"grows non-linearly with horizon. No native interpretability; "
        f"consider SHAP or permutation-based attribution post-fit."
        f"{fallback_note}"
    )


def trigger_insufficient_neural_training(results: dict) -> Optional[str]:
    n_train = int(results.get("n_train", 0) or 0)
    if n_train >= INSUFFICIENT_NEURAL_TRAINING:
        return None
    return (
        f"Training sample count {n_train} is below the "
        f"{INSUFFICIENT_NEURAL_TRAINING}-observation rule of thumb "
        f"for neural forecasters. Loss surface is poorly constrained; "
        f"forecasts may be unreliable. Consider a classical method "
        f"(ARIMA, ETS) on short series."
    )


def trigger_neural_convergence_not_reached(results: dict) -> Optional[str]:
    """D14 — fires when final_loss > 0.95 × initial_loss OR
    final_loss > 2 × median(middle 30% of epoch losses)."""
    curve = results.get("loss_curve_summary") or {}
    if not isinstance(curve, dict) or not curve:
        return None
    try:
        initial = float(curve.get("initial"))
        final = float(curve.get("final"))
        mid_median = float(curve.get("median_middle_30pct"))
    except Exception:
        return None
    condition_a = final > NEURAL_CONVERGENCE_FINAL_INITIAL_RATIO * initial
    condition_b = final > NEURAL_CONVERGENCE_FINAL_MID_RATIO * mid_median
    if not (condition_a or condition_b):
        return None
    which = "relative to initial" if condition_a else "relative to mid-training median"
    return (
        f"Training-loss curve suggests the model has not converged — "
        f"final loss {format_scale_aware(final)} vs initial "
        f"{format_scale_aware(initial)} ({which}). Consider training "
        f"for more epochs, lowering the learning rate, or using a "
        f"Balanced / Thorough preset. Forecasts may be unreliable "
        f"under the current fit."
    )


def trigger_params_exceed_training_samples(results: dict) -> Optional[str]:
    """D16 — fires when n_params > 10 × n_train."""
    n_params = results.get("n_params")
    n_train = results.get("n_train")
    if n_params is None or n_train is None:
        return None
    try:
        np_ = int(n_params)
        nt = int(n_train)
        if nt <= 0 or np_ <= PARAMS_OVER_SAMPLES_RATIO * nt:
            return None
    except Exception:
        return None
    return (
        f"Model parameter count ({np_}) exceeds training sample count "
        f"({nt}) by {np_ / max(nt, 1):.1f}× — the network is "
        f"severely overparameterized. Strong regularization (weight "
        f"decay / dropout / early stopping) or more data is required; "
        f"current fit likely memorizes training patterns."
    )


def trigger_backend_fallback_neural(
    results: dict, preferred: str = "pytorch"
) -> Optional[str]:
    """D3 — fires when backend != preferred (e.g., sklearn_mlp instead
    of pytorch)."""
    backend = str(results.get("backend") or "")
    if not backend or backend == preferred:
        return None
    return (
        f"Preferred backend `{preferred}` is not installed; running on "
        f"`{backend}` fallback. The two are NOT equivalent — the "
        f"fallback approximates the sequence model via a flat-feature "
        f"MLP and cannot capture true recurrence / convolution / "
        f"attention. For production use, install `{preferred}`."
    )
