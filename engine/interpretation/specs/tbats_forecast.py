"""
InterpretationSpec for tbats_forecast (Follow-up 1b).

TBATS / BATS multi-seasonal forecaster. Inherits the Prompt C2
forecaster Tier 1 template via `_forecast_common` helpers with a
seasonality-rendering closer that cites the fitted seasonal periods.
Tier 2 additions: trigonometric vs BATS framing, AIC-selected
options, Box-Cox interpretation, harmonics-per-period (TBATS only).

Tier 3 triggers (5 total):
  - short_series_for_seasonality — fires when n_obs < 2 × max period
    used (should be rare since wrapper filters; fires when filter
    threshold is borderline)
  - box_cox_severe — Box-Cox λ outside [-0.5, 1.5]
  - non_integer_seasonality — any fitted period is non-integer
    (TBATS-specific advantage)
  - rmse_exceeds_naive — fit RMSE >= naive baseline
  - user_specified_periods_filtered (D5) — user gave
    seasonal_periods=[...] but wrapper dropped some
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register
from interpretation.specs._forecast_common import (
    render_horizon_trend_clause,
    render_baseline_comparison_clause,
)

PRESET_GATED_KEYS = ()


# Named aliases for common seasonal periods (D1).
_PERIOD_ALIAS = {
    4.0: "quarterly",
    5.0: "weekly-business",
    7.0: "weekly",
    12.0: "monthly",
    24.0: "hourly",
    52.0: "weekly-in-annual",
    52.179: "weekly-in-annual",
    260.0: "business-annual",
    365.0: "annual-daily-integer",
    365.25: "annual-daily",
}


def _render_seasonal_periods(periods, source, filtered):
    """Render the seasonal-period part of Tier 1 / Tier 2."""
    if not periods and not filtered:
        if source == "no-seasonality-inferred":
            return ("No seasonality inferred from series (index has no "
                    "regular frequency, or frequency not recognized). "
                    "Pass seasonal_periods=[...] parameter to specify "
                    "explicitly.")
        if source == "user-specified":
            return "No seasonality (user-specified empty list)."
        return "No seasonality."

    parts = []
    for p in periods:
        try:
            pf = float(p)
        except Exception:
            continue
        name = _PERIOD_ALIAS.get(pf)
        if name is None and pf == int(pf):
            name = _PERIOD_ALIAS.get(int(pf))
        if name:
            parts.append(f"{name}={pf}" if pf != int(pf) else f"{name}={int(pf)}")
        else:
            parts.append(f"period={pf}")

    n_kept = len(parts)
    if n_kept == 0:
        base = "all inferred periods were filtered"
    elif n_kept == 1:
        base = f"1 seasonal cycle ({parts[0]})"
    else:
        base = f"{n_kept} seasonal cycles ({', '.join(parts)})"

    if filtered:
        filt_parts = []
        for f in filtered:
            try:
                fp = float(f.get("period"))
            except Exception:
                fp = f.get("period")
            filt_parts.append(f"period {fp} ({f.get('reason')})")
        base += " [Filtered: " + "; ".join(filt_parts) + "]"

    return base


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    model = str(results.get("model_type", "TBATS"))

    baseline_clause = render_baseline_comparison_clause(
        fit_rmse=results.get("fit_rmse"),
        baseline_rmse=results.get("baseline_rmse"),
        baseline_label=results.get("baseline_label", "naive"),
    )
    trend_clause = render_horizon_trend_clause(
        last_observed_value=float(results.get("last_observed_value") or 0.0),
        forecast_end_value=float(results.get("forecast_end_value") or 0.0),
        series_std=float(results.get("series_std") or 0.0),
        series_mean=results.get("series_mean"),
        horizon=horizon,
    )

    seasonal_desc = _render_seasonal_periods(
        results.get("seasonal_periods_used") or [],
        str(results.get("seasonal_periods_source") or ""),
        results.get("seasonal_periods_filtered") or [],
    ).rstrip(".")

    return (
        f"{model} forecast of {format_series_reference(name)} "
        f"({n} observations) over {horizon} periods. {baseline_clause}; "
        f"{trend_clause}. Seasonality: {seasonal_desc}."
    )


def _tier2(results: dict) -> str:
    model = str(results.get("model_type", "TBATS"))
    use_trig = bool(results.get("use_trigonometric", True))
    sp_used = results.get("seasonal_periods_used") or []
    sp_source = str(results.get("seasonal_periods_source") or "")
    box_cox_sel = bool(results.get("use_box_cox_selected", False))
    box_cox_lam = results.get("box_cox_lambda")
    arma_sel = bool(results.get("use_arma_errors_selected", False))
    damped_sel = bool(results.get("use_damped_trend_selected", False))
    alpha = results.get("alpha")
    beta = results.get("beta")
    harmonics = results.get("n_harmonics_per_period") or []
    aic = results.get("aic")
    n_params = results.get("n_params")
    bats_rounding = results.get("bats_rounding_applied") or []

    alpha_str = FMT_COEF_UNSIGNED.format(float(alpha)) if alpha is not None else "n/a"
    beta_str = FMT_COEF_UNSIGNED.format(float(beta)) if beta is not None else "n/a"
    aic_str = format_scale_aware(float(aic)) if aic is not None else "n/a"

    # Model-type framing
    if use_trig:
        model_desc = (
            "TBATS (Trigonometric seasonality, Box-Cox, ARMA errors, "
            "Trend, Seasonal) model fitted via the `tbats` Python library. "
            "Trigonometric representation handles non-integer seasonal "
            "periods natively."
        )
    else:
        model_desc = (
            "BATS (Box-Cox, ARMA errors, Trend, Seasonal — **no "
            "Trigonometric**) model fitted via the `tbats` Python "
            "library. BATS requires integer seasonal periods; "
            "non-integer periods are rounded (see below)."
        )

    # Seasonal periods sentence
    if sp_used:
        sp_str = str(sp_used)
        if sp_source == "auto-inferred":
            sp_sentence = (
                f"Seasonal periods {sp_str} auto-inferred from the series "
                f"frequency."
            )
        elif sp_source == "user-specified":
            sp_sentence = f"Seasonal periods {sp_str} user-specified."
        else:
            sp_sentence = f"Seasonal periods {sp_str}."
    elif sp_source == "no-seasonality-inferred":
        sp_sentence = (
            "No seasonality inferred from series frequency. Model fitted "
            "as non-seasonal (trend + ARMA only)."
        )
    else:
        sp_sentence = "No seasonality fitted."

    # AIC-selected options
    box_cox_clause = ""
    if box_cox_sel and box_cox_lam is not None:
        try:
            lam = float(box_cox_lam)
            if abs(lam) < 0.1:
                lam_desc = "near 0 — log-like transformation"
            elif abs(lam - 1.0) < 0.1:
                lam_desc = "near 1 — effectively no transformation"
            elif -0.5 <= lam <= 1.5:
                lam_desc = "moderate transformation"
            else:
                lam_desc = "severe transformation — see Tier 3"
            box_cox_clause = f"Box-Cox applied (λ={lam:.3f}, {lam_desc}). "
        except Exception:
            box_cox_clause = "Box-Cox applied. "
    elif box_cox_sel is False:
        box_cox_clause = "Box-Cox not applied. "

    arma_clause = "ARMA errors included. " if arma_sel else "ARMA errors not included. "
    damped_clause = "Damped trend enabled. " if damped_sel else "Damped trend disabled. "

    harmonics_clause = ""
    if use_trig and harmonics and sp_used:
        pairs = []
        for p, h in zip(sp_used, harmonics):
            try:
                pairs.append(f"{int(h)} for period {p}")
            except Exception:
                continue
        if pairs:
            harmonics_clause = (
                f"Trigonometric harmonics fitted per period: "
                f"{', '.join(pairs)}. "
            )

    # BATS rounding disclosure (D2)
    bats_clause = ""
    if bats_rounding:
        rounded_parts = []
        for r in bats_rounding:
            try:
                rounded_parts.append(
                    f"{r.get('original')} → {r.get('rounded')}"
                )
            except Exception:
                continue
        if rounded_parts:
            bats_clause = (
                f"Non-integer period(s) rounded for BATS compatibility "
                f"({', '.join(rounded_parts)}); consider TBATS "
                f"(use_trigonometric=True) to handle non-integer periods "
                f"natively. "
            )

    # Parameters
    param_clause = (
        f"Smoothing parameters: level α={alpha_str}, trend β={beta_str}. "
        f"AIC={aic_str}"
        + (f", effective parameters ≈ {int(n_params)}" if n_params is not None else "")
        + "."
    )

    # HD-4 — implementation provenance and cross-package note.
    # The Phase 1 reference-parity audit (1b) compared Python tbats
    # against R forecast::tbats and observed modest smoothing-
    # parameter divergence attributable to optimizer defaults.
    impl_clause = (
        " Implementation: TSL wraps the Python tbats package "
        "(De Livera-Hyndman-Snyder 2011 algorithm), which uses BFGS "
        "with the package's default tolerance settings. R "
        "forecast::tbats implements the same algorithm but ships "
        "different BFGS tolerances and a different Box-Cox lambda "
        "search range; on identical fixtures, smoothing parameters "
        "(α, β, γ) from the two implementations typically agree to "
        "within 2 to 3 percent and point forecasts to within a few "
        "percent. Both are mathematically correct."
    )

    return (
        f"{model_desc} {sp_sentence} {box_cox_clause}{arma_clause}"
        f"{damped_clause}{harmonics_clause}{bats_clause}{param_clause}"
        f"{impl_clause}"
    )


def _trigger_short_series_for_seasonality(results: dict) -> Optional[str]:
    """Fires when n_obs < 2 × max(seasonal_periods_used). Rare because
    wrapper filters, but fires on borderline cases where the wrapper
    kept a period that's still pushing the threshold."""
    periods = results.get("seasonal_periods_used") or []
    n = int(results.get("n_obs", 0))
    if not periods:
        return None
    try:
        max_p = max(float(p) for p in periods)
    except Exception:
        return None
    if n >= 2 * max_p:
        return None
    return (
        f"Series length {n} is less than 2× the longest fitted seasonal "
        f"period ({max_p}). Seasonal estimation may be unreliable; "
        f"consider aggregating to a longer period or using a simpler "
        f"forecaster."
    )


def _trigger_box_cox_severe(results: dict) -> Optional[str]:
    lam = results.get("box_cox_lambda")
    if lam is None:
        return None
    try:
        v = float(lam)
    except Exception:
        return None
    if -0.5 <= v <= 1.5:
        return None
    return (
        f"Box-Cox λ={v:.3f} is outside the typical range [-0.5, 1.5] — "
        f"variance-stabilizing transformation is severe; check the "
        f"series for extreme heteroscedasticity or consider explicit "
        f"pre-differencing."
    )


def _trigger_non_integer_seasonality(results: dict) -> Optional[str]:
    periods = results.get("seasonal_periods_used") or []
    non_int = []
    for p in periods:
        try:
            pf = float(p)
            if pf != int(pf):
                non_int.append(pf)
        except Exception:
            continue
    if not non_int:
        return None
    rendered = ", ".join(str(p) for p in non_int)
    return (
        f"Non-integer seasonal period(s) detected ({rendered}). TBATS "
        f"handles these via trigonometric representation; BATS would "
        f"not and would require rounding — this is a TBATS-specific "
        f"capability."
    )


def _trigger_rmse_exceeds_naive(results: dict) -> Optional[str]:
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None:
        return None
    try:
        if float(fit) < float(base):
            return None
    except Exception:
        return None
    label = str(results.get("baseline_label", "naive"))
    return (
        f"Fit RMSE {format_scale_aware(float(fit))} matches or exceeds "
        f"the {label} baseline {format_scale_aware(float(base))}. The "
        f"model does not beat naive on this series; reconsider "
        f"specification (e.g., different seasonal_periods, disable "
        f"Box-Cox, or switch to a simpler forecaster)."
    )


def _trigger_user_specified_periods_filtered(results: dict) -> Optional[str]:
    """D5 — fires when user-specified seasonal periods were dropped by
    the wrapper's length filter. Auto-inferred filtering does NOT fire
    this trigger (Tier 2 disclosure is sufficient); user-specified
    filtering fires because user intent was explicit."""
    source = str(results.get("seasonal_periods_source") or "")
    if source != "user-specified":
        return None
    filtered = results.get("seasonal_periods_filtered") or []
    if not filtered:
        return None
    dropped_list = [str(f.get("period")) for f in filtered]
    kept_list = [str(p) for p in (results.get("seasonal_periods_used") or [])]
    try:
        max_dropped = max(float(f.get("period")) for f in filtered)
        required = int(2 * max_dropped)
    except Exception:
        required = None
    n = int(results.get("n_obs", 0))
    return (
        f"User-specified seasonal period(s) [{', '.join(dropped_list)}] "
        f"could not be fitted on the available {n} observations (each "
        f"requires at least 2× the period length). "
        + (f"Only [{', '.join(kept_list)}] fitted. " if kept_list else "No seasonal periods fitted. ")
        + (f"Either provide at least {required} observations for all "
           f"specified periods, or remove unfittable periods from the "
           f"seasonal_periods parameter." if required else
           "Remove unfittable periods from the seasonal_periods parameter.")
    )


SPEC = InterpretationSpec(
    technique_id="tbats_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_short_series_for_seasonality,
        _trigger_box_cox_severe,
        _trigger_non_integer_seasonality,
        _trigger_rmse_exceeds_naive,
        _trigger_user_specified_periods_filtered,
    ),
    mode_aware=False,
)

register(SPEC)
