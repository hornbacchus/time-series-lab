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
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _forecast_combo_dgp(*, seed: int, n: int = 120, period: int = 12) -> np.ndarray:
    """Monthly trend + seasonal + noise -- a series the engine can fit ETS/
    ARIMA/Theta to and combine."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64)
    return 100 + 0.4 * t + 6.0 * np.sin(2 * np.pi * t / period) + rng.standard_normal(n) * 1.5


class ForecastCombinationParity(P3ParityCheck):
    technique_id = "p3_forecast_combination"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Phase 4a-harden #1: the engine fits ETS/ARIMA/Theta to a series and "
        "combines them (inverse-MSE) -- there is no isolated 'combine these "
        "forecasts' entry, so no clean independent reference. run_tsl now INVOKES "
        "the engine (was a self-parity formula MIRROR) and asserts STRUCTURAL "
        "INVARIANTS on its actual output: the inverse-MSE weights sum to 1 and are "
        "non-negative, and the combined forecast IS that weighted sum of the "
        "component forecasts. A violated invariant is a real combination defect."
    )
    HORIZON = 12
    DGP_N = 120

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _forecast_combo_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.forecast_combination as fc_mod  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_forecast_combination", "technique_id": "forecast_combination",
            "preset": "Balanced", "seed": 42, "frequency": "M",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        resp = fc_mod.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine forecast_combination failed: {resp.get('error_message')}")
        a = resp.get("audit_fields", {})
        imse_w = a.get("imse_weights", {})  # {model: weight} 4dp
        # Extract component forecasts + the Inv-MSE combined from "Combined Forecasts".
        tbl = next(t for t in resp.get("tables", []) if t.get("name") == "Combined Forecasts")
        cols, rows = tbl["columns"], tbl["rows"]
        model_names = list(imse_w.keys())
        comp = {m: np.array([float(r[cols.index(m)]) for r in rows]) for m in model_names}
        imse_combined = np.array([float(r[cols.index("Inv-MSE")]) for r in rows])
        return {
            "imse_weights": {m: float(w) for m, w in imse_w.items()},
            "component_forecasts": {m: comp[m] for m in model_names},
            "imse_combined": imse_combined,
            "primary_combined": np.asarray(a.get("primary_combined_forecast", []), dtype=np.float64),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # No isolated reference (the engine runs the full fit-and-combine pipeline);
        # validation is via structural invariants on the engine output in compare().
        return {"expected": "weights sum to 1, non-negative; combined == weighted sum of components"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        w = tsl["imse_weights"]
        wsum = sum(w.values())
        comp = tsl["component_forecasts"]
        combined = tsl["imse_combined"]
        # Recompute the weighted sum from the (4dp) weights + (6dp) components.
        recon = np.zeros_like(combined)
        for m, wm in w.items():
            recon = recon + wm * comp[m]
        recon_max_abs = float(np.max(np.abs(recon - combined))) if combined.size else float("inf")
        primary = {
            "weights_sum_to_1": {
                "status": "PASS" if abs(wsum - 1.0) < 1e-3 else "BLOCK",
                "weight_sum": round(wsum, 6), "weights": w,
            },
            "weights_nonnegative": {
                "status": "PASS" if all(v >= -1e-6 for v in w.values()) else "BLOCK",
                "min_weight": round(min(w.values()), 6) if w else None,
            },
            "combined_is_weighted_sum": {
                # 4dp weights x 6dp components vs the engine's full-precision combine
                # -> ~1e-2 floor on forecasts of O(100); a broken combination diverges far more.
                "status": "PASS" if recon_max_abs < 1e-1 else "BLOCK",
                "max_abs_diff": recon_max_abs,
            },
            "combined_finite_and_sized": {
                "status": ("PASS" if (combined.size == self.HORIZON
                                      and np.all(np.isfinite(combined))) else "BLOCK"),
                "len": int(combined.size), "horizon": self.HORIZON,
            },
        }
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"horizon": int(self.HORIZON), "n_models": len(w)},
        )
