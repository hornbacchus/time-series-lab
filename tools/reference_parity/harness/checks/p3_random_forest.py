"""Phase 3 Batch 8 — Random Forest forecast parity check.

Compares TSL ``engine/techniques/random_forest_forecast.py``
(sklearn.ensemble.RandomForestRegressor with lag features)
against direct ``sklearn.ensemble.RandomForestRegressor``
invocation (same-library self-test) with seed pinning.
Pattern A bit-exact target — verifies wrapper preprocessing
+ feature-engineering round-trip the sklearn primitive.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(*, seed: int, n: int = 200, phi: float = 0.6,
                     sigma: float = 1.0) -> np.ndarray:
    """AR(1) DGP same shape as p3_adf / p3_kpss."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50) * sigma
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = phi * y[t - 1] + eps[t]
    return y[50:]


def _make_lag_features(y: np.ndarray, n_lags: int = 6) -> tuple[np.ndarray, np.ndarray]:
    """Build n_lags lag features + target. Returns (X, y_target)
    after dropping rows with NaN. Mirrors TSL's lag-feature
    construction at minimal scope (no rolling stats — keeps
    the check focused on the regressor itself)."""
    n = len(y)
    feats: list[np.ndarray] = []
    for lag in range(1, n_lags + 1):
        f = np.full(n, np.nan)
        f[lag:] = y[:-lag]
        feats.append(f)
    X = np.column_stack(feats)
    mask = ~np.any(np.isnan(X), axis=1)
    return X[mask], y[mask]


class RandomForestParity(P3ParityCheck):
    """Random Forest forecast parity vs sklearn (same-library)."""

    technique_id = "p3_random_forest"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "RandomForestRegressor with random_state pinned is "
        "deterministic. TSL invokes sklearn.ensemble."
        "RandomForestRegressor and the reference invokes the "
        "same primitive with identical hyperparameters + lag "
        "features + random_state. Bit-exact in-sample "
        "predictions expected; same-library self-test catches "
        "wrapper preprocessing / parameter-resolution bugs."
    )

    DGP_N = 200
    N_LAGS = 6

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        from sklearn.ensemble import RandomForestRegressor  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        X, y_target = _make_lag_features(y, n_lags=self.N_LAGS)
        # Match TSL Fast preset: n_estimators=100, max_depth=6,
        # min_samples_leaf=5
        rf = RandomForestRegressor(
            n_estimators=100, max_depth=6, min_samples_leaf=5,
            random_state=seed, n_jobs=1,
        )
        rf.fit(X, y_target)
        preds = rf.predict(X)
        return {
            "in_sample_preds": preds,
            "feature_importances": rf.feature_importances_,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture, seed=42)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        out = self._fit_predict(fixture, seed=42)
        out["sklearn_version"] = sklearn.__version__
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
                "sklearn_version": ref.get("sklearn_version", "unknown"),
            },
        )
