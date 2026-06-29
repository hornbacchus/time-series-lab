"""Phase 4b + Item 4 — confidence_level exposure/harmonization discrimination (9 techniques).

The CI band level was engine-read but catalog-absent: block_bootstrap,
gaussian_process_forecast, kalman_imputation, rolling_origin_cv read
`confidence_level` (0.95); local_level, local_linear_trend read `alpha` (0.05).
Phase 4b exposes ONE harmonized control -- `confidence_level` -- on those 6 (the two
alpha-keyed ones translate engine-side: alpha = 1 - confidence_level). Item 4 extends
the same harmonization to the last 3 CI-band stragglers: kalman_filter +
kalman_smoother (the alpha=1-confidence_level translation in the SHARED resolver --
byte-identical at confidence_level 0.90) and conformal_intervals (a catalog-only
rename from `coverage`, the engine already read confidence_level).

This check proves: (1) each control has effect (0.95 vs 0.99 output differs); and
(2) ★ the band gets WIDER at a higher confidence (0.99 band width > 0.95) wherever
a band is extractable -- the direction/inversion guard (a higher confidence_level
must mean a WIDER interval; if the alpha translation were inverted it would
NARROW, the lomb-inversion lesson). rolling_origin_cv's band shape isn't a simple
lower/upper table -> effect-only (it's a direct confidence_level read, no
translation, so no inversion risk).
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _digest(res: dict) -> str:
    vals = []
    for t in res.get("tables", []) or []:
        for row in t.get("rows", []) or []:
            for c in row:
                if isinstance(c, (int, float)) and not isinstance(c, bool):
                    vals.append(round(float(c), 5))
    return hashlib.sha1(",".join(map(str, vals)).encode()).hexdigest()[:12]


def _ci_width(res: dict):
    for tb in res.get("tables", []) or []:
        cols = [str(c).lower() for c in (tb.get("columns") or [])]
        lo = [i for i, c in enumerate(cols) if "lower" in c]
        up = [i for i, c in enumerate(cols) if "upper" in c]
        if lo and up:
            w = [abs(r[up[0]] - r[lo[0]]) for r in tb.get("rows", []) or []
                 if isinstance(r[lo[0]], (int, float)) and isinstance(r[up[0]], (int, float))]
            if w:
                return float(np.mean(w))
    return None


class ConfidenceLevelExposureParity(P3ParityCheck):
    technique_id = "p3_confidence_level_exposure"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Knob-gap exposure + harmonization: the newly-exposed confidence_level "
        "control must change the output and (where a band is extractable) WIDEN "
        "it at higher confidence -- guarding the alpha=1-confidence_level "
        "translation against inversion. No effect / wrong direction -> BLOCK."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(5)
        n, t = 140, np.arange(140)
        y = (50 + 0.1 * t + 6 * np.sin(2 * np.pi * t / 12) + rng.standard_normal(n) * 1.5).tolist()
        ymiss = list(y)
        for i in (20, 55, 90, 120):
            ymiss[i] = float("nan")
        return {"y": y, "ymiss": ymiss}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques import registry  # type: ignore
        import importlib

        def run(tid, vals, cl):
            mod = importlib.import_module(registry.TECHNIQUE_REGISTRY[tid])
            nn = len(vals)
            tcol = [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01" for i in range(nn)]
            ctx = RunContext({"run_id": "p3_cl", "technique_id": tid, "preset": "Balanced",
                              "seed": 42, "frequency": "M", "time": tcol,
                              "series": [{"name": "y", "values": vals}],
                              "params": {"confidence_level": cl}})
            return mod.run(ctx, lambda *a, **k: None)

        y, ymiss = fixture["y"], fixture["ymiss"]
        techs = ["block_bootstrap", "gaussian_process_forecast", "kalman_imputation",
                 "rolling_origin_cv", "local_level", "local_linear_trend",
                 # Item 4 -- the harmonized CI-band controls (both kalman twins +
                 # conformal). kalman reads confidence_level in the SHARED
                 # _resolve_params (alpha = 1 - confidence_level); conformal already
                 # read confidence_level (catalog-only rename from `coverage`).
                 "kalman_filter", "kalman_smoother", "conformal_intervals"]
        # Per-technique inversion-guard contrast (default 0.95 vs 0.99). conformal uses
        # 0.50 vs 0.95: split-conformal's distribution-free width SATURATES at high
        # confidence with a finite calibration set (the empirical quantile clamps to the
        # max calibration residual -- a CORRECT finite-sample property, NOT inertness),
        # so the guard must test the responsive range, not the 0.95/0.99 plateau.
        contrast = {"conformal_intervals": (0.50, 0.95)}
        out = {}
        for tid in techs:
            vals = ymiss if tid == "kalman_imputation" else y
            lo, hi = contrast.get(tid, (0.95, 0.99))
            r_lo, r_hi = run(tid, vals, lo), run(tid, vals, hi)
            w_lo, w_hi = _ci_width(r_lo), _ci_width(r_hi)
            out[tid] = {
                "ok": r_lo.get("status") == "success" and r_hi.get("status") == "success",
                "differs": _digest(r_lo) != _digest(r_hi),
                "wider": (None if (w_lo is None or w_hi is None) else bool(w_hi > w_lo)),
            }
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {"expected": "confidence_level changes output; band widens at higher confidence"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary = {}
        for tid, r in tsl.items():
            # effect required; direction required only where a band is extractable
            passed = r["ok"] and r["differs"] and (r["wider"] in (True, None))
            primary[tid] = {"status": "PASS" if passed else "BLOCK",
                            "differs": r["differs"], "band_wider_at_0.99": r["wider"]}
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(technique_id=self.technique_id, outcome=outcome,
                            metrics={"primary": primary}, diagnostics={"n": len(tsl)})
