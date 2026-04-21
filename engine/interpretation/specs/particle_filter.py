"""
InterpretationSpec for particle_filter (Sequential Monte Carlo).

Distinct Tier 1 framing (per Prompt C3 Decision 4): SMC-centric
rather than forecast-trajectory-centric. Tier 1 centers on particle
count, ESS utilization adjective (efficient / moderate / degenerate),
resampling event rate, and log-likelihood approximation.

In-spec ESS adjective bands per Decision 3.
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


# ESS utilization adjective bands (avg_ess / n_particles). Decision 3.
# TODO: promote to a shared helper if a second distinct spec needs the
# same ratio-based banding logic for resampling-based methods.
ESS_DEGENERATE_MAX = 0.1
ESS_MODERATE_MAX = 0.5


def _ess_band(avg_ess, n_particles):
    if avg_ess is None or n_particles is None or float(n_particles) <= 0:
        return None
    ratio = float(avg_ess) / float(n_particles)
    if ratio < ESS_DEGENERATE_MAX:
        return "degenerate"
    if ratio < ESS_MODERATE_MAX:
        return "moderate"
    return "efficient"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    model_type = str(results.get("model_type", "state-space"))
    n_particles = int(results.get("n_particles", 0))
    avg_ess = results.get("avg_ess")
    min_ess = results.get("min_ess")
    n_resamples = int(results.get("n_resamples", 0))
    log_likelihood = results.get("log_likelihood")
    band = _ess_band(avg_ess, n_particles)

    ess_pct = (100.0 * float(avg_ess) / float(n_particles)
               if (avg_ess is not None and n_particles > 0) else 0.0)
    resample_pct = (100.0 * n_resamples / n) if n > 0 else 0.0
    ll_str = format_scale_aware(float(log_likelihood)) if log_likelihood is not None else "not reported"
    min_ess_clause = ""
    if min_ess is not None and float(min_ess) < 10:
        min_ess_clause = (
            f" The SMC approximation is stable in average but carries a "
            f"degenerate tail — minimum ESS dropped to {int(float(min_ess))} "
            f"particle{'s' if int(float(min_ess)) != 1 else ''} at its "
            f"worst, indicating weight collapse in isolated steps."
        )
    return (
        f"Bootstrap particle filter ({model_type} state-space model) "
        f"applied to {format_series_reference(name)} ({n} observations) "
        f"with {n_particles} particles over a {horizon}-step forecast "
        f"horizon. Average effective sample size "
        f"{int(float(avg_ess)) if avg_ess is not None else 0} "
        f"({ess_pct:.0f}% of particles effective — {band or 'unknown'}); "
        f"{n_resamples} resampling events across the sample "
        f"({resample_pct:.0f}% of steps triggered resampling). "
        f"Log-likelihood approximation {ll_str}.{min_ess_clause}"
    )


def _tier2(results: dict) -> str:
    n_particles = int(results.get("n_particles", 0))
    sigma_state = results.get("sigma_state")
    sigma_obs = results.get("sigma_obs")
    model_type = str(results.get("model_type", "state-space"))
    resample_thresh = results.get("resample_threshold", 0.5)
    ss_str = format_scale_aware(float(sigma_state)) if sigma_state is not None else "not reported"
    so_str = format_scale_aware(float(sigma_obs)) if sigma_obs is not None else "not reported"
    return (
        f"Sequential Monte Carlo via bootstrap sequential importance "
        f"resampling (SIR) with systematic resampling when ESS/N falls "
        f"below {FMT_COEF_UNSIGNED.format(float(resample_thresh))}. "
        f"Fit {n_particles} particles against a {model_type} state-space "
        f"model: state disturbance σ_state = {ss_str}, observation "
        f"noise σ_obs = {so_str}. The log-likelihood approximation is "
        f"an empirical accumulation of per-step marginal likelihoods, "
        f"so it is stochastic: running with a different seed will "
        f"produce a different value. The wrapper supports four "
        f"built-in model types (local_level, local_level_sv, "
        f"nonlinear_growth, random_walk_sv); user-supplied nonlinear "
        f"transitions are not injected. Forecast is a posterior-"
        f"predictive sample path propagated forward; 90% credible "
        f"bands are empirical quantiles (Q5, Q95) across the particle "
        f"population at each forecast step."
    )


def _trigger_ess_degeneracy(results: dict) -> Optional[str]:
    """Fires when the minimum ESS across the trajectory fell below 10
    particles, indicating weight collapse in one or more steps."""
    min_ess = results.get("min_ess")
    if min_ess is None or float(min_ess) >= 10:
        return None
    return (
        f"Minimum effective sample size dropped to "
        f"{int(float(min_ess))} particle{'s' if int(float(min_ess)) != 1 else ''}, "
        f"indicating weight collapse at one or more steps. SMC "
        f"approximation is unreliable for the affected steps; consider "
        f"increasing particle count (Balanced or Thorough preset) or "
        f"adjusting σ_state / σ_obs to reduce the likelihood variance "
        f"contribution."
    )


def _trigger_high_resampling_rate(results: dict) -> Optional[str]:
    """Fires when resampling occurs on more than 50% of steps —
    indicates persistent degeneracy pressure even if average ESS is
    acceptable."""
    n_resamples = results.get("n_resamples")
    n_obs = results.get("n_obs")
    if n_resamples is None or n_obs is None:
        return None
    n_obs_i = int(n_obs)
    if n_obs_i <= 0:
        return None
    if int(n_resamples) / n_obs_i <= 0.5:
        return None
    return (
        f"Resampling triggered on {int(n_resamples)} of {n_obs_i} steps "
        f"({100.0 * int(n_resamples) / n_obs_i:.0f}%); the SMC "
        f"approximation spends most of its budget on resampling rather "
        f"than sequential update. Consider increasing n_particles or "
        f"adjusting σ_state / σ_obs."
    )


def _trigger_degenerate_avg_ess(results: dict) -> Optional[str]:
    """Fires when the average ESS-to-particle ratio is in the
    'degenerate' band (< 0.1). Means the filter is persistently
    weight-degenerate, not just in isolated steps."""
    avg_ess = results.get("avg_ess")
    n_particles = results.get("n_particles")
    band = _ess_band(avg_ess, n_particles)
    if band != "degenerate":
        return None
    ratio = float(avg_ess) / float(n_particles)
    return (
        f"Average ESS/N ratio = {ratio:.2f} sits in the 'degenerate' "
        f"band (< {ESS_DEGENERATE_MAX}); particles are persistently "
        f"weight-degenerate across the sample. The filter's posterior "
        f"approximation is unreliable — increase particle count or "
        f"reconsider the model specification."
    )


SPEC = InterpretationSpec(
    technique_id="particle_filter",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_ess_degeneracy,
        _trigger_degenerate_avg_ess,
        _trigger_high_resampling_rate,
    ),
    mode_aware=False,
)

register(SPEC)
