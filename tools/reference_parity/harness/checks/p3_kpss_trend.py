"""Phase 7+ deeper-validation, scope-extension UNIT 2 — ``kpss_test``
TREND-spec (``reg=ct``) parity check (additive; ``p3_kpss`` unchanged).

``kpss_test`` is a T1-core member. Standalone ``p3_kpss`` validates only
``reg=c`` / ``LAG=5`` vs ``urca::ur.kpss type="mu"`` (bit-exact); the adf
pilot additionally discharged the ``reg=c`` / ``nlags="auto"`` level path
(identical ``_run_kpss_single(...,"c","auto")`` call, 3.89e-16). The
genuinely-new emitted surface is the **trend spec** ``reg=ct`` — a
DIFFERENT statistic (``urca::ur.kpss type="tau"``), never validated.

Class-B verdict: **B.i pure parameter-coverage** — the gap is the
``reg=ct`` spec over the SAME single KPSS statistic, with a trivial
single-threshold decision (``p < alpha`` <=> stat > CV). So this is a
COMPONENT cross-package EXTENSION only — NO orchestration arm, NO
functional check, NO negative-control mutants (kpss standalone emits no
verdict that combines multiple sub-results; manufacturing a functional
check for a single threshold would be apparatus bloat).

Two ``reg=ct`` arms, both bit-exact vs ``urca::ur.kpss type="tau"`` via the
shared (UNCHANGED) ``_stationarity_components.kpss_reference`` helper —
this is its SECOND caller (the pilot called it at triage params; here at
standalone trend params), no new helper:
  - Arm 1: ``nlags="auto"`` (the new DEFAULT trend surface) — validated at
    the engine's realized library-selected bandwidth (read back).
  - Arm 2: pinned ``LAG=5`` — bandwidth-robustness, mirrors p3_kpss.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._stationarity_components import (
    kpss_reference,
)
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_PIN_LAG = 5


def _trend_stationary(*, seed: int, n: int = 400, phi: float = 0.5,
                      slope: float = 0.05, burn: int = 200) -> np.ndarray:
    """Stationary AR(1) around a deterministic linear trend — the
    representative ``reg=ct`` use case (trend-stationary)."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn)
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return slope * np.arange(n) + y[burn:]


class KpssTrendParity(P3ParityCheck):
    """KPSS trend-spec (reg=ct) component cross-package extension."""

    technique_id = "p3_kpss_trend"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "KPSS eta statistic is closed-form (partial-sum-of-residuals over "
        "a long-run-variance estimator). The trend spec (reg=ct) detrends "
        "with a linear term and is validated cross-package vs "
        "urca::ur.kpss type='tau' at the engine's realized bandwidth — "
        "same closed-form class as the level spec (type='mu', p3_kpss). "
        "B.i pure parameter-coverage: the only decision is a single "
        "threshold (p<alpha), so there is no orchestration arm — this is "
        "a component cross-package extension, not a combined-classification "
        "check."
    )

    SEED = 7  # pinned; reg=ct auto bandwidth -> used_lag 7 on this series

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _trend_stationary(seed=self.SEED)}

    @staticmethod
    def _engine(y: np.ndarray, nlags):
        from techniques.kpss_test import _run_kpss_single  # noqa: E402
        return _run_kpss_single(np.asarray(y, dtype=np.float64), "ct", nlags)

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        auto = self._engine(y, "auto")
        pinned = self._engine(y, _PIN_LAG)
        return {
            "auto": {"stat": float(auto["stat"]), "lag": int(auto["used_lag"])},
            "pinned": {"stat": float(pinned["stat"]), "lag": int(pinned["used_lag"])},
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        # Re-derive the engine's realized auto bandwidth (deterministic) so
        # urca runs at the matched lag — validates the type="tau" statistic
        # GIVEN the library-selected bandwidth.
        auto_lag = int(self._engine(y, "auto")["used_lag"])
        return {
            "auto": kpss_reference(y, lag=auto_lag, regression="ct"),
            "pinned": kpss_reference(y, lag=_PIN_LAG, regression="ct"),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["ct_auto"] = _compare_scalar(
            tsl["auto"]["stat"], ref["auto"]["test_statistic"], ladder["primary"])
        primary["ct_pinned"] = _compare_scalar(
            tsl["pinned"]["stat"], ref["pinned"]["test_statistic"], ladder["primary"])
        for kk in ("ct_auto", "ct_pinned"):
            statuses.append(primary[kk]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "urca_version": ref["auto"].get("urca_version", "unknown"),
                "urca_type": "tau",
                "ct_auto_realized_lag": tsl["auto"]["lag"],
                "ct_pinned_lag": tsl["pinned"]["lag"],
                "ct_auto_abs_diff": primary["ct_auto"]["abs_diff"],
                "ct_pinned_abs_diff": primary["ct_pinned"]["abs_diff"],
            },
        )
