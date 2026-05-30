"""ENG-EXT-MULTIVARIATE-001 M3a — Blanchard–Quah SVAR parity check.

Validates the engine's net-new Blanchard–Quah (1989) long-run-restriction
SVAR identification (`var_model._blanchard_quah_b0` + structural IRF)
against R `vars::BQ`. statsmodels SVAR is A/B/AB short-run only, so BQ is
net-new; R `vars::BQ` is the independent cross-package reference (pinned
vars 1.6.1). Point-identified (long-run restrictions uniquely pin the
shocks — no set, no rotation sampling) → the familiar Q1 point-parity mode
(M2-like; formulation-correctness via the independent R fit). This is the
FIRST M3 sub-build — it establishes the SVAR-identification build pattern
(a scheme selector + structural outputs) that M3c (proxy) + M3b
(sign-restriction) reuse.

The DGP reuses p3_var.py's bivariate VAR(2) fixture, so the VAR fit matches
S64's already-validated fit (closed_form, machine precision) — the
comparison ISOLATES the BQ identification. The probe pre-verified bit-for-bit
agreement (engine B0 == R `$B`, engine C1·B0 == R `$LRIM`, sign convention
matches) → machine-precision closed_form.
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


def _generate_var_dgp(*, seed: int, n: int = 500, burn: int = 200) -> np.ndarray:
    """Stationary bivariate VAR(2) (mirrors p3_var.py's DGP so the fit
    matches S64's validated fit)."""
    rng = np.random.default_rng(seed)
    A1 = np.array([[0.5, 0.1], [0.0, 0.4]])
    A2 = np.array([[0.1, 0.0], [0.05, 0.2]])
    n_total = n + burn
    Y = np.zeros((n_total, 2))
    eps = rng.standard_normal((n_total, 2))
    for t in range(2, n_total):
        Y[t] = A1 @ Y[t - 1] + A2 @ Y[t - 2] + eps[t]
    return Y[burn:]


class VarBlanchardQuahParity(P3ParityCheck):
    """Blanchard–Quah SVAR identification point-parity vs R vars::BQ
    (ENG-EXT-MULTIVARIATE-001 M3a)."""

    technique_id = "p3_var_bq"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Blanchard–Quah identification (ENG-EXT-MULTIVARIATE-001 M3a) is "
        "closed-form matrix algebra on the VAR OLS fit: "
        "B0 = C(1)^-1 chol(C(1) Σ C(1)^T), structural IRF = ma_rep @ B0. "
        "VAR estimation is closed-form OLS (cf. p3_var closed_form), so the "
        "whole pipeline is closed-form. R vars::BQ implements the identical "
        "algorithm; the probe pre-verified bit-for-bit agreement (engine B0 "
        "== R $B, engine C1·B0 == R $LRIM; sign convention matches — "
        "positive-diagonal long-run Cholesky). Machine precision expected."
    )

    DGP_N = 500
    DGP_K = 2
    P_FIT = 2
    STEPS = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _generate_var_dgp(seed=seed, n=self.DGP_N)}

    # ---------------------------------------------------------------- TSL
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.api import VAR  # type: ignore
        from techniques.var_model import _blanchard_quah_b0  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = VAR(Y).fit(self.P_FIT, trend="c")
            B0, lrim = _blanchard_quah_b0(fit)
            Phi = np.asarray(fit.ma_rep(maxn=self.STEPS), dtype=np.float64)
            Theta = np.einsum("hrs,sc->hrc", Phi, B0)  # (STEPS+1, k, k)
        return {"B0": np.asarray(B0), "lrim": np.asarray(lrim), "sirf": Theta}

    # ---------------------------------------------------------- Reference
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        Y = np.asarray(fixture["Y"], dtype=np.float64)
        H = self.STEPS
        r_code = rf"""
            suppressPackageStartupMessages({{ library(vars) }})
            Y <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))
            k <- ncol(Y); H <- {H}
            v <- VAR(Y, p = {self.P_FIT}, type = "const")
            bq <- BQ(v)
            # Structural IRF: irf on the SVAR (BQ) object. ir$irf is a list by
            # impulse (structural shock); each (H+1) x k matrix [horizon, resp].
            ir <- vars::irf(bq, n.ahead = H, boot = FALSE)
            sirf <- array(0, dim = c(H + 1, k, k))   # [h, resp, shock]
            for (sh in 1:k) {{ sirf[, , sh] <- as.matrix(ir$irf[[sh]]) }}
            write.table(bq$B, "{{{{OUTPUT_B}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
            write.table(bq$LRIM, "{{{{OUTPUT_LRIM}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(sirf), ncol = 1),
                        "{{{{OUTPUT_sirf}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y},
            output_names=["B", "LRIM", "sirf"],
            timeout_sec=120,
            capture_versions_for=["vars"],
        )
        k = self.DGP_K
        r_B0 = np.atleast_1d(outputs["B"]).astype(np.float64).reshape((k, k), order="F")
        r_lrim = np.atleast_1d(outputs["LRIM"]).astype(np.float64).reshape((k, k), order="F")
        r_sirf = np.atleast_1d(outputs["sirf"]).astype(np.float64).reshape(
            (H + 1, k, k), order="F")
        return {
            "B0": r_B0, "lrim": r_lrim, "sirf": r_sirf,
            "vars_version": versions.get("vars", "unknown"),
        }

    # ------------------------------------------------------------ Compare
    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        k = self.DGP_K

        tsl_B0 = np.asarray(tsl["B0"], dtype=np.float64).copy()
        tsl_lrim = np.asarray(tsl["lrim"], dtype=np.float64).copy()
        tsl_sirf = np.asarray(tsl["sirf"], dtype=np.float64).copy()
        ref_B0 = np.asarray(ref["B0"], dtype=np.float64)
        ref_lrim = np.asarray(ref["lrim"], dtype=np.float64)
        ref_sirf = np.asarray(ref["sirf"], dtype=np.float64)

        # Defensive per-shock-column sign alignment: a structural shock is
        # identified only up to sign; flip an engine column whose sign opposes
        # R's (verified unnecessary on this DGP, guards other fixtures).
        for j in range(k):
            if float(tsl_B0[:, j] @ ref_B0[:, j]) < 0:
                tsl_B0[:, j] = -tsl_B0[:, j]
                tsl_lrim[:, j] = -tsl_lrim[:, j]
                tsl_sirf[:, :, j] = -tsl_sirf[:, :, j]

        primary: dict[str, Any] = {}
        statuses: list[str] = []
        primary["b0_vs_vars"] = _compare_vector(
            tsl_B0.reshape(-1), ref_B0.reshape(-1), ladder["b0_vs_vars"])
        primary["lrim_vs_vars"] = _compare_vector(
            tsl_lrim.reshape(-1), ref_lrim.reshape(-1), ladder["lrim_vs_vars"])
        primary["struct_irf_vs_vars"] = _compare_vector(
            tsl_sirf.reshape(-1), ref_sirf.reshape(-1), ladder["struct_irf_vs_vars"])
        for key in ("b0_vs_vars", "lrim_vs_vars", "struct_irf_vs_vars"):
            statuses.append(primary[key]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "vars_version": ref.get("vars_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_vars": int(self.DGP_K),
                "steps": int(self.STEPS),
                "b0_max_abs": primary["b0_vs_vars"].get("max_abs_diff"),
                "lrim_max_abs": primary["lrim_vs_vars"].get("max_abs_diff"),
                "sirf_max_abs": primary["struct_irf_vs_vars"].get("max_abs_diff"),
            },
        )
