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

Follow-up 3c: opt-in `decluster=True` applies Ferro-Segers 2003
intervals declustering. Tier 1 gains a closer (θ, K, 99% VaR bias
correction); Tier 2 gains an always-on mean residual life (MRL)
diagnostic, plus a conditional declustering methodology block and
fallback-disclosure block. Legacy D5 `_trigger_declustering_
timeseries` is re-gated to suppress when the user opts in (it now
points at `decluster=True` as the actionable option). Five new
Tier 3 triggers (D1-D5) cover severity, reduction-ratio,
few-peaks, material-bias-correction, and graceful fallback.

Results-dict keys consumed:

    series_name / n_obs
    xi / sigma / threshold / threshold_quantile
    n_exceedances / exceedance_rate / tail
    confidence_levels / var_values / es_values
    ks_stat / ks_pval
    is_time_series_input / exceedances_below_30
    # Follow-up 3c
    decluster_requested / decluster_applied / decluster_fallback_reason
    extremal_index_theta / extremal_index_method
    n_clusters_post_decluster / decluster_reduction_ratio
    xi_post_decluster / sigma_post_decluster
    ks_stat_post_decluster / ks_pval_post_decluster
    var_values_post_decluster / es_values_post_decluster
    var_bias_correction_at_99pct / var_bias_correction_pct_at_99pct
    mean_excess_at_threshold / mean_excess_implied_by_gpd
    mean_excess_match_verdict
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

    base_tier1 = (
        f"Extreme Value Theory POT fit on the {tail_label} of "
        f"{format_series_reference(name)} ({n} observations). "
        f"Threshold set at the {thr_q_str} {pct_label} "
        f"(u = {thr_disp}), yielding {n_exc} exceedances. "
        f"Generalized Pareto Distribution shape ξ = {xi_str} indicates "
        f"a {tail_band_str} tail; scale σ = {sigma_str}. "
        f"{var_clause}.{es_clause}"
    )

    # Follow-up 3c: declustering closer when user opted in and
    # declustering was applied successfully.
    if bool(results.get("decluster_applied", False)):
        theta = results.get("extremal_index_theta")
        K = results.get("n_clusters_post_decluster")
        nu_pre = int(results.get("n_exceedances", 0))
        var_post_99 = None
        var_pre_99 = None
        bias_pct = results.get("var_bias_correction_pct_at_99pct")
        var_post_list = list(results.get("var_values_post_decluster") or [])
        for i, p in enumerate(conf_levels):
            try:
                if abs(float(p) - 0.99) < 1e-9:
                    if i < len(var_values):
                        var_pre_99 = float(var_values[i])
                    if i < len(var_post_list):
                        var_post_99 = float(var_post_list[i])
                    break
            except Exception:
                continue
        if theta is not None and K is not None:
            bias_clause = ""
            if (
                var_pre_99 is not None
                and var_post_99 is not None
                and bias_pct is not None
            ):
                try:
                    bias_clause = (
                        f" Post-declustering 99% VaR "
                        f"{format_scale_aware(var_post_99)} vs pre-"
                        f"declustering {format_scale_aware(var_pre_99)} "
                        f"({float(bias_pct):+.1%} correction)."
                    )
                except Exception:
                    bias_clause = ""
            try:
                theta_f = float(theta)
                K_i = int(K)
                base_tier1 = base_tier1 + (
                    f" Extremal index θ = {theta_f:.3f} ({nu_pre} "
                    f"exceedances reduced to {K_i} cluster peaks via "
                    f"Ferro-Segers 2003 intervals).{bias_clause}"
                )
            except Exception:
                pass

    return base_tier1


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

    # Follow-up 3c, D14: always-on mean residual life (MRL) diagnostic
    # at the chosen threshold. Positioned after moment_clause, before
    # the independence disclaimer.
    mrl_clause = ""
    e_emp = results.get("mean_excess_at_threshold")
    e_imp = results.get("mean_excess_implied_by_gpd")
    mrl_verdict = results.get("mean_excess_match_verdict")
    if e_emp is not None:
        try:
            e_emp_f = float(e_emp)
            if e_imp is not None:
                try:
                    e_imp_f = float(e_imp)
                    verdict_txt = (
                        str(mrl_verdict) if mrl_verdict is not None else ""
                    )
                    mrl_clause = (
                        f" Mean residual life diagnostic at the chosen "
                        f"threshold: empirical e(u) = "
                        f"{format_scale_aware(e_emp_f)}; GPD-implied "
                        f"(σ + ξu)/(1 − ξ) = "
                        f"{format_scale_aware(e_imp_f)}"
                        + (f"; {verdict_txt}" if verdict_txt else "")
                        + "."
                    )
                except Exception:
                    verdict_txt = (
                        str(mrl_verdict) if mrl_verdict is not None else ""
                    )
                    mrl_clause = (
                        f" Mean residual life at the chosen threshold: "
                        f"empirical e(u) = "
                        f"{format_scale_aware(e_emp_f)}"
                        + (f"; {verdict_txt}" if verdict_txt else "")
                        + "."
                    )
            else:
                verdict_txt = (
                    str(mrl_verdict) if mrl_verdict is not None else ""
                )
                mrl_clause = (
                    f" Mean residual life at the chosen threshold: "
                    f"empirical e(u) = "
                    f"{format_scale_aware(e_emp_f)}"
                    + (f"; {verdict_txt}" if verdict_txt else "")
                    + "."
                )
        except Exception:
            pass

    # Follow-up 3c: declustering methodology block when the cascade
    # applied successfully.
    decl_clause = ""
    if bool(results.get("decluster_applied", False)):
        try:
            theta = results.get("extremal_index_theta")
            K = results.get("n_clusters_post_decluster")
            xi_post = results.get("xi_post_decluster")
            sigma_post = results.get("sigma_post_decluster")
            bias_pct = results.get("var_bias_correction_pct_at_99pct")
            method = str(
                results.get("extremal_index_method") or "ferro_segers_2003"
            )
            theta_f = float(theta) if theta is not None else None
            K_i = int(K) if K is not None else None
            severity = (
                "severe"
                if theta_f is not None and theta_f < 0.3
                else "notable"
                if theta_f is not None and theta_f < 0.7
                else "mild"
            )
            xi_post_str = (
                FMT_COEF_SIGNED.format(float(xi_post))
                if xi_post is not None
                else "n/a"
            )
            sigma_post_str = (
                format_scale_aware(float(sigma_post))
                if sigma_post is not None
                else "n/a"
            )
            n_total = int(results.get("n_obs", 1)) or 1
            zeta_u_post = (
                float(K_i) / float(n_total)
                if K_i is not None and n_total > 0
                else None
            )
            zeta_u_str = (
                f"{zeta_u_post:.4f}" if zeta_u_post is not None else "n/a"
            )
            bias_str = (
                f"{float(bias_pct):+.1%}" if bias_pct is not None else "n/a"
            )
            theta_str = (
                f"{theta_f:.3f}" if theta_f is not None else "n/a"
            )
            nu_pre = int(results.get("n_exceedances", 0))
            decl_clause = (
                f" Declustering: Ferro-Segers 2003 intervals estimator "
                f"applied ({method}). Extremal index θ = {theta_str} "
                f"indicates {severity} clustering. Pre-fit exceedance "
                f"count {nu_pre} reduced to {K_i} cluster peaks via "
                f"intervals-method cluster identification (K-1 largest "
                f"inter-exceedance gaps). GPD re-fit on cluster peaks "
                f"yields ξ = {xi_post_str}, σ = {sigma_post_str} with "
                f"ζ_u = K/n = {zeta_u_str} (cluster-peak rate; "
                f"Coles 2001) driving the post-declustering tail "
                f"estimator. 99% VaR bias correction: {bias_str}."
            )
        except Exception:
            decl_clause = ""

    # Follow-up 3c: fallback disclosure block when user requested
    # declustering but the cascade declined (insufficient exceedances
    # or runtime error).
    fallback_clause = ""
    if (
        bool(results.get("decluster_requested", False))
        and not bool(results.get("decluster_applied", False))
    ):
        reason = str(results.get("decluster_fallback_reason") or "")
        if reason == "insufficient_exceedances":
            fallback_clause = (
                f" Declustering was requested but only "
                f"{int(results.get('n_exceedances', 0))} exceedances are "
                f"above threshold — Ferro-Segers intervals estimator is "
                f"unreliable below 10 exceedances. Reverted to pre-"
                f"declustering GPD fit; consider lowering "
                f"threshold_quantile to admit more exceedances."
            )
        elif reason.startswith("runtime_error"):
            fallback_clause = (
                f" Declustering was requested but raised an unexpected "
                f"runtime error ({reason}). Reverted to pre-declustering "
                f"GPD fit."
            )

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
        f"tables.{ks_clause}{moment_clause}{mrl_clause} The wrapper "
        f"assumes exceedances are independent; for time-series data "
        f"with volatility clustering, this assumption is an "
        f"idealization — see Tier 3 caveats.{decl_clause}"
        f"{fallback_clause} No backtest is computed at the wrapper "
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
    """D5 (legacy, C6) — fires only on the `decluster=False` path for
    time-series input. Text now points at the actionable
    `decluster=True` option (Follow-up 3c)."""
    # Suppressed when the user has opted in — the dedicated
    # declustering methodology block in Tier 2 plus the Declustering
    # Summary output table already deliver the message.
    if bool(results.get("decluster_requested", False)):
        return None
    if not bool(results.get("is_time_series_input", False)):
        return None
    return (
        "POT assumes exceedances are independent. This input is a "
        "time series — volatility clusters can produce short-run "
        "exceedance runs that violate the independence assumption "
        "and understate tail risk at 99% / 99.5% VaR. Set "
        "decluster=True to apply Ferro-Segers 2003 intervals "
        "declustering — the wrapper will identify independent "
        "cluster peaks before GPD fitting and report the VaR bias "
        "correction explicitly. Alternatively, a block-maxima "
        "(GEV) fit is robust to clustering within blocks."
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


# ── Follow-up 3c Tier 3 triggers (D1-D5) ───────────────────────────


def _trigger_extremal_index_clustering_severe(
    results: dict,
) -> Optional[str]:
    """D1 (3c) — fires when θ < 0.3 on the decluster-applied path."""
    theta = results.get("extremal_index_theta")
    if theta is None or not bool(results.get("decluster_applied", False)):
        return None
    try:
        v = float(theta)
    except Exception:
        return None
    if v >= 0.3:
        return None
    return (
        f"Extremal index θ = {v:.3f} indicates severe clustering: "
        f"under 30% of exceedances are statistically independent. "
        f"Pre-declustering tail estimates substantially understate "
        f"true tail risk on this sample; use the post-declustering "
        f"VaR / ES values (see Declustering Summary table) for risk "
        f"reporting."
    )


def _trigger_decluster_reduction_extreme(
    results: dict,
) -> Optional[str]:
    """D2 (3c) — fires when K / N_u < 0.3 (more than 70% redundant)."""
    ratio = results.get("decluster_reduction_ratio")
    K = results.get("n_clusters_post_decluster")
    if (
        ratio is None
        or K is None
        or not bool(results.get("decluster_applied", False))
    ):
        return None
    try:
        r = float(ratio)
    except Exception:
        return None
    if r >= 0.3:
        return None
    return (
        f"More than 70% of exceedances were redundant cluster members "
        f"(K = {int(K)} cluster peaks from "
        f"{int(results.get('n_exceedances', 0))} exceedances; reduction "
        f"ratio = {r:.3f}). The declustered sample is small for GPD "
        f"MLE; consider lowering threshold_quantile to admit more "
        f"exceedances, giving more cluster peaks downstream."
    )


def _trigger_few_cluster_peaks_for_fit(
    results: dict,
) -> Optional[str]:
    """D3 (3c) — fires when K < 30 (rule of thumb for GPD MLE)."""
    K = results.get("n_clusters_post_decluster")
    if K is None or not bool(results.get("decluster_applied", False)):
        return None
    try:
        k_i = int(K)
    except Exception:
        return None
    if k_i >= 30:
        return None
    return (
        f"Only {k_i} cluster peaks retained after declustering — below "
        f"the 30-observation rule of thumb for reliable GPD MLE. "
        f"Tail-parameter standard errors are wide; consider lowering "
        f"threshold_quantile to admit more exceedances, or switching "
        f"to a block-maxima (GEV) fit."
    )


def _trigger_var_bias_correction_material(
    results: dict,
) -> Optional[str]:
    """D4 (3c) — fires when |correction / pre| > 20% at 99% VaR."""
    pct = results.get("var_bias_correction_pct_at_99pct")
    if pct is None or not bool(results.get("decluster_applied", False)):
        return None
    try:
        p = float(pct)
    except Exception:
        return None
    if abs(p) < 0.20:
        return None
    return (
        f"Pre-vs-post declustering 99% VaR differs by {p:+.1%}. "
        f"Material bias correction — practitioner rule of thumb is "
        f"> 20% deviation. Users reporting regulatory or risk-"
        f"management VaR should use the post-declustering estimate "
        f"from the Declustering Summary table."
    )


def _trigger_insufficient_exceedances_for_declustering(
    results: dict,
) -> Optional[str]:
    """D5 (3c new) — fires when declustering was requested but fell
    back due to insufficient exceedances or a runtime error."""
    if not bool(results.get("decluster_requested", False)):
        return None
    if bool(results.get("decluster_applied", False)):
        return None
    reason = str(results.get("decluster_fallback_reason") or "")
    if reason == "insufficient_exceedances":
        try:
            thr_q_f = float(results.get("threshold_quantile", 0.975))
            thr_q_disp = f"{thr_q_f:.3f}"
        except Exception:
            thr_q_disp = str(results.get("threshold_quantile", "0.975"))
        return (
            f"Declustering was requested but only "
            f"{int(results.get('n_exceedances', 0))} exceedances above "
            f"threshold — Ferro-Segers intervals estimator is unreliable "
            f"below 10 exceedances. Reverted to pre-declustering GPD "
            f"fit. Consider lowering threshold_quantile from the "
            f"current {thr_q_disp} to admit more exceedances."
        )
    if reason.startswith("runtime_error"):
        return (
            f"Declustering was requested but raised an unexpected "
            f"runtime error ({reason}). Reverted to pre-declustering "
            f"GPD fit. Please report a reproducible example; the "
            f"baseline POT/GPD output is the pre-declustering fit."
        )
    return None


SPEC = InterpretationSpec(
    technique_id="evt_pot_gpd",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # C6 legacy triggers
        _trigger_heavy_tail_finite_moments,
        _trigger_n_exceedances_under_30,
        _trigger_declustering_timeseries,  # re-gated per Q2
        _trigger_ks_rejects,
        # Follow-up 3c D1-D5
        _trigger_extremal_index_clustering_severe,
        _trigger_decluster_reduction_extreme,
        _trigger_few_cluster_peaks_for_fit,
        _trigger_var_bias_correction_material,
        _trigger_insufficient_exceedances_for_declustering,
    ),
    mode_aware=False,
)

register(SPEC)
