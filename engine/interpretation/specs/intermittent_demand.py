"""
InterpretationSpec for intermittent_demand (Croston / SBA / TSB).

Distinct Tier 1 shape (not the shared forecaster template): leads
with Syntetos-Boylan pattern classification + mean-demand baseline,
because the generic last-value naive is misleading for intermittent
series (most recent values are often zero). Method-branched Tier 2
discloses which of Croston / SBA / TSB was used.
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


# Minimum RMSE delta (as a fraction of baseline RMSE) at which the
# mean-baseline-wins Tier 3 trigger fires. Below this threshold, the
# baseline and the fitted method are treated as "effectively tied"
# and a gentler alternate trigger fires instead. Parallels
# forecast_combination's MEANINGFUL_LIFT_PCT_THRESHOLD (introduced in
# the Prompt C1 post-eval corrections batch).
MEANINGFUL_LIFT_RMSE_DELTA_PCT = 0.05


def _adi_language(adi: float) -> str:
    # Syntetos-Boylan ADI cutoff is 1.32.
    return "sporadic" if float(adi) >= 1.32 else "frequent"


def _cv2_language(cv2: float) -> str:
    c = float(cv2)
    if c < 0.25:
        return "low"
    if c < 0.75:
        return "moderate"
    return "high"


def _pattern_display(pattern: str) -> str:
    # The wrapper stores pattern with capitalized first letter
    # ("Intermittent"); render as lowercase for prose continuity.
    return str(pattern or "unknown").lower()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    zero_rate_pct = 100.0 * float(results.get("zero_rate", 0.0))
    pattern = _pattern_display(results.get("demand_pattern", "unknown"))
    adi = float(results.get("adi", 0.0))
    cv2 = float(results.get("cv2_demand", 0.0))
    method = str(results.get("method", "croston")).lower()
    method_name = {
        "croston": "Croston's method",
        "sba": "SBA (Syntetos-Boylan-Approximation)",
        "tsb": "TSB (Teunter-Syntetos-Babai)",
    }.get(method, f"{method}")
    fc_mean = float(results.get("forecast_mean_per_period", 0.0))
    baseline_mean = float(results.get("baseline_mean", 0.0))
    # Delta vs baseline (signed percentage, using abs in denominator
    # per the forecast-family convention).
    if baseline_mean != 0:
        delta_pct = 100.0 * (fc_mean - baseline_mean) / abs(baseline_mean)
        dir_word = "above" if delta_pct >= 0 else "below"
        delta_clause = (
            f"{format_scale_aware(baseline_mean)} ({abs(delta_pct):.1f}% {dir_word} baseline)"
        )
    else:
        delta_clause = f"{format_scale_aware(baseline_mean)} (delta undefined, baseline is zero)"
    return (
        f"{method_name} applied to {format_series_reference(name)} "
        f"({n} observations, {zero_rate_pct:.1f}% zero-periods), "
        f"classified as {pattern} demand — ADI={format_scale_aware(adi)} "
        f"indicates {_adi_language(adi)} demand periods, "
        f"CV²={format_scale_aware(cv2)} indicates {_cv2_language(cv2)} "
        f"demand-size variability. Flat forecast {format_scale_aware(fc_mean)} "
        f"units per period; mean-demand baseline {delta_clause}. "
        f"Point forecast only; realized values fluctuate due to "
        f"inter-arrival structure."
    )


def _tier2_croston(results: dict) -> str:
    alpha = float(results.get("alpha", 0.1))
    return (
        f"Croston was selected via the method parameter; the wrapper "
        f"also supports SBA (bias-corrected Croston with 1 − α/2 "
        f"multiplier, preferred for long-horizon aggregate demand) and "
        f"TSB (Teunter-Syntetos-Babai, preferred when the series shows "
        f"possible obsolescence). "
        f"Croston's method with smoothing parameter "
        f"α={FMT_COEF_UNSIGNED.format(alpha)} applied to non-zero-period "
        f"demand sizes and inter-arrival intervals separately. Updating "
        f"rule: when demand occurs at time t, z_t = α·y_t + (1-α)·z_{{t-1}} "
        f"(demand size) and p_t = α·q + (1-α)·p_{{t-1}} (inter-arrival "
        f"interval, where q counts periods since the last demand); "
        f"forecast is z/p per period. Croston's method is known to be "
        f"upward-biased on the forecast mean — SBA corrects this bias "
        f"via the 1 − α/2 multiplier. Syntetos-Boylan classification "
        f"grid (ADI cutoff 1.32, CV² cutoff 0.49) places this series in "
        f"the {_pattern_display(results.get('demand_pattern', 'unknown'))} "
        f"quadrant."
    )


def _tier2_sba(results: dict) -> str:
    alpha = float(results.get("alpha", 0.1))
    return (
        f"SBA was selected via the method parameter; the wrapper also "
        f"supports classical Croston (same update rule without the bias "
        f"correction) and TSB (for obsolescence-prone series). "
        f"SBA (Syntetos-Boylan-Approximation): bias-corrected Croston "
        f"with the multiplicative factor (1 − α/2) applied to the z/p "
        f"forecast. Smoothing parameter "
        f"α={FMT_COEF_UNSIGNED.format(alpha)}. Updating rule for z_t and "
        f"p_t matches Croston; the correction compensates for Croston's "
        f"upward bias on the forecast mean. Preferred over Croston for "
        f"aggregate-demand forecasting over long horizons; preferred "
        f"over TSB when the series shows stable (non-obsolescing) "
        f"demand probability. Syntetos-Boylan classification grid (ADI "
        f"cutoff 1.32, CV² cutoff 0.49) places this series in the "
        f"{_pattern_display(results.get('demand_pattern', 'unknown'))} "
        f"quadrant."
    )


def _tier2_tsb(results: dict) -> str:
    alpha = float(results.get("alpha", 0.1))
    beta = results.get("beta")
    beta_str = (FMT_COEF_UNSIGNED.format(float(beta)) if beta is not None else "α")
    return (
        f"TSB was selected via the method parameter; the wrapper also "
        f"supports classical Croston and SBA for series without "
        f"obsolescence risk. "
        f"TSB (Teunter-Syntetos-Babai): forecasts demand size z and "
        f"demand probability d separately and multiplies them. "
        f"Smoothing parameters α={FMT_COEF_UNSIGNED.format(alpha)} "
        f"(demand size) and β={beta_str} (probability). Updating rule: "
        f"z_t = α·y_t + (1-α)·z_{{t-1}} when demand occurs (else "
        f"z_{{t-1}} unchanged); d_t = β·𝟙{{y_t > 0}} + (1-β)·d_{{t-1}} "
        f"every period, so d decays toward zero when consecutive periods "
        f"show no demand. Preferred for series with obsolescence risk "
        f"(product end-of-life patterns); handles demand-probability "
        f"decline that Croston and SBA do not. Syntetos-Boylan "
        f"classification grid (ADI cutoff 1.32, CV² cutoff 0.49) places "
        f"this series in the "
        f"{_pattern_display(results.get('demand_pattern', 'unknown'))} "
        f"quadrant."
    )


def _tier2(results: dict) -> str:
    method = str(results.get("method", "croston")).lower()
    if method == "sba":
        return _tier2_sba(results)
    if method == "tsb":
        return _tier2_tsb(results)
    return _tier2_croston(results)


def _trigger_pattern_method_mismatch(results: dict) -> Optional[str]:
    pattern = _pattern_display(results.get("demand_pattern", "unknown"))
    method = str(results.get("method", "croston")).lower()
    if pattern != "smooth" or method not in {"croston", "sba", "tsb"}:
        return None
    return (
        "Series classified as smooth demand (ADI and CV² below "
        "intermittent thresholds); standard exponential smoothing or "
        "ARIMA may be preferable to intermittent-demand methods."
    )


def _trigger_obsolescence_risk(results: dict) -> Optional[str]:
    if not bool(results.get("last10_all_zero", False)):
        return None
    method = str(results.get("method", "croston")).lower()
    if method == "tsb":
        return None
    return (
        "Recent tail (last 10 periods) shows no demand — obsolescence "
        "risk. Consider TSB, which models demand-probability decline; "
        "Croston and SBA cannot detect series that are ending."
    )


def _trigger_baseline_beats_fitted_by_gt_5pct(results: dict) -> Optional[str]:
    """Fires when the mean-demand baseline's RMSE is meaningfully below
    the fitted model's RMSE (by more than MEANINGFUL_LIFT_RMSE_DELTA_PCT
    of the baseline). Below that delta, the companion
    ``_trigger_baseline_and_fitted_tied_within_5pct`` fires instead."""
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None or float(base) <= 0:
        return None
    # Baseline "wins" means lower RMSE (recall: base and fit are both RMSEs).
    # We want the case where base < fit by more than threshold.
    delta = (float(fit) - float(base)) / float(base)
    if delta <= MEANINGFUL_LIFT_RMSE_DELTA_PCT:
        return None
    return (
        f"Mean-demand baseline (RMSE {format_scale_aware(float(base))}) "
        f"beats the fitted intermittent model "
        f"(RMSE {format_scale_aware(float(fit))}) by more than "
        f"{int(MEANINGFUL_LIFT_RMSE_DELTA_PCT * 100)}%; the chosen method "
        f"does not add value on this series — prefer the simpler mean "
        f"forecast."
    )


def _trigger_baseline_and_fitted_tied_within_5pct(results: dict) -> Optional[str]:
    """Fires when the mean-demand baseline RMSE and the fitted model
    RMSE are within MEANINGFUL_LIFT_RMSE_DELTA_PCT of each other. A
    gentler companion to the ``baseline_beats_fitted_by_gt_5pct``
    trigger for the small-delta regime that would otherwise read as
    numerical noise."""
    fit = results.get("fit_rmse")
    base = results.get("baseline_rmse")
    if fit is None or base is None or float(base) <= 0:
        return None
    rel_diff = abs(float(fit) - float(base)) / float(base)
    if rel_diff > MEANINGFUL_LIFT_RMSE_DELTA_PCT:
        return None
    # Only fire on ties; if one meaningfully beats the other, the
    # corresponding single-sided trigger fires.
    return (
        f"Mean-demand baseline (RMSE {format_scale_aware(float(base))}) "
        f"and the fitted intermittent model "
        f"(RMSE {format_scale_aware(float(fit))}) are effectively tied; "
        f"the simpler baseline is a reasonable alternative if preferred."
    )


def _trigger_intervals_not_calibrated(results: dict) -> Optional[str]:
    # Always fires per Decision 5.
    return (
        "Intermittent-demand forecasts do not ship with calibrated "
        "prediction intervals; the point forecast represents expected "
        "demand per period, but realized values fluctuate due to "
        "inter-arrival structure."
    )


SPEC = InterpretationSpec(
    technique_id="intermittent_demand",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_pattern_method_mismatch,
        _trigger_obsolescence_risk,
        _trigger_baseline_beats_fitted_by_gt_5pct,
        _trigger_baseline_and_fitted_tied_within_5pct,
        _trigger_intervals_not_calibrated,
    ),
    mode_aware=False,
)

register(SPEC)
