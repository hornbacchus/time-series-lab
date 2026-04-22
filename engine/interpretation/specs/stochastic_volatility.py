"""
InterpretationSpec for stochastic_volatility (SV).

Inherits the Prompt A/B ``garch_model`` Tier 1 persistence-band
narrative (Decision D1). Tier 1 cites filtered volatility per D1
(forward-causal, comparable to GARCH's σ_t).

Tier 2 disclosures:

  D13 — transformation bias (quasi-ML on log-squared returns
        introduces Jensen-inequality bias on back-transform).
  D12 — innovation distribution (was Gaussian-only in C6;
        Follow-up 2c closes this by adding an opt-in Student-t
        path with jointly-estimated ν degrees of freedom).
  D4  — absence-of-forecast disclosure (wrapper does not emit
        forecast path; historical filtered/smoothed vol is the
        deliverable — parallels C5 BVAR IRF/FEVD absence).

Tier 2 conditional rewrite on Student-t path (Follow-up 2c):
  - Student-t-specific disclosure: observation offset /
    variance via digamma and trigamma of (ν/2); Gaussian
    limit recovered as ν → ∞.
  - "What Student-t fixes / what it does NOT fix" scope
    frame: closes the D12 Gaussian-only limitation but does
    NOT close the D13 transformation-bias limitation (still
    quasi-ML, Jensen's inequality still applies; future
    follow-up 2b addresses via MCMC).

Tier 3 triggers:

  D18 — near-integrated SV (φ > 0.98) inherited from GARCH.
  D16 — Gaussian-on-fat-tails mis-specification (input
        kurtosis > 6) — gated to Gaussian path only; Student-t
        user is already handling tails.
  D1  — very-heavy-tails on Student-t (ν < 5).
  D2  — near-Gaussian-on-Student-t-path (ν ≥ 30).
  D3  — Student-t optimization failed → Gaussian fallback
        (requested=student_t but fitted=gaussian). Fires with
        actionable remediation text per Follow-up 2c D13.

Results-dict keys consumed:

    series_name / n_obs
    mu / phi / sigma_eta / half_life
    aic / bic / neg_loglik
    filtered_vol_min / filtered_vol_max
    smoothed_vol_min / smoothed_vol_max
    input_kurtosis
    unconditional_log_vol_std
    innovations                  (2c) — "gaussian" or "student_t"
    requested_innovations        (2c) — user's original request
    fitted_innovations           (2c) — actually fitted
    fallback_occurred            (2c) — bool
    nu_degrees_of_freedom        (2c) — float or None
    nu_interpretation_band       (2c) — very_heavy/heavy/moderate/
                                        near_gaussian or None
    n_free_params                (2c) — 3 (Gaussian) or 4 (Student-t)
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


def _nu_band_phrase(band) -> str:
    """Map the wrapper's band token to a human-readable phrase."""
    return {
        "very_heavy_tails": "very heavy tails",
        "heavy_tails":      "heavy tails",
        "moderate_tails":   "moderate tails",
        "near_gaussian":    "near-Gaussian tails",
    }.get(str(band) if band is not None else "", "")


def _innovations_value(results: dict) -> str:
    """Return the fitted-innovations value (lowercased).

    Uses `fitted_innovations` (2c canonical) and falls back to
    `innovations` for older audit payloads. Defaults to
    "gaussian" when absent.
    """
    return str(
        results.get("fitted_innovations")
        or results.get("innovations")
        or "gaussian"
    ).strip().lower()


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

    # Follow-up 2c: Student-t innovation clause when the fit
    # successfully used Student-t. Suppressed on Gaussian (incl.
    # fallback) — the fallback itself is disclosed in Tier 2 / Tier 3.
    innov = _innovations_value(results)
    innov_clause = ""
    if innov == "student_t":
        nu = results.get("nu_degrees_of_freedom")
        band_tok = results.get("nu_interpretation_band")
        if nu is not None and band_tok:
            innov_clause = (
                f"Innovations: Student-t (ν = {float(nu):.2f}, "
                f"{_nu_band_phrase(band_tok)}). "
            )

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
        f"{vol_range_clause}{innov_clause}{closer}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    mu = results.get("mu")
    phi = results.get("phi")
    sigma_eta = results.get("sigma_eta")
    aic = results.get("aic")
    bic = results.get("bic")
    neg_ll = results.get("neg_loglik")
    s_min = results.get("smoothed_vol_min")
    s_max = results.get("smoothed_vol_max")
    unc = results.get("unconditional_log_vol_std")
    innov = _innovations_value(results)
    requested = str(
        results.get("requested_innovations") or innov
    ).strip().lower()
    fallback_occurred = bool(results.get("fallback_occurred", False))
    nu = results.get("nu_degrees_of_freedom")
    nu_band = results.get("nu_interpretation_band")
    k_params = results.get("n_free_params")

    mu_str = format_scale_aware(float(mu)) if mu is not None else "n/a"
    phi_str = FMT_COEF_UNSIGNED.format(float(phi)) if phi is not None else "n/a"
    sig_str = FMT_COEF_UNSIGNED.format(float(sigma_eta)) if sigma_eta is not None else "n/a"
    aic_str = format_scale_aware(float(aic)) if aic is not None else "n/a"
    bic_str = format_scale_aware(float(bic)) if bic is not None else None
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

    # k-adjusted AIC/BIC line
    if k_params is not None and bic_str is not None:
        ic_clause = (
            f"AIC = {aic_str}, BIC = {bic_str} on {int(k_params)} "
            f"free parameters"
        )
    elif k_params is not None:
        ic_clause = f"AIC = {aic_str} on {int(k_params)} free parameters"
    else:
        ic_clause = f"AIC = {aic_str}"

    # ── Conditional D12 — innovation-distribution disclosure ─────
    if innov == "student_t" and nu is not None:
        nu_f = float(nu)
        band_phrase = _nu_band_phrase(nu_band)
        innov_block = (
            f" Innovations ε_t ~ Student-t(ν = {nu_f:.2f}, {band_phrase}); "
            f"ν is jointly estimated with SV parameters via quasi-ML. "
            f"The Student-t path shifts the Kalman filter's "
            f"observation-equation offset to ψ(1/2) − ψ(ν/2) + log(ν) "
            f"and variance to ψ'(1/2) + ψ'(ν/2) (digamma and trigamma); "
            f"as ν → ∞ these recover the Gaussian log-χ²₁ values."
        )
        # "What Student-t fixes / what it does NOT fix" scope frame
        # (Follow-up 2c per-user-feedback refinement).
        scope_block = (
            " What Student-t fixes: the Gaussian-only innovation "
            "assumption (Convention C from the C6 disclosure); the "
            "wrapper now captures heavy tails explicitly. What "
            "Student-t does NOT fix: back-transforming filtered/"
            "smoothed log-volatility to volatility scale still "
            "introduces Jensen-inequality bias (E[exp(X)] ≠ exp(E[X])); "
            "reported volatility values carry this systematic bias "
            "regardless of innovation distribution. For unbiased "
            "volatility estimates, MCMC-based SV inference is "
            "preferable if available (future follow-up 2b addresses "
            "this)."
        )
    else:
        # Gaussian path (incl. D13 fallback) — C6 disclosure with
        # a softer pointer to the Student-t opt-in (Follow-up 2c).
        innov_block = (
            " Wrapper fits Gaussian innovations; Student-t innovations "
            "are available for heavy-tailed return series (set "
            "innovations='student_t' on the next fit)."
        )
        scope_block = (
            " Back-transforming filtered/smoothed log-volatility to "
            "volatility scale introduces Jensen-inequality bias "
            "(E[exp(X)] ≠ exp(E[X])); reported volatility values carry "
            "this systematic bias. For unbiased volatility estimates, "
            "MCMC-based SV inference is preferable if available."
        )

    # ── Fallback disclosure (Follow-up 2c D13) ───────────────────
    fallback_block = ""
    if fallback_occurred or (requested == "student_t" and innov == "gaussian"):
        fallback_block = (
            f" Student-t optimization did not converge on the requested "
            f"path; the wrapper automatically fell back to Gaussian fit "
            f"(reported below). Possible causes: (a) data is genuinely "
            f"Gaussian (ν ≈ ∞ — Student-t likelihood surface has no "
            f"well-defined maximum); (b) data is too short for the "
            f"4-parameter model to identify ν stably; (c) data has "
            f"outliers that destabilize ν estimation. Remediation: "
            f"(i) run innovations='gaussian' explicitly to verify (a); "
            f"(ii) provide a longer series for (b); (iii) inspect / "
            f"winsorize outliers for (c)."
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
        f"= {nll_str}, {ic_clause}).{scope_block}{innov_block}"
        f"{fallback_block}{no_forecast}"
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
    mis-specified on heavy-tailed return series. Gated to the Gaussian
    path (Follow-up 2c Q4): on Student-t path the user is already
    handling tails, so firing "switch to Student-t" would be noise."""
    if _innovations_value(results) == "student_t":
        return None  # Already on the Student-t path — trigger redundant.
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
        f"assumption understates tail-event volatility. Rerun with "
        f"innovations='student_t' to capture tails directly; "
        f"alternatively, GARCH with Student-t or skew-t innovations is "
        f"a simpler fit."
    )


def _trigger_student_t_very_heavy_tails(results: dict) -> Optional[str]:
    """Follow-up 2c D1 — fires when Student-t path estimates ν < 5.

    Even Student-t may struggle at very-heavy-tails; suggests
    checking for structural breaks or mean dynamics beyond SV scope.
    """
    if _innovations_value(results) != "student_t":
        return None
    nu = results.get("nu_degrees_of_freedom")
    if nu is None:
        return None
    try:
        v = float(nu)
    except Exception:
        return None
    if v >= 5.0:
        return None
    return (
        f"Estimated ν = {v:.2f} indicates very heavy tails. Even "
        f"Student-t may struggle to capture extreme moves; consider "
        f"checking for structural breaks, outliers, or heteroskedastic "
        f"mean dynamics beyond the SV model's scope."
    )


def _trigger_near_gaussian_on_student_t_path(results: dict) -> Optional[str]:
    """Follow-up 2c D2 — fires when Student-t path estimates ν ≥ 30.

    Student-t with large ν is essentially Gaussian; suggests running
    innovations='gaussian' on the next fit (faster, simpler).
    """
    if _innovations_value(results) != "student_t":
        return None
    nu = results.get("nu_degrees_of_freedom")
    if nu is None:
        return None
    try:
        v = float(nu)
    except Exception:
        return None
    if v < 30.0:
        return None
    return (
        f"Estimated ν = {v:.2f} is large enough that Student-t is "
        f"essentially Gaussian. Your series appears to not have heavy "
        f"tails at the daily level — Gaussian innovations would fit "
        f"similarly and run faster. Consider innovations='gaussian' on "
        f"the next fit."
    )


def _trigger_student_t_optimization_failed_fallback(results: dict) -> Optional[str]:
    """Follow-up 2c D3 — fires when the user requested Student-t but
    the wrapper fell back to Gaussian after optimization failed on all
    restarts.

    User-visible remediation: the Tier 2 fallback block already lists
    the three possible causes (a/b/c); this trigger summarizes the
    event for the Tier 3 caveats panel so it's not buried in dense
    Tier 2 prose.
    """
    requested = str(
        results.get("requested_innovations")
        or results.get("innovations")
        or "gaussian"
    ).strip().lower()
    fitted = _innovations_value(results)
    fallback_flag = bool(results.get("fallback_occurred", False))
    if not fallback_flag and not (requested == "student_t" and fitted == "gaussian"):
        return None
    return (
        "Student-t optimization did not converge after all restarts; "
        "the wrapper automatically fell back to Gaussian innovations. "
        "Reported parameters and volatility estimates are from the "
        "Gaussian fit, not Student-t. See Tier 2 for the three "
        "possible causes (genuinely-Gaussian data, too-short series, "
        "destabilizing outliers) and their specific remediations."
    )


SPEC = InterpretationSpec(
    technique_id="stochastic_volatility",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_near_integrated_volatility,
        _trigger_low_persistence,
        _trigger_gaussian_on_fat_tails,
        _trigger_student_t_very_heavy_tails,
        _trigger_near_gaussian_on_student_t_path,
        _trigger_student_t_optimization_failed_fallback,
    ),
    mode_aware=False,
)

register(SPEC)
