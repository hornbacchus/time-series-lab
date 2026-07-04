"""Harness Integrity Audit AUD-L1 — ``pp_test`` TREND-spec (``regression=ct``)
parity check (additive; ``p3_pp`` unchanged).

The audit's ledger fold-in found the KPSS/PP knob-gap note HALF-retired:
``p3_kpss_trend`` validates the kpss ``regression`` knob (c AND ct vs urca),
but ``pp_test`` exposes the same ``regression`` knob and NO check exercised it
— ``p3_pp`` validates the default (``c``) spec only. This check closes the
residual on the ``p3_kpss_trend`` shape (B.i pure parameter-coverage — the
trend spec over the SAME single PP statistic; no orchestration arm):

  - Arm 1: ``regression=ct`` at the engine's realized auto bandwidth
    (read back; identical-parameterization) vs ``urca::ur.pp`` Z-tau
    ``model="trend"`` at the MATCHED lag.
  - Arm 2: pinned ``lags=5`` — bandwidth-robustness, mirrors p3_pp.
  - Arm 3 (knob-movement contrast): the engine's ``c`` vs ``ct`` statistics
    DIFFER materially on the trending fixture — the knob is LIVE (an inert
    ``regression`` read -> identical stats -> BLOCK).

Bands are ``p3_pp``'s widened Pattern-J class (arch-vs-urca kernel/divisor
convention divergence — NOT bit-exact by design).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._stationarity_components import (
    pp_reference,
)
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_PIN_LAG = 5


def _trend_stationary(*, seed: int, n: int = 400, phi: float = 0.5,
                      slope: float = 0.05, burn: int = 200) -> np.ndarray:
    """Stationary AR(1) around a deterministic linear trend — the
    representative ``regression=ct`` use case (mirrors p3_kpss_trend)."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + burn)
    y = np.zeros(n + burn)
    for t in range(1, n + burn):
        y[t] = phi * y[t - 1] + eps[t]
    return slope * np.arange(n) + y[burn:]


class PpTrendParity(P3ParityCheck):
    """PP trend-spec (regression=ct) component cross-package extension +
    knob-movement contrast (AUD-L1)."""

    technique_id = "p3_pp_trend"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The PP Z-tau statistic is closed-form (Newey-West-corrected DF "
        "regression). The trend spec (regression=ct) detrends with a linear "
        "term and is validated cross-package vs urca::ur.pp type='Z-tau' "
        "model='trend' at the engine's realized bandwidth — the same "
        "widened Pattern-J band as p3_pp (arch-vs-urca kernel/divisor "
        "convention). B.i pure parameter-coverage on the p3_kpss_trend "
        "shape, plus a knob-movement contrast (c vs ct stats differ on a "
        "trending fixture — an inert regression read BLOCKs)."
    )

    SEED = 7  # pinned; mirrors p3_kpss_trend's fixture discipline

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _trend_stationary(seed=self.SEED)}

    @staticmethod
    def _engine(y: np.ndarray, regression: str, lags):
        from techniques.pp_test import _run_pp_single  # noqa: E402
        return _run_pp_single(np.asarray(y, dtype=np.float64), regression, lags)

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        auto = self._engine(y, "ct", None)
        pinned = self._engine(y, "ct", _PIN_LAG)
        c_auto = self._engine(y, "c", None)
        return {
            "auto": {"stat": float(auto["stat"]), "lag": int(auto["used_lag"])},
            "pinned": {"stat": float(pinned["stat"]), "lag": int(pinned["used_lag"])},
            "c_stat": float(c_auto["stat"]),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = fixture["y"]
        # Re-derive the engine's realized auto bandwidth (deterministic) so
        # urca runs at the matched lag (identical-parameterization).
        auto_lag = int(self._engine(y, "ct", None)["used_lag"])
        return {
            "auto": pp_reference(y, lag=auto_lag, regression="ct"),
            "pinned": pp_reference(y, lag=_PIN_LAG, regression="ct"),
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

        # Knob-movement contrast: c vs ct must differ materially on the
        # trending fixture (an inert regression read -> identical -> BLOCK).
        gap = abs(tsl["c_stat"] - tsl["auto"]["stat"])
        min_gap = float(ladder["knob_contrast"]["min_abs_gap"])
        k_status = "PASS" if gap >= min_gap else "BLOCK"
        primary["regression_knob_moves_stat"] = {
            "status": k_status, "c_stat": tsl["c_stat"],
            "ct_stat": tsl["auto"]["stat"], "abs_gap": round(gap, 6),
            "min_abs_gap": min_gap,
        }
        statuses.append(k_status)

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
                "urca_model": "trend",
                "ct_auto_realized_lag": tsl["auto"]["lag"],
                "ct_pinned_lag": tsl["pinned"]["lag"],
                "ct_auto_abs_diff": primary["ct_auto"].get("abs_diff"),
                "ct_pinned_abs_diff": primary["ct_pinned"].get("abs_diff"),
            },
        )
