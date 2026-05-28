"""Phase 3 Batch 8 — Quantile regression forecast parity check.

TSL ``engine/techniques/quantile_regression_model.py`` (sklearn
GradientBoostingRegressor with loss="quantile" at 7 quantile alphas
for Balanced preset + multi-quantile recursive forecasting +
prediction interval table construction) vs from-scratch paper-formula
reimpl mirroring engine pipeline exactly. Reference uses identical
sklearn primitives at identical hyperparameters at IDENTICAL
quantile alphas including auto-injected median (0.5) so any
divergence isolates engine wrapper orchestration vs paper-formula
reference.

Rewritten at SC6-side Cat 3 remediation cycle session 6/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern + family template + SC4-established two-
stage helper identity verification + SC5-established pre-fit /
post-fit pipeline scanning. SC6 closes Tier A tree-family ML
cohort (SC1 RF + SC2 GBR + SC3 XGB + SC4 LGB + SC5 SVR + SC6 QR).

**Helper identity verification (Step 1 of SC6 workflow per SC4
two-stage methodology):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at QR engine lines 37-57: MATCH SC1 RF
  (hash 57bae54d463c2fd7)
- `_create_features` at QR engine lines 60-103: DIFFER SC1 RF
  (RF=f69ca3848531a82c vs QR=5655a18ea743ce57)
- `_create_forecast_features` ABSENT — QR engine does NOT have
  this function; uses `_build_forecast_features` (single-step
  builder, lines 106-136) instead

Stage 2 (manual code inspection per SC4 methodology):
- `_create_features`: BEHAVIORAL DIVERGENCE — QR version OMITS
  the early-exit guard `if n <= max_lookback + 1: return None,
  None, None` (RF lines 64-68). All other lines byte-identical;
  divergence inert at parity fixture (n=200 >> max_lookback+1=13).
  Reimplemented as `_reference_quantile_create_features` to
  preserve institutional honesty + match engine source exactly.
- `_build_forecast_features` (NEW QR-specific helper): single-step
  feature vector builder (vs RF's batch builder); called
  iteratively per recursive step per quantile (QR's per-quantile-
  trajectory forecast pattern distinct from SC1-SC5 single-
  trajectory recursive forecast). Reimplemented as
  `_reference_quantile_build_forecast_features`.

`_prepare_series_reference` reused from SC1 (Stage 1 MATCH).

**SC6 architectural elements (multi-quantile pattern; SC1-SC5
single-trajectory pattern variant):**

1. **Multi-quantile model fitting:** engine lines 226-242 trains
   ONE GBR model per quantile alpha (7 models for Balanced preset).
   Quantile alphas: [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95].
2. **Forced 0.5 median auto-injection:** engine lines 208-210 add
   0.5 to quantiles if absent (Balanced preset already includes
   0.5; injection no-op for our fixture).
3. **Per-quantile recursive forecast trajectory:** engine lines
   246-256 produce ONE forecast trajectory per quantile (each
   quantile model's predictions extend its own recursive sequence;
   no shared median-based extension).
4. **3-table output structure:** Quantile Forecasts (wide format:
   Step + Q-columns; one row per horizon step) + Prediction
   Intervals (Step + Median + paired Lower/Upper columns) + Model
   Summary. Distinct from SC1-SC5 patterns (SC1-SC4 had Forecast
   + Model Summary + Feature Importance; SC5 had Forecast + Model
   Summary only).
5. **No CV computation:** engine does NOT compute cv_rmse; only
   median model train_rmse + train_mae reported.
6. **No fallback dispatch:** sklearn always available; SC3
   template element NOT APPLICABLE.
7. **No scaling pipeline:** unlike SC5 SVR; SC5 pre-fit /
   post-fit scaling refinement NOT APPLICABLE at SC6.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic seed; bit-exact target on
per-quantile forecast values + audit_fields modulo engine 6-decimal
rounding at forecast values (engine lines 266 + 275 + 283) +
4-decimal at audit metrics (engine lines 374-375).
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
    _prepare_series_reference,
)


# Engine preset Balanced config (engine `quantile_regression_model.py`
# lines 24-28). Mirrored verbatim per Disposition 2. Note QR-specific
# `quantiles` field (list of alphas) absent from SC1-SC5 presets.
_ENGINE_BALANCED_PRESET = {
    "n_estimators": 200,
    "max_depth": 4,
    "learning_rate": 0.05,
    "n_lags": 12,
    "rolling_windows": [3, 6, 12],
    "quantiles": [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95],
}


def _reference_quantile_create_features(series, n_lags, rolling_windows):
    """Reference reimpl of engine `_create_features` at QR engine
    lines 60-103. BEHAVIORAL DIVERGENCE from SC1 RF: QR version
    OMITS the early-exit guard at RF lines 64-68. All other lines
    byte-identical. For our parity fixture (n=200 >> max_lookback+1
    =13), divergence is inert; reimplemented here to match QR engine
    source exactly per institutional honesty.
    """
    n = len(series)
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
    X = X[valid_mask]
    y = y[valid_mask]
    return X, y, feature_names


def _reference_quantile_build_forecast_features(
    series, n_lags, rolling_windows,
):
    """Reference reimpl of engine `_build_forecast_features` at QR
    engine lines 106-136. Single-step feature vector builder (vs
    SC1-SC5 batch builder). Called iteratively per recursive step
    per quantile per QR's per-quantile-trajectory forecast pattern.
    """
    n = len(series)
    feat = []
    for lag in range(1, n_lags + 1):
        if n - lag >= 0:
            feat.append(series[n - lag])
        else:
            feat.append(0.0)
    for w in rolling_windows:
        if n >= w:
            feat.append(np.mean(series[n - w:n]))
        else:
            feat.append(np.mean(series))
    for w in rolling_windows:
        if w >= 3 and n >= w:
            feat.append(np.std(series[n - w:n], ddof=1))
        elif w >= 3:
            feat.append(0.0)
    if n >= 2:
        feat.append(series[-1] - series[-2])
    else:
        feat.append(0.0)
    feat.append(n / len(series))
    return np.array(feat)


def _reference_quantile_regression(
    y: np.ndarray, *, seed: int, horizon: int = 10, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl that mirrors engine `quantile_regression_model.
    run()` pipeline at lines 152-399: prepare_series + create_features
    (QR-specific) + auto-inject 0.5 if absent + train one GBR model
    per quantile alpha at engine-resolved hyperparameters with
    loss="quantile" + per-quantile recursive forecast trajectory +
    crossing detection.
    """
    from sklearn.ensemble import GradientBoostingRegressor  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    clean, n_interp = _prepare_series_reference(y)
    n = len(clean)

    n_lags = int(cfg["n_lags"])
    n_estimators = int(cfg["n_estimators"])
    max_depth = int(cfg["max_depth"])
    learning_rate = float(cfg["learning_rate"])
    rolling_windows = list(cfg["rolling_windows"])
    quantiles = sorted([float(q) for q in cfg["quantiles"]])

    # Ensure 0.5 in quantiles per engine lines 208-210
    if 0.5 not in quantiles:
        quantiles.append(0.5)
        quantiles.sort()

    # Cap lags per engine line 212
    n_lags = min(n_lags, n // 3)

    X, y_target, feature_names = _reference_quantile_create_features(
        clean, n_lags, rolling_windows,
    )

    # Train one GBR per quantile per engine lines 226-242
    models = {}
    for q in quantiles:
        model = GradientBoostingRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            loss="quantile",
            alpha=q,
            random_state=seed,
        )
        model.fit(X, y_target)
        models[q] = model

    # Per-quantile recursive forecast per engine lines 246-256
    quantile_forecasts = {q: [] for q in quantiles}
    for q in quantiles:
        extended = clean.tolist()
        for h in range(horizon):
            feat = _reference_quantile_build_forecast_features(
                np.array(extended), n_lags, rolling_windows,
            )
            pred = float(models[q].predict(feat.reshape(1, -1))[0])
            quantile_forecasts[q].append(pred)
            extended.append(pred)

    # In-sample median model metrics per engine lines 296-300
    median_model = models[0.5]
    y_pred = median_model.predict(X)
    residuals = y_target - y_pred
    train_rmse = float(np.sqrt(np.mean(residuals ** 2)))
    train_mae = float(np.mean(np.abs(residuals)))

    # Quantile crossing count per engine lines 303-308
    n_crossings = 0
    for i in range(horizon):
        vals = [quantile_forecasts[q][i] for q in quantiles]
        for j in range(len(vals) - 1):
            if vals[j] > vals[j + 1]:
                n_crossings += 1

    # Flatten quantile forecasts into a single ordered vector for
    # parity comparison (quantile-major: all Q[0] values, then all
    # Q[1] values, ...). Matches engine's table-row construction
    # which is step-major but a flat comparison vector covers both.
    fc_flat = np.array(
        [quantile_forecasts[q][i] for q in quantiles for i in range(horizon)],
        dtype=np.float64,
    )

    return {
        "forecast_flat": fc_flat,
        "n_quantiles": len(quantiles),
        "quantiles": list(quantiles),
        "horizon": horizon,
        "train_rmse_median": train_rmse,
        "train_mae_median": train_mae,
        "n_crossings": int(n_crossings),
        "n_features": len(feature_names),
    }


class QuantileRegressionParity(P3ParityCheck):
    """Quantile regression forecast parity vs from-scratch paper-
    formula reimpl.

    Engine arm invokes engine.techniques.quantile_regression_model.run()
    via RunContext + extracts per-quantile forecast values + audit_fields.
    Reference arm reimplements the same pipeline at Balanced preset
    (n_estimators=200 + max_depth=4 + learning_rate=0.05 + n_lags=12 +
    rolling_windows=[3, 6, 12] + 7 quantiles [0.05, 0.1, 0.25, 0.5,
    0.75, 0.9, 0.95]) including auto-0.5 injection + per-quantile
    recursive forecast trajectory + quantile crossing detection.
    """

    technique_id = "p3_quantile_regression"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "sklearn GradientBoostingRegressor with loss='quantile' at "
        "random_state=ctx.seed is deterministic at fixed seed (triage "
        "bit-exact confirmation). Engine and reference reimpl follow "
        "identical multi-quantile pipeline (one GBR fit per quantile "
        "alpha at 7 alphas for Balanced + per-quantile recursive "
        "forecast trajectory); forecast values match at machine "
        "precision modulo engine 6-decimal rounding floor."
    )

    DGP_N = 200
    HORIZON = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.quantile_regression_model as qr_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_quantile_regression_parity",
            "technique_id": "quantile_regression",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = qr_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL quantile_regression failed: "
                f"{resp.get('error_message')}"
            )
        # Extract "Quantile Forecasts" table — wide format with
        # Step column + one Q-column per quantile alpha
        fc_table = next(
            (t for t in resp["tables"]
             if t.get("name") == "Quantile Forecasts"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Quantile Forecasts' table")
        rows = fc_table["rows"]
        cols = fc_table["columns"]
        n_q = len(cols) - 1  # subtract Step column
        # rows are step-major; flatten to quantile-major for parity:
        # for each quantile column index j (1..n_q), collect all
        # step values at row[j].
        fc_flat = []
        for j in range(1, n_q + 1):
            for row in rows:
                fc_flat.append(float(row[j]))
        fc_flat = np.array(fc_flat, dtype=np.float64)

        audit = resp.get("audit_fields", {})
        return {
            "forecast_flat": fc_flat,
            "n_quantiles": int(audit.get("n_quantiles", 0)),
            "quantiles": list(audit.get("quantiles", [])),
            "horizon": int(audit.get("horizon", 0)),
            "train_rmse_median": float(audit.get("train_rmse_median", float("nan"))),
            "n_crossings": int(audit.get("n_crossings", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_quantile_regression(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["sklearn_version"] = sklearn.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounds forecast values to 6 decimals at engine line
        # 266 (Quantile Forecasts table); train metrics to 4 decimals
        # at audit lines 374-375. Round REF outputs to match per
        # Phase 1 finding B8.
        ref_forecast_rounded = np.round(ref["forecast_flat"], 6)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast_flat"] = _compare_vector(
            tsl["forecast_flat"], ref_forecast_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast_flat"]["status"])

        primary["train_rmse_median"] = _compare_scalar(
            tsl["train_rmse_median"], round(ref["train_rmse_median"], 4),
            ladder["primary"],
        )
        statuses.append(primary["train_rmse_median"]["status"])

        # Integer n_crossings exact match
        primary["n_crossings"] = {
            "status": (
                "PASS" if tsl["n_crossings"] == ref["n_crossings"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_crossings"]),
            "ref": int(ref["n_crossings"]),
        }
        statuses.append(primary["n_crossings"]["status"])

        # Integer n_quantiles exact match (auto-0.5 injection verification)
        primary["n_quantiles"] = {
            "status": (
                "PASS" if tsl["n_quantiles"] == ref["n_quantiles"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_quantiles"]),
            "ref": int(ref["n_quantiles"]),
        }
        statuses.append(primary["n_quantiles"]["status"])

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
                "learning_rate": float(_ENGINE_BALANCED_PRESET["learning_rate"]),
                "quantiles": list(_ENGINE_BALANCED_PRESET["quantiles"]),
                "sklearn_version": ref.get("sklearn_version", "unknown"),
            },
        )
