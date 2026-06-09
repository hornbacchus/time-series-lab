"""Inert-control fix #3 — caviar quantile + model_type discrimination (wiring).

★ `quantile` (the VaR level) + `model_type` (the CAViaR specification) were the
technique's two DEFINING knobs, both INERT — the dialog exposed them, the engine
read `theta` + `specification` (which the dialog never sends) -> the user's
settings were silently dropped (theta=0.05, spec=SAV always). Now engine-wired:
`quantile` -> `theta` (clean, same quantity/scale) and `model_type` ->
`specification` via a VALUE-MAP (symmetric_abs->SAV, asymmetric_slope->AS,
igarch->IG). The DEFAULT (quantile=0.05, model_type=symmetric_abs) reproduces
theta=0.05/spec=SAV byte-identical -> `3a_caviar_sav` PASSES unchanged (the
inverted-gate sentinel).

★ Two load-bearing assertions (the right thing, not just something):
 (1) quantile is DIRECTIONAL — a higher quantile -> a less-extreme (less
     negative) 1-step VaR (economically correct), monotone across {0.01,0.05,
     0.10}. A wiring that drives theta backwards would change the output but
     FAIL this.
 (2) model_type is PER-VALUE — EACH catalog value maps to its correct engine
     spec (symmetric_abs->SAV, asymmetric_slope->AS, igarch->IG), validated
     individually (the value-vocabulary trap: a map silently routing a value to
     the wrong spec would FAIL). The catalog's old `adaptive` option (no engine
     implementation) was corrected to `igarch`; the Engle-Manganelli Adaptive
     spec is a banked engine-improvement, deliberately not faked.

A still-inert engine -> quantile/model_type ignored -> theta/spec constant ->
BLOCK (the negative control).
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 600
_NPATHS = 200  # low MC paths; the 1-step VaR is from the fitted recursion


def _garch_returns(seed: int):
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(_N); h = np.ones(_N); y = np.zeros(_N)
    for t in range(1, _N):
        h[t] = 0.05 + 0.1 * y[t - 1] ** 2 + 0.85 * h[t - 1]
        y[t] = np.sqrt(h[t]) * e[t]
    return y


class CaviarControlsParity(P3ParityCheck):
    """caviar quantile + model_type are LIVE: quantile drives theta (directional
    VaR), model_type maps per-value to the engine spec. Default byte-identical."""

    technique_id = "p3_caviar_controls"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "CAViaR fit is a seeded (seed=42) stochastic-restart quantile-loss "
        "minimization; the 1-step VaR is the deterministic recursion on the "
        "fitted params. The discrimination is DIRECTIONAL (higher quantile -> "
        "less-extreme VaR, monotone) + CATEGORICAL (each model_type -> its "
        "engine spec code) -- robust to optimizer noise. The default "
        "(quantile=0.05, model_type=symmetric_abs) reproduces theta=0.05/spec=SAV "
        "byte-identical (sentinel = 3a_caviar_sav). Engine-wiring fix."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _garch_returns(seed)}

    def _engine(self, y, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.caviar_quantile_dynamics as cav  # type: ignore
        ctx = RunContext({
            "run_id": "p3_caviar_controls", "technique_id": "caviar_quantile_dynamics",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "ret", "values": y.tolist()}],
            "params": {"n_simulation_paths": _NPATHS, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = cav.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine caviar failed: {r.get('error_message')}")
        au = r["audit_fields"]
        return {"theta": float(au["theta"]), "spec": str(au["specification"]),
                "var1": float(au["one_step_ahead_var"])}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        q = {qv: self._engine(y, {"quantile": qv}) for qv in (0.01, 0.05, 0.10)}
        mt = {m: self._engine(y, {"model_type": m})
              for m in ("symmetric_abs", "asymmetric_slope", "igarch")}
        default = self._engine(y, {})
        return {"q": q, "mt": mt, "default": default}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {
            "theta_tol": float(ladder["default"]["abs_tol"]),
            "min_var_gap": float(ladder["discrimination"]["min_var_gap"]),
            "min_spec_gap": float(ladder["discrimination"]["min_spec_gap"]),
            "expect_spec": {"symmetric_abs": "SAV", "asymmetric_slope": "AS", "igarch": "IG"},
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        q, mt, d = tsl["q"], tsl["mt"], tsl["default"]
        tol = ref["theta_tol"]

        # (1) quantile resolves theta + DIRECTIONAL monotone VaR (less extreme as q up).
        theta_ok = all(abs(q[qv]["theta"] - qv) <= tol for qv in (0.01, 0.05, 0.10))
        v01, v05, v10 = q[0.01]["var1"], q[0.05]["var1"], q[0.10]["var1"]
        mono = (v01 < v05 < v10)
        gap = float(v10 - v01)
        q_ok = theta_ok and mono and gap >= ref["min_var_gap"]
        primary["quantile_drives_theta_directional"] = {
            "status": "PASS" if q_ok else "BLOCK",
            "resolved_theta": {str(k): q[k]["theta"] for k in (0.01, 0.05, 0.10)},
            "var1_by_quantile": {"0.01": round(v01, 4), "0.05": round(v05, 4), "0.10": round(v10, 4)},
            "monotone_less_extreme_as_q_up": mono, "v10_minus_v01": round(gap, 4),
            "note": "higher quantile -> less-extreme VaR (economically correct, not just different)"}
        statuses.append(primary["quantile_drives_theta_directional"]["status"])

        # (2) model_type value-map, EACH value -> its engine spec + distinct fits.
        spec_ok = all(mt[m]["spec"] == ref["expect_spec"][m] for m in mt)
        vars_ = [mt[m]["var1"] for m in ("symmetric_abs", "asymmetric_slope", "igarch")]
        spread = float(max(vars_) - min(vars_))
        distinct = spread >= ref["min_spec_gap"]
        mt_ok = spec_ok and distinct
        primary["model_type_value_map_per_value"] = {
            "status": "PASS" if mt_ok else "BLOCK",
            "resolved_spec": {m: mt[m]["spec"] for m in mt},
            "expected_spec": ref["expect_spec"],
            "all_values_correct": spec_ok,
            "var1_by_spec": {m: round(mt[m]["var1"], 4) for m in mt},
            "fits_distinct_spread": round(spread, 4),
            "note": "each catalog model_type -> its correct engine spec (per-value, not just one)"}
        statuses.append(primary["model_type_value_map_per_value"]["status"])

        # (3) SENTINEL cross-check: default -> theta 0.05, spec SAV (byte-identical).
        d_ok = abs(d["theta"] - 0.05) <= tol and d["spec"] == "SAV"
        primary["default_sentinel"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "default_theta": d["theta"], "default_spec": d["spec"],
            "note": "controls unset -> theta 0.05 / SAV (the inverted-gate default)"}
        statuses.append(primary["default_sentinel"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("engine-wired quantile + model_type now LIVE; default "
                          "byte-identical (sentinel = 3a_caviar_sav). adaptive->igarch "
                          "catalog correction (Adaptive spec banked). Ribbon->engine = "
                          "Matt-Excel."),
            },
        )
