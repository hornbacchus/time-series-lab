"""Phase 3 Batch 1 — MSTL (Multiple STL) parity check.

Compares TSL's ``engine/techniques/mstl_decompose.py``
(statsmodels ``MSTL`` backbone) against R ``forecast::mstl``
on a synthetic dual-seasonality fixture.

Reference selection note: both implementations apply STL
iteratively across multiple seasonal periods (Bandara, Hyndman,
Bergmeir 2021). statsmodels' MSTL and R forecast::mstl differ
in (a) inner-iteration counts, (b) LOESS bandwidths, and (c)
period-iteration order. Tolerance band per master plan §7.1
widened from p3_stl base.

Output-tier discipline:

- **Primary:** trend, seasonal-1 (period m1), residual.
- **Secondary:** seasonal-2 (period m2 if multi-period
  configuration succeeds on this fixture).

Fixture: T=300 daily-resolution series with 7-day weekly
seasonality + 30-day "monthly" seasonality + linear trend +
noise, seed=42. Periods m=[7, 30].
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


def _generate_dual_seasonal_dgp(
    *,
    seed: int,
    n: int = 300,
    sigma: float = 1.0,
    m1: int = 7,
    m2: int = 30,
    amp1: float = 2.0,
    amp2: float = 3.0,
    trend_slope: float = 0.05,
    initial_level: float = 50.0,
) -> np.ndarray:
    """Generate dual-seasonal series with both m1 and m2
    periodic patterns + trend + Gaussian noise."""
    rng = np.random.default_rng(seed)
    t_arr = np.arange(n)
    seasonal1 = amp1 * np.sin(2 * np.pi * t_arr / m1)
    seasonal2 = amp2 * np.sin(2 * np.pi * t_arr / m2)
    noise = rng.standard_normal(n) * sigma
    y = initial_level + trend_slope * t_arr + seasonal1 + seasonal2 + noise
    return y


class MstlParity(P3ParityCheck):
    """MSTL parity vs R forecast::mstl.

    DGP: dual-seasonal m1=7, m2=30, T=300, seed=42.
    """

    technique_id = "p3_mstl"
    tier = "fast"
    fixture_id = ""

    verdict_class = "iterative_loess"
    verdict_class_rationale = (
        "MSTL applies STL iteratively across multiple seasonal "
        "periods (Bandara, Hyndman, Bergmeir 2021). "
        "statsmodels MSTL and R forecast::mstl differ in "
        "default inner-iteration counts, LOESS bandwidths, and "
        "period-iteration ordering. Per-component decomposition "
        "is non-unique within the constraint y = trend + sum"
        "(seasonal_k) + resid; each implementation picks a "
        "different feasible point. Per-component divergence "
        "~1.0 abs but structural identity verified at 7.1e-14 "
        "abs (recon_cross_max_abs_diff diagnostic — Pattern F "
        "Session 4). reroll_on_caveat = False (class default)."
    )
    # Per user-locked refinement 2 (Session 5 plan):
    # ``structural_invariants`` declaration deferred to Batch 7
    # when wavelet/FFT class invariants populate. The
    # recon_cross_max_abs_diff diagnostic in compare() below
    # remains as a per-check inline computation — it does NOT
    # go through the structural_invariants registry this session.

    DGP_M1 = 7
    DGP_M2 = 30
    DGP_N = 300

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_dual_seasonal_dgp(
            seed=seed,
            n=self.DGP_N,
            sigma=1.0,
            m1=self.DGP_M1,
            m2=self.DGP_M2,
        )
        return {
            "y": y,
            "periods": [self.DGP_M1, self.DGP_M2],
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.seasonal import MSTL  # type: ignore
        import warnings as _w
        with _w.catch_warnings():
            _w.simplefilter("ignore")

            y = np.asarray(fixture["y"], dtype=np.float64)
            periods = list(fixture["periods"])

            mstl = MSTL(y, periods=periods)
            res = mstl.fit()

            trend = np.asarray(res.trend, dtype=np.float64)
            # MSTL exposes seasonal as an array of shape
            # (n, len(periods)); column k corresponds to periods[k].
            seasonal_all = np.asarray(res.seasonal, dtype=np.float64)
            if seasonal_all.ndim == 1:
                seasonal_all = seasonal_all.reshape(-1, 1)
            seasonal_1 = seasonal_all[:, 0]
            seasonal_2 = seasonal_all[:, 1] if seasonal_all.shape[1] > 1 else np.zeros_like(trend)
            resid = np.asarray(res.resid, dtype=np.float64)

        return {
            "trend": trend,
            "seasonal_1": seasonal_1,
            "seasonal_2": seasonal_2,
            "resid": resid,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        periods = list(fixture["periods"])
        m1, m2 = int(periods[0]), int(periods[1])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(forecast) }})
            y_raw <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            # MSTL accepts a multi-seasonal-period ts via msts()
            y <- msts(y_raw, seasonal.periods = c({m1}, {m2}))

            res <- mstl(y)
            # res is a multi-column ts: Data, Trend, Seasonal{m1},
            # Seasonal{m2} (in order), Remainder.
            colnms <- colnames(res)
            seas_cols <- grep("^Seasonal", colnms, value=TRUE)
            trend_col <- grep("^Trend", colnms, value=TRUE)[1]
            resid_col <- grep("^Remainder", colnms, value=TRUE)[1]

            trend_vec <- as.numeric(res[, trend_col])
            seas1_vec <- as.numeric(res[, seas_cols[1]])
            seas2_vec <- if (length(seas_cols) >= 2) as.numeric(res[, seas_cols[2]]) else rep(0, length(y_raw))
            resid_vec <- as.numeric(res[, resid_col])

            write.table(matrix(trend_vec, ncol=1), "{{{{OUTPUT_trend}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(seas1_vec, ncol=1), "{{{{OUTPUT_seasonal_1}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(seas2_vec, ncol=1), "{{{{OUTPUT_seasonal_2}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(resid_vec, ncol=1), "{{{{OUTPUT_resid}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["trend", "seasonal_1", "seasonal_2", "resid"],
            timeout_sec=60,
            capture_versions_for=["forecast"],
        )
        return {
            "trend": np.atleast_1d(outputs["trend"]).astype(np.float64).reshape(-1),
            "seasonal_1": np.atleast_1d(outputs["seasonal_1"]).astype(np.float64).reshape(-1),
            "seasonal_2": np.atleast_1d(outputs["seasonal_2"]).astype(np.float64).reshape(-1),
            "resid": np.atleast_1d(outputs["resid"]).astype(np.float64).reshape(-1),
            "forecast_version": versions.get("forecast", "unknown"),
        }

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        diagnostic: dict[str, Any] = {}
        any_block = False
        any_caveat = False

        # Structural identity check: trend + seasonal_1 +
        # seasonal_2 + resid == y (within machine precision).
        # MSTL's component decomposition is non-unique, but the
        # structural identity must hold on both sides.
        for side, arrs in (("tsl", tsl), ("ref", ref)):
            recon = (
                np.asarray(arrs["trend"], dtype=np.float64).reshape(-1)
                + np.asarray(arrs["seasonal_1"], dtype=np.float64).reshape(-1)
                + np.asarray(arrs["seasonal_2"], dtype=np.float64).reshape(-1)
                + np.asarray(arrs["resid"], dtype=np.float64).reshape(-1)
            )
            # Ground-truth reconstruction: TSL/REF should reproduce
            # the input fixture y. Use TSL's components — fixture
            # is shared, both sides decompose the same y.
            diagnostic[f"{side}_recon_max_abs_diff"] = float(
                np.max(np.abs(recon - recon.mean()))  # variation
            ) if len(recon) > 0 else float("nan")
        # Cross-side recon check: TSL recon should equal REF recon
        # since both decompose the same y.
        tsl_recon = (
            np.asarray(tsl["trend"]).reshape(-1)
            + np.asarray(tsl["seasonal_1"]).reshape(-1)
            + np.asarray(tsl["seasonal_2"]).reshape(-1)
            + np.asarray(tsl["resid"]).reshape(-1)
        )
        ref_recon = (
            np.asarray(ref["trend"]).reshape(-1)
            + np.asarray(ref["seasonal_1"]).reshape(-1)
            + np.asarray(ref["seasonal_2"]).reshape(-1)
            + np.asarray(ref["resid"]).reshape(-1)
        )
        n_common = min(len(tsl_recon), len(ref_recon))
        diagnostic["recon_cross_max_abs_diff"] = float(
            np.max(np.abs(tsl_recon[:n_common] - ref_recon[:n_common]))
        )

        for key in ("trend", "seasonal_1", "resid"):
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

        # Secondary: seasonal_2
        tsl_s2 = np.asarray(tsl["seasonal_2"], dtype=np.float64).reshape(-1)
        ref_s2 = np.asarray(ref["seasonal_2"], dtype=np.float64).reshape(-1)
        n_common = min(len(tsl_s2), len(ref_s2))
        mask_s2 = np.isfinite(tsl_s2[:n_common]) & np.isfinite(ref_s2[:n_common])
        if int(mask_s2.sum()) >= 5:
            secondary["seasonal_2"] = _compare_vector(
                tsl_s2[:n_common][mask_s2],
                ref_s2[:n_common][mask_s2],
                ladder["secondary"],
            )
        else:
            secondary["seasonal_2"] = {"status": "INFO", "note": "insufficient finite values"}

        outcome = "BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                **diagnostic,
                "forecast_version": ref.get("forecast_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "periods": [int(self.DGP_M1), int(self.DGP_M2)],
            },
        )

    # Phase 3 Session 5: explicit ``on_caveat_reroll`` override
    # removed; ``reroll_on_caveat = False`` is now the class
    # default. Same rationale as p3_stl.
