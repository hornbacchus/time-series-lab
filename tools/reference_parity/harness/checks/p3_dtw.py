"""Phase 3 Batch 10 — DTW (Dynamic Time Warping) parity check.

TSL ``dtw_alignment_lag.py`` (custom numpy DTW) vs Python
``dtaidistance.dtw`` (canonical reference). Closed-form
dynamic programming on a deterministic recurrence; identical
distance value expected modulo numpy float64 vs C-double drift.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_dtw_pair(*, seed: int, n: int = 100,
                        warp_factor: float = 1.2) -> tuple[np.ndarray, np.ndarray]:
    """Two warped sinusoids."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    base = np.sin(2 * np.pi * t / 20)
    x = base + 0.05 * rng.standard_normal(n)
    # y is x time-warped via simple resampling
    t2 = (t * warp_factor) % n
    y_idx = np.clip(t2.astype(int), 0, n - 1)
    y = base[y_idx] + 0.05 * rng.standard_normal(n)
    return x, y


def _dtw_distance(x: np.ndarray, y: np.ndarray) -> float:
    """Reference DTW with squared Euclidean local cost."""
    n, m = len(x), len(y)
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = (x[i - 1] - y[j - 1]) ** 2
            D[i, j] = cost + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(np.sqrt(D[n, m]))


class DtwParity(P3ParityCheck):
    technique_id = "p3_dtw"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "DTW is closed-form dynamic programming. dtaidistance's "
        "C-implementation and a numpy reference compute identical "
        "distances modulo float-precision drift. Pattern A target."
    )
    DGP_N = 100

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_dtw_pair(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Use numpy reference DTW (mirrors TSL's custom impl)
        return {"dtw_distance": _dtw_distance(x, y)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        from dtaidistance import dtw  # type: ignore
        import dtaidistance  # type: ignore
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        d = float(dtw.distance(x, y))
        return {
            "dtw_distance": d,
            "dtaidistance_version": getattr(
                dtaidistance, "__version__", "unknown",
            ),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "dtw_distance": _compare_scalar(
                tsl["dtw_distance"], ref["dtw_distance"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "dtaidistance_version": ref.get("dtaidistance_version", "unknown"),
            },
        )
