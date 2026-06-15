"""
Conformal Prediction Intervals for Time Series Lab.

Implements split conformal inference for time series forecasts.
Uses auto_arima residuals on a calibration set to construct
distribution-free prediction intervals.

IMPORTANT — scope of the coverage guarantee
============================================
Standard split conformal prediction (Vovk, Shafer & Vovk 2005;
Papadopoulos et al. 2002) gives distribution-free finite-sample
coverage guarantees when the data are **exchangeable** (e.g., iid).
Time-series residuals typically are NOT exchangeable — they exhibit
autocorrelation, regime shifts, and heteroskedasticity — so the
coverage guarantee does not transfer directly.

What this implementation actually provides:

  1. Rolling refit on the calibration set. The model is re-fit after
     each new observation in the calibration window, so the residuals
     used for the conformal quantile reflect the model's true one-step
     errors along that path. This is stronger than vanilla split
     conformal but still assumes the future conformity scores
     distribute like the calibration ones.

  2. An empirical quantile of the absolute residuals as the interval
     half-width. Valid under exchangeability; *approximately* valid
     when the series is close to stationary with short-range
     dependence; potentially mis-calibrated when the series has
     regime shifts or strong persistence.

If you need a formal coverage guarantee for time series, use an
adaptive / online conformal method (Lei et al. 2018, Gibbs & Candès
2021) — not implemented here. The output now emits a diagnostic
warning when calibration residuals show strong autocorrelation, which
is the most common scenario in which the intervals quietly
under-cover.
"""

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"cal_fraction": 0.2, "max_p": 2, "max_q": 2, "stepwise": True},
    "Balanced": {"cal_fraction": 0.25, "max_p": 5, "max_q": 5, "stepwise": True},
    "Thorough": {"cal_fraction": 0.3, "max_p": 7, "max_q": 7, "stepwise": False},
}


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN."""
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


def _infer_m(frequency):
    freq_map = {
        "D": 7, "B": 5, "W": 52, "M": 12, "MS": 12,
        "Q": 4, "QS": 4, "H": 24, "T": 60, "min": 60,
    }
    f = (frequency or "").strip().upper()
    return freq_map.get(f, 1)


def _cqr_intervals(X_train, y_train, X_cal, y_cal, X_eval, *, alpha, seed):
    """Conformalized Quantile Regression (Romano-Patterson-Candès 2019) —
    ENG-EXT-CONFORMAL-001 C1.

    Fit gradient-boosting quantile regressors at the lower (α/2) and upper
    (1−α/2) quantiles on the training set; conformalize against the
    calibration set via the CQR nonconformity score
    ``E_i = max(q̂_lo(x_i) − y_i, y_i − q̂_hi(x_i))``; the conformal
    adjustment is the ``⌈(n_cal+1)(1−α)⌉/n_cal`` empirical quantile of {E_i}
    (the same finite-sample index the split-conformal path uses); the
    interval is ``[q̂_lo(x) − Q, q̂_hi(x) + Q]``. Deterministic in ``seed``
    (the GBR ``random_state``).

    Returns a dict: ``lo``/``hi`` (eval intervals), ``Q`` (conformal
    adjustment), ``qlo_eval``/``qhi_eval`` (raw quantile predictions),
    ``glo``/``ghi`` (the fitted quantile regressors, for horizon recursion).
    """
    from sklearn.ensemble import GradientBoostingRegressor

    q_lo_level = alpha / 2.0
    q_hi_level = 1.0 - alpha / 2.0
    glo = GradientBoostingRegressor(
        loss="quantile", alpha=q_lo_level, random_state=seed).fit(X_train, y_train)
    ghi = GradientBoostingRegressor(
        loss="quantile", alpha=q_hi_level, random_state=seed).fit(X_train, y_train)
    qlo_cal = glo.predict(X_cal)
    qhi_cal = ghi.predict(X_cal)
    E = np.maximum(qlo_cal - y_cal, y_cal - qhi_cal)
    n_cal = len(y_cal)
    q_level = np.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal
    q_level = min(q_level, 1.0)
    Q = float(np.quantile(E, q_level))
    X_eval = np.atleast_2d(X_eval)
    qlo_eval = glo.predict(X_eval)
    qhi_eval = ghi.predict(X_eval)
    return {
        "lo": qlo_eval - Q, "hi": qhi_eval + Q, "Q": Q,
        "qlo_eval": qlo_eval, "qhi_eval": qhi_eval, "glo": glo, "ghi": ghi,
    }


def _enbpi_base_estimator(base_kind, seed):
    """Construct the EnbPI base estimator. ``"gbr"`` → gradient-boosting
    point regressor (deterministic, the default); ``"neural"`` → sklearn
    MLPRegressor (the S85 neural-forecast-PI fold-in — the same estimator
    family `nar_narx` uses; deterministic given random_state)."""
    if base_kind == "neural":
        from sklearn.neural_network import MLPRegressor
        return MLPRegressor(hidden_layer_sizes=(20, 10), random_state=seed,
                            max_iter=300, early_stopping=False)
    from sklearn.ensemble import GradientBoostingRegressor
    return GradientBoostingRegressor(random_state=seed)


def _enbpi_intervals(X_train, y_train, X_eval, *, alpha, base_kind,
                     n_resamplings, block_length, seed):
    """Ensemble Batch Prediction Intervals (Xu-Xie 2021) —
    ENG-EXT-CONFORMAL-001 C2.

    Block-bootstrap an ensemble of ``n_resamplings`` base models on the
    training rows (blocks of ``block_length`` preserve time dependence);
    for each training point i the leave-one-out / out-of-bag aggregate
    ``f^{−i}(x_i)`` is the mean of the models for which i is out-of-bag;
    residual ``ε_i = |y_i − f^{−i}(x_i)|``; the conformal width is the
    ``⌈(n+1)(1−α)⌉/n`` empirical quantile of {ε_i}; the test interval is
    ``ensemble_pred(x) ± w``. Deterministic in ``seed`` (a local
    ``RandomState`` drives the block bootstrap; the base estimator is
    seeded). Returns lo/hi/w/ensemble_pred.
    """
    X_train = np.asarray(X_train, dtype=np.float64)
    y_train = np.asarray(y_train, dtype=np.float64)
    X_eval = np.atleast_2d(np.asarray(X_eval, dtype=np.float64))
    n = len(y_train)
    rs = np.random.RandomState(seed)
    n_blocks = int(np.ceil(n / block_length))

    oob_pred = np.full((n, n_resamplings), np.nan)
    eval_pred = np.zeros((X_eval.shape[0], n_resamplings))
    models = []
    for b in range(n_resamplings):
        starts = rs.randint(0, max(1, n - block_length + 1), size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        model = _enbpi_base_estimator(base_kind, seed)
        model.fit(X_train[idx], y_train[idx])
        models.append(model)
        in_bag = np.zeros(n, dtype=bool)
        in_bag[np.unique(idx)] = True
        if np.any(~in_bag):
            oob_pred[~in_bag, b] = model.predict(X_train[~in_bag])
        eval_pred[:, b] = model.predict(X_eval)

    # leave-one-out aggregate (mean over models where i is OOB)
    fhat = np.array([
        np.nanmean(oob_pred[i]) if np.any(~np.isnan(oob_pred[i])) else y_train[i]
        for i in range(n)
    ])
    resid = np.abs(y_train - fhat)
    q_level = np.ceil((n + 1) * (1.0 - alpha)) / n
    q_level = min(q_level, 1.0)
    w = float(np.quantile(resid, q_level))
    pred = eval_pred.mean(axis=1)
    return {"lo": pred - w, "hi": pred + w, "w": w, "pred": pred, "models": models}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Split conformal prediction intervals.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    confidence_level : float
        Target coverage. Default 0.95. Sourced from the `coverage` dialog
        control when not passed natively (THOROUGH power-path) — same quantity
        and scale (the nominal interval LEVEL, e.g. 0.95; not the miscoverage
        alpha, whose 1 - level conversion stays internal).
    cal_fraction : float, optional
        Fraction of data used for calibration. Default from preset.
    seasonal : bool
        Seasonal ARIMA. Default False.
    m : int
        Seasonal period. Auto-inferred if not given.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")
        n = len(clean)

        if n < 30:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Conformal intervals need at least 30 (training + calibration).",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1
        # confidence_level = the target coverage, sourced from the `coverage`
        # dialog control (same quantity/scale -- the nominal interval LEVEL,
        # not the miscoverage alpha; the alpha = 1 - level conversion below
        # stays internal). Precedence: confidence_level (THOROUGH) > coverage
        # (dialog) > 0.95.
        conf_level = float(ctx.get_param("confidence_level",
                                         ctx.get_param("coverage", 0.95)))
        alpha = 1.0 - conf_level
        # Fix B Tier 1c-1: blank/absent -> default (byte-identical); literal
        # get_param keeps keys visible to catalog_key_alignment. seasonal/m
        # are read here but consumed only on the split (ARIMA) path.
        _se = ctx.get_param("seasonal", False)
        seasonal = _se if isinstance(_se, bool) else str(_se).strip().lower() in ("true", "1", "yes")
        _m_default = _infer_m(ctx.frequency)
        _m = ctx.get_param("m", _m_default)
        m_val = _m_default if (_m is None or str(_m).strip() == "") else int(_m)
        if seasonal and m_val <= 1:
            m_val = _infer_m(ctx.frequency)
            if m_val <= 1:
                m_val = 12

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        _cf = ctx.get_param("cal_fraction", preset_cfg["cal_fraction"])
        cal_frac = preset_cfg["cal_fraction"] if (_cf is None or str(_cf).strip() == "") else float(_cf)
        # CAI Phase 2 Session 21 fix (F-EU-CI-CALFRAC): explicit
        # range gate. Pre-fix, out-of-range cal_fraction silently
        # accepted.
        if not (0.0 < cal_frac < 1.0):
            return make_error_response(
                ctx,
                f"cal_fraction must be in (0, 1). Got {cal_frac}.",
                error_fixes=[
                    "Use a value strictly between 0 and 1 — typical "
                    "values are 0.1-0.3 for the calibration split. "
                    "The calibration set holds residuals used to "
                    "calibrate conformal coverage.",
                ],
            )
        if not (0.0 < conf_level < 1.0):
            return make_error_response(
                ctx,
                f"confidence_level must be in (0, 1). Got {conf_level}.",
                error_fixes=[
                    "Use a value strictly between 0 and 1; typical "
                    "choices are 0.90, 0.95 (default), 0.99.",
                ],
            )

        # ENG-EXT-CONFORMAL-001 C1 — method selector (ADDITIVE). Default
        # "split" = the existing split-conformal path (byte-identical; this
        # branch not taken). "cqr" = conformalized quantile regression.
        _cm = ctx.get_param("conformal_method", "split")
        conformal_method = "split" if (_cm is None or str(_cm).strip() == "") else str(_cm).strip().lower()
        # Fix B Tier 1c-1: allowlist guard (was silent fallthrough -> split).
        if conformal_method not in ("split", "cqr", "enbpi"):
            return make_error_response(
                ctx,
                f"Unknown conformal_method '{conformal_method}'. Must be one of: split, cqr, enbpi.",
                error_fixes=[
                    "Use 'split' (default; ARIMA + split-conformal), 'cqr' "
                    "(conformalized quantile regression), or 'enbpi' (ensemble "
                    "batch prediction intervals).",
                ],
            )
        if conformal_method == "cqr":
            return _run_cqr(
                ctx, progress_callback, name, clean, n, horizon, alpha,
                conf_level, cal_frac, warn_list,
            )
        if conformal_method == "enbpi":
            return _run_enbpi(
                ctx, progress_callback, name, clean, n, horizon, alpha,
                conf_level, warn_list,
            )

        # Split data: training | calibration | (future)
        n_cal = max(10, int(n * cal_frac))
        n_train = n - n_cal
        if n_train < 15:
            n_train = 15
            n_cal = n - n_train
        if n_cal < 5:
            return make_error_response(
                ctx,
                f"After reserving training data, only {n_cal} calibration points remain. "
                "Need at least 5.",
                error_fixes=["Provide a longer series or reduce cal_fraction."],
            )

        train = clean[:n_train]
        cal = clean[n_train:]

        progress_callback("Fitting model on training data", 15)

        import pmdarima as pm
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            model = pm.auto_arima(
                train, seasonal=seasonal, m=m_val if seasonal else 1,
                stepwise=preset_cfg["stepwise"],
                max_p=preset_cfg["max_p"], max_q=preset_cfg["max_q"],
                suppress_warnings=True, error_action="ignore", trace=False,
            )

        progress_callback("Computing calibration residuals", 40)

        # One-step-ahead residuals on calibration set using rolling refit
        # For efficiency, we use the fitted model to predict and compute residuals
        # rather than refitting at each step
        cal_residuals = []
        extended = train.copy()
        for i in range(n_cal):
            pct = 40 + int(25 * i / n_cal)
            if i % max(1, n_cal // 5) == 0:
                progress_callback(f"Calibration step {i + 1}/{n_cal}", pct)

            fc_one = model.predict(n_periods=1)
            resid = abs(cal[i] - fc_one[0])
            cal_residuals.append(resid)
            # Update model with new observation
            model.update(np.array([cal[i]]))
            extended = np.append(extended, cal[i])

        cal_residuals = np.array(cal_residuals)

        # Diagnose whether the "exchangeability" assumption behind
        # split conformal looks plausible here. If the calibration
        # residuals carry strong autocorrelation, the implicit
        # assumption breaks and realized coverage can fall below the
        # Compute calibration-residual lag-1 ACF unconditionally (lifted
        # from inside the warning branch per Prompt C1 wiring). Preserve
        # the defensive guards (short-residuals, zero-variance) by
        # setting _rho_calibration to None when guards fail.
        _rho_calibration = None
        if len(cal_residuals) >= 3:
            _cr = cal_residuals - np.mean(cal_residuals)
            _c0 = float(np.sum(_cr ** 2))
            if _c0 > 0:
                _c1 = float(np.sum(_cr[:-1] * _cr[1:]))
                _rho_calibration = _c1 / _c0
                if abs(_rho_calibration) > 0.2:
                    warn_list.append(
                        f"Calibration residuals show lag-1 autocorrelation "
                        f"(rho = {_rho_calibration:+.2f}). Standard split conformal assumes "
                        f"exchangeable residuals; the reported coverage guarantee "
                        f"may not hold. For formally-guaranteed time-series "
                        f"coverage, use an adaptive conformal method (not yet "
                        f"implemented in this technique)."
                    )

        progress_callback("Computing conformal quantile", 70)

        # Conformal quantile: ceil((n_cal + 1)(1 - alpha)) / n_cal -th quantile
        # of absolute residuals
        q_level = np.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal
        q_level = min(q_level, 1.0)
        conformal_q = float(np.quantile(cal_residuals, q_level))

        progress_callback("Generating forecasts with conformal intervals", 80)

        # Generate point forecasts and construct conformal intervals
        fc, arima_ci = model.predict(n_periods=horizon, return_conf_int=True, alpha=alpha)

        # Conformal intervals: point forecast +/- conformal quantile
        conf_lower = fc - conformal_q
        conf_upper = fc + conformal_q

        # Build forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([
                i + 1,
                round(float(fc[i]), 6),
                round(float(conf_lower[i]), 6),
                round(float(conf_upper[i]), 6),
                round(float(arima_ci[i, 0]), 6),
                round(float(arima_ci[i, 1]), 6),
            ])
        ci_label = f"{conf_level * 100:.0f}%"
        fc_table = make_table(
            "Forecast with Conformal Intervals",
            ["Step", "Point Forecast",
             f"Conformal Lower {ci_label}", f"Conformal Upper {ci_label}",
             f"Parametric Lower {ci_label}", f"Parametric Upper {ci_label}"],
            fc_rows,
        )

        # Calibration diagnostics
        resid_stats_rows = [
            ["Calibration Set Size", n_cal],
            ["Training Set Size", n_train],
            ["Conformal Quantile (q)", round(conformal_q, 6)],
            ["Target Coverage", f"{ci_label}"],
            ["Mean |Residual|", round(float(np.mean(cal_residuals)), 6)],
            ["Median |Residual|", round(float(np.median(cal_residuals)), 6)],
            ["Max |Residual|", round(float(np.max(cal_residuals)), 6)],
            ["ARIMA Order", f"({model.order[0]},{model.order[1]},{model.order[2]})"],
            ["Horizon", horizon],
        ]
        diag_table = make_table("Diagnostics", ["Metric", "Value"], resid_stats_rows)

        # Calibration residuals table (show all)
        cal_rows = []
        for i in range(n_cal):
            cal_rows.append([
                n_train + i + 1,
                round(float(cal[i]), 6),
                round(float(cal_residuals[i]), 6),
                "Yes" if cal_residuals[i] <= conformal_q else "No",
            ])
        cal_table = make_table(
            "Calibration Residuals",
            ["Index", "Actual", "|Residual|", "Within Quantile"],
            cal_rows,
        )

        # Width comparison
        conformal_width = 2.0 * conformal_q
        parametric_widths = arima_ci[:, 1] - arima_ci[:, 0]
        avg_parametric_width = float(np.mean(parametric_widths))

        wider = "conformal" if conformal_width > avg_parametric_width else "parametric"

        plain_english = (
            f"Conformal prediction intervals for '{name}' with {ci_label} target coverage. "
            f"Based on {n_cal} calibration residuals, the conformal half-width is {conformal_q:.4f}. "
            f"The conformal intervals are constant-width ({conformal_width:.4f}), while the "
            f"parametric ARIMA intervals average {avg_parametric_width:.4f} wide. "
            f"The {wider} intervals are wider on average. "
            f"Conformal intervals provide distribution-free coverage guarantees."
        )

        if conformal_q > 3 * np.std(clean):
            warn_list.append(
                "The conformal quantile is very large relative to the series variability, "
                "suggesting the model may not fit well."
            )

        charting = (
            "Line chart showing the original series, point forecast continuation, "
            "and TWO sets of shaded intervals: conformal (outer, lighter shade) and "
            "parametric ARIMA (inner, darker shade). "
            "Secondary panel: histogram of calibration residuals with vertical line at conformal quantile."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("conformal_intervals", {
            "series_name": name,
            "target_coverage": float(conf_level),
            "horizon": int(horizon),
            "avg_interval_width": float(conformal_width),
            "parametric_baseline_width": float(avg_parametric_width),
            "base_model": f"ARIMA({model.order[0]},{model.order[1]},{model.order[2]})",
            "train_frac": float(1.0 - cal_frac),
            "calibration_frac": float(cal_frac),
            "conformal_quantile": float(conformal_q),
            "calibration_residual_acf_lag1": (
                float(_rho_calibration) if _rho_calibration is not None else None
            ),
        })
        return make_response(
            ctx,
            tables=[fc_table, diag_table, cal_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "n_train": n_train,
                "n_cal": n_cal,
                "conformal_quantile": round(conformal_q, 6),
                "confidence_level": conf_level,
                "horizon": horizon,
                "arima_order": f"({model.order[0]},{model.order[1]},{model.order[2]})",
                "conformal_width": round(conformal_width, 4),
                "avg_parametric_width": round(avg_parametric_width, 4),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Conformal prediction intervals failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=30).",
                "Try a smaller calibration fraction.",
                "Check that pmdarima is installed.",
            ],
        )


def _run_cqr(ctx, progress_callback, name, clean, n, horizon, alpha,
             conf_level, cal_frac, warn_list):
    """ENG-EXT-CONFORMAL-001 C1 — Conformalized Quantile Regression path.

    Conformalizes the gradient-boosting quantile-regression base (reuses
    `quantile_regression_model._create_features` / `_build_forecast_features`)
    via `_cqr_intervals`. Splits the supervised lag-feature rows into
    train | calibration | test; reports a held-out empirical-coverage
    diagnostic on the test slice; produces horizon intervals by median
    recursion. ADDITIVE — only reached when `conformal_method="cqr"`.
    """
    try:
        from techniques.quantile_regression_model import (
            _create_features, _build_forecast_features,
        )
        from sklearn.ensemble import GradientBoostingRegressor

        progress_callback("Building quantile-regression features", 15)
        # Fix B Tier 1c-1: blank/absent -> data-driven default (byte-identical);
        # n_lags applies to the CQR + EnbPI methods.
        _nl_default = min(12, max(3, n // 10))
        _nl = ctx.get_param("n_lags", _nl_default)
        n_lags = _nl_default if (_nl is None or str(_nl).strip() == "") else int(_nl)
        if not (1 <= n_lags < n):
            return make_error_response(
                ctx,
                f"n_lags must be in [1, {n}). Got {n_lags}.",
                error_fixes=["Use a positive number of lags smaller than the series length."],
            )
        rolling_windows = [3, 6]
        seed = int(ctx.seed)

        X, y, _ = _create_features(clean, n_lags, rolling_windows)
        if len(y) < 40:
            return make_error_response(
                ctx,
                f"Too few usable rows ({len(y)}) after building lag features "
                f"for CQR. Provide a longer series or reduce n_lags.",
                error_fixes=["Provide a longer time series."],
            )

        # train | calibration | test (test = held-out coverage diagnostic)
        m = len(y)
        n_test = max(10, int(0.2 * m))
        n_rem = m - n_test
        n_cal = max(10, int(cal_frac * n_rem))
        n_train = n_rem - n_cal
        if n_train < 20:
            return make_error_response(
                ctx, f"Too few training rows ({n_train}) for CQR.",
                error_fixes=["Provide a longer series or reduce cal_fraction."],
            )
        X_train, y_train = X[:n_train], y[:n_train]
        X_cal, y_cal = X[n_train:n_train + n_cal], y[n_train:n_train + n_cal]
        X_test, y_test = X[n_train + n_cal:], y[n_train + n_cal:]

        progress_callback("Fitting conformalized quantile regression", 45)
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            res = _cqr_intervals(
                X_train, y_train, X_cal, y_cal, X_test, alpha=alpha, seed=seed)
            # median regressor for the horizon point recursion
            gmed = GradientBoostingRegressor(
                loss="quantile", alpha=0.5, random_state=seed).fit(X_train, y_train)

        lo_test, hi_test, Q = res["lo"], res["hi"], res["Q"]
        empirical_coverage = float(np.mean((y_test >= lo_test) & (y_test <= hi_test)))
        mean_width = float(np.mean(hi_test - lo_test))

        progress_callback("Generating CQR forecast intervals", 75)
        glo, ghi = res["glo"], res["ghi"]
        series_ext = clean.copy()
        fc_rows = []
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            for step in range(horizon):
                fx = _build_forecast_features(series_ext, n_lags, rolling_windows).reshape(1, -1)
                point = float(gmed.predict(fx)[0])
                lo = float(glo.predict(fx)[0] - Q)
                hi = float(ghi.predict(fx)[0] + Q)
                fc_rows.append([
                    step + 1, round(point, 6), round(lo, 6), round(hi, 6),
                ])
                series_ext = np.append(series_ext, point)

        ci_label = f"{conf_level * 100:.0f}%"
        fc_table = make_table(
            "CQR Forecast with Conformal Intervals",
            ["Step", "Point Forecast (median)",
             f"CQR Lower {ci_label}", f"CQR Upper {ci_label}"],
            fc_rows,
        )
        diag_table = make_table(
            "CQR Coverage Diagnostics",
            ["Metric", "Value"],
            [
                ["Method", "CQR (conformalized quantile regression)"],
                ["Target Coverage", ci_label],
                ["Held-out Empirical Coverage", round(empirical_coverage, 4)],
                ["Held-out Test Size", n_test],
                ["Mean Interval Width", round(mean_width, 6)],
                ["Conformal Adjustment (Q)", round(Q, 6)],
                ["Train / Calibration Size", f"{n_train} / {n_cal}"],
                ["Lag Features", n_lags],
            ],
        )

        if empirical_coverage < conf_level - 0.10:
            warn_list.append(
                f"CQR held-out coverage ({empirical_coverage:.3f}) is below the "
                f"target ({conf_level:.2f}) — the quantile model may be "
                "miscalibrated on this series (non-exchangeable residuals)."
            )

        plain = (
            f"Conformalized quantile regression (CQR) intervals for '{name}' at "
            f"{ci_label} target coverage. The quantile-regression base produces "
            f"adaptive-width intervals; conformalization adds Q={Q:.4f} to "
            f"guarantee finite-sample validity. Held-out empirical coverage on "
            f"{n_test} test points was {empirical_coverage:.3f}; mean interval "
            f"width {mean_width:.4f}."
        )
        charting = (
            "Line chart of the series with the CQR point forecast and an "
            "ADAPTIVE-width shaded interval (wider where the quantile spread is "
            "larger). Secondary panel: held-out coverage vs nominal."
        )
        progress_callback("Done", 100)
        return make_response(
            ctx,
            tables=[fc_table, diag_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=None,
            audit_fields={
                "conformal_method": "cqr",
                "confidence_level": conf_level,
                "horizon": horizon,
                "cqr_coverage": round(empirical_coverage, 6),
                "cqr_mean_width": round(mean_width, 6),
                "cqr_Q": round(Q, 6),
                "n_train": n_train,
                "n_cal": n_cal,
                "n_test": n_test,
                "n_lags": n_lags,
            },
        )
    except Exception as e:
        return make_error_response(
            ctx,
            f"CQR conformal intervals failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Check that scikit-learn is installed.",
            ],
        )


def _run_enbpi(ctx, progress_callback, name, clean, n, horizon, alpha,
               conf_level, warn_list):
    """ENG-EXT-CONFORMAL-001 C2 — Ensemble Batch Prediction Intervals path.

    EnbPI (Xu-Xie 2021) via `_enbpi_intervals` on the gradient-boosting (or
    neural, the S85 fold-in) base over lag features (reuses
    `quantile_regression_model._create_features`). Holds out a test slice for
    the empirical-coverage diagnostic; forecasts the horizon by ensemble-mean
    recursion ± the conformal width. ADDITIVE — only reached when
    `conformal_method="enbpi"`.
    """
    try:
        from techniques.quantile_regression_model import (
            _create_features, _build_forecast_features,
        )
        progress_callback("Building features for EnbPI", 15)
        # Fix B Tier 1c-1: blank/absent -> default (byte-identical). n_lags +
        # enbpi_base/n_resamplings/block_length apply to the EnbPI method.
        _nl_default = min(12, max(3, n // 10))
        _nl = ctx.get_param("n_lags", _nl_default)
        n_lags = _nl_default if (_nl is None or str(_nl).strip() == "") else int(_nl)
        rolling_windows = [3, 6]
        seed = int(ctx.seed)
        _eb = ctx.get_param("enbpi_base", "gbr")
        base_kind = "gbr" if (_eb is None or str(_eb).strip() == "") else str(_eb).strip().lower()
        _nr = ctx.get_param("n_resamplings", 30)
        n_resamplings = 30 if (_nr is None or str(_nr).strip() == "") else int(_nr)
        _bl = ctx.get_param("block_length", 10)
        block_length = 10 if (_bl is None or str(_bl).strip() == "") else int(_bl)
        if not (1 <= n_lags < n):
            return make_error_response(
                ctx,
                f"n_lags must be in [1, {n}). Got {n_lags}.",
                error_fixes=["Use a positive number of lags smaller than the series length."],
            )
        if base_kind not in ("gbr", "neural"):
            return make_error_response(
                ctx,
                f"Unknown enbpi_base '{base_kind}'. Must be one of: gbr, neural.",
                error_fixes=["Use 'gbr' (gradient boosting, default) or 'neural' (MLP)."],
            )
        if n_resamplings < 1:
            return make_error_response(
                ctx,
                f"n_resamplings must be >= 1. Got {n_resamplings}.",
                error_fixes=["Use a positive number of bootstrap resamples (e.g. 30)."],
            )
        if block_length < 1:
            return make_error_response(
                ctx,
                f"block_length must be >= 1. Got {block_length}.",
                error_fixes=["Use a positive block length (e.g. 10)."],
            )

        X, y, _ = _create_features(clean, n_lags, rolling_windows)
        if len(y) < 40:
            return make_error_response(
                ctx, f"Too few usable rows ({len(y)}) for EnbPI.",
                error_fixes=["Provide a longer time series."],
            )
        m = len(y)
        n_test = max(10, int(0.2 * m))
        n_train = m - n_test
        if n_train < 30:
            return make_error_response(
                ctx, f"Too few training rows ({n_train}) for EnbPI.",
                error_fixes=["Provide a longer series."],
            )
        X_train, y_train = X[:n_train], y[:n_train]
        X_test, y_test = X[n_train:], y[n_train:]
        block_length = max(2, min(block_length, n_train // 3))

        progress_callback(f"Fitting EnbPI ensemble (base={base_kind})", 45)
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            res = _enbpi_intervals(
                X_train, y_train, X_test, alpha=alpha, base_kind=base_kind,
                n_resamplings=n_resamplings, block_length=block_length, seed=seed)
        lo_test, hi_test, w = res["lo"], res["hi"], res["w"]
        empirical_coverage = float(np.mean((y_test >= lo_test) & (y_test <= hi_test)))
        mean_width = float(np.mean(hi_test - lo_test))

        progress_callback("Generating EnbPI forecast intervals", 78)
        # Fit the forward-forecast ensemble ONCE on the full data, then iterate
        # the ensemble-mean ± w over the horizon (reuse the fitted models — no
        # per-step refit).
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fc_fit = _enbpi_intervals(
                X, y, X[-1:], alpha=alpha, base_kind=base_kind,
                n_resamplings=n_resamplings,
                block_length=max(2, min(block_length, len(y) // 3)), seed=seed)
            fc_models, fc_w = fc_fit["models"], fc_fit["w"]
            series_ext = clean.copy()
            fc_rows = []
            for step in range(horizon):
                fx = _build_forecast_features(series_ext, n_lags, rolling_windows).reshape(1, -1)
                point = float(np.mean([mdl.predict(fx)[0] for mdl in fc_models]))
                fc_rows.append([
                    step + 1, round(point, 6),
                    round(point - fc_w, 6), round(point + fc_w, 6),
                ])
                series_ext = np.append(series_ext, point)

        ci_label = f"{conf_level * 100:.0f}%"
        fc_table = make_table(
            "EnbPI Forecast with Conformal Intervals",
            ["Step", "Point Forecast (ensemble)",
             f"EnbPI Lower {ci_label}", f"EnbPI Upper {ci_label}"],
            fc_rows,
        )
        diag_table = make_table(
            "EnbPI Coverage Diagnostics",
            ["Metric", "Value"],
            [
                ["Method", "EnbPI (ensemble batch prediction intervals)"],
                ["Base Estimator", "neural (MLP)" if base_kind == "neural" else "gradient boosting"],
                ["Target Coverage", ci_label],
                ["Held-out Empirical Coverage", round(empirical_coverage, 4)],
                ["Held-out Test Size", n_test],
                ["Mean Interval Width", round(mean_width, 6)],
                ["Conformal Width (w)", round(w, 6)],
                ["Ensemble Size / Block Length", f"{n_resamplings} / {block_length}"],
                ["Lag Features", n_lags],
            ],
        )
        if empirical_coverage < conf_level - 0.10:
            warn_list.append(
                f"EnbPI held-out coverage ({empirical_coverage:.3f}) is below the "
                f"target ({conf_level:.2f}) — the ensemble may be miscalibrated "
                "on this series."
            )
        base_label = "neural (MLP)" if base_kind == "neural" else "gradient-boosting"
        plain = (
            f"Ensemble batch prediction intervals (EnbPI) for '{name}' at "
            f"{ci_label} target coverage, on a {base_label} base. A "
            f"{n_resamplings}-model block-bootstrap ensemble produces "
            f"out-of-bag residuals conformalized to a width w={w:.4f}. Held-out "
            f"empirical coverage on {n_test} test points was "
            f"{empirical_coverage:.3f}; mean interval width {mean_width:.4f}."
        )
        charting = (
            "Line chart of the series with the EnbPI ensemble forecast and a "
            "shaded conformal interval. Secondary panel: held-out coverage vs "
            "nominal."
        )
        progress_callback("Done", 100)
        return make_response(
            ctx,
            tables=[fc_table, diag_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=None,
            audit_fields={
                "conformal_method": "enbpi",
                "enbpi_base": base_kind,
                "confidence_level": conf_level,
                "horizon": horizon,
                "enbpi_coverage": round(empirical_coverage, 6),
                "enbpi_mean_width": round(mean_width, 6),
                "enbpi_w": round(w, 6),
                "n_train": n_train,
                "n_test": n_test,
                "n_resamplings": n_resamplings,
                "block_length": block_length,
                "n_lags": n_lags,
            },
        )
    except Exception as e:
        return make_error_response(
            ctx,
            f"EnbPI conformal intervals failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Check that scikit-learn is installed.",
            ],
        )
