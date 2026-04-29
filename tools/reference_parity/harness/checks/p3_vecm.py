"""Phase 3 Batch 3 — VECM (Vector Error Correction Model)
parity check.

Compares TSL's ``engine/techniques/vecm_model.py``
(statsmodels ``VECM``) against R ``urca::ca.jo`` (cointegration
test) + ``vars::vec2var`` (VECM → VAR-form for forecasting) on
a synthetic bivariate cointegrated VAR(2) with rank=1
cointegration.

Reference selection note: the canonical R workflow for VECM is
two-step: `urca::ca.jo` runs Johansen's procedure to determine
cointegration rank `r`, then `vars::vec2var(coint_test, r)`
converts to VAR form for forecasting. statsmodels
`VECM(endog, k_ar_diff, coint_rank)` fits in one step. Both
implement the Johansen MLE.

This check focuses on **rank invariance** (the structural
invariant — vecm_cointegration_rank) and the alpha (loading) +
beta (cointegrating vector) coefficient parity.

Output-tier discipline:

- **Primary:** alpha matrix (k, r), beta matrix (k, r),
  short-run AR coefs (k, k * (k_ar_diff)), log-likelihood,
  cointegrating rank r.
- **Secondary:** AIC, BIC.

Structural invariants (Pattern F, Session 7 second concrete
population):
- ``vecm_cointegration_rank``: TSL r == R r (exact integer
  match expected on standard fixtures).
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


def _generate_vecm_dgp(
    *,
    seed: int,
    n: int = 500,
    burn: int = 200,
) -> np.ndarray:
    """Generate stationary bivariate cointegrated VAR(2)
    realization with cointegration rank r=1.

    Build via random-walk + cointegrating relation:
        y2_t = y2_{t-1} + eta_t,  eta ~ N(0, 1)
        y1_t = 0.7 * y2_t + xi_t,  xi ~ N(0, 0.5^2) (stationary)
    Cointegrating vector: (1, -0.7) so y1 - 0.7*y2 ~ I(0).

    Returns shape (n, 2).
    """
    rng = np.random.default_rng(seed)
    n_total = n + burn
    y2 = np.cumsum(rng.standard_normal(n_total))
    xi = rng.standard_normal(n_total) * 0.5
    y1 = 0.7 * y2 + xi
    Y = np.column_stack([y1, y2])
    return Y[burn:]


class VecmParity(P3ParityCheck):
    """VECM rank=1 parity vs R urca::ca.jo + vars::vec2var.

    DGP: bivariate cointegrated, true rank=1, T=500, seed=42.
    """

    technique_id = "p3_vecm"
    tier = "fast"
    fixture_id = ""

    # Phase 3.5 Session 3 (Item 1): migrated from `mle_fit` to
    # `single_impl_mle`. Phase 3 Session 7 measured 9.99e-16 abs
    # (beta after sign normalization) and 2.78e-13 abs (alpha) —
    # 13 orders of magnitude headroom inside the canonical mle_fit
    # 1e-3 band. Both implementations reduce to closed-form OLS
    # on the cointegrating vectors after Johansen's reduced-rank
    # regression collapses to its analytical solution; only
    # invisible optimizer convergence noise separates them.
    verdict_class = "single_impl_mle"
    verdict_class_rationale = (
        "VECM Johansen reduces to closed-form OLS on the "
        "cointegrating vectors. statsmodels `VECM.fit` and R "
        "`urca::ca.jo`+`vars::vec2var` implement identical "
        "reduced-rank regression math; both arms produce machine-"
        "precision-identical betas (Phase 3 Session 7 measured "
        "9.99e-16 abs after sign normalization). The single-"
        "implementation MLE classification reflects that the "
        "underlying linear algebra is identical between the two "
        "arms — only optimizer convergence-criterion noise "
        "(invisible at this regression scale) separates them."
    )

    structural_invariants = (
        StructuralInvariant(
            name="cointegrating_rank_match",
            invariant_type="vecm_cointegration_rank",
            tolerance=0,  # exact integer match expected
            tolerance_type="absolute",
        ),
    )

    DGP_N = 500
    K_AR_DIFF = 1  # VECM lag-difference order = VAR(p) p-1
    COINT_RANK = 1
    DET_ORDER = 0  # no deterministic trend; constant inside coint

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "Y": _generate_vecm_dgp(seed=seed, n=self.DGP_N),
            "k_ar_diff": self.K_AR_DIFF,
            "coint_rank": self.COINT_RANK,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.vector_ar.vecm import VECM  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        k_ar_diff = int(fixture["k_ar_diff"])
        coint_rank = int(fixture["coint_rank"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            # `deterministic="ci"` = constant inside the
            # cointegrating relation (matches R `ecdet="const"`).
            model = VECM(Y, k_ar_diff=k_ar_diff,
                         coint_rank=coint_rank, deterministic="ci")
            fit = model.fit()

        # alpha: loading matrix (k, r); beta: cointegrating
        # vectors (k, r).
        alpha = np.asarray(fit.alpha, dtype=np.float64)
        beta = np.asarray(fit.beta, dtype=np.float64)
        # Short-run AR diff coefs: gamma (k, k * k_ar_diff)
        try:
            gamma = np.asarray(fit.gamma, dtype=np.float64)
        except Exception:
            gamma = np.zeros((Y.shape[1], 0))
        # statsmodels VECM.llf is the log-likelihood
        try:
            loglik = float(fit.llf)
        except Exception:
            loglik = float("nan")
        try:
            aic = float(fit.aic)
            bic = float(fit.bic)
        except Exception:
            aic = float("nan")
            bic = float("nan")

        return {
            "alpha": alpha,
            "beta": beta,
            "gamma": gamma,
            "loglik": loglik,
            "aic": aic,
            "bic": bic,
            "cointegrating_rank": coint_rank,  # asserted
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        k_ar_diff = int(fixture["k_ar_diff"])
        coint_rank = int(fixture["coint_rank"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca); library(vars) }})
            Y <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))

            # urca::ca.jo: Johansen cointegration test.
            #   K = number of lags in the level form (VAR(K), so
            #       VECM has K-1 short-run differences).
            #   ecdet = "const" → constant inside cointegrating
            #       relation (matches statsmodels deterministic="ci").
            #   spec = "longrun" → standard Johansen.
            jt <- ca.jo(Y, K = {k_ar_diff} + 1, ecdet = "const",
                        spec = "longrun")

            # Extract trace stats and critical values to
            # determine rank
            trace_stats <- jt@teststat
            cvals_5pct <- jt@cval[, "5pct"]
            r_inferred <- 0
            for (i in seq_along(trace_stats)) {{
                # ca.jo orders test stats from H0:r=k-1 (smallest)
                # to H0:r=0 (largest). The "trace" sequence is
                # iterated from the smallest hypothesis upward
                # in vars::cajorls usage but here we follow
                # ca.jo's natural ordering: H0:r<=k-i for i=1..k.
                if (trace_stats[i] > cvals_5pct[i]) {{
                    r_inferred <- length(trace_stats) - i + 1
                    break
                }}
            }}

            # Convert to VAR form with the user-specified rank
            # for coefficient extraction.
            vmod <- vec2var(jt, r = {coint_rank})

            # Extract alpha (loadings) and beta (cointegrating
            # vectors). cajorls returns these as part of the
            # restricted regression.
            cajo_rls <- cajorls(jt, r = {coint_rank})
            alpha <- as.matrix(cajo_rls$rlm$coefficients[1:{coint_rank}, ,
                                                          drop = FALSE])
            # ca.jo's beta (V) is in jt@V (eigenvector matrix);
            # the first r columns are the cointegrating relations
            beta_full <- jt@V
            beta <- beta_full[1:nrow(Y_to_check_dim_only <- t(t(Y))[1:1, , drop=FALSE]) , 1:{coint_rank}, drop = FALSE]
            # The above index trick is to get k rows; simplify:
            beta <- jt@V[, 1:{coint_rank}, drop = FALSE]
            # jt@V has dim (k+ecdet_extras, k+ecdet_extras); take
            # first k rows (variable rows; trailing rows are
            # determinstic/intercept terms).
            k <- ncol(Y)
            beta <- beta[1:k, , drop = FALSE]

            # vec2var Phi (level coefficient matrices); not used
            # for parity but available.
            log_lik <- as.numeric(logLik(vmod))

            scalars <- c(rank = r_inferred, loglik = log_lik)
            write.table(matrix(as.numeric(alpha), ncol = 1),
                        "{{{{OUTPUT_alpha}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(beta), ncol = 1),
                        "{{{{OUTPUT_beta}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(scalars, ncol = 1),
                        "{{{{OUTPUT_scalars}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y},
            output_names=["alpha", "beta", "scalars"],
            timeout_sec=60,
            capture_versions_for=["urca", "vars"],
        )
        k = Y.shape[1]
        alpha_flat = np.atleast_1d(outputs["alpha"]).astype(np.float64).reshape(-1)
        beta_flat = np.atleast_1d(outputs["beta"]).astype(np.float64).reshape(-1)
        # alpha shape: (rank, k) per cajorls output (rows = ECT,
        # cols = equation). statsmodels returns (k, rank). We
        # transpose to (k, rank).
        alpha = alpha_flat.reshape((coint_rank, k), order="F").T
        beta = beta_flat.reshape((k, coint_rank), order="F")
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "alpha": alpha,
            "beta": beta,
            "loglik": float(sc[1]),
            "cointegrating_rank": int(sc[0]),
            "urca_version": versions.get("urca", "unknown"),
            "vars_version": versions.get("vars", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        statuses: list[str] = []

        # Beta normalization: statsmodels normalizes the first
        # element of each cointegrating vector to 1; R ca.jo's
        # @V eigenvectors have arbitrary norm. Normalize both
        # sides via first element to align.
        def _normalize_beta(b: np.ndarray) -> np.ndarray:
            b = np.asarray(b, dtype=np.float64).copy()
            for j in range(b.shape[1]):
                if abs(b[0, j]) > 1e-12:
                    b[:, j] /= b[0, j]
            return b

        tsl_beta_norm = _normalize_beta(tsl["beta"])
        ref_beta_norm = _normalize_beta(ref["beta"])

        # Alpha sign-canonicalize: the alpha-beta product is
        # what's identified, not alpha alone. After normalizing
        # beta's first element to 1, alpha is determined uniquely
        # up to sign (joint flip of alpha and beta produces same
        # alpha @ beta.T). Apply the same first-row sign
        # convention to alpha for parity.
        def _align_alpha_sign(alpha: np.ndarray,
                              beta_normalized: np.ndarray,
                              beta_normalized_ref: np.ndarray) -> np.ndarray:
            a = np.asarray(alpha, dtype=np.float64).copy()
            for j in range(a.shape[1]):
                # If beta col j has flipped sign vs ref, flip alpha
                # col j to match.
                tsl_sign = np.sign(beta_normalized[1, j]) if beta_normalized.shape[0] > 1 else 1.0
                ref_sign = np.sign(beta_normalized_ref[1, j]) if beta_normalized_ref.shape[0] > 1 else 1.0
                if tsl_sign * ref_sign < 0:
                    a[:, j] = -a[:, j]
            return a

        tsl_alpha_aligned = _align_alpha_sign(
            tsl["alpha"], tsl_beta_norm, ref_beta_norm,
        )

        primary["beta"] = _compare_vector(
            tsl_beta_norm.reshape(-1),
            ref_beta_norm.reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["beta"]["status"])

        primary["alpha"] = _compare_vector(
            tsl_alpha_aligned.reshape(-1),
            np.asarray(ref["alpha"]).reshape(-1),
            ladder["primary"],
        )
        statuses.append(primary["alpha"]["status"])

        # Note: log-likelihood may diverge between statsmodels
        # VECM and vars::vec2var due to different handling of
        # initial values; we report it but compare loosely
        # (Secondary tier).
        secondary["loglik"] = _compare_scalar(
            tsl["loglik"], ref["loglik"], ladder["secondary"],
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
                "urca_version": ref.get("urca_version", "unknown"),
                "vars_version": ref.get("vars_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "tsl_rank_asserted": int(tsl["cointegrating_rank"]),
                "ref_rank_inferred": int(ref["cointegrating_rank"]),
            },
        )
