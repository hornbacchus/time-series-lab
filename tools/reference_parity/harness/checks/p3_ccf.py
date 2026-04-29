"""Phase 3 Batch 10 — CCF (cross-correlation) parity check.

TSL ``prewhitened_ccf_lag.py`` (statsmodels.ccf) vs R
``stats::ccf``. Closed-form Pearson correlation across lags;
Pattern A bit-exact target on lag-zero correlation and the
peak-correlation lag.
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


def _generate_lagged_pair_dgp(*, seed: int, n: int = 200,
                               lag: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Y leads X by `lag` positions."""
    rng = np.random.default_rng(seed)
    base = np.cumsum(rng.standard_normal(n + lag))
    x = base[lag:lag + n] + 0.1 * rng.standard_normal(n)
    y = base[:n] + 0.1 * rng.standard_normal(n)
    return x, y


class CcfParity(P3ParityCheck):
    technique_id = "p3_ccf"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "CCF is closed-form Pearson cross-correlation across "
        "lags. statsmodels.ccf and R stats::ccf compute "
        "identical normalized cross-covariance values."
    )
    DGP_N = 200
    MAX_LAG = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_lagged_pair_dgp(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.stattools import ccf as sm_ccf  # type: ignore
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # statsmodels.ccf returns positive lags only;
        # ccf(x, y)[k] = corr(x[t], y[t-k]) (i.e., y leads x by k)
        ccf_vals = sm_ccf(x, y, adjusted=False)[:self.MAX_LAG + 1]
        return {"ccf_positive": np.asarray(ccf_vals, dtype=np.float64)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        combined = np.column_stack([x, y])
        # R stats::ccf returns symmetric lags; we want ccf at
        # positive lags 0..MAX_LAG (corresponding to y leading x).
        # R ccf(x, y) returns acf$acf with lags from
        # -(N-1)/2..(N-1)/2; positive index k means
        # cor(x[t+k], y[t]) in R's convention. To match
        # statsmodels semantics exactly, we extract the
        # NEGATIVE-lag side of R's output (since
        # statsmodels.ccf(x,y)[k] = cor(x[t], y[t-k]) =
        # cor(x[t+k], y[t]) <=> R lag -k).
        r_code = rf"""
            data <- read.csv("{{{{INPUT_data}}}}", header=FALSE)
            x <- data[, 1]
            y <- data[, 2]
            res <- ccf(x, y, lag.max = {self.MAX_LAG}, plot = FALSE,
                       type = "correlation")
            # acf vector is symmetric around 0; lag at index
            # res$lag == 0 is in the middle. Extract lags 0..MAX_LAG.
            lags <- as.numeric(res$lag)
            vals <- as.numeric(res$acf)
            # R's ccf(x,y) at lag k is cor(x_{{t+k}}, y_t).
            # statsmodels.ccf(x,y)[k] is cor(x_t, y_{{t-k}}) =
            # cor(x_{{t+k}}, y_t) where k>=0 in statsmodels means
            # y leads x. So statsmodels[k] == R at lag -k (R's
            # negative side).
            # statsmodels.ccf(x, y)[k] = E[x[t+k] * y[t]] /
            # (sqrt(var(x)*var(y)). R ccf(x, y) at lag k is the
            # SAME quantity (R uses positive-lag = x leads y);
            # extract POSITIVE side of R's output.
            wanted <- numeric(length = {self.MAX_LAG} + 1)
            for (k in 0:{self.MAX_LAG}) {{
                idx <- which(abs(lags - k) < 1e-9)
                if (length(idx) > 0) {{
                    wanted[k + 1] <- vals[idx[1]]
                }} else {{
                    wanted[k + 1] <- NA
                }}
            }}
            write.table(matrix(wanted, ncol=1), "{{{{OUTPUT_ccf}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, _ = bridge.rscript_call(
            r_code=r_code, inputs={"data": combined},
            output_names=["ccf"], timeout_sec=60,
        )
        return {
            "ccf_positive": np.asarray(
                outputs["ccf"], dtype=np.float64,
            ).reshape(-1),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "ccf_positive": _compare_vector(
                tsl["ccf_positive"], ref["ccf_positive"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_obs": int(self.DGP_N), "max_lag": int(self.MAX_LAG)},
        )
