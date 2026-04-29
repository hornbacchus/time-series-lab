"""Phase 3 Batch 5 — Structural TS parity check.

Compares TSL ``engine/techniques/structural_ts.py``
(statsmodels UnobservedComponents with level + trend +
seasonal) against R ``KFAS`` (SSMtrend + SSMseasonal).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks._kalman_helpers import (
    fit_uc_model,
    generate_structural_dgp,
)


class StructuralTsParity(P3ParityCheck):
    """Structural TS parity vs R KFAS."""

    technique_id = "p3_structural_ts"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Structural TS = level + trend + seasonal state-space "
        "model. statsmodels UnobservedComponents and R KFAS "
        "implement the same Kalman MLE; both maximize log-"
        "likelihood over 4 variances (eps, level, trend, "
        "seasonal). Multi-component model has more parameters "
        "to identify; achievable PASS at MLE-fit band."
    )

    DGP_N = 240
    DGP_M = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": generate_structural_dgp(seed=seed, n=self.DGP_N,
                                              m=self.DGP_M)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        return fit_uc_model(
            y, level="local linear trend",
            seasonal=self.DGP_M, stochastic_seasonal=True,
        )

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        m = self.DGP_M

        r_code = rf"""
            suppressPackageStartupMessages({{ library(KFAS) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            mod <- SSModel(
                y ~ SSMtrend(degree=2,
                              Q=list(matrix(NA), matrix(NA))) +
                    SSMseasonal(period={m}, sea.type="dummy",
                                Q=matrix(NA)),
                H = matrix(NA)
            )

            inits <- log(c(var(y)/2, var(y)/4, var(y)/16, var(y)/4))
            fit <- fitSSM(mod, inits = inits, method = "BFGS")
            mod_fitted <- fit$model

            sigma_eps2 <- as.numeric(mod_fitted$H[1, 1, 1])
            Q <- mod_fitted$Q[, , 1]
            sigma_eta2 <- as.numeric(Q[1, 1])
            sigma_zeta2 <- as.numeric(Q[2, 2])
            sigma_omega2 <- as.numeric(Q[3, 3])

            log_lik <- as.numeric(logLik(mod_fitted))

            scalars <- c(sigma_eps2, sigma_eta2, sigma_zeta2,
                         sigma_omega2, log_lik)
            write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars"],
            timeout_sec=180,
            capture_versions_for=["KFAS"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "sigma_eps2": float(sc[0]),
            "sigma_eta2": float(sc[1]),
            "sigma_zeta2": float(sc[2]),
            "sigma_omega2": float(sc[3]),
            "log_likelihood": float(sc[4]),
            "kfas_version": versions.get("KFAS", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        for key in ("sigma_eps2", "sigma_eta2", "sigma_zeta2",
                    "sigma_omega2", "log_likelihood"):
            tsl_v = tsl.get(key)
            ref_v = ref.get(key)
            if tsl_v is None or ref_v is None or not np.isfinite(tsl_v):
                primary[key] = {
                    "status": "CAVEAT",
                    "note": f"tsl={tsl_v} ref={ref_v}",
                }
                statuses.append("CAVEAT")
                continue
            primary[key] = _compare_scalar(tsl_v, ref_v, ladder["primary"])
            statuses.append(primary[key]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "kfas_version": ref.get("kfas_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "m": int(self.DGP_M),
            },
        )
