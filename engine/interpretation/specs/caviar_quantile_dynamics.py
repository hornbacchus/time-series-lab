"""
InterpretationSpec for caviar_quantile_dynamics (Conditional
Autoregressive Value-at-Risk — Engle & Manganelli 2004).

Stand-alone Tier 1 shape — quantile-forecast-with-backtest. Distinct
from GARCH (models variance, not quantile directly), EVT (fits tail
distribution, not dynamic quantile), and C2 forecasters (point
forecast, not quantile).

Decision D7: Tier 2 opening sentence makes distribution-free framing
explicit per Convention C.
Decision D8: Tier 1 backtest ordering — Kupiec first, then DQ
(Engle-Manganelli); Christoffersen relegated to Tier 2 / Tier 3.
Decision D17: Christoffersen referenced as "conditional coverage
test" (not "independence test"); DQ as "Engle-Manganelli Dynamic
Quantile joint test".

Results-dict keys consumed:

    series_name / n_obs
    specification (SAV / AS / IG) / theta / parameter_names / parameters
    quantile_loss
    n_violations / expected_violations / violation_ratio
    kupiec_stat / kupiec_pval
    christoffersen_stat / christoffersen_pval
    dq_stat / dq_pval
    distribution_free
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


def _fmt_confidence_from_theta(theta: float) -> str:
    """Convention A: the 'confidence level' for VaR is (1 − θ) · 100%.
    Integer when whole (θ = 0.05 → 95%), fractional otherwise (θ =
    0.005 → 99.5%)."""
    try:
        conf = (1.0 - float(theta)) * 100.0
    except Exception:
        return f"{theta}"
    if abs(conf - round(conf)) < 1e-9:
        return f"{int(round(conf))}%"
    return f"{conf:.1f}%"


def _fmt_theta_pct(theta: float) -> str:
    try:
        v = float(theta) * 100.0
    except Exception:
        return f"{theta}"
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}%"
    return f"{v:.1f}%"


_SPEC_FULL_NAME = {
    "SAV": "Symmetric Absolute Value",
    "AS": "Asymmetric Slope",
    "IG": "Indirect GARCH",
}


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the return series"))
    n = int(results.get("n_obs", 0))
    spec = str(results.get("specification", "SAV")).upper()
    spec_full = _SPEC_FULL_NAME.get(spec, spec)
    theta = results.get("theta", 0.05)
    conf_str = _fmt_confidence_from_theta(theta)
    theta_pct = _fmt_theta_pct(theta)

    n_viol = int(results.get("n_violations", 0))
    exp_viol = results.get("expected_violations")
    try:
        exp_viol_f = float(exp_viol) if exp_viol is not None else float(n) * float(theta)
        exp_viol_str = f"{exp_viol_f:.1f}"
    except Exception:
        exp_viol_f = None
        exp_viol_str = "n/a"

    v_ratio = results.get("violation_ratio")
    try:
        v_ratio_str = f"{float(v_ratio):.2f}" if v_ratio is not None else "n/a"
    except Exception:
        v_ratio_str = "n/a"

    kupiec_p = results.get("kupiec_pval")
    dq_p = results.get("dq_pval")
    kupiec_clause = ""
    if kupiec_p is not None:
        try:
            verdict = (
                "does not reject"
                if float(kupiec_p) >= 0.05
                else "rejects"
            )
            kupiec_clause = (
                f"Kupiec unconditional coverage test {verdict} "
                f"(p = {FMT_P_VALUE.format(float(kupiec_p))})."
            )
        except Exception:
            kupiec_clause = ""
    dq_clause = ""
    if dq_p is not None:
        try:
            verdict = (
                "does not reject"
                if float(dq_p) >= 0.05
                else "rejects"
            )
            dq_clause = (
                f" Dynamic Quantile (Engle-Manganelli 2004) joint test "
                f"{verdict} (p = {FMT_P_VALUE.format(float(dq_p))})."
            )
        except Exception:
            dq_clause = ""

    # Coverage descriptor (mirrors wrapper convention).
    coverage_desc = ""
    try:
        vr = float(v_ratio) if v_ratio is not None else None
        if vr is not None:
            if vr < 0.8:
                coverage_desc = "too conservative (fewer violations than expected)"
            elif vr > 1.2:
                coverage_desc = "too aggressive (more violations than expected)"
            else:
                coverage_desc = "well-calibrated at the unconditional coverage level"
    except Exception:
        pass
    cov_phrase = f" — {coverage_desc}" if coverage_desc else ""

    return (
        f"CAViaR {spec} ({spec_full}) dynamic quantile model at the "
        f"{conf_str} VaR level ({theta_pct} quantile) on "
        f"{format_series_reference(name)} ({n} daily observations). "
        f"{n_viol} violations observed vs {exp_viol_str} expected "
        f"(realized / nominal exceedance ratio {v_ratio_str}"
        f"{cov_phrase}). {kupiec_clause}{dq_clause} The Christoffersen "
        f"conditional coverage test is flagged separately in Tier 3."
    )


def _tier2(results: dict) -> str:
    spec = str(results.get("specification", "SAV")).upper()
    spec_full = _SPEC_FULL_NAME.get(spec, spec)
    theta = results.get("theta", 0.05)

    pnames = list(results.get("parameter_names") or [])
    pvals = list(results.get("parameters") or [])

    # Parameter disclosure — align names with values by position.
    param_clauses = []
    for nm, v in zip(pnames, pvals):
        try:
            param_clauses.append(
                f"{nm} = {FMT_COEF_SIGNED.format(float(v))}"
            )
        except Exception:
            continue
    params_str = ", ".join(param_clauses) if param_clauses else "parameters unavailable"

    qloss = results.get("quantile_loss")
    qloss_str = format_scale_aware(float(qloss)) if qloss is not None else "n/a"

    kupiec_p = results.get("kupiec_pval")
    cc_p = results.get("christoffersen_pval")
    dq_p = results.get("dq_pval")

    def _verdict(p, reject_text="rejects", accept_text="does not reject"):
        if p is None:
            return "unavailable"
        try:
            return reject_text if float(p) < 0.05 else accept_text
        except Exception:
            return "unavailable"

    backtests_clause = (
        f"Kupiec unconditional coverage "
        f"(p = {FMT_P_VALUE.format(float(kupiec_p))}, "
        f"{_verdict(kupiec_p)}); Christoffersen conditional coverage "
        f"via first-order Markov chain on the hit indicators "
        f"(p = {FMT_P_VALUE.format(float(cc_p))}, "
        f"{_verdict(cc_p)}); Engle-Manganelli Dynamic Quantile joint "
        f"test (p = {FMT_P_VALUE.format(float(dq_p))}, "
        f"{_verdict(dq_p)})."
        if all(x is not None for x in (kupiec_p, cc_p, dq_p))
        else "Backtest p-values unavailable for one or more tests."
    )

    # Specification-specific color.
    spec_color = ""
    if spec == "SAV":
        spec_color = (
            " SAV: q_t = β₀ + β₁ · q_{t−1} + β₂ · |y_{t−1}| — symmetric "
            "response to positive and negative lagged returns. Does not "
            "capture leverage effects; consider the Asymmetric Slope "
            "(AS) variant if negative returns should widen VaR more "
            "than positive returns."
        )
    elif spec == "AS":
        spec_color = (
            " AS: q_t = β₀ + β₁ · q_{t−1} + β₂ · y_{t−1}^+ + β₃ · "
            "y_{t−1}^− — asymmetric response separates positive and "
            "negative lagged returns, capturing leverage-effect "
            "dynamics."
        )
    elif spec == "IG":
        spec_color = (
            " IG: q_t derived from an indirect GARCH(1,1) variance "
            "process — quantile implied by variance dynamics but fit "
            "directly via quantile loss rather than likelihood."
        )

    # Variant-specific follow-up suggestion — don't suggest refitting
    # with the variant we're already using.
    if spec == "SAV":
        followup = (
            " For a leverage-aware check on the dynamic response, "
            "refit with the Asymmetric Slope (AS) variant."
        )
    elif spec == "AS":
        followup = (
            " For a symmetric-response check (no leverage asymmetry), "
            "compare against the Symmetric Absolute Value (SAV) "
            "variant."
        )
    else:  # IG
        followup = (
            " For a direct-quantile check independent of the variance "
            "process, compare against the Symmetric Absolute Value "
            "(SAV) variant."
        )

    # Convention C — distribution-free opening.
    return (
        f"CAViaR is distribution-free: the quantile loss "
        f"(check / pinball function) "
        f"L(y, q; θ) = (y − q)(θ − 𝟙[y < q]) makes no assumption "
        f"about the return distribution — unlike GARCH-based VaR "
        f"(parametric) or EVT (tail-parametric). Fit by Nelder-Mead "
        f"minimization of the empirical quantile loss with random "
        f"restarts (preset-gated). Specification {spec} ({spec_full}) "
        f"at quantile θ = {theta}: {params_str}. Minimized quantile "
        f"loss = {qloss_str}.{spec_color} **Backtests:** "
        f"{backtests_clause}{followup}"
    )


def _trigger_kupiec_rejects(results: dict) -> Optional[str]:
    p = results.get("kupiec_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Kupiec unconditional coverage test rejects at the 5% level "
        f"(p = {FMT_P_VALUE.format(float(p))}). Realized exceedance "
        f"rate differs materially from the nominal rate; the quantile "
        f"level is miscalibrated on this sample. Consider an "
        f"alternative CAViaR specification or widen the optimization "
        f"restart count."
    )


def _trigger_christoffersen_rejects(results: dict) -> Optional[str]:
    p = results.get("christoffersen_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Christoffersen conditional coverage test rejects at the 5% "
        f"level (p = {FMT_P_VALUE.format(float(p))}); violations are "
        f"clustered, not independent. Unconditional coverage may be "
        f"correct (see Kupiec separately) but the pattern of "
        f"exceedances shows serial dependence — the model's dynamic "
        f"response is too slow to adjust the quantile after a "
        f"violation. Consider the Asymmetric Slope (AS) variant, "
        f"which separates leverage-effect responses to positive vs "
        f"negative lagged returns."
    )


def _trigger_dq_rejects(results: dict) -> Optional[str]:
    p = results.get("dq_pval")
    if p is None:
        return None
    try:
        if float(p) >= 0.05:
            return None
    except Exception:
        return None
    return (
        f"Dynamic Quantile (Engle-Manganelli 2004) joint test rejects "
        f"at the 5% level (p = {FMT_P_VALUE.format(float(p))}); the "
        f"model is neither well-calibrated nor adequate on the joint "
        f"coverage-and-independence criterion. Consider an alternative "
        f"CAViaR specification (AS for leverage; IG for "
        f"variance-linked dynamics) or increase the optimization "
        f"restart count (Thorough preset)."
    )


SPEC = InterpretationSpec(
    technique_id="caviar_quantile_dynamics",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_kupiec_rejects,
        _trigger_christoffersen_rejects,
        _trigger_dq_rejects,
    ),
    mode_aware=False,
)

register(SPEC)
