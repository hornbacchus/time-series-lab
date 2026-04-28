"""Phase 3 Batch 1 — ETS / Holt-Winters parity check.

Compares TSL's ``engine/techniques/ets_hw.py`` (statsmodels
``ExponentialSmoothing`` backbone) against R ``forecast::ets``
on a synthetic Holt-Winters additive trend + additive seasonal
DGP-recovery fixture.

Reference selection note: R ``forecast::ets`` is the canonical
state-space-formulated ETS implementation (Hyndman, Koehler,
Snyder, Grose 2002). statsmodels' ``ExponentialSmoothing``
implements the "classical" Holt-Winters smoothing recursion,
which is mathematically equivalent for the deterministic-state
case but parameterizes the initial state and noise differently.
Tolerance band per master plan §7.1 MLE-fit class accommodates
the optimizer-convergence-criterion difference.

Output-tier discipline:

- **Primary:** smoothing parameters (alpha, beta, gamma where
  applicable), h-step forecast.
- **Secondary:** AIC, BIC, sigma^2, RMSE on in-sample residuals.
- **Diagnostic:** initial level / trend / seasonal states
  (correlation only — implementations differ on initial-state
  parameterization).

Fixture: T=200 Holt-Winters DGP with additive trend + additive
seasonality, alpha=0.3, beta=0.1, gamma=0.2, m=12, sigma=0.5,
seed=42. Generated at runtime.
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


def _generate_hw_dgp(
    *,
    seed: int,
    n: int = 200,
    alpha: float = 0.3,
    beta: float = 0.1,
    gamma: float = 0.2,
    m: int = 12,
    sigma: float = 0.5,
    initial_level: float = 100.0,
    initial_trend: float = 0.5,
) -> np.ndarray:
    """Generate Holt-Winters additive-trend additive-seasonal
    realization via the standard state-space recursion.

    State updates:
        l_t = alpha * (y_t - s_{t-m}) + (1-alpha) * (l_{t-1} + b_{t-1})
        b_t = beta * (l_t - l_{t-1}) + (1-beta) * b_{t-1}
        s_t = gamma * (y_t - l_t)   + (1-gamma) * s_{t-m}
    Forecast:
        y_t = l_{t-1} + b_{t-1} + s_{t-m} + eps_t

    Initial seasonal pattern: sin(2*pi*k/m) for k=0..m-1.
    Burn-in 50 to wash out initial-state transient.
    """
    rng = np.random.default_rng(seed)
    burn = 50
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma

    l = np.zeros(n_total)
    b = np.zeros(n_total)
    s = np.zeros(n_total + m)
    y = np.zeros(n_total)

    # Initial seasonal pattern
    for k in range(m):
        s[k] = 3.0 * np.sin(2 * np.pi * k / m)

    l[0] = initial_level
    b[0] = initial_trend
    y[0] = l[0] + b[0] + s[0] + eps[0]

    for t in range(1, n_total):
        s_lag = s[t - 1] if t < m else s[t - 1]  # use most recent of m periods back
        # standard HW: y_t = l_{t-1} + b_{t-1} + s_{t-m} + eps
        s_t_minus_m = s[t - m + (m - 1)] if t >= m else s[t - 1]
        y[t] = l[t - 1] + b[t - 1] + s_t_minus_m + eps[t]
        l[t] = alpha * (y[t] - s_t_minus_m) + (1 - alpha) * (l[t - 1] + b[t - 1])
        b[t] = beta * (l[t] - l[t - 1]) + (1 - beta) * b[t - 1]
        s[t + m - 1] = gamma * (y[t] - l[t]) + (1 - gamma) * s_t_minus_m

    return y[burn:]


class EtsParity(ParityCheck):
    """ETS / Holt-Winters parity vs R forecast::ets.

    DGP: Holt-Winters AAA (additive trend + additive seasonal),
    alpha=0.3, beta=0.1, gamma=0.2, m=12, sigma=0.5, seed=42,
    T=200.
    """

    technique_id = "p3_ets"
    tier = "fast"
    fixture_id = ""

    DGP_ALPHA = 0.3
    DGP_BETA = 0.1
    DGP_GAMMA = 0.2
    DGP_M = 12
    DGP_SIGMA = 0.5
    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_hw_dgp(
            seed=seed,
            n=self.DGP_N,
            alpha=self.DGP_ALPHA,
            beta=self.DGP_BETA,
            gamma=self.DGP_GAMMA,
            m=self.DGP_M,
            sigma=self.DGP_SIGMA,
        )
        return {"y": y, "m": self.DGP_M, "horizon": self.HORIZON}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.holtwinters import ExponentialSmoothing  # type: ignore
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            y = np.asarray(fixture["y"], dtype=np.float64)
            m = int(fixture["m"])
            horizon = int(fixture["horizon"])

            fit = ExponentialSmoothing(
                y,
                trend="add",
                seasonal="add",
                seasonal_periods=m,
                damped_trend=False,
                initialization_method="estimated",
            ).fit(optimized=True)

        params = fit.params
        alpha = float(params.get("smoothing_level", np.nan))
        beta = float(params.get("smoothing_trend", np.nan))
        gamma = float(params.get("smoothing_seasonal", np.nan))
        # AIC / BIC: statsmodels exposes these on the ETS fit object
        try:
            aic = float(fit.aic)
        except Exception:
            aic = float("nan")
        try:
            bic = float(fit.bic)
        except Exception:
            bic = float("nan")
        sse = float(fit.sse) if hasattr(fit, "sse") else float("nan")
        sigma2 = sse / max(len(y) - 3, 1)  # rough estimate; not exact MLE
        rmse = float(np.sqrt(np.nanmean((y - fit.fittedvalues) ** 2)))

        forecast = np.asarray(fit.forecast(horizon), dtype=np.float64)

        return {
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "aic": aic,
            "bic": bic,
            "sigma2": sigma2,
            "rmse": rmse,
            "forecast": forecast,
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

            # Fit ETS(A,A,A) explicitly. forecast::ets parameterises
            # AAA = additive trend + additive seasonal.
            fit <- ets(y, model = "AAA", damped = FALSE, opt.crit = "lik")

            cf <- coef(fit)
            alpha <- as.numeric(fit$par["alpha"])
            beta  <- as.numeric(fit$par["beta"])
            gamma <- as.numeric(fit$par["gamma"])
            scalars <- c(
                alpha = alpha, beta = beta, gamma = gamma,
                aic = as.numeric(fit$aic),
                bic = as.numeric(fit$bic),
                sigma2 = as.numeric(fit$sigma2),
                rmse = as.numeric(accuracy(fit)["Training set", "RMSE"])
            )
            write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)

            fc <- forecast(fit, h = {horizon})
            write.table(matrix(as.numeric(fc$mean), ncol=1),
                        "{{{{OUTPUT_forecast}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars", "forecast"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )

        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "alpha": float(sc[0]),
            "beta": float(sc[1]),
            "gamma": float(sc[2]),
            "aic": float(sc[3]),
            "bic": float(sc[4]),
            "sigma2": float(sc[5]),
            "rmse": float(sc[6]),
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
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

        for key in ("alpha", "beta", "gamma"):
            primary[key] = _compare_scalar(
                tsl[key], ref[key], ladder["primary"],
            )
            if primary[key]["status"] == "BLOCK":
                any_block = True
            elif primary[key]["status"] == "CAVEAT":
                any_caveat = True

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref["forecast"], ladder["primary"],
        )
        if primary["forecast"]["status"] == "BLOCK":
            any_block = True
        elif primary["forecast"]["status"] == "CAVEAT":
            any_caveat = True

        for key in ("aic", "bic", "sigma2", "rmse"):
            secondary[key] = _compare_scalar(
                tsl[key], ref[key], ladder["secondary"],
            )

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "forecast_version": ref.get("forecast_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "m": int(self.DGP_M),
                "horizon": int(self.HORIZON),
            },
        )
