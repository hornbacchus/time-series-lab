"""Phase 3 Batch 6 — KPSS (Kwiatkowski-Phillips-Schmidt-Shin) parity check.

Compares TSL ``engine/techniques/kpss_test.py`` (statsmodels
``kpss``) against R ``urca::ur.kpss`` on a synthetic stationary
AR(1) fixture. Closed-form test statistic + Hobijn-Franses-
Ooms-style critical values; Pattern A bit-exact target on the
test statistic.

KPSS reverses ADF's null: H0 is stationarity (rejecting →
non-stationary). To align bandwidth, we pin ``lags="short"``
(int(4*(n/100)^(1/4))) on the R side and the equivalent
integer on the statsmodels side.
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
    """Stationary AR(1) — same DGP shape as p3_adf."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn) * sigma
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return y[burn:]


class KpssParity(P3ParityCheck):
    """KPSS stationarity-test parity vs R urca::ur.kpss."""

    technique_id = "p3_kpss"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "KPSS test statistic is a closed-form ratio of "
        "partial-sums-of-residuals to a Newey-West-style "
        "long-run variance estimator. statsmodels and urca "
        "compute the identical statistic given identical "
        "bandwidth (lag truncation). Critical values come "
        "from Hobijn-Franses-Ooms 2004 / KPSS 1992 tables; "
        "both packages use the same tables."
    )

    DGP_N = 500
    DGP_PHI = 0.7
    # Schwert-style "short" lag rule: int(4*(n/100)^(1/4))
    # n=500 -> int(4 * 5^0.25) = int(5.98) = 5; statsmodels
    # accepts an integer. urca takes lags="short" string for
    # the equivalent calculation (but pins to 5 internally).
    LAG = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar1(seed=seed, n=self.DGP_N, phi=self.DGP_PHI)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.stattools import kpss  # type: ignore
        import warnings as _w
        y = np.asarray(fixture["y"], dtype=np.float64)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            stat, p_value, used_lags, crit = kpss(
                y, regression="c", nlags=self.LAG,
            )
        return {
            "test_statistic": float(stat),
            "p_value": float(p_value),
            "used_lags": int(used_lags),
            "cv5": float(crit["5%"]),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            test <- ur.kpss(y, type = "mu", use.lag = {self.LAG})
            stat <- as.numeric(test@teststat[1])
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
                "tsl_cv5": tsl.get("cv5"),
            },
        )
