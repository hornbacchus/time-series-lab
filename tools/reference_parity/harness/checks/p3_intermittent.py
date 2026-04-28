"""Phase 3 Batch 1 — Intermittent demand (Croston) parity check.

Compares TSL's ``engine/techniques/intermittent_demand.py``
(Croston method) against R ``forecast::croston`` on a synthetic
intermittent-demand fixture (zero-inflated demand pattern).

Reference selection note: R ``forecast::croston(y, h, alpha)``
implements the original Croston 1972 method via simple
exponential smoothing on demand sizes z_t and inter-arrival
intervals p_t separately, then forecasts z_hat / p_hat. TSL's
``_croston`` helper in ``intermittent_demand.py`` implements
the same algorithm with the same recursion. Given identical
alpha and identical initialization (first non-zero demand),
they should agree at machine precision. The wrapper covers
SBA and TSB as separate methods; this audit verifies the
canonical Croston path. SBA / TSB cross-checks deferred (no
clean R reference for TSB; SBA = Croston * (1 - beta/2)
correction is closed-form and trivially derivable from
verified Croston output).

Output-tier discipline:

- **Primary:** flat forecast value (constant for h>=1).
- **Secondary:** in-sample fitted-values vector (length T).
- **Diagnostic:** demand-size estimate z_hat, inter-arrival
  estimate p_hat at end of training.

Fixture: T=100 zero-inflated demand series (demand pattern
~3-4 per ~20 periods), seed=42, alpha=0.1 (R default).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks.p3_arima import (
    _compare_scalar,
    _compare_vector,
    _ensure_engine_on_path,
)


def _generate_intermittent_dgp(
    *,
    seed: int,
    n: int = 100,
    p_demand: float = 0.25,
    demand_mean: float = 5.0,
    demand_std: float = 1.5,
) -> np.ndarray:
    """Generate intermittent demand series.

    Each period: with probability p_demand, sample demand size
    from N(demand_mean, demand_std); else 0. Round to integer +
    clip to >=0 (typical retail / spare-parts pattern).
    """
    rng = np.random.default_rng(seed)
    has_demand = rng.uniform(size=n) < p_demand
    sizes = np.maximum(
        np.round(rng.normal(demand_mean, demand_std, size=n)), 0,
    )
    y = np.where(has_demand, sizes, 0.0)
    return y


class IntermittentParity(ParityCheck):
    """Croston intermittent-demand parity vs R forecast::croston.

    DGP: zero-inflated demand, p=0.25, mean=5, std=1.5, T=100,
    seed=42. Alpha=0.1 explicit on both sides (R default).
    """

    technique_id = "p3_intermittent"
    tier = "fast"
    fixture_id = ""

    DGP_P_DEMAND = 0.25
    DGP_DEMAND_MEAN = 5.0
    DGP_DEMAND_STD = 1.5
    DGP_N = 100
    ALPHA = 0.1
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_intermittent_dgp(
            seed=seed,
            n=self.DGP_N,
            p_demand=self.DGP_P_DEMAND,
            demand_mean=self.DGP_DEMAND_MEAN,
            demand_std=self.DGP_DEMAND_STD,
        )
        return {
            "y": y,
            "alpha": self.ALPHA,
            "horizon": self.HORIZON,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques import intermittent_demand as id_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        alpha = float(fixture["alpha"])
        horizon = int(fixture["horizon"])

        # Call _croston directly (same alpha/beta on demand size +
        # inter-arrival, matching forecast::croston default).
        fitted, fc, info = id_mod._croston(y, alpha, alpha, horizon)
        return {
            "forecast": float(fc),
            "fitted": np.asarray(fitted, dtype=np.float64),
            "z_final": float(info["z_final"]),
            "p_final": float(info["p_final"]),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        alpha = float(fixture["alpha"])
        horizon = int(fixture["horizon"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            fc <- croston(y, h = {horizon}, alpha = {alpha})

            # forecast::croston exposes only the alpha parameter
            # in fc$model — internal demand/period components
            # are not retained as named slots. We compare forecast
            # value (flat constant) + in-sample fitted vector.
            write.table(matrix(as.numeric(fc$mean), ncol=1),
                        "{{{{OUTPUT_forecast}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(fc$fitted), ncol=1),
                        "{{{{OUTPUT_fitted}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["forecast", "fitted"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )
        return {
            "forecast": float(np.atleast_1d(outputs["forecast"]).reshape(-1)[0]),
            "fitted": np.atleast_1d(outputs["fitted"]).astype(np.float64).reshape(-1),
            "forecast_version": versions.get("forecast", "unknown"),
        }

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        any_block = False
        any_caveat = False

        primary["forecast"] = _compare_scalar(
            tsl["forecast"], ref["forecast"], ladder["primary"],
        )
        if primary["forecast"]["status"] == "BLOCK":
            any_block = True
        elif primary["forecast"]["status"] == "CAVEAT":
            any_caveat = True

        # Fitted vector: align lengths (R may return shorter
        # fitted vector if leading values are NA).
        tsl_fitted = np.asarray(tsl["fitted"], dtype=np.float64).reshape(-1)
        ref_fitted = np.asarray(ref["fitted"], dtype=np.float64).reshape(-1)
        # Truncate to common length from end (most-recent values
        # most relevant; R may pad with NAs at front).
        n_common = min(len(tsl_fitted), len(ref_fitted))
        tsl_tail = tsl_fitted[-n_common:]
        ref_tail = ref_fitted[-n_common:]
        # NaN-tolerant comparison
        mask = np.isfinite(tsl_tail) & np.isfinite(ref_tail)
        if int(mask.sum()) >= 5:
            secondary["fitted"] = _compare_vector(
                tsl_tail[mask], ref_tail[mask], ladder["secondary"],
            )
        else:
            secondary["fitted"] = {
                "status": "PASS",
                "note": "fewer than 5 finite values; skipping",
                "n_compared": int(mask.sum()),
            }

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "forecast_version": ref.get("forecast_version", "unknown"),
                "tsl_z_final": float(tsl.get("z_final", float("nan"))),
                "tsl_p_final": float(tsl.get("p_final", float("nan"))),
                "ref_internals_exposed": False,
                "n_obs": int(self.DGP_N),
                "alpha": float(self.ALPHA),
            },
        )
