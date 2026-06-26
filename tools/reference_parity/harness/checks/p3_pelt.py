"""Phase 3 Batch 6 — PELT change-point parity check.

Compares TSL ``engine/techniques/pelt_change_points.py``
(``ruptures.Pelt``) against direct ``ruptures.Pelt``
invocation on a synthetic mean-shift fixture.

This is a SAME-LIBRARY parity check: both arms call
``ruptures.Pelt(model="l2", min_size=5, jump=1).fit(y).predict(pen=p)``
with identical arguments. Pattern A bit-exact target;
divergence indicates a TSL preprocessing or argument-handling
bug, not a methodology difference.

★ FUNCTIONAL LAYER (self-parity (F) upgrade): same-library bit-exact
parity proves DETERMINISM, not that the detector FUNCTIONS (the BOCPD
scar -- a detector that passed self-parity while never firing). So a
defining-invariant functional check runs the ENGINE (default penalty,
the user path) on a structured series with KNOWN injected breaks and
asserts the detected change points land near the true breaks, AND on a
flat no-break series asserts the detector stays quiet. The pair is
verified-discriminating: a broken detector that fires everywhere fails
the negative control; one that never fires fails the structured arm.
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

    # Functional layer (§5.1): structured fixture with KNOWN breaks +
    # flat negative control. FN_SHIFT is large enough that the breaks are
    # unambiguously detectable (pre-flight: engine recovers exactly
    # [200, 400] at default penalty; flat -> 0).
    FN_SHIFT = 8.0
    FN_TRUE_BREAKS = (200, 400)
    FN_WINDOW = 15        # +/- samples a detected CP may fall from a true break
    # Negative-control guard: catch GROSS over-firing, not the modest
    # false-positive rate intrinsic to a BIC penalty. Calibration (16
    # seeds): a working detector gives 0-5 false CPs on 600 noise samples
    # (mean 2.1); a broken too-liberal detector (penalty=1) gives 63. The
    # <=10 guard sits cleanly between -> verified-discriminating.
    FN_FLAT_MAX = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(seed + 7)
        a, b = self.FN_TRUE_BREAKS
        struct = np.concatenate([
            rng.standard_normal(a),
            self.FN_SHIFT + rng.standard_normal(b - a),
            rng.standard_normal(self.DGP_N - b),
        ])
        flat = rng.standard_normal(self.DGP_N)
        return {
            "y": _generate_mean_shift_dgp(
                seed=seed, n=self.DGP_N, n_segments=self.DGP_K,
            ),
            "y_struct": struct,
            "y_flat": flat,
        }

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

        # --- Functional layer: run the ENGINE with DEFAULT penalty (the
        # user-facing path) on the structured + flat fixtures.
        def _engine_cps(vals: list[float]) -> list[int]:
            fctx = RunContext({
                "run_id": "p3_pelt_fn",
                "technique_id": "pelt_change_points",
                "preset": "Balanced", "seed": 42, "frequency": "irregular",
                "time": list(range(len(vals))),
                "series": [{"name": "y", "values": list(vals)}],
                "params": {},  # engine default penalty resolution
            })
            fr = pelt_run(fctx, lambda *_a, **_k: None)
            fa = fr.get("audit_fields", {}) if fr.get("status") == "success" else {}
            return sorted(int(x) - 1 for x in (fa.get("change_point_positions") or []))

        struct_cps = _engine_cps(list(fixture["y_struct"]))
        flat_cps = _engine_cps(list(fixture["y_flat"]))
        return {
            "n_change_points": int(a.get("n_change_points", 0)),
            "change_points": sorted(cps_0indexed),
            "penalty": pen,
            "functional": {
                "true_breaks": list(self.FN_TRUE_BREAKS),
                "window": self.FN_WINDOW,
                "struct_cps": struct_cps,
                "struct_n": len(struct_cps),
                "flat_n": len(flat_cps),
            },
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
        # --- Functional layer (§5.1): the detector must FIRE near the
        # known breaks AND stay quiet on the flat control. The pair is
        # verified-discriminating (a fires-everywhere or never-fires bug
        # fails one arm). A BLOCK here = a real engine defect, NOT a
        # tolerance to tune (the BOCPD precedent).
        fn = tsl.get("functional", {})
        true_breaks = fn.get("true_breaks", [])
        win = int(fn.get("window", self.FN_WINDOW))
        struct_cps = fn.get("struct_cps", [])
        hits = [b for b in true_breaks
                if any(abs(c - b) <= win for c in struct_cps)]
        detects = (len(hits) == len(true_breaks)
                   and fn.get("struct_n", 0) >= len(true_breaks))
        primary["functional_detects_breaks"] = {
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
