"""A-batch — johansen k_ar_diff discrimination (adf string-sentinel pattern).

★ The `k_ar_diff` dialog control was INERT (the engine read `lag`); the dialog
DISPLAYED 2 but DELIVERED IC-selection. Fixed: catalog int->string, default
"auto"; engine chain `lag (THOROUGH) > k_ar_diff (dialog) > None` with the
"auto" sentinel -> IC-select (delivered, dialog-default byte-identical); an
int -> a pinned lag (now LIVE). The engine's `lag` is passed STRAIGHT to
statsmodels coint_johansen(k_ar_diff=p) — identity confirmed, no off-by-one —
so the exact reported-order assertion (audit `lag_order` == the pinned value)
is the off-by-one guard: a convention-shifted wiring would land p±1 -> BLOCK;
an inert wiring -> the IC pick -> BLOCK.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path

_N = 300


def _coint_pair(seed: int):
    rng = np.random.default_rng(seed)
    z = np.cumsum(rng.standard_normal(_N))
    y1 = z + rng.standard_normal(_N) * 0.4
    y2 = 0.7 * z + rng.standard_normal(_N) * 0.4
    return y1, y2


class JohansenKardiffParity(P3ParityCheck):
    """johansen k_ar_diff LIVE: a pinned value lands exactly (audit lag_order);
    'auto' reproduces the delivered IC-selection."""

    technique_id = "p3_johansen_kardiff"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The Johansen test's lag order is a deterministic structural property "
        "(audit `lag_order`); the engine passes it straight to statsmodels "
        "coint_johansen(k_ar_diff=p) (identity confirmed — no off-by-one). A "
        "pinned k_ar_diff must land exactly (int equality — the off-by-one "
        "guard); 'auto' must reproduce the no-param IC-selection. Engine-wiring "
        "fix (A-batch, adf string-sentinel pattern)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y1, y2 = _coint_pair(seed)
        return {"y1": y1, "y2": y2}

    def _engine(self, fixture, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.johansen_cointegration as jc  # type: ignore
        ctx = RunContext({
            "run_id": "p3_johansen_kardiff", "technique_id": "johansen_cointegration",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(_N)),
            "series": [{"name": "y1", "values": fixture["y1"].tolist()},
                       {"name": "y2", "values": fixture["y2"].tolist()}],
            "params": params,
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = jc.run(ctx, lambda *a, **k: None)
        return {"status": r.get("status"),
                "lag": r.get("audit_fields", {}).get("lag_order")}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return {
            "noparam": self._engine(fixture, {}),
            "auto": self._engine(fixture, {"k_ar_diff": "auto"}),
            "pin4": self._engine(fixture, {"k_ar_diff": 4}),
            "pin4s": self._engine(fixture, {"k_ar_diff": "4"}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        np_, au, p4, p4s = tsl["noparam"], tsl["auto"], tsl["pin4"], tsl["pin4s"]

        a_ok = (au["status"] == "success" and np_["status"] == "success"
                and au["lag"] == np_["lag"])
        primary["auto_sentinel"] = {
            "status": "PASS" if a_ok else "BLOCK",
            "noparam_lag": np_["lag"], "auto_lag": au["lag"],
            "note": "k_ar_diff='auto' -> IC-selection == no-param (dialog-default byte-identical)"}
        statuses.append(primary["auto_sentinel"]["status"])

        p_ok = (p4["status"] == "success" and p4["lag"] == 4
                and p4s["status"] == "success" and p4s["lag"] == 4
                and np_["lag"] != 4)
        primary["pinned_lag_lands"] = {
            "status": "PASS" if p_ok else "BLOCK",
            "pin4_lag": p4["lag"], "pin4_str_lag": p4s["lag"], "ic_pick": np_["lag"],
            "note": ("reported lag_order == the set value exactly (the off-by-one guard; "
                     "inert -> the IC pick -> BLOCK)")}
        statuses.append(primary["pinned_lag_lands"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"scope": ("engine-wired k_ar_diff (adf string-sentinel pattern); "
                                   "sentinel = 3d_johansen_bartlett (no lag key). "
                                   "Ribbon->engine = Matt-Excel.")},
        )
