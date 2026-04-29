"""Phase 4.5 reference parity check for critical_slowing_down.

Validates that TSL's CSD pipeline matches Python ``ewstools``
(Bury 2023) on the saddle-node-normal-form SDE fixture (Phase 1
amendment 2026-04-25 replaced the original logistic-map fixture
with this true saddle-node fold).

Tolerance ladder (per Phase 3.1 workflow doc + Refinement A):

  Tier 1 (strict, bitwise) -- ASSERTED:
    - Rolling AR(1) series: abs_tol=1e-8
    - Rolling variance series: abs_tol=1e-8
    - Kendall tau on AR(1): abs_tol=1e-8
    - Kendall tau on variance: abs_tol=1e-8

  Tier 2 (informational only for v1) -- RECORDED, NOT ASSERTED:
    - Composite EWS score
    - Empirical p-values

R4 + R5 alignment notes (resolved at apply time, ewstools 2.1.2):

  - ewstools.TimeSeries(data=pd.Series, transition=None) wraps
    the input. We pass a pandas Series with integer index.
  - ewstools detrend(method='Gaussian', bandwidth=B) converts
    bandwidth -> kernel sigma via ``sigma = (0.25/0.675) * B``.
    TSL passes ``bandwidth`` directly to scipy.gaussian_filter1d
    as the kernel sigma. To match the same effective sigma we
    pass ``ewstools_bandwidth = sigma_tsl * (0.675/0.25)`` so
    ewstools reverses the conversion to the same kernel sigma.
  - ewstools rolling-window outputs use pandas right-aligned
    convention (NaN for first W-1 positions). TSL helpers also
    use right-aligned and emit a length-(T-W+1) array. The
    parity comparison drops ewstools' leading NaNs and aligns
    the two arrays by length.
  - ewstools.compute_ktau() computes Kendall tau over the
    NON-NaN portion of each indicator series; matches what TSL
    does on its own length-(T-W+1) array.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck


# Conversion factor: ewstools applies sigma = (0.25/0.675) * bandwidth.
# To get scipy.gaussian_filter1d to receive sigma=S given an
# ewstools-style bandwidth call, pass bandwidth = S / (0.25/0.675)
# = S * (0.675/0.25) = 2.7 * S.
_EWS_BW_FROM_SIGMA = 0.675 / 0.25  # ~2.7


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import the TSL CSD
    wrapper."""
    import pathlib
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


class CriticalSlowingDownParity(P3ParityCheck):
    """CSD parity vs ewstools on saddle-node SDE fixture."""

    technique_id = "critical_slowing_down"
    tier = "fast"
    fixture_id = "critical_slowing_down_saddle_node"

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Critical-slowing-down EWS detection is closed-form: "
        "rolling AR(1) coefficient + variance + autocorrelation. "
        "TSL and ewstools 2.1.2 implement identical rolling-"
        "window stats; bit-exact at machine precision."
    )

    # Tier 1 strict tolerances
    ROLLING_AR1_ABS_TOL = 1e-8
    ROLLING_VAR_ABS_TOL = 1e-8
    TAU_ABS_TOL = 1e-8

    # Pipeline parameters (must match between TSL + ewstools)
    ROLLING_WINDOW = 500
    GAUSSIAN_SIGMA = 200.0   # TSL bandwidth = scipy gaussian_filter1d sigma

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        """Runner already loaded fixture data; nothing extra needed."""
        return {"_seed": int(seed)}

    # -----------------------------------------------------------------
    # TSL side
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext
        from techniques import critical_slowing_down as csd_mod

        y = np.asarray(fixture["y"], dtype=np.float64)
        T = int(np.asarray(fixture.get("T", len(y))))
        seed = int(fixture.get("_seed", 42))

        ctx = RunContext({
            "run_id": "parity_csd",
            "technique_id": "critical_slowing_down",
            "preset": "Balanced",
            "seed": seed,
            "frequency": "daily",
            "time": list(range(T)),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "detrending_method": "gaussian",
                "detrending_bandwidth": self.GAUSSIAN_SIGMA,
                "rolling_window": self.ROLLING_WINDOW,
                # Use a Kendall lookback that includes essentially
                # the entire indicator series. The wrapper's
                # insufficient-data guard requires T >= W + lookback,
                # so the maximum is T - W (NOT T - W + 1, which is
                # the indicator series length and would trip the
                # guard by 1). ewstools' compute_ktau uses the
                # full non-NaN indicator series; this gives an
                # off-by-one in the tail that is corrected at the
                # comparison step (TSL drops the last point of the
                # indicator series compared to ewstools' usage).
                "kendall_lookback": T - self.ROLLING_WINDOW,
                # We don't need surrogate p-values for Tier 1 parity;
                # asymptotic p is fine and avoids the surrogate-loop
                # runtime cost.
                "compute_pvalues": False,
                "expose_rolling_series": True,
            },
        })
        res = csd_mod.run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL CSD run failed: {res.get('error_message')}"
            )
        a = res["audit_fields"]
        return {
            "rolling_ar1": np.asarray(
                a["rolling_ar1_series"], dtype=np.float64,
            ),
            "rolling_variance": np.asarray(
                a["rolling_variance_series"], dtype=np.float64,
            ),
            "tau_ar1": float(a["tau_ar1"]),
            "tau_variance": float(a["tau_variance"]),
            "composite_score": float(a["ews_composite_score"]),
        }

    # -----------------------------------------------------------------
    # Reference side -- ewstools 2.1.2
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import ewstools  # noqa: F401 — required reference import
        import pandas as pd
        from scipy import stats as scipy_stats

        y = np.asarray(fixture["y"], dtype=np.float64)
        T = len(y)

        # Wrap as pandas Series with integer index
        s = pd.Series(y, index=np.arange(T, dtype=np.int64))
        ts = ewstools.TimeSeries(data=s, transition=None)

        # Detrend with ewstools' Gaussian. Pass bandwidth so
        # internal conversion produces our target sigma:
        #   ewstools sigma = (0.25/0.675) * bandwidth
        # so bandwidth = sigma_target / (0.25/0.675)
        #              = sigma_target * (0.675/0.25)
        ews_bandwidth = self.GAUSSIAN_SIGMA * _EWS_BW_FROM_SIGMA
        ts.detrend(method="Gaussian", bandwidth=ews_bandwidth)

        # Compute rolling indicators with the same window
        ts.compute_var(rolling_window=self.ROLLING_WINDOW)
        ts.compute_auto(rolling_window=self.ROLLING_WINDOW, lag=1)

        # ewstools writes results to ts.ews (DataFrame).
        ews_df = ts.ews
        # Drop leading NaNs (from rolling-window warm-up); the
        # remaining values align with TSL's length-(T-W+1) array.
        ar1_ref = ews_df["ac1"].dropna().values.astype(np.float64)
        var_ref = ews_df["variance"].dropna().values.astype(np.float64)

        # Tau alignment (per §16 failure-protocol "fixable by
        # edge-trim in compare()"): ewstools' compute_ktau() uses
        # the full T-W+1 indicator series; TSL's wrapper guard
        # requires T >= W + lookback so the maximum lookback is
        # T - W (= len(indicator) - 1). We therefore compute the
        # reference tau on the SAME trailing slice TSL uses
        # (last T-W = 1500 of 1501 points), so the parity
        # comparison is bitwise across both arms.
        kendall_lookback = T - self.ROLLING_WINDOW
        ar1_tail = ar1_ref[-kendall_lookback:]
        var_tail = var_ref[-kendall_lookback:]
        n_pts = ar1_tail.size
        t_idx = np.arange(n_pts, dtype=np.float64)
        tau_ar1_ref = float(scipy_stats.kendalltau(
            t_idx, ar1_tail, variant="b", method="asymptotic",
        ).statistic)
        tau_var_ref = float(scipy_stats.kendalltau(
            t_idx, var_tail, variant="b", method="asymptotic",
        ).statistic)

        return {
            "rolling_ar1": ar1_ref,
            "rolling_variance": var_ref,
            "tau_ar1": tau_ar1_ref,
            "tau_variance": tau_var_ref,
            "ewstools_version": "2.1.2",
        }

    # -----------------------------------------------------------------
    # Compare -- two-tier
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        metrics: dict[str, Any] = {}
        any_block = False

        tsl_ar1 = np.asarray(tsl["rolling_ar1"], dtype=np.float64)
        ref_ar1 = np.asarray(ref["rolling_ar1"], dtype=np.float64)

        if tsl_ar1.shape != ref_ar1.shape:
            metrics["rolling_ar1_shape_mismatch"] = {
                "status": "BLOCK",
                "tsl_shape": list(tsl_ar1.shape),
                "ref_shape": list(ref_ar1.shape),
                "note": (
                    "Length mismatch likely indicates rolling-window "
                    "alignment difference. TSL uses right-aligned "
                    "with length T-W+1; ewstools uses pandas "
                    "right-aligned with leading NaNs (dropped here)."
                ),
            }
            any_block = True
            ar1_diff = float("nan")
        else:
            ar1_diff = float(np.max(np.abs(tsl_ar1 - ref_ar1)))
            ar1_ok = ar1_diff <= self.ROLLING_AR1_ABS_TOL
            metrics["rolling_ar1_abs_diff"] = {
                "status": "PASS" if ar1_ok else "BLOCK",
                "max_abs_diff": ar1_diff,
                "tolerance": self.ROLLING_AR1_ABS_TOL,
                "n_points": int(tsl_ar1.size),
            }
            if not ar1_ok:
                any_block = True

        tsl_var = np.asarray(tsl["rolling_variance"], dtype=np.float64)
        ref_var = np.asarray(ref["rolling_variance"], dtype=np.float64)
        if tsl_var.shape != ref_var.shape:
            metrics["rolling_variance_shape_mismatch"] = {
                "status": "BLOCK",
                "tsl_shape": list(tsl_var.shape),
                "ref_shape": list(ref_var.shape),
            }
            any_block = True
            var_diff = float("nan")
        else:
            var_diff = float(np.max(np.abs(tsl_var - ref_var)))
            var_ok = var_diff <= self.ROLLING_VAR_ABS_TOL
            metrics["rolling_variance_abs_diff"] = {
                "status": "PASS" if var_ok else "BLOCK",
                "max_abs_diff": var_diff,
                "tolerance": self.ROLLING_VAR_ABS_TOL,
                "n_points": int(tsl_var.size),
            }
            if not var_ok:
                any_block = True

        tau_ar1_diff = abs(
            float(tsl["tau_ar1"]) - float(ref["tau_ar1"])
        )
        tau_ar1_ok = tau_ar1_diff <= self.TAU_ABS_TOL
        metrics["tau_ar1_abs_diff"] = {
            "status": "PASS" if tau_ar1_ok else "BLOCK",
            "tsl_value": float(tsl["tau_ar1"]),
            "ref_value": float(ref["tau_ar1"]),
            "abs_diff": tau_ar1_diff,
            "tolerance": self.TAU_ABS_TOL,
        }
        if not tau_ar1_ok:
            any_block = True

        tau_var_diff = abs(
            float(tsl["tau_variance"]) - float(ref["tau_variance"])
        )
        tau_var_ok = tau_var_diff <= self.TAU_ABS_TOL
        metrics["tau_variance_abs_diff"] = {
            "status": "PASS" if tau_var_ok else "BLOCK",
            "tsl_value": float(tsl["tau_variance"]),
            "ref_value": float(ref["tau_variance"]),
            "abs_diff": tau_var_diff,
            "tolerance": self.TAU_ABS_TOL,
        }
        if not tau_var_ok:
            any_block = True

        outcome = "BLOCK" if any_block else "PASS"

        diagnostics = {
            "tsl_composite_score": float(tsl.get("composite_score", 0.0)),
            "ewstools_version": ref.get("ewstools_version", "unknown"),
            "tier_2_note": (
                "Composite EWS score and empirical p-values are "
                "informational-only per Refinement A; not asserted "
                "in v1. The Tier 1 strict assertions cover the four "
                "deterministic primitives (rolling AR(1), rolling "
                "variance, Kendall tau on each)."
            ),
            "alignment_note": (
                "TSL uses raw bandwidth as gaussian_filter1d sigma. "
                "ewstools applies sigma = (0.25/0.675) * bandwidth. "
                "Parity passes ewstools_bandwidth = sigma_tsl * "
                "(0.675/0.25) ~= 2.7 * sigma_tsl so internal kernel "
                "sigmas match."
            ),
        }

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics=diagnostics,
        )
