"""Phase 3 Batch 10 — X-13ARIMA-SEATS seasonal adjustment parity check.

TSL ``x13_seasonal_adjust.py`` (subprocess wrapper around the
US Census Bureau X-13ARIMA-SEATS binary) vs R ``seasonal``
package (also wraps the same binary). Pattern A target —
both implementations call the same binary; differences should
be limited to wrapper preprocessing.

**Tier C / SKIP-graceful:** the R `seasonal` package requires
the X-13 binary on the host system (non-trivial to install on
Windows; failed install during Session 14 deps verification).
When the package is missing, the harness translates the
RPackageMissingError to a SKIP outcome — informative-not-
failing. Both CI and local invocations handle this cleanly.

Master plan §15.12 deferred this from Session 1 inventory due
to install difficulty; **the check is built but expected to
SKIP** in most environments.
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


def _generate_seasonal_dgp(*, seed: int, n: int = 120,
                            period: int = 12) -> np.ndarray:
    """Monthly trend + seasonal + noise (typical X-13 input)."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    trend = 100 + 0.5 * t
    seasonal = 5 * np.sin(2 * np.pi * t / period)
    return trend + seasonal + 2 * rng.standard_normal(n)


class X13Parity(P3ParityCheck):
    technique_id = "p3_x13"
    tier = "slow"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "X-13ARIMA-SEATS binary called by both TSL and R "
        "seasonal package; output is deterministic given "
        "identical input + identical x13 spec. Tier C / "
        "SKIP-graceful when the X-13 binary is unavailable."
    )
    DGP_N = 120
    PERIOD = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_seasonal_dgp(
            seed=seed, n=self.DGP_N, period=self.PERIOD,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # statsmodels.tsa.x13 wraps the X-13 binary. When the
        # binary is missing on the host, statsmodels raises
        # X13NotFoundError. Re-raise as ImportError so the
        # harness's SKIP-on-import-error path catches it
        # cleanly (the runner's run_check already wraps
        # ImportError → SKIP for run_reference; we want the
        # same semantics for run_tsl in this binary-dependent
        # case).
        from statsmodels.tsa.x13 import x13_arima_analysis  # type: ignore
        from statsmodels.tools.sm_exceptions import X13NotFoundError  # type: ignore
        import pandas as pd  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        idx = pd.date_range("2010-01-01", periods=len(y), freq="MS")
        s = pd.Series(y, index=idx)
        try:
            res = x13_arima_analysis(s, x12path=None)
        except X13NotFoundError as e:
            raise ImportError(
                f"X-13 binary not found on system PATH; "
                f"p3_x13 SKIPped: {e}"
            ) from e
        return {
            "seasadj": np.asarray(res.seasadj.values, dtype=np.float64),
            "trend": np.asarray(res.trend.values, dtype=np.float64),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Will raise RPackageMissingError (→ SKIP) if seasonal
        # package isn't installed (typical Windows scenario).
        r_code = rf"""
            suppressPackageStartupMessages({{ library(seasonal) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            y_ts <- ts(y, start = c(2010, 1), frequency = {self.PERIOD})
            res <- seas(y_ts)
            seasadj <- as.numeric(final(res))
            trend <- as.numeric(trend(res))
            write.table(matrix(seasadj, ncol=1), "{{{{OUTPUT_seasadj}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(trend, ncol=1), "{{{{OUTPUT_trend}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"y": y.reshape(-1, 1)},
            output_names=["seasadj", "trend"], timeout_sec=120,
            capture_versions_for=["seasonal"],
        )
        return {
            "seasadj": np.asarray(outputs["seasadj"], dtype=np.float64).reshape(-1),
            "trend": np.asarray(outputs["trend"], dtype=np.float64).reshape(-1),
            "seasonal_version": versions.get("seasonal", "unknown"),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        n_common = min(len(tsl["seasadj"]), len(ref["seasadj"]))
        primary = {
            "seasadj": _compare_vector(
                tsl["seasadj"][:n_common], ref["seasadj"][:n_common],
                ladder["primary"],
            ),
            "trend": _compare_vector(
                tsl["trend"][:n_common], ref["trend"][:n_common],
                ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "period": int(self.PERIOD),
                "seasonal_version": ref.get("seasonal_version", "unknown"),
            },
        )
