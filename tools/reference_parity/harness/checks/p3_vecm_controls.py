"""A-batch — vecm k_ar_diff discrimination + the coint_rank="auto" crash fix pin.

★ The `k_ar_diff` dialog control was INERT (the engine read `lag`); the dialog
DISPLAYED 2 but DELIVERED IC-selection. Fixed via the adf string-sentinel
pattern: catalog int->string, default "auto"; engine chain `lag (THOROUGH) >
k_ar_diff (dialog) > None`, with "auto"/""/"none" -> None -> IC-select (the
delivered behavior, dialog-default byte-identical) and an int -> a pinned lag
(now LIVE). The PRIMARY discrimination is the exact reported-order assertion:
audit `lag_order` == the pinned value (an inert wiring -> IC-pick regardless ->
BLOCK; a wrong-target wiring -> the wrong reported order -> BLOCK).

★ Also pins the coint_rank="auto" CRASH FIX: pre-fix, the dialog's DEFAULT
coint_rank value ("auto", a string) crashed `int()` (ValueError) -> every
dialog-default vecm run failed. Post-fix "auto" -> None -> the engine's
existing select_coint_rank path. The arm asserts status==success + an
auto-selected rank (a regression to the crash -> BLOCK).
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


class VecmControlsParity(P3ParityCheck):
    """vecm k_ar_diff LIVE (reported order == set; "auto" == delivered
    IC-select) + the coint_rank="auto" default-path crash fix pinned."""

    technique_id = "p3_vecm_controls"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The VECM lag order is a deterministic structural property (audit "
        "`lag_order`): a pinned k_ar_diff must land exactly (int equality, no "
        "tolerance); 'auto' must reproduce the no-param IC-selection. The "
        "coint_rank='auto' arm pins the default-path crash fix (pre-fix: "
        "ValueError on the dialog's default value). Engine-wiring fix "
        "(A-batch, adf string-sentinel pattern)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y1, y2 = _coint_pair(seed)
        return {"y1": y1, "y2": y2}

    def _engine(self, fixture, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.vecm_model as vm  # type: ignore
        ctx = RunContext({
            "run_id": "p3_vecm_controls", "technique_id": "vecm",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(_N)),
            "series": [{"name": "y1", "values": fixture["y1"].tolist()},
                       {"name": "y2", "values": fixture["y2"].tolist()}],
            "params": params,
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = vm.run(ctx, lambda *a, **k: None)
        au = r.get("audit_fields", {})
        # AUD-S3: digest the EMITTED tables so the gates ride the parameter's
        # EFFECT on output (VECM emits no per-lag coefficient table, so the
        # lag itself is not recomputable from output — the effect contrast is
        # the honest observable; the audit echo is cross-checked, not gated).
        import hashlib
        import json
        tbl_blob = json.dumps(r.get("tables", []), sort_keys=True, default=str)
        return {"status": r.get("status"), "lag": au.get("lag_order"),
                "rank": au.get("coint_rank"),
                "digest": hashlib.sha256(tbl_blob.encode()).hexdigest(),
                "err": str(r.get("error_message", ""))[:80]}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return {
            "noparam": self._engine(fixture, {"coint_rank": 1}),
            "auto": self._engine(fixture, {"k_ar_diff": "auto", "coint_rank": 1}),
            "pin4": self._engine(fixture, {"k_ar_diff": 4, "coint_rank": 1}),
            "pin4s": self._engine(fixture, {"k_ar_diff": "4", "coint_rank": 1}),
            "rank_auto": self._engine(fixture, {"coint_rank": "auto"}),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        np_, au, p4, p4s, ra = (tsl["noparam"], tsl["auto"], tsl["pin4"],
                                tsl["pin4s"], tsl["rank_auto"])

        # AUD-S3 upgrade: the load-bearing gates ride EMITTED-OUTPUT digests
        # (the parameter's effect), not the audit lag echoes. Echoes are
        # cross-checked in the consistency gate below.
        # (1) "auto" == the no-param run — byte-identical DELIVERED output.
        a_ok = (au["status"] == "success" and np_["status"] == "success"
                and au["digest"] == np_["digest"])
        primary["auto_sentinel"] = {
            "status": "PASS" if a_ok else "BLOCK",
            "digests_equal": au["digest"] == np_["digest"],
            "note": "k_ar_diff='auto' -> emitted tables byte-identical to the no-param run"}
        statuses.append(primary["auto_sentinel"]["status"])

        # (2) a pinned k_ar_diff BINDS on output (int + int-string identical;
        # pinned output differs from the IC pick's output on this fixture).
        p_ok = (p4["status"] == "success" and p4s["status"] == "success"
                and p4["digest"] == p4s["digest"]
                and p4["digest"] != np_["digest"])
        primary["pinned_lag_binds_on_output"] = {
            "status": "PASS" if p_ok else "BLOCK",
            "pin_int_eq_str": p4["digest"] == p4s["digest"],
            "pin_differs_from_ic": p4["digest"] != np_["digest"],
            "note": ("an inert k_ar_diff (the bug shape) -> pinned output == "
                     "IC output -> BLOCK; VECM emits no per-lag coefficient "
                     "table, so the effect contrast is the honest observable")}
        statuses.append(primary["pinned_lag_binds_on_output"]["status"])

        # (2b) consistency: the audit lag_order echoes match expectations
        # (engine misreport check — cross-checks, no longer the gate input).
        c_ok = (au["lag"] == np_["lag"] and p4["lag"] == 4 and p4s["lag"] == 4)
        primary["audit_echo_consistency"] = {
            "status": "PASS" if c_ok else "BLOCK",
            "noparam_lag": np_["lag"], "auto_lag": au["lag"],
            "pin4_lag": p4["lag"], "pin4_str_lag": p4s["lag"]}
        statuses.append(primary["audit_echo_consistency"]["status"])

        # (3) coint_rank='auto' crash fix: success + auto-selected rank.
        r_ok = (ra["status"] == "success" and ra["rank"] is not None
                and int(ra["rank"]) >= 1)
        primary["coint_rank_auto_no_crash"] = {
            "status": "PASS" if r_ok else "BLOCK",
            "rank_auto": ra,
            "note": ("pre-fix: ValueError int('auto') on the dialog DEFAULT -> failure; "
                     "post-fix: select_coint_rank auto path (regression -> BLOCK)")}
        statuses.append(primary["coint_rank_auto_no_crash"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"scope": ("engine-wired k_ar_diff (adf string-sentinel pattern) + the "
                                   "coint_rank='auto' crash fix; sentinels = p3_vecm_crosspkg/"
                                   "half_life (native lag). Ribbon->engine = Matt-Excel.")},
        )
