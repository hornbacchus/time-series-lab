"""
InterpretationSpec for quantile_regression (stands alone per D7).

Distinct from CAViaR: CAViaR is autoregressive on the quantile state
(3-4 parameters), while quantile regression is a cross-sectional
feature-based regression fitted independently per quantile.

Tier 1 shape: quantile-forecast-with-crossing-count.
D7: stands-alone framing (no CAViaR inheritance).
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)

PRESET_GATED_KEYS = ()


def _fmt_quantile(q: float) -> str:
    try:
        v = float(q) * 100.0
    except Exception:
        return str(q)
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v))}%"
    return f"{v:.1f}%"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    quantiles = results.get("quantiles") or []
    horizon = int(results.get("horizon", 0))
    n_q = len(quantiles)
    median_rmse = results.get("train_rmse_median")
    n_crossings = int(results.get("n_crossings", 0) or 0)
    median_str = format_scale_aware(float(median_rmse)) if median_rmse is not None else "n/a"
    quantile_list = ", ".join(_fmt_quantile(q) for q in quantiles)
    crossings_phrase = (
        f"**{n_crossings} quantile crossing(s) detected** in the forecast table (see Tier 3)"
        if n_crossings > 0 else
        "no quantile crossings detected"
    )
    return (
        f"Quantile regression forecast of {format_series_reference(name)} "
        f"({n} observations) at {n_q} quantile level(s) ({quantile_list}) "
        f"over a {horizon}-period horizon. Median-model in-sample RMSE "
        f"{median_str}. {crossings_phrase}. Multi-step rollover uses "
        f"the median-model prediction as the forward anchor; all "
        f"quantile paths drift via the same trajectory — a documented "
        f"coupling risk."
    )


def _render_top_features(results: dict) -> str:
    top = results.get("top_features_per_quantile") or {}
    if not isinstance(top, dict) or not top:
        return "top feature importances per quantile not available"
    parts = []
    for q_key, features in top.items():
        if not isinstance(features, list) or not features:
            continue
        f_parts = []
        for entry in features[:3]:
            try:
                f_parts.append(
                    f"{entry.get('name')}={FMT_COEF_UNSIGNED.format(float(entry.get('importance', 0)))}"
                )
            except Exception:
                continue
        if f_parts:
            parts.append(f"q={q_key}: " + ", ".join(f_parts))
    if not parts:
        return "top feature importances per quantile not available"
    return " ; ".join(parts)


def _tier2(results: dict) -> str:
    n_estimators = int(results.get("n_estimators", 0) or 0)
    max_depth = results.get("max_depth")
    n_lags = int(results.get("n_lags", 0) or 0)
    quantiles = results.get("quantiles") or []
    top_features_rendered = _render_top_features(results)
    return (
        f"Quantile regression via scikit-learn GradientBoostingRegressor "
        f"with `loss='quantile'` fitted independently per quantile "
        f"level ({n_estimators} estimators, max_depth={max_depth} per "
        f"quantile). {n_lags} lag features plus rolling statistics. "
        f"The check / pinball loss makes no distributional assumption "
        f"— distribution-free framing. **Unlike CAViaR**, this wrapper "
        f"does not emit a backtest suite (Kupiec / DQ); only the "
        f"quantile-crossing count is reported as a monotonicity sanity "
        f"check. Top-3 feature importances per quantile: "
        f"{top_features_rendered}. Recursive multi-step rollover uses "
        f"the median prediction as the forward anchor — if the median "
        f"is biased, all quantiles drift with it."
    )


def _trigger_crossings_detected(results: dict) -> Optional[str]:
    """D7 — fires when n_crossings > 0."""
    n_crossings = results.get("n_crossings")
    if n_crossings is None:
        return None
    try:
        nc = int(n_crossings)
        if nc == 0:
            return None
    except Exception:
        return None
    return (
        f"{nc} quantile crossing(s) detected in the forecast horizon — "
        f"quantile estimates are not monotonic at all forecast steps. "
        f"This violates the probabilistic interpretation of quantile "
        f"forecasts. Consider (a) reducing tree depth or n_estimators; "
        f"(b) post-hoc isotonic regression to enforce monotonicity; "
        f"(c) using a model that fits quantiles jointly (e.g., "
        f"quantile random forest)."
    )


def _trigger_median_rollover_caveat(results: dict) -> Optional[str]:
    """Always-fires — median rollover coupling disclosure."""
    horizon = int(results.get("horizon", 0) or 0)
    if horizon <= 1:
        return None
    return (
        "Multi-step forecast uses the median-model's prediction to "
        "extend the feature window; all quantile paths share this "
        "extension, so quantile uncertainty at long horizons reflects "
        "median uncertainty rather than quantile-specific dynamics."
    )


SPEC = InterpretationSpec(
    technique_id="quantile_regression",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_crossings_detected,
        _trigger_median_rollover_caveat,
    ),
    mode_aware=False,
)

register(SPEC)
