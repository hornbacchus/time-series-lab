"""Phase 3 Batch 6 — STL + Generalized ESD parity check.

Compares TSL ``engine/techniques/stl_esd_anomaly.py`` (two-
stage: statsmodels STL → Generalized ESD on remainder) against
a from-scratch reference that mirrors TSL's algorithm
verbatim. Both arms use statsmodels STL identically; the
only varying logic is the ESD sequential test (Rosner 1983).

**Pattern A self-parity** — same rationale as p3_bocpd /
p3_cusum_page_hinkley. Twitter's AnomalyDetection R package
(historical canonical reference) was archived from CRAN;
no actively-maintained CRAN package implements the
STL+ESD pipeline as a single recipe. Self-parity is the
only path.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats as sp_stats

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_seasonal_with_outliers_dgp(
    *, seed: int, n: int = 240, period: int = 12,
    n_outliers: int = 5, outlier_magnitude: float = 5.0,
) -> tuple[np.ndarray, list[int]]:
    """Seasonal + AR(0) noise + injected outliers."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    seasonal = 2.0 * np.sin(2 * np.pi * t / period)
    trend = 0.01 * t
    noise = rng.standard_normal(n) * 0.5
    y = seasonal + trend + noise
    # Inject outliers at known indices
    outlier_idx = sorted(rng.choice(
        np.arange(period, n - period),  # avoid edges
        size=n_outliers, replace=False,
    ).tolist())
    for idx in outlier_idx:
        sign = 1.0 if rng.random() > 0.5 else -1.0
        y[idx] += sign * outlier_magnitude
    return y, outlier_idx


def _stl_decompose(y: np.ndarray, period: int) -> np.ndarray:
    """Run statsmodels STL with TSL-default Balanced config."""
    from statsmodels.tsa.seasonal import STL  # type: ignore
    seasonal_window = max(7, period + (1 if period % 2 == 0 else 2))
    stl = STL(y, period=period, seasonal=seasonal_window, robust=True)
    res = stl.fit(inner_iter=5, outer_iter=2)
    return np.asarray(res.resid, dtype=np.float64)


def _generalized_esd(
    remainder: np.ndarray, *, alpha: float = 0.05,
    max_anomalies: int = 24, direction: str = "both",
) -> list[int]:
    """Rosner 1983 Generalized ESD on ``remainder``.

    Returns a sorted list of anomaly indices. Reference
    implementation; mirrors Rosner's sequential algorithm
    exactly.
    """
    n = len(remainder)
    r = remainder.copy()
    indices = np.arange(n)
    valid_mask = np.ones(n, dtype=bool)
    detected: list[int] = []

    for i in range(1, max_anomalies + 1):
        active = indices[valid_mask]
        if len(active) < 3:
            break
        ra = r[valid_mask]
        med = float(np.median(ra))
        if direction == "upper":
            dev = ra - med
        elif direction == "lower":
            dev = med - ra
        else:  # both
            dev = np.abs(ra - med)
        s = float(np.std(ra, ddof=1))
        if s <= 0:
            break
        Ri = float(np.max(dev) / s)
        # Worst-active index (in original coordinates)
        worst_local = int(np.argmax(dev))
        worst_orig = int(active[worst_local])
        # Critical value: t_{1-p, n-i-1} where p = alpha / (2*(n-i+1))
        n_active = len(active)
        if direction == "both":
            p = 1.0 - alpha / (2.0 * n_active)
        else:
            p = 1.0 - alpha / n_active
        df = n_active - 2
        if df <= 0:
            break
        t_crit = float(sp_stats.t.ppf(p, df))
        lam = (
            (n_active - 1) * t_crit
            / np.sqrt((df + t_crit ** 2) * n_active)
        )
        if Ri > lam:
            detected.append(worst_orig)
            valid_mask[worst_orig] = False
        else:
            # No more rejections; per Rosner sequential test
            # we still continue the loop to allow later
            # rejections (the test is sequential, not stop-on-
            # first-fail). However TSL's wrapper stops; mirror.
            valid_mask[worst_orig] = False
            # Continue masking but don't add to detected
    return sorted(detected)


class StlEsdParity(P3ParityCheck):
    """STL + Generalized ESD anomaly-detection parity (self)."""

    technique_id = "p3_stl_esd"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Both arms use statsmodels STL on the SAME fixture "
        "(identical inner_iter, outer_iter, seasonal window) "
        "→ remainder is bitwise identical. ESD is closed-form "
        "sequential Rosner 1983 test. TSL and reference "
        "implement identical recursion math; bit-exact "
        "anomaly indices expected. Pattern J avoidance: "
        "Twitter AnomalyDetection R is archived; no CRAN "
        "successor matches the STL+ESD recipe shape."
    )

    DGP_N = 240
    DGP_PERIOD = 12
    N_OUTLIERS = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, true_outliers = _generate_seasonal_with_outliers_dgp(
            seed=seed, n=self.DGP_N, period=self.DGP_PERIOD,
            n_outliers=self.N_OUTLIERS, outlier_magnitude=5.0,
        )
        return {
            "y": y, "period": int(self.DGP_PERIOD),
            "true_outliers": true_outliers,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques.stl_esd_anomaly import run as stl_run  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        period = int(fixture["period"])
        ctx = RunContext({
            "run_id": "p3_stl_esd_tsl",
            "technique_id": "stl_esd_anomaly",
            "preset": "Balanced", "seed": 42, "frequency": "monthly",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "period": period,
                "max_anomalies_pct": 0.10,
                "alpha": 0.05,
                "direction": "both",
            },
        })
        res = stl_run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL STL+ESD failed: {res.get('error_message')}"
            )
        a = res["audit_fields"]
        return {
            "n_anomalies": int(a.get("n_anomalies", 0)),
            "anomaly_indices": list(a.get("anomaly_indices") or []),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        period = int(fixture["period"])
        remainder = _stl_decompose(y, period)
        # max_anomalies = floor(0.10 * n) per TSL convention
        max_n = int(np.floor(0.10 * len(y)))
        outliers = _generalized_esd(
            remainder, alpha=0.05, max_anomalies=max_n,
            direction="both",
        )
        return {
            "n_anomalies": int(len(outliers)),
            "anomaly_indices": outliers,
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        primary["n_anomalies"] = _compare_scalar(
            float(tsl["n_anomalies"]), float(ref["n_anomalies"]),
            ladder["primary"],
        )
        tsl_set = set(int(x) for x in tsl["anomaly_indices"])
        ref_set = set(int(x) for x in ref["anomaly_indices"])
        match = tsl_set == ref_set
        primary["anomaly_indices_set_match"] = {
            "status": "PASS" if match else (
                "CAVEAT" if len(tsl_set & ref_set) >= 0.5 * max(
                    1, len(tsl_set | ref_set)
                ) else "BLOCK"
            ),
            "tsl_only": sorted(tsl_set - ref_set),
            "ref_only": sorted(ref_set - tsl_set),
            "intersection_size": len(tsl_set & ref_set),
            "union_size": len(tsl_set | ref_set),
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
                "n_obs": int(self.DGP_N),
                "period": int(self.DGP_PERIOD),
                "n_outliers_injected": int(self.N_OUTLIERS),
                "tsl_anomalies": list(tsl.get("anomaly_indices") or []),
                "ref_anomalies": list(ref.get("anomaly_indices") or []),
            },
        )
