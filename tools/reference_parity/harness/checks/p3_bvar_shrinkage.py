"""Inert-control fix #2 — bvar `lambda_shrinkage` discrimination (engine-wiring).

★ `lambda_shrinkage` (the Minnesota overall-tightness knob, a DEFINING BVAR
parameter) was INERT — the dialog exposed it, the engine never `get_param`-read
it (it read `lambda1`, which the dialog never sends) → it did nothing. Now
engine-wired: `lambda_shrinkage` -> `lambda1` (precedence lambda1 >
lambda_shrinkage > preset default). The DEFAULT (lambda_shrinkage=0.1 ==
cfg lambda1) reproduces the prior posterior byte-identical — `1c_bvar_irf_fevd`
PASSES unchanged (the inverted-gate sentinel).

★ Load-bearing DIRECTIONAL check: the control must do the RIGHT thing, not just
SOMETHING. The Minnesota prior mean is a random walk (B_prior[i,i]=1.0), so a
TIGHTER lambda_shrinkage shrinks the own-lag-1 coefficient TOWARD 1.0 (more
shrinkage), a looser one toward OLS. The check asserts MONOTONE tight > default >
loose — a wiring driving the wrong direction (or the wrong hyperparameter) would
change the output but FAIL this. A still-inert engine -> identical posterior for
all lambda -> BLOCK.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 120
_NDRAWS = 200  # coef posterior is closed-form (indep of n_draws); small = fast


def _var1_dgp(seed: int):
    rng = np.random.default_rng(seed)
    A = np.array([[0.6, 0.15], [0.05, 0.5]])
    Y = np.zeros((_N, 2)); e = rng.standard_normal((_N, 2)) * 0.5
    for t in range(1, _N):
        Y[t] = A @ Y[t - 1] + e[t]
    return Y


class BvarShrinkageParity(P3ParityCheck):
    """bvar lambda_shrinkage is LIVE + directional (tighter -> more shrinkage
    toward the RW prior); the default is byte-identical (sentinel)."""

    technique_id = "p3_bvar_shrinkage"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The BVAR coefficient posterior MEAN is the closed-form conjugate "
        "Minnesota-NIW GLS solve (deterministic given the hyperparameters; "
        "independent of n_draws). Validates the engine-wired lambda_shrinkage is "
        "LIVE + DIRECTIONAL: tighter -> more shrinkage of the own-lag-1 "
        "coefficient toward the random-walk prior mean (1.0). The default "
        "(lambda_shrinkage=0.1 == cfg lambda1) reproduces the prior posterior "
        "byte-identical (sentinel = 1c_bvar_irf_fevd). Engine-wiring fix."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"Y": _var1_dgp(seed)}

    def _own_lag1(self, Y, params):
        from techniques.base import RunContext  # type: ignore
        import techniques.bvar as bv  # type: ignore
        ctx = RunContext({
            "run_id": "p3_bvar_shrinkage", "technique_id": "bvar",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(Y))),
            "series": [{"name": "y1", "values": Y[:, 0].tolist()},
                       {"name": "y2", "values": Y[:, 1].tolist()}],
            "params": {"lags": 1, "n_draws": _NDRAWS, **params},
        })
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            r = bv.run(ctx, lambda *a, **k: None)
        if r.get("status") != "success":
            raise RuntimeError(f"engine bvar failed: {r.get('error_message')}")
        tbl = next(t for t in r["tables"] if "Coef" in t.get("name", ""))
        coef = next(float(row[2]) for row in tbl["rows"]
                    if row[0] == "y1" and row[1] == "y1_lag1")
        return coef, float(r["audit_fields"].get("lambda1"))

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        Y = fixture["Y"]
        t_coef, t_l1 = self._own_lag1(Y, {"lambda_shrinkage": 0.02})   # tight
        d_coef, d_l1 = self._own_lag1(Y, {})                           # default
        l_coef, l_l1 = self._own_lag1(Y, {"lambda_shrinkage": 0.8})    # loose
        return {"tight_coef": t_coef, "tight_l1": t_l1,
                "default_coef": d_coef, "default_l1": d_l1,
                "loose_coef": l_coef, "loose_l1": l_l1}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"default_l1": 0.1, "l1_tol": float(ladder["default"]["abs_tol"]),
                "min_spread": float(ladder["discrimination"]["min_spread"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}; statuses: list[str] = []
        tc, dc, lc = tsl["tight_coef"], tsl["default_coef"], tsl["loose_coef"]

        # (1) SENTINEL: default resolves lambda1 == cfg 0.1 (byte-identical path).
        d_ok = (abs(tsl["default_l1"] - ref["default_l1"]) <= ref["l1_tol"]
                and abs(tsl["tight_l1"] - 0.02) <= ref["l1_tol"]
                and abs(tsl["loose_l1"] - 0.8) <= ref["l1_tol"])
        primary["lambda_shrinkage_resolves"] = {
            "status": "PASS" if d_ok else "BLOCK",
            "default_lambda1": tsl["default_l1"], "tight": tsl["tight_l1"], "loose": tsl["loose_l1"],
            "note": "lambda_shrinkage -> lambda1; default 0.1 == cfg (sentinel)"}
        statuses.append(primary["lambda_shrinkage_resolves"]["status"])

        # (2) ★ DIRECTIONAL — tighter -> MORE shrinkage toward the RW prior (1.0):
        # own-lag-1 coef monotone tight > default > loose, by a margin.
        mono = (tc > dc > lc)
        spread = float(tc - lc)
        dir_ok = mono and spread >= ref["min_spread"]
        primary["shrinkage_directional_monotone"] = {
            "status": "PASS" if dir_ok else "BLOCK",
            "tight_coef": round(tc, 4), "default_coef": round(dc, 4), "loose_coef": round(lc, 4),
            "monotone_tight>default>loose": mono, "tight_minus_loose": round(spread, 4),
            "min_spread": ref["min_spread"],
            "note": ("RW prior mean = 1.0; tighter lambda_shrinkage shrinks own-lag-1 "
                     "TOWARD 1.0 (more), looser toward OLS — the right thing, not just "
                     "something. Inert engine -> all equal -> BLOCK.")}
        statuses.append(primary["shrinkage_directional_monotone"]["status"])

        outcome = "BLOCK" if any(s == "BLOCK" for s in statuses) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "scope": ("engine-wired lambda_shrinkage now LIVE + directional; "
                          "default byte-identical (sentinel = 1c_bvar_irf_fevd). "
                          "Ribbon->engine = Matt-Excel."),
                "own_lag1_by_shrinkage": {"0.02": round(tc, 4), "0.1(default)": round(dc, 4),
                                          "0.8": round(lc, 4)},
            },
        )
