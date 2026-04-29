"""Phase 3 Batch 10 — LOESS interpolation parity check.

TSL ``loess_interpolation.py`` (statsmodels.nonparametric.lowess)
vs direct statsmodels.lowess (same-library self-test).
Pattern A bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_lowess_dgp(*, seed: int, n: int = 200) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 10, n)
    y = np.sin(x) + 0.3 * rng.standard_normal(n)
    return x, y


class LoessParity(P3ParityCheck):
    technique_id = "p3_loess"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "statsmodels.nonparametric.lowess is deterministic given "
        "identical inputs + frac. Same-library self-test."
    )
    DGP_N = 200
    FRAC = 0.3

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_lowess_dgp(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def _smooth(self, fixture: dict[str, Any]) -> dict[str, Any]:
        from statsmodels.nonparametric.smoothers_lowess import (  # type: ignore
            lowess,
        )
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        out = lowess(y, x, frac=self.FRAC, return_sorted=True)
        # out shape (n, 2): [:, 0] = sorted x, [:, 1] = smoothed y
        return {"smoothed_y": out[:, 1].astype(np.float64)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._smooth(fixture)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import statsmodels  # type: ignore
        out = self._smooth(fixture)
        out["statsmodels_version"] = statsmodels.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "smoothed_y": _compare_vector(
                tsl["smoothed_y"], ref["smoothed_y"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "frac": float(self.FRAC),
                "statsmodels_version": ref.get("statsmodels_version", "unknown"),
            },
        )
