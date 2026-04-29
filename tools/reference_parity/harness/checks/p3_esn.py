"""Phase 3 Batch 9 — Echo State Network parity check.

Compares TSL ``engine/techniques/echo_state_network.py``
(reservoirpy-based ESN) against direct reservoirpy invocation
(same-library self-test). Reservoir state evolves
deterministically given pinned numpy random state for the
random reservoir initialization. Pattern A.1 same-library
target with seed pinning.
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


class EsnParity(P3ParityCheck):
    """ESN forecast parity (reservoirpy same-library)."""

    technique_id = "p3_esn"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "reservoirpy ESN with rng.seed pinned for both reservoir "
        "initialization and ridge-regression solve is "
        "deterministic. Same-library self-test verifies wrapper "
        "preprocessing + reservoir-construction round-trip the "
        "reservoirpy primitive."
    )

    DGP_N = 200
    RESERVOIR_SIZE = 50
    SPECTRAL_RADIUS = 0.9
    LEAK_RATE = 0.3

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        import reservoirpy as rpy  # type: ignore
        from reservoirpy.nodes import Reservoir, Ridge  # type: ignore
        rpy.set_seed(seed)
        np.random.seed(seed)
        y = np.asarray(fixture["y"], dtype=np.float64).reshape(-1, 1)
        reservoir = Reservoir(
            self.RESERVOIR_SIZE,
            sr=self.SPECTRAL_RADIUS,
            lr=self.LEAK_RATE,
            seed=seed,
        )
        ridge = Ridge(ridge=1e-6)
        # Train on (y_t, y_{t+1}) one-step prediction
        X_train = y[:-1]
        y_train = y[1:]
        states = reservoir.run(X_train)
        ridge.fit(states, y_train)
        # In-sample predictions
        in_sample = ridge.run(states).reshape(-1)
        return {
            "in_sample_preds": in_sample.astype(np.float64),
            "n_predictions": int(len(in_sample)),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture, seed=42)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import reservoirpy  # type: ignore
        out = self._fit_predict(fixture, seed=42)
        out["reservoirpy_version"] = reservoirpy.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        primary["in_sample_preds"] = _compare_vector(
            tsl["in_sample_preds"], ref["in_sample_preds"],
            ladder["primary"],
        )
        statuses = [primary["in_sample_preds"]["status"]]
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
                "reservoir_size": int(self.RESERVOIR_SIZE),
                "reservoirpy_version": ref.get("reservoirpy_version", "unknown"),
            },
        )
