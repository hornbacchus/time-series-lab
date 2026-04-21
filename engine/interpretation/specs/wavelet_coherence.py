"""
InterpretationSpec for wavelet_coherence.

Class 3 (cross-spectral bivariate). Tier 1 mirrors rolling_ccf_lag's
paired-fact structure (lead/lag + magnitude) but extends to time-
frequency space by citing the dominant scale's period.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
    interpret_correlation_strength,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _direction_clause(phase_deg, lag):
    """Translate phase-degrees-at-dominant-scale into a direction verb."""
    if phase_deg is None:
        return "in phase with", 0.0
    p = float(phase_deg)
    # Normalize to [-180, 180]
    while p > 180.0:
        p -= 360.0
    while p < -180.0:
        p += 360.0
    abs_p = abs(p)
    if abs_p < 30.0:
        return "in phase with", abs(float(lag or 0.0))
    if abs(abs_p - 180.0) < 30.0:
        return "in antiphase with", abs(float(lag or 0.0))
    # Positive phase → x leads y; negative → x lags y.
    # Wrapper's best_scale_lag is already signed per its convention.
    if p > 0:
        return "leads", abs(float(lag or 0.0))
    return "lags", abs(float(lag or 0.0))


def _tier1(results: dict) -> str:
    x = str(results.get("series_name_x", "X"))
    y = str(results.get("series_name_y", "Y"))
    n = int(results.get("n_obs", 0))
    freq_code = str(results.get("frequency", ""))
    unit_label = {
        "D": "days", "B": "business days", "W": "weeks",
        "M": "months", "MS": "months", "Q": "quarters",
        "QS": "quarters", "Y": "years", "A": "years",
    }.get(freq_code.upper().strip(), "time units")

    best_period = results.get("best_period")
    best_coh = results.get("best_scale_coherence")
    best_lag = results.get("best_scale_lag")
    phase_deg = results.get("phase_degrees_at_dominant_scale")
    global_mean_coh = results.get("global_mean_coherence")
    high_coh_pct = results.get("high_coherence_pct")

    # Years-approximation for long-period leads on quarterly/monthly data
    years_note = ""
    if best_period and freq_code.upper() in ("Q", "QS") and float(best_period) >= 8:
        years_note = f" (≈{float(best_period) / 4:.1f} years)"
    elif best_period and freq_code.upper() in ("M", "MS") and float(best_period) >= 24:
        years_note = f" (≈{float(best_period) / 12:.1f} years)"

    # Coherence adjective via C1 primitive (treat coherence in [0,1] as |rho|)
    coh_adj = "moderate"
    if best_coh is not None:
        coh_info = interpret_correlation_strength(float(best_coh))
        coh_adj = str(coh_info.get("adjective", "moderate"))

    verb, lag_mag = _direction_clause(phase_deg, best_lag)
    # Lag context for antiphase
    lag_context = ""
    if verb == "in antiphase with" and best_period:
        half_period = float(best_period) / 2.0
        lag_context = (
            f" — the {format_scale_aware(float(lag_mag))} {unit_label} "
            f"offset is roughly half the period of {format_scale_aware(float(best_period))}, "
            f"consistent with antiphase coupling"
        )
    elif verb in ("leads", "lags"):
        lag_context = f" by {format_scale_aware(float(lag_mag))} {unit_label}"

    global_clause = ""
    if global_mean_coh is not None:
        gm_adj = interpret_correlation_strength(float(global_mean_coh)).get("adjective", "moderate")
        global_clause = (
            f" Global mean coherence "
            f"{format_scale_aware(float(global_mean_coh))} ({gm_adj})"
        )
    high_clause = ""
    if high_coh_pct is not None:
        high_clause = (
            f"; {float(high_coh_pct):.1f}% of the time-frequency plane "
            f"exceeds coherence 0.70"
        )

    if best_period is None or best_coh is None:
        return (
            f"Wavelet coherence between {format_series_reference(x)} and "
            f"{format_series_reference(y)} ({n} observations). No clearly-"
            f"dominant scale identified."
        )

    # Build the core sentence
    coupling_verb_phrase = (
        f"{format_series_reference(x)} {verb} {format_series_reference(y)}"
        if verb != "in antiphase with"
        else f"{format_series_reference(x)} moves in antiphase with {format_series_reference(y)}"
    )
    return (
        f"Wavelet coherence between {format_series_reference(x)} and "
        f"{format_series_reference(y)} ({n} {unit_label.replace(' ', '-') if unit_label != 'time units' else ''} observations) "
        f"peaks at period {format_scale_aware(float(best_period))} "
        f"{unit_label}{years_note} with coherence "
        f"{format_scale_aware(float(best_coh))} ({coh_adj}); at that "
        f"scale, {coupling_verb_phrase}{lag_context}.{global_clause}"
        f"{high_clause}."
    )


def _tier2(results: dict) -> str:
    wavelet = str(results.get("wavelet", "morl"))
    n_scales = results.get("n_scales")
    smoothing_width = results.get("smoothing_width")
    phase_deg = results.get("phase_degrees_at_dominant_scale")
    best_period = results.get("best_period")
    best_lag = results.get("best_scale_lag")

    scales_str = f"{int(n_scales)} log-spaced scales" if n_scales else "log-spaced scales"
    smooth_str = (
        f"Gaussian smoothing in time and scale (width={int(smoothing_width)} samples)"
        if smoothing_width else
        "Gaussian smoothing in time and scale"
    )
    # Phase-at-dominant context
    phase_clause = ""
    if phase_deg is not None and best_period is not None:
        p = float(phase_deg)
        while p > 180.0:
            p -= 360.0
        while p < -180.0:
            p += 360.0
        if abs(abs(p) - 180.0) < 30.0 and best_lag is not None:
            half_period = float(best_period) / 2.0
            phase_clause = (
                f" Phase lag at dominant scale ≈ 180° (antiphase) — the "
                f"reported {format_scale_aware(float(abs(best_lag)))}-unit lead "
                f"equals half the dominant period "
                f"{format_scale_aware(float(best_period))}, reflecting "
                f"the antiphase pairing rather than a true lead-lag "
                f"causal direction."
            )
        else:
            phase_clause = (
                f" Phase lag at dominant scale: {format_scale_aware(p)}°."
            )

    return (
        f"Wavelet coherence via {wavelet} wavelet on {scales_str}, "
        f"coherence computed as |S_xy|² / (S_xx · S_yy) with {smooth_str}. "
        f"Coherence is bounded [0, 1]; no analytic null distribution is "
        f"emitted for this technique. For formal peak-significance "
        f"testing against a red-noise null, a Monte Carlo surrogate-data "
        f"procedure (not in this wrapper) is required.{phase_clause} "
        f"The cone of influence is not masked; coherence estimates at "
        f"the highest scales near the series boundaries are artificially "
        f"elevated by edge effects."
    )


def _trigger_antiphase_coupling(results: dict) -> Optional[str]:
    phase_deg = results.get("phase_degrees_at_dominant_scale")
    if phase_deg is None:
        return None
    p = float(phase_deg)
    while p > 180.0:
        p -= 360.0
    while p < -180.0:
        p += 360.0
    if abs(abs(p) - 180.0) >= 30.0:
        return None
    return (
        f"Phase lag at dominant scale is approximately antiphase (≈180°); "
        f"the \"leads by N {results.get('frequency', 'periods')}\" "
        f"rendering is a half-period reflection of antiphase coupling, "
        f"not a causal lead-lag. Interpret with caution — the two series "
        f"move in opposing directions at this frequency rather than with "
        f"a fixed time delay."
    )


def _trigger_low_global_coherence(results: dict) -> Optional[str]:
    gmc = results.get("global_mean_coherence")
    if gmc is None or float(gmc) >= 0.3:
        return None
    return (
        f"Global mean coherence {format_scale_aware(float(gmc))} is below "
        f"0.3 — the two series are largely uncoupled across the time-"
        f"frequency plane. Peak coherence at a specific scale may still "
        f"be meaningful, but the overall relationship is weak."
    )


SPEC = InterpretationSpec(
    technique_id="wavelet_coherence",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_antiphase_coupling,
        _trigger_low_global_coherence,
    ),
    mode_aware=False,
)

register(SPEC)
