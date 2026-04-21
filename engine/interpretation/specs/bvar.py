"""
InterpretationSpec for bvar (Bayesian VAR with Minnesota prior).

Inherits the Prompt C1 var_model Tier 1 shape (multivariate forecasts +
series list + cross-series RMSEs). Tier 2 reframes as Bayesian —
Minnesota prior specification + credible-interval semantic label
(Decision D2) + honest disclosure that this wrapper does not emit
IRF/FEVD (Decision D15 cross-spec pointer).

Results-dict keys consumed:

    variables / n_variables / lags
    lambda1 / lambda2 / lambda3
    n_effective / n_draws / total_params
    bic_approx
    rmse                      : dict {series_name -> float}
    horizon
    prior_tightness_band      : "tight" | "moderate" | "loose"
    credible_interval_coverage: float (e.g. 0.90)
    interval_type             : "credible"
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    FMT_COEF_UNSIGNED,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _format_lambda(val, default=""):
    if val is None:
        return default
    try:
        return FMT_COEF_UNSIGNED.format(float(val))
    except Exception:
        return default


def _rmse_clauses(results: dict) -> str:
    rmse = results.get("rmse") or {}
    if not isinstance(rmse, dict) or not rmse:
        return "Per-variable fit RMSEs not reported."
    parts = []
    for name in sorted(rmse.keys()):
        val = rmse[name]
        if val is None:
            continue
        try:
            parts.append(f"{name} {format_scale_aware(float(val))}")
        except Exception:
            continue
    if not parts:
        return "Per-variable fit RMSEs not reported."
    return "Per-variable fit RMSEs: " + ", ".join(parts) + "."


def _tier1(results: dict) -> str:
    names = list(results.get("variables") or [])
    k = int(results.get("n_variables", len(names)))
    p = int(results.get("lags", 0))
    n_eff = int(results.get("n_effective", 0))
    horizon = int(results.get("horizon", 0))
    n_draws = int(results.get("n_draws", 0) or 0)
    coverage = results.get("credible_interval_coverage", 0.90)
    try:
        coverage_pct = int(round(float(coverage) * 100))
    except Exception:
        coverage_pct = 90
    lam1 = results.get("lambda1")
    tightness_band = str(results.get("prior_tightness_band", "moderate"))

    names_quoted = ", ".join(f"'{n}'" for n in names) if names else f"{k} series"
    lam1_str = _format_lambda(lam1, "unavailable")

    rmse_clause = _rmse_clauses(results)

    # Decision D15 — cross-spec pointer to frequentist var_model
    cross_spec_pointer = (
        f" Unlike the frequentist var_model technique, this run does not "
        f"emit impulse-response functions or forecast-error-variance "
        f"decomposition — see Tier 2 for the Bayesian-specific disclosure."
    )

    draws_clause = (
        f" {horizon}-step posterior-mean forecasts with {coverage_pct}% "
        f"credible intervals from {n_draws} posterior draws."
    ) if n_draws > 0 else (
        f" {horizon}-step posterior-mean forecasts with {coverage_pct}% "
        f"credible intervals."
    )

    return (
        f"Bayesian VAR({p}) on {k} variables ({names_quoted}) with "
        f"{n_eff} effective observations under a Minnesota prior "
        f"(tightness λ1={lam1_str}, {tightness_band})."
        f" {rmse_clause}{draws_clause}"
        f"{cross_spec_pointer}"
    )


def _tier2(results: dict) -> str:
    k = int(results.get("n_variables", 0))
    p = int(results.get("lags", 0))
    lam1 = _format_lambda(results.get("lambda1"), "unavailable")
    lam2 = _format_lambda(results.get("lambda2"), "unavailable")
    lam3 = _format_lambda(results.get("lambda3"), "unavailable")
    tightness_band = str(results.get("prior_tightness_band", "moderate"))
    n_draws = int(results.get("n_draws", 0) or 0)
    coverage = results.get("credible_interval_coverage", 0.90)
    try:
        coverage_pct = int(round(float(coverage) * 100))
    except Exception:
        coverage_pct = 90
    total_params = results.get("total_params")
    total_params_str = str(total_params) if total_params is not None else "not reported"
    bic = results.get("bic_approx")
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"

    # Decision D2 — credible-vs-confidence semantic disclosure
    credible_sentence = (
        f"Reported intervals are {coverage_pct}% Bayesian credible intervals "
        f"from the posterior distribution, not frequentist confidence intervals "
        f"— they answer 'what is the probability the parameter lies in this "
        f"range given the data and prior' rather than 'what fraction of "
        f"resampled intervals would contain the true parameter under repeated "
        f"sampling.'"
    )

    return (
        f"Bayesian VAR with Minnesota (Litterman) prior and analytical "
        f"Normal-Inverse-Wishart posterior (no MCMC). Hyperparameters: "
        f"λ1={lam1} (overall tightness — {tightness_band} shrinkage toward "
        f"a random-walk prior), λ2={lam2} (cross-equation scaling), "
        f"λ3={lam3} (lag decay rate). Posterior means and standard errors "
        f"computed equation-by-equation; {n_draws} Monte Carlo posterior "
        f"draws generate the {coverage_pct}% credible intervals for the "
        f"forecast paths. {credible_sentence} BIC approximation {bic_str} "
        f"on {total_params_str} total parameters. Impulse-response functions "
        f"and forecast-error-variance decomposition are not emitted by this "
        f"wrapper (unlike var_model); if causal structure is needed, refit "
        f"with the frequentist var_model spec."
    )


def _trigger_tight_prior_extreme(results: dict) -> Optional[str]:
    lam1 = results.get("lambda1")
    if lam1 is None:
        return None
    try:
        v = float(lam1)
    except Exception:
        return None
    if v >= 0.05:
        return None
    return (
        f"Prior tightness λ1={v:.3f} is very tight (below 0.05). The posterior "
        f"mean is shrunk strongly toward the random-walk prior, so per-series "
        f"forecasts will mirror simple RW-forecasts; increase λ1 if data-driven "
        f"cross-equation dynamics matter for this application."
    )


def _trigger_loose_prior_extreme(results: dict) -> Optional[str]:
    lam1 = results.get("lambda1")
    if lam1 is None:
        return None
    try:
        v = float(lam1)
    except Exception:
        return None
    if v <= 0.5:
        return None
    return (
        f"Prior tightness λ1={v:.3f} is loose (above 0.5). The posterior is "
        f"closer to the OLS (frequentist) estimate with little shrinkage; "
        f"Bayesian regularization benefits are muted on this run."
    )


def _trigger_parameter_blowup(results: dict) -> Optional[str]:
    total = results.get("total_params")
    n_eff = results.get("n_effective")
    if total is None or n_eff is None:
        return None
    try:
        tot = int(total)
        n = int(n_eff)
    except Exception:
        return None
    if n <= 0 or tot <= 0.2 * n:
        return None
    return (
        f"Total parameters {tot} exceed 20% of effective observations "
        f"{n}; even with Minnesota shrinkage the fit is data-hungry. "
        f"Consider reducing lags or tightening λ1 if credible intervals "
        f"appear implausibly wide."
    )


SPEC = InterpretationSpec(
    technique_id="bvar",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_tight_prior_extreme,
        _trigger_loose_prior_extreme,
        _trigger_parameter_blowup,
    ),
    mode_aware=False,
)

register(SPEC)
