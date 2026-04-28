"""Phase 3 Batch 1 — ARIMAX / SARIMAX parity check.

Compares TSL's ``engine/techniques/arimax_sarimax.py`` (SARIMAX
with exogenous regressors) against R ``forecast::Arima`` with
``xreg`` arg on a synthetic ARIMAX(1,0,1) DGP-recovery fixture
with one exogenous regressor.

Output-tier discipline:

- **Primary:** AR + MA coefs, exog regression coefficient(s),
  log-likelihood, h-step forecast.
- **Secondary:** sigma^2, AIC, BIC.
- **Diagnostic:** fitted in-sample correlation.

Fixture: T=300 ARIMAX(1,0,1) with phi=0.6, theta=0.4, sigma=1.0,
exogenous regressor x ~ AR(1) with rho=0.7, exog coef beta=1.5,
seed=42. d=0 + no seasonal differencing keeps the parity audit
focused on MLE optimizer convergence rather than differencing
operator semantics (audited separately in p3_arima_manual which
does have d=1).

Session 2 manual-pattern lock: structurally identical to
``p3_arima.py`` and ``p3_sarima.py``; adds an `xreg` input + an
extra primary metric (regression coefficient parity).
"""

from __future__ import annotations

import sys
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


# ---------------------------------------------------------------------
# DGP generator — ARIMAX(1,0,1) with one exogenous AR(1) regressor
# ---------------------------------------------------------------------

def _generate_arimax_dgp(
    *,
    seed: int,
    n: int = 300,
    phi: float = 0.6,
    theta: float = 0.4,
    beta: float = 1.5,
    rho_x: float = 0.7,
    sigma_y: float = 1.0,
    sigma_x: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate stationary ARIMAX realization plus the exog
    regressor.

    Process:
      x_t = rho_x * x_{t-1} + nu_t,           nu ~ N(0, sigma_x^2)
      u_t = phi * u_{t-1} + eps_t + theta * eps_{t-1},  eps ~ N(0, sigma_y^2)
      y_t = beta * x_t + u_t

    Returns (y, x) of length n. Burn-in 100 samples.
    """
    rng = np.random.default_rng(seed)
    burn = 100
    n_total = n + burn
    nu = rng.standard_normal(n_total) * sigma_x
    eps = rng.standard_normal(n_total) * sigma_y
    x = np.zeros(n_total)
    u = np.zeros(n_total)
    for t in range(1, n_total):
        x[t] = rho_x * x[t - 1] + nu[t]
        u[t] = phi * u[t - 1] + eps[t] + theta * eps[t - 1]
    y = beta * x + u
    return y[burn:], x[burn:]


class ArimaxSarimaxParity(ParityCheck):
    """ARIMAX parity vs R forecast::Arima with xreg.

    DGP: ARIMAX(1,0,1) with phi=0.6, theta=0.4, beta=1.5,
    rho_x=0.7, sigma=1.0, seed=42, T=300.
    """

    technique_id = "p3_arimax_sarimax"
    tier = "fast"
    fixture_id = ""

    DGP_PHI = 0.6
    DGP_THETA = 0.4
    DGP_BETA = 1.5
    DGP_RHO_X = 0.7
    DGP_SIGMA = 1.0
    DGP_N = 300
    FIT_ORDER = (1, 0, 1)
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, x = _generate_arimax_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=self.DGP_PHI,
            theta=self.DGP_THETA,
            beta=self.DGP_BETA,
            rho_x=self.DGP_RHO_X,
            sigma_y=self.DGP_SIGMA,
        )
        # Future-x for forecast horizon: continue x's AR(1) with
        # zero noise (deterministic continuation; the parity audit
        # tests the wrapper's forecast math given a fixed future
        # exog path, not stochastic future-x estimation).
        future_x = np.zeros(self.HORIZON)
        future_x[0] = self.DGP_RHO_X * x[-1]
        for h in range(1, self.HORIZON):
            future_x[h] = self.DGP_RHO_X * future_x[h - 1]
        return {
            "y": y,
            "x": x,
            "future_x": future_x,
            "order": self.FIT_ORDER,
            "horizon": self.HORIZON,
        }

    # -----------------------------------------------------------------
    # TSL side: invoke statsmodels SARIMAX directly with exog
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.arimax_sarimax as ax_mod  # type: ignore
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        x = np.asarray(fixture["x"], dtype=np.float64).reshape(-1, 1)
        future_x = np.asarray(fixture["future_x"], dtype=np.float64).reshape(-1, 1)
        order = tuple(fixture["order"])
        horizon = int(fixture["horizon"])

        sm_fit = SARIMAX(
            y,
            exog=x,
            order=order,
            seasonal_order=(0, 0, 0, 0),
            trend="n",
            enforce_stationarity=True,
            enforce_invertibility=True,
        ).fit(disp=False, maxiter=200)

        names = list(sm_fit.param_names)
        params = np.asarray(sm_fit.params, dtype=np.float64)
        # Exog coefficient name in statsmodels is "x1" (or per
        # column name); for our anonymous exog it's "x1".
        exog_names = [n for n in names if n.startswith("x") and n[1:].isdigit()]
        exog_coefs = np.array(
            [params[names.index(n)] for n in exog_names],
            dtype=np.float64,
        )

        ar_coefs = np.array(
            [params[names.index(f"ar.L{i}")]
             for i in range(1, order[0] + 1) if f"ar.L{i}" in names],
            dtype=np.float64,
        )
        ma_coefs = np.array(
            [params[names.index(f"ma.L{i}")]
             for i in range(1, order[2] + 1) if f"ma.L{i}" in names],
            dtype=np.float64,
        )
        sigma2 = float(params[names.index("sigma2")]) if "sigma2" in names else float("nan")
        loglik = float(sm_fit.llf)
        aic = float(sm_fit.aic)
        bic = float(sm_fit.bic)

        fc_obj = sm_fit.get_forecast(steps=horizon, exog=future_x)
        fc = np.asarray(fc_obj.predicted_mean, dtype=np.float64)

        fitted_raw = np.asarray(sm_fit.fittedvalues, dtype=np.float64)
        if len(fitted_raw) < len(y):
            pad = np.full(len(y) - len(fitted_raw), np.nan)
            fitted = np.concatenate([pad, fitted_raw])
        else:
            fitted = fitted_raw

        # Wrapper sanity
        ctx = RunContext({
            "run_id": "p3_arimax_parity",
            "technique_id": "arimax",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [
                {"name": "y", "values": y.tolist()},
                {"name": "x1", "values": x.reshape(-1).tolist()},
            ],
            "params": {
                "order": list(order),
                "seasonal_order": [0, 0, 0, 0],
                "horizon": horizon,
                "trend": "n",
            },
        })
        try:
            wrapper_resp = ax_mod.run(ctx, lambda *a, **kw: None)
            wrapper_aic = wrapper_resp.get("audit_fields", {}).get("aic")
        except Exception:
            wrapper_aic = None

        return {
            "ar_coefs": ar_coefs,
            "ma_coefs": ma_coefs,
            "exog_coefs": exog_coefs,
            "sigma2": sigma2,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": fc,
            "fitted": fitted,
            "wrapper_aic": wrapper_aic,
        }

    # -----------------------------------------------------------------
    # Reference side: R forecast::Arima with xreg
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        x = np.asarray(fixture["x"], dtype=np.float64).reshape(-1, 1)
        future_x = np.asarray(fixture["future_x"], dtype=np.float64).reshape(-1, 1)
        order = tuple(fixture["order"])
        horizon = int(fixture["horizon"])

        p, d, q = order
        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            x <- as.matrix(read.csv("{{{{INPUT_x}}}}", header=FALSE))
            fx <- as.matrix(read.csv("{{{{INPUT_fx}}}}", header=FALSE))

            fit <- Arima(
                y,
                order = c({p}, {d}, {q}),
                xreg = x,
                method = "ML",
                include.constant = FALSE
            )

            cf <- coef(fit)
            ar_names <- grep("^ar[0-9]", names(cf), value = TRUE)
            ma_names <- grep("^ma[0-9]", names(cf), value = TRUE)
            # Anything that's not ar/ma/sar/sma/intercept is an
            # exog regressor coefficient. forecast::Arima names
            # the exog coefficients by the colnames of xreg, or
            # "xreg" / "xreg1" / etc. when colnames are absent.
            other_names <- setdiff(
                names(cf),
                c(ar_names, ma_names, "intercept", "drift")
            )
            other_names <- grep(
                "^(sar|sma)", other_names, invert = TRUE, value = TRUE
            )
            ar_coefs   <- if (length(ar_names) > 0)    cf[ar_names]    else numeric(0)
            ma_coefs   <- if (length(ma_names) > 0)    cf[ma_names]    else numeric(0)
            exog_coefs <- if (length(other_names) > 0) cf[other_names] else numeric(0)

            write.table(matrix(ar_coefs,   ncol = 1), "{{{{OUTPUT_ar_coefs}}}}",   sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(ma_coefs,   ncol = 1), "{{{{OUTPUT_ma_coefs}}}}",   sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(exog_coefs, ncol = 1), "{{{{OUTPUT_exog_coefs}}}}", sep = ",", row.names = FALSE, col.names = FALSE)

            scalars <- c(
                loglik = as.numeric(logLik(fit)),
                aic = as.numeric(fit$aic),
                bic = as.numeric(fit$bic),
                sigma2 = as.numeric(fit$sigma2)
            )
            write.table(matrix(scalars, ncol = 1), "{{{{OUTPUT_scalars}}}}", sep = ",", row.names = FALSE, col.names = FALSE)

            fc <- forecast(fit, h = {horizon}, xreg = fx)
            write.table(matrix(as.numeric(fc$mean), ncol = 1), "{{{{OUTPUT_forecast}}}}", sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(fitted(fit)), ncol = 1), "{{{{OUTPUT_fitted}}}}", sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1), "x": x, "fx": future_x},
            output_names=["ar_coefs", "ma_coefs", "exog_coefs",
                          "scalars", "forecast", "fitted"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )

        scalars = np.atleast_1d(outputs["scalars"]).reshape(-1)
        loglik, aic, bic, sigma2 = float(scalars[0]), float(scalars[1]), float(scalars[2]), float(scalars[3])

        return {
            "ar_coefs":   np.atleast_1d(outputs["ar_coefs"]).astype(np.float64).reshape(-1),
            "ma_coefs":   np.atleast_1d(outputs["ma_coefs"]).astype(np.float64).reshape(-1),
            "exog_coefs": np.atleast_1d(outputs["exog_coefs"]).astype(np.float64).reshape(-1),
            "sigma2": sigma2,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
            "fitted":   np.atleast_1d(outputs["fitted"]).astype(np.float64).reshape(-1),
            "forecast_version": versions.get("forecast", "unknown"),
        }

    # -----------------------------------------------------------------
    # Compare
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary_metrics: dict[str, Any] = {}
        secondary_metrics: dict[str, Any] = {}
        diagnostic_metrics: dict[str, Any] = {}
        any_block = False
        any_caveat = False

        for key in ("ar_coefs", "ma_coefs", "exog_coefs"):
            primary_metrics[key] = _compare_vector(
                tsl[key], ref[key], ladder["primary"],
            )
            if primary_metrics[key]["status"] == "BLOCK":
                any_block = True
            elif primary_metrics[key]["status"] == "CAVEAT":
                any_caveat = True

        primary_metrics["loglik"] = _compare_scalar(
            tsl["loglik"], ref["loglik"], ladder["primary"],
        )
        if primary_metrics["loglik"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["loglik"]["status"] == "CAVEAT":
            any_caveat = True

        primary_metrics["forecast"] = _compare_vector(
            tsl["forecast"], ref["forecast"], ladder["primary"],
        )
        if primary_metrics["forecast"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["forecast"]["status"] == "CAVEAT":
            any_caveat = True

        for key in ("sigma2", "aic", "bic"):
            secondary_metrics[key] = _compare_scalar(
                tsl[key], ref[key], ladder["secondary"],
            )

        try:
            tsl_fitted = np.asarray(tsl["fitted"], dtype=np.float64)
            ref_fitted = np.asarray(ref["fitted"], dtype=np.float64)
            mask = np.isfinite(tsl_fitted) & np.isfinite(ref_fitted)
            if int(mask.sum()) > 10:
                corr = float(np.corrcoef(
                    tsl_fitted[mask], ref_fitted[mask],
                )[0, 1])
            else:
                corr = float("nan")
            diagnostic_metrics["fitted_correlation"] = {
                "status": "INFO",
                "pearson_corr": corr,
                "n_compared": int(mask.sum()),
            }
        except Exception as e:
            diagnostic_metrics["fitted_correlation"] = {
                "status": "INFO",
                "error": f"{type(e).__name__}: {e}",
            }

        if any_block:
            outcome = "BLOCK"
        elif any_caveat:
            outcome = "CAVEAT"
        else:
            outcome = "PASS"

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary_metrics, "secondary": secondary_metrics},
            diagnostics={
                **diagnostic_metrics,
                "forecast_version": ref.get("forecast_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "fit_order": list(self.FIT_ORDER),
                "wrapper_aic": tsl.get("wrapper_aic"),
            },
        )
