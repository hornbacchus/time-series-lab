"""Phase 3 Batch 6 — ADF (Augmented Dickey-Fuller) parity check.

Compares TSL ``engine/techniques/adf_test.py`` (statsmodels
``adfuller``) against R ``urca::ur.df`` on a synthetic AR(1)
fixture. Closed-form test statistic + Mackinnon critical
values; Pattern A bit-exact target on the test statistic
itself (lag selection may differ, so we pin lag explicitly).
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


def _generate_ar1(
    *, seed: int, n: int = 500, phi: float = 0.7,
    sigma: float = 1.0, burn: int = 100,
) -> np.ndarray:
    """Stationary AR(1) realization for stationarity-test fixtures."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn) * sigma
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return y[burn:]


class AdfParity(P3ParityCheck):
    """ADF stationarity-test parity vs R urca::ur.df."""

    technique_id = "p3_adf"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "ADF test statistic is OLS-on-differenced-series "
        "regression: tau = (rho_hat - 1) / SE(rho_hat). "
        "statsmodels and urca compute identical closed-form "
        "statistic given identical lag specification. Critical "
        "values come from Mackinnon 1996 tables (or interpolated "
        "asymptotics); both packages use the same tables."
    )

    DGP_N = 500
    DGP_PHI = 0.7
    LAG = 1  # pinned to align both implementations

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar1(seed=seed, n=self.DGP_N, phi=self.DGP_PHI)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.stattools import adfuller  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        # autolag=None pins to user-specified maxlag
        result = adfuller(y, maxlag=self.LAG, autolag=None,
                          regression="c")
        return {
            "test_statistic": float(result[0]),
            "p_value": float(result[1]),
            "n_used": int(result[3]),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            test <- ur.df(y, type = "drift", lags = {self.LAG})
            stat <- as.numeric(test@teststat[1])  # tau-stat (unit root)
            cv5 <- as.numeric(test@cval[1, "5pct"])
            scalars <- c(test_statistic = stat, cv5 = cv5)
            write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"y": y.reshape(-1, 1)},
            output_names=["scalars"], timeout_sec=60,
            capture_versions_for=["urca"],
        )
        sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
        return {
            "test_statistic": float(sc[0]),
            "cv5": float(sc[1]),
            "urca_version": versions.get("urca", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        primary["test_statistic"] = _compare_scalar(
            tsl["test_statistic"], ref["test_statistic"],
            ladder["primary"],
        )
        status = primary["test_statistic"]["status"]
        outcome = ("BLOCK" if status == "BLOCK" else
                   ("CAVEAT" if status == "CAVEAT" else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "urca_version": ref.get("urca_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "lag": int(self.LAG),
                "tsl_p_value": tsl.get("p_value"),
                "ref_cv5": ref.get("cv5"),
            },
        )
