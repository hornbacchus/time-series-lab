"""A-batch — har_rv horizon discrimination (engine-fallback to h_ahead).

★ The `horizon` dialog control was INERT (the engine read `h_ahead`); the
dialog DISPLAYED 10 but DELIVERED h=1 (the HAR-canonical one-day-ahead). Fixed:
engine chain `h_ahead (THOROUGH) > horizon (dialog) > 1`; catalog default
corrected 10->1 to STATE the delivered value (dialog-default byte-identical).
horizon == h_ahead identity confirmed: the h-step target (aggregate RV over the
next h days), int, h=1 = one-step.

Discrimination: the resolved h (audit `h_ahead`) tracks the dialog value
exactly, AND the fitted model genuinely changes with h (the regression target
is the h-aggregated RV -> the coefficients move). An inert wiring -> h_ahead=1
regardless + identical coefficients -> BLOCK.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 400


def _rv_series(seed: int):
    rng = np.random.default_rng(seed)
    # persistent positive RV-like series (vol clustering via AR on log-RV)
    lrv = np.zeros(_N)
    for t in range(1, _N):
        lrv[t] = 0.7 * lrv[t - 1] + rng.standard_normal() * 0.5
    return np.exp(lrv - 9.0) + 1e-6


class HarRvHorizonParity(P3ParityCheck):
    """har_rv horizon LIVE: resolves h_ahead exactly; the fit changes with h;
    dialog-default (1) == the delivered no-param run."""

    technique_id = "p3_har_rv_horizon"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The HAR-RV regression is deterministic OLS given (rv, lags, h); the "
        "resolved h is an exact structural property (audit `h_ahead`) and the "
        "coefficients change with the h-aggregated target. horizon == h_ahead "
        "identity confirmed (the h-step target horizon); the catalog default "
        "was corrected 10->1 to state the delivered value. Engine-wiring fix "
        "(A-batch)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"rv": _rv_series(seed)}

    def _engine(self, fixture, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.har_rv as hr  # type: ignore
        ctx = RunContext({
            "run_id": "p3_har_rv_horizon", "technique_id": "har_rv",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(_N)),
            "series": [{"name": "rv", "values": fixture["rv"].tolist()}],
            "params": params,
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = hr.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine har_rv failed: {r.get('error_message')}")
        au = r["audit_fields"]
        coefs = []
        for t in r.get("tables", []):
            if "Coefficient" in t.get("name", ""):
                for row in t["rows"]:
                    try:
                        coefs.append(float(row[1]))
                    except (TypeError, ValueError, IndexError):
                        pass
                break
        return {"h": au.get("h_ahead"), "coefs": coefs}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return {
            "noparam": self._engine(fixture, {}),
            "h1": self._engine(fixture, {"horizon": 1}),
            "h10": self._engine(fixture, {"horizon": 10}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"coef_tol": float(ladder["default"]["abs_tol"]),
                "min_coef_delta": float(ladder["discrimination"]["min_coef_delta"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        np_, h1, h10 = tsl["noparam"], tsl["h1"], tsl["h10"]

        # (1) horizon resolves h_ahead exactly; dialog-default (1) == no-param.
        c_np, c_h1 = np.array(np_["coefs"]), np.array(h1["coefs"])
        r_ok = (h1["h"] == 1 and h10["h"] == 10 and np_["h"] == 1
                and len(c_np) == len(c_h1) and len(c_np) > 0
                and float(np.max(np.abs(c_np - c_h1))) <= ref["coef_tol"])
        primary["horizon_resolves"] = {
            "status": "PASS" if r_ok else "BLOCK",
            "resolved_h": {"noparam": np_["h"], "horizon=1": h1["h"], "horizon=10": h10["h"]},
            "note": "horizon -> h_ahead exactly; dialog-default 1 == the delivered no-param run"}
        statuses.append(primary["horizon_resolves"]["status"])

        # (2) the fit changes with h (coefficients move on the h-aggregated target).
        c_h10 = np.array(h10["coefs"])
        delta = (float(np.max(np.abs(c_h1 - c_h10)))
                 if len(c_h1) == len(c_h10) and len(c_h1) > 0 else 0.0)
        d_ok = delta >= ref["min_coef_delta"]
        primary["fit_changes_with_h"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "max_coef_delta_h1_vs_h10": round(delta, 6),
            "min_required": ref["min_coef_delta"],
            "note": "the h-aggregated target moves the OLS coefficients (inert -> identical -> BLOCK)"}
        statuses.append(primary["fit_changes_with_h"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"scope": ("engine-wired horizon -> h_ahead; sentinel = p3_har_rv "
                                   "(native h_ahead). Ribbon->engine = Matt-Excel.")},
        )
