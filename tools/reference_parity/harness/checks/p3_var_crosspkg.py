"""Phase 7+ — var ENGINE-INVOKED cross-package (the engine-invocation upgrade).

★ The existing `p3_var` invokes **statsmodels VAR directly** ("bypass TSL
wrapper") and compares vs R `vars::VAR`. For exact-OLS VAR coefficients
statsmodels ≡ R vars is STRUCTURALLY TAUTOLOGICAL (same-estimator-class), and
the ENGINE (`var_model.py`) is never in the loop — so the published `var`
surface is unvalidated by it.

This check closes the engine-invocation gap: it invokes the ENGINE via
RunContext (the same path the published numbers go through) and compares the
engine's EMITTED VAR coefficients + forecast vs R `vars::VAR` at matched params
(lag=2, trend=const).

★ TIER (honest, modest): "cross-package OLS, engine-WRAPPER-validated". This
validates the engine's wrapper plumbing — lag handling, trend, coefficient
extraction, output emission — reproduces the VAR and agrees with an independent
package (R vars). It does NOT newly validate the ESTIMATOR: OLS-on-stacked-
equations is closed-form, so statsmodels/engine and R vars agree by
construction. Real value = catches wrapper/lag/trend/extraction bugs in the
engine path. `p3_var` stays byte-identical.
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
from reference_parity.harness.checks.p3_var import _generate_var_dgp

_ROUND = 6  # engine B8 output-rounding floor (6 decimals)


class VarCrossPkgParity(P3ParityCheck):
    """Engine-invoked standalone VAR vs R vars::VAR (wrapper-validated)."""

    technique_id = "p3_var_crosspkg"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "VAR(p) is OLS-on-stacked-equations (closed-form); the engine wraps "
        "statsmodels VAR and R vars::VAR is an independent package. ENGINE-"
        "INVOKED (RunContext) — validates the engine wrapper (lag/trend/"
        "extraction/emission) reproduces the VAR and agrees with R vars at "
        "matched params. Modest tier: cross-package OLS, engine-WRAPPER-"
        "validated — the estimator agreement is structural (closed-form OLS), "
        "the new evidence is that the engine PATH (not statsmodels-direct) is "
        "correct. Distinct from the bond_yield BVAR work (that validated the "
        "SV-marginal conjugate machinery; this is the standalone user-data VAR)."
    )

    DGP_K = 2
    DGP_P = 2
    DGP_N = 500
    HORIZON = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _generate_var_dgp(seed=seed, n=self.DGP_N, k=self.DGP_K, p=self.DGP_P),
                "p": self.DGP_P, "horizon": self.HORIZON}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """ENGINE-INVOKED via RunContext (the published path), NOT statsmodels-
        direct. Extract coefficients + forecast from the emitted tables."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.var_model as vm  # type: ignore

        Y = np.asarray(fixture["Y"], float)
        p = int(fixture["p"]); horizon = int(fixture["horizon"])
        ctx = RunContext({
            "run_id": "p3_var_crosspkg", "technique_id": "var",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(Y))),
            "series": [{"name": "y1", "values": Y[:, 0].tolist()},
                       {"name": "y2", "values": Y[:, 1].tolist()}],
            # Pin lag + trend to match R VAR(p=2, type="const").
            "params": {"lag": p, "trend": "c", "horizon": horizon},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            resp = vm.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine var failed: {resp.get('error_message')}")
        au = resp.get("audit_fields", {})
        names = list(au.get("variable_names", ["y1", "y2"]))
        k = len(names)
        tbls = {t.get("name"): t for t in resp["tables"]}

        # Coefficients table -> coefs[(p,k,k)] (statsmodels order [lag,eq,var]) + intercept.
        coefs = np.zeros((p, k, k)); intercept = np.zeros(k)
        for row in tbls["Coefficients"]["rows"]:
            eq, param, est = str(row[0]), str(row[1]), float(row[2])
            e = names.index(eq)
            if param == "const":
                intercept[e] = est
            else:
                lagstr, var = param.split(".")
                coefs[int(lagstr[1:]) - 1, e, names.index(var)] = est

        # VAR Forecast table -> forecast[(horizon,k)] (cols: Step, y1, y2).
        fc_rows = tbls["VAR Forecast"]["rows"]
        forecast = np.array([[float(r[1 + j]) for j in range(k)] for r in fc_rows], float)

        return {"coefs": coefs, "intercept": intercept, "forecast": forecast,
                "var_order": int(au.get("var_order", p)),
                "aic": float(au.get("aic", np.nan)), "bic": float(au.get("bic", np.nan))}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """R vars::VAR at matched params (reuses the p3_var reference algebra)."""
        bridge = RBridge(Manifest.load())
        Y = np.asarray(fixture["Y"], float)
        p = int(fixture["p"]); horizon = int(fixture["horizon"])
        r_code = rf"""
            suppressPackageStartupMessages({{ library(vars) }})
            Y_raw <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))
            fit <- VAR(Y_raw, p = {p}, type = "const")
            k <- ncol(Y_raw)
            coefs_per_eq <- sapply(seq_len(k), function(i) coef(fit$varresult[[i]]))
            ar_block <- coefs_per_eq[1:(k * {p}), , drop = FALSE]
            coefs_array <- array(0, dim = c({p}, k, k))
            for (j in 1:{p}) {{
                lag_block <- ar_block[((j - 1) * k + 1):(j * k), , drop = FALSE]
                coefs_array[j, , ] <- t(lag_block)
            }}
            intercept <- coefs_per_eq[k * {p} + 1, ]
            fc <- predict(fit, n.ahead = {horizon})
            fc_mat <- sapply(seq_len(k), function(i) fc$fcst[[i]][, "fcst"])
            write.table(matrix(as.numeric(coefs_array), ncol=1), "{{{{OUTPUT_coefs}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(intercept), ncol=1), "{{{{OUTPUT_intercept}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(fc_mat), ncol=1), "{{{{OUTPUT_forecast}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"Y": Y},
            output_names=["coefs", "intercept", "forecast"],
            timeout_sec=60, capture_versions_for=["vars"])
        k = Y.shape[1]
        coefs = np.atleast_1d(outputs["coefs"]).astype(float).reshape((p, k, k), order="F")
        forecast = np.atleast_1d(outputs["forecast"]).astype(float).reshape((horizon, k), order="F")
        return {"coefs": coefs,
                "intercept": np.atleast_1d(outputs["intercept"]).astype(float).reshape(-1),
                "forecast": forecast, "vars_version": versions.get("vars", "unknown")}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine emits 6-dp rounded values (B8 floor); round R to match.
        r_coefs = np.round(ref["coefs"], _ROUND)
        r_int = np.round(ref["intercept"], _ROUND)
        r_fc = np.round(ref["forecast"], _ROUND)
        primary: dict[str, Any] = {}; statuses: list[str] = []
        primary["coefs"] = _compare_vector(np.asarray(tsl["coefs"]).reshape(-1),
                                           r_coefs.reshape(-1), ladder["primary"])
        primary["intercept"] = _compare_vector(np.asarray(tsl["intercept"]).reshape(-1),
                                               r_int.reshape(-1), ladder["primary"])
        primary["forecast"] = _compare_vector(np.asarray(tsl["forecast"]).reshape(-1),
                                              r_fc.reshape(-1), ladder["primary"])
        for kk in ("coefs", "intercept", "forecast"):
            statuses.append(primary[kk]["status"])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "reference": "R vars::VAR (engine-invoked; wrapper-validated, NOT statsmodels-direct)",
                "vars_version": ref.get("vars_version"),
                "engine_invoked": True, "var_order_engine": tsl["var_order"],
                "tier_note": ("cross-package OLS, engine-WRAPPER-validated — estimator "
                              "agreement is structural (closed-form OLS); the new evidence "
                              "is the engine PATH (lag/trend/extraction) is correct"),
                "coefs_max_abs_diff": primary["coefs"].get("max_abs_diff"),
                "forecast_max_abs_diff": primary["forecast"].get("max_abs_diff"),
            },
        )
