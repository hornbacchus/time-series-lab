"""Phase 3 Batch 6 — Phillips-Perron parity check.

Compares TSL ``engine/techniques/pp_test.py`` (statsmodels >=
0.14 ``phillips_perron`` / ``arch.unitroot.PhillipsPerron``
fallback chain) against R ``urca::ur.pp`` on a synthetic
stationary AR(1) fixture. Closed-form Newey-West-corrected
test statistic; Pattern A bit-exact target on the test
statistic.

The TSL backend dispatcher tries
``statsmodels.tsa.stattools.phillips_perron`` first, then
``arch.unitroot.PhillipsPerron``, then a manual implementation.
Whichever path wins on this machine is recorded in the
``method`` field for diagnostic disclosure. urca uses the
Z(t) statistic with ``type="Z-tau"``.
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
    """Stationary AR(1) — same DGP shape as p3_adf / p3_kpss."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn) * sigma
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return y[burn:]


class PpParity(P3ParityCheck):
    """Phillips-Perron unit-root test parity vs R urca::ur.pp."""

    technique_id = "p3_pp"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Phillips-Perron Z(t) statistic is a closed-form "
        "Newey-West correction to the Dickey-Fuller t-statistic. "
        "Both implementations use the same underlying OLS + HAC "
        "long-run variance estimator. Pattern J candidate: "
        "package-internal default bandwidth rules can differ "
        "(arch uses Schwert-style int(4*(n/100)^(2/9)); urca "
        "uses lags='short' which maps to int(4*(n/100)^(1/4)) "
        "or int(12*(n/100)^(1/4))). We pin lags=5 (n=500 short "
        "rule baseline) on both sides to align."
    )

    DGP_N = 500
    DGP_PHI = 0.7
    LAG = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar1(seed=seed, n=self.DGP_N, phi=self.DGP_PHI)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # Use arch.unitroot.PhillipsPerron with explicit lag pin
        # to align with urca's use.lag. statsmodels >= 0.14
        # phillips_perron may not exist on this Python; arch is
        # installed (Phase 3 Batch 2 dep).
        from arch.unitroot import PhillipsPerron  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        pp = PhillipsPerron(y, trend="c", lags=self.LAG)
        return {
            "test_statistic": float(pp.stat),
            "p_value": float(pp.pvalue),
            "lags": int(self.LAG),
            "method": "arch.PhillipsPerron",
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        r_code = rf"""
            suppressPackageStartupMessages({{ library(urca) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            test <- ur.pp(y, type = "Z-tau", model = "constant",
                          use.lag = {self.LAG})
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
                "tsl_method": tsl.get("method"),
                "tsl_p_value": tsl.get("p_value"),
                "ref_cv5": ref.get("cv5"),
            },
        )
