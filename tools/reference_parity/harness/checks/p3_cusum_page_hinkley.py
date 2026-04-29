"""Phase 3 Batch 6 — CUSUM / Page-Hinkley parity check.

Compares TSL ``engine/techniques/cusum_page_hinkley.py`` against
a from-scratch reference that mirrors TSL's recursion math
verbatim. Catches wrapper-level bugs (preprocessing, param
forwarding, audit-field rounding, alarm filtering) without
chasing the multi-package methodology zoo (R ``cpm``, R
``changepoint``, scikit-multiflow, river — each implements a
slightly different CUSUM/PH variant).

**Pattern A self-parity** — same rationale as p3_bocpd.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_step_dgp(
    *, seed: int, n: int = 400, shift_at: int = 200,
    pre_mean: float = 0.0, post_mean: float = 1.0,
    sigma: float = 1.0,
) -> np.ndarray:
    """Single mean shift at t=shift_at."""
    rng = np.random.default_rng(seed)
    y = np.empty(n)
    y[:shift_at] = pre_mean + rng.standard_normal(shift_at) * sigma
    y[shift_at:] = post_mean + rng.standard_normal(n - shift_at) * sigma
    return y


def _cusum_ph_reference(
    y: np.ndarray, *,
    target: float, cusum_k: float, cusum_h: float,
    ph_delta: float, ph_lambda: float,
) -> dict[str, Any]:
    """Reference CUSUM + Page-Hinkley implementation.

    Mirrors TSL's recursion verbatim (same standardization,
    same alarm + reset logic, same warmup-of-10 on PH).
    """
    n = len(y)
    z = y - target
    S_up = np.zeros(n)
    S_down = np.zeros(n)
    cusum_up_alarms: list = []
    cusum_down_alarms: list = []

    for t in range(n):
        prev_up = S_up[t - 1] if t > 0 else 0.0
        prev_dn = S_down[t - 1] if t > 0 else 0.0
        S_up[t] = max(0.0, prev_up + z[t] - cusum_k)
        S_down[t] = max(0.0, prev_dn - z[t] - cusum_k)
        if S_up[t] > cusum_h:
            cusum_up_alarms.append(t)
            S_up[t] = 0.0
        if S_down[t] > cusum_h:
            cusum_down_alarms.append(t)
            S_down[t] = 0.0

    m_t = np.zeros(n)
    M_t = np.zeros(n)
    PH_up = np.zeros(n)
    m_t_down = np.zeros(n)
    M_t_up = np.zeros(n)
    PH_down = np.zeros(n)
    ph_up_alarms: list = []
    ph_down_alarms: list = []
    running_mean = 0.0
    for t in range(n):
        running_mean = (running_mean * t + y[t]) / (t + 1)
        m_t[t] = (m_t[t - 1] if t > 0 else 0.0) + (
            y[t] - running_mean - ph_delta
        )
        M_t[t] = min(M_t[t - 1] if t > 0 else m_t[t], m_t[t])
        PH_up[t] = m_t[t] - M_t[t]
        if PH_up[t] > ph_lambda and t > 10:
            ph_up_alarms.append(t)
        m_t_down[t] = (m_t_down[t - 1] if t > 0 else 0.0) + (
            y[t] - running_mean + ph_delta
        )
        M_t_up[t] = max(M_t_up[t - 1] if t > 0 else m_t_down[t], m_t_down[t])
        PH_down[t] = M_t_up[t] - m_t_down[t]
        if PH_down[t] > ph_lambda and t > 10:
            ph_down_alarms.append(t)

    return {
        "n_cusum_up": len(cusum_up_alarms),
        "n_cusum_down": len(cusum_down_alarms),
        "n_ph_up": len(ph_up_alarms),
        "n_ph_down": len(ph_down_alarms),
        "cusum_up_alarms": cusum_up_alarms,
        "cusum_down_alarms": cusum_down_alarms,
        "ph_up_alarms": ph_up_alarms,
        "ph_down_alarms": ph_down_alarms,
    }


class CusumPageHinkleyParity(P3ParityCheck):
    """CUSUM + Page-Hinkley parity vs from-scratch reference."""

    technique_id = "p3_cusum_page_hinkley"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "CUSUM and Page-Hinkley are both deterministic "
        "recursive accumulators with closed-form decision "
        "rules. TSL and the from-scratch reference implement "
        "identical recursion math verbatim; bit-exact alarm "
        "counts + indices expected. R cpm / changepoint use "
        "different formulations (CPM tests; PELT-style cost "
        "functions); a self-parity reference avoids a "
        "Pattern J methodology zoo."
    )

    DGP_N = 400
    SHIFT_AT = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_step_dgp(
            seed=seed, n=self.DGP_N, shift_at=self.SHIFT_AT,
            pre_mean=0.0, post_mean=1.5, sigma=1.0,
        )}

    def _common_params(self, y: np.ndarray) -> dict[str, float]:
        sigma = float(np.std(y, ddof=1))
        mu = float(np.mean(y))
        # Lower thresholds vs default to actually trigger alarms
        # on the synthetic step fixture (default 5*sigma is too
        # conservative for the 1.5-sigma shift fixture).
        return {
            "target": mu,
            "cusum_k": 0.5 * sigma,
            "cusum_h": 3.0 * sigma,
            "ph_delta": 0.005 * sigma,
            "ph_lambda": 20.0,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques.cusum_page_hinkley import run as cph_run  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        params = self._common_params(y)
        # Use Fast preset to skip bootstrap (deterministic).
        ctx = RunContext({
            "run_id": "p3_cph_tsl",
            "technique_id": "cusum_page_hinkley",
            "preset": "Fast", "seed": 42, "frequency": "irregular",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": params,
        })
        res = cph_run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL CUSUM/PH failed: {res.get('error_message')}"
            )
        a = res["audit_fields"]
        return {
            "n_cusum_up": int(a.get("n_cusum_up", 0)),
            "n_cusum_down": int(a.get("n_cusum_down", 0)),
            "n_ph_up": int(a.get("n_ph_up", 0)),
            "n_ph_down": int(a.get("n_ph_down", 0)),
            "params": params,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        params = self._common_params(y)
        ref = _cusum_ph_reference(y, **params)
        return {
            "n_cusum_up": int(ref["n_cusum_up"]),
            "n_cusum_down": int(ref["n_cusum_down"]),
            "n_ph_up": int(ref["n_ph_up"]),
            "n_ph_down": int(ref["n_ph_down"]),
            "params": params,
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        for k in ("n_cusum_up", "n_cusum_down", "n_ph_up", "n_ph_down"):
            primary[k] = _compare_scalar(
                float(tsl[k]), float(ref[k]), ladder["primary"],
            )
        any_block = any(p["status"] == "BLOCK" for p in primary.values())
        any_caveat = any(p["status"] == "CAVEAT" for p in primary.values())
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "true_shift_at": int(self.SHIFT_AT),
                "tsl_alarms_total": (
                    tsl["n_cusum_up"] + tsl["n_cusum_down"]
                    + tsl["n_ph_up"] + tsl["n_ph_down"]
                ),
                "ref_alarms_total": (
                    ref["n_cusum_up"] + ref["n_cusum_down"]
                    + ref["n_ph_up"] + ref["n_ph_down"]
                ),
            },
        )
