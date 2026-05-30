"""ENG-EXT-MULTIVARIATE-001 M2 — VECM IRF + FEVD parity check.

Validates the IRF and FEVD that ``vecm_model.py`` now emits (S65 VECM
previously emitted NEITHER — the broadest gap in the commission). The
validation is the FAMILIAR Q1 point-parity cross-package mode (NOT M1's
interval pattern): an independent R Johansen fit (``urca::ca.jo`` →
``vars::vec2var``) produces VECM IRF (``vars::irf``) + FEVD (``vars::fevd``),
and the engine's orthogonalized IRF (statsmodels ``VECMResults.irf().
orth_irfs``) + net-new FEVD (``_vecm_fevd`` on ``orth_ma_rep``) are compared
to it. Formulation-correctness via the independent R reference.

The DGP reuses ``p3_vecm.py``'s bivariate cointegrated rank=1 fixture, so
the VECM FIT matches S65's already-validated fit (β/α machine-precision,
single_impl_mle) — the comparison therefore ISOLATES the IRF/FEVD
computation given a matching fit.

Tolerance shape (Pattern H DSCD nuance): the orthogonalized IRF carries a
σ-divisor sensitivity (statsmodels sigma_u uses T−k_total; R vec2var may
differ) → expected mle-band (~0.3% rel at T=500). FEVD is RATIO-invariant
to uniform σ scaling → expected near-bit-exact. Hence separate sub-metric
tolerances (irf_vs_vars mle-band; fevd_vs_vars tight; fevd_sum_to_one
structural).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_vecm_dgp(*, seed: int, n: int = 500, burn: int = 200) -> np.ndarray:
    """Bivariate cointegrated VAR with rank=1 (mirrors p3_vecm.py's DGP so
    the fit matches S65's validated fit). Cointegrating vector (1, -0.7);
    y1 - 0.7*y2 ~ I(0)."""
    rng = np.random.default_rng(seed)
    n_total = n + burn
    y2 = np.cumsum(rng.standard_normal(n_total))
    xi = rng.standard_normal(n_total) * 0.5
    y1 = 0.7 * y2 + xi
    return np.column_stack([y1, y2])[burn:]


class VecmIrfFevdParity(P3ParityCheck):
    """VECM IRF + FEVD point-parity vs R urca::ca.jo + vars::vec2var →
    vars::irf / vars::fevd (ENG-EXT-MULTIVARIATE-001 M2)."""

    technique_id = "p3_vecm_irf_fevd"
    tier = "fast"
    fixture_id = ""

    verdict_class = "single_impl_mle"
    verdict_class_rationale = (
        "VECM IRF + FEVD (ENG-EXT-MULTIVARIATE-001 M2) derive from the "
        "Johansen MLE fit (β/α validated single_impl_mle at S65). IRF is a "
        "native wrap of statsmodels VECMResults.irf().orth_irfs; FEVD is "
        "net-new (cumulative-squared-orthogonalized-MA from orth_ma_rep, "
        "orth_ma_rep == orth_irfs exactly). Cross-package vs R urca+vars "
        "(independent Johansen fit). Same classification as p3_vecm: the "
        "Johansen fit reduces to closed-form reduced-rank regression and the "
        "IRF/FEVD are closed-form matrix algebra on top — only invisible "
        "optimizer noise separates the arms. The anticipated σ-divisor (T−k) "
        "IRF sensitivity did NOT materialize: measured max_abs 5.63e-14 / "
        "max_rel 1.34e-13 on the IRF and 3.59e-14 on the FEVD (FEVD also "
        "ratio-invariant to uniform σ scaling) — MACHINE PRECISION, 9+ "
        "orders inside the single_impl_mle band (1e-5 abs / 1e-4 rel)."
    )

    DGP_N = 500
    DGP_K = 2
    K_AR_DIFF = 1
    COINT_RANK = 1
    IRF_PERIODS = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _generate_vecm_dgp(seed=seed, n=self.DGP_N)}

    # ---------------------------------------------------------------- TSL
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.vector_ar.vecm import VECM  # type: ignore
        from techniques.vecm_model import _vecm_fevd  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        H = self.IRF_PERIODS
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = VECM(Y, k_ar_diff=self.K_AR_DIFF,
                       coint_rank=self.COINT_RANK, deterministic="ci").fit()
            orth_irfs = np.asarray(fit.irf(H).orth_irfs, dtype=np.float64)  # (H+1,k,k)
            orth_ma = np.asarray(fit.orth_ma_rep(maxn=H), dtype=np.float64)
            fevd = _vecm_fevd(orth_ma, H)  # (H,k,k) [h, var, shock], fractions
        return {"irf": orth_irfs, "fevd": fevd}

    # ---------------------------------------------------------- Reference
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        Y = np.asarray(fixture["Y"], dtype=np.float64)
        H = self.IRF_PERIODS
        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca); library(vars) }})
            Y <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))
            k <- ncol(Y); H <- {H}
            jt <- ca.jo(Y, K = {self.K_AR_DIFF} + 1, ecdet = "const",
                        spec = "longrun")
            vmod <- vec2var(jt, r = {self.COINT_RANK})

            # Orthogonalized point IRF. ir$irf is a list by impulse variable;
            # each element an (H+1) x k matrix [horizon 0..H, response].
            ir <- vars::irf(vmod, n.ahead = H, ortho = TRUE, boot = FALSE)
            irf_arr <- array(0, dim = c(H + 1, k, k))   # [h, resp, imp]
            for (imp in 1:k) {{ irf_arr[, , imp] <- as.matrix(ir$irf[[imp]]) }}

            # FEVD. fv is a list by RESPONSE variable; each element an H x k
            # matrix [horizon 1..H, shock] of variance shares.
            fv <- vars::fevd(vmod, n.ahead = H)
            fevd_arr <- array(0, dim = c(H, k, k))      # [h (=m-1), var, shock]
            for (vv in 1:k) {{ fevd_arr[, vv, ] <- as.matrix(fv[[vv]]) }}

            write.table(matrix(as.numeric(irf_arr), ncol = 1),
                        "{{{{OUTPUT_irf}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(fevd_arr), ncol = 1),
                        "{{{{OUTPUT_fevd}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y},
            output_names=["irf", "fevd"],
            timeout_sec=120,
            capture_versions_for=["urca", "vars"],
        )
        k = self.DGP_K
        r_irf = np.atleast_1d(outputs["irf"]).astype(np.float64).reshape(
            (H + 1, k, k), order="F")
        r_fevd = np.atleast_1d(outputs["fevd"]).astype(np.float64).reshape(
            (H, k, k), order="F")
        return {
            "irf": r_irf,
            "fevd": r_fevd,
            "urca_version": versions.get("urca", "unknown"),
            "vars_version": versions.get("vars", "unknown"),
        }

    # ------------------------------------------------------------ Compare
    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        tsl_irf = np.asarray(tsl["irf"], dtype=np.float64)
        ref_irf = np.asarray(ref["irf"], dtype=np.float64)
        primary["irf_vs_vars"] = _compare_vector(
            tsl_irf.reshape(-1), ref_irf.reshape(-1), ladder["irf_vs_vars"],
        )
        statuses.append(primary["irf_vs_vars"]["status"])

        tsl_fevd = np.asarray(tsl["fevd"], dtype=np.float64)
        ref_fevd = np.asarray(ref["fevd"], dtype=np.float64)
        primary["fevd_vs_vars"] = _compare_vector(
            tsl_fevd.reshape(-1), ref_fevd.reshape(-1), ladder["fevd_vs_vars"],
        )
        statuses.append(primary["fevd_vs_vars"]["status"])

        # FEVD row-sum-to-one structural invariant (both arms).
        sum_tol = float(ladder["fevd_sum_to_one"]["abs_tol"])
        tsl_dev = float(np.max(np.abs(tsl_fevd.sum(axis=2) - 1.0)))
        ref_dev = float(np.max(np.abs(ref_fevd.sum(axis=2) - 1.0)))
        sum_ok = (tsl_dev <= sum_tol) and (ref_dev <= sum_tol)
        primary["fevd_sum_to_one"] = {
            "status": "PASS" if sum_ok else "BLOCK",
            "tsl_max_dev": tsl_dev,
            "ref_max_dev": ref_dev,
        }
        statuses.append(primary["fevd_sum_to_one"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "urca_version": ref.get("urca_version", "unknown"),
                "vars_version": ref.get("vars_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_vars": int(self.DGP_K),
                "irf_periods": int(self.IRF_PERIODS),
                "irf_max_abs": primary["irf_vs_vars"].get("max_abs_diff"),
                "irf_max_rel": primary["irf_vs_vars"].get("max_rel_diff"),
                "fevd_max_abs": primary["fevd_vs_vars"].get("max_abs_diff"),
            },
        )
