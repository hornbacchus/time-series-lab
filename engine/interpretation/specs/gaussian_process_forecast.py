"""
InterpretationSpec for gaussian_process_forecast.

Inherits C2 forecaster Tier 1 structure (RMSE + n_obs + horizon); Tier
2 reuses the C5 BVAR credible-vs-confidence semantic disclosure (D6).
D17: length-scale-at-bound Tier 3 trigger flags kernel convergence
failures.
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


LENGTH_SCALE_BOUND_MULT = 1.1


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_observations", 0))
    horizon = int(results.get("horizon", 0))
    rmse = results.get("rmse")
    r2 = results.get("r2")
    avg_std = results.get("avg_forecast_std")
    kernel = str(results.get("kernel_type") or "rbf").upper()
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "n/a"
    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
    std_str = format_scale_aware(float(avg_std)) if avg_std is not None else "n/a"
    try:
        r2_f = float(r2) if r2 is not None else None
    except Exception:
        r2_f = None
    verdict = ""
    if r2_f is not None:
        if r2_f < 0.4:
            verdict = " — weak fit"
        elif r2_f < 0.7:
            verdict = " — moderate fit"
    return (
        f"Gaussian process forecast of {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods using a {kernel} "
        f"kernel. In-sample RMSE {rmse_str} on {n} observations "
        f"(R²={r2_str}{verdict}). Average forecast posterior standard "
        f"deviation {std_str} — reported credible intervals are "
        f"Bayesian-posterior intervals (95% by default)."
    )


def _tier2(results: dict) -> str:
    lml = results.get("log_marginal_likelihood")
    kernel_params = str(results.get("kernel_params") or "unavailable")
    length_scale = results.get("length_scale")
    normalized = bool(results.get("normalized", False))
    n = int(results.get("n_observations", 0))
    lml_str = format_scale_aware(float(lml)) if lml is not None else "n/a"
    ls_str = format_scale_aware(float(length_scale)) if length_scale is not None else "n/a"

    # D6 — credible-vs-confidence reuse of BVAR pattern
    credible_sentence = (
        "**Credible intervals (Bayesian posterior) are not confidence "
        "intervals (frequentist coverage)** — they answer 'what is "
        "the probability the true value lies in this range given the "
        "data and prior' rather than 'what fraction of resampled "
        "intervals would contain the true value'."
    )

    normalize_note = (
        " Input series was normalized before fitting (zero mean, unit "
        "variance); forecasts and posterior std are denormalized back "
        "to the original scale."
        if normalized
        else " Input series used on the original scale (no normalization)."
    )

    return (
        f"Gaussian process regression via scikit-learn. Fitted kernel: "
        f"{kernel_params}. Length-scale (primary smoothness "
        f"hyperparameter) = {ls_str}. Log marginal likelihood = "
        f"{lml_str}. {credible_sentence} Joint multi-horizon posterior; "
        f"posterior covariance encodes multi-step dependencies "
        f"naturally so credible intervals widen with horizon. "
        f"Computational cost is O(n³) — gated to at most 200 training "
        f"points on Fast, 500 on Balanced, 1000 on Thorough; larger "
        f"samples are subsampled with a warning.{normalize_note}"
    )


def _trigger_length_scale_at_bound(results: dict) -> Optional[str]:
    """D17 — fires when length_scale is within 10% of its lower
    bound, indicating the optimizer failed to find a meaningful
    smoothness scale."""
    ls = results.get("length_scale")
    bound = results.get("length_scale_lower_bound")
    if ls is None or bound is None:
        return None
    try:
        ls_v = float(ls)
        bnd = float(bound)
        if bnd <= 0 or ls_v >= LENGTH_SCALE_BOUND_MULT * bnd:
            return None
    except Exception:
        return None
    return (
        f"Length-scale ℓ={format_scale_aware(ls_v)} hit the optimizer's "
        f"lower bound ({format_scale_aware(bnd)}). The GP has "
        f"degenerated into a near-white-noise model over training "
        f"points; the fit is numerically unstable. Consider a Matérn "
        f"kernel (less smooth), rescaling the input time axis, or "
        f"adding more training observations."
    )


def _trigger_low_r2(results: dict) -> Optional[str]:
    r2 = results.get("r2")
    avg_std = results.get("avg_forecast_std")
    rmse = results.get("rmse")
    if r2 is None or avg_std is None or rmse is None:
        return None
    try:
        if float(r2) >= 0.4:
            return None
    except Exception:
        return None
    return (
        f"R²={FMT_COEF_UNSIGNED.format(float(r2))} with average "
        f"posterior std {format_scale_aware(float(avg_std))} "
        f"comparable to RMSE {format_scale_aware(float(rmse))} — the "
        f"GP explains little variance but posterior intervals are "
        f"appropriately wide. Treat as an uncertain nowcast rather "
        f"than a point forecast."
    )


SPEC = InterpretationSpec(
    technique_id="gaussian_process_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_length_scale_at_bound,
        _trigger_low_r2,
    ),
    mode_aware=False,
)

register(SPEC)
