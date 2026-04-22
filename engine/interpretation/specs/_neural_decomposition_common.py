"""
Shared helpers for Prompt C7 Neural-decomposition forecaster specs.

Used by `nbeats_forecast` and `nhits_forecast`. Both use architectural
decomposition with direct multi-horizon training — the model outputs
all horizon steps in a single pass rather than recursive 1-step feed-
forward.

Leading-underscore filename marks this as spec-internal.
"""

from typing import Optional

from interpretation.specs._neural_sequence_common import (
    trigger_insufficient_neural_training,
    trigger_neural_convergence_not_reached,
    trigger_params_exceed_training_samples,
    trigger_backend_fallback_neural,
)
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)


def render_decomposition_tier1(
    technique_label: str,
    results: dict,
    architecture_desc: str,
    preferred_backend: str = "pytorch",
) -> str:
    """Tier 1 for neural decomposition forecasters.

    Same structure as neural sequence but cites direct multi-horizon
    mechanism in Tier 1.
    """
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    rmse = results.get("rmse")
    r2 = results.get("r2")
    backend = str(results.get("backend") or "")
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "n/a"
    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
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
        f"({n} observations) over {horizon} periods via **direct multi-"
        f"horizon** architecture — the model outputs all {horizon} "
        f"steps in a single pass. In-sample 1-step RMSE {rmse_str}, "
        f"R²={r2_str}{verdict}. {architecture_desc}.{backend_clause}"
    )
