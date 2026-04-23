"""
InterpretationSpec for stochastic_volatility (SV).

Inherits the Prompt A/B ``garch_model`` Tier 1 persistence-band
narrative (Decision D1). Tier 1 cites filtered volatility per D1
(forward-causal, comparable to GARCH's σ_t).

Tier 2 disclosures (three conditional axes — innovations × inference
method × fallback):

  D13 — transformation bias (quasi-ML on log-squared returns
        introduces Jensen-inequality bias on back-transform).
        Applies to quasi-ML path only. MCMC path (Follow-up 2b)
        removes this bias by sampling directly on returns.
  D12 — innovation distribution (was Gaussian-only in C6;
        Follow-up 2c closes this by adding an opt-in Student-t
        path with jointly-estimated ν degrees of freedom).
  D4  — absence-of-forecast disclosure (wrapper does not emit
        forecast path; historical filtered/smoothed vol is the
        deliverable — parallels C5 BVAR IRF/FEVD absence).
  Backend disclosure — MCMC path always cites which sampler ran
        (pymc NUTS or Kim-Shephard-Chib Gibbs) for replicability.

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


def _inference_method_value(results: dict) -> str:
    """Return the fitted inference-method value (lowercased).

    Uses `fitted_inference_method` (2b canonical) and falls back to
    `inference_method`. Defaults to "quasi_ml" when absent.
    """
    return str(
        results.get("fitted_inference_method")
        or results.get("inference_method")
        or "quasi_ml"
    ).strip().lower()


def _mcmc_backend_display(results: dict) -> str:
    """Render backend name for Tier 2 disclosure.

    Accepts "pymc" or "gibbs" from the audit; emits a human-readable
    phrase. Unknown/None → generic phrase.
    """
    backend = str(results.get("mcmc_backend") or "").strip().lower()
    if backend == "pymc":
        return "pymc NUTS sampler"
    if backend == "gibbs":
        return (
            "Kim-Shephard-Chib mixture-of-normals Gibbs sampler "
            "(pure numpy/scipy; no external MCMC dependency)"
        )
    return "MCMC sampler"


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

    # Follow-up 2b: MCMC posterior-φ closer (Q5). Features φ
    # (persistence) per Q5 — matches quasi-ML Tier 1 band.
    mcmc_clause = ""
    if _inference_method_value(results) == "mcmc":
        phi_mean = results.get("phi_posterior_mean")
        phi_lo = results.get("phi_posterior_hdi_lower")
        phi_hi = results.get("phi_posterior_hdi_upper")
        chains = results.get("mcmc_chains")
        draws = results.get("mcmc_draws_per_chain")
        if phi_mean is not None and phi_lo is not None and phi_hi is not None:
            backend = str(results.get("mcmc_backend", "")).lower()
            backend_short = (
                "pymc NUTS" if backend == "pymc"
                else "Kim-Shephard-Chib Gibbs" if backend == "gibbs"
                else "MCMC"
            )
            chains_str = f"{chains}×{draws}" if chains and draws else "posterior"
            mcmc_clause = (
                f"Posterior mean φ = {float(phi_mean):.3f} with "
                f"95% HDI [{float(phi_lo):.3f}, {float(phi_hi):.3f}] "
                f"({chains_str} draws via {backend_short}). "
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
        f"{vol_range_clause}{innov_clause}{mcmc_clause}{closer}"
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

    # Follow-up 2b — inference method (3rd Tier 2 conditional axis)
    inference = _inference_method_value(results)
    is_mcmc = (inference == "mcmc")

    # ── Estimation clause (quasi-ML vs MCMC) ─────────────────────
    if is_mcmc:
        backend_display = _mcmc_backend_display(results)
        chains = results.get("mcmc_chains")
        draws = results.get("mcmc_draws_per_chain")
        tune = results.get("mcmc_tune")
        total_draws = results.get("mcmc_total_draws")
        rhat_max = results.get("rhat_max")
        rhat_param = results.get("rhat_max_param")
        ess_min = results.get("ess_min")
        ess_param = results.get("ess_min_param")
        div_count = results.get("divergences_count")
        div_fraction = results.get("divergences_fraction")

        cfg_clause = (
            f"{chains} chains × {draws} draws (after {tune} warmup); "
            f"{total_draws} total posterior draws"
            if chains and draws and tune
            else "posterior sampling"
        )

        # Divergence disclosure — pymc has it, Gibbs does not
        div_clause = ""
        if div_count is not None:
            if div_fraction is not None and div_fraction > 0:
                div_clause = (
                    f"; {int(div_count)} divergent transitions "
                    f"({100 * float(div_fraction):.2f}% of draws)"
                )
            elif int(div_count) == 0 and str(results.get("mcmc_backend", "")).lower() == "gibbs":
                div_clause = "; divergent transitions not tracked by the Gibbs sampler"
            elif int(div_count) == 0:
                div_clause = "; no divergent transitions"

        rhat_clause = (
            f"max R-hat {float(rhat_max):.3f} over parameters "
            f"({rhat_param})"
            if rhat_max is not None and rhat_param else "convergence metrics not reported"
        )
        ess_clause = (
            f"minimum ESS {int(float(ess_min))} at parameter {ess_param}"
            if ess_min is not None and ess_param else ""
        )

        # Posterior summaries per parameter
        summary_parts = []
        for pname, pdisplay in (("mu", "μ"), ("phi", "φ"),
                                 ("sigma_eta", "σ_η"), ("nu", "ν")):
            pm = results.get(f"{pname}_posterior_mean")
            lo = results.get(f"{pname}_posterior_hdi_lower")
            hi = results.get(f"{pname}_posterior_hdi_upper")
            if pm is not None and lo is not None and hi is not None:
                summary_parts.append(
                    f"{pdisplay} = {float(pm):.3f} "
                    f"[HDI {float(lo):.3f}, {float(hi):.3f}]"
                )
        posterior_clause = (
            "Posterior: " + ", ".join(summary_parts) + "."
            if summary_parts else ""
        )

        # Information criteria (pymc only)
        waic = results.get("waic")
        loo = results.get("loo")
        ic_extra = ""
        if waic is not None:
            ic_extra += f" WAIC {format_scale_aware(float(waic))}"
            if loo is not None:
                ic_extra += f", LOO {format_scale_aware(float(loo))}."
            else:
                ic_extra += "."
        elif str(results.get("mcmc_backend", "")).lower() == "gibbs":
            ic_extra = (
                " WAIC and LOO not computed by the Gibbs sampler "
                "(pymc backend required for these information criteria)."
            )

        # Backend disclosure (full sentence)
        estimation_clause = (
            f" Estimation: MCMC sampling via {backend_display} with "
            f"{cfg_clause}. Direct likelihood on returns — the log-"
            f"squared transformation bias that affects quasi-ML is "
            f"fully avoided. Convergence diagnostics: {rhat_clause}; "
            f"{ess_clause}{div_clause}. {posterior_clause}{ic_extra}"
        )
    else:
        # quasi-ML path
        estimation_clause = (
            f" Estimation: quasi-maximum likelihood via Kalman filter "
            f"on log-squared returns on {n} observations (neg log-"
            f"likelihood = {nll_str}, {ic_clause}). For publication-"
            f"quality work or posterior uncertainty quantification, "
            f"set inference_method='mcmc' on Balanced or Thorough "
            f"preset to bypass the Jensen-inequality transformation "
            f"bias via direct sampling on returns."
        )

    # ── D13 transformation-bias disclosure ───────────────────────
    # Gated to quasi-ML path (MCMC removes this bias by construction)
    if is_mcmc:
        bias_block = ""  # MCMC removes the bias; no disclosure needed
    else:
        bias_block = (
            " Back-transforming filtered/smoothed log-volatility to "
            "volatility scale introduces Jensen-inequality bias "
            "(E[exp(X)] ≠ exp(E[X])); reported volatility values carry "
            "this systematic bias. For unbiased volatility estimates, "
            "set inference_method='mcmc' (Balanced or Thorough preset)."
        )

    # ── D12 innovation-distribution disclosure ──────────────────
    if innov == "student_t" and nu is not None:
        nu_f = float(nu)
        band_phrase = _nu_band_phrase(nu_band)
        if is_mcmc:
            innov_block = (
                f" Innovations ε_t ~ Student-t(ν = {nu_f:.2f}, "
                f"{band_phrase}); ν was jointly estimated with SV "
                f"parameters via MCMC."
            )
        else:
            innov_block = (
                f" Innovations ε_t ~ Student-t(ν = {nu_f:.2f}, "
                f"{band_phrase}); ν is jointly estimated with SV "
                f"parameters via quasi-ML. The Student-t path shifts "
                f"the Kalman filter's observation-equation offset to "
                f"ψ(1/2) − ψ(ν/2) + log(ν) and variance to ψ'(1/2) + "
                f"ψ'(ν/2) (digamma and trigamma); as ν → ∞ these "
                f"recover the Gaussian log-χ²₁ values."
            )
        # Scope frame — only on Student-t quasi-ML path (on MCMC,
        # both limitations are addressed, so no "what doesn't" needed)
        if is_mcmc:
            scope_block = ""
        else:
            scope_block = (
                " What Student-t fixes: the Gaussian-only innovation "
                "assumption (Convention C from the C6 disclosure); "
                "the wrapper now captures heavy tails explicitly. "
                "What Student-t does NOT fix: back-transforming "
                "filtered/smoothed log-volatility to volatility scale "
                "still introduces Jensen-inequality bias (E[exp(X)] "
                "≠ exp(E[X])); reported volatility values carry this "
                "systematic bias regardless of innovation distribution. "
                "For unbiased volatility estimates, set "
                "inference_method='mcmc' (Balanced or Thorough preset)."
            )
    else:
        # Gaussian path — softer pointer to Student-t opt-in
        innov_block = (
            " Wrapper fits Gaussian innovations; Student-t innovations "
            "are available for heavy-tailed return series (set "
            "innovations='student_t' on the next fit)."
        )
        scope_block = ""

    # ── Fallback disclosures ────────────────────────────────────
    fallback_block = ""
    # Follow-up 2b D9 — Fast + MCMC auto-downgrade
    if bool(results.get("fast_preset_mcmc_downgrade", False)):
        fallback_block += (
            " MCMC was requested on Fast preset; Fast preset's latency "
            "budget is incompatible with MCMC compute cost (30-120 s "
            "minimum). Auto-downgraded to quasi-ML for this fit. "
            "Switch to Balanced or Thorough preset to perform MCMC "
            "inference."
        )
    # Follow-up 2b D7 — MCMC runtime failure → quasi-ML fallback
    if bool(results.get("mcmc_fallback_occurred", False)):
        fallback_block += (
            " MCMC sampling did not converge on the requested path; "
            "the wrapper automatically fell back to quasi-ML "
            "(reported below). Possible causes: (a) sampler "
            "divergences exceeded threshold (R-hat > 1.10 or too many "
            "divergent transitions); (b) library or runtime error "
            "during sampling (pymc/arviz import failure, pytensor "
            "compile failure, memory exhaustion); (c) input data has "
            "pathological features (non-stationarity, extreme "
            "outliers, regime shifts) that MCMC cannot fit without "
            "additional structural assumptions. Remediation: (i) try "
            "Thorough preset for longer chains and tighter target-"
            "accept; (ii) inspect data for stationarity and outliers; "
            "(iii) file an issue with a reproducible example if the "
            "problem persists on clean data."
        )
    # Follow-up 2c D13 — Student-t → Gaussian fallback (unchanged)
    if fallback_occurred or (requested == "student_t" and innov == "gaussian"):
        fallback_block += (
            " Student-t optimization did not converge on the requested "
            "path; the wrapper automatically fell back to Gaussian fit "
            "(reported below). Possible causes: (a) data is genuinely "
            "Gaussian (ν ≈ ∞ — Student-t likelihood surface has no "
            "well-defined maximum); (b) data is too short for the "
            "4-parameter model to identify ν stably; (c) data has "
            "outliers that destabilize ν estimation. Remediation: "
            "(i) run innovations='gaussian' explicitly to verify (a); "
            "(ii) provide a longer series for (b); (iii) inspect / "
            "winsorize outliers for (c)."
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
        f"is the retrospective-view estimate.{smoothed_clause}{unc_clause}"
        f"{estimation_clause}{scope_block}{innov_block}{bias_block}"
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


# ---------------------------------------------------------------------
# Follow-up 2b — 6 new MCMC-related Tier 3 triggers
# ---------------------------------------------------------------------


def _trigger_rhat_failure(results: dict) -> Optional[str]:
    """D4 — fires when max R-hat > 1.01 (warn band) or > 1.05 (fail).

    MCMC path only. R-hat > 1.01 indicates chains haven't fully mixed;
    > 1.05 indicates a real problem. The wrapper's internal threshold
    (1.10 pymc, 1.25 Gibbs) triggers D7 fallback; this D4 trigger
    surfaces sub-threshold values to the user.
    """
    if _inference_method_value(results) != "mcmc":
        return None
    rhat = results.get("rhat_max")
    rhat_param = results.get("rhat_max_param")
    if rhat is None:
        return None
    try:
        v = float(rhat)
    except Exception:
        return None
    if v <= 1.01:
        return None
    severity = "warning" if v <= 1.05 else "failure"
    return (
        f"Convergence {severity}: max R-hat {v:.3f} on parameter "
        f"{rhat_param or '(unspecified)'} exceeds the 1.01 "
        f"convergence threshold. Chain mixing is imperfect — posterior "
        f"summaries should be interpreted with caution. Remediation: "
        f"switch to Thorough preset (longer chains, tighter target-"
        f"accept)."
    )


def _trigger_low_ess(results: dict) -> Optional[str]:
    """D5 — fires when minimum bulk ESS < 400 (warn) or < 200 (fail).

    MCMC path only. Low ESS means few effectively independent draws;
    posterior uncertainty estimates become unreliable.
    """
    if _inference_method_value(results) != "mcmc":
        return None
    ess = results.get("ess_min")
    ess_param = results.get("ess_min_param")
    chains = results.get("mcmc_chains") or 1
    if ess is None:
        return None
    try:
        v = float(ess)
    except Exception:
        return None
    # Threshold scaled per-chain: expect ESS ≥ 400 * chains for
    # reasonable precision.
    per_chain_threshold = 400
    total_threshold = per_chain_threshold * int(chains)
    if v >= total_threshold:
        return None
    severity = (
        "failure" if v < per_chain_threshold * int(chains) / 2
        else "warning"
    )
    return (
        f"Effective sample size {severity}: bulk ESS {int(v)} on "
        f"parameter {ess_param or '(unspecified)'} falls below the "
        f"{total_threshold} threshold ({per_chain_threshold} per "
        f"chain × {int(chains)} chains). Posterior summaries for this "
        f"parameter have wider Monte Carlo error than the other "
        f"parameters. Remediation: run Thorough preset for more draws."
    )


def _trigger_divergent_transitions(results: dict) -> Optional[str]:
    """D6 — fires when divergent transitions exceed 5% of draws.

    Applies to pymc NUTS only — Gibbs sampler has no divergence
    concept (divergences_count=0 by construction on Gibbs path).
    """
    if _inference_method_value(results) != "mcmc":
        return None
    backend = str(results.get("mcmc_backend", "")).lower()
    if backend != "pymc":
        return None
    frac = results.get("divergences_fraction")
    if frac is None:
        return None
    try:
        v = float(frac)
    except Exception:
        return None
    if v <= 0.05:
        return None
    count = int(results.get("divergences_count", 0) or 0)
    return (
        f"Divergent transitions: {count} divergences ({100 * v:.1f}% "
        f"of draws) exceed the 5% threshold. NUTS is struggling with "
        f"the posterior geometry — posterior estimates may be biased. "
        f"Remediation: switch to Thorough preset (higher target-"
        f"accept), or re-run with the Kim-Shephard-Chib Gibbs backend "
        f"(which samples SV's awkward geometry via conjugate updates "
        f"rather than Hamiltonian dynamics)."
    )


def _trigger_mcmc_fallback_to_quasi_ml(results: dict) -> Optional[str]:
    """D7 — fires when MCMC was requested but wrapper fell back to
    quasi-ML (mcmc_fallback_occurred=True)."""
    if not bool(results.get("mcmc_fallback_occurred", False)):
        return None
    return (
        "MCMC optimization failed — the wrapper fell back to quasi-ML. "
        "Reported parameters and volatility paths are from the quasi-"
        "ML approximation, NOT from MCMC. See Tier 2 for the three "
        "possible causes (sampler divergences, library/runtime error, "
        "pathological input) and their specific remediations. The "
        "Jensen-inequality transformation bias that MCMC would have "
        "removed applies to these results."
    )


def _trigger_ppc_undercoverage(results: dict) -> Optional[str]:
    """D8 — fires when PPC 90% coverage < 0.80 (Thorough + MCMC only).

    Posterior predictive should cover ~90% of observations by
    construction if the model fits; coverage < 0.80 indicates the
    model misses important features (outliers, tail behavior).
    """
    if _inference_method_value(results) != "mcmc":
        return None
    cov = results.get("ppc_coverage_90pct")
    if cov is None:
        return None
    try:
        v = float(cov)
    except Exception:
        return None
    if v >= 0.80:
        return None
    return (
        f"Posterior predictive check flags model mis-fit: 90% PPC "
        f"band covers only {100 * v:.1f}% of observations (target "
        f"~90%). The model misses features of the data — commonly "
        f"extreme moves on heavy-tailed return series. Remediation: "
        f"switch to innovations='student_t' (if currently Gaussian) "
        f"to capture tails, or inspect for structural breaks / "
        f"regime shifts beyond the SV model's scope."
    )


def _trigger_fast_preset_mcmc_downgrade(results: dict) -> Optional[str]:
    """D9 — fires when Fast preset + MCMC auto-downgraded to quasi-ML.

    Parallel to 2c's D3 disclosure pattern; surfaces the event at
    Tier 3 for visibility (Tier 2 already carries the full sentence).
    """
    if not bool(results.get("fast_preset_mcmc_downgrade", False)):
        return None
    return (
        "MCMC requested on Fast preset — Fast cannot run MCMC. The "
        "wrapper fitted quasi-ML instead; reported parameters and "
        "volatility paths reflect the quasi-ML approximation. To "
        "perform MCMC inference, re-run on Balanced (2 chains × 2000 "
        "draws) or Thorough (4 chains × 4000 draws) preset."
    )


SPEC = InterpretationSpec(
    technique_id="stochastic_volatility",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # Existing (C6 + 2c):
        _trigger_near_integrated_volatility,
        _trigger_low_persistence,
        _trigger_gaussian_on_fat_tails,
        _trigger_student_t_very_heavy_tails,
        _trigger_near_gaussian_on_student_t_path,
        _trigger_student_t_optimization_failed_fallback,
        # Follow-up 2b (D4–D9):
        _trigger_rhat_failure,
        _trigger_low_ess,
        _trigger_divergent_transitions,
        _trigger_mcmc_fallback_to_quasi_ml,
        _trigger_ppc_undercoverage,
        _trigger_fast_preset_mcmc_downgrade,
    ),
    mode_aware=False,
)

register(SPEC)
