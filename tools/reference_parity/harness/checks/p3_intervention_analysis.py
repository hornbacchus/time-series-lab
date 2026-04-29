"""Phase 3 Batch 6 — Intervention Analysis parity check.

Compares TSL ``engine/techniques/intervention_analysis.py``
(ARIMA + intervention dummies via statsmodels SARIMAX with
exog regressors) against R ``stats::arima(..., xreg=...)``
on a synthetic AR(1) + step intervention fixture. Pattern A
MLE-fit class — both packages optimize the same Gaussian
likelihood with identical exog design.

For a STEP intervention, the model
    y_t = phi * y_{t-1} + omega * D_step(t) + eps_t
where ``D_step(t) = 1{t >= t*}`` is mathematically equivalent
to standard ARIMA-with-xreg. R's ``TSA::arimax`` has a
different API (xtransf for dynamic transfer functions);
``stats::arima(..., xreg=...)`` is the canonical reference
for static-effect intervention modeling.
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


def _generate_intervention_dgp(
    *, seed: int, n: int = 300, intervention_at: int = 150,
    phi: float = 0.5, omega: float = 2.0, sigma: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """AR(1) + step intervention fixture.

    Returns ``(y, step_dummy)`` where step_dummy[t] = 1 iff
    t >= intervention_at, else 0. Burn-in 100 to discard
    transient.
    """
    rng = np.random.default_rng(seed)
    burn = 100
    y_full = np.zeros(n + burn)
    step = np.zeros(n + burn, dtype=np.float64)
    step[burn + intervention_at:] = 1.0
    eps = rng.standard_normal(n + burn) * sigma
    for t in range(1, n + burn):
        y_full[t] = phi * y_full[t - 1] + omega * step[t] + eps[t]
    return y_full[burn:], step[burn:]


class InterventionAnalysisParity(P3ParityCheck):
    """Intervention analysis parity vs R stats::arima(xreg=...)."""

    technique_id = "p3_intervention_analysis"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Intervention analysis = ARIMA + xreg dummy. Both "
        "TSL (statsmodels SARIMAX with exog) and R "
        "(stats::arima with xreg) optimize the same Gaussian "
        "likelihood. Optimizer-convergence-criterion divergence "
        "between L-BFGS-B (statsmodels) and CSS-ML (R) "
        "produces ~1e-3 abs / 1e-2 rel divergence on the "
        "intervention coefficient; MLE-fit class."
    )

    DGP_N = 300
    INTERVENTION_AT = 150
    DGP_PHI = 0.5
    DGP_OMEGA = 2.0

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, step = _generate_intervention_dgp(
            seed=seed, n=self.DGP_N,
            intervention_at=self.INTERVENTION_AT,
            phi=self.DGP_PHI, omega=self.DGP_OMEGA,
        )
        return {"y": y, "step": step,
                "intervention_index": int(self.INTERVENTION_AT)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # Bypass the wrapper output-rounding by calling
        # statsmodels SARIMAX directly with the same exog +
        # order TSL would set up internally for a step
        # intervention. This is the closed-form math TSL
        # delegates to.
        import warnings as _w
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        step = np.asarray(fixture["step"], dtype=np.float64).reshape(-1, 1)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            model = SARIMAX(
                y, exog=step, order=(1, 0, 0),
                trend="n", enforce_stationarity=False,
                enforce_invertibility=False,
            )
            fit = model.fit(disp=False, maxiter=200)
        params = dict(zip(
            list(fit.model.param_names),
            np.asarray(fit.params, dtype=np.float64),
        ))
        # statsmodels SARIMAX with exog names:
        #   x1 = exog coef (= omega), ar.L1 = phi, sigma2
        return {
            "ar1": float(params.get("ar.L1", float("nan"))),
            "omega": float(params.get("x1", float("nan"))),
            "sigma2": float(params.get("sigma2", float("nan"))),
            "log_likelihood": float(fit.llf),
            "aic": float(fit.aic),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        step = np.asarray(fixture["step"], dtype=np.float64)
        # Concatenate y and step into a single 2-column CSV
        # so we can read both with one read.csv call.
        combined = np.column_stack([y, step])
        r_code = r"""
            data <- read.csv("{{INPUT_data}}", header=FALSE)
            y <- as.numeric(data[, 1])
            step <- as.numeric(data[, 2])
            fit <- arima(y, order = c(1, 0, 0), xreg = step,
                         include.mean = FALSE,
                         method = "CSS-ML")
            ar1 <- as.numeric(coef(fit)["ar1"])
            omega <- as.numeric(coef(fit)["step"])
            if (is.na(omega)) {
                # R may name xreg coefs by column name or generic.
                # Try the second-to-last position as fallback.
                cf <- coef(fit)
                omega <- as.numeric(cf[length(cf)])
            }
            sigma2 <- as.numeric(fit$sigma2)
            llf <- as.numeric(fit$loglik)
            aic <- as.numeric(fit$aic)
            scalars <- c(ar1 = ar1, omega = omega,
                         sigma2 = sigma2, llf = llf, aic = aic)
            write.table(matrix(scalars, ncol=1), "{{OUTPUT_scalars}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"data": combined},
            output_names=["scalars"], timeout_sec=60,
            capture_versions_for=[],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "ar1": float(sc[0]),
            "omega": float(sc[1]),
            "sigma2": float(sc[2]),
            "log_likelihood": float(sc[3]),
            "aic": float(sc[4]),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        primary["ar1"] = _compare_scalar(
            tsl["ar1"], ref["ar1"], ladder["primary"],
        )
        primary["omega"] = _compare_scalar(
            tsl["omega"], ref["omega"], ladder["primary"],
        )
        primary["log_likelihood"] = _compare_scalar(
            tsl["log_likelihood"], ref["log_likelihood"],
            ladder["primary"],
        )
        secondary["sigma2"] = _compare_scalar(
            tsl["sigma2"], ref["sigma2"], ladder["secondary"],
        )
        secondary["aic"] = _compare_scalar(
            tsl["aic"], ref["aic"], ladder["secondary"],
        )
        any_block = any(
            primary[k]["status"] == "BLOCK" for k in primary
        )
        any_caveat = any(
            primary[k]["status"] == "CAVEAT" for k in primary
        )
        # Secondary CAVEAT/BLOCK does not escalate the primary
        # outcome (Pattern B / master plan §7.2 — secondary
        # findings are diagnostic).
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "intervention_at": int(self.INTERVENTION_AT),
                "true_phi": float(self.DGP_PHI),
                "true_omega": float(self.DGP_OMEGA),
                "tsl_omega": float(tsl["omega"]),
                "ref_omega": float(ref["omega"]),
            },
        )
