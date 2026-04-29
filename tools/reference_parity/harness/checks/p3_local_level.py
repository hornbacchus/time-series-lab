"""Phase 3 Batch 5 — Local Level Model parity check.

Compares TSL ``engine/techniques/local_level.py`` (statsmodels
UnobservedComponents) against R ``KFAS::SSModel`` + ``fitSSM``
+ ``KFS`` on a synthetic local-level DGP.

Local level model: y_t = mu_t + eps_t; mu_t = mu_{t-1} + eta_t.

Structural invariants (Pattern F fourth concrete batch):
- ``kalman_covariance_ordering``: filtered cov ≤ predicted cov;
  smoothed ≤ filtered.
- ``kalman_innovation_positivity``: F_t > 0 ∀ t.
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
from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
)
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks._kalman_helpers import (
    fit_uc_model,
    generate_local_level_dgp,
)


class LocalLevelParity(P3ParityCheck):
    """Local level (random walk + noise) parity vs R KFAS."""

    technique_id = "p3_local_level"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Local level model fit by Kalman MLE. statsmodels "
        "UnobservedComponents and R KFAS implement the same "
        "Kalman filter recursions; both maximize the same "
        "Gaussian likelihood. Closed-form Kalman recursions "
        "given variances; MLE on (sigma_eps2, sigma_eta2). "
        "Achieves Pattern A bit-exact on smoothed states + "
        "log-likelihood when both implementations land at the "
        "same likelihood-optimum variances."
    )

    structural_invariants = (
        StructuralInvariant(
            name="kalman_filter_covariance_ordering",
            invariant_type="kalman_covariance_ordering",
            tolerance=1e-10,
            tolerance_type="absolute",
        ),
        StructuralInvariant(
            name="kalman_innovation_positivity",
            invariant_type="kalman_innovation_positivity",
            tolerance=1e-10,
            tolerance_type="absolute",
        ),
    )

    DGP_N = 200
    DGP_SIGMA_ETA = 1.0
    DGP_SIGMA_EPS = 2.0

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "y": generate_local_level_dgp(
                seed=seed, n=self.DGP_N,
                sigma_eta=self.DGP_SIGMA_ETA,
                sigma_eps=self.DGP_SIGMA_EPS,
            ),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        out = fit_uc_model(y, level="local level")
        # Flatten 1-D state for invariants
        out["filtered_state_cov"] = (
            out["filtered_state_cov"][:, 0, 0]
            if out["filtered_state_cov"] is not None else None
        )
        out["predicted_state_cov"] = (
            out["predicted_state_cov"][:, 0, 0]
            if out["predicted_state_cov"] is not None else None
        )
        out["smoothed_state_cov"] = (
            out["smoothed_state_cov"][:, 0, 0]
            if out["smoothed_state_cov"] is not None else None
        )
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)

        r_code = r"""
            suppressPackageStartupMessages({ library(KFAS) })
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])

            # Local level model: SSModel with single state (level)
            mod <- SSModel(y ~ SSMtrend(degree=1, Q=list(matrix(NA))),
                            H=matrix(NA))

            # Fit via numerical optimization on log(sigma) for
            # Q (state noise) and H (observation noise).
            inits <- log(c(var(y)/2, var(y)/2))
            fit <- fitSSM(mod, inits = inits, method = "BFGS")
            mod_fitted <- fit$model

            # Extract variance estimates
            sigma_eps2 <- as.numeric(mod_fitted$H[1, 1, 1])
            sigma_eta2 <- as.numeric(mod_fitted$Q[1, 1, 1])

            # Run Kalman filter + smoother
            ks <- KFS(mod_fitted, smoothing = c("state", "mean"),
                      filtering = c("state"))
            log_lik <- as.numeric(logLik(mod_fitted))
            smoothed_state <- as.numeric(ks$alphahat[, 1])
            smoothed_cov <- as.numeric(ks$V[1, 1, ])

            scalars <- c(sigma_eps2 = sigma_eps2,
                         sigma_eta2 = sigma_eta2,
                         log_lik = log_lik)
            write.table(matrix(scalars, ncol = 1),
                        "{{OUTPUT_scalars}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(smoothed_state, ncol = 1),
                        "{{OUTPUT_smoothed_state}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(smoothed_cov, ncol = 1),
                        "{{OUTPUT_smoothed_cov}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars", "smoothed_state", "smoothed_cov"],
            timeout_sec=120,
            capture_versions_for=["KFAS"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "sigma_eps2": float(sc[0]),
            "sigma_eta2": float(sc[1]),
            "log_likelihood": float(sc[2]),
            "smoothed_state": np.atleast_1d(outputs["smoothed_state"]).astype(np.float64).reshape(-1),
            "smoothed_state_cov_diag": np.atleast_1d(outputs["smoothed_cov"]).astype(np.float64).reshape(-1),
            "kfas_version": versions.get("KFAS", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["sigma_eps2"] = _compare_scalar(
            tsl["sigma_eps2"], ref["sigma_eps2"], ladder["primary"],
        )
        statuses.append(primary["sigma_eps2"]["status"])

        primary["sigma_eta2"] = _compare_scalar(
            tsl["sigma_eta2"], ref["sigma_eta2"], ladder["primary"],
        )
        statuses.append(primary["sigma_eta2"]["status"])

        primary["log_likelihood"] = _compare_scalar(
            tsl["log_likelihood"], ref["log_likelihood"], ladder["primary"],
        )
        statuses.append(primary["log_likelihood"]["status"])

        # Smoothed state vector (TSL is (T,) for local level)
        tsl_smooth = np.asarray(
            tsl["smoothed_state"], dtype=np.float64,
        ).reshape(-1)
        ref_smooth = np.asarray(
            ref["smoothed_state"], dtype=np.float64,
        ).reshape(-1)
        primary["smoothed_state"] = _compare_vector(
            tsl_smooth, ref_smooth, ladder["primary"],
        )
        statuses.append(primary["smoothed_state"]["status"])

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
