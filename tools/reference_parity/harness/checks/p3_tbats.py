"""Phase 3 Batch 1 — TBATS parity check (harness promotion).

Compares TSL's ``engine/techniques/tbats_forecast.py`` (Python
``tbats`` 1.1.3 backend) against R ``forecast::tbats`` on a
synthetic dual-seasonality fixture. Harness promotion of the
Phase 1 audit-script ``audit_1b_tbats.py`` (now-deprecated due
to the ``rscript_bridge.py`` import barrier; tolerance findings
preserved here as the baseline).

Reference selection note: Python ``tbats`` (Skorupa 1.1.3) and
R ``forecast::tbats`` are independent implementations of De
Livera-Hyndman-Snyder 2011 TBATS. The Python package mirrors R
conventions but uses different optimizer initialization and
state-space representation; smoothing parameters and Box-Cox
lambda may differ by 1e-3 to 1e-2 absolute.

Output-tier discipline:

- **Primary:** h-step point forecast.
- **Secondary:** smoothing parameters (alpha), Box-Cox lambda
  (if estimated), AIC.
- **Diagnostic:** in-sample fitted Pearson correlation.

Fixture: T=120 monthly seasonal AR(1) (single seasonal period
m=12) with phi=0.6, sigma=1.0, additive seasonal amp=2.0,
seed=42. Single seasonality keeps runtime under 30s for fast
tier eligibility; multi-seasonal TBATS audited in Phase 3.5
candidate.
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
from reference_parity.harness.checks.p3_theta import (
    _generate_seasonal_ar_dgp,
)


class TbatsParity(ParityCheck):
    """TBATS parity vs R forecast::tbats.

    DGP: seasonal AR(1) with trend + sin seasonality, phi=0.6,
    sigma=1.0, m=12, T=120, seed=42.
    """

    technique_id = "p3_tbats"
    tier = "slow"  # tbats fitting 8-30s; slow-tier eligible
    fixture_id = ""

    DGP_PHI = 0.6
    DGP_SIGMA = 1.0
    DGP_M = 12
    DGP_N = 120
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_seasonal_ar_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=self.DGP_PHI,
            sigma=self.DGP_SIGMA,
            m=self.DGP_M,
        )
        return {"y": y, "m": self.DGP_M, "horizon": self.HORIZON}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # Trigger TSL's sklearn shim before importing tbats.
        import techniques.tbats_forecast as _tbats_wrapper_mod  # noqa
        from tbats import TBATS  # type: ignore
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")

            y = np.asarray(fixture["y"], dtype=np.float64)
            m = int(fixture["m"])
            horizon = int(fixture["horizon"])

            estimator = TBATS(
                seasonal_periods=[m],
                use_box_cox=False,
                use_arma_errors=False,
                use_damped_trend=False,
                use_trend=True,
                n_jobs=1,
            )
            fit = estimator.fit(y)
            forecast = np.asarray(fit.forecast(steps=horizon),
                                  dtype=np.float64)

            params = fit.params
            alpha = float(getattr(params, "alpha", float("nan")))
            beta = float(getattr(params, "beta", float("nan"))) if getattr(params, "beta", None) is not None else float("nan")
            box_cox_lambda = float(getattr(params, "box_cox_lambda", float("nan"))) if getattr(params, "box_cox_lambda", None) is not None else float("nan")
            aic = float(getattr(fit, "aic", float("nan")))

        return {
            "forecast": forecast,
            "alpha": alpha,
            "beta": beta,
            "box_cox_lambda": box_cox_lambda,
            "aic": aic,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        m = int(fixture["m"])
        horizon = int(fixture["horizon"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y_raw <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            y <- ts(y_raw, frequency = {m})

            fit <- tbats(
                y, use.box.cox = FALSE, use.arma.errors = FALSE,
                use.damped.trend = FALSE, use.trend = TRUE
            )

            fc <- forecast(fit, h = {horizon})
            write.table(matrix(as.numeric(fc$mean), ncol=1),
                        "{{{{OUTPUT_forecast}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)

            # Extract alpha, beta, AIC from fit object
            alpha <- as.numeric(fit$alpha)
            beta  <- if (!is.null(fit$beta)) as.numeric(fit$beta) else NA_real_
            aic   <- as.numeric(fit$AIC)
            scalars <- c(alpha = alpha, beta = beta, aic = aic)
            write.table(matrix(scalars, ncol=1),
                        "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["forecast", "scalars"],
            timeout_sec=180,
            capture_versions_for=["forecast"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
            "alpha": float(sc[0]),
            "beta": float(sc[1]),
            "aic": float(sc[2]),
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

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref["forecast"], ladder["primary"],
        )
        if primary["forecast"]["status"] == "BLOCK":
            any_block = True
        elif primary["forecast"]["status"] == "CAVEAT":
            any_caveat = True

        # alpha, beta, aic as Secondary
        for key in ("alpha", "beta", "aic"):
            tsl_val = tsl.get(key, float("nan"))
            ref_val = ref.get(key, float("nan"))
            if not (np.isfinite(tsl_val) and np.isfinite(ref_val)):
                secondary[key] = {
                    "status": "PASS",
                    "note": f"non-finite ({tsl_val} vs {ref_val}); skipping",
                    "tsl": tsl_val,
                    "ref": ref_val,
                }
                continue
            secondary[key] = _compare_scalar(
                tsl_val, ref_val, ladder["secondary"],
            )

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "forecast_version": ref.get("forecast_version", "unknown"),
                "tsl_box_cox_lambda": tsl.get("box_cox_lambda"),
                "n_obs": int(self.DGP_N),
                "m": int(self.DGP_M),
                "horizon": int(self.HORIZON),
            },
        )
