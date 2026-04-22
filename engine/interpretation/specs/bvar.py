"""
InterpretationSpec for bvar (Bayesian VAR with Minnesota prior).

Inherits the Prompt C1 var_model Tier 1 shape (multivariate forecasts +
series list + cross-series RMSEs). Tier 2 reframes as Bayesian —
Minnesota prior specification + credible-interval semantic label
(Decision D2).

Follow-up 1c added IRF/FEVD capability: the C5 "does not emit IRF/FEVD"
honest disclosure now conditions on ``irf_fevd_computed``:
  - When True, Tier 1 cross-spec pointer is removed and Tier 2
    discloses Cholesky identification, ordering sensitivity,
    FEVD breakdown at the longest horizon, and the Σ point-estimate
    simplification.
  - When False (Fast preset default, or user disabled), Tier 2
    discloses the skip reason and how to enable.

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
    # Follow-up 1c fields:
    irf_fevd_computed         : bool
    identification_scheme     : "cholesky" | None
    variable_ordering         : list[str] | None
    irf_horizon               : int | None
    fevd_horizons             : list[int]
    own_shock_share_longest_horizon : dict[var -> share (0..1)]
    fevd_longest_horizon      : int | None
    zero_straddle_pairs       : list[dict]  (D1 trigger input)
    irf_skip_reason           : "fast_preset_default" | "user_disabled"
                                | "computation_error: ..." | None
    sigma_posterior_uncertainty_propagated : bool (R1 disclosure flag)
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

    # Follow-up 1c — Tier 1 closer conditions on irf_fevd_computed.
    # When computed: point readers to Tier 2 for the structural analysis.
    # When not computed: keep a softer cross-spec pointer indicating
    # IRF/FEVD are available by re-running on Balanced / Thorough.
    irf_fevd_computed = bool(results.get("irf_fevd_computed", False))
    if irf_fevd_computed:
        structural_closer = (
            " Impulse-response functions and forecast-error-variance "
            "decomposition are computed under Cholesky identification "
            "— see Tier 2 for the structural analysis."
        )
    else:
        structural_closer = (
            " Impulse-response functions and forecast-error-variance "
            "decomposition are not computed on this run (see Tier 2 "
            "for the skip reason); Balanced / Thorough preset enables "
            "them by default."
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
        f"{structural_closer}"
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

    # Follow-up 1c — structural analysis block conditions on
    # irf_fevd_computed.
    irf_fevd_computed = bool(results.get("irf_fevd_computed", False))
    if irf_fevd_computed:
        ordering = list(results.get("variable_ordering") or [])
        irf_horizon_val = results.get("irf_horizon")
        fevd_horizons_val = list(results.get("fevd_horizons") or [])
        fevd_longest = results.get("fevd_longest_horizon")
        own_shares = results.get("own_shock_share_longest_horizon") or {}

        # Ordering-effect explanation
        if len(ordering) >= 2:
            first = ordering[0]
            last_vars = ordering[1:]
            if len(last_vars) == 1:
                order_note = (
                    f"'{first}' shocks can affect '{last_vars[0]}' "
                    f"contemporaneously, but not vice versa."
                )
            else:
                order_note = (
                    f"'{first}' shocks can affect '{', '.join(last_vars)}' "
                    f"contemporaneously, '{ordering[1]}' shocks affect "
                    f"'{', '.join(ordering[2:])}' contemporaneously but "
                    f"not '{first}', and so on down the ordering."
                )
        else:
            order_note = ""

        # FEVD own-shock breakdown (R3: one-decimal formatting)
        if own_shares and fevd_longest is not None:
            parts = []
            for var_name in ordering:
                share = own_shares.get(var_name)
                if share is not None:
                    try:
                        parts.append(
                            f"'{var_name}'s own shocks account for "
                            f"{float(share) * 100:.1f}% of its forecast-"
                            f"error variance"
                        )
                    except Exception:
                        continue
            if parts:
                fevd_sentence = (
                    f" Forecast-error-variance decomposition at horizons "
                    f"{fevd_horizons_val}. At the {fevd_longest}-period "
                    f"horizon, " + "; ".join(parts)
                    + ". The FEVD data table gives the full breakdown "
                    "with 90% credible bands."
                )
            else:
                fevd_sentence = (
                    f" Forecast-error-variance decomposition at horizons "
                    f"{fevd_horizons_val}; see the FEVD data table for "
                    f"the full breakdown."
                )
        else:
            fevd_sentence = ""

        # R1 — Σ point-estimate disclosure
        sigma_note = (
            " Credible bands reflect posterior uncertainty in VAR "
            "coefficient draws; innovation covariance Σ is held at its "
            "posterior point estimate (a common simplification that "
            "keeps computational cost bounded). For fuller posterior "
            "propagation including Σ uncertainty, refit with MCMC-"
            "based BVAR (not yet available in TSL)."
        )

        structural_block = (
            f" **Structural analysis (IRF and FEVD)**: posterior "
            f"impulse-response functions computed under Cholesky "
            f"identification with ordering "
            f"[{', '.join(ordering)}] over {irf_horizon_val} periods. "
            f"The ordering reflects an economic-theory assumption: "
            f"{order_note} Reported IRF is the posterior median; 90% "
            f"credible bands are in the Impulse Response data table."
            f"{fevd_sentence}{sigma_note}"
        )
    else:
        skip = str(results.get("irf_skip_reason") or "")
        if skip == "fast_preset_default":
            skip_msg = (
                "Impulse-response functions and forecast-error-variance "
                "decomposition were skipped on the Fast preset for speed. "
                "Switch to Balanced or Thorough preset, or pass "
                "compute_irf_fevd=True in params, to enable posterior "
                "structural analysis."
            )
        elif skip == "user_disabled":
            skip_msg = (
                "Impulse-response functions and forecast-error-variance "
                "decomposition were disabled by the caller "
                "(compute_irf_fevd=False). Pass compute_irf_fevd=True "
                "to enable."
            )
        elif skip.startswith("computation_error"):
            skip_msg = (
                f"IRF/FEVD computation failed ({skip}); the fit itself "
                f"succeeded but structural analysis was skipped. Check "
                f"the warning log for details; re-running may succeed."
            )
        else:
            skip_msg = (
                "Impulse-response functions and forecast-error-variance "
                "decomposition are not computed on this run. Enable "
                "with Balanced / Thorough preset or compute_irf_fevd=True."
            )
        structural_block = f" **Structural analysis**: {skip_msg}"

    return (
        f"Bayesian VAR with Minnesota (Litterman) prior and analytical "
        f"Normal-Inverse-Wishart posterior (no MCMC). Hyperparameters: "
        f"λ1={lam1} (overall tightness — {tightness_band} shrinkage toward "
        f"a random-walk prior), λ2={lam2} (cross-equation scaling), "
        f"λ3={lam3} (lag decay rate). Posterior means and standard errors "
        f"computed equation-by-equation; {n_draws} Monte Carlo posterior "
        f"draws generate the {coverage_pct}% credible intervals for the "
        f"forecast paths. {credible_sentence} BIC approximation {bic_str} "
        f"on {total_params_str} total parameters."
        f"{structural_block}"
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


def _trigger_irf_credible_bands_straddle_zero(results: dict) -> Optional[str]:
    """Follow-up 1c D1 — fires when any cross-variable shock-response
    pair has a 90% credible band straddling zero at the peak IRF lag
    AND the median effect exceeds the R2 magnitude-threshold filter
    applied in the wrapper (so this only fires on "uncertain non-
    trivial effects", not "essentially null effects")."""
    pairs = results.get("zero_straddle_pairs") or []
    if not pairs:
        return None
    n_pairs = len(pairs)
    example_parts = []
    for p in pairs[:3]:
        try:
            example_parts.append(
                f"'{p.get('shock')}' → '{p.get('response')}' "
                f"(peak at horizon {p.get('peak_horizon')})"
            )
        except Exception:
            continue
    more_clause = (
        f", and {n_pairs - 3} more" if n_pairs > 3 else ""
    )
    return (
        f"{n_pairs} cross-variable shock-response pair"
        f"{'s' if n_pairs != 1 else ''} have a 90% credible band "
        f"straddling zero at the peak IRF lag: "
        + ", ".join(example_parts)
        + more_clause
        + ". These structural effects are not statistically "
        "distinguishable from no response under the posterior. "
        "Draw conclusions about these channels cautiously."
    )


def _trigger_cholesky_ordering_sensitivity(results: dict) -> Optional[str]:
    """Follow-up 1c D2 — always-fires when IRF/FEVD was computed,
    reminding the reader that Cholesky identification is ordering-
    dependent. Silent when IRF/FEVD was skipped."""
    if not results.get("irf_fevd_computed"):
        return None
    ordering = list(results.get("variable_ordering") or [])
    if not ordering:
        return None
    return (
        f"Cholesky identification imposes a recursive ordering: "
        f"{', '.join(ordering)}. Results are sensitive to the "
        f"variable order — rearranging these series will change "
        f"IRF and FEVD interpretation. The ordering reflects an "
        f"economic-theory assumption that earlier variables' shocks "
        f"can contemporaneously affect later variables, but not "
        f"vice versa. For robust structural analysis, compare "
        f"results across multiple plausible orderings."
    )


SPEC = InterpretationSpec(
    technique_id="bvar",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_tight_prior_extreme,
        _trigger_loose_prior_extreme,
        _trigger_parameter_blowup,
        _trigger_irf_credible_bands_straddle_zero,
        _trigger_cholesky_ordering_sensitivity,
    ),
    mode_aware=False,
)

register(SPEC)
