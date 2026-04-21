"""
InterpretationSpec for evt_pot_gpd (Peaks-Over-Threshold Generalized
Pareto Distribution).

Stand-alone Tier 1 shape — distribution-fit-with-tail-parameters.
Tier 1 leads with threshold + exceedances + ξ band + canonical VaR/ES
quantiles. Tier 2 explicitly names "Generalized Pareto Distribution
(GPD)" per Convention C and discloses POT independence assumption.

Decision D5: always-fires Tier 3 declustering caveat for time-indexed
input. Decision D6: Tier 3 triggers when 10 ≤ n_exceedances < 30.
Decision D14: wrapper's Anderson-Darling bug fixed in Phase 3 apply
(scipy.stats.anderson doesn't support dist='uniform').

Results-dict keys consumed:

    series_name / n_obs
    xi / sigma / threshold / threshold_quantile
    n_exceedances / exceedance_rate / tail
    confidence_levels / var_values / es_values
    ks_stat / ks_pval
    is_time_series_input / exceedances_below_30
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_P_VALUE,
    FMT_COEF_SIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tail_band(xi: float) -> str:
    """EVT tail-index adjective band (in-spec, mirrors wrapper
    convention at evt_pot_gpd.py:306-314)."""
    try:
        v = float(xi)
    except Exception:
        return "unknown"
    if v > 0.05:
        return "heavy-tailed (Frechet domain)"
    if v < -0.05:
        return "bounded (Weibull domain)"
    return "approximately exponential"


def _fmt_confidence(p: float) -> str:
    """Convention A: integer-when-whole, else ``:.1f``."""
    try:
        v = float(p) * 100.0
    except Exception:
        return f"{p}"
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}%"
    return f"{v:.1f}%"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    tail = str(results.get("tail", "upper")).lower()
    tail_label = "left tail" if tail == "lower" else "right tail"
    thr_q = results.get("threshold_quantile", 0.975)
    try:
        thr_q_pct = float(thr_q) * 100.0
        thr_q_str = (
            f"{int(round(thr_q_pct))}th"
            if abs(thr_q_pct - round(thr_q_pct)) < 1e-9
            else f"{thr_q_pct:.1f}th"
        )
    except Exception:
        thr_q_str = str(thr_q)

    u_val = results.get("threshold")
    thr_disp = format_scale_aware(float(u_val)) if u_val is not None else "n/a"
    # Phrasing for threshold percentile: "loss percentile" reads
    # naturally for left-tail return analysis but is awkward for
    # right-tail rate spikes or gains. Use "tail percentile" as a
    # neutral phrase; the tail_label ("left tail" / "right tail")
    # already names the direction above.
    pct_label = "tail percentile"

    n_exc = int(results.get("n_exceedances", 0))
    xi = results.get("xi")
    sigma = results.get("sigma")
    xi_str = FMT_COEF_SIGNED.format(float(xi)) if xi is not None else "n/a"
    sigma_str = format_scale_aware(float(sigma)) if sigma is not None else "n/a"
    tail_band_str = _tail_band(xi) if xi is not None else "unavailable"

    # Canonical VaR/ES citation — use the highest available confidence
    # level for the headline, and 99% for the secondary citation when
    # available.
    conf_levels = list(results.get("confidence_levels") or [])
    var_values = list(results.get("var_values") or [])
    es_values = list(results.get("es_values") or [])
    citations = []
    for lvl, vr in zip(conf_levels, var_values):
        try:
            if float(lvl) in (0.99, 0.999):
                citations.append(
                    f"{_fmt_confidence(lvl)} VaR = "
                    f"{format_scale_aware(float(vr))}%"
                )
        except Exception:
            continue
    var_clause = "; ".join(citations) if citations else "VaR quantiles in the data tables"

    es_clause = ""
    for lvl, e in zip(conf_levels, es_values):
        if e is None:
            continue
        try:
            if abs(float(lvl) - 0.99) < 1e-9:
                es_clause = (
                    f" {_fmt_confidence(lvl)} Expected Shortfall = "
                    f"{format_scale_aware(float(e))}%."
                )
                break
        except Exception:
            continue

    return (
        f"Extreme Value Theory POT fit on the {tail_label} of "
        f"{format_series_reference(name)} ({n} observations). "
        f"Threshold set at the {thr_q_str} {pct_label} "
        f"(u = {thr_disp}), yielding {n_exc} exceedances. "
        f"Generalized Pareto Distribution shape ξ = {xi_str} indicates "
        f"a {tail_band_str} tail; scale σ = {sigma_str}. "
        f"{var_clause}.{es_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    n_exc = int(results.get("n_exceedances", 0))
    try:
        exc_rate = float(results.get("exceedance_rate", 0.0)) * 100.0
    except Exception:
        exc_rate = 0.0
    xi = results.get("xi")
    sigma = results.get("sigma")
    xi_str = FMT_COEF_SIGNED.format(float(xi)) if xi is not None else "n/a"
    sigma_str = format_scale_aware(float(sigma)) if sigma is not None else "n/a"

    ks_stat = results.get("ks_stat")
    ks_pval = results.get("ks_pval")
    ks_clause = ""
    if ks_stat is not None and ks_pval is not None:
        try:
            ks_verdict = (
                "does-not-reject the GPD fit at 5%"
                if float(ks_pval) > 0.05
                else "rejects the GPD fit at 5%"
            )
            ks_clause = (
                f" Kolmogorov-Smirnov goodness-of-fit statistic = "
                f"{format_scale_aware(float(ks_stat))}, "
                f"p = {FMT_P_VALUE.format(float(ks_pval))} ({ks_verdict})."
            )
        except Exception:
            pass

    # Moment-finiteness note for heavy tails (ξ > 0): E[X^k] < ∞ only
    # for k < 1/ξ.
    moment_clause = ""
    if xi is not None:
        try:
            xi_f = float(xi)
            if xi_f > 0.05:
                inv_xi = 1.0 / xi_f
                moment_clause = (
                    f" For ξ = {xi_str} > 0, the fitted loss distribution "
                    f"has finite moments only of order less than "
                    f"1/ξ ≈ {inv_xi:.1f}; higher moments (skewness, "
                    f"kurtosis) of the raw distribution beyond this order "
                    f"are theoretically infinite and finite-sample "
                    f"estimates should be treated with caution."
                )
        except Exception:
            pass

    return (
        f"Peaks-Over-Threshold (POT) extreme-value fit via Generalized "
        f"Pareto Distribution (GPD) on excesses above the user-"
        f"specified threshold (exceedance rate {exc_rate:.2f}% of the "
        f"{n}-observation sample, {n_exc} exceedances). Fit via maximum "
        f"likelihood (scipy.stats.genpareto). Shape parameter ξ = "
        f"{xi_str}, scale σ = {sigma_str}. Tail quantiles and Expected "
        f"Shortfall values are extrapolated using the GPD tail estimator "
        f"ζ_u · F̄_ξ,σ(x − u); uncertainty is reported via 95% "
        f"percentile bootstrap confidence intervals in the data "
        f"tables.{ks_clause}{moment_clause} The wrapper assumes "
        f"exceedances are independent; for time-series data with "
        f"volatility clustering, this assumption is an idealization "
        f"— see Tier 3 caveats. No backtest is computed at the wrapper "
        f"level (honest-disclose per Convention D)."
    )


def _trigger_heavy_tail_finite_moments(results: dict) -> Optional[str]:
    xi = results.get("xi")
    if xi is None:
        return None
    try:
        v = float(xi)
    except Exception:
        return None
    if v <= 0.0:
        return None
    inv_xi = 1.0 / max(1e-9, v)
    return (
        f"Shape ξ = {FMT_COEF_SIGNED.format(v)} > 0 implies the fitted "
        f"tail is heavy-tailed (Frechet domain); moments of order ≥ "
        f"{inv_xi:.1f} are infinite in the limiting GPD. Finite-sample "
        f"estimates of higher moments (skewness, kurtosis) are "
        f"therefore unreliable indicators of the true distribution."
    )


def _trigger_n_exceedances_under_30(results: dict) -> Optional[str]:
    """D6 — bridges the wrapper's hard minimum (10) and the 30-obs
    reliable-fit rule-of-thumb."""
    below_30 = results.get("exceedances_below_30")
    if not below_30:
        return None
    n_exc = int(results.get("n_exceedances", 0))
    return (
        f"Exceedance count {n_exc} is above the wrapper's hard minimum "
        f"of 10 but below the 30-observation rule of thumb for reliable "
        f"GPD maximum-likelihood estimation. Tail-parameter standard "
        f"errors are wide; treat extreme quantiles as indicative rather "
        f"than precise. Consider lowering the threshold quantile to "
        f"include more exceedances, or obtaining a longer sample."
    )


def _trigger_declustering_timeseries(results: dict) -> Optional[str]:
    """D5 — always-fires for time-indexed input."""
    if not bool(results.get("is_time_series_input", False)):
        return None
    return (
        "POT assumes exceedances are independent. This input is a "
        "time series — volatility clusters can produce short-run "
        "exceedance runs that violate the independence assumption. "
        "For production risk measurement on clustered returns, "
        "consider a declustered POT approach (e.g., runs declustering "
        "with a fixed gap) or a block-maxima fit, which is robust to "
        "clustering within blocks."
    )


def _trigger_ks_rejects(results: dict) -> Optional[str]:
    p = results.get("ks_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Kolmogorov-Smirnov test rejects the GPD fit at the 5% level "
        f"(p = {FMT_P_VALUE.format(float(p))}). The chosen threshold "
        f"may be too low (GPD only applies asymptotically to tail "
        f"excesses); try raising the threshold quantile and re-fitting, "
        f"or inspect the mean excess function for a stable-linear "
        f"region."
    )


SPEC = InterpretationSpec(
    technique_id="evt_pot_gpd",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_heavy_tail_finite_moments,
        _trigger_n_exceedances_under_30,
        _trigger_declustering_timeseries,
        _trigger_ks_rejects,
    ),
    mode_aware=False,
)

register(SPEC)
