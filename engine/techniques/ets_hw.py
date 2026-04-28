"""
ETS / Holt-Winters Exponential Smoothing for Time Series Lab.

Fits an Exponential Smoothing model (Simple, Holt, or Holt-Winters) using
statsmodels ExponentialSmoothing and produces forecasts with prediction intervals.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)


def _infer_period(ctx: RunContext) -> int:
    """Infer seasonal period, return 0/1 if no seasonality."""
    user_period = ctx.get_param("seasonal_periods")
    if user_period is not None:
        return int(user_period)
    user_period = ctx.get_param("period")
    if user_period is not None:
        return int(user_period)

    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    freq = (ctx.frequency or "").strip().upper()
    if freq in freq_map:
        return freq_map[freq]
    freq_lower = (ctx.frequency or "").strip()
    if freq_lower in freq_map:
        return freq_map[freq_lower]
    return 0


def _prepare_series(values):
    """Strip edge NaN, interpolate interior. Returns (clean, n_interpolated)."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([]), 0

    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
        else:
            trimmed = trimmed[~np.isnan(trimmed)]
            nan_count = 0
    return trimmed, nan_count


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit ETS / Holt-Winters and generate forecasts.

    Parameters (via ctx.params)
    ---------------------------
    trend : str or None
        'add', 'mul', or None. Default: 'add'.
    seasonal : str or None
        'add', 'mul', or None. Default: auto-detect.
    seasonal_periods : int, optional
        Seasonal period. Auto-inferred if omitted.
    damped_trend : bool, optional
        Whether to use damped trend. Default False.
    horizon : int, optional
        Forecast steps. Default 10.
    use_boxcox : bool or float, optional
        Apply Box-Cox transform. Default False.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 6:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. Need at least 6.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        # CAI Phase 2 Session 27 fix (F-ETS-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=["Use a positive integer for forecast horizon."],
            )

        # Trend
        # CAI Phase 2 Session 27 fix (F-ETS-TREND): explicit
        # allowlist gate. Pre-fix, invalid `trend` strings
        # silently fell through to "add" via if/else at line
        # 113-115. Session 18 silent-fall-through pattern.
        trend_param = ctx.get_param("trend", "add")
        if trend_param and str(trend_param).lower() in ("none", "null", "false"):
            trend_param = None
        elif trend_param:
            _t_normalized = str(trend_param).lower()[:3]
            if _t_normalized not in ("add", "mul"):
                return make_error_response(
                    ctx,
                    f"Unknown trend '{trend_param}'. Must be one "
                    "of: None, 'add', 'mul'.",
                    error_fixes=[
                        "Use None (no trend), 'add' (additive; "
                        "default), or 'mul' (multiplicative; "
                        "requires positive data).",
                    ],
                )
            trend_param = _t_normalized

        damped = ctx.get_param("damped_trend", False)
        # CAI Phase 2 Session 27 fix (F-ETS-DAMPED-NOTREND):
        # multi-parameter consistency. Pre-fix, damped_trend=True
        # was silently disabled when trend=None (line 182:
        # damped if trend_param else False).
        if damped and trend_param is None:
            return make_error_response(
                ctx,
                "damped_trend=True requires trend to be set "
                "('add' or 'mul'). Got trend=None.",
                error_fixes=[
                    "Set trend='add' or 'mul' to use damped "
                    "trend, or set damped_trend=False.",
                ],
            )

        # Seasonal.
        period = _infer_period(ctx)
        user_supplied_seasonal = "seasonal" in ctx.params
        seasonal_param = ctx.get_param("seasonal")
        if seasonal_param and str(seasonal_param).lower() in ("none", "null", "false"):
            seasonal_param = None  # explicit string disable
        elif seasonal_param:
            # CAI Phase 2 Session 27 fix (F-ETS-SEASONAL):
            # explicit allowlist gate. Pre-fix, invalid
            # `seasonal` silently fell through to "add" via
            # if/else at line 132-134. Session 18 pattern.
            _s_normalized = str(seasonal_param).lower()[:3]
            if _s_normalized not in ("add", "mul"):
                return make_error_response(
                    ctx,
                    f"Unknown seasonal '{seasonal_param}'. Must "
                    "be one of: None, 'add', 'mul'.",
                    error_fixes=[
                        "Use None (no seasonal), 'add' (additive "
                        "seasonal), or 'mul' (multiplicative; "
                        "requires positive data).",
                    ],
                )
            seasonal_param = _s_normalized
        elif user_supplied_seasonal:
            seasonal_param = None
        else:
            if period >= 2 and n >= 2 * period:
                seasonal_param = "add"
            else:
                seasonal_param = None

        if seasonal_param is not None and (period < 2 or n < 2 * period):
            warn_list.append(
                f"Seasonal component disabled: period={period}, n={n} "
                f"(need n >= {2 * period})."
            )
            seasonal_param = None

        # CAI Phase 2 Session 27 fix (F-ETS-MUL-NEG-SEAS,
        # F-ETS-MUL-NEG-TREND): multi-parameter consistency.
        # Pre-fix, mul + non-positive data silently switched to
        # add (with warning). Session 16 loud-and-coerced is
        # severe — user's intended computation differs from what
        # ran. Reject explicitly.
        if seasonal_param == "mul" and np.any(clean <= 0):
            return make_error_response(
                ctx,
                "seasonal='mul' requires strictly positive "
                "observations; series contains non-positive "
                "values.",
                error_fixes=[
                    "Use seasonal='add' for series with "
                    "non-positive values, or transform the "
                    "series (e.g. log) so all values are > 0.",
                ],
            )
        if trend_param == "mul" and np.any(clean <= 0):
            return make_error_response(
                ctx,
                "trend='mul' requires strictly positive "
                "observations; series contains non-positive "
                "values.",
                error_fixes=[
                    "Use trend='add' for series with "
                    "non-positive values, or transform.",
                ],
            )

        use_boxcox = ctx.get_param("use_boxcox", False)
        if use_boxcox and np.any(clean <= 0):
            warn_list.append("Box-Cox requires positive values. Disabling.")
            use_boxcox = False

        progress_callback("Fitting ETS model", 20)

        # Preset: optimize vs fixed
        optimized = True  # always optimize

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                model = ExponentialSmoothing(
                    clean,
                    trend=trend_param,
                    seasonal=seasonal_param,
                    seasonal_periods=period if seasonal_param else None,
                    damped_trend=damped if trend_param else False,
                    use_boxcox=use_boxcox,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=optimized)
            except Exception as e1:
                # Fallback: simpler model
                warn_list.append(
                    f"Full model failed ({e1}). Falling back to simpler specification."
                )
                model = ExponentialSmoothing(
                    clean,
                    trend="add",
                    seasonal=None,
                    damped_trend=False,
                    initialization_method="estimated",
                )
                fit = model.fit(optimized=True)
                trend_param = "add"
                seasonal_param = None
                damped = False

        progress_callback("Generating forecasts", 55)

        # Forecast
        fc = fit.forecast(horizon)

        # Simulation-based prediction intervals (if preset allows)
        n_sim = {"Fast": 100, "Balanced": 500, "Thorough": 1000}.get(ctx.preset, 500)
        try:
            sim = fit.simulate(horizon, repetitions=n_sim, error="mul" if seasonal_param == "mul" else "add")
            lower = np.percentile(sim, 2.5, axis=1)
            upper = np.percentile(sim, 97.5, axis=1)
        except Exception:
            # Fallback: t-distribution interval from residual std.
            # 1.96 (standard normal 97.5 percentile) assumes known
            # variance and infinite DoF — wrong on small samples and
            # on skewed/heavy-tailed residuals. Use t-critical with
            # T − n_params degrees of freedom and horizon-scaled σ
            # (variance grows approximately √h for ETS random-walk
            # additive errors; multiplicative errors grow differently
            # but the simulation path above handles that case when
            # it's available).
            from scipy.stats import t as _t_dist
            resid = clean - fit.fittedvalues
            resid_std = float(np.std(resid, ddof=1))
            n_params = int(getattr(fit, "k_params", len(getattr(fit, "params", [])) or 3))
            dof = max(1, len(clean) - n_params)
            t_crit = float(_t_dist.ppf(0.975, dof))
            horizon_scale = np.sqrt(np.arange(1, horizon + 1))
            half_width = t_crit * resid_std * horizon_scale
            lower = fc - half_width
            upper = fc + half_width
            warn_list.append(
                f"Prediction intervals estimated from residual std with "
                f"t-critical ({t_crit:.2f}, dof={dof}) — simulation path "
                f"failed. Intervals may under-cover if residuals are "
                f"non-iid or heavily skewed."
            )

        # In-sample
        fitted_vals = fit.fittedvalues
        residuals = clean - fitted_vals

        progress_callback("Building output", 80)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                n + i + 1,
                round(float(fc.iloc[i] if hasattr(fc, 'iloc') else fc[i]), 6),
                round(float(lower[i]), 6),
                round(float(upper[i]), 6),
            ])
        forecast_table = make_table(
            "Forecast", ["Step", "Forecast", "Lower 95%", "Upper 95%"], fc_rows
        )

        # Fitted values table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        fit_rows = []
        for i in range(n):
            fit_rows.append([
                time_col[i],
                clean[i],
                float(fitted_vals.iloc[i] if hasattr(fitted_vals, 'iloc') else fitted_vals[i]),
                float(residuals.iloc[i] if hasattr(residuals, 'iloc') else residuals[i]),
            ])
        fitted_table = make_table(
            "Fitted Values", ["Time", name, "Fitted", "Residual"], fit_rows
        )

        # Model summary
        aic = float(fit.aic)
        bic = float(fit.bic)
        valid_resid = np.asarray(residuals)
        valid_resid = valid_resid[~np.isnan(valid_resid)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
        mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

        model_desc = _describe_model(trend_param, seasonal_param, damped, period)

        summary_rows = [
            ["Model", model_desc],
            ["Trend", trend_param or "None"],
            ["Seasonal", seasonal_param or "None"],
            ["Seasonal Periods", period if seasonal_param else "N/A"],
            ["Damped Trend", damped],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Observations", n],
            ["Forecast Horizon", horizon],
        ]

        # Smoothing parameters
        params_dict = fit.params_formatted if hasattr(fit, 'params_formatted') else {}
        if hasattr(fit, 'params'):
            p = fit.params
            for k, v in p.items():
                summary_rows.append([f"Param: {k}", round(float(v), 6) if isinstance(v, (int, float, np.floating)) else v])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Plain English
        plain = (
            f"{model_desc} fitted to '{name}' ({n} observations). "
            f"AIC={aic:.1f}"
        )
        if rmse:
            plain += f", RMSE={rmse:.4f}"
        plain += f". {horizon}-step forecast produced."
        if damped:
            plain += " Damped trend reduces long-horizon forecast divergence."

        charting = (
            "Line chart with original series, fitted values overlaid, and forecast "
            "continuation with shaded 95% prediction interval. "
            "Secondary panel: residuals."
        )

        progress_callback("Done", 100)

        # Prompt C2: naive-baseline comparison + smoothing-param labeling
        # + Tier 1 trend-extrapolation fields.
        from techniques.base import fit_naive_baseline
        baseline = fit_naive_baseline(
            clean, frequency=ctx.frequency, horizon=horizon, mode="auto",
        )
        last_observed_value = float(clean[-1]) if len(clean) > 0 else 0.0
        forecast_end_value = float(np.asarray(fc)[-1]) if len(fc) > 0 else 0.0
        # Extract labeled smoothing params from the fit object.
        _alpha = _beta = _gamma = _phi = None
        def _coerce(v):
            """Return float(v) when finite, else None. statsmodels reports
            missing smoothing params (e.g., gamma when seasonal is disabled)
            as float('nan'); the spec should treat those as absent."""
            if v is None:
                return None
            try:
                fv = float(v)
            except Exception:
                return None
            if np.isnan(fv):
                return None
            return fv
        try:
            _p = fit.params
            if hasattr(_p, "get"):
                _alpha = _coerce(_p.get("smoothing_level"))
                _beta  = _coerce(_p.get("smoothing_trend"))
                _gamma = _coerce(_p.get("smoothing_seasonal"))
                _phi   = _coerce(_p.get("damping_trend"))
        except Exception:
            pass

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None

        _interp_dict = {
            "series_name": name,
            "n_obs": int(n),
            "horizon": int(horizon),
            "trend_type": trend_param,
            "seasonal_type": seasonal_param,
            "seasonal_period": int(period) if seasonal_param else None,
            "damped_trend": bool(damped),
            "alpha": _alpha,
            "beta": _beta,
            "gamma": _gamma,
            "phi": _phi,
            "aic": float(aic),
            "bic": float(bic),
            "fit_rmse": float(rmse) if rmse is not None else None,
            "last_observed_value": last_observed_value,
            "forecast_end_value": forecast_end_value,
            "baseline_rmse": float(baseline["rmse"]),
            "baseline_label": baseline["label"],
            "series_min": float(np.nanmin(clean)) if len(clean) > 0 else 0.0,
            "series_std": float(np.nanstd(clean, ddof=1)) if len(clean) > 1 else 0.0,
            "series_mean": float(np.nanmean(clean)) if len(clean) > 0 else 0.0,
        }
        # Route to ets vs holt_winters spec by technique_id.
        _tid = str(ctx.technique_id or "").lower()
        if _tid == "ets":
            interp = build_interpretation("ets", _interp_dict)
        elif _tid in ("holt_winters", "hw"):
            interp = build_interpretation("holt_winters", _interp_dict)
        else:
            # default ets_hw alias falls to holt_winters spec
            interp = build_interpretation("holt_winters", _interp_dict)

        return make_response(
            ctx,
            tables=[forecast_table, fitted_table, summary_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "model": model_desc,
                "trend": trend_param,
                "seasonal": seasonal_param,
                "seasonal_periods": period if seasonal_param else None,
                "damped_trend": damped,
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "rmse": round(rmse, 4) if rmse else None,
                "horizon": horizon,
                "alpha": round(_alpha, 6) if _alpha is not None else None,
                "beta": round(_beta, 6) if _beta is not None else None,
                "gamma": round(_gamma, 6) if _gamma is not None else None,
                "phi": round(_phi, 6) if _phi is not None else None,
                "last_observed_value": last_observed_value,
                "forecast_end_value": forecast_end_value,
                "baseline_rmse": round(float(baseline["rmse"]), 4),
                "baseline_label": baseline["label"],
                **format_significance_disclosure(
                    test_name=(
                        "ETS prediction interval (t-critical on residual std)"
                    ),
                    critical_value_formula=(
                        "forecast ± t(1-α/2, T - n_params) · resid_std · "
                        "sqrt(h). DoF-aware; NOT autocorrelation-aware — "
                        "if residuals retain serial correlation, coverage is "
                        "optimistic. Consider a rolling-origin bootstrap re-fit."
                    ),
                    ac_corrected=False,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"ETS/Holt-Winters failed: {e}",
            error_fixes=[
                "Ensure the data is numeric.",
                "For multiplicative models, all values must be positive.",
                "Try setting trend=None or seasonal=None for simpler models.",
                "Check that the seasonal period is correct.",
            ],
        )


def _describe_model(trend, seasonal, damped, period):
    """Build a human-readable model name."""
    parts = []
    if trend is None and seasonal is None:
        return "Simple Exponential Smoothing (SES)"
    if trend and seasonal is None:
        name = "Holt's Linear" if not damped else "Damped Holt's"
        return f"{name} ({trend}. trend)"
    if trend and seasonal:
        name = "Holt-Winters"
        if damped:
            name = "Damped " + name
        return f"{name} ({trend}. trend, {seasonal}. seasonal, period={period})"
    if seasonal and trend is None:
        return f"Seasonal Exponential Smoothing ({seasonal}. seasonal, period={period})"
    return "ETS"
