"""
InterpretationSpec for echo_state_network.

Inherits C2 forecaster Tier 1 structure. Tier 2 highlights the
distinctive closed-form readout (no training-loss curve) and the D9
non-interpretability disclosure (random sparse reservoir projection).
Preferred backend reservoirpy with numpy fallback.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    rmse = results.get("rmse")
    r2 = results.get("r2")
    N = int(results.get("reservoir_size", 0) or 0)
    rho = results.get("spectral_radius")
    alpha = results.get("leak_rate")
    ridge_alpha = results.get("ridge_alpha")
    sparsity = results.get("sparsity")
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
            verdict = " — good fit"
        elif r2_f >= 0.4:
            verdict = " — moderate fit"
        else:
            verdict = " — weak fit"
    sparsity_pct = int(round(float(sparsity) * 100)) if sparsity is not None else 10
    backend_clause = ""
    if backend and backend != "reservoirpy":
        backend_clause = f" Running on {backend} fallback — reservoirpy library not installed."
    return (
        f"Echo State Network forecast of {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. In-sample RMSE "
        f"{rmse_str}, R²={r2_str}{verdict}. Reservoir: {N} neurons, "
        f"spectral radius ρ={rho}, leak rate α={alpha}, sparsity "
        f"{sparsity_pct}%, ridge-regularized readout (α={ridge_alpha})."
        f"{backend_clause}"
    )


def _tier2(results: dict) -> str:
    N = int(results.get("reservoir_size", 0) or 0)
    rho = results.get("spectral_radius")
    alpha = results.get("leak_rate")
    ridge_alpha = results.get("ridge_alpha")
    backend = str(results.get("backend") or "")
    fallback_note = ""
    if backend and backend != "reservoirpy":
        fallback_note = (
            f" **Backend fallback:** reservoirpy not available; "
            f"{backend} implementation in use. Results should be "
            f"comparable across backends but may differ in warmup / "
            f"state-initialization details."
        )
    # D9 — non-interpretability disclosure
    non_interp = (
        "**Non-interpretability disclosure:** the reservoir is a "
        "random sparse projection — no feature semantics are learned. "
        "Readout coefficients operate on random high-dimensional "
        "coordinates rather than original time-series features; the "
        "model is a black-box memory machine. Parallel to the BVAR "
        "IRF/FEVD-absence honest-disclosure convention."
    )
    return (
        f"Echo State Network — a reservoir-computing RNN variant. "
        f"**Training is closed-form**, not iterative: a sparse random "
        f"reservoir of {N} neurons updates via leak-rate-weighted tanh "
        f"activation; only the readout weights W_out are trained via "
        f"ridge regression (α={ridge_alpha}). No loss curve exists "
        f"because the readout is a closed-form ridge solve — do not "
        f"expect epoch/batch disclosure. Spectral radius ρ={rho} "
        f"below 1.0 satisfies the echo state property; leak rate "
        f"α={alpha} gives temporal integration.{fallback_note} "
        f"{non_interp}"
    )


def _trigger_backend(results: dict) -> Optional[str]:
    backend = str(results.get("backend") or "")
    if not backend or backend == "reservoirpy":
        return None
    return (
        f"Preferred backend `reservoirpy` is not installed; running on "
        f"`{backend}` fallback. Results are valid but may differ from "
        f"the reference reservoirpy implementation in warmup / state-"
        f"initialization details. For exact semantics, install "
        f"`reservoirpy`."
    )


def _trigger_spectral_radius_boundary(results: dict) -> Optional[str]:
    rho = results.get("spectral_radius")
    if rho is None:
        return None
    try:
        r = float(rho)
        if r < 1.0:
            return None
    except Exception:
        return None
    return (
        f"Spectral radius ρ={rho} is at or above 1.0 — the echo state "
        f"property may be violated; reservoir dynamics could be "
        f"non-stable. Reduce spectral_radius below 1.0."
    )


def _trigger_insufficient_training(results: dict) -> Optional[str]:
    n_train = results.get("n_train")
    N = results.get("reservoir_size")
    if n_train is None or N is None:
        return None
    try:
        if int(n_train) >= 5 * int(N):
            return None
    except Exception:
        return None
    return (
        f"Training sample count ({n_train}) is below 5× the reservoir "
        f"size ({N}). The readout ridge regression is poorly "
        f"constrained; forecasts may be unreliable. Consider shrinking "
        f"reservoir_size or obtaining more data."
    )


SPEC = InterpretationSpec(
    technique_id="echo_state_network",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_backend,
        _trigger_spectral_radius_boundary,
        _trigger_insufficient_training,
    ),
    mode_aware=False,
)

register(SPEC)
