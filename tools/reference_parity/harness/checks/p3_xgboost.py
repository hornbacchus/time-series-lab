"""Phase 3 Batch 8 — XGBoost forecast parity check.

TSL ``engine/techniques/xgboost_forecast.py`` (xgboost.XGBRegressor
primary path with sklearn GradientBoostingRegressor fallback when
xgboost unavailable + engine preset preprocessing + lag/rolling/
diff/time features + recursive multi-step forecasting) vs from-
scratch paper-formula reimplementation that mirrors the engine's
exact pipeline at the primary (xgboost) path (NaN edge-strip-and-
interpolate + lag features at n_lags + rolling mean/std features
at rolling_windows + diff feature + time index feature +
XGBRegressor fit at IDENTICAL engine-resolved hyperparameters
including subsample + colsample_bytree + TimeSeriesSplit CV +
multi-step recursive forecast). Reference arm uses identical
xgboost primitive at identical hyperparameters so any divergence
isolates the engine wrapper's orchestration vs the paper-formula
reference.

Rewritten at SC3-side Cat 3 remediation cycle session 3/17 per
triage close (Cat 3 bit-exact deterministic confirmation) +
inventory verification 12d3785 + Tier 2 incremental forward-
amendment pattern + two-layer family template established at SC1
+ SC2 (Layer 1 per-technique verbatim preset mirror; Layer 2 per-
family shared helper imports when engine source byte-identical).

**Helper identity verification (Step 1 of SC3 workflow per ratified
spec):** Engine `_prepare_series` + `_create_features` +
`_create_forecast_features` at `engine/techniques/xgboost_forecast.py`
lines 46-176 are byte-identical (AST source-segment SHA256 match) to
the corresponding functions at `engine/techniques/random_forest_
forecast.py` lines 35-165. Layer 2 family-shared helper imports
from SC1 `p3_random_forest.py` per ratified two-layer family
template; no `_reference_xgboost_*` helper reimplementation required.

**Fallback dispatch handling (Step 2 of SC3 workflow):** Engine
`_has_xgboost()` at lines 19-24 dispatches to xgboost.XGBRegressor
primary path when xgboost available; sklearn.GradientBoostingRegressor
fallback path when not. This audit session validates PRIMARY path
(xgboost 3.2.0 confirmed installed at audit-environment Step 2
empirical check). Fallback path NOT validated at math layer; covered
at wrapper-layer 3-check at Check 2 (Balanced preset invocation
exercises engine code path which dispatches to whichever backend is
available at engine-invocation time).

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic seed; bit-exact target on
forecast values + audit_fields modulo engine 6-decimal output-
rounding floor at forecast values (engine line 397) + 4-decimal
floor at importance + train/cv metrics (engine lines 391 + 412-416).
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
from reference_parity.harness.checks.p3_random_forest import (
    _generate_ar_dgp,
    _create_features_reference,
    _create_forecast_features_reference,
    _prepare_series_reference,
)


# Engine preset Balanced config (engine `xgboost_forecast.py` lines
# 33-37). Mirrored verbatim per Disposition 2 ratified at SC1 close.
# Note XGBoost-specific fields: `subsample` + `colsample_bytree`
# (column-subsampling per tree); distinct from RF (no subsample,
# n_jobs=-1) and GBR (subsample only).
_ENGINE_BALANCED_PRESET = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "n_lags": 12,
    "rolling_windows": [3, 6, 12],
    "subsample": 0.8,
    "colsample_bytree": 0.8,
}


def _reference_xgboost(
    y: np.ndarray, *, seed: int, horizon: int = 12, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl that mirrors engine `xgboost_forecast.run()`
    primary path at lines 196-504: prepare_series + create_features +
    XGBRegressor.fit at engine-resolved hyperparameters (including
    `subsample=0.8` + `colsample_bytree=0.8` for stochastic XGBoost
    with column-subsampling) + TimeSeriesSplit CV + multi-step
    recursive forecast. Shares `_prepare_series_reference` +
    `_create_features_reference` + `_create_forecast_features_reference`
    helpers with SC1 random_forest via verified byte-identical engine
    source (Layer 2 family-shared helper imports per SC3 Step 1
    verification).
    """
    import xgboost as xgb  # type: ignore
    from sklearn.model_selection import TimeSeriesSplit  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    clean, n_interp = _prepare_series_reference(y)
    n = len(clean)

    n_lags = int(cfg["n_lags"])
    n_estimators = int(cfg["n_estimators"])
    max_depth = int(cfg["max_depth"])
    learning_rate = float(cfg["learning_rate"])
    rolling_windows = list(cfg["rolling_windows"])
    subsample = float(cfg["subsample"])
    colsample_bytree = float(cfg["colsample_bytree"])

    # Cap lags per engine line 260
    n_lags = min(n_lags, n // 3)

    X, y_target, feature_names = _create_features_reference(
        clean, n_lags, rolling_windows,
    )

    # XGBoost primary path per engine lines 287-297
    model = xgb.XGBRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        objective="reg:squarederror",
        random_state=seed,
        verbosity=0,
    )
    model.fit(X, y_target)

    # In-sample metrics (engine lines 320-327)
    y_pred_train = model.predict(X)
    train_residuals = y_target - y_pred_train
    train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
    train_mae = float(np.mean(np.abs(train_residuals)))
    ss_res = float(np.sum(train_residuals ** 2))
    ss_tot = float(np.sum((y_target - np.mean(y_target)) ** 2))
    train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # TimeSeriesSplit CV (engine lines 334-361). Engine CV model uses
    # max(50, n_estimators//2) trees + NO subsample / colsample
    # parameters (defaults to 1.0; engine lines 342-348 omit both
    # subsample + colsample_bytree args at CV scope distinct from
    # main-model stochastic XGBoost fitting).
    n_splits = min(3, max(2, len(X) // 20))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y_target[train_idx], y_target[val_idx]
        cv_model = xgb.XGBRegressor(
            n_estimators=max(50, n_estimators // 2),
            max_depth=max_depth,
            learning_rate=learning_rate,
            objective="reg:squarederror",
            random_state=seed,
            verbosity=0,
        )
        cv_model.fit(X_tr, y_tr)
        pred = cv_model.predict(X_val)
        cv_rmse = float(np.sqrt(np.mean((y_val - pred) ** 2)))
        cv_scores.append(cv_rmse)
    avg_cv_rmse = float(np.mean(cv_scores))

    # Multi-step recursive forecast (engine lines 368-380)
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


class XgboostParity(P3ParityCheck):
    """XGBoost forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.xgboost_forecast.run() via
    RunContext + extracts forecast values + audit_fields. Reference
    arm reimplements the same primary-path pipeline at Balanced preset
    (n_estimators=300 + max_depth=6 + learning_rate=0.05 + n_lags=12
    + rolling_windows=[3, 6, 12] + subsample=0.8 +
    colsample_bytree=0.8). Fallback path (sklearn GBR when xgboost
    unavailable) NOT validated at math layer.
    """

    technique_id = "p3_xgboost"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "XGBoost forecast with xgboost.XGBRegressor at "
        "random_state=ctx.seed is deterministic at fixed seed "
        "(triage bit-exact confirmation post inventory verification "
        "12d3785). Engine and reference reimpl follow identical "
        "primary-path pipeline (prepare_series NaN edge-strip + "
        "interior interpolate + lag/rolling/diff/time feature "
        "engineering at Balanced preset config + XGBRegressor fit at "
        "engine-resolved hyperparameters with subsample=0.8 + "
        "colsample_bytree=0.8 stochastic XGBoost + TimeSeriesSplit "
        "CV + multi-step recursive forecast); forecast values + "
        "audit_fields match at machine precision modulo engine "
        "6-decimal output-rounding floor at forecast values + "
        "4-decimal floor at importance + train/cv metrics. Fallback "
        "path (sklearn GBR when xgboost unavailable) covered at "
        "wrapper-layer 3-check only."
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext at Balanced preset;
        extract forecast values from "Forecast" table col[1] +
        audit_fields for cross-comparison vs reference reimpl."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.xgboost_forecast as xgb_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_xgboost_parity",
            "technique_id": "xgboost_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = xgb_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL xgboost_forecast failed: "
                f"{resp.get('error_message')}"
            )
        # Verify engine dispatched to xgboost primary path; surface
        # if engine dispatched to sklearn fallback (would indicate
        # xgboost unavailable in audit environment despite Step 2
        # availability check).
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "xgboost":
            raise RuntimeError(
                f"TSL xgboost_forecast dispatched to backend='{backend}' "
                f"not 'xgboost'; primary path validation requires xgboost "
                f"installed in audit environment"
            )
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]], dtype=np.float64,
        )
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
            "backend": backend,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        try:
            import xgboost as xgb  # type: ignore
            xgb_version = xgb.__version__
        except ImportError:
            xgb_version = "NOT_INSTALLED"
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_xgboost(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["xgboost_version"] = xgb_version
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounds forecast values to 6 decimals at engine line 397
        # + audit train_rmse/mae/r2/cv_rmse to 4 decimals at engine lines
        # 473-476. Round REF outputs to match display precision per
        # Phase 1 finding B8 precedent.
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
                "backend": str(tsl.get("backend", "?")),
                "n_estimators": int(_ENGINE_BALANCED_PRESET["n_estimators"]),
                "max_depth": int(_ENGINE_BALANCED_PRESET["max_depth"]),
                "learning_rate": float(_ENGINE_BALANCED_PRESET["learning_rate"]),
                "subsample": float(_ENGINE_BALANCED_PRESET["subsample"]),
                "colsample_bytree": float(_ENGINE_BALANCED_PRESET["colsample_bytree"]),
                "xgboost_version": ref.get("xgboost_version", "unknown"),
                "top_feature_tsl": str(tsl.get("top_feature_name", "")),
                "top_feature_ref": str(ref.get("top_feature_name", "")),
            },
        )
