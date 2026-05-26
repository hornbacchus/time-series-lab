"""Phase 3 Batch 8 — LightGBM forecast parity check.

TSL ``engine/techniques/lightgbm_forecast.py`` (lightgbm.LGBMRegressor
primary path with sklearn GradientBoostingRegressor fallback when
lightgbm unavailable + engine preset preprocessing + lag/rolling/
diff/time features + recursive multi-step forecasting +
num_leaves-controlled leaf-wise tree growth + post-fit importance
normalization to sum-to-1) vs from-scratch paper-formula reimpl
mirroring engine's primary path exactly. Reference uses identical
lightgbm primitive at identical hyperparameters + identical
importance normalization so any divergence isolates engine wrapper
orchestration vs paper-formula reference.

Rewritten at SC4-side Cat 3 remediation cycle session 4/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern + two-layer family template (SC1 + SC2 +
SC3) + SC3-established fallback dispatch handling template element
SECOND-INSTANCE application.

**Helper identity verification (Step 1 of SC4 workflow per AST
source-segment SHA256 hash check):** Engine `_prepare_series` +
`_create_features` at `engine/techniques/lightgbm_forecast.py`
lines 52-133 are byte-identical (SHA256 match) to corresponding
SC1 random_forest functions. `_create_forecast_features` at
LightGBM engine lines 136-181 SHA256 hash DIFFERS from SC1 RF
version (`97ab66c14484c5d5` RF vs `e598dd6a587adb14` LGB) — but
divergence is COMMENT-ONLY (RF version includes
`# Placeholder for recursive prediction (will be set later)`
comment before `extended.append(0.0)` line; LightGBM version omits
this comment). Behavioral logic byte-identical at runtime. Layer 2
family-shared helper imports from SC1 ratified empirically;
institutional nuance documented in §2.5 entry. FOURTH-INSTANCE
confirmation of two-layer template at behavior scope (despite
comment-level SHA256 divergence at one helper).

**Fallback dispatch handling (Step 2 of SC4 workflow; SECOND-
INSTANCE application of SC3-established template element):**
Engine `_has_lightgbm()` at lines 22-27 dispatches to
lightgbm.LGBMRegressor primary path when lightgbm available;
sklearn.GradientBoostingRegressor fallback path when not. This
audit session validates PRIMARY path (lightgbm 4.6.0 confirmed
installed). Fallback path NOT validated at math layer; covered at
wrapper-layer 3-check Check 2.

**LightGBM-specific engine refinement (importance normalization):**
Engine lines 297-301 normalize raw LightGBM split-count importances
to sum-to-1 fractions (`importances = importances / imp_sum`).
Reference arm mirrors this normalization step exactly. Distinct
from RF + GBR + XGBoost which expose normalized importances at the
sklearn-API level natively (no engine normalization step).

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic seed.
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


# Engine preset Balanced config (engine `lightgbm_forecast.py` lines
# 37-42). Mirrored verbatim per Disposition 2. Note LightGBM-specific
# `num_leaves` field absent from SC1+SC2+SC3 presets (LightGBM uses
# leaf-wise tree growth; num_leaves caps leaves per tree rather than
# depth-first growth like RF/GBR/XGBoost).
_ENGINE_BALANCED_PRESET = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "n_lags": 12,
    "rolling_windows": [3, 6, 12],
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "num_leaves": 31,
}


def _reference_lightgbm(
    y: np.ndarray, *, seed: int, horizon: int = 12, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl that mirrors engine `lightgbm_forecast.run()`
    primary path at lines 203-507: prepare_series + create_features +
    LGBMRegressor.fit at engine-resolved hyperparameters (including
    `num_leaves=31` leaf-wise growth control + `subsample=0.8` +
    `colsample_bytree=0.8` stochastic + post-fit importance
    normalization to sum-to-1) + TimeSeriesSplit CV + multi-step
    recursive forecast.
    """
    import lightgbm as lgb  # type: ignore
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
    num_leaves = int(cfg["num_leaves"])

    # Cap lags per engine line 257
    n_lags = min(n_lags, n // 3)

    X, y_target, feature_names = _create_features_reference(
        clean, n_lags, rolling_windows,
    )

    # LightGBM primary path per engine lines 284-294
    model = lgb.LGBMRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        subsample=subsample,
        colsample_bytree=colsample_bytree,
        objective="regression",
        random_state=seed,
        verbosity=-1,
    )
    model.fit(X, y_target)

    # Importance normalization per engine lines 297-301: LightGBM
    # raw feature_importances_ are split counts (integers); engine
    # normalizes to sum-to-1 fractions for cross-technique comparability.
    importances = model.feature_importances_.astype(float)
    imp_sum = importances.sum()
    if imp_sum > 0:
        importances = importances / imp_sum

    # In-sample metrics (engine lines 321-328)
    y_pred_train = model.predict(X)
    train_residuals = y_target - y_pred_train
    train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
    train_mae = float(np.mean(np.abs(train_residuals)))
    ss_res = float(np.sum(train_residuals ** 2))
    ss_tot = float(np.sum((y_target - np.mean(y_target)) ** 2))
    train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # TimeSeriesSplit CV (engine lines 335-363). Engine CV model uses
    # max(50, n_estimators//2) trees + NO subsample / colsample
    # parameters (engine lines 343-351 omit both at CV scope distinct
    # from main-model stochastic LightGBM fitting). num_leaves
    # preserved at CV scope (engine line 347).
    n_splits = min(3, max(2, len(X) // 20))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y_target[train_idx], y_target[val_idx]
        cv_model = lgb.LGBMRegressor(
            n_estimators=max(50, n_estimators // 2),
            max_depth=max_depth,
            learning_rate=learning_rate,
            num_leaves=num_leaves,
            objective="regression",
            random_state=seed,
            verbosity=-1,
        )
        cv_model.fit(X_tr, y_tr)
        pred = cv_model.predict(X_val)
        cv_rmse = float(np.sqrt(np.mean((y_val - pred) ** 2)))
        cv_scores.append(cv_rmse)
    avg_cv_rmse = float(np.mean(cv_scores))

    # Multi-step recursive forecast (engine lines 371-381)
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


class LightgbmParity(P3ParityCheck):
    """LightGBM forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.lightgbm_forecast.run() via
    RunContext + extracts forecast values + audit_fields. Reference
    arm reimplements the same primary-path pipeline at Balanced preset
    (n_estimators=300 + max_depth=6 + learning_rate=0.05 + num_leaves=31
    + n_lags=12 + rolling_windows=[3, 6, 12] + subsample=0.8 +
    colsample_bytree=0.8 + importance-normalization-to-sum-to-1).
    Fallback path (sklearn GBR when lightgbm unavailable) NOT
    validated at math layer.
    """

    technique_id = "p3_lightgbm"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "LightGBM forecast with lightgbm.LGBMRegressor at "
        "random_state=ctx.seed is deterministic at fixed seed "
        "(triage bit-exact confirmation). Engine and reference "
        "reimpl follow identical primary-path pipeline including "
        "post-fit importance normalization to sum-to-1; forecast "
        "values + audit_fields match at machine precision modulo "
        "engine 6-decimal output-rounding floor at forecast values "
        "+ 4-decimal floor at importance + train/cv metrics. "
        "Fallback path (sklearn GBR) covered at wrapper-layer "
        "3-check only — mathematically distinct from LightGBM "
        "leaf-wise tree growth + histogram-based splits."
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.lightgbm_forecast as lgb_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_lightgbm_parity",
            "technique_id": "lightgbm_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = lgb_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL lightgbm_forecast failed: "
                f"{resp.get('error_message')}"
            )
        # Backend dispatch verification (SC3 template element second-
        # instance application)
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "lightgbm":
            raise RuntimeError(
                f"TSL lightgbm_forecast dispatched to backend='{backend}' "
                f"not 'lightgbm'; primary path validation requires "
                f"lightgbm installed in audit environment"
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
            "num_leaves": int(audit.get("num_leaves", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        try:
            import lightgbm as lgb  # type: ignore
            lgb_version = lgb.__version__
        except ImportError:
            lgb_version = "NOT_INSTALLED"
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_lightgbm(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["lightgbm_version"] = lgb_version
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
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
                "num_leaves": int(_ENGINE_BALANCED_PRESET["num_leaves"]),
                "learning_rate": float(_ENGINE_BALANCED_PRESET["learning_rate"]),
                "subsample": float(_ENGINE_BALANCED_PRESET["subsample"]),
                "colsample_bytree": float(_ENGINE_BALANCED_PRESET["colsample_bytree"]),
                "lightgbm_version": ref.get("lightgbm_version", "unknown"),
                "top_feature_tsl": str(tsl.get("top_feature_name", "")),
                "top_feature_ref": str(ref.get("top_feature_name", "")),
            },
        )
