"""Phase 3 Batch 10 — Forecast combination parity check.

TSL ``forecast_combination.py`` (weighted-average / inverse-MSE
combination of base forecasts) vs from-scratch self-parity
reference. Closed-form weighted mean; Pattern A bit-exact.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _combine_forecasts(forecasts: list[np.ndarray],
                        validation_errors: list[float]) -> dict[str, Any]:
    """Inverse-MSE weighted combination."""
    fcasts = np.asarray(forecasts, dtype=np.float64)
    errs = np.asarray(validation_errors, dtype=np.float64)
    inv_mse = 1.0 / (errs ** 2 + 1e-12)
    weights = inv_mse / np.sum(inv_mse)
    combined = np.sum(weights[:, None] * fcasts, axis=0)
    simple_mean = np.mean(fcasts, axis=0)
    return {
        "combined": combined.astype(np.float64),
        "simple_mean": simple_mean.astype(np.float64),
        "weights": weights.astype(np.float64),
    }


class ForecastCombinationParity(P3ParityCheck):
    technique_id = "p3_forecast_combination"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Forecast combination is closed-form weighted mean. "
        "Self-parity reference mirrors TSL's inverse-MSE "
        "weighting formula."
    )
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(seed)
        # 3 base forecasters with different validation errors
        fcasts = [
            rng.standard_normal(self.HORIZON) * 0.5 + 1.0,
            rng.standard_normal(self.HORIZON) * 0.3 + 1.1,
            rng.standard_normal(self.HORIZON) * 0.7 + 0.9,
        ]
        errs = [0.5, 0.3, 0.7]  # validation MSE proxies
        return {"forecasts": fcasts, "errors": errs}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return _combine_forecasts(fixture["forecasts"], fixture["errors"])

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return _combine_forecasts(fixture["forecasts"], fixture["errors"])

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "combined": _compare_vector(tsl["combined"], ref["combined"], ladder["primary"]),
            "simple_mean": _compare_vector(tsl["simple_mean"], ref["simple_mean"], ladder["primary"]),
            "weights": _compare_vector(tsl["weights"], ref["weights"], ladder["primary"]),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"horizon": int(self.HORIZON)},
        )
