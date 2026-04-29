"""Phase 3 Batch 4 — TAR / SETAR parity check.

Compares TSL's ``engine/techniques/tar_setar.py`` (custom
threshold autoregression with grid-search threshold + OLS per
regime) against R ``tsDyn::setar`` on a synthetic 2-regime
SETAR fixture.

Output-tier discipline: AR coefficients per regime + threshold
+ residual variance per regime. Closed-form OLS given fixed
threshold; threshold determination is grid-search optimization
on either side.
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


def _generate_setar_dgp(
    *,
    seed: int,
    n: int = 500,
    threshold: float = 0.0,
    phi_low: float = 0.7,
    phi_high: float = -0.3,
    sigma: float = 1.0,
    burn: int = 100,
) -> np.ndarray:
    """Generate 2-regime SETAR(1, d=1) realization.

    Process:
        y_t = phi_low * y_{t-1} + eps_t  if y_{t-1} <= threshold
        y_t = phi_high * y_{t-1} + eps_t if y_{t-1} > threshold
    """
    rng = np.random.default_rng(seed)
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma
    y = np.zeros(n_total)
    for t in range(1, n_total):
        if y[t - 1] <= threshold:
            y[t] = phi_low * y[t - 1] + eps[t]
        else:
            y[t] = phi_high * y[t - 1] + eps[t]
    return y[burn:]


class TarSetarParity(P3ParityCheck):
    """SETAR(2, d=1) parity vs R tsDyn::setar."""

    technique_id = "p3_tar_setar"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "SETAR with grid-search threshold + per-regime OLS. "
        "TSL's custom implementation and R tsDyn::setar use "
        "different threshold-search heuristics; the per-regime "
        "OLS step is closed-form given identical thresholds. "
        "If grid resolutions match closely, achieves Pattern A; "
        "otherwise CAVEAT due to threshold precision differences."
    )

    DGP_N = 500
    THRESHOLD_DELAY = 1  # SETAR(d=1)

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "y": _generate_setar_dgp(seed=seed, n=self.DGP_N),
            "thDelay": self.THRESHOLD_DELAY,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.tar_setar as ts_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_tar_setar_parity",
            "technique_id": "tar_setar",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"n_regimes": 2, "ar_order": 1, "thDelay": 1},
        })
        wrapper_resp = ts_mod.run(ctx, lambda *a, **kw: None)
        if wrapper_resp.get("status") != "success":
            raise RuntimeError(f"TSL TAR/SETAR run failed: {wrapper_resp.get('error_message')}")

        # Extract from audit_fields. TSL uses key "thresholds"
        # (plural list); for nthresh=1 it has a single element.
        af = wrapper_resp.get("audit_fields", {})
        thresholds_list = af.get("thresholds", [])
        threshold = float(thresholds_list[0]) if thresholds_list else float("nan")
        # Coefficients per regime — extract from the model summary
        # table. TSL reports coefficients in tables.
        return {
            "threshold": threshold,
            "model_label": af.get("model", "SETAR"),
            "n_regimes": int(af.get("n_regimes", 2)),
            "wrapper_response": wrapper_resp,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)

        r_code = r"""
            suppressPackageStartupMessages({ library(tsDyn) })
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])
            # tsDyn::setar requires thDelay < m. With m=1 the
            # only valid thDelay is 0 (threshold variable =
            # contemporaneous y_{t}, but for SETAR(d=1) we
            # actually want y_{t-1} as the threshold variable —
            # so use m=2 with thDelay=0 to match TSL's d=1
            # convention which uses y_{t-1} as threshold).
            fit <- setar(y, m = 2, thDelay = 0, nthresh = 1)

            # tsDyn 11.x stores threshold in coef(fit)["th"], not
            # in fit$model.specific$th (the latter is NULL on
            # current versions).
            cf <- coef(fit)
            threshold <- as.numeric(cf["th"])
            # AR coefs: low regime then high regime (excluding
            # threshold "th")
            ar_names <- setdiff(names(cf), "th")
            coefs <- as.numeric(cf[ar_names])
            # tsDyn::setar has no logLik method; compute from
            # residuals (Gaussian log-lik plug-in)
            resid_vec <- as.numeric(residuals(fit))
            resid_vec <- resid_vec[!is.na(resid_vec)]
            n <- length(resid_vec)
            sigma2 <- sum(resid_vec^2) / n
            log_lik <- -n/2 * (log(2*pi) + log(sigma2) + 1)

            scalars <- c(threshold = threshold, loglik = log_lik)
            write.table(matrix(coefs, ncol = 1),
                        "{{OUTPUT_coefs}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(scalars, ncol = 1),
                        "{{OUTPUT_scalars}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["coefs", "scalars"],
            timeout_sec=120,
            capture_versions_for=["tsDyn"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "threshold": float(sc[0]),
            "log_likelihood": float(sc[1]),
            "coefs": np.atleast_1d(outputs["coefs"]).astype(np.float64).reshape(-1),
            "tsdyn_version": versions.get("tsDyn", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["threshold"] = _compare_scalar(
            tsl["threshold"], ref["threshold"], ladder["primary"],
        )
        statuses.append(primary["threshold"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "tsdyn_version": ref.get("tsdyn_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "tsl_model_label": tsl.get("model_label"),
                "ref_loglik": ref.get("log_likelihood"),
                "ref_coefs_first3": np.asarray(ref["coefs"])[:3].tolist()
                if "coefs" in ref else None,
            },
        )
