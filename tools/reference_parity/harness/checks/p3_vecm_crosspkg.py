"""Phase 7+ — vecm ENGINE-INVOKED cross-package (the GENUINE one of the three).

★ The existing `p3_vecm` invokes statsmodels VECM directly (engine bypassed)
and compares vs R `urca::ca.jo`+`cajorls`. Unlike var (exact-OLS, tautological),
VECM Johansen is a generalized-eigenvalue problem: statsmodels VECM and R urca
are INDEPENDENT Johansen implementations, so the cointegration RANK + the
β (cointegrating vectors) / α (loadings) comparison is NON-tautological — a
genuine cross-package validation.

This check closes the engine-invocation gap: it invokes the ENGINE via
RunContext (`vecm_model.py`, which emits Phillips-normalized β/α + the audit
`coint_rank`) and compares vs R urca/vars at matched params:
  - cointegration RANK = 1 (exact integer match),
  - deterministic term: engine `deterministic="ci"` ↔ R `ecdet="const"`,
  - β NORMALIZATION: both Phillips/first-element=1 (so the comparison isolates
    the estimate, not the normalization).

Genuine cross-package tier (the strongest of the three FUND-NOW arms).
`p3_vecm` stays byte-identical.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_vecm import _generate_vecm_dgp


def _normalize_beta(b: np.ndarray) -> np.ndarray:
    """First-element=1 normalization (matches the engine's Phillips pivot for
    the standard fixture where pivot index 0 is the first nonzero)."""
    b = np.asarray(b, float).copy()
    for j in range(b.shape[1]):
        if abs(b[0, j]) > 1e-12:
            b[:, j] /= b[0, j]
    return b


def _align_alpha_sign(alpha, beta_norm, beta_norm_ref):
    a = np.asarray(alpha, float).copy()
    for j in range(a.shape[1]):
        tsl_sign = np.sign(beta_norm[1, j]) if beta_norm.shape[0] > 1 else 1.0
        ref_sign = np.sign(beta_norm_ref[1, j]) if beta_norm_ref.shape[0] > 1 else 1.0
        if tsl_sign * ref_sign < 0:
            a[:, j] = -a[:, j]
    return a


class VecmCrossPkgParity(P3ParityCheck):
    """Engine-invoked VECM vs R urca::ca.jo + vars (genuine cross-package:
    independent Johansen, rank + Phillips-normalized beta/alpha)."""

    technique_id = "p3_vecm_crosspkg"
    tier = "fast"
    fixture_id = ""

    verdict_class = "single_impl_mle"
    verdict_class_rationale = (
        "VECM Johansen reduces to a generalized-eigenvalue / reduced-rank "
        "regression. statsmodels VECM (engine wrapper) and R urca::ca.jo are "
        "INDEPENDENT implementations -> the rank + Phillips-normalized beta/"
        "alpha comparison is genuinely cross-package (non-tautological, unlike "
        "exact-OLS var). ENGINE-INVOKED (RunContext) at matched rank=1, "
        "deterministic ci<->ecdet=const, first-element beta normalization. The "
        "genuine cross-package upgrade of the three FUND-NOW arms."
    )

    DGP_N = 500
    K_AR_DIFF = 1
    COINT_RANK = 1

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _generate_vecm_dgp(seed=seed),
                "k_ar_diff": self.K_AR_DIFF, "coint_rank": self.COINT_RANK}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """ENGINE-INVOKED via RunContext (the published path), NOT statsmodels-
        direct. Extract Phillips-normalized beta/alpha + rank from audit."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.vecm_model as vm  # type: ignore

        Y = np.asarray(fixture["Y"], float)
        ctx = RunContext({
            "run_id": "p3_vecm_crosspkg", "technique_id": "vecm",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(Y))),
            "series": [{"name": "y1", "values": Y[:, 0].tolist()},
                       {"name": "y2", "values": Y[:, 1].tolist()}],
            "params": {"coint_rank": int(fixture["coint_rank"]),
                       "deterministic": "ci", "lag": int(fixture["k_ar_diff"])},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            resp = vm.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine vecm failed: {resp.get('error_message')}")
        au = resp.get("audit_fields", {})
        beta = np.asarray(au["beta_normalized"], float)    # (k, r), Phillips
        alpha = np.asarray(au["alpha_normalized"], float)  # (k, r)
        return {"beta": beta, "alpha": alpha,
                "cointegrating_rank": int(au.get("coint_rank", fixture["coint_rank"]))}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """R urca::ca.jo + cajorls (reuses the p3_vecm reference algebra)."""
        bridge = RBridge(Manifest.load())
        Y = np.asarray(fixture["Y"], float)
        k_ar_diff = int(fixture["k_ar_diff"]); coint_rank = int(fixture["coint_rank"])
        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca); library(vars) }})
            Y <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))
            jt <- ca.jo(Y, K = {k_ar_diff} + 1, ecdet = "const", spec = "longrun")
            trace_stats <- jt@teststat
            cvals_5pct <- jt@cval[, "5pct"]
            r_inferred <- 0
            for (i in seq_along(trace_stats)) {{
                if (trace_stats[i] > cvals_5pct[i]) {{
                    r_inferred <- length(trace_stats) - i + 1
                    break
                }}
            }}
            cajo_rls <- cajorls(jt, r = {coint_rank})
            alpha <- as.matrix(cajo_rls$rlm$coefficients[1:{coint_rank}, , drop = FALSE])
            k <- ncol(Y)
            beta <- jt@V[1:k, 1:{coint_rank}, drop = FALSE]
            scalars <- c(rank = r_inferred)
            write.table(matrix(as.numeric(alpha), ncol=1), "{{{{OUTPUT_alpha}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(beta), ncol=1), "{{{{OUTPUT_beta}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"Y": Y},
            output_names=["alpha", "beta", "scalars"],
            timeout_sec=60, capture_versions_for=["urca", "vars"])
        k = Y.shape[1]
        alpha = np.atleast_1d(outputs["alpha"]).astype(float).reshape((coint_rank, k), order="F").T
        beta = np.atleast_1d(outputs["beta"]).astype(float).reshape((k, coint_rank), order="F")
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {"alpha": alpha, "beta": beta, "cointegrating_rank": int(sc[0]),
                "urca_version": versions.get("urca", "unknown"),
                "vars_version": versions.get("vars", "unknown")}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}; statuses: list[str] = []

        # Rank match (exact integer) — the structural invariant.
        rank_ok = int(tsl["cointegrating_rank"]) == int(ref["cointegrating_rank"])
        primary["cointegration_rank"] = {
            "status": "PASS" if rank_ok else "BLOCK",
            "engine": int(tsl["cointegrating_rank"]), "r_inferred": int(ref["cointegrating_rank"])}
        statuses.append(primary["cointegration_rank"]["status"])

        # Beta (Phillips/first-element=1) + alpha (sign-aligned) cross-package.
        tsl_beta = _normalize_beta(tsl["beta"])
        ref_beta = _normalize_beta(ref["beta"])
        tsl_alpha = _align_alpha_sign(tsl["alpha"], tsl_beta, ref_beta)
        primary["beta"] = _compare_vector(tsl_beta.reshape(-1), ref_beta.reshape(-1), ladder["primary"])
        primary["alpha"] = _compare_vector(np.asarray(tsl_alpha).reshape(-1),
                                           np.asarray(ref["alpha"]).reshape(-1), ladder["primary"])
        statuses.append(primary["beta"]["status"])
        statuses.append(primary["alpha"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "reference": ("R urca::ca.jo + cajorls (engine-invoked; independent "
                              "Johansen, genuine cross-package — NOT statsmodels-direct)"),
                "urca_version": ref.get("urca_version"), "vars_version": ref.get("vars_version"),
                "engine_invoked": True,
                "rank_engine": int(tsl["cointegrating_rank"]),
                "rank_ref": int(ref["cointegrating_rank"]),
                "beta_max_abs_diff": primary["beta"].get("max_abs_diff"),
                "alpha_max_abs_diff": primary["alpha"].get("max_abs_diff"),
            },
        )
