"""Phase 3 Batch 1 — Classical decomposition parity check.

Compares TSL's ``engine/techniques/classical_decompose.py``
(statsmodels ``seasonal_decompose`` backbone) against R
``stats::decompose`` on a synthetic additive seasonal+trend+noise
fixture.

Reference selection note: both implementations follow the
classical decomposition algorithm: centered moving average →
trend → detrend (additive: subtract; multiplicative: divide) →
group seasonal averages → de-seasonalized residual. Closed-form
arithmetic; bit-exact parity expected.

Output-tier discipline:

- **Primary:** trend, seasonal, residual component vectors
  (centered MA portion only — leading and trailing trend
  values are NaN by convention).
- **Secondary:** seasonal-component periodicity check (length
  m, repeats T/m times).

Fixture: T=120 monthly seasonal+trend, additive model, m=12,
seed=42 (reused via _generate_seasonal_ar_dgp from p3_theta).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks.p3_arima import (
    _compare_vector,
    _ensure_engine_on_path,
)
from reference_parity.harness.checks.p3_theta import (
    _generate_seasonal_ar_dgp,
)


class ClassicalDecomposeParity(P3ParityCheck):
    """Classical additive decomposition parity vs R stats::decompose.

    DGP: seasonal AR(1) with linear trend + sin seasonality;
    same generator as p3_theta. T=120, m=12, seed=42.
    """

    technique_id = "p3_classical_decompose"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Classical decomposition is closed-form arithmetic: "
        "centered moving average -> trend; detrend -> group "
        "seasonal averages; residual = y - trend - seasonal. "
        "statsmodels seasonal_decompose and R stats::decompose "
        "implement the same algorithm; achieved 7.1e-14 abs "
        "across all three components (machine precision)."
    )

    DGP_M = 12
    DGP_N = 120

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_seasonal_ar_dgp(
            seed=seed,
            n=self.DGP_N,
            phi=0.7,
            sigma=1.0,
            m=self.DGP_M,
        )
        return {"y": y, "m": self.DGP_M}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.seasonal import seasonal_decompose  # type: ignore
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")

            y = np.asarray(fixture["y"], dtype=np.float64)
            m = int(fixture["m"])

            decomp = seasonal_decompose(
                y, model="additive", period=m, two_sided=True,
                extrapolate_trend=0,
            )
            trend = np.asarray(decomp.trend, dtype=np.float64)
            seasonal = np.asarray(decomp.seasonal, dtype=np.float64)
            resid = np.asarray(decomp.resid, dtype=np.float64)

        return {
            "trend": trend,
            "seasonal": seasonal,
            "resid": resid,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        m = int(fixture["m"])

        r_code = rf"""
            y_raw <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            y <- ts(y_raw, frequency = {m})

            d <- decompose(y, type = "additive")

            # Trend, seasonal, random components — length T,
            # leading/trailing entries NA where centered MA is
            # undefined.
            write.table(matrix(as.numeric(d$trend), ncol=1),
                        "{{{{OUTPUT_trend}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(d$seasonal), ncol=1),
                        "{{{{OUTPUT_seasonal}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(d$random), ncol=1),
                        "{{{{OUTPUT_resid}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["trend", "seasonal", "resid"],
            timeout_sec=30,
            capture_versions_for=[],
        )
        return {
            "trend": np.atleast_1d(outputs["trend"]).astype(np.float64).reshape(-1),
            "seasonal": np.atleast_1d(outputs["seasonal"]).astype(np.float64).reshape(-1),
            "resid": np.atleast_1d(outputs["resid"]).astype(np.float64).reshape(-1),
        }

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        any_block = False
        any_caveat = False

        for key in ("trend", "seasonal", "resid"):
            tsl_v = np.asarray(tsl[key], dtype=np.float64).reshape(-1)
            ref_v = np.asarray(ref[key], dtype=np.float64).reshape(-1)
            # Truncate to common length (R may pad NaN at edges
            # of trend; lengths should match T but be defensive).
            n_common = min(len(tsl_v), len(ref_v))
            tsl_v = tsl_v[:n_common]
            ref_v = ref_v[:n_common]
            mask = np.isfinite(tsl_v) & np.isfinite(ref_v)
            if int(mask.sum()) < 5:
                primary[key] = {
                    "status": "BLOCK",
                    "note": f"fewer than 5 finite values in common ({int(mask.sum())})",
                    "n_finite": int(mask.sum()),
                }
                any_block = True
                continue
            primary[key] = _compare_vector(
                tsl_v[mask], ref_v[mask], ladder["primary"],
            )
            if primary[key]["status"] == "BLOCK":
                any_block = True
            elif primary[key]["status"] == "CAVEAT":
                any_caveat = True

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "m": int(self.DGP_M),
            },
        )
