"""Satellite-ledger fix — VAR max_lag regression guard.

★ The defect was a CATALOG key mismatch: the VAR "Max Lags" control wrote the
param `max_lags` (plural) while the engine reads `max_lag` (singular) → the
control's value was silently dropped → the VAR used its default lag regardless
of the user's setting. The fix is CATALOG-ONLY (rename the control's param key
`max_lags` → `max_lag`); the engine already reads `max_lag` correctly.

★ HONEST SCOPE — this check guards the ENGINE, NOT the catalog fix. It asserts
the engine HONORS `max_lag` (the param affects the VAR order/output), so a
FUTURE engine regression that re-breaks the `max_lag` read is caught. It does
NOT and cannot validate the catalog fix itself: the bug was the ribbon passing
the wrong key, and the harness invokes the engine directly (bypassing the
ribbon) — the ribbon→engine wiring (does the "Max Lags" control now change the
result) is Matt-Excel-acceptance, not harness-testable. Belt-and-suspenders,
correctly scoped.

`p3_var` / `p3_var_crosspkg` are unaffected (they pass the fixed `lag` param,
not `max_lag`); the engine is byte-identical (the fix is catalog-only).
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 300


def _var13_dgp(seed: int):
    """A VAR with lag-1 AND lag-3 structure, so IC order-selection RESPONDS to
    the max_lag cap (a cap of 1 forces order 1; a higher cap lets IC pick 3)."""
    rng = np.random.default_rng(seed)
    A1 = np.array([[0.4, 0.1], [0.0, 0.3]])
    A3 = np.array([[0.2, 0.0], [0.1, 0.15]])
    Y = np.zeros((_N, 2)); e = rng.standard_normal((_N, 2)) * 0.5
    for t in range(3, _N):
        Y[t] = A1 @ Y[t - 1] + A3 @ Y[t - 3] + e[t]
    return Y


class VarMaxLagGuard(P3ParityCheck):
    """Engine-honors-max_lag regression guard (the param affects VAR order)."""

    technique_id = "p3_var_max_lag"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "VAR order selection is deterministic (IC argmin over OLS fits up to "
        "max_lag). This guards that the engine HONORS the max_lag cap — a cap "
        "of 1 forces order 1, a higher cap lets IC select a higher order — so "
        "a future regression re-breaking the max_lag read is caught. NOT the "
        "catalog-fix validation (that is Matt-Excel ribbon acceptance); a "
        "regression guard on the already-correct engine read."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _var13_dgp(seed)}

    def _order(self, Y, max_lag) -> dict[str, int]:
        import re
        from techniques.base import RunContext  # type: ignore
        import techniques.var_model as vm  # type: ignore
        ctx = RunContext({
            "run_id": "p3_var_max_lag", "technique_id": "var",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(Y))),
            "series": [{"name": "y1", "values": Y[:, 0].tolist()},
                       {"name": "y2", "values": Y[:, 1].tolist()}],
            "params": {"trend": "c", "max_lag": int(max_lag)},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            resp = vm.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine var failed: {resp.get('error_message')}")
        # AUD-S3: recompute the selected order from the EMITTED Coefficients
        # table (statsmodels parameter names L<k>.<var>) — the parameter's
        # EFFECT on output, not the audit echo. The audit scalar is
        # cross-checked below, never gated on.
        coef = next(t for t in resp.get("tables", [])
                    if t.get("name") == "Coefficients")
        lag_ids = []
        for row in coef["rows"]:
            m = re.match(r"L(\d+)\.", str(row[1]))
            if m:
                lag_ids.append(int(m.group(1)))
        return {"emitted": max(lag_ids) if lag_ids else 0,
                "reported": int(resp["audit_fields"]["var_order"])}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        Y = fixture["Y"]
        return {"cap1": self._order(Y, 1), "cap8": self._order(Y, 8)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        # Analytic expectation: a cap of 1 forces order 1; a higher cap lets IC
        # select a higher order. The discrimination = the two orders DIFFER.
        return {"expected_order_cap1": 1,
                "min_order_cap8": int(ladder["discrimination"]["min_order_cap8"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        # AUD-S3 upgrade: all order gates consume the order RECOMPUTED from
        # the emitted Coefficients table; the audit echoes are cross-checked
        # in the consistency gate below.
        o1, o8 = tsl["cap1"]["emitted"], tsl["cap8"]["emitted"]
        primary: dict[str, Any] = {}; statuses: list[str] = []

        # (a) the cap is honored — order(max_lag=1) == 1 (cannot exceed the cap).
        cap_ok = o1 == ref["expected_order_cap1"]
        primary["cap_honored"] = {"status": "PASS" if cap_ok else "BLOCK",
                                  "order_at_cap1": o1, "expected": ref["expected_order_cap1"]}
        statuses.append(primary["cap_honored"]["status"])

        # (b) a higher cap selects a higher order.
        hi_ok = o8 >= ref["min_order_cap8"]
        primary["higher_cap_higher_order"] = {"status": "PASS" if hi_ok else "BLOCK",
                                              "order_at_cap8": o8, "min_expected": ref["min_order_cap8"]}
        statuses.append(primary["higher_cap_higher_order"]["status"])

        # ★ (c) DISCRIMINATION (load-bearing) — the two caps give DIFFERENT orders.
        # If max_lag were dropped (the bug), both → the same default order → BLOCK.
        disc_ok = o1 != o8
        primary["max_lag_affects_output"] = {
            "status": "PASS" if disc_ok else "BLOCK",
            "order_cap1": o1, "order_cap8": o8,
            "note": ("the param-affects-output guard: if the engine dropped "
                     "max_lag (the catalog-bug shape), both caps -> the same "
                     "default order -> BLOCK")}
        statuses.append(primary["max_lag_affects_output"]["status"])

        # (d) consistency: the audit `var_order` echo must match the order
        # recomputed from the emitted table (an engine misreport check).
        cons_ok = (tsl["cap1"]["reported"] == o1
                   and tsl["cap8"]["reported"] == o8)
        primary["audit_echo_consistency"] = {
            "status": "PASS" if cons_ok else "BLOCK",
            "cap1_reported": tsl["cap1"]["reported"], "cap1_emitted": o1,
            "cap8_reported": tsl["cap8"]["reported"], "cap8_emitted": o8}
        statuses.append(primary["audit_echo_consistency"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("ENGINE-honors-max_lag regression guard; NOT the "
                          "catalog-fix validation (ribbon->engine = Matt-Excel)"),
                "order_cap1": o1, "order_cap8": o8,
                "order_source": "emitted Coefficients table (L<k>. parameter names)",
                "catalog_fix": "techniques_catalog.json VAR control name max_lags -> max_lag",
            },
        )
