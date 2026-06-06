"""Phase 7+ deeper-validation, scope-extension UNIT 5 (FINAL T1-core) —
dtw_alignment_lag DTW-distance CROSS-PACKAGE parity check (additive;
``p3_dtw`` unchanged).

★ COVERAGE CORRECTION of a standing OVERSTATEMENT. The engine's DTW distance
had never been validated against an independent library with the engine in the
loop:
  (i)  pre-rewrite, ``p3_dtw`` compared a HARNESS ``_dtw_distance`` vs
       ``dtaidistance.dtw.distance`` with the ENGINE BYPASSED (degenerate
       self-parity);
  (ii) the SC8 rewrite put the engine in the loop but SWAPPED dtaidistance for
       a from-scratch self-reimpl (to cover Layer 2 + Layer 3) — so the engine's
       DTW distance has been SELF-PARITY ONLY;
  (iii)the §2.5 "Pattern A cross-package bit-exact Layer 1" verdict was therefore
       degenerate/superseded — corrected here.
This check provides the FIRST engine-in-the-loop cross-package distance evidence:
engine ``dtw_alignment_lag.run()`` (via RunContext) vs INLINE
``dtaidistance.dtw.distance`` on the engine's z-normalized series at the matched
Sakoe-Chiba window. (``p3_dtw``'s self-parity reimpl is left UNCHANGED — it
legitimately covers the engine-specific lag/warp downstream.)

B.i — single cross-package primitive (the DTW distance); the lag is an
argmin over the warp (trivial, downstream/self-parity). Third case REJECTED on
the denton boundary: the distance has a full cross-package reference, so the
cross-package carries the discrimination — no defining-invariant arm (the
warp-path monotonicity/boundary is structural-by-construction, tautological).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks.p3_dtw import _generate_dtw_pair
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_DGP_N = 100


def _znorm(a: np.ndarray) -> np.ndarray:
    """Engine z-normalization: (a - mean) / std (ddof=0)."""
    s = float(np.std(a))
    return (a - float(np.mean(a))) / s if s > 1e-10 else a


class DtwCrossPkgParity(P3ParityCheck):
    """Engine-invoked DTW distance vs the independent dtaidistance library —
    the first engine-in-the-loop cross-package evidence (corrects the prior
    degenerate/superseded 'cross-package Layer 1' claim)."""

    technique_id = "p3_dtw_crosspkg"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "DTW distance is closed-form dynamic programming (squared-euclidean "
        "local cost + min(diag,ins,del) recurrence + sqrt). The engine's "
        "hand-rolled _dtw and dtaidistance compute the identical standard DTW "
        "given matched z-normalization + Sakoe-Chiba window; measured bit-exact "
        "at the engine's 4-dp emitted precision (3.87e-05). B.i: the distance "
        "is the single cross-package primitive; the lag is argmin-trivial and "
        "the warp downstream is engine-specific (self-parity, p3_dtw). This is "
        "the FIRST engine-in-the-loop cross-package distance evidence — the "
        "prior p3_dtw 'cross-package' arm bypassed the engine, then was "
        "superseded by a self-reimpl."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_dtw_pair(seed=seed, n=_DGP_N)
        return {"x": np.asarray(x, float), "y": np.asarray(y, float)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.dtw_alignment_lag as dtw_mod  # type: ignore
        x, y = fixture["x"], fixture["y"]
        ctx = RunContext({
            "run_id": "p3_dtw_crosspkg", "technique_id": "dtw_alignment_lag",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(x))),
            "series": [{"name": "x", "values": x.tolist()},
                       {"name": "y", "values": y.tolist()}],
            "params": {},
        })
        resp = dtw_mod.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine dtw failed: {resp.get('error_message')}")
        au = resp.get("audit_fields", {})
        return {"dtw_distance": float(au["dtw_distance"]),
                "window_frac": float(au.get("window_frac", 0.20))}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        from dtaidistance import dtw as dtai  # type: ignore
        x, y = fixture["x"], fixture["y"]
        # Match the engine: drop NaN (none here), z-normalize, Sakoe-Chiba window.
        xn, yn = _znorm(x), _znorm(y)
        # Balanced preset window_frac=0.20; Sakoe-Chiba half-width on the
        # working series (n=100, no subsample). Probe-verified non-binding.
        w = max(1, int(0.20 * max(len(xn), len(yn))))
        d = float(dtai.distance(xn, yn, window=w, use_c=False))
        # Negative control: skip the engine's z-normalization (raw series).
        d_raw = float(dtai.distance(x, y, window=w, use_c=False))
        return {"dtai_distance": d, "control_raw_distance": d_raw, "window": int(w)}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["dtw_distance"] = _compare_scalar(
            tsl["dtw_distance"], ref["dtai_distance"], ladder["primary"])
        statuses.append(primary["dtw_distance"]["status"])

        # Discrimination guard (always-on): the z-norm negative control must
        # diverge — confirms the cross-package is sensitive to the preprocessing
        # / metric match (a wrong build is caught), not vacuously passing.
        control_gap = abs(tsl["dtw_distance"] - ref["control_raw_distance"])
        disc = control_gap > 10 * float(ladder["primary"]["abs_tol"])
        primary["discrimination"] = {
            "status": "PASS" if disc else "BLOCK",
            "control_raw_gap": round(control_gap, 6), "discriminates": bool(disc)}
        statuses.append(primary["discrimination"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "reference": "dtaidistance.dtw.distance (cross-package)",
                "engine_invoked": True,
                "dtw_distance_abs_diff": primary["dtw_distance"]["abs_diff"],
                "matched_window": ref["window"],
                "control_raw_gap": round(control_gap, 6),
                "note": ("first engine-in-the-loop cross-package DTW distance "
                         "evidence; corrects the prior degenerate/superseded "
                         "'cross-package Layer 1' claim"),
            },
        )
