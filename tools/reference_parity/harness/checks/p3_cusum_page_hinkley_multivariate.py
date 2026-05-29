"""ENG-EXT-CHANGEPOINT-001 A1b — multivariate (joint) CUSUM/Page-Hinkley
parity check.

Compares TSL ``engine/techniques/cusum_page_hinkley.py`` MULTIVARIATE
path (auto-detected for >=2 input series) against a FROM-SCRATCH
reimplementation of the IDENTICAL formulation. No library exists for
multivariate CUSUM, so this is a SELF-PARITY check (the S85/C3 fallback):
both arms implement the proper Crosier (1988) MCUSUM (shrinking vector
accumulator on Σ⁻¹-standardized deviations) + a joint Page-Hinkley on the
running-mean-centered Mahalanobis distance, with bootstrap-calibrated
alarm thresholds (no-reset null-max 95th percentile, seeded). Both are
deterministic given the seed → bit-exact joint change-point set.

IDENTICAL-FORMULATION discipline (load-bearing, the A1a identical-penalty
analog in self-parity form): the reference reimplements the engine's EXACT
formulation — same Σ (np.cov + UNCONDITIONAL pinv), same target (mean
vector), same k_m=0.5 allowance, same ph_delta, same bootstrap
(np.random.seed(seed) then n_boot row-permutations, no-reset null max,
95th percentile), same detection (reset-at-calibrated-threshold), same
NaN row-drop. Any divergence breaks the bit-match for a convention
reason, not an implementation bug.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_joint_shift_dgp(
    *, seed: int, n: int = 400, k: int = 3, shift: float = 2.0,
    sigma: float = 1.0,
) -> np.ndarray:
    """Multivariate (n, k) signal: all k curve points shift mean JOINTLY
    at t = n/2 (a curve-wide coordinated regime shift)."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, k)) * sigma
    X[n // 2:, :] += shift
    return X


# ---- Reference (from-scratch) Crosier MCUSUM + joint Page-Hinkley ----
# Mirrors engine/techniques/cusum_page_hinkley.py::_run_multivariate EXACTLY.

def _ref_multivariate(X, preset, seed):
    np.random.seed(seed)  # mirror engine np.random.seed(ctx.seed)
    significance = 0.05
    k_m = 0.5
    ph_delta = 0.005
    n, k = X.shape
    target = X.mean(axis=0)
    Sigma = np.atleast_2d(np.cov(X, rowvar=False))
    Sigma_inv = np.linalg.pinv(Sigma)
    Z = X - target

    def maha(row):
        z = row - target
        q = float(z @ Sigma_inv @ z)
        return float(np.sqrt(q)) if q > 0 else 0.0

    def crosier(Zmat, reset_h):
        Sv = np.zeros(Zmat.shape[1])
        yv = np.zeros(len(Zmat))
        alarms = []
        for t in range(len(Zmat)):
            cand = Sv + Zmat[t]
            C = float(np.sqrt(cand @ Sigma_inv @ cand))
            Sv = np.zeros(Zmat.shape[1]) if C <= k_m else cand * (1.0 - k_m / C)
            yv[t] = float(np.sqrt(Sv @ Sigma_inv @ Sv))
            if reset_h is not None and yv[t] > reset_h:
                alarms.append(t)
                Sv = np.zeros(Zmat.shape[1])
                yv[t] = 0.0
        return yv, alarms

    def mph(Dvec, lam):
        PHv = np.zeros(len(Dvec))
        alarms = []
        acc = 0.0
        run_min = 0.0
        rm = 0.0
        for t in range(len(Dvec)):
            rm = (rm * t + Dvec[t]) / (t + 1)
            acc += (Dvec[t] - rm - ph_delta)
            run_min = min(run_min, acc)
            PHv[t] = acc - run_min
            if lam is not None and PHv[t] > lam and t > 10:
                alarms.append(t)
        return PHv, alarms

    D = np.array([maha(X[t]) for t in range(n)], dtype=float)
    mv_nboot = {"Fast": 200, "Balanced": 500, "Thorough": 2000}.get(preset, 500)
    cusum_maxes = np.zeros(mv_nboot)
    ph_maxes = np.zeros(mv_nboot)
    for b in range(mv_nboot):
        perm = np.random.permutation(n)
        yv_b, _ = crosier(Z[perm], None)
        cusum_maxes[b] = float(np.max(yv_b)) if len(yv_b) else 0.0
        PHv_b, _ = mph(D[perm], None)
        ph_maxes[b] = float(np.max(PHv_b)) if len(PHv_b) else 0.0
    h_cal = float(np.percentile(cusum_maxes, (1 - significance) * 100))
    lambda_cal = float(np.percentile(ph_maxes, (1 - significance) * 100))

    _, mcusum_alarms = crosier(Z, h_cal)
    _, mph_alarms = mph(D, lambda_cal)
    joint = sorted(set(mcusum_alarms) | set(mph_alarms))
    return {
        "change_points": [i + 1 for i in joint],
        "n_change_points": len(joint),
        "n_mcusum_alarms": len(mcusum_alarms),
        "n_mph_alarms": len(mph_alarms),
        "h_cal": h_cal,
        "lambda_cal": lambda_cal,
    }


class CusumPageHinkleyMultivariateParity(P3ParityCheck):
    """Multivariate (joint) Crosier MCUSUM / Page-Hinkley parity
    (from-scratch self-test)."""

    technique_id = "p3_cusum_page_hinkley_multivariate"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Multivariate Crosier MCUSUM + joint Page-Hinkley "
        "(ENG-EXT-CHANGEPOINT-001 A1b) — deterministic sequential "
        "detection with seeded bootstrap-calibrated thresholds. No "
        "library exists, so the reference is a from-scratch "
        "reimplementation of the IDENTICAL formulation; bit-exact joint "
        "change-point set given identical input + seed. Failure = a "
        "formulation/Σ/threshold/NaN convention divergence between arms."
    )

    DGP_N = 400
    DGP_K = 3
    PRESET = "Balanced"
    SEED = 42

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"X": _generate_joint_shift_dgp(
            seed=seed, n=self.DGP_N, k=self.DGP_K,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques.cusum_page_hinkley import run as cph_run  # type: ignore

        X = np.asarray(fixture["X"], dtype=np.float64)
        n, k = X.shape
        ctx = RunContext({
            "run_id": "p3_cph_mv_tsl",
            "technique_id": "cusum_page_hinkley",
            "preset": self.PRESET, "seed": self.SEED, "frequency": "irregular",
            "time": list(range(n)),
            "series": [
                {"name": f"t{j}", "values": X[:, j].tolist()} for j in range(k)
            ],
            "params": {},
        })
        res = cph_run(ctx, lambda *a, **kw: None)
        if res.get("status") != "success":
            raise RuntimeError(f"TSL multivariate CUSUM/PH failed: {res.get('error_message')}")
        a = res["audit_fields"]
        if a.get("mode") != "multivariate":
            raise RuntimeError(f"Expected multivariate mode, got {a.get('mode')!r}.")
        return {
            "change_points": sorted(int(x) for x in (a.get("change_point_positions") or [])),
            "n_change_points": int(a.get("n_change_points", 0)),
            "n_mcusum_alarms": int(a.get("n_mcusum_alarms", 0)),
            "n_mph_alarms": int(a.get("n_mph_alarms", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        X = np.asarray(fixture["X"], dtype=np.float64)
        ref = _ref_multivariate(X, self.PRESET, self.SEED)
        ref["change_points"] = sorted(int(x) for x in ref["change_points"])
        return ref

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
                "n_obs": int(self.DGP_N),
                "n_features": int(self.DGP_K),
                "tsl_n_cp": int(tsl.get("n_change_points", 0)),
                "ref_n_cp": int(ref.get("n_change_points", 0)),
                "tsl_n_mcusum": int(tsl.get("n_mcusum_alarms", 0)),
                "ref_n_mcusum": int(ref.get("n_mcusum_alarms", 0)),
                "ref_h_cal": round(float(ref.get("h_cal", 0.0)), 4),
            },
        )
