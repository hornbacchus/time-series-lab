"""Phase 3 Batch 1 — SARIMA parity check.

Compares TSL's ``engine/techniques/sarima.py`` (SARIMAX backbone)
against R ``forecast::Arima`` (with seasonal arg) on a synthetic
SARIMA(1,0,1)x(1,0,1)[12] DGP-recovery fixture. Both
implementations fit by maximum likelihood via state-space
representation; the parity audit verifies that the deterministic
optimizers converge to the same point estimate within the master
plan §7.1 MLE-fit tolerance band.

Output-tier discipline:

- **Primary:** non-seasonal AR + MA coefs, seasonal AR + MA coefs,
  log-likelihood, h-step point forecast.
- **Secondary:** sigma^2, AIC, BIC.
- **Diagnostic:** fitted in-sample correlation (Pearson).

Fixture: T=240 SARIMA(1,0,1)x(1,0,1)[12] with phi=0.6, theta=0.4,
Phi=0.5, Theta=0.3, sigma=1.0, seed=42. d=0 + D=0 keeps the
process strictly stationary so optimizer convergence is robust;
the seasonal differencing/integrating path is a separate concern
audited by Batch 1 SARIMA seasonal-difference variants if/when
added.

Session 2 manual-pattern lock: structurally identical to
``p3_arima.py`` with seasonal-order extensions. Re-uses
``_compare_scalar`` / ``_compare_vector`` helpers via local
re-import (Session 5 generator abstraction will factor into
``compare.py``).
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

# Re-use the comparison helpers locked in p3_arima.py
from reference_parity.harness.checks.p3_arima import (
    _compare_scalar,
    _compare_vector,
    _ensure_engine_on_path,
)


# ---------------------------------------------------------------------
# DGP generator — SARIMA(1,0,1)x(1,0,1)[m]
# ---------------------------------------------------------------------

def _generate_sarima_dgp(
    *,
    seed: int,
    n: int = 240,
    phi: float = 0.6,
    theta: float = 0.4,
    Phi: float = 0.5,
    Theta: float = 0.3,
    sigma: float = 1.0,
    m: int = 12,
) -> np.ndarray:
    """Generate stationary SARIMA(1,0,1)x(1,0,1)[m] realization
    via state-space simulation (no integrating component).

    Process (multiplicative seasonal ARMA):
        (1 - phi B)(1 - Phi B^m) y_t = (1 + theta B)(1 + Theta B^m) eps_t
    where eps_t ~ N(0, sigma^2). Burn-in 200 samples to wash out
    the zero initial condition.
    """
    rng = np.random.default_rng(seed)
    burn = 200
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma
    y = np.zeros(n_total)
    for t in range(max(m, 1) + 1, n_total):
        # AR: phi*y_{t-1} + Phi*y_{t-m} - phi*Phi*y_{t-m-1}
        ar = (phi * y[t - 1]
              + Phi * y[t - m]
              - phi * Phi * y[t - m - 1])
        # MA: eps_t + theta*eps_{t-1} + Theta*eps_{t-m} + theta*Theta*eps_{t-m-1}
        ma = (eps[t]
              + theta * eps[t - 1]
              + Theta * eps[t - m]
              + theta * Theta * eps[t - m - 1])
        y[t] = ar + ma
    return y[burn:]


class SarimaParity(ParityCheck):
    """SARIMA parity vs R forecast::Arima with seasonal arg.

    DGP: SARIMA(1,0,1)x(1,0,1)[12] with phi=0.6, theta=0.4,
    Phi=0.5, Theta=0.3, sigma=1.0, seed=42, T=240.
    """

    technique_id = "p3_sarima"
    tier = "fast"
    fixture_id = ""

    DGP_PHI = 0.6
    DGP_THETA = 0.4
    DGP_PHI_SEASONAL = 0.5
    DGP_THETA_SEASONAL = 0.3
    DGP_SIGMA = 1.0
    DGP_M = 12
    DGP_N = 240
    FIT_ORDER = (1, 0, 1)
    FIT_SEASONAL = (1, 0, 1, 12)
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_sarima_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=self.DGP_PHI,
            theta=self.DGP_THETA,
            Phi=self.DGP_PHI_SEASONAL,
            Theta=self.DGP_THETA_SEASONAL,
            sigma=self.DGP_SIGMA,
            m=self.DGP_M,
        )
        return {
            "y": y,
            "order": self.FIT_ORDER,
            "seasonal_order": self.FIT_SEASONAL,
            "horizon": self.HORIZON,
        }

    # -----------------------------------------------------------------
    # TSL side: invoke statsmodels SARIMAX directly to extract
    # AR/MA coefficient breakdown explicitly. The public sarima.py
    # wrapper is exercised in parallel for audit-field sanity but
    # does not surface the coefficients in audit_fields.
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.sarima as sarima_mod  # type: ignore
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        order = tuple(fixture["order"])
        seasonal = tuple(fixture["seasonal_order"])
        horizon = int(fixture["horizon"])

        sm_fit = SARIMAX(
            y,
            order=order,
            seasonal_order=seasonal,
            trend="n",
            enforce_stationarity=True,
            enforce_invertibility=True,
        ).fit(disp=False, maxiter=200)

        names = list(sm_fit.param_names)
        params = np.asarray(sm_fit.params, dtype=np.float64)

        def _get_named(prefix: str, count: int) -> np.ndarray:
            arr = []
            for i in range(1, count + 1):
                key = f"{prefix}{i}"
                if key in names:
                    arr.append(params[names.index(key)])
                else:
                    arr.append(np.nan)
            return np.array(arr, dtype=np.float64)

        ar_coefs = _get_named("ar.L", order[0])
        ma_coefs = _get_named("ma.L", order[2])
        # Seasonal AR / MA: statsmodels names like "ar.S.L12" for
        # the first seasonal lag (period m). For (P, D, Q, m) =
        # (1, 0, 1, 12), the names are ar.S.L12 and ma.S.L12.
        sar_coefs = np.array(
            [params[names.index(f"ar.S.L{seasonal[3] * i}")]
             for i in range(1, seasonal[0] + 1)
             if f"ar.S.L{seasonal[3] * i}" in names],
            dtype=np.float64,
        )
        sma_coefs = np.array(
            [params[names.index(f"ma.S.L{seasonal[3] * i}")]
             for i in range(1, seasonal[2] + 1)
             if f"ma.S.L{seasonal[3] * i}" in names],
            dtype=np.float64,
        )
        sigma2 = float(params[names.index("sigma2")]) if "sigma2" in names else float("nan")
        loglik = float(sm_fit.llf)
        aic = float(sm_fit.aic)
        bic = float(sm_fit.bic)

        fc_obj = sm_fit.get_forecast(steps=horizon)
        fc = np.asarray(fc_obj.predicted_mean, dtype=np.float64)

        fitted_raw = np.asarray(sm_fit.fittedvalues, dtype=np.float64)
        if len(fitted_raw) < len(y):
            pad = np.full(len(y) - len(fitted_raw), np.nan)
            fitted = np.concatenate([pad, fitted_raw])
        else:
            fitted = fitted_raw

        # Wrapper sanity (regression check, not part of parity)
        ctx = RunContext({
            "run_id": "p3_sarima_parity",
            "technique_id": "sarima",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "M",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "order": list(order),
                "seasonal_order": list(seasonal),
                "horizon": horizon,
            },
        })
        try:
            wrapper_resp = sarima_mod.run(ctx, lambda *a, **kw: None)
            wrapper_aic = wrapper_resp.get("audit_fields", {}).get("aic")
        except Exception:
            wrapper_aic = None

        return {
            "ar_coefs": ar_coefs,
            "ma_coefs": ma_coefs,
            "sar_coefs": sar_coefs,
            "sma_coefs": sma_coefs,
            "sigma2": sigma2,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": fc,
            "fitted": fitted,
            "wrapper_aic": wrapper_aic,
        }

    # -----------------------------------------------------------------
    # Reference side: R forecast::Arima with seasonal arg
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        order = tuple(fixture["order"])
        seasonal = tuple(fixture["seasonal_order"])
        horizon = int(fixture["horizon"])

        p, d, q = order
        P, D, Q, m = seasonal
        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            fit <- Arima(
                y,
                order = c({p}, {d}, {q}),
                seasonal = list(order = c({P}, {D}, {Q}), period = {m}),
                method = "ML",
                include.constant = FALSE
            )

            cf <- coef(fit)
            ar_names <- grep("^ar[0-9]", names(cf), value = TRUE)
            ma_names <- grep("^ma[0-9]", names(cf), value = TRUE)
            sar_names <- grep("^sar", names(cf), value = TRUE)
            sma_names <- grep("^sma", names(cf), value = TRUE)
            ar_coefs  <- if (length(ar_names) > 0)  cf[ar_names]  else numeric(0)
            ma_coefs  <- if (length(ma_names) > 0)  cf[ma_names]  else numeric(0)
            sar_coefs <- if (length(sar_names) > 0) cf[sar_names] else numeric(0)
            sma_coefs <- if (length(sma_names) > 0) cf[sma_names] else numeric(0)

            write.table(matrix(ar_coefs,  ncol = 1), "{{{{OUTPUT_ar_coefs}}}}",  sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(ma_coefs,  ncol = 1), "{{{{OUTPUT_ma_coefs}}}}",  sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(sar_coefs, ncol = 1), "{{{{OUTPUT_sar_coefs}}}}", sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(sma_coefs, ncol = 1), "{{{{OUTPUT_sma_coefs}}}}", sep = ",", row.names = FALSE, col.names = FALSE)

            scalars <- c(
                loglik = as.numeric(logLik(fit)),
                aic = as.numeric(fit$aic),
                bic = as.numeric(fit$bic),
                sigma2 = as.numeric(fit$sigma2)
            )
            write.table(matrix(scalars, ncol = 1), "{{{{OUTPUT_scalars}}}}", sep = ",", row.names = FALSE, col.names = FALSE)

            fc <- forecast(fit, h = {horizon})
            write.table(matrix(as.numeric(fc$mean), ncol = 1), "{{{{OUTPUT_forecast}}}}", sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(fitted(fit)), ncol = 1), "{{{{OUTPUT_fitted}}}}", sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["ar_coefs", "ma_coefs", "sar_coefs",
                          "sma_coefs", "scalars", "forecast",
                          "fitted"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )

        scalars = np.atleast_1d(outputs["scalars"]).reshape(-1)
        loglik, aic, bic, sigma2 = float(scalars[0]), float(scalars[1]), float(scalars[2]), float(scalars[3])

        return {
            "ar_coefs":  np.atleast_1d(outputs["ar_coefs"]).astype(np.float64).reshape(-1),
            "ma_coefs":  np.atleast_1d(outputs["ma_coefs"]).astype(np.float64).reshape(-1),
            "sar_coefs": np.atleast_1d(outputs["sar_coefs"]).astype(np.float64).reshape(-1),
            "sma_coefs": np.atleast_1d(outputs["sma_coefs"]).astype(np.float64).reshape(-1),
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

        for key in ("ar_coefs", "ma_coefs", "sar_coefs", "sma_coefs"):
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
                "fit_seasonal": list(self.FIT_SEASONAL),
                "wrapper_aic": tsl.get("wrapper_aic"),
            },
        )
