"""Phase 3 Batch 6 — PELT change-point parity check.

Compares TSL ``engine/techniques/pelt_change_points.py``
(``ruptures.Pelt``) against direct ``ruptures.Pelt``
invocation on a synthetic mean-shift fixture.

This is a SAME-LIBRARY parity check: both arms call
``ruptures.Pelt(model="l2", min_size=5, jump=1).fit(y).predict(pen=p)``
with identical arguments. Pattern A bit-exact target;
divergence indicates a TSL preprocessing or argument-handling
bug, not a methodology difference.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_mean_shift_dgp(
    *, seed: int, n: int = 600, n_segments: int = 4,
    sigma: float = 1.0,
) -> np.ndarray:
    """Mean-shift signal: 4 segments of length n/4, means
    drawn from N(0, 4); piecewise-constant + Gaussian noise.
    """
    rng = np.random.default_rng(seed)
    seg_len = n // n_segments
    means = rng.standard_normal(n_segments) * 2.0
    y = np.zeros(n)
    for k in range(n_segments):
        a = k * seg_len
        b = (k + 1) * seg_len if k < n_segments - 1 else n
        y[a:b] = means[k] + rng.standard_normal(b - a) * sigma
    return y


class PeltParity(P3ParityCheck):
    """PELT change-point detection parity (ruptures self-test)."""

    technique_id = "p3_pelt"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PELT is a deterministic dynamic-programming algorithm "
        "(Killick-Fearnhead-Eckley 2012). TSL and reference "
        "both invoke ruptures.Pelt with identical model/cost "
        "function/penalty/min_size; output is bitwise-identical "
        "given identical input + arguments. Failure = TSL "
        "preprocessing or argument-passing bug."
    )

    DGP_N = 600
    DGP_K = 4   # segments
    MIN_SIZE = 5
    MODEL = "l2"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_mean_shift_dgp(
            seed=seed, n=self.DGP_N, n_segments=self.DGP_K,
        )}

    def _pelt_predict(self, y: np.ndarray, pen: float) -> list[int]:
        """Run ruptures.Pelt with the same arguments TSL uses."""
        import ruptures as rpt  # type: ignore
        signal = y.reshape(-1, 1)
        algo = rpt.Pelt(
            model=self.MODEL, min_size=self.MIN_SIZE, jump=1,
        ).fit(signal)
        bkps = algo.predict(pen=pen)
        # Strip trailing n (ruptures convention: last entry == len(y))
        if bkps and bkps[-1] == len(y):
            bkps = bkps[:-1]
        return bkps

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # Run via TSL wrapper to exercise its full code path
        # (preprocessing, NaN handling, penalty resolution).
        from techniques.base import RunContext  # type: ignore
        from techniques.pelt_change_points import run as pelt_run  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        # BIC penalty pinned: pen = log(n) * sigma^2 (matches
        # TSL's wrapper default for "bic" string).
        sigma2 = float(np.var(y))
        pen = float(np.log(len(y)) * sigma2)

        ctx = RunContext({
            "run_id": "p3_pelt_tsl",
            "technique_id": "pelt_change_points",
            "preset": "Balanced", "seed": 42, "frequency": "irregular",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "model": self.MODEL,
                "min_size": self.MIN_SIZE,
                "penalty": pen,  # numeric, bypasses string branch
                "jump": 1,
            },
        })
        res = pelt_run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL PELT failed: {res.get('error_message')}"
            )
        a = res["audit_fields"]
        # change_point_positions stored 1-indexed in audit;
        # convert to 0-indexed indices for comparison
        cps_1indexed = a.get("change_point_positions") or []
        cps_0indexed = [int(x) - 1 for x in cps_1indexed]
        return {
            "n_change_points": int(a.get("n_change_points", 0)),
            "change_points": sorted(cps_0indexed),
            "penalty": pen,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # Direct ruptures invocation (same library; in-process).
        import ruptures  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        sigma2 = float(np.var(y))
        pen = float(np.log(len(y)) * sigma2)
        bkps = self._pelt_predict(y, pen)
        return {
            "n_change_points": int(len(bkps)),
            "change_points": sorted([int(x) for x in bkps]),
            "penalty": pen,
            "ruptures_version": getattr(ruptures, "__version__", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        # Compare change-point counts (must match exactly)
        primary["n_change_points"] = _compare_scalar(
            float(tsl["n_change_points"]),
            float(ref["n_change_points"]),
            ladder["primary"],
        )
        # Set-equality of indices (positions). TSL stores
        # 1-indexed → converted; ref stores raw ruptures
        # output (0-indexed end-of-segment markers). Compare
        # them as sets after conversion.
        tsl_cps = set(tsl["change_points"])
        ref_cps = set(ref["change_points"])
        positions_match = tsl_cps == ref_cps
        # Also report mismatch metrics as a dict-style entry
        primary["positions_set_match"] = {
            "status": "PASS" if positions_match else "BLOCK",
            "tsl_only": sorted(tsl_cps - ref_cps),
            "ref_only": sorted(ref_cps - tsl_cps),
            "intersection_size": len(tsl_cps & ref_cps),
        }
        any_block = any(
            primary[k]["status"] == "BLOCK" for k in primary
        )
        any_caveat = any(
            primary[k]["status"] == "CAVEAT" for k in primary
        )
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "ruptures_version": ref.get("ruptures_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "n_segments_true": int(self.DGP_K),
                "model": self.MODEL,
                "min_size": int(self.MIN_SIZE),
                "penalty": float(tsl.get("penalty", 0.0)),
                "tsl_n_cp": int(tsl.get("n_change_points", 0)),
                "ref_n_cp": int(ref.get("n_change_points", 0)),
            },
        )
