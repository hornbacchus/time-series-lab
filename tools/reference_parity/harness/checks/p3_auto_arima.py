"""Phase 7+ S73 — auto_arima (automatic order selection) parity check.

NEW harness (Disposition B; net-new harness construction at S73, NOT
the read+verify pattern of S68-S72). Compares TSL's
``engine/techniques/arima.py`` auto_arima path (technique_id
"auto_arima" → ``_run_auto_arima`` using pmdarima.auto_arima) against
R ``forecast::auto.arima`` on a synthetic ARIMA(1,1,1) DGP-recovery
fixture.

Two parity layers (S73 novel scope):

1. **Order-selection-algorithm cross-implementation** — both
   pmdarima and R forecast::auto.arima implement the Hyndman-Khandakar
   (2008) stepwise algorithm, but may explore the order space
   differently. The harness determines at compare() time whether the
   two arms select the SAME order:
     - **Path (a) selected-order AGREEMENT:** if orders match,
       proceed with coef-by-coef parity of the agreed model (cleanest
       validation).
     - **Path (b) selected-order DIVERGENCE:** if orders differ,
       coef-by-coef is meaningless (different models); validate
       forecast-only parity characterizing model-selection-driven
       divergence.
2. **SARIMAX-fit-at-selected-order** — once the order is selected,
   the fit is statsmodels SARIMAX (pmdarima) vs stats::arima (R),
   the same Gaussian-innovation MLE backbone validated at S62
   (conformal auto_arima base) + S70 (manual ARIMA) + S71 (SARIMA) +
   S72 (ARIMAX). PARTIAL cross-reference: S62 covers the fit layer;
   the order-selection-cross-implementation layer is novel to S73.

Output-tier discipline:

- **Primary:** selected-order integer match (order-agreement metric)
  + (path a only) AR/MA coefs + log-likelihood + h-step forecast.
  Path b: forecast vector only.
- **Secondary:** AIC, BIC (at agreed order; path a).
- **Diagnostic:** selected orders by arm; path determination.

Fixture: T=400 ARIMA(1,1,1) DGP with phi=0.6, theta=0.4, sigma=1.0,
d=1, seed=42 (same DGP as p3_arima_manual). pmdarima selects (1,1,1)
on this fixture per S73 Step-1 probe; expectation is path (a)
agreement with R auto.arima (clean ARIMA(1,1,1) DGP).
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

# Reuse the ARIMA(1,1,1) DGP generator locked at p3_arima.
from reference_parity.harness.checks.p3_arima import _generate_arima_dgp


class AutoArimaParity(P3ParityCheck):
    """auto_arima parity vs R forecast::auto.arima.

    DGP: ARIMA(1,1,1) with phi=0.6, theta=0.4, sigma=1.0, d=1,
    seed=42, T=400. Both arms run automatic order selection
    (Hyndman-Khandakar 2008 stepwise); the harness determines
    selected-order agreement (path a) vs divergence (path b) at
    compare() time and validates accordingly.
    """

    technique_id = "p3_auto_arima"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "auto_arima runs Hyndman-Khandakar 2008 stepwise order "
        "selection (pmdarima vs R forecast::auto.arima) then fits "
        "the selected order by Gaussian-innovation MLE (statsmodels "
        "SARIMAX vs stats::arima). When both arms select the same "
        "order (path a) the fit-layer parity is the §7.1 MLE-fit "
        "band identical to p3_arima_manual; when orders differ "
        "(path b) forecast-only parity characterizes model-"
        "selection-driven divergence. Order-selection-cross-"
        "implementation is the novel S73 layer; SARIMAX fit layer "
        "cross-references S62/S70/S71/S72."
    )

    DGP_PHI = 0.6
    DGP_THETA = 0.4
    DGP_SIGMA = 1.0
    DGP_D = 1
    DGP_N = 400
    HORIZON = 5
    # Search config mirrors engine `_run_auto_arima` Balanced preset
    # (non-seasonal): max_p=5, max_q=5, max_d=2, seasonal=False.
    MAX_P = 5
    MAX_Q = 5
    MAX_D = 2

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_arima_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=self.DGP_PHI,
            theta=self.DGP_THETA,
            sigma=self.DGP_SIGMA,
            d=self.DGP_D,
        )
        return {"y": y, "horizon": self.HORIZON}

    # -----------------------------------------------------------------
    # TSL side: pmdarima auto_arima (matching engine _run_auto_arima
    # non-seasonal Balanced config) + public wrapper sanity.
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.arima as arima_mod  # type: ignore
        import pmdarima as pm  # type: ignore
        import warnings as _w

        y = np.asarray(fixture["y"], dtype=np.float64)
        horizon = int(fixture["horizon"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            # Mirror engine `_run_auto_arima` non-seasonal config
            # (engine lines 159-183): seasonal=False sets
            # start_P/max_P/start_Q/max_Q/max_D = 0.
            model = pm.auto_arima(
                y,
                d=None,
                max_p=self.MAX_P,
                max_q=self.MAX_Q,
                max_d=self.MAX_D,
                seasonal=False,
                m=1,
                start_P=0, max_P=0, start_Q=0, max_Q=0, max_D=0,
                stepwise=True,
                information_criterion="aic",
                suppress_warnings=True,
                error_action="ignore",
                trace=False,
            )

        order = tuple(int(x) for x in model.order)  # (p, d, q)

        # Extract AR/MA coefs from the underlying statsmodels result.
        res = model.arima_res_
        names = list(res.param_names)
        params = np.asarray(res.params, dtype=np.float64)
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
        loglik = float(res.llf)
        aic = float(model.aic())
        bic = float(model.bic())

        fc = np.asarray(
            model.predict(n_periods=horizon), dtype=np.float64,
        )

        # Public wrapper sanity (regression check, not parity).
        ctx = RunContext({
            "run_id": "p3_auto_arima_parity",
            "technique_id": "auto_arima",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": horizon, "seasonal": False},
        })
        try:
            wrapper_resp = arima_mod.run(ctx, lambda *a, **kw: None)
            wrapper_aic = wrapper_resp.get("audit_fields", {}).get("aic")
            wrapper_order = wrapper_resp.get("audit_fields", {}).get("order")
        except Exception:
            wrapper_aic = None
            wrapper_order = None

        return {
            "order": order,
            "ar_coefs": ar_coefs,
            "ma_coefs": ma_coefs,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": fc,
            "wrapper_aic": wrapper_aic,
            "wrapper_order": wrapper_order,
        }

    # -----------------------------------------------------------------
    # Reference side: R forecast::auto.arima
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        horizon = int(fixture["horizon"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            # forecast::auto.arima — Hyndman-Khandakar stepwise.
            # Match pmdarima non-seasonal config: seasonal=FALSE,
            # stepwise=TRUE, ic="aic", max.p/q/d mirror engine.
            fit <- auto.arima(
                y,
                max.p = {self.MAX_P}, max.q = {self.MAX_Q},
                max.d = {self.MAX_D},
                seasonal = FALSE,
                stepwise = TRUE,
                ic = "aic",
                allowmean = FALSE, allowdrift = FALSE
            )

            ord <- arimaorder(fit)   # c(p, d, q) for non-seasonal
            p_sel <- as.numeric(ord["p"])
            d_sel <- as.numeric(ord["d"])
            q_sel <- as.numeric(ord["q"])

            cf <- coef(fit)
            ar_names <- grep("^ar[0-9]", names(cf), value = TRUE)
            ma_names <- grep("^ma[0-9]", names(cf), value = TRUE)
            ar_coefs <- if (length(ar_names) > 0) cf[ar_names] else numeric(0)
            ma_coefs <- if (length(ma_names) > 0) cf[ma_names] else numeric(0)

            write.table(matrix(c(p_sel, d_sel, q_sel), ncol = 1),
                        "{{{{OUTPUT_order}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(ar_coefs, ncol = 1), "{{{{OUTPUT_ar_coefs}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(ma_coefs, ncol = 1), "{{{{OUTPUT_ma_coefs}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)

            scalars <- c(
                loglik = as.numeric(logLik(fit)),
                aic = as.numeric(fit$aic),
                bic = as.numeric(fit$bic)
            )
            write.table(matrix(scalars, ncol = 1), "{{{{OUTPUT_scalars}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)

            fc <- forecast(fit, h = {horizon})
            write.table(matrix(as.numeric(fc$mean), ncol = 1),
                        "{{{{OUTPUT_forecast}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["order", "ar_coefs", "ma_coefs",
                          "scalars", "forecast"],
            timeout_sec=120,
            capture_versions_for=["forecast"],
        )

        order_arr = np.atleast_1d(outputs["order"]).astype(int).reshape(-1)
        order = (int(order_arr[0]), int(order_arr[1]), int(order_arr[2]))
        scalars = np.atleast_1d(outputs["scalars"]).reshape(-1)

        return {
            "order": order,
            "ar_coefs": np.atleast_1d(outputs["ar_coefs"]).astype(np.float64).reshape(-1),
            "ma_coefs": np.atleast_1d(outputs["ma_coefs"]).astype(np.float64).reshape(-1),
            "loglik": float(scalars[0]),
            "aic": float(scalars[1]),
            "bic": float(scalars[2]),
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
            "forecast_version": versions.get("forecast", "unknown"),
        }

    # -----------------------------------------------------------------
    # Compare — selected-order path determination
    # -----------------------------------------------------------------

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

        tsl_order = tuple(tsl["order"])
        ref_order = tuple(ref["order"])
        orders_agree = tsl_order == ref_order

        # ---- Primary: selected-order agreement (integer match) ----
        primary["selected_order_match"] = {
            "status": "PASS" if orders_agree else "CAVEAT",
            "tsl_order": list(tsl_order),
            "ref_order": list(ref_order),
            "agree": orders_agree,
        }
        if not orders_agree:
            any_caveat = True  # path (b): documented divergence

        if orders_agree:
            # ---- Path (a): coef-by-coef + loglik + forecast ----
            primary["ar_coefs"] = _compare_vector(
                tsl["ar_coefs"], ref["ar_coefs"], ladder["primary"],
            )
            primary["ma_coefs"] = _compare_vector(
                tsl["ma_coefs"], ref["ma_coefs"], ladder["primary"],
            )
            primary["loglik"] = _compare_scalar(
                tsl["loglik"], ref["loglik"], ladder["primary"],
            )
            primary["forecast"] = _compare_vector(
                tsl["forecast"], ref["forecast"], ladder["primary"],
            )
            for key in ("ar_coefs", "ma_coefs", "loglik", "forecast"):
                st = primary[key]["status"]
                if st == "BLOCK":
                    any_block = True
                elif st == "CAVEAT":
                    any_caveat = True

            secondary["aic"] = _compare_scalar(
                tsl["aic"], ref["aic"], ladder["secondary"],
            )
            secondary["bic"] = _compare_scalar(
                tsl["bic"], ref["bic"], ladder["secondary"],
            )
            path = "a_selected_order_agreement"
        else:
            # ---- Path (b): forecast-only (different models) ----
            primary["forecast"] = _compare_vector(
                tsl["forecast"], ref["forecast"], ladder["primary"],
            )
            st = primary["forecast"]["status"]
            if st == "BLOCK":
                any_block = True
            elif st == "CAVEAT":
                any_caveat = True
            path = "b_selected_order_divergence"

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "forecast_version": ref.get("forecast_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "selected_order_path": path,
                "tsl_selected_order": list(tsl_order),
                "ref_selected_order": list(ref_order),
                "wrapper_order": tsl.get("wrapper_order"),
                "wrapper_aic": tsl.get("wrapper_aic"),
            },
        )
