"""Phase 3 Batch 5 — Local Linear Trend parity check.

Compares TSL ``engine/techniques/local_linear_trend.py``
(statsmodels UnobservedComponents, level='local linear trend')
against R ``KFAS`` SSMtrend(degree=2). Two-state model:
level + slope.

Pattern I candidate: slope sign ambiguity. State convention
varies — both implementations should produce equivalent
slope estimates after sign-canonicalization.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import (
    _compare_scalar,
    _compare_vector,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks._kalman_helpers import (
    fit_uc_model,
    generate_llt_dgp,
)


class LocalLinearTrendParity(P3ParityCheck):
    """LLT parity vs R KFAS SSMtrend(degree=2)."""

    technique_id = "p3_local_linear_trend"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Local linear trend = level + slope state-space model. "
        "statsmodels UnobservedComponents (level='local linear "
        "trend') and R KFAS SSMtrend(degree=2) implement the "
        "same Kalman MLE. Both maximize log-likelihood over 3 "
        "variances (sigma_eps2, sigma_eta2, sigma_zeta2)."
    )

    DGP_N = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": generate_llt_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        return fit_uc_model(y, level="local linear trend")

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)

        r_code = r"""
            suppressPackageStartupMessages({ library(KFAS) })
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])

            # Local linear trend: 2 state vars (level, slope)
            # SSMtrend(degree=2) needs Q = list(level_var, slope_var)
            mod <- SSModel(
                y ~ SSMtrend(degree=2,
                              Q=list(matrix(NA), matrix(NA))),
                H = matrix(NA)
            )

            inits <- log(c(var(y)/2, var(y)/4, var(y)/8))
            fit <- fitSSM(mod, inits = inits, method = "BFGS")
            mod_fitted <- fit$model

            sigma_eps2 <- as.numeric(mod_fitted$H[1, 1, 1])
            # Q is 2x2 diagonal: Q[1,1] = level var, Q[2,2] = slope var
            Q <- mod_fitted$Q[, , 1]
            sigma_eta2 <- as.numeric(Q[1, 1])
            sigma_zeta2 <- as.numeric(Q[2, 2])

            ks <- KFS(mod_fitted)
            log_lik <- as.numeric(logLik(mod_fitted))
            # alphahat is (T, k_states); for LLT k=2: level + slope
            level_smooth <- as.numeric(ks$alphahat[, 1])
            slope_smooth <- as.numeric(ks$alphahat[, 2])

            scalars <- c(sigma_eps2, sigma_eta2, sigma_zeta2, log_lik)
            write.table(matrix(scalars, ncol=1), "{{OUTPUT_scalars}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(level_smooth, ncol=1),
                        "{{OUTPUT_level_smooth}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(slope_smooth, ncol=1),
                        "{{OUTPUT_slope_smooth}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars", "level_smooth", "slope_smooth"],
            timeout_sec=120,
            capture_versions_for=["KFAS"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "sigma_eps2": float(sc[0]),
            "sigma_eta2": float(sc[1]),
            "sigma_zeta2": float(sc[2]),
            "log_likelihood": float(sc[3]),
            "level_smoothed": np.atleast_1d(outputs["level_smooth"]).astype(np.float64).reshape(-1),
            "slope_smoothed": np.atleast_1d(outputs["slope_smooth"]).astype(np.float64).reshape(-1),
            "kfas_version": versions.get("KFAS", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        for key in ("sigma_eps2", "sigma_eta2", "sigma_zeta2",
                    "log_likelihood"):
            primary[key] = _compare_scalar(
                tsl[key], ref[key], ladder["primary"],
            )
            statuses.append(primary[key]["status"])

        # Smoothed level + slope. statsmodels stores 2-state
        # in smoothed_state shape (T, 2): col 0 = level, col 1 = slope.
        tsl_smoothed = np.asarray(tsl["smoothed_state"], dtype=np.float64)
        if tsl_smoothed.ndim == 2:
            tsl_level = tsl_smoothed[:, 0]
            tsl_slope = tsl_smoothed[:, 1]
        else:
            tsl_level = tsl_smoothed
            tsl_slope = np.full_like(tsl_smoothed, np.nan)

        primary["level_smoothed"] = _compare_vector(
            tsl_level, ref["level_smoothed"], ladder["primary"],
        )
        statuses.append(primary["level_smoothed"]["status"])

        primary["slope_smoothed"] = _compare_vector(
            tsl_slope, ref["slope_smoothed"], ladder["primary"],
        )
        statuses.append(primary["slope_smoothed"]["status"])

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
            },
        )
