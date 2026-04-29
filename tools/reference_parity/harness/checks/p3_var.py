"""Phase 3 Batch 3 — VAR (Vector Autoregression) parity check.

Compares TSL's ``engine/techniques/var_model.py`` (statsmodels
``VAR``) against R ``vars::VAR`` on a synthetic bivariate
VAR(2) DGP-recovery fixture.

Reference selection note: TSL uses statsmodels VAR (Python);
R `vars::VAR` is an independent implementation. Per Pattern H
(DSCD — Documented Sub-Class Divergence within mle_fit) — both
optimizers solve the same OLS-on-stacked-equations VAR
estimation, but differ in: (a) sigma residual covariance
divisor convention (statsmodels divides by T - k_total;
vars::VAR also uses T - k_total but with slightly different
k_total accounting for the constant term); (b) lag selection
heuristics (here we pin lag=2 explicitly to bypass).

VAR is technically OLS-on-stacked equations, so it should fit
in the **closed-form** verdict_class (no iterative MLE on the
coefficient matrix; the OLS step is exact). Coefficient parity
should achieve machine precision modulo the divisor convention.

Output-tier discipline:

- **Primary:** stacked AR coefficient matrix A (k*p, k), Sigma
  residual covariance, log-likelihood.
- **Secondary:** AIC, BIC, h-step forecast.
- **Diagnostic:** companion-form eigenvalues (TSL-side; feeds
  the structural-invariant check).

Structural invariants (Pattern F):
- ``var_eigenvalues``: max |companion eigenvalue| < 1
  (stationarity).
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


def _generate_var_dgp(
    *,
    seed: int,
    n: int = 500,
    k: int = 2,
    p: int = 2,
    burn: int = 200,
) -> np.ndarray:
    """Generate stationary VAR(2) realization, k=2.

    Coefficients chosen so companion eigenvalues are well inside
    the unit circle:
        A_1 = [[0.5, 0.1], [0.0, 0.4]]
        A_2 = [[0.1, 0.0], [0.05, 0.2]]
    Sigma = I_2 (identity innovation covariance).

    Returns shape (n, k).
    """
    rng = np.random.default_rng(seed)
    A1 = np.array([[0.5, 0.1], [0.0, 0.4]])
    A2 = np.array([[0.1, 0.0], [0.05, 0.2]])
    n_total = n + burn
    Y = np.zeros((n_total, k))
    eps = rng.standard_normal((n_total, k))
    for t in range(2, n_total):
        Y[t] = A1 @ Y[t - 1] + A2 @ Y[t - 2] + eps[t]
    return Y[burn:]


class VarParity(P3ParityCheck):
    """VAR(2) parity vs R vars::VAR.

    DGP: bivariate VAR(2), seed=42, T=500.
    """

    technique_id = "p3_var"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "VAR(p) estimation is OLS-on-stacked-equations: "
        "regress each variable on its own and other variables' "
        "p lags. statsmodels VAR and R vars::VAR implement the "
        "same closed-form normal-equations solve. Coefficients "
        "agree at machine precision modulo divisor convention "
        "for the residual covariance Sigma (T - k_total), which "
        "is identical between the two implementations once "
        "constants are accounted for."
    )

    structural_invariants = (
        StructuralInvariant(
            name="companion_eigenvalues_stable",
            invariant_type="var_eigenvalues",
            tolerance=1e-3,
            tolerance_type="relative",
        ),
    )

    DGP_K = 2
    DGP_P_FIT = 2
    DGP_N = 500
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "Y": _generate_var_dgp(
                seed=seed, n=self.DGP_N, k=self.DGP_K, p=self.DGP_P_FIT,
            ),
            "p": self.DGP_P_FIT,
            "horizon": self.HORIZON,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke statsmodels VAR directly to bypass TSL
        wrapper's 6-decimal output rounding (Phase 1 finding B8).
        """
        _ensure_engine_on_path()
        from statsmodels.tsa.api import VAR  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        p = int(fixture["p"])
        horizon = int(fixture["horizon"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            model = VAR(Y)
            fit = model.fit(p, trend="c")

        # Stacked AR coefficient matrix: shape (k*p + 1, k)
        # where the first row is the constant term. Reshape to
        # (p, k, k) for per-lag matrices excluding constant.
        # statsmodels: fit.coefs has shape (p, k, k).
        coefs = np.asarray(fit.coefs, dtype=np.float64)  # (p, k, k)
        intercept = np.asarray(fit.intercept, dtype=np.float64)  # (k,)
        sigma_u = np.asarray(fit.sigma_u, dtype=np.float64)  # (k, k)
        loglik = float(fit.llf)
        aic = float(fit.aic)
        bic = float(fit.bic)

        # h-step forecast given last p observations
        last_p = Y[-p:]
        forecast = fit.forecast(last_p, steps=horizon)

        # Companion-form eigenvalues for structural invariant
        k = Y.shape[1]
        # Stack: top row is [A_1, A_2, ..., A_p]; bottom is
        # block identity shifted right by k.
        companion = np.zeros((k * p, k * p))
        for i in range(p):
            companion[:k, i * k:(i + 1) * k] = coefs[i]
        if p > 1:
            companion[k:, :k * (p - 1)] = np.eye(k * (p - 1))
        eigs = np.linalg.eigvals(companion)
        eig_magnitudes = np.abs(eigs)

        return {
            "coefs": coefs,           # (p, k, k)
            "intercept": intercept,   # (k,)
            "sigma_u": sigma_u,       # (k, k)
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "forecast": forecast,     # (horizon, k)
            "companion_eig_magnitudes": eig_magnitudes,  # (k*p,)
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        p = int(fixture["p"])
        horizon = int(fixture["horizon"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(vars) }})
            Y_raw <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))

            fit <- VAR(Y_raw, p = {p}, type = "const")

            # Extract coefficients per equation. vars::VAR returns
            # a list of lm() objects, one per equation. The
            # coefficient ordering for each equation is:
            #   variable_1.l1, variable_2.l1, ..., variable_k.l1,
            #   variable_1.l2, ..., variable_k.l2, ...,
            #   variable_1.lp, ..., variable_k.lp, const
            k <- ncol(Y_raw)
            coefs_per_eq <- sapply(seq_len(k), function(i) {{
                coef(fit$varresult[[i]])
            }})  # shape ((k*p+1), k); each column is an equation
            # Drop intercept (last row) for AR coefs
            ar_block <- coefs_per_eq[1:(k * {p}), , drop = FALSE]
            # Reshape to (p, k_lag, k_eq):
            # for lag j (1..p), per-eq AR matrix is rows
            # ((j-1)*k+1):(j*k) of ar_block. Result block[j,i,e]
            # = coefficient of variable i at lag j in equation e.
            # statsmodels uses (p, k_eq, k_var); we transpose
            # to that shape.
            coefs_array <- array(0, dim = c({p}, k, k))
            for (j in 1:{p}) {{
                # ar_block rows ((j-1)*k+1):(j*k), all cols.
                # Each col = an equation; rows = predictor vars
                # at lag j. Transposed so first index is equation.
                lag_block <- ar_block[((j - 1) * k + 1):(j * k), ,
                                      drop = FALSE]
                # lag_block: rows = predictors, cols = equations.
                # statsmodels coefs[j-1] indexed [eq, var]; need
                # to transpose lag_block so rows = equations.
                coefs_array[j, , ] <- t(lag_block)
            }}
            intercept <- coefs_per_eq[k * {p} + 1, ]

            # Sigma_u via residuals
            res <- residuals(fit)
            sigma_u <- crossprod(res) / (nrow(res) - ({p} * k + 1))

            # Log-likelihood + IC
            ll <- as.numeric(logLik(fit))
            aic_v <- as.numeric(AIC(fit))
            bic_v <- as.numeric(BIC(fit))

            # h-step forecast (point only)
            fc <- predict(fit, n.ahead = {horizon})
            fc_mat <- sapply(seq_len(k), function(i) fc$fcst[[i]][, "fcst"])
            # fc_mat is (horizon, k)

            write.table(matrix(as.numeric(coefs_array), ncol = 1),
                        "{{{{OUTPUT_coefs}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(intercept), ncol = 1),
                        "{{{{OUTPUT_intercept}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(sigma_u), ncol = 1),
                        "{{{{OUTPUT_sigma_u}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            scalars <- c(loglik = ll, aic = aic_v, bic = bic_v)
            write.table(matrix(scalars, ncol = 1),
                        "{{{{OUTPUT_scalars}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(fc_mat), ncol = 1),
                        "{{{{OUTPUT_forecast}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y},
            output_names=["coefs", "intercept", "sigma_u",
                          "scalars", "forecast"],
            timeout_sec=60,
            capture_versions_for=["vars"],
        )
        k = Y.shape[1]
        coefs_flat = np.atleast_1d(outputs["coefs"]).astype(np.float64).reshape(-1)
        # R column-major; reshape (p, k, k) using Fortran order
        coefs = coefs_flat.reshape((p, k, k), order="F")
        sigma_u_flat = np.atleast_1d(outputs["sigma_u"]).astype(np.float64).reshape(-1)
        sigma_u = sigma_u_flat.reshape((k, k), order="F")
        forecast_flat = np.atleast_1d(outputs["forecast"]).astype(np.float64).reshape(-1)
        forecast = forecast_flat.reshape((horizon, k), order="F")
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "coefs": coefs,
            "intercept": np.atleast_1d(outputs["intercept"]).astype(np.float64).reshape(-1),
            "sigma_u": sigma_u,
            "loglik": float(sc[0]),
            "aic": float(sc[1]),
            "bic": float(sc[2]),
            "forecast": forecast,
            "vars_version": versions.get("vars", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["coefs"] = _compare_vector(
            np.asarray(tsl["coefs"]).reshape(-1),
            np.asarray(ref["coefs"]).reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["coefs"]["status"])

        primary["intercept"] = _compare_vector(
            np.asarray(tsl["intercept"]).reshape(-1),
            np.asarray(ref["intercept"]).reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["intercept"]["status"])

        primary["sigma_u"] = _compare_vector(
            np.asarray(tsl["sigma_u"]).reshape(-1),
            np.asarray(ref["sigma_u"]).reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["sigma_u"]["status"])

        primary["loglik"] = _compare_scalar(
            tsl["loglik"], ref["loglik"], ladder["primary"],
        )
        statuses.append(primary["loglik"]["status"])

        primary["forecast"] = _compare_vector(
            np.asarray(tsl["forecast"]).reshape(-1),
            np.asarray(ref["forecast"]).reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["forecast"]["status"])

        for key in ("aic", "bic"):
            secondary[key] = _compare_scalar(
                tsl[key], ref[key], ladder["secondary"],
            )

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "vars_version": ref.get("vars_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_vars": int(self.DGP_K),
                "p_lag": int(self.DGP_P_FIT),
                "max_companion_eig": float(np.max(
                    np.asarray(tsl["companion_eig_magnitudes"]),
                )),
            },
        )
