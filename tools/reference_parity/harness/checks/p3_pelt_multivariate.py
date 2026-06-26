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

★ FUNCTIONAL LAYER (self-parity (F) upgrade): same-library bit-exact
parity proves DETERMINISM, not that the joint detector FUNCTIONS. So a
defining-invariant functional check runs the ENGINE (default penalty,
the user path) on a multivariate series with a KNOWN JOINT break and
asserts the detected joint change points land near the true breaks, AND
on a flat no-break multivariate series asserts the detector stays quiet.
Verified-discriminating: a fires-everywhere bug fails the control, a
never-fires bug fails the structured arm.
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

    # Functional layer (§5.1): structured fixture with a KNOWN JOINT break
    # + flat negative control. FN_SHIFT large enough to be unambiguous
    # (pre-flight: engine recovers exactly [200, 400] at default penalty;
    # flat -> 0).
    FN_SHIFT = 8.0
    FN_TRUE_BREAKS = (200, 400)
    FN_WINDOW = 15
    # Negative-control guard: catch GROSS over-firing, not the modest
    # BIC false-positive rate (see p3_pelt calibration: working 0-5,
    # broken 63). <=10 is verified-discriminating.
    FN_FLAT_MAX = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(seed + 7)
        a, b = self.FN_TRUE_BREAKS
        struct = rng.standard_normal((self.DGP_N, self.DGP_K))
        struct[a:b, :] += self.FN_SHIFT  # joint shift across all features
        flat = rng.standard_normal((self.DGP_N, self.DGP_K))
        return {
            "X": _generate_joint_mean_shift_dgp(
                seed=seed, n=self.DGP_N, k=self.DGP_K, n_segments=self.DGP_SEG,
            ),
            "X_struct": struct,
            "X_flat": flat,
        }

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

        # --- Functional layer: run the ENGINE (default penalty) on the
        # structured + flat multivariate fixtures.
        def _engine_mv_cps(Xarr: np.ndarray) -> list[int]:
            nn, kk = Xarr.shape
            fctx = RunContext({
                "run_id": "p3_pelt_mv_fn",
                "technique_id": "pelt_change_points",
                "preset": "Balanced", "seed": 42, "frequency": "irregular",
                "time": list(range(nn)),
                "series": [
                    {"name": f"t{j}", "values": Xarr[:, j].tolist()}
                    for j in range(kk)
                ],
                "params": {},  # engine default penalty resolution
            })
            fr = pelt_run(fctx, lambda *_a, **_k: None)
            fa = fr.get("audit_fields", {}) if fr.get("status") == "success" else {}
            return sorted(int(x) - 1 for x in (fa.get("change_point_positions") or []))

        struct_cps = _engine_mv_cps(np.asarray(fixture["X_struct"], dtype=np.float64))
        flat_cps = _engine_mv_cps(np.asarray(fixture["X_flat"], dtype=np.float64))
        return {
            "n_change_points": int(a.get("n_change_points", 0)),
            "change_points": sorted(cps_0indexed),
            "penalty": pen,
            "n_features": int(a.get("n_features", k)),
            "functional": {
                "true_breaks": list(self.FN_TRUE_BREAKS),
                "window": self.FN_WINDOW,
                "struct_cps": struct_cps,
                "struct_n": len(struct_cps),
                "flat_n": len(flat_cps),
            },
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
        # --- Functional layer (§5.1): the joint detector must FIRE near
        # the known joint breaks AND stay quiet on the flat control.
        # Verified-discriminating; a BLOCK = a real engine defect.
        fn = tsl.get("functional", {})
        true_breaks = fn.get("true_breaks", [])
        win = int(fn.get("window", self.FN_WINDOW))
        struct_cps = fn.get("struct_cps", [])
        hits = [b for b in true_breaks
                if any(abs(c - b) <= win for c in struct_cps)]
        detects = (len(hits) == len(true_breaks)
                   and fn.get("struct_n", 0) >= len(true_breaks))
        primary["functional_detects_joint_breaks"] = {
            "status": "PASS" if detects else "BLOCK",
            "true_breaks": true_breaks, "detected": struct_cps,
            "hits_within_window": hits, "window": win,
        }
        flat_n = int(fn.get("flat_n", 99))
        primary["functional_negative_control"] = {
            "status": "PASS" if flat_n <= self.FN_FLAT_MAX else "BLOCK",
            "flat_n_change_points": flat_n,
            "max_tolerated": self.FN_FLAT_MAX,
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
