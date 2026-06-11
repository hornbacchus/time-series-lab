"""A-batch — auto_arima ic discrimination (every catalog value, the caviar standard).

★ The `ic` dialog control was INERT (the engine read `information_criterion`);
the dialog DISPLAYED aicc but DELIVERED aic. Fixed: engine chain
`information_criterion (THOROUGH) > ic (dialog) > "aic"`; catalog default
corrected aicc->aic to STATE the delivered value (dialog-default
byte-identical). Vocabulary verified honorable: pmdarima 2.1.1 accepts
aicc/aic/bic/hqic/oob — every catalog option ({aicc, aic, bic}) is genuinely
honored (no silent routing).

★ Per the ratified caviar standard, EVERY catalog value is exercised: each
resolves (audit information_criterion tracks the set value), and on the SPLIT
fixture (pre-verified: aic and bic select genuinely different orders) the
aic-vs-bic selections differ — an inert wiring (ic ignored -> aic always) ->
identical selections + a non-tracking audit -> BLOCK. (aicc's selection
coinciding with bic's on the fixture is fine; what must hold is per-value
resolution + the aic split.)
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path

_N = 150


def _split_dgp(seed: int):
    """ARMA(2,1)-ish, moderate n — pre-verified to SPLIT aic vs bic selections
    (aic richer order, bic sparser; the binding lesson: a non-splitting fixture
    falsely shows 'no effect')."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(_N + 2)
    x = np.zeros(_N)
    for t in range(2, _N):
        x[t] = 0.55 * x[t - 1] - 0.25 * x[t - 2] + e[t] + 0.4 * e[t - 1]
    return x


class AutoArimaIcParity(P3ParityCheck):
    """auto_arima ic LIVE: every catalog value resolves; aic vs bic selections
    differ on the split fixture; default == explicit-aic (byte-identical)."""

    technique_id = "p3_auto_arima_ic"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "pmdarima's stepwise search is deterministic given (y, bounds, "
        "information_criterion); the selected order is a categorical output. "
        "Every catalog ic value (aicc/aic/bic — all pmdarima-2.1.1-honorable, "
        "verified) must resolve (audit tracks), and aic-vs-bic must select "
        "different orders on the pre-verified split fixture. The default run "
        "must equal the explicit-aic run (the delivered behavior; the catalog "
        "default was corrected aicc->aic to state it). Engine-wiring fix "
        "(A-batch)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"x": _split_dgp(seed)}

    def _engine(self, fixture, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.arima as ar  # type: ignore
        ctx = RunContext({
            "run_id": "p3_auto_arima_ic", "technique_id": "auto_arima",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(_N)),
            "series": [{"name": "x", "values": fixture["x"].tolist()}],
            "params": {"seasonal": False, "horizon": 5, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = ar.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine auto_arima failed: {r.get('error_message')}")
        au = r["audit_fields"]
        return {"order": str(au.get("order")),
                "ic": str(au.get("information_criterion", au.get("ic")))}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        out = {v: self._engine(fixture, {"ic": v}) for v in ("aicc", "aic", "bic")}
        out["default"] = self._engine(fixture, {})
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return {}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []

        # (1) EVERY catalog value resolves (audit tracks the set value).
        res_ok = all(tsl[v]["ic"] == v for v in ("aicc", "aic", "bic"))
        primary["every_value_resolves"] = {
            "status": "PASS" if res_ok else "BLOCK",
            "resolved": {v: tsl[v]["ic"] for v in ("aicc", "aic", "bic")},
            "note": "each catalog ic value -> audit information_criterion (per-value, the caviar standard)"}
        statuses.append(primary["every_value_resolves"]["status"])

        # (2) the aic split: aic vs bic select DIFFERENT orders (categorical).
        split_ok = tsl["aic"]["order"] != tsl["bic"]["order"]
        primary["aic_bic_selections_differ"] = {
            "status": "PASS" if split_ok else "BLOCK",
            "orders": {v: tsl[v]["order"] for v in ("aicc", "aic", "bic")},
            "note": ("the split fixture: aic vs bic orders differ (inert -> aic always -> "
                     "identical -> BLOCK; aicc==bic coincidence on this fixture is fine)")}
        statuses.append(primary["aic_bic_selections_differ"]["status"])

        # (3) default == explicit-aic (the delivered behavior, byte-identical).
        d_ok = (tsl["default"]["order"] == tsl["aic"]["order"]
                and tsl["default"]["ic"] == "aic")
        primary["default_sentinel"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "default": tsl["default"], "explicit_aic": tsl["aic"],
            "note": "ic unset -> aic (the delivered default; catalog corrected aicc->aic to state it)"}
        statuses.append(primary["default_sentinel"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"scope": ("engine-wired ic; sentinel = p3_auto_arima (no ic key). "
                                   "Ribbon->engine = Matt-Excel.")},
        )
