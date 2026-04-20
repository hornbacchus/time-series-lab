"""
InterpretationSpec for intervention_analysis.

Distinct from detection-based change-point specs: user provides event
dates, wrapper estimates the effect. Tier 1 leads with the event date,
effect magnitude, and significance verdict. Per V1 rewrite, scale
reference is cited in citation form (scale std=X.X), not bare-paren.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_SIGNED,
    FMT_COEF_UNSIGNED,
    FMT_P_VALUE,
    format_scale_aware,
    format_series_reference,
    interpret_pvalue,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n_interventions = int(results.get("n_interventions", 0))
    n_sig = int(results.get("n_significant", 0))
    top_date = results.get("top_intervention_date")
    top_label = results.get("top_intervention_label")
    top_coef = results.get("top_intervention_coef")
    top_p = results.get("top_intervention_p_value")
    top_ci_lo = results.get("top_intervention_ci_lower")
    top_ci_hi = results.get("top_intervention_ci_upper")
    series_std = results.get("series_std")

    if n_interventions == 0 or top_date is None or top_coef is None:
        return (
            f"Intervention analysis ran on {format_series_reference(name)} "
            f"but no user-specified interventions were evaluated. Add "
            f"event dates and re-run."
        )

    label_clause = f" ('{top_label}')" if top_label else ""
    coef_str = FMT_COEF_SIGNED.format(float(top_coef))
    p_clause = ""
    if top_p is not None:
        p_f = float(top_p)
        if p_f < 1e-3:
            p_clause = ", p<0.001"
        else:
            p_clause = f", p={FMT_P_VALUE.format(p_f)}"
    ci_clause = ""
    if top_ci_lo is not None and top_ci_hi is not None:
        ci_clause = f", 95% CI [{FMT_COEF_SIGNED.format(float(top_ci_lo))}, {FMT_COEF_SIGNED.format(float(top_ci_hi))}]"
    significance_clause = ""
    if top_p is not None:
        sig_word = "significant" if float(top_p) < 0.05 else "not significant"
        significance_clause = f" ({sig_word})"
    sig_ratio_clause = ""
    if n_interventions > 0:
        sig_ratio_clause = (
            f" {n_sig} of {n_interventions} user-specified "
            f"intervention{'s' if n_interventions != 1 else ''} "
            f"show{'s' if n_interventions == 1 else ''} significant effects."
        )
    scale_clause = ""
    if series_std is not None:
        scale_clause = (
            f" The magnitude is material relative to the series scale "
            f"std={FMT_COEF_UNSIGNED.format(float(series_std))}."
        )
    return (
        f"For intervention on {top_date}{label_clause}, the estimated "
        f"effect in {format_series_reference(name)} was {coef_str}"
        f"{p_clause}{ci_clause}{significance_clause}."
        f"{sig_ratio_clause}{scale_clause}"
    )


def _tier2(results: dict) -> str:
    arima_order = results.get("arima_order")
    order_clause = (
        f"ARIMA{tuple(arima_order)}"
        if arima_order else "ARIMA specification"
    )
    lb_p = results.get("ljung_box_p_value")
    aic = results.get("aic")
    aic_noint = results.get("aic_no_intervention")
    lb_clause = (
        f"Ljung-Box at lag 10 {'does-not-reject' if lb_p is not None and float(lb_p) >= 0.05 else 'rejects'} "
        f"(p={FMT_P_VALUE.format(float(lb_p))})"
        if lb_p is not None else "residual autocorrelation diagnostic in the data tables"
    )
    aic_clause = ""
    if aic is not None and aic_noint is not None:
        aic_clause = (
            f" AIC {format_scale_aware(float(aic))} vs "
            f"{format_scale_aware(float(aic_noint))} for the "
            f"no-intervention specification."
        )
    return (
        f"{order_clause} with intervention dummies; estimates by "
        f"maximum-likelihood. Per-intervention: effect coefficient, "
        f"SE, 95% CI, p-value in the data tables. Residual "
        f"diagnostics: {lb_clause}. Counterfactual series in the data "
        f"tables shows the hypothetical path without the "
        f"interventions.{aic_clause}"
    )


def _trigger_insignificant_intervention(results: dict) -> Optional[str]:
    n_interventions = int(results.get("n_interventions", 0))
    n_sig = int(results.get("n_significant", 0))
    if n_interventions == 0 or n_sig == n_interventions:
        return None
    n_insig = n_interventions - n_sig
    return (
        f"{n_insig} of {n_interventions} specified "
        f"intervention{'s' if n_insig != 1 else ''} "
        f"{'are' if n_insig != 1 else 'is'} not statistically "
        f"distinguishable from zero at the 5% level. Consider "
        f"whether they represent genuine events the series could "
        f"be expected to respond to, or whether the event timing is "
        f"misaligned with the data frequency."
    )


def _trigger_low_aic_improvement(results: dict) -> Optional[str]:
    aic = results.get("aic")
    aic_noint = results.get("aic_no_intervention")
    if aic is None or aic_noint is None:
        return None
    improvement = float(aic_noint) - float(aic)
    if improvement >= 2:
        return None
    return (
        f"AIC improvement over the no-intervention ARIMA is only "
        f"{improvement:.2f}, below the 2-point threshold for "
        f"meaningful model improvement. Interventions add little; "
        f"the no-intervention specification is competitive."
    )


def _trigger_residual_structure(results: dict) -> Optional[str]:
    lb_p = results.get("ljung_box_p_value")
    if lb_p is None or float(lb_p) >= 0.05:
        return None
    return (
        f"Residual Ljung-Box rejects white-noise at the 5% level "
        f"(p={FMT_P_VALUE.format(float(lb_p))}); the ARMA structure "
        f"is inadequate. Review the ARIMA order or consider "
        f"additional intervention types (level shift vs temporary "
        f"pulse)."
    )


SPEC = InterpretationSpec(
    technique_id="intervention_analysis",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_insignificant_intervention,
        _trigger_low_aic_improvement,
        _trigger_residual_structure,
    ),
    mode_aware=False,
)

register(SPEC)
