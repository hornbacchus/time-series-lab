"""Phase 3 Batch 1 — ETS / Holt-Winters parity check.

Compares TSL's ``engine/techniques/ets_hw.py`` against R
``forecast::ets`` on a synthetic Holt-Winters additive trend +
additive seasonal DGP-recovery fixture.

B1 migration update (Q2 engine-improvement): the engine was migrated
from CLASSICAL ``statsmodels.tsa.holtwinters.ExponentialSmoothing``
(SSE) to the modern STATE-SPACE
``statsmodels.tsa.exponential_smoothing.ets.ETSModel`` (likelihood).
``run_tsl`` was correspondingly rewritten from the prior INLINED
classical bypass to **invoke the migrated engine wrapper via
RunContext** — so the harness now exercises the real engine code path
(closing the prior bypass methodology gap) AND measures the
post-migration state-space-vs-state-space parity (both arms now
state-space ETS, per Hyndman-Koehler-Snyder-Grose 2008). The
cross-API-paradigm gap that drove the pre-migration mle-band should
narrow.

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

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
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


class EtsParity(P3ParityCheck):
    """ETS / Holt-Winters parity vs R forecast::ets.

    DGP: Holt-Winters AAA (additive trend + additive seasonal),
    alpha=0.3, beta=0.1, gamma=0.2, m=12, sigma=0.5, seed=42,
    T=200.
    """

    technique_id = "p3_ets"
    tier = "fast"
    fixture_id = ""

    verdict_class = "state_space_reform"
    verdict_class_rationale = (
        "statsmodels ExponentialSmoothing implements the "
        "classical Holt-Winters smoothing recursion; R "
        "forecast::ets implements the state-space "
        "reformulation per Hyndman-Khandakar 2008. Both are "
        "mathematically equivalent for the deterministic-state "
        "case but the optimizers see different objective "
        "surfaces and can land at different local optima with "
        "smoothing-parameter divergence ~1e-2 abs. AIC scale "
        "offset (~1070 abs) is methodology-equivalent (Secondary "
        "tier; non-blocking)."
    )

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
        # B1 migration: invoke the migrated engine wrapper (state-space
        # ETSModel) via RunContext rather than inlining statsmodels. This
        # exercises the real engine code path and measures the post-
        # migration parity. frequency="M" -> the engine infers
        # seasonal_periods=12; explicit params pin ETS AAA to match the R
        # forecast::ets model="AAA" reference.
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.ets_hw as ets_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        m = int(fixture["m"])
        horizon = int(fixture["horizon"])

        ctx = RunContext({
            "run_id": "p3_ets_parity",
            "technique_id": "ets",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "M",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "trend": "add", "seasonal": "add",
                "seasonal_periods": m, "horizon": horizon,
            },
        })
        resp = ets_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL ETS run failed: {resp.get('error_message')}"
            )
        af = resp.get("audit_fields", {})

        # Forecast vector from the Forecast table (column 1).
        fc_table = next(
            (t for t in resp["tables"] if "Forecast" in t.get("name", "")),
            None,
        )
        if fc_table is None:
            raise RuntimeError("TSL ETS forecast table not found")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]], dtype=np.float64,
        )

        # Residuals from the Fitted Values table (column 3, full
        # precision) -> sigma2/rmse secondary metrics (original
        # convention: sse/(n-3)).
        fv_table = next(
            (t for t in resp["tables"] if "Fitted" in t.get("name", "")),
            None,
        )
        if fv_table is not None:
            resid = np.array(
                [float(row[3]) for row in fv_table["rows"]], dtype=np.float64,
            )
            resid = resid[~np.isnan(resid)]
        else:
            resid = np.array([])
        if resid.size:
            sse = float(np.sum(resid ** 2))
            sigma2 = sse / max(len(y) - 3, 1)
            rmse = float(np.sqrt(np.mean(resid ** 2)))
        else:
            sigma2 = float("nan")
            rmse = float(af.get("rmse") or "nan")

        def _f(v):
            return float(v) if v is not None else float("nan")

        return {
            "alpha": _f(af.get("alpha")),
            "beta": _f(af.get("beta")),
            "gamma": _f(af.get("gamma")),
            "aic": _f(af.get("aic")),
            "bic": _f(af.get("bic")),
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
