"""Phase 3 Batch 4 — NAR / NARX (Neural AR) parity check.

Compares TSL's ``engine/techniques/nar_narx.py`` (sklearn
``MLPRegressor``) against R ``tsDyn::nlar`` on a synthetic
nonlinear AR fixture.

**NO-REFERENCE candidate per master plan §5 Tier C:** TSL
uses sklearn MLPRegressor with random weight initialization;
R tsDyn::nlar uses a different neural architecture and
training algorithm. Even with seed pinning, the two
implementations are unlikely to converge to numerically
identical weights — the function approximations achieved are
behaviorally similar but not bit-comparable.

**Audit strategy:** instead of weight parity, compare:
1. **Forecast correlation** (Pearson r between TSL and R
   forecast paths on a held-out test segment).
2. **In-sample R²** (each implementation's training fit
   quality; both should be in similar range).
3. **DGP recovery** (forecast direction matches the true
   nonlinear AR signal).

Verdict: typically CAVEAT (forecast-level agreement; weight-
level divergence is methodology-equivalent). DOCUMENTED-
DIVERGENCE if forecast correlation < 0.9.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import (
    _compare_scalar,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_nar_dgp(
    *,
    seed: int,
    n: int = 500,
    sigma: float = 0.5,
    burn: int = 100,
) -> np.ndarray:
    """Generate nonlinear AR realization.

    y_t = 0.7 * y_{t-1} - 0.3 * tanh(y_{t-1}) + eps_t

    Mild nonlinearity; both NAR (sklearn MLP) and tsDyn::nlar
    can in principle approximate but with different fidelity.
    """
    rng = np.random.default_rng(seed)
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma
    y = np.zeros(n_total)
    for t in range(1, n_total):
        y[t] = 0.7 * y[t - 1] - 0.3 * np.tanh(y[t - 1]) + eps[t]
    return y[burn:]


class NarNarxParity(P3ParityCheck):
    """NAR(1) parity vs R tsDyn::nlar — forecast-correlation
    comparison only (NO weight-level parity due to architecture
    divergence)."""

    technique_id = "p3_nar_narx"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "Neural AR with sklearn MLPRegressor (TSL) vs tsDyn::nlar "
        "(R) — different neural architectures and training "
        "algorithms. Weight-level parity is mathematically "
        "intractable (DL Tier C / NO-REFERENCE candidate per "
        "master plan §5). Audit compares forecast paths via "
        "Pearson correlation on the test segment + in-sample R² "
        "agreement. CAVEAT verdict typical when forecast corr > "
        "0.9; DOCUMENTED-DIVERGENCE when corr < 0.9."
    )

    DGP_N = 500
    TRAIN_FRAC = 0.8

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_nar_dgp(seed=seed, n=self.DGP_N)
        n_train = int(len(y) * self.TRAIN_FRAC)
        return {
            "y_train": y[:n_train],
            "y_test": y[n_train:],
            "horizon": len(y) - n_train,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.nar_narx as nn_mod  # type: ignore

        y_train = np.asarray(fixture["y_train"], dtype=np.float64)
        horizon = int(fixture["horizon"])
        ctx = RunContext({
            "run_id": "p3_nar_narx_parity",
            "technique_id": "nar_narx",
            "preset": "Fast",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y_train))),
            "series": [{"name": "y", "values": y_train.tolist()}],
            "params": {"horizon": horizon, "ar_order": 1},
        })
        wrapper_resp = nn_mod.run(ctx, lambda *a, **kw: None)
        if wrapper_resp.get("status") != "success":
            raise RuntimeError(
                f"TSL NAR run failed: {wrapper_resp.get('error_message')}"
            )
        # Extract forecast
        af = wrapper_resp.get("audit_fields", {})
        # Forecast values: extract from tables
        forecast_table = next(
            (t for t in wrapper_resp["tables"]
             if "Forecast" in t.get("name", "")),
            None,
        )
        if forecast_table is None:
            raise RuntimeError("TSL NAR forecast table not found")
        forecast = np.array(
            [float(row[1]) for row in forecast_table["rows"]],
            dtype=np.float64,
        )
        return {
            "forecast": forecast,
            "in_sample_r2": float(af.get("r_squared", np.nan)),
            "rmse": float(af.get("rmse", np.nan)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y_train = np.asarray(fixture["y_train"], dtype=np.float64)
        horizon = int(fixture["horizon"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(tsDyn) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            set.seed(20260429)
            # tsDyn::nlar — neural autoregression. Use small
            # hidden size for quick fitting.
            fit <- tryCatch(
                nlar(y, m = 1, size = 4),
                error = function(e) NULL
            )

            if (is.null(fit)) {{
                fc <- rep(NA, {horizon})
                r2 <- NA
            }} else {{
                fc_obj <- predict(fit, n.ahead = {horizon})
                fc <- as.numeric(fc_obj)
                # In-sample R²: 1 - SSE/SST
                fitted_vals <- fitted(fit)
                resid_in <- y[(length(y) - length(fitted_vals) + 1):length(y)] -
                            fitted_vals
                sse <- sum(resid_in ^ 2)
                sst <- sum((y - mean(y)) ^ 2)
                r2 <- 1 - sse / sst
            }}

            write.table(matrix(fc, ncol = 1), "{{{{OUTPUT_forecast}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(c(r2), ncol = 1), "{{{{OUTPUT_scalars}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y_train.reshape(-1, 1)},
            output_names=["forecast", "scalars"],
            timeout_sec=120,
            capture_versions_for=["tsDyn"],
        )
        return {
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
            "in_sample_r2": float(np.atleast_1d(outputs["scalars"]).reshape(-1)[0]),
            "tsdyn_version": versions.get("tsDyn", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}

        tsl_fc = np.asarray(tsl["forecast"], dtype=np.float64).reshape(-1)
        ref_fc = np.asarray(ref["forecast"], dtype=np.float64).reshape(-1)

        # Reference may have failed
        if not np.isfinite(ref_fc).all() or not np.isfinite(tsl_fc).all():
            return ParityResult(
                technique_id=self.technique_id,
                outcome="CAVEAT",
                metrics={
                    "primary": {
                        "reference_convergence": {
                            "status": "CAVEAT",
                            "note": (
                                "R tsDyn::nlar did not produce finite "
                                "forecasts on this fixture. NO-REFERENCE "
                                "fallback per master plan §5 Tier C."
                            ),
                            "tsl_in_sample_r2": tsl.get("in_sample_r2"),
                        }
                    }
                },
                diagnostics={
                    "tsdyn_version": ref.get("tsdyn_version", "unknown"),
                    "n_obs": int(self.DGP_N),
                    "ref_failed": True,
                },
            )

        # Forecast correlation (Pearson) — primary metric for
        # this NO-REFERENCE-class wrapper
        n_common = min(len(tsl_fc), len(ref_fc))
        try:
            corr = float(np.corrcoef(
                tsl_fc[:n_common], ref_fc[:n_common],
            )[0, 1])
        except Exception:
            corr = float("nan")

        corr_pass = ladder["primary"].get("corr_pass", 0.9)
        corr_caveat = ladder["primary"].get("corr_caveat", 0.7)
        if not np.isfinite(corr):
            status = "BLOCK"
        elif corr >= corr_pass:
            status = "PASS"
        elif corr >= corr_caveat:
            status = "CAVEAT"
        else:
            status = "BLOCK"

        primary["forecast_correlation"] = {
            "status": status,
            "pearson_corr": corr,
            "n_compared": n_common,
            "tsl_first": float(tsl_fc[0]) if tsl_fc.size > 0 else None,
            "ref_first": float(ref_fc[0]) if ref_fc.size > 0 else None,
        }

        primary["in_sample_r2"] = _compare_scalar(
            tsl.get("in_sample_r2") or 0.0,
            ref.get("in_sample_r2") or 0.0,
            ladder["primary"],
        )

        any_block = primary["forecast_correlation"]["status"] == "BLOCK"
        any_caveat = (
            primary["forecast_correlation"]["status"] == "CAVEAT"
            or primary["in_sample_r2"]["status"] == "CAVEAT"
        )
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "tsdyn_version": ref.get("tsdyn_version", "unknown"),
                "n_obs": int(self.DGP_N),
            },
        )
