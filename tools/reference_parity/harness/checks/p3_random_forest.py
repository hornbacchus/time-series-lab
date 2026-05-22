"""Phase 3 Batch 8 — Random Forest forecast parity check.

TSL ``engine/techniques/random_forest_forecast.py``
(sklearn.ensemble.RandomForestRegressor with engine preset
preprocessing + lag/rolling/diff/time features + recursive multi-
step forecasting) vs from-scratch paper-formula reimplementation
that mirrors the engine's exact pipeline (NaN
edge-strip-and-interpolate + lag features at n_lags + rolling
mean/std features at rolling_windows + diff feature + time index
feature + RandomForestRegressor at identical hyperparameters +
recursive multi-step forecast). Reference arm uses identical
sklearn primitive at identical engine-resolved hyperparameters
so any divergence isolates the engine wrapper's orchestration vs
the paper-formula reference.

Rewritten at S62-side Cat 3 remediation cycle session 1/17 per
triage close (Cat 3 bit-exact deterministic confirmation) +
inventory verification 12d3785 + Tier 2 incremental forward-
amendment pattern. The original harness implemented an
abbreviated `_fit_predict` helper instantiating
RandomForestRegressor directly with hardcoded Fast-preset
hyperparameters (n_estimators=100 + max_depth=6 +
min_samples_leaf=5 + n_lags=6) called by BOTH `run_tsl` and
`run_reference` arms — a degenerate self-parity loop bypassing
engine code path. Category 3 DEGENERATE-VACUOUS → Category 1
LEGITIMATE rewrite per established p3_rolling_origin_cv +
p3_conformal hygiene precedent.

Pattern A.3 paper-formula self-parity (Tier IV) at deterministic
seed; bit-exact target on forecast values + audit_fields modulo
engine 6-decimal output-rounding floor at engine line 326
(forecast) + 4-decimal floor at engine lines 320 + 339-343
(importance + train/cv metrics). The compare() rounds REF
outputs to match display precision per Phase 1 finding B8.
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(
    *, seed: int, n: int = 200, phi: float = 0.6, sigma: float = 1.0,
) -> np.ndarray:
    """AR(1) DGP same shape as p3_adf / p3_kpss."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50) * sigma
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = phi * y[t - 1] + eps[t]
    return y[50:]


def _make_lag_features(
    y: np.ndarray, n_lags: int = 6,
) -> tuple[np.ndarray, np.ndarray]:
    """Legacy n_lag-only feature builder retained for back-compat —
    p3_gradient_boosting + p3_lightgbm + p3_svr + p3_quantile_regression
    + p3_xgboost still import this symbol pending their respective Cat
    3 → Cat 1 remediation sessions per triage close ordering (Tier A
    sessions 2-6). Returns (X, y_target) with NaN-row drop. Mirrors the
    pre-rewrite scope; once dependent harnesses are remediated the
    import dependencies fall away and this stub can be removed.
    """
    n = len(y)
    feats: list[np.ndarray] = []
    for lag in range(1, n_lags + 1):
        f = np.full(n, np.nan)
        f[lag:] = y[:-lag]
        feats.append(f)
    X = np.column_stack(feats)
    mask = ~np.any(np.isnan(X), axis=1)
    return X[mask], y[mask]


# Engine preset Balanced config (engine `random_forest_forecast.py`
# lines 24-27). Mirrored verbatim so REF arm exercises identical
# engine math at identical hyperparameters.
_ENGINE_BALANCED_PRESET = {
    "n_estimators": 200,
    "max_depth": 10,
    "min_samples_leaf": 3,
    "n_lags": 12,
    "rolling_windows": [3, 6, 12],
}


def _prepare_series_reference(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Reference reimpl of engine `_prepare_series` lines 35-55: strip
    edge NaN + interpolate interior NaN."""
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


def _create_features_reference(
    series: np.ndarray, n_lags: int, rolling_windows: list[int],
):
    """Reference reimpl of engine `_create_features` lines 58-116."""
    n = len(series)
    max_lookback = max(n_lags, max(rolling_windows) if rolling_windows else 0)
    if n <= max_lookback + 1:
        return None, None, None
    features = []
    feature_names = []
    for lag in range(1, n_lags + 1):
        feat = np.full(n, np.nan)
        feat[lag:] = series[:-lag]
        features.append(feat)
        feature_names.append(f"lag_{lag}")
    for w in rolling_windows:
        feat = np.full(n, np.nan)
        for i in range(w, n):
            feat[i] = np.mean(series[i - w:i])
        features.append(feat)
        feature_names.append(f"roll_mean_{w}")
    for w in rolling_windows:
        if w >= 3:
            feat = np.full(n, np.nan)
            for i in range(w, n):
                feat[i] = np.std(series[i - w:i], ddof=1)
            features.append(feat)
            feature_names.append(f"roll_std_{w}")
    diff1 = np.full(n, np.nan)
    diff1[1:] = np.diff(series)
    features.append(diff1)
    feature_names.append("diff_1")
    time_idx = np.arange(n, dtype=float) / n
    features.append(time_idx)
    feature_names.append("time_index")
    X = np.column_stack(features)
    y = series.copy()
    valid_mask = ~np.any(np.isnan(X), axis=1)
    return X[valid_mask], y[valid_mask], feature_names


def _create_forecast_features_reference(
    series: np.ndarray, horizon: int, n_lags: int,
    rolling_windows: list[int],
):
    """Reference reimpl of engine `_create_forecast_features` lines 119-165."""
    extended = series.tolist()
    forecast_features = []
    for h in range(horizon):
        n_ext = len(extended)
        feat = []
        for lag in range(1, n_lags + 1):
            if n_ext - lag >= 0:
                feat.append(extended[n_ext - lag])
            else:
                feat.append(0.0)
        for w in rolling_windows:
            if n_ext >= w:
                feat.append(float(np.mean(extended[n_ext - w:n_ext])))
            else:
                feat.append(float(np.mean(extended)))
        for w in rolling_windows:
            if w >= 3 and n_ext >= w:
                feat.append(float(np.std(extended[n_ext - w:n_ext], ddof=1)))
            elif w >= 3:
                feat.append(0.0)
        if n_ext >= 2:
            feat.append(extended[-1] - extended[-2])
        else:
            feat.append(0.0)
        feat.append(n_ext / len(series))
        forecast_features.append(np.array(feat))
        extended.append(0.0)
    return forecast_features


def _reference_random_forest(
    y: np.ndarray, *, seed: int, horizon: int = 12, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl that mirrors engine `random_forest_forecast.run()`
    pipeline at lines 183-433: prepare_series + create_features +
    RandomForestRegressor.fit at engine-resolved hyperparameters +
    TimeSeriesSplit CV + multi-step recursive forecast + identical
    audit_fields construction.
    """
    from sklearn.ensemble import RandomForestRegressor  # type: ignore
    from sklearn.model_selection import TimeSeriesSplit  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    clean, n_interp = _prepare_series_reference(y)
    n = len(clean)

    n_lags = int(cfg["n_lags"])
    n_estimators = int(cfg["n_estimators"])
    max_depth = int(cfg["max_depth"])
    min_samples_leaf = int(cfg["min_samples_leaf"])
    rolling_windows = list(cfg["rolling_windows"])

    # Cap lags per engine line 237
    n_lags = min(n_lags, n // 3)

    X, y_target, feature_names = _create_features_reference(
        clean, n_lags, rolling_windows,
    )

    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X, y_target)

    # In-sample metrics (engine lines 261-268)
    y_pred_train = model.predict(X)
    train_residuals = y_target - y_pred_train
    train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
    train_mae = float(np.mean(np.abs(train_residuals)))
    ss_res = float(np.sum(train_residuals ** 2))
    ss_tot = float(np.sum((y_target - np.mean(y_target)) ** 2))
    train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # TimeSeriesSplit CV (engine lines 273-292)
    n_splits = min(3, max(2, len(X) // 20))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y_target[train_idx], y_target[val_idx]
        cv_model = RandomForestRegressor(
            n_estimators=max(50, n_estimators // 2),
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=seed,
            n_jobs=-1,
        )
        cv_model.fit(X_tr, y_tr)
        pred = cv_model.predict(X_val)
        cv_rmse = float(np.sqrt(np.mean((y_val - pred) ** 2)))
        cv_scores.append(cv_rmse)
    avg_cv_rmse = float(np.mean(cv_scores))

    # Multi-step recursive forecast (engine lines 296-310)
    fc_features = _create_forecast_features_reference(
        clean, horizon, n_lags, rolling_windows,
    )
    extended_for_fc = clean.tolist()
    fc_values = []
    for h in range(horizon):
        pred = float(model.predict(fc_features[h].reshape(1, -1))[0])
        fc_values.append(pred)
        extended_for_fc.append(pred)
        if h + 1 < horizon:
            fc_features[h + 1] = _create_forecast_features_reference(
                np.array(extended_for_fc), 1, n_lags, rolling_windows,
            )[0]
    fc_values = np.array(fc_values, dtype=np.float64)

    importances = model.feature_importances_
    feat_imp = sorted(
        zip(feature_names, importances), key=lambda x: -x[1],
    )

    return {
        "forecast": fc_values,
        "feature_importances_sorted": np.array(
            [float(x[1]) for x in feat_imp[:15]], dtype=np.float64,
        ),
        "top_feature_name": feat_imp[0][0] if feat_imp else "",
        "train_rmse": train_rmse,
        "train_mae": train_mae,
        "train_r2": train_r2,
        "cv_rmse": avg_cv_rmse,
        "n_features": len(feature_names),
        "n_train": int(n - n_lags),
    }


class RandomForestParity(P3ParityCheck):
    """Random Forest forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.random_forest_forecast.run()
    via RunContext + extracts forecast values + audit_fields. Reference
    arm reimplements the same pipeline (prepare_series + create_features
    + RandomForestRegressor at engine-resolved Balanced preset
    hyperparameters + TimeSeriesSplit CV + multi-step recursive forecast).
    """

    technique_id = "p3_random_forest"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Random Forest forecast with sklearn.ensemble.RandomForestRegressor "
        "at random_state=ctx.seed is deterministic at fixed seed (triage "
        "bit-exact confirmation post inventory verification 12d3785). "
        "Engine and reference reimpl follow identical pipeline "
        "(prepare_series NaN edge-strip + interior interpolate + lag/"
        "rolling/diff/time feature engineering at Balanced preset config "
        "+ RandomForestRegressor fit at engine-resolved hyperparameters "
        "+ TimeSeriesSplit CV + multi-step recursive forecast); forecast "
        "values + audit_fields match at machine precision modulo engine "
        "6-decimal output-rounding floor at forecast values (engine line "
        "326) + 4-decimal floor at importance + train/cv metrics (engine "
        "lines 320 + 339-343)."
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext at Balanced preset;
        extract forecast values from "Forecast" table col[1] + audit_fields
        for cross-comparison vs reference reimpl."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.random_forest_forecast as rf_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_random_forest_parity",
            "technique_id": "random_forest_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = rf_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL random_forest_forecast failed: {resp.get('error_message')}"
            )
        # Extract forecast table (Step | Forecast)
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]], dtype=np.float64,
        )
        # Extract Feature Importance table sorted desc, top 15
        imp_table = next(
            (t for t in resp["tables"] if t.get("name") == "Feature Importance"),
            None,
        )
        if imp_table is None:
            raise RuntimeError("engine missing 'Feature Importance' table")
        importances_sorted = np.array(
            [float(row[1]) for row in imp_table["rows"]], dtype=np.float64,
        )
        audit = resp.get("audit_fields", {})
        return {
            "forecast": forecast,
            "feature_importances_sorted": importances_sorted,
            "top_feature_name": str(audit.get("top_feature", "")),
            "train_rmse": float(audit.get("train_rmse", float("nan"))),
            "train_mae": float(audit.get("train_mae", float("nan"))),
            "train_r2": float(audit.get("train_r2", float("nan"))),
            "cv_rmse": float(audit.get("cv_rmse", float("nan"))),
            "n_features": int(audit.get("n_features", 0)),
            "n_train": int(audit.get("n_train", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_random_forest(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["sklearn_version"] = sklearn.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounds forecast values to 6 decimals at engine line 326
        # + audit train_rmse/mae/r2/cv_rmse to 4 decimals at engine lines
        # 402-405. Round REF outputs to match display precision per
        # Phase 1 finding B8 precedent (p3_rolling_origin_cv at 4 decimals
        # + p3_conformal at 6 decimals).
        ref_forecast_rounded = np.round(ref["forecast"], 6)
        ref_imp_rounded = np.round(ref["feature_importances_sorted"], 4)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref_forecast_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast"]["status"])

        primary["feature_importances_sorted"] = _compare_vector(
            tsl["feature_importances_sorted"], ref_imp_rounded,
            ladder["primary"],
        )
        statuses.append(primary["feature_importances_sorted"]["status"])

        primary["train_rmse"] = _compare_scalar(
            tsl["train_rmse"], round(ref["train_rmse"], 4),
            ladder["primary"],
        )
        statuses.append(primary["train_rmse"]["status"])

        primary["train_r2"] = _compare_scalar(
            tsl["train_r2"], round(ref["train_r2"], 4),
            ladder["primary"],
        )
        statuses.append(primary["train_r2"]["status"])

        primary["cv_rmse"] = _compare_scalar(
            tsl["cv_rmse"], round(ref["cv_rmse"], 4),
            ladder["primary"],
        )
        statuses.append(primary["cv_rmse"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = (
            "BLOCK" if any_block else
            ("CAVEAT" if any_caveat else "PASS")
        )
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "horizon": int(self.HORIZON),
                "preset": "Balanced",
                "n_estimators": int(_ENGINE_BALANCED_PRESET["n_estimators"]),
                "max_depth": int(_ENGINE_BALANCED_PRESET["max_depth"]),
                "n_lags_resolved": int(tsl.get("n_features", 0)),
                "sklearn_version": ref.get("sklearn_version", "unknown"),
                "top_feature_tsl": str(tsl.get("top_feature_name", "")),
                "top_feature_ref": str(ref.get("top_feature_name", "")),
            },
        )
