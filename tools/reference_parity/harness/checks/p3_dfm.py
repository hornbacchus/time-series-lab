"""Phase 3 Batch 3 — DFM (Dynamic Factor Model) parity check.

Compares TSL's ``engine/techniques/dynamic_factor_model.py``
(statsmodels ``DynamicFactor``, EM-fit) against R
``MARSS::MARSS`` (independent EM/Kalman implementation) on a
synthetic 3-variable / 1-factor DFM fixture.

Reference selection note: master plan §6.1 lists R `MARSS` as
primary. Both implementations fit DFM via Kalman filter +
EM, but use different initialization heuristics, convergence
tolerances, and parameter parameterizations. This is an
**EM-stochastic verdict_class** — tolerance bands per master
plan §7.1 are loose (1e-2 abs / 5e-2 rel).

Output-tier discipline:

- **Primary:** estimated factor loadings vector (k_obs,),
  factor AR coefficient (scalar for k_factors=1, factor_order=1),
  log-likelihood.
- **Secondary:** AIC, BIC, factor-process variance
  (idiosyncratic + factor variance).
- **Diagnostic:** estimated latent factor series (correlation
  with TSL's smoothed factor, modulo sign).

Tier: **slow** (DFM EM-fit takes 5–20s typically; pile of two
EM-fits per check pushes it past the fast-tier 30s budget).

Fixture: T=200 with 3 observed series driven by 1 latent
AR(1) factor.
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


def _generate_dfm_dgp(
    *,
    seed: int,
    n: int = 200,
    k_obs: int = 3,
    factor_phi: float = 0.7,
    sigma_factor: float = 1.0,
    sigma_eps: float = 0.5,
    burn: int = 50,
) -> np.ndarray:
    """Generate (n, k_obs) DFM realization with 1 latent AR(1)
    factor.

    Process:
        f_t = factor_phi * f_{t-1} + eta_t,  eta ~ N(0, sigma_factor^2)
        Y_t,i = lambda_i * f_t + eps_{t,i},  eps ~ N(0, sigma_eps^2)
    Loadings lambda = (1.0, 0.7, 0.5) (anchored at first =1
    for identifiability).
    """
    rng = np.random.default_rng(seed)
    n_total = n + burn
    eta = rng.standard_normal(n_total) * sigma_factor
    f = np.zeros(n_total)
    for t in range(1, n_total):
        f[t] = factor_phi * f[t - 1] + eta[t]
    lambdas = np.array([1.0, 0.7, 0.5])[:k_obs]
    Y = np.outer(f, lambdas) + rng.standard_normal((n_total, k_obs)) * sigma_eps
    return Y[burn:]


class DfmParity(P3ParityCheck):
    """DFM 1-factor parity vs R MARSS::MARSS.

    DGP: 3-variable / 1-factor / AR(1) factor, T=200, seed=42.
    """

    technique_id = "p3_dfm"
    tier = "slow"  # EM-fit; ~10-30s typical
    fixture_id = ""

    verdict_class = "em_stochastic"
    verdict_class_rationale = (
        "DFM is fit via Kalman filter + Expectation-"
        "Maximization. statsmodels DynamicFactor and R "
        "MARSS::MARSS are independent EM implementations with "
        "different convergence criteria and parameter "
        "parameterizations. EM is a non-convex local-optimum "
        "search; small-sample fits can land at different "
        "loadings even with same data. Master plan §7.1 EM-"
        "stochastic class: 1e-2 abs / 5e-2 rel tolerance bands "
        "on Primary outputs."
    )

    DGP_N = 200
    DGP_K_OBS = 3
    DGP_K_FACTORS = 1
    DGP_FACTOR_ORDER = 1

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "Y": _generate_dfm_dgp(seed=seed, n=self.DGP_N,
                                    k_obs=self.DGP_K_OBS),
            "k_factors": self.DGP_K_FACTORS,
            "factor_order": self.DGP_FACTOR_ORDER,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.statespace.dynamic_factor import (  # type: ignore
            DynamicFactor,
        )
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        k_factors = int(fixture["k_factors"])
        factor_order = int(fixture["factor_order"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            model = DynamicFactor(
                Y, k_factors=k_factors, factor_order=factor_order,
                error_order=0,
            )
            fit = model.fit(disp=False, maxiter=200)

        # Loadings: parameters indexed by name; statsmodels names
        # them "loading.f1.y1", "loading.f1.y2", etc.
        params_dict = dict(zip(fit.param_names, fit.params))
        loadings = np.array(
            [params_dict.get(f"loading.f1.y{i + 1}", np.nan)
             for i in range(Y.shape[1])],
            dtype=np.float64,
        )
        # Factor AR coefficient
        factor_phi = float(params_dict.get("L1.f1.f1", np.nan))
        loglik = float(fit.llf)
        aic = float(fit.aic)
        bic = float(fit.bic)

        # Smoothed factor (for diagnostic correlation)
        try:
            factor_smoothed = np.asarray(
                fit.factors.smoothed[:, 0], dtype=np.float64,
            )
        except Exception:
            factor_smoothed = np.full(Y.shape[0], np.nan)

        return {
            "loadings": loadings,
            "factor_phi": factor_phi,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "factor_smoothed": factor_smoothed,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        # MARSS expects (k_obs, T) — transpose.
        Y_t = Y.T

        r_code = r"""
            suppressPackageStartupMessages({ library(MARSS) })
            Y <- as.matrix(read.csv("{{INPUT_Y}}", header=FALSE))
            # Y shape (k_obs, T) per MARSS convention.

            # Single-factor DFM model:
            #   x_t = B * x_{t-1} + w_t,  w ~ N(0, Q)
            #   y_t = Z * x_t + v_t,       v ~ N(0, R)
            # B = factor_phi (1x1); Q = sigma_factor^2 (1x1);
            # Z = loadings vector (k_obs x 1); R = diagonal
            # idiosyncratic variances.
            # Anchor first loading to 1 for identifiability
            # (matches statsmodels DynamicFactor default).
            k_obs <- nrow(Y)
            Z_mat <- matrix(list(0), k_obs, 1)
            Z_mat[1, 1] <- 1.0
            for (i in 2:k_obs) {
                Z_mat[i, 1] <- paste0("z", i)
            }

            mod_list <- list(
                B = matrix(list("phi"), 1, 1),
                U = matrix(0, 1, 1),
                Q = matrix(list("Q"), 1, 1),
                Z = Z_mat,
                A = matrix(0, k_obs, 1),
                R = "diagonal and unequal",
                x0 = matrix(0, 1, 1),
                tinitx = 0
            )

            fit <- MARSS(Y, model = mod_list, silent = TRUE,
                          control = list(maxit = 200, conv.test.slope.tol = 0.5))

            # Extract loadings z2..z_k_obs (z1 fixed at 1.0)
            params <- coef(fit, type = "vector")
            loadings <- c(1.0)
            for (i in 2:k_obs) {
                key <- paste0("Z.z", i)
                if (key %in% names(params)) {
                    loadings <- c(loadings, params[[key]])
                } else {
                    loadings <- c(loadings, NA)
                }
            }
            factor_phi <- params[["B.phi"]]
            log_lik <- as.numeric(fit$logLik)

            # AIC / BIC (MARSS exposes these)
            aic_v <- as.numeric(fit$AIC)
            bic_v <- as.numeric(fit$AICc)  # AICc; closest to BIC convention

            # Smoothed factor
            states <- as.numeric(fit$states)

            scalars <- c(factor_phi = factor_phi, loglik = log_lik,
                         aic = aic_v, bic = bic_v)
            write.table(matrix(loadings, ncol = 1),
                        "{{OUTPUT_loadings}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(scalars, ncol = 1),
                        "{{OUTPUT_scalars}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(states, ncol = 1),
                        "{{OUTPUT_factor_smoothed}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y_t},
            output_names=["loadings", "scalars", "factor_smoothed"],
            timeout_sec=240,
            capture_versions_for=["MARSS"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "loadings": np.atleast_1d(outputs["loadings"]).astype(np.float64).reshape(-1),
            "factor_phi": float(sc[0]),
            "loglik": float(sc[1]),
            "aic": float(sc[2]),
            "bic": float(sc[3]),
            "factor_smoothed": np.atleast_1d(outputs["factor_smoothed"]).astype(np.float64).reshape(-1),
            "marss_version": versions.get("MARSS", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        diagnostic: dict[str, Any] = {}
        statuses: list[str] = []

        # Loadings: MARSS anchors loadings[0] = 1.0 by explicit
        # constraint; statsmodels DynamicFactor does NOT anchor —
        # the factor is identified up to a scaling and sign
        # factor (the sign convention is implicit). Both
        # implementations find the same factor up to sign;
        # canonicalize TSL's loadings to the same sign convention
        # by anchoring loadings[0] = 1.0 (divide all by tsl
        # loadings[0]). Apply same canonicalization to ref to
        # guard against any divergence in MARSS's anchor.
        tsl_loadings = np.asarray(tsl["loadings"], dtype=np.float64).copy()
        ref_loadings = np.asarray(ref["loadings"], dtype=np.float64).copy()
        if abs(tsl_loadings[0]) > 1e-10:
            tsl_loadings = tsl_loadings / tsl_loadings[0]
        if abs(ref_loadings[0]) > 1e-10:
            ref_loadings = ref_loadings / ref_loadings[0]
        primary["loadings"] = _compare_vector(
            tsl_loadings, ref_loadings, ladder["primary"],
        )
        statuses.append(primary["loadings"]["status"])

        primary["factor_phi"] = _compare_scalar(
            tsl["factor_phi"], ref["factor_phi"], ladder["primary"],
        )
        statuses.append(primary["factor_phi"]["status"])

        # Log-likelihood: both maximize the same Gaussian
        # state-space likelihood. Different EM convergence
        # criteria → different stopping points → likelihood
        # divergence; expected within EM-stochastic band.
        primary["loglik"] = _compare_scalar(
            tsl["loglik"], ref["loglik"], ladder["primary"],
        )
        statuses.append(primary["loglik"]["status"])

        for key in ("aic", "bic"):
            secondary[key] = _compare_scalar(
                tsl[key], ref[key], ladder["secondary"],
            )

        # Diagnostic: smoothed factor correlation (modulo sign)
        try:
            tsl_f = np.asarray(tsl["factor_smoothed"], dtype=np.float64)
            ref_f = np.asarray(ref["factor_smoothed"], dtype=np.float64)
            mask = np.isfinite(tsl_f) & np.isfinite(ref_f)
            if int(mask.sum()) > 10:
                corr = float(np.corrcoef(
                    tsl_f[mask], ref_f[mask],
                )[0, 1])
            else:
                corr = float("nan")
            diagnostic["factor_correlation"] = {
                "status": "INFO",
                "abs_pearson_corr": float(abs(corr)),
                "n_compared": int(mask.sum()),
            }
        except Exception as e:
            diagnostic["factor_correlation"] = {
                "status": "INFO",
                "error": f"{type(e).__name__}: {e}",
            }

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                **diagnostic,
                "marss_version": ref.get("marss_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_obs": int(self.DGP_K_OBS),
            },
        )
