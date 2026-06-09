"""Inert-control fix #1 — forecast_combination `models` + `combination_method`
discrimination (engine-wiring; the controls are now live).

★ Both controls were INERT (the engine ignored them — the technique's two
defining knobs did nothing). Now engine-wired: `models` selects the component
subset; `combination_method` selects the headline/primary weighting scheme.
The DEFAULT reproduces the prior behavior byte-identical (all 3 models +
inverse-MSE primary) — `p3_forecast_combination` (self-parity) PASSES unchanged
(the inverted-gate sentinel). THIS check is the discrimination: non-default
selections CHANGE the output (the controls are live).

★ Load-bearing: `combination_method` must change the PRIMARY FORECAST VECTOR
(the headline `primary_combined_forecast`), NOT just a label — a relabel-only
wiring would be the inert bug in cosmetic form. The check compares forecast
VECTORS, not labels.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 160
_HORIZON = 8


def _dgp(seed: int):
    rng = np.random.default_rng(seed)
    t = np.arange(_N)
    return (np.cumsum(rng.standard_normal(_N)) * 0.5 + np.sin(t * 0.3) * 2 + 50.0)


class ForecastCombinationControlsParity(P3ParityCheck):
    """forecast_combination models + combination_method are LIVE (the
    non-default output differs; the default is byte-identical — sentinel)."""

    technique_id = "p3_forecast_combination_controls"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Deterministic at a fixed seed (pmdarima auto_arima + statsmodels ETS/"
        "Theta). Validates the engine-wired controls are LIVE: combination_method "
        "moves the primary FORECAST VECTOR (not just a label), models changes the "
        "combined forecast (component subset). The default reproduces the prior "
        "inverse-MSE-primary all-3-models behavior (the byte-identical sentinel, "
        "guarded by p3_forecast_combination). Engine-wiring fix, not a rename."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _dgp(seed)}

    def _engine(self, y, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.forecast_combination as fc  # type: ignore
        ctx = RunContext({
            "run_id": "p3_fc_controls", "technique_id": "forecast_combination",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": list(map(float, y))}],
            "params": {"horizon": _HORIZON, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = fc.run(ctx, lambda *a, **k: None)
        return r

    @staticmethod
    def _col(resp, name):
        t = next(t for t in resp["tables"] if t.get("name") == "Combined Forecasts")
        c = t["columns"]
        return np.array([float(row[c.index(name)]) for row in t["rows"]], float)

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        rd = self._engine(y, {})                                    # default
        ro = self._engine(y, {"combination_method": "ols"})         # method
        rs = self._engine(y, {"models": "auto_arima,theta"})        # subset
        au = rd["audit_fields"]
        return {
            "default_primary": list(map(float, au["primary_combined_forecast"])),
            "default_cm": au["combination_method"],
            "default_models": list(au["models"]),
            "default_invmse_col": self._col(rd, "Inv-MSE").tolist(),
            "ols_primary": list(map(float, ro["audit_fields"]["primary_combined_forecast"])),
            "ols_cm": ro["audit_fields"]["combination_method"],
            "ols_col_in_ols_run": self._col(ro, "OLS").tolist(),
            "subset_models": list(rs["audit_fields"]["models"]),
            "subset_invmse_col": self._col(rs, "Inv-MSE").tolist(),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"method_min_move": float(ladder["discrimination"]["method_min_move"]),
                "models_min_move": float(ladder["discrimination"]["models_min_move"]),
                "match_tol": float(ladder["discrimination"]["match_tol"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        dp = np.asarray(tsl["default_primary"], float)
        inv = np.asarray(tsl["default_invmse_col"], float)
        op = np.asarray(tsl["ols_primary"], float)
        ocol = np.asarray(tsl["ols_col_in_ols_run"], float)
        sub = np.asarray(tsl["subset_invmse_col"], float)
        mt = ref["match_tol"]

        # (1) DEFAULT sentinel: primary == the Inv-MSE scheme (current behavior).
        d_ok = (tsl["default_cm"] == "inverse_mse"  # audit holds the param key
                and tsl["default_models"] == ["ARIMA", "ETS", "Theta"]
                and float(np.max(np.abs(dp - inv))) <= mt)
        primary["default_primary_is_inverse_mse"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "default_cm": tsl["default_cm"], "default_models": tsl["default_models"],
            "primary_vs_invmse_max_diff": float(np.max(np.abs(dp - inv)))}
        statuses.append(primary["default_primary_is_inverse_mse"]["status"])

        # (2) ★ combination_method LIVE — the primary VECTOR tracks OLS + MOVES.
        moved = float(np.max(np.abs(op - dp)))
        tracks = float(np.max(np.abs(op - ocol)))
        m_ok = (tsl["ols_cm"] == "ols" and tracks <= mt and moved >= ref["method_min_move"])
        primary["combination_method_live"] = {
            "status": "PASS" if m_ok else "BLOCK",
            "ols_cm": tsl["ols_cm"], "primary_tracks_ols_col_maxdiff": tracks,
            "primary_moved_vs_default_maxdiff": moved, "min_move": ref["method_min_move"],
            "note": "the HEADLINE forecast vector moves with the control (not just a label)"}
        statuses.append(primary["combination_method_live"]["status"])

        # (3) models LIVE — subset excludes ETS + the combined forecast changes.
        smoved = float(np.max(np.abs(sub - inv)))
        s_ok = (tsl["subset_models"] == ["ARIMA", "Theta"] and smoved >= ref["models_min_move"])
        primary["models_live"] = {
            "status": "PASS" if s_ok else "BLOCK",
            "subset_models": tsl["subset_models"],
            "subset_combined_moved_maxdiff": smoved, "min_move": ref["models_min_move"]}
        statuses.append(primary["models_live"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("engine-wired controls (models + combination_method) "
                          "now LIVE; default byte-identical (sentinel = "
                          "p3_forecast_combination). Ribbon->engine = Matt-Excel."),
                "primary_moved_ols": moved, "subset_moved": smoved,
            },
        )
