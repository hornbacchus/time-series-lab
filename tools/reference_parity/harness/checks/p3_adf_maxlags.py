"""Inert-control fix #4 — adf_test max_lags discrimination (type-mismatch).

★ `max_lags` (the "Max Lags" dialog control, type string, default "auto") was
INERT and a TYPE-MISMATCH: the engine read `max_lag` (int or None), never
`max_lags`, and `_run_adf_single` does `int(max_lag_param)` -> passing the
catalog's "auto" string there would have crashed (`int("auto")`). Now engine-
wired: `max_lag = get_param("max_lag", get_param("max_lags", None))` with the
string "auto" branched as a SENTINEL for auto-lag selection (Schwert bound +
autolag) == the current default; an int sets a fixed maxlag cap. The DEFAULT
("auto") reproduces the current auto-select byte-identical -> `p3_adf` AND
`p3_adf_triage` PASS unchanged (the inverted-gate sentinels; adf feeds the
triage).

★ Two load-bearing assertions:
 (1) the STRING "auto" is accepted (not crashed) and reproduces the no-param
     run -- the type-mismatch crux.
 (2) an int cap is LIVE *when it binds*: on a lag-4 DGP (AIC wants ~3 lags), a
     small cap (max_lags=1) BINDS the AIC selection -> lag 1, a very different
     ADF statistic; a large cap (>=4) == auto. A non-binding DGP would falsely
     show "no effect" (the first pre-verification did) -- so the DGP is chosen
     so the cap binds.

A still-inert engine -> max_lags ignored -> auto regardless of the int -> BLOCK.
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


def _lag4_dgp(seed: int):
    """y_t = 0.30 y_{t-1} + 0.45 y_{t-4} + e_t -- AIC wants ~3 lags, so a small
    maxlag cap BINDS the selection (the discrimination is visible)."""
    rng = np.random.default_rng(seed)
    y = np.zeros(_N); e = rng.standard_normal(_N)
    for t in range(4, _N):
        y[t] = 0.30 * y[t - 1] + 0.45 * y[t - 4] + e[t]
    return y


class AdfMaxLagsParity(P3ParityCheck):
    """adf_test max_lags is LIVE: "auto" -> auto-select (== default, byte-
    identical), an int -> a fixed cap that binds the AIC lag selection."""

    technique_id = "p3_adf_maxlags"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The ADF statistic is the deterministic statsmodels adfuller output given "
        "the (maxlag, autolag, regression). Validates the engine-wired max_lags: "
        "the string 'auto' is branched as a SENTINEL for auto-lag selection "
        "(reproduces the no-param run byte-identical -- sentinels p3_adf + "
        "p3_adf_triage), and an int sets a fixed maxlag cap that changes the "
        "selected lag + ADF statistic when it binds. Type-mismatch fix."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _lag4_dgp(seed)}

    def _engine(self, y, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.adf_test as adf  # type: ignore
        ctx = RunContext({
            "run_id": "udf_p3_adf_maxlags", "technique_id": "adf_test",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"triage": False, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = adf.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine adf failed: {r.get('error_message')}")
        au = r["audit_fields"]
        tbl = next(t for t in r["tables"] if t["name"] == "ADF Test Results")
        row = tbl["rows"][0]  # [Series, ADF Stat, P, Lags Used, ...]
        return {"resolved": au.get("max_lag_param"),
                "stat": float(row[1]), "lags": int(row[3])}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        return {
            "default": self._engine(y, {}),
            "auto": self._engine(y, {"max_lags": "auto"}),
            "cap1": self._engine(y, {"max_lags": 1}),
            "cap1_str": self._engine(y, {"max_lags": "1"}),
            "cap2": self._engine(y, {"max_lags": 2}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"match_tol": float(ladder["default"]["abs_tol"]),
                "min_stat_gap": float(ladder["discrimination"]["min_stat_gap"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        d, a, c1, c1s, c2 = (tsl["default"], tsl["auto"], tsl["cap1"],
                             tsl["cap1_str"], tsl["cap2"])
        tol = ref["match_tol"]

        # (1) "auto" string accepted (not crashed) + reproduces the no-param run.
        auto_ok = (a["resolved"] is None and d["resolved"] is None
                   and abs(a["stat"] - d["stat"]) <= tol and a["lags"] == d["lags"])
        primary["auto_string_sentinel"] = {
            "status": "PASS" if auto_ok else "BLOCK",
            "default": d, "auto": a,
            "note": "max_lags='auto' -> None (auto-select) == no-param run; string accepted, not crashed"}
        statuses.append(primary["auto_string_sentinel"]["status"])

        # (2) int cap LIVE + binds: cap=1 -> lag 1, ADF stat far from auto.
        bind_ok = (c1["resolved"] == 1 and c1["lags"] == 1
                   and abs(c1["stat"] - d["stat"]) >= ref["min_stat_gap"]
                   and c2["resolved"] == 2 and c2["lags"] == 2)
        primary["int_cap_binds"] = {
            "status": "PASS" if bind_ok else "BLOCK",
            "cap1": c1, "cap2": c2, "auto_stat": round(d["stat"], 4),
            "cap1_minus_auto": round(c1["stat"] - d["stat"], 4),
            "note": "binding cap changes the selected lag + ADF statistic (cap1->lag1, far from auto)"}
        statuses.append(primary["int_cap_binds"]["status"])

        # (3) type resolved both ways: int-string "1" == int 1.
        type_ok = (c1s["resolved"] == 1 and c1s["lags"] == 1
                   and abs(c1s["stat"] - c1["stat"]) <= tol)
        primary["type_both_ways"] = {
            "status": "PASS" if type_ok else "BLOCK",
            "int_string_1": c1s, "int_1": c1,
            "note": "string 'auto' AND int (and int-string) all accepted -- type-mismatch resolved"}
        statuses.append(primary["type_both_ways"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("engine-wired max_lags now LIVE; default 'auto' byte-identical "
                          "(sentinels p3_adf + p3_adf_triage). Ribbon->engine = Matt-Excel."),
                "adf_stat_by_cap": {"auto": round(d["stat"], 4), "cap1": round(c1["stat"], 4),
                                    "cap2": round(c2["stat"], 4)},
            },
        )
