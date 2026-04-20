"""
InterpretationSpec for star_model (smooth-transition AR).

Per V3 rewrite: AR coefficients cited in citation form (per-regime =
value pairs), not Greek φ outside citation form.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_SIGNED,
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _smoothness_band(gamma: float) -> str:
    g = float(gamma)
    if g < 0.5:
        return "gradual"
    if g < 5:
        return "moderate"
    if g < 50:
        return "fast"
    return "effectively discrete"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    transition_type = str(results.get("transition_type", "LSTAR"))
    ar_order = int(results.get("ar_order", 1))
    delay = int(results.get("delay", 1))
    gamma = float(results.get("gamma", 1.0))
    c = float(results.get("c", 0.0))
    G_at_T = results.get("G_at_latest")
    regime_clause = ""
    if G_at_T is not None:
        G_f = float(G_at_T)
        if G_f > 0.8:
            regime_at_latest = "mostly in the upper regime"
        elif G_f < 0.2:
            regime_at_latest = "mostly in the lower regime"
        else:
            regime_at_latest = "transitioning between regimes"
        regime_clause = (
            f"The regime-indicator G(s_T)={G_f:.2f} places the latest "
            f"observation {regime_at_latest}; AR coefficients "
            f"interpolate between the two regimes via the "
            f"{transition_type.lower()} function."
        )
    return (
        f"{transition_type}({ar_order}) model on "
        f"{format_series_reference(name)} with transition variable "
        f"y(t-{delay}). Smoothness γ={FMT_COEF_UNSIGNED.format(gamma)} "
        f"({_smoothness_band(gamma)} transition speed), centered at "
        f"c={FMT_COEF_SIGNED.format(c)}. {regime_clause}"
    )


def _tier2(results: dict) -> str:
    transition_type = str(results.get("transition_type", "LSTAR"))
    ar_order = int(results.get("ar_order", 1))
    phi_lower = list(results.get("phi_lower") or [])
    phi_upper = list(results.get("phi_upper") or [])
    aic = results.get("aic")
    aic_linear = results.get("aic_linear_baseline")
    transition_math = {
        "LSTAR": "G(s_t;γ,c) = 1/(1+exp(-γ(s_t-c)))",
        "ESTAR": "G(s_t;γ,c) = 1 - exp(-γ(s_t-c)²)",
    }.get(transition_type.upper(), "G(s_t;γ,c)")
    lower_coefs = (
        ", ".join(f"AR({i+1})={FMT_COEF_SIGNED.format(float(v))}" for i, v in enumerate(phi_lower))
        if phi_lower else "not reported"
    )
    upper_coefs = (
        ", ".join(f"AR({i+1})={FMT_COEF_SIGNED.format(float(v))}" for i, v in enumerate(phi_upper))
        if phi_upper else "not reported"
    )
    aic_clause = ""
    if aic is not None and aic_linear is not None:
        improvement = float(aic_linear) - float(aic)
        aic_clause = (
            f" AIC {format_scale_aware(float(aic))} vs "
            f"{format_scale_aware(float(aic_linear))} for a "
            f"linear AR({ar_order}) baseline — STAR improvement is "
            f"{improvement:.1f} AIC units."
        )
    return (
        f"Smooth-transition AR with {transition_type.lower()} transition "
        f"{transition_math}. Per-regime AR coefficients in the lower "
        f"regime: {lower_coefs}; in the upper regime: {upper_coefs}. "
        f"Model fit via nonlinear least squares.{aic_clause} Unlike "
        f"TAR, regime assignment is continuous; unlike Markov "
        f"Switching, regime dynamics are deterministic given the "
        f"transition variable."
    )


def _trigger_very_gradual(results: dict) -> Optional[str]:
    gamma = results.get("gamma")
    if gamma is None or float(gamma) >= 0.5:
        return None
    return (
        f"Smoothness γ={FMT_COEF_UNSIGNED.format(float(gamma))} is "
        f"below 0.5 — the transition is very gradual. The series may "
        f"not require a two-regime specification; a linear AR may "
        f"suffice."
    )


def _trigger_effectively_discrete(results: dict) -> Optional[str]:
    gamma = results.get("gamma")
    if gamma is None or float(gamma) <= 100:
        return None
    return (
        f"Smoothness γ={FMT_COEF_UNSIGNED.format(float(gamma))} "
        f"exceeds 100 — the transition is effectively discrete. TAR "
        f"or SETAR may fit equivalently with fewer parameters; "
        f"consider switching model class."
    )


def _trigger_low_aic_improvement(results: dict) -> Optional[str]:
    aic = results.get("aic")
    aic_linear = results.get("aic_linear_baseline")
    if aic is None or aic_linear is None:
        return None
    improvement = float(aic_linear) - float(aic)
    if improvement >= 2:
        return None
    return (
        f"AIC improvement over linear AR is only {improvement:.1f}, "
        f"below the 2-point threshold for meaningful model "
        f"improvement. STAR adds little over the linear baseline; "
        f"prefer the simpler linear model."
    )


SPEC = InterpretationSpec(
    technique_id="star_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_very_gradual,
        _trigger_effectively_discrete,
        _trigger_low_aic_improvement,
    ),
    mode_aware=False,
)

register(SPEC)
