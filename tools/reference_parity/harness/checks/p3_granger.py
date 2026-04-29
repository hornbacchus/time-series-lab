"""Phase 3 Batch 10 — Granger causality parity check.

TSL ``granger_causality.py`` (statsmodels.tsa.stattools.
grangercausalitytests) vs R ``lmtest::grangertest``.
Closed-form F-test on nested OLS regressions; Pattern A
bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_granger_dgp(*, seed: int, n: int = 200,
                          phi: float = 0.5, beta: float = 0.4) -> tuple[np.ndarray, np.ndarray]:
    """X granger-causes Y: Y_t = phi*Y_{t-1} + beta*X_{t-1} + eps."""
    rng = np.random.default_rng(seed)
    x = np.zeros(n + 50)
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        x[t] = 0.7 * x[t - 1] + rng.standard_normal()
        y[t] = phi * y[t - 1] + beta * x[t - 1] + rng.standard_normal()
    return x[50:], y[50:]


class GrangerParity(P3ParityCheck):
    technique_id = "p3_granger"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Granger F-test is closed-form: nested OLS, sum-of-"
        "squares ratio, F-distribution. statsmodels and R "
        "lmtest::grangertest implement the identical procedure."
    )
    DGP_N = 200
    LAG = 2

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_granger_dgp(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.stattools import grangercausalitytests  # type: ignore
        import warnings as _w
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # statsmodels expects (T, 2) with target in col 0,
        # potential cause in col 1
        data = np.column_stack([y, x])
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            res = grangercausalitytests(
                data, maxlag=self.LAG, verbose=False,
            )
        # ssr_ftest: (F, p, df_diff, df_resid)
        f_stat, p_val, _, _ = res[self.LAG][0]["ssr_ftest"]
        return {"f_stat": float(f_stat), "p_value": float(p_val)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        combined = np.column_stack([y, x])
        r_code = rf"""
            suppressPackageStartupMessages({{ library(lmtest) }})
            data <- read.csv("{{{{INPUT_data}}}}", header=FALSE)
            y <- data[, 1]
            x <- data[, 2]
            res <- grangertest(y ~ x, order = {self.LAG})
            f_stat <- res[2, "F"]
            p_val <- res[2, "Pr(>F)"]
            scalars <- c(f_stat=f_stat, p_value=p_val)
            write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"data": combined},
            output_names=["scalars"], timeout_sec=60,
            capture_versions_for=["lmtest"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "f_stat": float(sc[0]), "p_value": float(sc[1]),
            "lmtest_version": versions.get("lmtest", "unknown"),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "f_stat": _compare_scalar(tsl["f_stat"], ref["f_stat"], ladder["primary"]),
            "p_value": _compare_scalar(tsl["p_value"], ref["p_value"], ladder["primary"]),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "lag": int(self.LAG),
                "lmtest_version": ref.get("lmtest_version", "unknown"),
            },
        )
