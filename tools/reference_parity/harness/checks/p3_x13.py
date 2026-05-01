"""Phase 3 Batch 10 — X-13ARIMA-SEATS seasonal adjustment parity check.

TSL ``x13_seasonal_adjust.py`` (subprocess wrapper around the
US Census Bureau X-13ARIMA-SEATS binary) vs R ``seasonal``
package (also wraps the same binary). Pattern A target —
both implementations call the same binary; differences should
be limited to wrapper preprocessing.

**Phase 4 Session 2 (2026-05-01) — P4-2 pathway (c) closure:**
``run_tsl`` now invokes TSL's actual wrapper
(``engine/techniques/x13_seasonal_adjust.py:run``) via the
dispatch entry point rather than calling
``statsmodels.x13_arima_analysis`` directly. The pre-S2
implementation called statsmodels because it produced the
seasadj+trend output in a single library call; that path
fails on Linux CI because statsmodels' temp-file naming
convention is incompatible with the ``x13ashtml`` binary's
output convention (statsmodels expects ``.err`` files at a
specific prefix; ``x13ashtml`` writes elsewhere). TSL's
wrapper does direct binary invocation + .d10/.d11/.d12/.d13
parsing, which is fully x13ashtml-compatible. Linux CI now
PASSes ``p3_x13`` (was SKIP-graceful). Windows CI behavior
unchanged — the wrapper still SKIPs gracefully via
ImportError when no binary is found locally.

The ``run_reference`` path continues to invoke R
``seasonal::seas`` via RBridge unchanged (R seasonal works
correctly with x13ashtml on both platforms via the
x13binary package).
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
        # Phase 4 Session 2 (P4-2 pathway (c)): invoke TSL's
        # wrapper through the dispatch entry point. TSL's
        # ``engine/techniques/x13_seasonal_adjust.py:run`` does
        # direct x13 binary invocation and .d10/.d11/.d12/.d13
        # parsing — fully compatible with the x13ashtml binary
        # produced by the R ``x13binary`` package (used on the
        # Linux CI runner). The pre-S2 implementation called
        # ``statsmodels.x13_arima_analysis`` directly, which
        # fails on Linux due to incompatible temp-file
        # conventions vs x13ashtml's output naming.
        from techniques.base import RunContext
        from techniques.x13_seasonal_adjust import run as tsl_x13_run

        y = np.asarray(fixture["y"], dtype=np.float64)
        # Series spans 2010-01 .. 2010-01 + (DGP_N - 1) months.
        # Build the time column as ISO date strings; TSL's
        # wrapper parses this to recover ``start_year`` /
        # ``start_period``.
        from datetime import datetime
        time_col = []
        for i in range(len(y)):
            year = 2010 + (i // 12)
            month = (i % 12) + 1
            time_col.append(f"{year}-{month:02d}-01T00:00:00")

        ctx = RunContext({
            "run_id": "p3_x13_audit_tsl",
            "technique_id": "x13_seasonal_adjust",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "MS",
            "time": time_col,
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                # Force a fixed start so audit is deterministic
                # regardless of how the wrapper parses the time
                # column.
                "start_year": 2010,
                "start_period": 1,
                # Use all DGP_N=120 observations (default
                # fit_window_obs is 10*period=120 for monthly,
                # which equals N here; setting 0 disables the
                # window and uses every observation
                # unconditionally).
                "fit_window_obs": 0,
            },
        })
        res = tsl_x13_run(ctx, lambda *a, **k: None)
        # TSL's wrapper returns SKIP-equivalent via a failure
        # response when the binary cannot be located. Translate
        # to ImportError so the harness's SKIP-on-import-error
        # path catches it.
        if res.get("status") != "success":
            err_msg = res.get("error_message") or "unknown"
            if "binary not found" in err_msg.lower():
                raise ImportError(
                    f"X-13 binary not found by TSL wrapper; "
                    f"p3_x13 SKIPped: {err_msg}"
                )
            raise RuntimeError(
                f"TSL x13_seasonal_adjust failed in audit: "
                f"{err_msg}"
            )

        # Extract seasadj + trend from the X-13 Decomposition
        # table. Columns: [Time, name, Seasonally Adjusted,
        # Trend, Seasonal, Irregular].
        decomp_table = next(
            (t for t in res.get("tables", [])
             if t.get("name") == "X-13 Decomposition"),
            None,
        )
        if decomp_table is None:
            raise RuntimeError(
                "TSL x13_seasonal_adjust did not produce the "
                "expected 'X-13 Decomposition' table."
            )
        rows = decomp_table["rows"]
        seasadj = np.asarray(
            [r[2] for r in rows], dtype=np.float64,
        )
        trend = np.asarray(
            [r[3] for r in rows], dtype=np.float64,
        )
        return {
            "seasadj": seasadj,
            "trend": trend,
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
