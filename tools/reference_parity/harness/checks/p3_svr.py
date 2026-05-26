"""Phase 3 Batch 8 — SVR (Support Vector Regression) forecast parity check.

TSL ``engine/techniques/svr_forecast.py`` (sklearn.svm.SVR with
RBF kernel + dual StandardScaler scaling pipeline on both X and y
+ engine preset preprocessing + lag/rolling/diff/time features +
recursive multi-step forecasting + inverse-scaling on predictions)
vs from-scratch paper-formula reimpl mirroring engine pipeline
exactly. Reference uses identical sklearn SVR primitive at
identical hyperparameters + identical scaling pipeline + identical
inverse-scaling transformation so any divergence isolates engine
wrapper orchestration vs paper-formula reference.

Rewritten at SC5-side Cat 3 remediation cycle session 5/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern + two-layer family template + SC4-
established two-stage helper identity verification + NEW SC5
architectural transition handling (kernel methods with scaling
pipeline).

**Helper identity verification (Step 1 of SC5 workflow per SC4
two-stage methodology):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at SVR engine lines 34-54: MATCH SC1 RF
  (hash 57bae54d463c2fd7)
- `_create_features` at SVR engine lines 57-115: MATCH SC1 RF
  (hash f69ca3848531a82c)
- `_create_forecast_features` at SVR engine lines 118-163: DIFFER
  SC1 RF (RF=97ab66c14484c5d5 vs SVR=e598dd6a587adb14)

Stage 2 (manual code inspection on `_create_forecast_features`
divergence): COMMENT-ONLY divergence — RF version includes
`# Placeholder for recursive prediction (will be set later)`
comment before `extended.append(0.0)` line; SVR version omits
this comment (same pattern as SC4 LightGBM finding). Behavioral
logic byte-identical at runtime. Reuse ratified per SC4 two-stage
methodology established at SC4 §2.5 entry NEW SC4 template
refinement.

**Architectural transition (SC5 FIRST kernel-method session in
Tier A; departs from SC1-SC4 tree-family pattern):**

Distinct from SC1-SC4 tree-family pipeline, SC5 SVR engine adds:
- Dual StandardScaler pipeline: separate scaler for X (features)
  and y (target); both fit_transformed at engine lines 257-261
- Inverse-scaling on predictions: predictions go through
  `scaler_y.inverse_transform(...)` before final output (engine
  lines 274-275 + 315-317)
- CV reuses pre-scaled `X_scaled` + `y_scaled` arrays (engine
  lines 294-295)
- NO `feature_importances_` exposed (SVR doesn't have this
  attribute); engine outputs ONLY 2 tables (`Forecast` + `Model
  Summary`) — distinct from SC1-SC4 3-table structure
- Support vector count + sv_ratio audit fields (SVR-specific)
- NO fallback dispatch (sklearn always available); SC3-established
  fallback-handling template element NOT APPLICABLE at SC5

Reference arm mirrors all SC5 architectural elements exactly +
shares SC1 feature-engineering helpers per Layer 2 family template
(byte-identical at engine source modulo comment-only divergence
at `_create_forecast_features` per SC4 two-stage methodology).

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic sklearn SVR (libsvm
backend; deterministic at fixed input).
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


# Engine preset Balanced config (engine `svr_forecast.py` lines
# 23-26). Mirrored verbatim per Disposition 2. Note SVR-specific
# fields: `kernel` + `C` + `epsilon` + `gamma`; distinct from tree-
# family which have n_estimators + max_depth + num_leaves (LGB) +
# subsample/colsample (XGB+LGB). SVR has NO ensemble / no stochastic
# subsampling — single deterministic SVR fit per data split.
_ENGINE_BALANCED_PRESET = {
    "kernel": "rbf",
    "C": 10.0,
    "epsilon": 0.05,
    "gamma": "scale",
    "n_lags": 12,
    "rolling_windows": [3, 6, 12],
}


def _reference_svr(
    y: np.ndarray, *, seed: int, horizon: int = 12, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl that mirrors engine `svr_forecast.run()`
    pipeline at lines 183-444: prepare_series + create_features +
    StandardScaler dual-pipeline scaling on X + y + SVR.fit at
    engine-resolved hyperparameters + inverse-scaling on predictions
    + TimeSeriesSplit CV on pre-scaled arrays + multi-step recursive
    forecast with scale → predict → inverse-scale per step.
    """
    from sklearn.svm import SVR  # type: ignore
    from sklearn.preprocessing import StandardScaler  # type: ignore
    from sklearn.model_selection import TimeSeriesSplit  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    clean, n_interp = _prepare_series_reference(y)
    n = len(clean)

    n_lags = int(cfg["n_lags"])
    kernel = str(cfg["kernel"])
    C = float(cfg["C"])
    epsilon = float(cfg["epsilon"])
    gamma = cfg["gamma"]  # may be str ("scale", "auto") or float
    rolling_windows = list(cfg["rolling_windows"])

    # Cap lags per engine line 242
    n_lags = min(n_lags, n // 3)

    X, y_target, feature_names = _create_features_reference(
        clean, n_lags, rolling_windows,
    )

    # Dual StandardScaler pipeline per engine lines 257-261
    scaler_X = StandardScaler()
    X_scaled = scaler_X.fit_transform(X)

    scaler_y = StandardScaler()
    y_scaled = scaler_y.fit_transform(y_target.reshape(-1, 1)).ravel()

    # SVR fit per engine lines 265-271
    model = SVR(
        kernel=kernel,
        C=C,
        epsilon=epsilon,
        gamma=gamma,
    )
    model.fit(X_scaled, y_scaled)

    # In-sample predictions with inverse-scaling per engine lines 274-275
    y_pred_scaled = model.predict(X_scaled)
    y_pred_train = scaler_y.inverse_transform(
        y_pred_scaled.reshape(-1, 1)
    ).ravel()
    train_residuals = y_target - y_pred_train
    train_rmse = float(np.sqrt(np.mean(train_residuals ** 2)))
    train_mae = float(np.mean(np.abs(train_residuals)))
    ss_res = float(np.sum(train_residuals ** 2))
    ss_tot = float(np.sum((y_target - np.mean(y_target)) ** 2))
    train_r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Support vector count per engine lines 284-285
    n_sv = model.n_support_ if hasattr(model, "n_support_") else None
    total_sv = (
        int(np.sum(n_sv)) if n_sv is not None else len(model.support_)
    )

    # TimeSeriesSplit CV per engine lines 290-303. Engine reuses
    # pre-computed X_scaled + y_scaled arrays inside CV loop (does
    # NOT re-scale per fold). Predictions inverse-scaled back for
    # RMSE computation on original-scale y_val.
    n_splits = min(3, max(2, len(X) // 20))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_scores = []
    for train_idx, val_idx in tscv.split(X):
        X_tr, X_val = X_scaled[train_idx], X_scaled[val_idx]
        y_tr = y_scaled[train_idx]
        y_val_orig = y_target[val_idx]
        cv_model = SVR(kernel=kernel, C=C, epsilon=epsilon, gamma=gamma)
        cv_model.fit(X_tr, y_tr)
        pred_s = cv_model.predict(X_val)
        pred = scaler_y.inverse_transform(
            pred_s.reshape(-1, 1)
        ).ravel()
        cv_rmse = float(np.sqrt(np.mean((y_val_orig - pred) ** 2)))
        cv_scores.append(cv_rmse)
    avg_cv_rmse = float(np.mean(cv_scores))

    # Multi-step recursive forecast per engine lines 311-323:
    # scale features → predict → inverse-scale → append per step.
    fc_features = _create_forecast_features_reference(
        clean, horizon, n_lags, rolling_windows,
    )
    extended_for_fc = clean.tolist()
    fc_values = []
    for h in range(horizon):
        feat_scaled = scaler_X.transform(fc_features[h].reshape(1, -1))
        pred_scaled = model.predict(feat_scaled)
        pred = float(
            scaler_y.inverse_transform(pred_scaled.reshape(-1, 1))[0, 0]
        )
        fc_values.append(pred)
        extended_for_fc.append(pred)
        if h + 1 < horizon:
            fc_features[h + 1] = _create_forecast_features_reference(
                np.array(extended_for_fc), 1, n_lags, rolling_windows,
            )[0]
    fc_values = np.array(fc_values, dtype=np.float64)

    sv_ratio = (
        float(total_sv) / float(n - n_lags)
        if (n - n_lags) > 0 else 0.0
    )

    return {
        "forecast": fc_values,
        "train_rmse": train_rmse,
        "train_mae": train_mae,
        "train_r2": train_r2,
        "cv_rmse": avg_cv_rmse,
        "n_support_vectors": total_sv,
        "sv_ratio": sv_ratio,
        "n_features": len(feature_names),
        "n_train": int(n - n_lags),
    }


class SvrParity(P3ParityCheck):
    """SVR forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.svr_forecast.run() via
    RunContext + extracts forecast values + audit_fields. Reference
    arm reimplements the same pipeline at Balanced preset (kernel=
    "rbf" + C=10.0 + epsilon=0.05 + gamma="scale" + n_lags=12 +
    rolling_windows=[3, 6, 12]) including dual StandardScaler
    scaling pipeline + inverse-scaling on predictions + recursive
    multi-step forecast with per-step scale → predict → inverse-scale.
    No fallback dispatch (sklearn always available); VSC match YES
    standard framework applies.
    """

    technique_id = "p3_svr"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "sklearn.svm.SVR's libsvm backend is deterministic given "
        "identical inputs + hyperparameters (no random state in the "
        "SMO optimizer; convergence is deterministic from fixed "
        "initialization). Engine and reference reimpl follow "
        "identical pipeline including dual StandardScaler scaling + "
        "inverse-scaling transformations; outputs match at machine "
        "precision modulo engine 6-decimal output-rounding floor at "
        "forecast values + 4-decimal floor at audit metrics. SC5 "
        "architectural transition: first kernel-method session in "
        "Tier A; departs from SC1-SC4 tree-family pattern; reference "
        "arm mirrors scaling pipeline + inverse-scaling exactly."
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.svr_forecast as svr_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_svr_parity",
            "technique_id": "svr_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = svr_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL svr_forecast failed: "
                f"{resp.get('error_message')}"
            )
        # SVR engine produces only Forecast + Model Summary tables
        # (NO Feature Importance table — SVR doesn't expose
        # feature_importances_). Distinct from SC1-SC4 tree-family.
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]], dtype=np.float64,
        )
        audit = resp.get("audit_fields", {})
        return {
            "forecast": forecast,
            "train_rmse": float(audit.get("train_rmse", float("nan"))),
            "train_mae": float(audit.get("train_mae", float("nan"))),
            "train_r2": float(audit.get("train_r2", float("nan"))),
            "cv_rmse": float(audit.get("cv_rmse", float("nan"))),
            "n_support_vectors": int(audit.get("n_support_vectors", 0)),
            "sv_ratio": float(audit.get("sv_ratio", 0.0)),
            "n_features": int(audit.get("n_features", 0)),
            "n_train": int(audit.get("n_train", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_svr(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["sklearn_version"] = sklearn.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding alignment per Phase 1 finding B8:
        # forecast 6-decimal (engine line 332); audit metrics
        # 4-decimal (engine lines 415-418); sv_ratio 4-decimal
        # (engine line 413).
        ref_forecast_rounded = np.round(ref["forecast"], 6)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref_forecast_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast"]["status"])

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

        # Support vector count is an integer; exact match expected
        primary["n_support_vectors"] = {
            "status": (
                "PASS" if tsl["n_support_vectors"] == ref["n_support_vectors"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_support_vectors"]),
            "ref": int(ref["n_support_vectors"]),
        }
        statuses.append(primary["n_support_vectors"]["status"])

        # sv_ratio at engine 4-decimal rounding
        primary["sv_ratio"] = _compare_scalar(
            tsl["sv_ratio"], round(ref["sv_ratio"], 4),
            ladder["primary"],
        )
        statuses.append(primary["sv_ratio"]["status"])

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
                "kernel": str(_ENGINE_BALANCED_PRESET["kernel"]),
                "C": float(_ENGINE_BALANCED_PRESET["C"]),
                "epsilon": float(_ENGINE_BALANCED_PRESET["epsilon"]),
                "gamma": str(_ENGINE_BALANCED_PRESET["gamma"]),
                "sklearn_version": ref.get("sklearn_version", "unknown"),
            },
        )
