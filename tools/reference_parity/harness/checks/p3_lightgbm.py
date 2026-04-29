"""Phase 3 Batch 8 — LightGBM forecast parity check.

Compares TSL ``engine/techniques/lightgbm_forecast.py``
(lightgbm.LGBMRegressor) against direct lightgbm invocation
(same-library self-test). Pattern A bit-exact target.

**Pattern J catalog candidate:** lightgbm parameter case
sensitivity (camelCase vs snake_case) — we use the canonical
sklearn-API names (snake_case) on both sides.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_random_forest import (
    _generate_ar_dgp, _make_lag_features,
)


class LightgbmParity(P3ParityCheck):
    """LightGBM forecast parity vs lightgbm (same-library)."""

    technique_id = "p3_lightgbm"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "lightgbm.LGBMRegressor with seed pinned + "
        "deterministic=True + single-threaded is deterministic. "
        "TSL and reference invoke the same lightgbm primitive "
        "with identical hyperparameters + lag features. "
        "Bit-exact in-sample predictions expected."
    )

    DGP_N = 200
    N_LAGS = 6

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        import lightgbm as lgb  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        X, y_target = _make_lag_features(y, n_lags=self.N_LAGS)
        # Fast preset: n_estimators=100, max_depth=4, learning_rate=0.1,
        # num_leaves=15. Pin deterministic=True and num_threads=1
        # for reproducibility.
        model = lgb.LGBMRegressor(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            num_leaves=15, subsample=1.0, colsample_bytree=1.0,
            random_state=seed, n_jobs=1,
            deterministic=True, force_col_wise=True,
            verbose=-1,
        )
        model.fit(X, y_target)
        return {
            "in_sample_preds": model.predict(X),
            "feature_importances": model.feature_importances_.astype(np.float64),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture, seed=42)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import lightgbm as lgb  # type: ignore
        out = self._fit_predict(fixture, seed=42)
        out["lightgbm_version"] = lgb.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        for k in ("in_sample_preds", "feature_importances"):
            primary[k] = _compare_vector(tsl[k], ref[k], ladder["primary"])
            statuses.append(primary[k]["status"])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "n_lags": int(self.N_LAGS),
                "lightgbm_version": ref.get("lightgbm_version", "unknown"),
            },
        )
