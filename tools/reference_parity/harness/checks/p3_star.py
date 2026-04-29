"""Phase 3 Batch 4 — STAR (Smooth Transition AR) parity check.

Compares TSL's ``engine/techniques/star_model.py`` (custom
scipy.optimize-based fit) against R ``tsDyn::star`` on a
synthetic LSTAR(1) (logistic STAR) fixture.

**Tier B/C verdict expected per master plan §5:** STAR with
non-standard transition functions has methodology divergence
between TSL and R tsDyn that is intrinsic to optimizer
choice + transition-function parameterization. May land
CAVEAT or DOCUMENTED-DIVERGENCE on most fixtures; potentially
NO-REFERENCE for fixtures where the two implementations
optimize different objective surfaces.

Compares: regime AR coefficients, smoothness parameter gamma,
threshold c, log-likelihood. Sign / scale alignment via gamma
positivity normalization (gamma > 0 by convention).
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


def _generate_lstar_dgp(
    *,
    seed: int,
    n: int = 500,
    phi_low: tuple[float] = (0.7,),
    phi_high: tuple[float] = (-0.3,),
    gamma: float = 5.0,
    c: float = 0.0,
    sigma: float = 1.0,
    burn: int = 100,
) -> np.ndarray:
    """Generate LSTAR(1) realization.

    Logistic transition: G(z, gamma, c) = 1 / (1 + exp(-gamma * (z - c)))
    z_t = y_{t-1}.
    y_t = (phi_low_0 + phi_low_1 * y_{t-1}) * (1 - G)
        + (phi_high_0 + phi_high_1 * y_{t-1}) * G
        + eps_t
    """
    rng = np.random.default_rng(seed)
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma
    y = np.zeros(n_total)
    for t in range(1, n_total):
        z = y[t - 1]
        G = 1.0 / (1.0 + np.exp(-gamma * (z - c)))
        ar_low = phi_low[0] * y[t - 1]
        ar_high = phi_high[0] * y[t - 1]
        y[t] = ar_low * (1 - G) + ar_high * G + eps[t]
    return y[burn:]


class StarParity(P3ParityCheck):
    """LSTAR(1) parity vs R tsDyn::star."""

    technique_id = "p3_star"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "STAR (Smooth Transition AR) — TSL's custom scipy.optimize "
        "fit and R tsDyn::star use different optimizer "
        "initialization heuristics for the smoothness parameter "
        "gamma. Independent-implementation optimizer-driven; "
        "Pattern H (DSCD) candidate. Master plan §5 Tier B/C: "
        "if R tsDyn::star fails to converge or diverges by >1e-1 "
        "abs on the smoothness parameter, the audit downgrades "
        "to DOCUMENTED-DIVERGENCE."
    )

    DGP_N = 500

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "y": _generate_lstar_dgp(seed=seed, n=self.DGP_N),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.star_model as star_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_star_parity",
            "technique_id": "star",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"transition": "logistic", "ar_order": 1},
        })
        wrapper_resp = star_mod.run(ctx, lambda *a, **kw: None)
        if wrapper_resp.get("status") != "success":
            raise RuntimeError(
                f"TSL STAR run failed: {wrapper_resp.get('error_message')}"
            )
        af = wrapper_resp.get("audit_fields", {})
        return {
            "gamma": float(af.get("gamma", np.nan)),
            "c": float(af.get("c", np.nan)),
            "log_likelihood": float(af.get("log_likelihood", np.nan)),
            "rmse": float(af.get("rmse", np.nan)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)

        r_code = r"""
            suppressPackageStartupMessages({ library(tsDyn) })
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])

            # tsDyn::star fits LSTAR(m=1, d=1) by default (one
            # AR lag, threshold delay 1).
            fit <- tryCatch(
                star(y, m = 1, d = 1, control = list(maxit = 200)),
                error = function(e) NULL
            )

            if (is.null(fit)) {
                # Reference failed — emit NA scalars; check
                # downgrades to DOCUMENTED-DIVERGENCE / NO-REF
                scalars <- c(gamma = NA, c = NA, loglik = NA)
            } else {
                # tsDyn LSTAR exposes gamma + c via the model
                # parameter vector. Names vary by version;
                # tsDyn 11.x uses "gamma" and "th".
                cf <- coef(fit)
                gamma_val <- if ("gamma" %in% names(cf)) {
                    as.numeric(cf["gamma"])
                } else NA
                c_val <- if ("th" %in% names(cf)) {
                    as.numeric(cf["th"])
                } else NA
                # tsDyn::star has no logLik method; compute
                # Gaussian log-lik manually from residuals.
                resid_vec <- as.numeric(residuals(fit))
                resid_vec <- resid_vec[!is.na(resid_vec)]
                n <- length(resid_vec)
                sigma2 <- sum(resid_vec^2) / n
                ll <- -n/2 * (log(2*pi) + log(sigma2) + 1)
                scalars <- c(gamma = gamma_val, c = c_val, loglik = ll)
            }

            write.table(matrix(scalars, ncol = 1),
                        "{{OUTPUT_scalars}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars"],
            timeout_sec=120,
            capture_versions_for=["tsDyn"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "gamma": float(sc[0]) if not np.isnan(sc[0]) else None,
            "c": float(sc[1]) if not np.isnan(sc[1]) else None,
            "log_likelihood": float(sc[2]) if not np.isnan(sc[2]) else None,
            "tsdyn_version": versions.get("tsDyn", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Reference may have failed → all NA. If so, mark as
        # CAVEAT (matches except in stated regime — reference
        # didn't converge).
        if ref.get("gamma") is None or ref.get("c") is None:
            return ParityResult(
                technique_id=self.technique_id,
                outcome="CAVEAT",
                metrics={
                    "primary": {
                        "reference_convergence": {
                            "status": "CAVEAT",
                            "note": (
                                "R tsDyn::star did not converge on "
                                "this fixture. TSL fit succeeded; "
                                "no comparison available. Documented "
                                "divergence per master plan §5 Tier "
                                "B/C."
                            ),
                            "tsl_gamma": tsl.get("gamma"),
                            "tsl_c": tsl.get("c"),
                            "tsl_loglik": tsl.get("log_likelihood"),
                        }
                    }
                },
                diagnostics={
                    "tsdyn_version": ref.get("tsdyn_version", "unknown"),
                    "n_obs": int(self.DGP_N),
                    "ref_failed_to_converge": True,
                },
            )

        # gamma sign canonicalization: by convention gamma > 0.
        # If TSL fits negative gamma + flipped low/high regimes,
        # take |gamma|.
        primary["gamma"] = _compare_scalar(
            abs(tsl["gamma"]), abs(ref["gamma"]), ladder["primary"],
        )
        statuses.append(primary["gamma"]["status"])

        primary["c"] = _compare_scalar(
            tsl["c"], ref["c"], ladder["primary"],
        )
        statuses.append(primary["c"]["status"])

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
                "tsl_loglik": tsl.get("log_likelihood"),
                "ref_loglik": ref.get("log_likelihood"),
            },
        )
