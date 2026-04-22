"""
InterpretationSpec for autoencoder_anomaly.

Inherits the C1 stl_esd_anomaly Tier 1 shape (count + rate + threshold
+ most-extreme) with key divergences:
  - No direction split — reconstruction error is unsigned magnitude.
  - Threshold is percentile-of-training-error (contamination-based),
    not hypothesis-test alpha (D10 disclosure).
  - D18 always-fires: detected rate = contamination by construction.

Preferred backend pytorch; sklearn PCA fallback approximates the
autoencoder via linear reconstruction.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    n_anom = int(results.get("n_anomalies", 0))
    anom_rate = results.get("anomaly_rate", 0.0)
    most_extreme_idx = results.get("most_extreme_idx")
    most_extreme_error = results.get("most_extreme_error")
    window_size = int(results.get("window_size", 0) or 0)
    hidden_dim = int(results.get("hidden_dim", 0) or 0)
    backend = str(results.get("backend") or "")
    try:
        rate_pct = float(anom_rate) * 100
    except Exception:
        rate_pct = 0.0
    extreme_clause = ""
    if most_extreme_idx is not None and most_extreme_error is not None:
        try:
            extreme_clause = (
                f" Most extreme anomaly at index {int(most_extreme_idx)} "
                f"(reconstruction error "
                f"{format_scale_aware(float(most_extreme_error))})."
            )
        except Exception:
            pass
    backend_clause = ""
    if backend and backend != "pytorch":
        backend_clause = f" Running on {backend} fallback — PyTorch not installed."
    return (
        f"Autoencoder anomaly detection on "
        f"{format_series_reference(name)} ({n} observations). "
        f"**{n_anom} anomalies detected ({rate_pct:.1f}% of "
        f"observations)** at the contamination threshold.{extreme_clause} "
        f"Window size {window_size}, latent dimension {hidden_dim}."
        f"{backend_clause}"
    )


def _tier2(results: dict) -> str:
    window_size = int(results.get("window_size", 0) or 0)
    hidden_dim = int(results.get("hidden_dim", 0) or 0)
    contamination = results.get("contamination")
    threshold = results.get("threshold")
    backend = str(results.get("backend") or "")
    try:
        cont_pct = float(contamination) * 100 if contamination is not None else 5.0
    except Exception:
        cont_pct = 5.0
    backend_note = ""
    if backend and backend != "pytorch":
        backend_note = (
            f" **Backend fallback:** PyTorch not available; {backend} "
            f"used as the autoencoder substitute (linear reconstruction "
            f"rather than non-linear encoder/decoder). Results are "
            f"approximate."
        )
    # D10 — threshold-is-contamination disclosure
    threshold_disclosure = (
        f"**Threshold mechanism:** percentile-based on the user-supplied "
        f"`contamination` parameter ({cont_pct:.1f}% here — the "
        f"top-{cont_pct:.1f}% of reconstruction errors are flagged as "
        f"anomalies). **This is NOT a hypothesis-test alpha** (unlike "
        f"stl_esd_anomaly's α). If the true anomaly fraction differs "
        f"from the user's `contamination` guess, the threshold is "
        f"biased."
    )
    # No-direction-split note (D7 divergence from stl_esd_anomaly)
    direction_note = (
        " **Anomaly direction:** reconstruction error is unsigned — "
        "no upward / downward split (unlike stl_esd_anomaly). "
        "Per-feature reconstruction-error attribution is not exposed "
        "at the wrapper level (backlog)."
    )
    return (
        f"Autoencoder-based anomaly detection via reconstruction error. "
        f"Windows of size {window_size} are encoded to a latent "
        f"dimension of {hidden_dim}; the decoder reconstructs the "
        f"window. Anomaly score = mean squared reconstruction error "
        f"per window. {threshold_disclosure}{backend_note}"
        f"{direction_note}"
    )


def _trigger_contamination_matches_rate(results: dict) -> Optional[str]:
    """D18 — always-fires disclosure.

    By construction, detected rate = contamination. Users should
    understand this is mathematical, not empirical."""
    contamination = results.get("contamination")
    rate = results.get("anomaly_rate")
    if contamination is None or rate is None:
        return None
    try:
        cont = float(contamination)
        r = float(rate)
        if abs(cont - r) > 0.005:
            return None  # only fire when they match closely
    except Exception:
        return None
    return (
        f"Detected anomaly rate ({r*100:.1f}%) equals the user-supplied "
        f"contamination parameter ({cont:.3f}). This is by construction "
        f"— the threshold was set at the {(1-cont)*100:.1f}th "
        f"percentile of reconstruction errors. The detected count does "
        f"not provide evidence about the true anomaly fraction."
    )


def _trigger_backend_fallback(results: dict) -> Optional[str]:
    backend = str(results.get("backend") or "")
    if not backend or backend == "pytorch":
        return None
    return (
        f"Preferred backend `pytorch` is not installed; running on "
        f"`{backend}` fallback. The fallback uses linear reconstruction "
        f"(PCA) rather than a non-linear autoencoder, so it cannot "
        f"capture non-linear anomaly patterns. For exact autoencoder "
        f"semantics, install `pytorch`."
    )


SPEC = InterpretationSpec(
    technique_id="autoencoder_anomaly",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend_fallback,
        _trigger_contamination_matches_rate,
    ),
    mode_aware=False,
)

register(SPEC)
