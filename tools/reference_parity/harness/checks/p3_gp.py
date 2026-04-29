"""Phase 3 Batch 9 — Gaussian Process forecast parity check.

Compares TSL ``engine/techniques/gaussian_process_forecast.py``
(sklearn.gaussian_process.GaussianProcessRegressor with
RBF + WhiteKernel) against direct sklearn invocation (same-
library self-test). Pattern A same-library bit-exact target.

Master plan §15.11 named GPyTorch as reference, but TSL's
wrapper actually uses sklearn (NOT GPyTorch). Self-parity
against sklearn is the practical reference.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_lstm_gru import _generate_ar_dgp


class GpParity(P3ParityCheck):
    """GP forecast parity (sklearn same-library)."""

    technique_id = "p3_gp"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "sklearn.gaussian_process.GaussianProcessRegressor with "
        "RBF + WhiteKernel and random_state pinned: the L-BFGS-B "
        "hyperparameter optimization with fixed n_restarts and "
        "fixed seed is deterministic. Same-library self-test "
        "verifies wrapper preprocessing round-trips the sklearn "
        "primitive."
    )

    DGP_N = 100
    LOOKBACK = 6

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        from sklearn.gaussian_process import (  # type: ignore
            GaussianProcessRegressor,
        )
        from sklearn.gaussian_process.kernels import (  # type: ignore
            RBF, WhiteKernel,
        )
        np.random.seed(seed)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Build (n_samples, lookback) feature matrix
        n_seq = len(y) - self.LOOKBACK
        X = np.zeros((n_seq, self.LOOKBACK))
        target = np.zeros(n_seq)
        for i in range(n_seq):
            X[i] = y[i:i + self.LOOKBACK]
            target[i] = y[i + self.LOOKBACK]
        kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
        gp = GaussianProcessRegressor(
            kernel=kernel, n_restarts_optimizer=2,
            random_state=seed, normalize_y=True,
        )
        gp.fit(X, target)
        preds = gp.predict(X)
        return {
            "in_sample_preds": preds,
            "log_marginal_likelihood": float(gp.log_marginal_likelihood_value_),
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
        primary["in_sample_preds"] = _compare_vector(
            tsl["in_sample_preds"], ref["in_sample_preds"],
            ladder["primary"],
        )
        statuses.append(primary["in_sample_preds"]["status"])
        primary["log_marginal_likelihood"] = _compare_scalar(
            tsl["log_marginal_likelihood"],
            ref["log_marginal_likelihood"],
            ladder["primary"],
        )
        statuses.append(primary["log_marginal_likelihood"]["status"])
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
                "lookback": int(self.LOOKBACK),
                "sklearn_version": ref.get("sklearn_version", "unknown"),
            },
        )
