"""ENG-EXT-CHANGEPOINT-001 A1a — multivariate (joint) PELT parity check.

Compares TSL ``engine/techniques/pelt_change_points.py`` MULTIVARIATE
path (auto-detected for >=2 input series) against a direct
``ruptures.Pelt`` invocation on the SAME (n, k) signal.

This is a SAME-LIBRARY self-parity check (Pattern A.1): both arms call
``ruptures.Pelt(model="l2", min_size=5, jump=1).fit(X).predict(pen=p)``
on the identical (n, k) multivariate signal with the IDENTICAL numeric
penalty. ruptures returns a SINGLE JOINT breakpoint set common across
all curve points (the curve-wide regime-shift dates). Pattern A bit-
exact target; divergence indicates a TSL multivariate-stacking or
penalty-convention bug, not a methodology difference.

Penalty discipline (load-bearing): the engine's multivariate BIC
penalty is pen = log(n) * sum_j(var_j) (dimensionally-correct; reduces
to the univariate log(n)*sigma^2 at k=1). The harness passes this exact
numeric penalty to BOTH the engine (via params, bypassing the string
branch) AND the direct-ruptures reference, so the comparison isolates
the wrapper's stacking/argument-handling from any penalty-convention
divergence.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_joint_mean_shift_dgp(
    *, seed: int, n: int = 600, k: int = 3, n_segments: int = 4,
    sigma: float = 1.0,
) -> np.ndarray:
    """Multivariate (n, k) signal with JOINT mean shifts: all k curve
    points shift mean SIMULTANEOUSLY at the same n_segments-1 breakpoints
    (a curve-wide regime model). Per-feature segment means drawn from
    N(0, 4); piecewise-constant + Gaussian noise.
    """
    rng = np.random.default_rng(seed)
    seg_len = n // n_segments
    X = np.zeros((n, k))
    for s in range(n_segments):
        a = s * seg_len
        b = (s + 1) * seg_len if s < n_segments - 1 else n
        means = rng.standard_normal(k) * 2.0  # joint per-feature segment means
        X[a:b, :] = means + rng.standard_normal((b - a, k)) * sigma
    return X


class PeltMultivariateParity(P3ParityCheck):
    """Multivariate (joint) PELT change-point parity (ruptures self-test)."""

    technique_id = "p3_pelt_multivariate"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Multivariate PELT (ENG-EXT-CHANGEPOINT-001 A1a) is a "
        "deterministic dynamic-programming segmentation. TSL's "
        "multivariate path and the reference both invoke ruptures.Pelt "
        "on the same (n,k) signal with identical model/min_size/jump and "
        "the identical numeric penalty; the joint breakpoint set is "
        "bitwise-identical given identical input + arguments. Failure = "
        "TSL multivariate-stacking or penalty-convention bug."
    )

    DGP_N = 600
    DGP_K = 3       # curve points (features)
    DGP_SEG = 4     # joint segments -> 3 joint breakpoints
    MIN_SIZE = 5
    MODEL = "l2"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"X": _generate_joint_mean_shift_dgp(
            seed=seed, n=self.DGP_N, k=self.DGP_K, n_segments=self.DGP_SEG,
        )}

    @staticmethod
    def _mv_penalty(X: np.ndarray) -> float:
        """Engine's multivariate BIC penalty: log(n)*sum_j(var_j)."""
        n = X.shape[0]
        return float(np.log(n) * float(np.sum(np.var(X, axis=0))))

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques.pelt_change_points import run as pelt_run  # type: ignore

        X = np.asarray(fixture["X"], dtype=np.float64)
        n, k = X.shape
        pen = self._mv_penalty(X)
        # Supply k series -> the engine auto-detects multivariate. Numeric
        # penalty bypasses the string branch so both arms use the same pen.
        ctx = RunContext({
            "run_id": "p3_pelt_mv_tsl",
            "technique_id": "pelt_change_points",
            "preset": "Balanced", "seed": 42, "frequency": "irregular",
            "time": list(range(n)),
            "series": [
                {"name": f"t{j}", "values": X[:, j].tolist()} for j in range(k)
            ],
            "params": {
                "model": self.MODEL, "min_size": self.MIN_SIZE,
                "penalty": pen, "jump": 1,
            },
        })
        res = pelt_run(ctx, lambda *a, **kw: None)
        if res.get("status") != "success":
            raise RuntimeError(f"TSL multivariate PELT failed: {res.get('error_message')}")
        a = res["audit_fields"]
        if a.get("mode") != "multivariate":
            raise RuntimeError(
                f"Expected multivariate mode, got {a.get('mode')!r} "
                "(auto-detect did not engage the multivariate path)."
            )
        cps_0indexed = [int(x) - 1 for x in (a.get("change_point_positions") or [])]
        return {
            "n_change_points": int(a.get("n_change_points", 0)),
            "change_points": sorted(cps_0indexed),
            "penalty": pen,
            "n_features": int(a.get("n_features", k)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import ruptures  # type: ignore
        X = np.asarray(fixture["X"], dtype=np.float64)
        n = X.shape[0]
        pen = self._mv_penalty(X)
        algo = ruptures.Pelt(
            model=self.MODEL, min_size=self.MIN_SIZE, jump=1,
        ).fit(X)  # native multivariate (n, k) signal
        bkps = algo.predict(pen=pen)
        if bkps and bkps[-1] == n:
            bkps = bkps[:-1]
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
        primary["n_change_points"] = _compare_scalar(
            float(tsl["n_change_points"]), float(ref["n_change_points"]),
            ladder["primary"],
        )
        tsl_cps = set(tsl["change_points"])
        ref_cps = set(ref["change_points"])
        match = tsl_cps == ref_cps
        primary["joint_positions_set_match"] = {
            "status": "PASS" if match else "BLOCK",
            "tsl_only": sorted(tsl_cps - ref_cps),
            "ref_only": sorted(ref_cps - tsl_cps),
            "intersection_size": len(tsl_cps & ref_cps),
        }
        any_block = any(primary[k]["status"] == "BLOCK" for k in primary)
        any_caveat = any(primary[k]["status"] == "CAVEAT" for k in primary)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "ruptures_version": ref.get("ruptures_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "n_features": int(tsl.get("n_features", self.DGP_K)),
                "n_segments_true": int(self.DGP_SEG),
                "model": self.MODEL,
                "min_size": int(self.MIN_SIZE),
                "penalty": float(tsl.get("penalty", 0.0)),
                "tsl_n_cp": int(tsl.get("n_change_points", 0)),
                "ref_n_cp": int(ref.get("n_change_points", 0)),
            },
        )
