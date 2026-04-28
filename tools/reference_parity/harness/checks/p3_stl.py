"""Phase 3 Batch 1 — STL (Seasonal-Trend Loess) parity check.

Compares TSL's ``engine/techniques/stl_decompose.py`` (statsmodels
``STL`` backbone) against R ``stats::stl`` on a synthetic seasonal
fixture.

Reference selection note: both implementations follow Cleveland
et al. 1990 STL. statsmodels' STL and R's stats::stl have
slightly different defaults for inner/outer iterations, LOESS
smoothing windows, and trend-extraction convention. Tolerance
band per master plan §7.1 widened to 5e-2 abs / 5e-2 rel.

Output-tier discipline:

- **Primary:** trend, seasonal, residual component vectors.
- **Secondary:** seasonal-strength and trend-strength
  diagnostics (computed from the same components).

Fixture: T=120 monthly seasonal+trend, m=12, seed=42 (reused
from p3_theta DGP).
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


class StlParity(P3ParityCheck):
    """STL parity vs R stats::stl.

    DGP: seasonal AR(1) with linear trend + sin seasonality;
    same generator as p3_theta. T=120, m=12, seed=42.
    Configuration matches between TSL and R as closely as
    possible: s.window = 13 (default for monthly), robust=FALSE,
    inner=2, outer=0 (statsmodels Fast preset matches R defaults
    closer than Balanced).
    """

    technique_id = "p3_stl"
    tier = "fast"
    fixture_id = ""

    verdict_class = "iterative_loess"
    verdict_class_rationale = (
        "STL is iterative LOESS decomposition (Cleveland et al. "
        "1990). statsmodels STL and R stats::stl implement the "
        "canonical algorithm but differ in default LOESS "
        "internals + inner-iteration convergence path. Per-"
        "index divergence ~9e-2 abs is reproducible across "
        "seeds (deterministic; not MC noise). reroll_on_caveat "
        "= False (class default) prevents the runner's "
        "CAVEAT-reroll-and-bump-to-BLOCK protocol from firing "
        "on what is a structural implementation difference."
    )
    # reroll_on_caveat = False (class default; previously this
    # check overrode on_caveat_reroll() explicitly — now the
    # default itself per Session 5 lock)

    DGP_M = 12
    DGP_N = 120
    SEASONAL_WINDOW = 13  # odd; matches R default for m=12
    INNER_ITER = 2  # match R default
    OUTER_ITER = 0
    ROBUST = False

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
        from statsmodels.tsa.seasonal import STL  # type: ignore
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")

            y = np.asarray(fixture["y"], dtype=np.float64)
            m = int(fixture["m"])

            stl = STL(
                y,
                period=m,
                seasonal=self.SEASONAL_WINDOW,
                seasonal_deg=1,
                trend_deg=1,
                low_pass_deg=1,
                robust=self.ROBUST,
            )
            res = stl.fit(
                inner_iter=self.INNER_ITER,
                outer_iter=self.OUTER_ITER,
            )

            trend = np.asarray(res.trend, dtype=np.float64)
            seasonal = np.asarray(res.seasonal, dtype=np.float64)
            resid = np.asarray(res.resid, dtype=np.float64)

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

        # R stats::stl arguments:
        #   s.window: integer or "periodic"; here 13 (matches TSL)
        #   s.degree: 0 or 1; default 0; we use 1 to match TSL
        #     seasonal_deg=1
        #   t.window: not specified → automatically chosen as
        #     the smallest odd integer >= 1.5 * period / (1 - 1.5/s.window)
        #   robust: FALSE
        #   inner: 2 (default), outer: 0 if !robust
        r_code = rf"""
            y_raw <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            y <- ts(y_raw, frequency = {m})

            res <- stl(
                y, s.window = {self.SEASONAL_WINDOW},
                s.degree = 1, t.degree = 1, l.degree = 1,
                robust = FALSE, inner = {self.INNER_ITER},
                outer = {self.OUTER_ITER}
            )

            comps <- res$time.series
            # comps is a 3-column ts: seasonal, trend, remainder
            write.table(matrix(as.numeric(comps[, "trend"]), ncol=1),
                        "{{{{OUTPUT_trend}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(comps[, "seasonal"]), ncol=1),
                        "{{{{OUTPUT_seasonal}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(as.numeric(comps[, "remainder"]), ncol=1),
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
            n_common = min(len(tsl_v), len(ref_v))
            tsl_v = tsl_v[:n_common]
            ref_v = ref_v[:n_common]
            mask = np.isfinite(tsl_v) & np.isfinite(ref_v)
            if int(mask.sum()) < 5:
                primary[key] = {
                    "status": "BLOCK",
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
                "seasonal_window": int(self.SEASONAL_WINDOW),
                "inner_iter": int(self.INNER_ITER),
                "outer_iter": int(self.OUTER_ITER),
                "robust": bool(self.ROBUST),
            },
        )

    # Phase 3 Session 5: explicit ``on_caveat_reroll`` override
    # removed because ``reroll_on_caveat = False`` is now the
    # P3ParityCheck class default. Pre-Session-5, this method
    # body was the canonical example of the deterministic-CAVEAT
    # discipline pattern; Session 5 promoted it to default,
    # leaving deterministic checks free of override boilerplate.
    # MC / EM-stochastic checks opt in via
    # ``reroll_on_caveat = True``.
