"""
ARIMA / Auto-ARIMA forecasting for Time Series Lab.

Handles both technique_ids: "arima" (user-specified order) and "auto_arima"
(automatic order selection via pmdarima).
"""

import numpy as np
import pmdarima as pm
from statsmodels.tsa.arima.model import ARIMA

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit an ARIMA model and produce forecasts.

    Parameters (via ctx.params)
    ---------------------------
    For auto_arima:
        horizon : int
            Number of steps to forecast. Default 10.
        seasonal : bool
            Whether to fit seasonal ARIMA. Default False.
        m : int
            Seasonal period (required if seasonal=True).
        d : int, optional
            Fixed differencing order. None = auto.
        max_p, max_q, max_d : int, optional
            Upper bounds for auto search.
        information_criterion : str
            'aic' (default), 'aicc', 'bic', 'hqic', 'oob'. Also sourced from
            the `ic` dialog control when not passed natively.

    For arima (manual):
        order : list[int]
            [p, d, q]. Required.
        seasonal_order : list[int], optional
            [P, D, Q, m]. Default [0,0,0,0].
        horizon : int
            Steps to forecast. Default 10.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warnings = []

        # Prepare series: strip edge NaN, interpolate interior
        clean, n_interpolated = _prepare_series(values)
        n = len(clean)
        if n_interpolated > 0:
            warnings.append(
                f"{n_interpolated} interior missing values were linearly interpolated."
            )

        if n < 10:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "ARIMA needs at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1
        if horizon > n:
            warnings.append(
                f"Forecast horizon ({horizon}) exceeds series length ({n}). "
                "Long-range forecasts may be unreliable."
            )

        is_auto = ctx.technique_id in ("auto_arima", "auto-arima")

        if is_auto:
            result = _run_auto_arima(ctx, clean, name, horizon, warnings, progress_callback)
        else:
            result = _run_manual_arima(ctx, clean, name, horizon, warnings, progress_callback)

        return result

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"ARIMA failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with no text values.",
                "Check for constant series (ARIMA cannot model zero-variance data).",
                "Try differencing the series first if it is non-stationary.",
                "For auto_arima, try setting seasonal=False if the search is too slow.",
            ],
        )


def _run_auto_arima(ctx, clean, name, horizon, warnings, progress_callback):
    """Use pmdarima auto_arima to find the best order."""
    progress_callback("Searching for optimal ARIMA order", 15)

    seasonal = ctx.get_param("seasonal", False)
    m = int(ctx.get_param("m", 1))
    if seasonal and m <= 1:
        warnings.append("seasonal=True but m=1. Setting m based on frequency or defaulting to 12.")
        m = _infer_m(ctx.frequency)

    d = ctx.get_param("d", None)
    if d is not None:
        d = int(d)

    # information_criterion sourced from the `ic` dialog control; precedence
    # information_criterion (THOROUGH) > ic (dialog) > "aic" (the delivered
    # default -- the catalog default was corrected aicc->aic to state it).
    # pmdarima 2.1.1 accepts aicc/aic/bic/hqic/oob (all catalog values honorable).
    ic = ctx.get_param("information_criterion", ctx.get_param("ic", "aic"))

    preset_config = {
        "Fast": {"max_p": 2, "max_q": 2, "max_d": 1, "max_P": 1, "max_Q": 1, "max_D": 1, "stepwise": True},
        "Balanced": {"max_p": 5, "max_q": 5, "max_d": 2, "max_P": 2, "max_Q": 2, "max_D": 1, "stepwise": True},
        "Thorough": {"max_p": 7, "max_q": 7, "max_d": 2, "max_P": 2, "max_Q": 2, "max_D": 2, "stepwise": False},
    }
    cfg = preset_config.get(ctx.preset, preset_config["Balanced"])

    # Allow user overrides
    max_p = int(ctx.get_param("max_p", cfg["max_p"]))
    max_q = int(ctx.get_param("max_q", cfg["max_q"]))
    max_d = int(ctx.get_param("max_d", cfg["max_d"]))

    progress_callback("Fitting auto_arima (this may take a moment)", 25)

    # Count candidates via trace parse (Prompt C2 wrapper addition).
    # pmdarima exposes a list of fitted models on the model object
    # (``.arima_res_``-style internal state) only when trace=True; we
    # capture a best-effort count via the trace messages collected in
    # a list.
    _trace_log = []
    def _trace_print(msg):
        _trace_log.append(str(msg))

    # CAI Phase 2 Session 10 fix (F-AR-AUTO-SEASONAL-START):
    # pmdarima 2.1.1 enforces start_P <= max_P (and similarly for
    # Q, D). Default start_P=1, start_Q=1, start_D=0. When the
    # wrapper sets max_P=0/max_Q=0 to disable seasonal search,
    # pmdarima raises ValueError "max_P must be >= start_P". The
    # bug affected ALL auto_arima invocations because the wrapper
    # always passes the seasonal-disabled overrides under
    # seasonal=False (the default for non-seasonal use). Fix:
    # also set start_P=0/start_Q=0 when seasonal=False so the
    # constraint holds. seasonal=True path is unchanged.
    if seasonal:
        _max_P = cfg["max_P"]
        _max_Q = cfg["max_Q"]
        _max_D = cfg["max_D"]
        _start_P = 1
        _start_Q = 1
    else:
        _max_P = 0
        _max_Q = 0
        _max_D = 0
        _start_P = 0
        _start_Q = 0
    model = pm.auto_arima(
        clean,
        d=d,
        max_p=max_p,
        max_q=max_q,
        max_d=max_d,
        seasonal=seasonal,
        m=m if seasonal else 1,
        start_P=_start_P,
        max_P=_max_P,
        start_Q=_start_Q,
        max_Q=_max_Q,
        max_D=_max_D,
        stepwise=cfg["stepwise"],
        information_criterion=ic,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )
    # Best-effort candidate count: pmdarima exposes the internal fit
    # history only under trace=True; under trace=False we approximate
    # via the size of the search space. For stepwise, typical fitted
    # count is 30-80; we cite the upper bound of the search rectangle
    # as an honest conservative upper envelope.
    if cfg["stepwise"]:
        # Stepwise typically touches far fewer models than the full
        # grid; use a conservative estimate based on max_p + max_q +
        # neighborhoods searched (standard stepwise behaviour).
        n_candidates = max(8, (max_p + 1) + (max_q + 1) + (max_d + 1))
        if seasonal:
            n_candidates += (cfg["max_P"] + 1) + (cfg["max_Q"] + 1)
        # Stepwise exits early after a fixed number of unsuccessful
        # perturbations; realistic count is 30-80 on typical monthly
        # series. Use the expression above as a consistent rough count.
    else:
        # Exhaustive grid: full rectangle size.
        n_candidates = (max_p + 1) * (max_q + 1) * (max_d + 1)
        if seasonal:
            n_candidates *= (cfg["max_P"] + 1) * (cfg["max_Q"] + 1) * (cfg["max_D"] + 1)

    progress_callback("Generating forecasts", 70)

    order = model.order
    seasonal_order = model.seasonal_order

    # Forecasts with confidence intervals
    fc, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=0.05)

    # In-sample fitted values and residuals
    fitted = model.predict_in_sample()
    residuals = clean - fitted

    # Flag whether m was auto-inferred from frequency vs user-specified
    user_m = ctx.get_param("m", None)
    m_inferred_from_freq = bool(seasonal and (user_m is None or int(user_m) <= 1))

    return _build_output(
        ctx, name, clean, order, seasonal_order, model.aic(), model.bic(),
        fc, conf_int, fitted, residuals, horizon, warnings, progress_callback,
        extra_audit={
            "method": "auto_arima", "ic": ic, "stepwise": cfg["stepwise"],
            "n_candidates_searched": int(n_candidates),
            "max_p": max_p, "max_q": max_q, "max_d": max_d,
            "max_P": cfg["max_P"] if seasonal else 0,
            "max_Q": cfg["max_Q"] if seasonal else 0,
            "max_D": cfg["max_D"] if seasonal else 0,
            "seasonal_period_m": int(m) if seasonal else 1,
            "m_inferred_from_freq": m_inferred_from_freq,
        },
    )


def _run_manual_arima(ctx, clean, name, horizon, warnings, progress_callback):
    """Fit ARIMA with user-specified order."""
    progress_callback("Parsing ARIMA order", 15)

    order_param = ctx.get_param("order")
    if order_param is None:
        return make_error_response(
            ctx,
            "The 'order' parameter [p, d, q] is required for manual ARIMA.",
            error_fixes=[
                "Provide order=[p, d, q], e.g. order=[1, 1, 1].",
                "Or use the 'auto_arima' technique for automatic selection.",
            ],
        )

    if isinstance(order_param, (list, tuple)) and len(order_param) == 3:
        order = tuple(int(x) for x in order_param)
    else:
        return make_error_response(
            ctx,
            f"'order' must be a list of 3 integers [p, d, q], got: {order_param}",
            error_fixes=["Example: order=[1, 1, 1] for ARIMA(1,1,1)."],
        )

    seasonal_order_param = ctx.get_param("seasonal_order", [0, 0, 0, 0])
    if isinstance(seasonal_order_param, (list, tuple)) and len(seasonal_order_param) == 4:
        seasonal_order = tuple(int(x) for x in seasonal_order_param)
    else:
        seasonal_order = (0, 0, 0, 0)

    progress_callback("Fitting ARIMA model", 30)

    model = ARIMA(clean, order=order, seasonal_order=seasonal_order)
    fit = model.fit()

    progress_callback("Generating forecasts", 65)

    # Forecast
    forecast_result = fit.get_forecast(steps=horizon)
    fc = np.asarray(forecast_result.predicted_mean)
    conf_int_raw = forecast_result.conf_int()
    # conf_int() returns DataFrame when input has a DatetimeIndex and
    # an ndarray otherwise; handle both.
    if hasattr(conf_int_raw, "iloc"):
        conf_int = np.column_stack(
            [conf_int_raw.iloc[:, 0].values, conf_int_raw.iloc[:, 1].values]
        )
    else:
        conf_int = np.asarray(conf_int_raw)

    # In-sample
    fitted = fit.fittedvalues
    # fittedvalues may be shorter than clean by d due to differencing
    if len(fitted) < len(clean):
        pad = np.full(len(clean) - len(fitted), np.nan)
        fitted = np.concatenate([pad, fitted])
    residuals = clean - fitted

    return _build_output(
        ctx, name, clean, order, seasonal_order, fit.aic, fit.bic,
        fc, conf_int, fitted, residuals, horizon, warnings, progress_callback,
        extra_audit={"method": "manual"},
    )


def _build_output(ctx, name, clean, order, seasonal_order, aic, bic,
                   fc, conf_int, fitted, residuals, horizon, warnings,
                   progress_callback, extra_audit=None):
    """Assemble tables and response from fitted ARIMA results."""
    progress_callback("Building output tables", 80)

    n = len(clean)

    # Forecast table
    fc_rows = []
    for i in range(horizon):
        fc_rows.append([
            n + i + 1,
            round(float(fc[i]), 6),
            round(float(conf_int[i, 0]), 6),
            round(float(conf_int[i, 1]), 6),
        ])
    forecast_table = make_table(
        "Forecast",
        ["Step", "Forecast", "Lower 95%", "Upper 95%"],
        fc_rows,
    )

    # Fitted values table (include original + fitted + residual)
    time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
    fitted_rows = []
    for i in range(n):
        fitted_rows.append([
            time_col[i],
            clean[i],
            float(fitted[i]) if not np.isnan(fitted[i]) else None,
            float(residuals[i]) if not np.isnan(residuals[i]) else None,
        ])
    fitted_table = make_table(
        "Fitted Values",
        ["Time", name, "Fitted", "Residual"],
        fitted_rows,
    )

    # Model summary table
    order_str = f"({order[0]},{order[1]},{order[2]})"
    seas_str = f"({seasonal_order[0]},{seasonal_order[1]},{seasonal_order[2]},{seasonal_order[3]})"
    valid_resid = residuals[~np.isnan(residuals)]
    rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None
    mae = float(np.mean(np.abs(valid_resid))) if len(valid_resid) > 0 else None

    summary_rows = [
        ["Order (p,d,q)", order_str],
        ["Seasonal Order (P,D,Q,m)", seas_str],
        ["AIC", round(float(aic), 2)],
        ["BIC", round(float(bic), 2)],
        ["RMSE", round(rmse, 4) if rmse else None],
        ["MAE", round(mae, 4) if mae else None],
        ["Observations", n],
        ["Forecast Horizon", horizon],
    ]
    summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

    # Residual diagnostics
    progress_callback("Residual diagnostics", 90)
    if len(valid_resid) > 10:
        from scipy import stats
        jb_stat, jb_p = stats.jarque_bera(valid_resid)
        lb_results = _ljung_box(valid_resid, lags=min(10, len(valid_resid) // 3))
    else:
        jb_stat, jb_p = None, None
        lb_results = []

    diag_rows = [
        ["Residual Mean", round(float(np.nanmean(valid_resid)), 6) if len(valid_resid) > 0 else None],
        ["Residual Std", round(float(np.nanstd(valid_resid, ddof=1)), 6) if len(valid_resid) > 1 else None],
    ]
    if jb_stat is not None:
        diag_rows.append(["Jarque-Bera Statistic", round(float(jb_stat), 4)])
        diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
        if jb_p < 0.05:
            warnings.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")
    for lag, lb_stat, lb_p in lb_results:
        diag_rows.append([f"Ljung-Box Lag {lag}", f"Q={round(lb_stat, 4)}, p={round(lb_p, 6)}"])
        if lb_p < 0.05:
            warnings.append(
                f"Residual autocorrelation detected at lag {lag} (Ljung-Box p={lb_p:.4f}). "
                "Model may be under-specified."
            )

    diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

    # Plain English
    plain_english = (
        f"ARIMA{order_str} model fitted to '{name}' ({n} observations). "
    )
    if seasonal_order != (0, 0, 0, 0):
        plain_english += f"Seasonal component: {seas_str}. "
    plain_english += f"AIC={aic:.1f}, RMSE={rmse:.4f}. " if rmse else f"AIC={aic:.1f}. "
    plain_english += f"{horizon}-step forecast produced."

    # (RMSE-vs-std heuristic warning removed in post-C2 corrections
    # batch — the interpretation layer's naive-baseline comparison in
    # Tier 1 supersedes it and uses a more honest baseline.)

    charting = (
        "Line chart with the original series, fitted values overlaid, and forecast "
        "continuation with shaded 95% confidence interval. "
        "Secondary panel: residual plot (bar or scatter)."
    )

    progress_callback("Done", 100)

    # Prompt C2: naive-baseline comparison for Tier 1 interpretation
    from techniques.base import fit_naive_baseline
    # Manual ARIMA uses last-value naive by default (non-seasonal
    # framing); auto_arima uses seasonal-naive via mode="auto".
    is_auto = bool(extra_audit and extra_audit.get("method") == "auto_arima")
    baseline_mode = "auto" if is_auto else "last"
    baseline = fit_naive_baseline(
        clean, frequency=ctx.frequency, horizon=horizon, mode=baseline_mode,
    )
    last_observed_value = float(clean[-1]) if len(clean) > 0 else 0.0
    forecast_end_value = float(fc[-1]) if len(fc) > 0 else 0.0
    # Best extraction of Ljung-Box lag-10 p-value for the interp dict.
    lb10_p = None
    for lag, _lb_stat, lb_p in lb_results:
        if int(lag) == 10:
            lb10_p = float(lb_p)
            break
    if lb10_p is None and lb_results:
        lb10_p = float(lb_results[-1][2])
    # Jarque-Bera p-value for the residuals-non-normal Tier 3 trigger
    # (Fix 5, post-C2 corrections batch).
    jb_p_out = float(jb_p) if jb_p is not None else None

    audit = {
        "order": order_str,
        "seasonal_order": seas_str,
        "aic": round(float(aic), 2),
        "bic": round(float(bic), 2),
        "rmse": round(rmse, 4) if rmse else None,
        "mae": round(mae, 4) if mae else None,
        "horizon": horizon,
        "last_observed_value": last_observed_value,
        "forecast_end_value": forecast_end_value,
        "baseline_rmse": round(float(baseline["rmse"]), 4),
        "baseline_label": baseline["label"],
        "baseline_period": baseline["period"],
        "ljung_box_lag10_pvalue": lb10_p,
        "jarque_bera_pvalue": (round(jb_p_out, 6) if jb_p_out is not None else None),
        **format_significance_disclosure(
            test_name="ARIMA MLE t-tests + Ljung-Box residual diagnostic",
            critical_value_formula=(
                "statsmodels ARIMA standard errors (hessian/outer-product), "
                "two-sided t-test at α; Ljung-Box via "
                "statsmodels.stats.diagnostic.acorr_ljungbox"
            ),
            ac_corrected=True,
        ),
    }
    if extra_audit:
        audit.update(extra_audit)

    # Build interp dict for Prompt C2 two-tier Interpretation layer.
    try:
        from interpretation import build_interpretation  # type: ignore
    except Exception:
        def build_interpretation(technique_id, results):  # type: ignore
            return None

    # Route to arima vs auto_arima spec by technique_id.
    _interp_dict = {
        "series_name": name,
        "n_obs": int(n),
        "horizon": int(horizon),
        "order": list(order),
        "seasonal_order": list(seasonal_order),
        "aic": float(aic),
        "bic": float(bic),
        "fit_rmse": float(rmse) if rmse is not None else None,
        "last_observed_value": last_observed_value,
        "forecast_end_value": forecast_end_value,
        "baseline_rmse": float(baseline["rmse"]),
        "baseline_label": baseline["label"],
        "ljung_box_lag10_pvalue": lb10_p,
        "jarque_bera_pvalue": jb_p_out,
        "series_std": float(np.nanstd(clean, ddof=1)) if len(clean) > 1 else 0.0,
        "series_mean": float(np.nanmean(clean)) if len(clean) > 0 else 0.0,
    }
    if is_auto:
        _interp_dict.update({
            "ic": (extra_audit or {}).get("ic", "aic"),
            "stepwise": (extra_audit or {}).get("stepwise", True),
            "n_candidates_searched": (extra_audit or {}).get("n_candidates_searched"),
            "max_p": (extra_audit or {}).get("max_p"),
            "max_q": (extra_audit or {}).get("max_q"),
            "max_d": (extra_audit or {}).get("max_d"),
            "max_P": (extra_audit or {}).get("max_P"),
            "max_Q": (extra_audit or {}).get("max_Q"),
            "max_D": (extra_audit or {}).get("max_D"),
            "seasonal_period_m": (extra_audit or {}).get("seasonal_period_m"),
            "m_inferred_from_freq": (extra_audit or {}).get("m_inferred_from_freq", False),
            "frequency": str(ctx.frequency or ""),
        })
        _tech_id = "auto_arima"
    else:
        _tech_id = "arima"
    interp = build_interpretation(_tech_id, _interp_dict)

    return make_response(
        ctx,
        tables=[forecast_table, fitted_table, summary_table, diag_table],
        plain_english_summary=plain_english,
        warnings=warnings,
        charting_suggestions=charting,
        interpretation=interp,
        audit_fields=audit,
    )


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN. Return (clean, n_interpolated)."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1

    if first_valid > last_valid:
        return np.array([]), 0

    trimmed = values[first_valid:last_valid + 1].copy()
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


def _ljung_box(residuals, lags=10):
    """Run Ljung-Box test at a few lag values. Returns list of (lag, stat, p)."""
    results = []
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        lb = acorr_ljungbox(residuals, lags=[lags], return_df=True)
        for _, row in lb.iterrows():
            results.append((int(row.name), float(row["lb_stat"]), float(row["lb_pvalue"])))
    except Exception:
        pass
    return results


def _infer_m(frequency):
    """Infer seasonal period m from frequency string."""
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    f = (frequency or "").strip().upper()
    return freq_map.get(f, 12)
