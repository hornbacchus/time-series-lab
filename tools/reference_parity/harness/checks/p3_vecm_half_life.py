"""Phase 7+ engine-improvement #3 — VECM half_life_periods guard discrimination.

★ S65 guard fix: the VECM adjustment half-life `half_life = -ln(2)/ln(1+α[0,0])`
is DEFINED only for α[0,0] ∈ (−1, 0) (1+α[0,0] ∈ (0,1) → stable monotone decay).
The old guard `−2 < a0 < 0` admitted α[0,0] ∈ (−2,−1) where 1+α[0,0] < 0 →
`np.log(negative)` returns nan SILENTLY (a warning, not an exception, so the
engine's try/except never caught it) → the emitted `half_life_periods` was nan.
Fixed: the guard is tightened to the strict (−1, 0); the over-correcting range
returns None (the undefined-flag the interpretation spec routes on).

This is an ENGINE-INVOKED, verified-discriminating check (NOT self-parity):
  - POSITIVE (valid range): the standard cointegrated fixture (α[0,0]≈−0.93)
    -> a finite half-life that matches the documented formula at the fitted α.
  - ★ NEGATIVE CONTROL (the discrimination): an OVER-CORRECTING DGP
    (α=[−1.5, 0.2] -> fitted α[0,0] ∈ (−2,−1), precondition asserted) -> the
    half-life is None (NOT nan, NOT a garbage finite). Pre-fix this is nan ->
    the arm BLOCKS, catching exactly the bug. The OLD guard leaked nan; the new
    guard returns the correct undefined-flag.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_vecm import _generate_vecm_dgp


def _over_correcting_dgp(seed: int, n: int = 200):
    """Bivariate rank-1 cointegrated VAR with an OVER-correcting adjustment
    (α=[−1.5, 0.2]) -> fitted α[0,0] lands in (−2,−1), the over-correcting /
    oscillatory range where the half-life is undefined."""
    rng = np.random.default_rng(seed)
    a = np.array([-1.5, 0.2]); b = np.array([1.0, -1.0])
    y = np.zeros((n, 2))
    for t in range(1, n):
        y[t] = y[t - 1] + a * (b @ y[t - 1]) + rng.standard_normal(2) * 0.5
    return y


def _engine_vecm(Y):
    from techniques.base import RunContext  # type: ignore
    import techniques.vecm_model as vm  # type: ignore
    n = len(Y)
    ctx = RunContext({
        "run_id": "p3_vecm_half_life", "technique_id": "vecm",
        "preset": "Balanced", "seed": 42, "frequency": "",
        "time": list(range(n)),
        "series": [{"name": "y1", "values": Y[:, 0].tolist()},
                   {"name": "y2", "values": Y[:, 1].tolist()}],
        "params": {"coint_rank": 1, "deterministic": "ci", "lag": 1},
    })
    resp = vm.run(ctx, lambda *a, **k: None)
    if resp.get("status") != "success":
        raise RuntimeError(f"engine vecm failed: {resp.get('error_message')}")
    au = resp["audit_fields"]
    a0 = float(np.asarray(au["alpha_normalized"])[0, 0])
    return a0, au.get("half_life_periods")


class VecmHalfLifeParity(P3ParityCheck):
    """VECM half_life_periods guard discrimination (S65 fix): valid-range
    finite + formula-matched; over-correcting range -> None (was nan)."""

    technique_id = "p3_vecm_half_life"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The VECM adjustment half-life -ln(2)/ln(1+α[0,0]) is closed-form, "
        "defined only for α[0,0] ∈ (−1,0). Engine-invoked discrimination of the "
        "S65 guard fix: valid-range -> finite + matches the documented formula; "
        "over-correcting range (α[0,0] ∈ (−2,−1)) -> None (the undefined-flag), "
        "where the old loose guard silently leaked nan. Verified-discriminating "
        "(negative control fires on the undefined range), NOT self-parity."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"valid": _generate_vecm_dgp(seed=seed),
                "over": _over_correcting_dgp(seed=seed + 1)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        a0_valid, hl_valid = _engine_vecm(fixture["valid"])
        a0_over, hl_over = _engine_vecm(fixture["over"])
        return {"a0_valid": a0_valid, "hl_valid": hl_valid,
                "a0_over": a0_over, "hl_over": hl_over}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # No engine state needed; the documented formula is evaluated in
        # compare() at the engine's own fitted α[0,0] (external-authority value
        # check). The over-correcting range is analytically undefined -> None.
        return {"valid_range": "(-1, 0)", "undefined_range": "(-2, -1)"}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        def _is_nan(x):
            return isinstance(x, float) and x != x

        # POSITIVE — valid range: finite, >0, matches the documented formula.
        # The engine emits half_life_periods rounded to 2 dp (B8 floor), so the
        # documented formula is rounded to match the emitted precision.
        a0v, hlv = tsl["a0_valid"], tsl["hl_valid"]
        in_valid = -1.0 < a0v < 0.0
        formula = (float(-np.log(2.0) / np.log(1.0 + a0v)) if in_valid else None)
        formula_2dp = (round(formula, 2) if formula is not None else None)
        atol = float(ladder["formula"]["abs_tol"])
        finite_hl = isinstance(hlv, (int, float)) and not _is_nan(hlv)
        abs_diff = (abs(float(hlv) - formula_2dp)
                    if (finite_hl and formula_2dp is not None) else None)
        pos_ok = (in_valid and finite_hl and hlv > 0.0
                  and formula_2dp is not None and abs_diff <= atol)
        primary["valid_range_formula_match"] = {
            "status": "PASS" if pos_ok else "BLOCK",
            "a0": a0v, "engine_half_life": hlv,
            "documented_formula_full": (round(formula, 6) if formula is not None else None),
            "documented_formula_2dp": formula_2dp, "abs_diff": abs_diff}
        statuses.append(primary["valid_range_formula_match"]["status"])

        # ★ NEGATIVE CONTROL — over-correcting range: half_life is None (NOT nan).
        a0o, hlo = tsl["a0_over"], tsl["hl_over"]
        precond = -2.0 < a0o < -1.0   # the DGP must exercise the undefined range
        neg_ok = precond and (hlo is None)
        primary["over_correcting_undefined_control"] = {
            "status": "PASS" if neg_ok else "BLOCK",
            "a0": a0o, "engine_half_life": hlo,
            "is_none": hlo is None, "is_nan": _is_nan(hlo),
            "precondition_a0_in_(-2,-1)": precond,
            "note": ("over-correcting alpha[0,0] in (-2,-1): half-life undefined "
                     "-> must be None. Pre-fix the old guard leaked nan here.")}
        statuses.append(primary["over_correcting_undefined_control"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "valid_a0": a0v, "valid_half_life": hlv,
                "over_a0": a0o, "over_half_life": hlo,
                "documented_formula": "-ln(2)/ln(1+alpha[0,0]), defined on (-1,0)",
            },
        )
