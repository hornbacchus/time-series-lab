"""
Shared helpers for Prompt C2 Forecasting-family interpretation specs.

Leading-underscore filename marks this as spec-internal (not a
registered spec). Used by arima, auto_arima, ets, holt_winters, theta,
and prophet specs for the shared horizon-trend-extrapolation clause
and the baseline-comparison clause.

Intermittent_demand uses a distinct Tier 1 shape and does NOT route
through this helper.
"""

from interpretation.primitives import format_scale_aware


def render_horizon_trend_clause(
    *,
    last_observed_value: float,
    forecast_end_value: float,
    series_std: float,
    horizon: int,
) -> str:
    """Render the "forecast ends {...}" clause.

    Three-rule fallback hierarchy (Prompt C2 Decision 7):
      1. ``|last| < 1e-6`` → absolute-level fallback.
      2. ``|last| < 0.2 * series_std`` → absolute-level fallback.
      3. ``|trend_pct| > 100.0`` → absolute-level fallback.
      4. Else: render as signed percentage change.

    Absolute-level fallback phrasing includes the units suffix and
    named start-value context per Revision 1:
      "forecast ends at X, starting from Y"
    """
    last = float(last_observed_value)
    end = float(forecast_end_value)
    std = float(series_std) if series_std is not None else 0.0
    abs_last = abs(last)

    # Rule 1: near-zero last observation
    if abs_last < 1e-6:
        return (
            f"forecast ends at {format_scale_aware(end)}, "
            f"starting from {format_scale_aware(last)}"
        )

    # Rule 2: last is small relative to series scale
    if std > 0 and abs_last < 0.2 * std:
        return (
            f"forecast ends at {format_scale_aware(end)}, "
            f"starting from {format_scale_aware(last)}"
        )

    trend_pct = 100.0 * (end - last) / abs_last

    # Rule 3: extreme-ratio cap
    if abs(trend_pct) > 100.0:
        return (
            f"forecast ends at {format_scale_aware(end)}, "
            f"starting from {format_scale_aware(last)}"
        )

    # Standard rendering
    direction = "above" if trend_pct >= 0 else "below"
    return (
        f"forecast ends {trend_pct:+.1f}% {direction} the latest "
        f"observation at horizon {int(horizon)}"
    )


def render_baseline_comparison_clause(
    *,
    fit_rmse: float,
    baseline_rmse: float,
    baseline_label: str,
) -> str:
    """Render the "Fit RMSE X vs {baseline_label} Y (Δ% better|worse)" clause.

    If fit_rmse or baseline_rmse is None or non-positive, returns a
    best-effort fragment without the delta percentage.
    """
    if fit_rmse is None or baseline_rmse is None or float(baseline_rmse) <= 0:
        if fit_rmse is not None:
            return (
                f"Fit RMSE {format_scale_aware(float(fit_rmse))} "
                f"(no {baseline_label or 'naive'} baseline available)"
            )
        return f"Fit RMSE not computed"
    fit = float(fit_rmse)
    base = float(baseline_rmse)
    delta_pct = 100.0 * (base - fit) / base
    if delta_pct >= 0:
        direction = "better"
    else:
        direction = "worse"
    return (
        f"Fit RMSE {format_scale_aware(fit)} vs {baseline_label} "
        f"{format_scale_aware(base)} ({abs(delta_pct):.1f}% {direction})"
    )
