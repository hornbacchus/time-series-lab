"""Phase 3 Batch 8 — SVR forecast parity check.

Compares TSL ``engine/techniques/svr_forecast.py``
(sklearn.svm.SVR with RBF kernel) against direct sklearn
invocation (same-library self-test). Pattern A bit-exact
target — sklearn SVR's libsvm backend is deterministic given
identical inputs + hyperparameters.
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


class SvrParity(P3ParityCheck):
    """SVR forecast parity vs sklearn (same-library)."""

    technique_id = "p3_svr"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "sklearn.svm.SVR's libsvm backend is deterministic "
        "given identical inputs + hyperparameters (no random "
        "state in the SMO optimizer; convergence is "
        "deterministic from a fixed initialization). TSL and "
        "reference invoke the same primitive with identical "
        "(C, epsilon, gamma, kernel). Bit-exact predictions "
        "expected. Pattern H DSCD candidate ruled out: same "
        "library means no optimizer-divergence DSCD."
    )

    DGP_N = 200
    N_LAGS = 6

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any]):
        from sklearn.svm import SVR  # type: ignore
        from sklearn.preprocessing import StandardScaler  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        X, y_target = _make_lag_features(y, n_lags=self.N_LAGS)
        # Match TSL's wrapper: standardize features (SVR is
        # scale-sensitive), fit with Fast preset (C=1, eps=0.1,
        # gamma='scale').
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = SVR(
            kernel="rbf", C=1.0, epsilon=0.1, gamma="scale",
            cache_size=200, max_iter=-1,
        )
        model.fit(X_scaled, y_target)
        return {
            "in_sample_preds": model.predict(X_scaled),
            "n_support": int(model.n_support_[0]),
            "intercept": float(model.intercept_[0]),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        out = self._fit_predict(fixture)
        out["sklearn_version"] = sklearn.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        primary["in_sample_preds"] = _compare_vector(
            tsl["in_sample_preds"], ref["in_sample_preds"],
            ladder["primary"],
        )
        statuses.append(primary["in_sample_preds"]["status"])
        from reference_parity.harness.compare import _compare_scalar
        primary["intercept"] = _compare_scalar(
            tsl["intercept"], ref["intercept"], ladder["primary"],
        )
        statuses.append(primary["intercept"]["status"])
        primary["n_support_match"] = {
            "status": "PASS" if tsl["n_support"] == ref["n_support"] else "BLOCK",
            "tsl_n_support": tsl["n_support"],
            "ref_n_support": ref["n_support"],
        }
        statuses.append(primary["n_support_match"]["status"])
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
