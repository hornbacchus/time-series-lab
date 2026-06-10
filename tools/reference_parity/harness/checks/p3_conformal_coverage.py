"""Inert-control fix #5 — conformal_intervals coverage discrimination (B-alias).

★ `coverage` (the "Coverage" dialog control, float, default 0.95) was INERT —
the engine read `confidence_level` (which the dialog never sends), so the
user's coverage setting was silently dropped (intervals always at 0.95). Now
engine-wired as a CLEAN ALIAS: `confidence_level = get_param("confidence_level",
get_param("coverage", 0.95))` — identity CONFIRMED from the engine (not
assumed): confidence_level IS the target coverage (the nominal interval LEVEL;
the miscoverage alpha = 1 - level conversion is internal, downstream of the
read), same scale (both 0.95 fractions), same direction (neither is alpha).
The single read point feeds all three conformal methods (split/CQR/EnbPI). The
DEFAULT (coverage=0.95 == native default) is byte-identical -> p3_conformal +
p3_conformal_cqr + p3_conformal_enbpi all PASS unchanged (the inverted-gate
sentinels, which pass confidence_level natively and win via precedence).

★ Directional + SATURATION-TOLERANT design: higher coverage -> WIDER intervals.
On a finite calibration set the empirical quantile ceil((n_cal+1)(1-alpha))/n_cal
saturates at the max residual, so the 0.95->0.99 step can be tiny. The check:
 - STRICT lower step  : w(0.90) < w(0.95) by a margin
 - NON-STRICT top step: w(0.99) >= w(0.95) (tolerates ONLY the saturation
   plateau)
 - HARD spread margin : w(0.99) - w(0.90) >= min_spread (measured 0.816)
This still catches BOTH failure modes: an INERT engine -> identical widths ->
the hard spread BLOCKs; a COMPLEMENT-backwards wiring (coverage read as alpha)
-> w(0.90) wider than w(0.99) -> the strict lower step FAILS.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 200
_HORIZON = 6


def _dgp(seed: int):
    rng = np.random.default_rng(seed)
    return (np.cumsum(rng.standard_normal(_N) * 0.5)
            + 10.0 * np.sin(np.arange(_N) * 2.0 * np.pi / 12.0) + 50.0)


class ConformalCoverageParity(P3ParityCheck):
    """conformal coverage is LIVE: drives confidence_level (clean alias) ->
    monotone-wider intervals; default byte-identical."""

    technique_id = "p3_conformal_coverage"
    tier = "fast"
    fixture_id = ""

    verdict_class = "conformal_coverage"
    verdict_class_rationale = (
        "Split-conformal interval width is the deterministic empirical-quantile "
        "of calibration residuals at ceil((n_cal+1)(1-alpha))/n_cal given the "
        "seeded base forecaster. Validates the engine-wired `coverage` dialog "
        "control (a clean same-quantity alias of confidence_level -- the LEVEL, "
        "not alpha) is LIVE + DIRECTIONAL: higher coverage -> wider intervals, "
        "with a saturation-tolerant top step (finite-calibration quantile "
        "plateau) and a hard 0.90<->0.99 spread margin. The default "
        "(coverage=0.95 == native) is byte-identical (sentinels = p3_conformal "
        "+ p3_conformal_cqr + p3_conformal_enbpi). Engine-wiring fix."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _dgp(seed)}

    def _engine(self, y, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.conformal_intervals as ci  # type: ignore
        ctx = RunContext({
            "run_id": "p3_conformal_coverage", "technique_id": "conformal_intervals",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": _HORIZON, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = ci.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine conformal failed: {r.get('error_message')}")
        au = r["audit_fields"]
        width = None
        for t in r.get("tables", []):
            cols = [str(c).lower() for c in t.get("columns", [])]
            lo_i = [i for i, c in enumerate(cols) if "lower" in c]
            hi_i = [i for i, c in enumerate(cols) if "upper" in c]
            if lo_i and hi_i:
                lo = np.array([float(rr[lo_i[0]]) for rr in t["rows"]])
                hi = np.array([float(rr[hi_i[0]]) for rr in t["rows"]])
                width = float(np.mean(hi - lo))
                break
        if width is None:
            raise RuntimeError("no interval table found")
        return {"cl": float(au["confidence_level"]), "width": width}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        return {
            "default": self._engine(y, {}),
            "c90": self._engine(y, {"coverage": 0.90}),
            "c95": self._engine(y, {"coverage": 0.95}),
            "c99": self._engine(y, {"coverage": 0.99}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"cl_tol": float(ladder["default"]["abs_tol"]),
                "min_lower_step": float(ladder["discrimination"]["min_lower_step"]),
                "min_spread": float(ladder["discrimination"]["min_spread"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        d, c90, c95, c99 = tsl["default"], tsl["c90"], tsl["c95"], tsl["c99"]
        tol = ref["cl_tol"]

        # (1) coverage resolves confidence_level (the alias is live, level not alpha).
        res_ok = (abs(c90["cl"] - 0.90) <= tol and abs(c95["cl"] - 0.95) <= tol
                  and abs(c99["cl"] - 0.99) <= tol)
        primary["coverage_resolves_level"] = {
            "status": "PASS" if res_ok else "BLOCK",
            "resolved_cl": {"0.90": c90["cl"], "0.95": c95["cl"], "0.99": c99["cl"]},
            "note": "coverage -> confidence_level (the LEVEL, not alpha)"}
        statuses.append(primary["coverage_resolves_level"]["status"])

        # (2) DIRECTIONAL width, saturation-tolerant: strict lower step,
        # non-strict top step, hard 0.90<->0.99 spread.
        lower_step = float(c95["width"] - c90["width"])
        top_step = float(c99["width"] - c95["width"])
        spread = float(c99["width"] - c90["width"])
        dir_ok = (lower_step >= ref["min_lower_step"] and top_step >= 0.0
                  and spread >= ref["min_spread"])
        primary["width_directional"] = {
            "status": "PASS" if dir_ok else "BLOCK",
            "width": {"0.90": round(c90["width"], 4), "0.95": round(c95["width"], 4),
                      "0.99": round(c99["width"], 4)},
            "lower_step_0.90->0.95": round(lower_step, 4),
            "top_step_0.95->0.99": round(top_step, 4),
            "spread_0.90<->0.99": round(spread, 4),
            "note": ("higher coverage -> wider (strict lower step; top step >=0 "
                     "tolerates only the finite-calibration quantile plateau; hard "
                     "spread catches inert; strict lower step catches "
                     "complement-backwards)")}
        statuses.append(primary["width_directional"]["status"])

        # (3) SENTINEL cross-check: default == coverage=0.95 (byte-identical).
        d_ok = (abs(d["cl"] - 0.95) <= tol
                and abs(d["width"] - c95["width"]) <= tol)
        primary["default_sentinel"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "default": {"cl": d["cl"], "width": round(d["width"], 4)},
            "note": "controls unset -> 0.95 / identical width (the inverted-gate default)"}
        statuses.append(primary["default_sentinel"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("engine-wired coverage now LIVE (clean alias of "
                          "confidence_level); default byte-identical (sentinels = the "
                          "three p3_conformal* checks). Ribbon->engine = Matt-Excel."),
            },
        )
