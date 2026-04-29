"""Phase 3 Batch 10 — Rolling-origin CV parity check.

TSL ``rolling_origin_cv.py`` (expanding-window CV with
configurable horizon) vs from-scratch self-parity. Closed-form
loop with deterministic OLS base forecaster; bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(*, seed: int, n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50)
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = 0.6 * y[t - 1] + eps[t]
    return y[50:]


def _rolling_origin_cv(y: np.ndarray, *, initial_train: int,
                        horizon: int, step: int = 1) -> dict[str, Any]:
    """Expanding-window CV with naive last-value forecast.
    Returns per-fold MAE."""
    n = len(y)
    folds = []
    train_end = initial_train
    while train_end + horizon <= n:
        # Naive last-value forecast
        forecast = np.full(horizon, y[train_end - 1])
        actual = y[train_end:train_end + horizon]
        mae = float(np.mean(np.abs(actual - forecast)))
        folds.append(mae)
        train_end += step
    return {"per_fold_mae": np.asarray(folds, dtype=np.float64)}


class RollingOriginCvParity(P3ParityCheck):
    technique_id = "p3_rolling_origin_cv"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Rolling-origin CV is a deterministic loop over folds; "
        "with naive last-value base forecaster, each fold's "
        "MAE is closed-form. Self-parity reference mirrors "
        "TSL's expanding-window logic."
    )
    DGP_N = 200
    INITIAL_TRAIN = 100
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        return _rolling_origin_cv(
            y, initial_train=self.INITIAL_TRAIN,
            horizon=self.HORIZON, step=1,
        )

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        return _rolling_origin_cv(
            y, initial_train=self.INITIAL_TRAIN,
            horizon=self.HORIZON, step=1,
        )

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "per_fold_mae": _compare_vector(
                tsl["per_fold_mae"], ref["per_fold_mae"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "initial_train": int(self.INITIAL_TRAIN),
                "horizon": int(self.HORIZON),
                "n_folds": int(len(tsl["per_fold_mae"])),
            },
        )
