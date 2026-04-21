"""
InterpretationSpec for stochastic_volatility (SV).

Inherits the Prompt A/B ``garch_model`` Tier 1 persistence-band
narrative (Decision D1). Tier 1 cites filtered volatility per D1
(forward-causal, comparable to GARCH's σ_t). Tier 2 adds three
SV-specific honest disclosures:

  D13 — transformation bias (quasi-ML on log-squared returns
        introduces Jensen-inequality bias on back-transform).
  D12 — Gaussian-only innovation distribution (wrapper does not
        support Student-t).
  D4  — absence-of-forecast disclosure (wrapper does not emit
        forecast path; historical filtered/smoothed vol is the
        deliverable — parallels C5 BVAR IRF/FEVD absence).

Decision D18: near-integrated Tier 3 trigger at φ > 0.98 inherited
from GARCH for cross-spec consistency.

Decision D16: input-kurtosis Tier 3 trigger when sample excess
kurtosis > 6 flags Gaussian-only SV as mis-specified on heavy-
tailed return series.

Results-dict keys consumed:

    series_name / n_obs
    mu / phi / sigma_eta / half_life
    aic / neg_loglik
    filtered_vol_min / filtered_vol_max
    smoothed_vol_min / smoothed_vol_max
    input_kurtosis
    unconditional_log_vol_std
    innovation_distribution
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _persistence_band(phi: float) -> str:
    """Reuses the GARCH 4-band convention (garch_model.py:56-71)."""
    try:
        v = float(phi)
    except Exception:
        return "unknown"
    if v < 0.3:
        return "low"
    if v < 0.7:
        return "moderate"
    if v < 0.9:
        return "high"
    return "very high"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    phi = results.get("phi")
    half_life = results.get("half_life")
    filt_min = results.get("filtered_vol_min")
    filt_max = results.get("filtered_vol_max")

    phi_str = FMT_COEF_UNSIGNED.format(float(phi)) if phi is not None else "n/a"
    band = _persistence_band(phi) if phi is not None else "unavailable"

    hl_clause = ""
    if half_life is not None:
        try:
            hl_clause = (
                f"volatility shocks have a half-life of approximately "
                f"{format_scale_aware(float(half_life))} trading days. "
            )
        except Exception:
            pass

    vol_range_clause = ""
    if filt_min is not None and filt_max is not None:
        try:
            ratio = float(filt_max) / max(float(filt_min), 1e-12)
            vol_range_clause = (
                f"Filtered conditional volatility (the wrapper's forward-"
                f"causal analog of GARCH's σ_t) ranges from "
                f"{format_scale_aware(float(filt_min))} to "
                f"{format_scale_aware(float(filt_max))} across the sample "
                f"— a {ratio:.1f}× dynamic range. "
            )
        except Exception:
            pass

    # Actionable closer keyed on persistence band.
    if band in ("very high",):
        closer = (
            "At this persistence level, the model's forward-looking "
            "utility is limited to short horizons (single-digit "
            "trading weeks) before reverting toward the long-run mean."
        )
    elif band == "high":
        closer = (
            "Medium-horizon volatility forecasts are meaningful; "
            "mean-reversion takes weeks to materialize."
        )
    elif band == "moderate":
        closer = (
            "Short-horizon volatility forecasts are meaningful; "
            "the process mean-reverts within a handful of periods."
        )
    else:
        closer = (
            "Volatility is near-iid; the model offers little "
            "forward-looking benefit over a sample-mean-volatility "
            "baseline."
        )

    return (
        f"Stochastic volatility model fitted to "
        f"{format_series_reference(name)} ({n} observations). Latent "
        f"volatility persistence φ = {phi_str} ({band}); {hl_clause}"
        f"{vol_range_clause}{closer}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    mu = results.get("mu")
    phi = results.get("phi")
    sigma_eta = results.get("sigma_eta")
    aic = results.get("aic")
    neg_ll = results.get("neg_loglik")
    s_min = results.get("smoothed_vol_min")
    s_max = results.get("smoothed_vol_max")
    unc = results.get("unconditional_log_vol_std")
    innov = str(results.get("innovation_distribution", "Gaussian"))

    mu_str = format_scale_aware(float(mu)) if mu is not None else "n/a"
    phi_str = FMT_COEF_UNSIGNED.format(float(phi)) if phi is not None else "n/a"
    sig_str = FMT_COEF_UNSIGNED.format(float(sigma_eta)) if sigma_eta is not None else "n/a"
    aic_str = format_scale_aware(float(aic)) if aic is not None else "n/a"
    nll_str = format_scale_aware(float(neg_ll)) if neg_ll is not None else "n/a"

    smoothed_clause = ""
    if s_min is not None and s_max is not None:
        try:
            smoothed_clause = (
                f" Smoothed volatility (retrospective Kalman smoother, "
                f"conditioning on the full sample) ranges from "
                f"{format_scale_aware(float(s_min))} to "
                f"{format_scale_aware(float(s_max))}."
            )
        except Exception:
            pass

    unc_clause = ""
    if unc is not None:
        try:
            unc_clause = (
                f" Unconditional log-volatility standard deviation "
                f"σ_η / √(1 − φ²) = {format_scale_aware(float(unc))}."
            )
        except Exception:
            pass

    # D13 — transformation-bias disclosure.
    transformation_bias = (
        " Back-transforming filtered/smoothed log-volatility to "
        "volatility scale introduces Jensen-inequality bias "
        "(E[exp(X)] ≠ exp(E[X])); reported volatility values carry "
        "this systematic bias. For unbiased volatility estimates, "
        "MCMC-based SV inference is preferable if available."
    )

    # D12 — Gaussian-only disclosure.
    innov_clause = (
        f" Wrapper assumes {innov} innovations in both observation and "
        "state equations; Student-t or other heavy-tailed alternatives "
        "are not implemented (Convention C)."
    )

    # D4 — no-forecast disclosure (parallel to C5 BVAR IRF/FEVD).
    no_forecast = (
        " The wrapper does not emit a forecast path; historical "
        "filtered/smoothed volatility is the deliverable (parallel to "
        "the BVAR wrapper's IRF/FEVD absence — cross-technique honest-"
        "disclosure convention)."
    )

    return (
        f"Stochastic volatility AR(1) log-variance model: "
        f"h_t = μ + φ(h_{{t−1}} − μ) + σ_η · η_t, with observation "
        f"equation y_t = exp(h_t/2) · ε_t. Persistence φ = {phi_str}, "
        f"innovation std σ_η = {sig_str}, long-run log-variance "
        f"μ = {mu_str}. Filtered volatility from the Kalman filter is "
        f"the forward-causal conditional estimate; smoothed volatility "
        f"is the retrospective-view estimate.{smoothed_clause}{unc_clause} "
        f"Estimation: quasi-maximum likelihood via Kalman filter on "
        f"log-squared returns on {n} observations (neg log-likelihood "
        f"= {nll_str}, AIC = {aic_str}).{transformation_bias}"
        f"{innov_clause}{no_forecast}"
    )


def _trigger_near_integrated_volatility(results: dict) -> Optional[str]:
    """D18 — threshold φ > 0.98 inherited from GARCH for cross-spec
    consistency."""
    phi = results.get("phi")
    if phi is None:
        return None
    try:
        v = float(phi)
    except Exception:
        return None
    if v <= 0.98:
        return None
    return (
        f"Persistence φ = {FMT_COEF_UNSIGNED.format(v)} is very close "
        f"to 1. Volatility is near-integrated — shocks decay extremely "
        f"slowly and the long-run mean interpretation is weak. This "
        f"pattern is typical of high-frequency equity returns. Forward-"
        f"looking use beyond a few weeks carries substantial "
        f"uncertainty; the wrapper's half-life approximation may "
        f"understate persistence at this boundary."
    )


def _trigger_low_persistence(results: dict) -> Optional[str]:
    phi = results.get("phi")
    if phi is None:
        return None
    try:
        v = float(phi)
    except Exception:
        return None
    if v >= 0.3:
        return None
    return (
        f"Persistence φ = {FMT_COEF_UNSIGNED.format(v)} is low; "
        f"volatility is essentially iid. The SV framing adds little "
        f"over a sample-mean-volatility forecast on this series. "
        f"Verify the input is returns (not levels) and that the "
        f"series has meaningful volatility clustering."
    )


def _trigger_gaussian_on_fat_tails(results: dict) -> Optional[str]:
    """D16 — input-kurtosis threshold of 6 flags Gaussian-only SV as
    mis-specified on heavy-tailed return series. Normal distribution
    has kurtosis exactly 3; k > 6 is twice that (3× excess)."""
    k = results.get("input_kurtosis")
    if k is None:
        return None
    try:
        v = float(k)
    except Exception:
        return None
    if v <= 6.0:
        return None
    return (
        f"Sample kurtosis {format_scale_aware(v)} exceeds 6 — the "
        f"input series is heavy-tailed. The wrapper's Gaussian-innovation "
        f"assumption understates tail-event volatility. MCMC-based SV "
        f"with Student-t innovations would better capture tail behavior "
        f"on this series; alternatively, GARCH with Student-t or skew-t "
        f"innovations is a simpler fit."
    )


SPEC = InterpretationSpec(
    technique_id="stochastic_volatility",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_near_integrated_volatility,
        _trigger_low_persistence,
        _trigger_gaussian_on_fat_tails,
    ),
    mode_aware=False,
)

register(SPEC)
