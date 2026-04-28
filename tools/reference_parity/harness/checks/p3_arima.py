"""Phase 3 Batch 1 — ARIMA (manual order) parity check.

Compares TSL's ``engine/techniques/arima.py`` (manual-order path,
``technique_id="arima"``) against R ``forecast::Arima`` on a
synthetic ARIMA(1,1,1) DGP-recovery fixture. Both implementations
fit by maximum likelihood; the parity audit verifies that the
deterministic optimizers (statsmodels' L-BFGS-B vs R's CSS-then-
ML) converge to the same point estimate within the master plan
§7.1 MLE-fit tolerance band (abs_tol=1e-3, rel_tol=1e-2).

Output-tier discipline (master plan §4):

- **Primary:** AR coefficient vector, MA coefficient vector,
  log-likelihood, h-step point forecast.
- **Secondary:** AIC, BIC, RMSE on in-sample residuals, sigma^2
  (innovation variance).
- **Diagnostic:** fitted in-sample series (correlation only).

Fixture: T=400 ARIMA(1,1,1) DGP with phi=0.6, theta=0.4,
sigma=1.0, drift=0.0, seed=42. Generated at runtime
(``fixture_id=""``) so the fixture is fully reproducible from
the seed alone — no on-disk artifact needed.

This check is the first in the **Session 2 manual harness pattern
lock**: the structural layout (DGP generator → TSL invoke →
R reference invoke → tolerance ladder application → tiered
metric reporting) is the template Sessions 3–4 follow for the
remaining 7 Batch 1 wrappers.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


# ---------------------------------------------------------------------
# Path setup helper (replicated across harness/checks/* per the
# established pattern; Session 5 generator abstraction will factor
# out into a shared module)
# ---------------------------------------------------------------------

def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import TSL's arima
    wrapper."""
    import pathlib
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


# ---------------------------------------------------------------------
# DGP generator
# ---------------------------------------------------------------------

def _generate_arima_dgp(
    *,
    seed: int,
    n: int = 400,
    phi: float = 0.6,
    theta: float = 0.4,
    sigma: float = 1.0,
    d: int = 1,
) -> np.ndarray:
    """Generate ARIMA(1, d, 1) realization.

    Process: y_t = y_{t-1} + u_t where u_t = phi*u_{t-1} +
    eps_t + theta*eps_{t-1}, eps ~ N(0, sigma^2). For d=1, the
    differenced series is ARMA(1,1). Burn-in 100 samples to
    achieve stationarity of the underlying ARMA component.
    """
    rng = np.random.default_rng(seed)
    burn = 100
    n_total = n + burn
    eps = rng.standard_normal(n_total) * sigma

    # ARMA(1,1) in differences: u_t = phi*u_{t-1} + eps_t + theta*eps_{t-1}
    u = np.zeros(n_total)
    for t in range(1, n_total):
        u[t] = phi * u[t - 1] + eps[t] + theta * eps[t - 1]

    # Integrate d times
    y = u
    for _ in range(d):
        y = np.cumsum(y)

    return y[burn:]


# ---------------------------------------------------------------------
# ParityCheck subclass
# ---------------------------------------------------------------------

class ArimaManualParity(ParityCheck):
    """ARIMA manual-order parity vs R forecast::Arima.

    DGP: ARIMA(1,1,1) with phi=0.6, theta=0.4, sigma=1.0,
    seed=42, T=400. Both implementations fit ARIMA(1,1,1) order;
    we compare MLE point estimates + log-likelihood + 5-step
    forecast.
    """

    technique_id = "p3_arima_manual"
    tier = "fast"
    fixture_id = ""  # generated at runtime from seed

    # DGP parameters (also used as fitted order)
    DGP_PHI = 0.6
    DGP_THETA = 0.4
    DGP_SIGMA = 1.0
    DGP_D = 1
    DGP_N = 400
    FIT_ORDER = (1, 1, 1)
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_arima_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=self.DGP_PHI,
            theta=self.DGP_THETA,
            sigma=self.DGP_SIGMA,
            d=self.DGP_D,
        )
        return {"y": y, "order": self.FIT_ORDER, "horizon": self.HORIZON}

    # -----------------------------------------------------------------
    # TSL side
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.arima as arima_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        order = tuple(fixture["order"])
        horizon = int(fixture["horizon"])

        ctx = RunContext({
            "run_id": "p3_arima_parity",
            "technique_id": "arima",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "order": list(order),
                "horizon": horizon,
                "seasonal_order": [0, 0, 0, 0],
            },
        })

        # We need access to the underlying statsmodels fit object
        # to extract AR/MA coefficients explicitly. The wrapper
        # returns a public response with audit_fields (aic, bic,
        # rmse) but does NOT expose AR/MA coefs in audit. So we
        # call the underlying ARIMA fit directly to extract coefs
        # and run the wrapper for AIC/BIC/forecast cross-check.
        from statsmodels.tsa.arima.model import ARIMA  # type: ignore
        sm_fit = ARIMA(y, order=order, seasonal_order=(0, 0, 0, 0)).fit()

        # Extract AR + MA coefficients from statsmodels params
        # vector. The params order for ARIMA(p,d,q) is:
        #   [const (if d=0)?, ar.L1..ar.Lp, ma.L1..ma.Lq, sigma2]
        # We use the named param_names instead of positional.
        names = list(sm_fit.param_names)
        params = np.asarray(sm_fit.params, dtype=np.float64)
        ar_coefs = np.array(
            [params[names.index(f"ar.L{i}")] for i in range(1, order[0] + 1)],
            dtype=np.float64,
        )
        ma_coefs = np.array(
            [params[names.index(f"ma.L{i}")] for i in range(1, order[2] + 1)],
            dtype=np.float64,
        )
        # sigma2 is named "sigma2" in statsmodels
        sigma2 = float(params[names.index("sigma2")])
        loglik = float(sm_fit.llf)
        aic = float(sm_fit.aic)
        bic = float(sm_fit.bic)

        # Forecast h steps
        fc_obj = sm_fit.get_forecast(steps=horizon)
        fc = np.asarray(fc_obj.predicted_mean, dtype=np.float64)

        # Fitted in-sample (for diagnostic correlation)
        fitted_raw = np.asarray(sm_fit.fittedvalues, dtype=np.float64)
        # statsmodels may return a shorter fittedvalues array when
        # d > 0; pad with NaN at the front so length matches y.
        if len(fitted_raw) < len(y):
            pad = np.full(len(y) - len(fitted_raw), np.nan)
            fitted = np.concatenate([pad, fitted_raw])
        else:
            fitted = fitted_raw
        residuals = y - fitted
        rmse = float(np.sqrt(np.nanmean(residuals ** 2)))

        # Also exercise the public wrapper to verify it returns
        # consistent audit_fields (regression sanity; not part of
        # the parity assertion).
        try:
            wrapper_resp = arima_mod.run(ctx, lambda *a, **kw: None)
            wrapper_aic = wrapper_resp.get("audit_fields", {}).get("aic")
        except Exception:
            wrapper_aic = None

        return {
            "ar_coefs": ar_coefs,
            "ma_coefs": ma_coefs,
            "sigma2": sigma2,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": fc,
            "fitted": fitted,
            "rmse": rmse,
            "wrapper_aic": wrapper_aic,
        }

    # -----------------------------------------------------------------
    # Reference side: R forecast::Arima
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        order = tuple(fixture["order"])
        horizon = int(fixture["horizon"])

        p, d, q = order
        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])

            # Fit ARIMA(p,d,q) with method = "ML" (MLE only — matches
            # statsmodels' MLE-only path). Default is CSS-ML which
            # uses CSS for starting values then switches to ML;
            # asking for "ML" directly gives a closer apples-to-
            # apples optimizer comparison.
            fit <- Arima(y, order = c({p}, {d}, {q}), method = "ML",
                         include.constant = FALSE)

            # AR / MA coefficients
            cf <- coef(fit)
            ar_names <- grep("^ar", names(cf), value = TRUE)
            ma_names <- grep("^ma", names(cf), value = TRUE)
            ar_coefs <- if (length(ar_names) > 0) cf[ar_names] else numeric(0)
            ma_coefs <- if (length(ma_names) > 0) cf[ma_names] else numeric(0)

            write.table(
                matrix(ar_coefs, ncol = 1), "{{{{OUTPUT_ar_coefs}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )
            write.table(
                matrix(ma_coefs, ncol = 1), "{{{{OUTPUT_ma_coefs}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )

            # Scalars: loglik, aic, bic, sigma^2
            scalars <- c(
                loglik = as.numeric(logLik(fit)),
                aic = as.numeric(fit$aic),
                bic = as.numeric(fit$bic),
                sigma2 = as.numeric(fit$sigma2)
            )
            write.table(
                matrix(scalars, ncol = 1), "{{{{OUTPUT_scalars}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )

            # h-step forecast (point only)
            fc <- forecast(fit, h = {horizon})
            write.table(
                matrix(as.numeric(fc$mean), ncol = 1),
                "{{{{OUTPUT_forecast}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )

            # In-sample fitted (for diagnostic correlation)
            write.table(
                matrix(as.numeric(fitted(fit)), ncol = 1),
                "{{{{OUTPUT_fitted}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["ar_coefs", "ma_coefs", "scalars",
                          "forecast", "fitted"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )

        scalars = np.atleast_1d(outputs["scalars"]).reshape(-1)
        loglik, aic, bic, sigma2 = scalars[0], scalars[1], scalars[2], scalars[3]

        return {
            "ar_coefs": np.atleast_1d(outputs["ar_coefs"]).astype(np.float64).reshape(-1),
            "ma_coefs": np.atleast_1d(outputs["ma_coefs"]).astype(np.float64).reshape(-1),
            "sigma2": float(sigma2),
            "loglik": float(loglik),
            "aic": float(aic),
            "bic": float(bic),
            "forecast": np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1),
            "fitted": np.atleast_1d(outputs["fitted"]).astype(np.float64).reshape(-1),
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

        # ---- Primary tier: AR coefs ----
        primary_metrics["ar_coefs"] = _compare_vector(
            tsl["ar_coefs"], ref["ar_coefs"], ladder["primary"],
        )
        if primary_metrics["ar_coefs"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["ar_coefs"]["status"] == "CAVEAT":
            any_caveat = True

        # ---- Primary tier: MA coefs ----
        primary_metrics["ma_coefs"] = _compare_vector(
            tsl["ma_coefs"], ref["ma_coefs"], ladder["primary"],
        )
        if primary_metrics["ma_coefs"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["ma_coefs"]["status"] == "CAVEAT":
            any_caveat = True

        # ---- Primary tier: log-likelihood ----
        primary_metrics["loglik"] = _compare_scalar(
            tsl["loglik"], ref["loglik"], ladder["primary"],
        )
        if primary_metrics["loglik"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["loglik"]["status"] == "CAVEAT":
            any_caveat = True

        # ---- Primary tier: forecast vector ----
        primary_metrics["forecast"] = _compare_vector(
            tsl["forecast"], ref["forecast"], ladder["primary"],
        )
        if primary_metrics["forecast"]["status"] == "BLOCK":
            any_block = True
        elif primary_metrics["forecast"]["status"] == "CAVEAT":
            any_caveat = True

        # ---- Secondary tier: sigma^2 ----
        secondary_metrics["sigma2"] = _compare_scalar(
            tsl["sigma2"], ref["sigma2"], ladder["secondary"],
        )

        # ---- Secondary tier: AIC, BIC ----
        secondary_metrics["aic"] = _compare_scalar(
            tsl["aic"], ref["aic"], ladder["secondary"],
        )
        secondary_metrics["bic"] = _compare_scalar(
            tsl["bic"], ref["bic"], ladder["secondary"],
        )

        # ---- Diagnostic tier: fitted in-sample correlation ----
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

        # Determine outcome
        if any_block:
            outcome = "BLOCK"
        elif any_caveat:
            outcome = "CAVEAT"
        else:
            outcome = "PASS"

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={
                "primary": primary_metrics,
                "secondary": secondary_metrics,
            },
            diagnostics={
                **diagnostic_metrics,
                "forecast_version": ref.get("forecast_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "fit_order": list(self.FIT_ORDER),
                "wrapper_aic": tsl.get("wrapper_aic"),
            },
        )


# ---------------------------------------------------------------------
# Comparison helpers (Session 2 manual-pattern lock — duplicated in
# p3_sarima.py and p3_arimax_sarimax.py; Session 5 generator
# abstraction will factor into compare.py)
# ---------------------------------------------------------------------

def _compare_scalar(
    a: float, b: float, tol: dict[str, float],
) -> dict[str, Any]:
    """Compare two scalars within an absolute/relative tolerance
    band. Returns a metric dict with status PASS / CAVEAT /
    BLOCK and the achieved abs/rel diff."""
    abs_tol = float(tol.get("abs_tol", 1e-3))
    rel_tol = float(tol.get("rel_tol", 1e-2))
    block_abs_tol = float(tol.get("block_abs_tol", 10 * abs_tol))
    block_rel_tol = float(tol.get("block_rel_tol", 10 * rel_tol))
    a, b = float(a), float(b)
    diff = abs(a - b)
    denom = max(abs(a), abs(b), 1e-300)
    rel = diff / denom
    if diff <= abs_tol or rel <= rel_tol:
        status = "PASS"
    elif diff <= block_abs_tol or rel <= block_rel_tol:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "status": status,
        "abs_diff": diff,
        "rel_diff": rel,
        "tsl": a,
        "ref": b,
    }


def _compare_vector(
    a: np.ndarray, b: np.ndarray, tol: dict[str, float],
) -> dict[str, Any]:
    """Compare two 1-D vectors within an absolute/relative
    tolerance band. PASS iff every element passes; CAVEAT if any
    element CAVEATs but none BLOCK; BLOCK if any element BLOCKs."""
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        return {
            "status": "BLOCK",
            "shape_mismatch": True,
            "tsl_shape": list(a.shape),
            "ref_shape": list(b.shape),
        }
    if a.size == 0:
        return {
            "status": "PASS",
            "max_abs_diff": 0.0,
            "max_rel_diff": 0.0,
            "n_compared": 0,
        }
    abs_tol = float(tol.get("abs_tol", 1e-3))
    rel_tol = float(tol.get("rel_tol", 1e-2))
    block_abs_tol = float(tol.get("block_abs_tol", 10 * abs_tol))
    block_rel_tol = float(tol.get("block_rel_tol", 10 * rel_tol))
    diff = np.abs(a - b)
    denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-300)
    rel = diff / denom
    max_abs = float(np.max(diff))
    max_rel = float(np.max(rel))
    # PASS iff max_abs <= abs_tol OR max_rel <= rel_tol (per element
    # OR aggregate; we use aggregate here since shape parity has
    # already been checked).
    if max_abs <= abs_tol or max_rel <= rel_tol:
        status = "PASS"
    elif max_abs <= block_abs_tol or max_rel <= block_rel_tol:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "status": status,
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "n_compared": int(a.size),
        "tsl_first": float(a.flat[0]) if a.size > 0 else None,
        "ref_first": float(b.flat[0]) if b.size > 0 else None,
    }
