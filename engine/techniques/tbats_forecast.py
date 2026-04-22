"""
TBATS / BATS forecasting for Time Series Lab.

TBATS (Trigonometric seasonality, Box-Cox, ARMA errors, Trend, Seasonal)
and BATS (the non-trigonometric sibling) handle MULTIPLE seasonalities
natively (e.g., daily retail with weekly=7 and annual=365.25 cycles).

TBATS uses trigonometric representation of seasonal states, which
lets it fit non-integer periods like 365.25 directly. BATS uses
classical seasonal-dummy representation and requires integer periods.

This wrapper ships both; `use_trigonometric=True` (default) selects
TBATS; `use_trigonometric=False` selects BATS.

Backend: the ``tbats`` Python package (Skorupa; mirrors R
``forecast::tbats`` conventions). A sklearn compatibility shim is
applied at import time because tbats 1.1.3 calls
``sklearn.utils.validation.check_array(force_all_finite=True)`` but
sklearn 1.6+ renamed the argument to ``ensure_all_finite``.
"""

from __future__ import annotations

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    fit_naive_baseline,
    format_significance_disclosure,
)


# ---------------------------------------------------------------------------
# sklearn / tbats compatibility shim
# ---------------------------------------------------------------------------
#
# tbats 1.1.3 passes ``force_all_finite`` to sklearn's check_array;
# sklearn 1.6 renamed this argument to ``ensure_all_finite`` and
# sklearn 1.8+ raises TypeError on the old name. Apply a process-wide
# translating shim once at wrapper import time. This is scoped to the
# check_array call; no other sklearn behavior changes.
def _install_tbats_sklearn_shim():
    try:
        import sklearn.utils.validation as _v
        _orig = _v.check_array
        if getattr(_orig, "_tbats_shim_installed", False):
            return
        import inspect
        try:
            sig = inspect.signature(_orig)
            if "force_all_finite" in sig.parameters:
                # Old sklearn still accepts it; no shim needed.
                return
        except (TypeError, ValueError):
            pass

        def _compat_check_array(*args, **kwargs):
            if "force_all_finite" in kwargs:
                kwargs["ensure_all_finite"] = kwargs.pop("force_all_finite")
            return _orig(*args, **kwargs)

        _compat_check_array._tbats_shim_installed = True  # type: ignore[attr-defined]
        _v.check_array = _compat_check_array
    except Exception:
        # Best-effort; if sklearn is missing entirely, tbats import
        # will raise a clearer error than our shim would.
        pass


_install_tbats_sklearn_shim()

try:
    from tbats import TBATS, BATS
    _TBATS_AVAILABLE = True
except Exception:
    TBATS = None
    BATS = None
    _TBATS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Preset configuration
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast":     {"use_box_cox": False, "use_arma_errors": False,
                 "use_damped_trend": False, "n_jobs": 1},
    "Balanced": {"use_box_cox": None,  "use_arma_errors": None,
                 "use_damped_trend": None,  "n_jobs": 1},
    "Thorough": {"use_box_cox": None,  "use_arma_errors": None,
                 "use_damped_trend": None,  "n_jobs": 1},
}


# ---------------------------------------------------------------------------
# Seasonal-period auto-inference (Refinement 2)
# ---------------------------------------------------------------------------

# Simple pandas-freq-code → default seasonal_periods map. Returns a
# list of floats. Non-listed frequency codes yield [] (no seasonality
# inferred).
_FREQ_TO_PERIODS = {
    "D":  [7.0, 365.25],
    "B":  [5.0, 260.0],
    "W":  [52.179],
    "M":  [12.0],
    "MS": [12.0],
    "Q":  [4.0],
    "QS": [4.0],
    "Y":  [],
    "A":  [],
    "H":  [24.0, 24.0 * 7, 24.0 * 365.25],
}


def _infer_seasonal_periods(ctx) -> tuple[list, str]:
    """Infer default seasonal periods from ctx.frequency.

    Returns (periods, source_label):
      - "user-specified": ctx.params["seasonal_periods"] provided
      - "auto-inferred": frequency code recognized; default periods used
      - "no-seasonality-inferred": frequency unknown / missing
    """
    freq_code = str(getattr(ctx, "frequency", "") or "").strip().upper()
    # Strip pandas-style integer prefix (e.g., "2D" → "D") before lookup
    # because multi-interval frequencies don't have clean default periods.
    while freq_code and freq_code[0].isdigit():
        freq_code = freq_code[1:]
    if freq_code in _FREQ_TO_PERIODS:
        periods = list(_FREQ_TO_PERIODS[freq_code])
        if not periods:
            return [], "no-seasonality-inferred"
        return periods, "auto-inferred"
    return [], "no-seasonality-inferred"


def _prepare_series(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Strip edge NaN; linearly interpolate interior."""
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
    Fit a TBATS or BATS model to the primary series.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int, optional
        Forecast steps. Default 10.
    seasonal_periods : list[float] | None, optional
        Explicit seasonal periods. If None, inferred from ctx.frequency.
    use_trigonometric : bool, optional
        True → TBATS (default); False → BATS.
    use_box_cox : bool | None, optional
        None lets the library choose via AIC.
    use_arma_errors : bool | None, optional
    use_damped_trend : bool | None, optional
    """
    try:
        progress_callback("Validating inputs", 5)

        if not _TBATS_AVAILABLE:
            return make_error_response(
                ctx,
                "The `tbats` Python package is not installed.",
                error_fixes=[
                    "Install via `pip install tbats`.",
                    "If already installed, the sklearn-compatibility "
                    "shim may have failed — check Python environment.",
                ],
            )

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(np.asarray(values, dtype=float))
        n = int(len(clean))
        if n_interp > 0:
            warn_list.append(
                f"{n_interp} interior missing values linearly interpolated."
            )
        if n < 8:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                f"TBATS needs at least 8.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # ── Seasonal period resolution ────────────────────────────────
        user_periods = ctx.get_param("seasonal_periods", None)
        if user_periods is not None:
            try:
                requested_periods = [float(p) for p in user_periods]
                requested_periods = [p for p in requested_periods if p > 0]
                periods_source = "user-specified"
            except (TypeError, ValueError):
                requested_periods = []
                periods_source = "user-specified"
                warn_list.append(
                    "seasonal_periods param could not be parsed as a list "
                    "of positive numbers; falling back to no-seasonality."
                )
        else:
            requested_periods, periods_source = _infer_seasonal_periods(ctx)

        # Filter periods that are too long for the sample.
        # TBATS requires n >= 2 × period to estimate a seasonal state.
        seasonal_periods_used = []
        seasonal_periods_filtered = []
        for p in requested_periods:
            min_needed = int(np.ceil(2.0 * float(p)))
            if n >= min_needed:
                seasonal_periods_used.append(float(p))
            else:
                seasonal_periods_filtered.append({
                    "period": float(p),
                    "reason": f"requires at least {min_needed} observations, only {n} available",
                })

        use_trigonometric = bool(ctx.get_param("use_trigonometric", True))
        use_box_cox = ctx.get_param("use_box_cox", cfg["use_box_cox"])
        use_arma_errors = ctx.get_param("use_arma_errors", cfg["use_arma_errors"])
        use_damped_trend = ctx.get_param("use_damped_trend", cfg["use_damped_trend"])
        n_jobs = int(ctx.get_param("n_jobs", cfg["n_jobs"]))

        # BATS cannot fit non-integer periods natively; round and disclose.
        bats_rounding_applied = []
        if not use_trigonometric and seasonal_periods_used:
            rounded = []
            for p in seasonal_periods_used:
                ip = int(round(p))
                if ip != p:
                    bats_rounding_applied.append({"original": p, "rounded": ip})
                rounded.append(float(ip))
            seasonal_periods_used = rounded

        # Build estimator.
        EstimatorCls = TBATS if use_trigonometric else BATS
        # tbats wants None for empty seasonal list (not []) on some versions;
        # normalize empty → None.
        sp_arg = seasonal_periods_used if seasonal_periods_used else None

        progress_callback(
            f"Fitting {'TBATS' if use_trigonometric else 'BATS'} "
            f"(periods={seasonal_periods_used})", 20
        )
        try:
            estimator = EstimatorCls(
                seasonal_periods=sp_arg,
                use_box_cox=use_box_cox,
                use_arma_errors=use_arma_errors,
                use_damped_trend=use_damped_trend,
                n_jobs=n_jobs,
            )
            fitted = estimator.fit(clean)
        except Exception as e:
            return make_error_response(
                ctx,
                f"{'TBATS' if use_trigonometric else 'BATS'} fit failed: {e}",
                error_fixes=[
                    "Check that the series is numeric and positive "
                    "(required if use_box_cox=True).",
                    "Try reducing seasonal_periods to the strongest cycle.",
                    "Try use_box_cox=False if the series contains "
                    "non-positive values.",
                ],
            )

        progress_callback("Generating forecasts", 70)

        # Forecast with 95% confidence interval.
        try:
            fc_values, conf_info = fitted.forecast(
                steps=horizon, confidence_level=0.95
            )
            fc_values = np.asarray(fc_values, dtype=float)
            fc_lower = np.asarray(conf_info.get("lower_bound"), dtype=float) if isinstance(conf_info, dict) else None
            fc_upper = np.asarray(conf_info.get("upper_bound"), dtype=float) if isinstance(conf_info, dict) else None
        except Exception:
            fc_values = np.asarray(fitted.forecast(steps=horizon), dtype=float)
            fc_lower = None
            fc_upper = None

        # Fit diagnostics.
        y_hat = np.asarray(fitted.y_hat, dtype=float)
        if len(y_hat) != n:
            aligned_n = min(len(y_hat), n)
            resid = clean[-aligned_n:] - y_hat[-aligned_n:]
        else:
            resid = clean - y_hat
        fit_rmse = float(np.sqrt(np.mean(resid ** 2))) if len(resid) else None

        # Extract model parameters.
        params = fitted.params
        components = params.components
        box_cox_lambda = float(params.box_cox_lambda) if (
            components.use_box_cox and params.box_cox_lambda is not None
        ) else None
        alpha = float(params.alpha) if params.alpha is not None else None
        beta_val = float(getattr(params, "beta", 0.0) or 0.0) if components.use_trend else None
        gamma_params = getattr(params, "gamma_params", None)
        if gamma_params is None:
            gamma_list = None
        else:
            try:
                gamma_list = [float(g) for g in np.asarray(gamma_params)]
            except Exception:
                gamma_list = None
        # Use explicit None-checks to avoid numpy's "truth value of
        # empty array is ambiguous" error on zero-length arrays.
        _ar = getattr(params, "ar_coefs", None)
        ar_coefs = list(_ar) if _ar is not None else []
        _ma = getattr(params, "ma_coefs", None)
        ma_coefs = list(_ma) if _ma is not None else []
        _harm = getattr(components, "seasonal_harmonics", None)
        harmonics = list(_harm) if _harm is not None else []
        if not use_trigonometric:
            harmonics = []  # BATS has no harmonics concept

        aic = float(fitted.aic) if fitted.aic is not None else None
        # Approximate effective parameters: trend (1 or 2) + seasonal
        # state block + ARMA coefficients + harmonics params.
        try:
            n_params_est = 1  # always fitting level
            if components.use_trend:
                n_params_est += 1
                if components.use_damped_trend:
                    n_params_est += 1
            if use_trigonometric:
                n_params_est += 2 * sum(int(h) for h in harmonics)
            else:
                n_params_est += sum(int(p) for p in seasonal_periods_used)
            n_params_est += len(ar_coefs) + len(ma_coefs)
            if box_cox_lambda is not None:
                n_params_est += 1
        except Exception:
            n_params_est = None

        progress_callback("Building output", 90)

        # ── Output tables ─────────────────────────────────────────────
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else list(range(1, n + 1))

        # Forecast table with intervals.
        fc_rows = []
        for i in range(horizon):
            row = [i + 1, round(float(fc_values[i]), 6)]
            if fc_lower is not None and fc_upper is not None:
                row.append(round(float(fc_lower[i]), 6))
                row.append(round(float(fc_upper[i]), 6))
            fc_rows.append(row)
        fc_cols = ["Step", "Forecast"] + (["Lower 95%", "Upper 95%"] if fc_lower is not None else [])
        fc_table = make_table("Forecast", fc_cols, fc_rows)

        # Model summary.
        model_name = "TBATS" if use_trigonometric else "BATS"
        summary_rows = [
            ["Model", model_name],
            ["Observations", n],
            ["Horizon", horizon],
            ["Seasonal periods used", str(seasonal_periods_used) if seasonal_periods_used else "none"],
            ["Seasonal periods filtered", str(seasonal_periods_filtered) if seasonal_periods_filtered else "none"],
            ["Seasonal periods source", periods_source],
            ["Use trigonometric", use_trigonometric],
            ["Use Box-Cox (fit)", bool(components.use_box_cox)],
            ["Box-Cox lambda", round(box_cox_lambda, 6) if box_cox_lambda is not None else None],
            ["Use ARMA errors (fit)", bool(components.use_arma_errors)],
            ["Use damped trend (fit)", bool(components.use_damped_trend)],
            ["Alpha (level)", round(alpha, 6) if alpha is not None else None],
            ["Beta (trend)", round(beta_val, 6) if beta_val is not None else None],
            ["Gamma params", str(gamma_list) if gamma_list is not None else "n/a"],
            ["Harmonics per period", str(harmonics) if harmonics else "n/a"],
            ["AR coefficients", str([round(c, 4) for c in ar_coefs]) if ar_coefs else "n/a"],
            ["MA coefficients", str([round(c, 4) for c in ma_coefs]) if ma_coefs else "n/a"],
            ["AIC", round(aic, 4) if aic is not None else None],
            ["n_params (approx)", n_params_est if n_params_est is not None else "n/a"],
            ["Fit RMSE", round(fit_rmse, 6) if fit_rmse is not None else None],
            ["BATS non-integer rounding", str(bats_rounding_applied) if bats_rounding_applied else "n/a"],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [fc_table, summary_table]

        # ── Naive baseline ────────────────────────────────────────────
        baseline_mode = "seasonal" if seasonal_periods_used else "last"
        baseline = fit_naive_baseline(
            clean, frequency=ctx.frequency, horizon=horizon, mode=baseline_mode
        )

        # ── Plain English summary ─────────────────────────────────────
        if seasonal_periods_used:
            sp_str = ", ".join(str(p) for p in seasonal_periods_used)
            season_desc = f" with seasonal periods [{sp_str}]"
        else:
            season_desc = " (non-seasonal fit)"
        plain = (
            f"{model_name} forecast of '{name}' ({n} observations{season_desc}). "
            f"Fit RMSE {fit_rmse:.4f} on the training sample; "
            f"{horizon}-step forecast produced."
        )
        if seasonal_periods_filtered:
            plain += f" Filtered periods (too long for series): {seasonal_periods_filtered}."

        charting = (
            "Line chart with the original series and the forecast continuation; "
            "overlay 95% prediction interval. For multi-seasonal runs, consider "
            "plotting the fitted seasonal components separately."
        )

        progress_callback("Done", 100)

        # ── Build audit + interpretation ──────────────────────────────
        last_observed_value = float(clean[-1])
        forecast_end_value = float(fc_values[-1]) if len(fc_values) else last_observed_value
        series_mean = float(np.mean(clean))
        series_std = float(np.std(clean, ddof=1)) if n > 1 else 0.0

        audit = {
            "series_name": name,
            "n_obs": n,
            "horizon": horizon,
            "model_type": model_name,
            "seasonal_periods_used": seasonal_periods_used,
            "seasonal_periods_filtered": seasonal_periods_filtered,
            "seasonal_periods_source": periods_source,
            "use_trigonometric": use_trigonometric,
            "use_box_cox_selected": bool(components.use_box_cox),
            "box_cox_lambda": round(box_cox_lambda, 6) if box_cox_lambda is not None else None,
            "use_arma_errors_selected": bool(components.use_arma_errors),
            "use_damped_trend_selected": bool(components.use_damped_trend),
            "alpha": round(alpha, 6) if alpha is not None else None,
            "beta": round(beta_val, 6) if beta_val is not None else None,
            "gamma_per_period": gamma_list,
            "n_harmonics_per_period": [int(h) for h in harmonics],
            "aic": round(aic, 4) if aic is not None else None,
            "n_params": n_params_est,
            "fit_rmse": round(fit_rmse, 6) if fit_rmse is not None else None,
            "baseline_rmse": round(float(baseline["rmse"]), 6),
            "baseline_label": baseline["label"],
            "last_observed_value": round(last_observed_value, 6),
            "forecast_end_value": round(forecast_end_value, 6),
            "series_mean": round(series_mean, 6),
            "series_std": round(series_std, 6),
            "bats_rounding_applied": bats_rounding_applied,
            **format_significance_disclosure(
                test_name=f"{model_name} 95% prediction interval",
                critical_value_formula=(
                    "forecast ± z(0.975) · posterior_std from tbats "
                    "package's forecast(steps, confidence_level=0.95). "
                    "Intervals widen with horizon and reflect one-step-"
                    "ahead forecast variance plus state uncertainty."
                ),
                ac_corrected=True,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("tbats_forecast", dict(audit))

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"TBATS / BATS forecast failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Check that seasonal_periods values are positive "
                "and fit within 2× the sample length.",
                "Try a different preset (Fast skips Box-Cox and ARMA).",
            ],
        )
