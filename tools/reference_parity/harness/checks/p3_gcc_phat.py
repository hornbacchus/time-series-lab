"""Phase 3 Batch 10 — GCC-PHAT delay parity check.

TSL ``gcc_phat_delay.py`` (Generalized Cross-Correlation with
Phase Transform) vs from-scratch paper-formula self-parity
(Knapp-Carter 1976). Tier A closed-form: argmax of inverse
FFT of normalized cross-power-spectrum.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_delayed_pair(*, seed: int, n: int = 512,
                            true_delay: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Y is X delayed by `true_delay` samples + noise."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n + true_delay)
    y = np.roll(x, true_delay)[:n]
    x = x[:n]
    return x, y + 0.05 * rng.standard_normal(n)


def _gcc_phat(x: np.ndarray, y: np.ndarray) -> int:
    """Reference Knapp-Carter 1976 GCC-PHAT. Returns the integer-sample DELAY D
    where y[t] = x[t - D] -- positive D means the first series (x) leads the
    second (y), matching cross_correlation_lag's convention. R = X*conj(Y) peaks
    at the raw lag -D, so the argmax position is negated to report the delay D
    (the engine applies the same negation; F-CL-GCC-DELAY convention)."""
    n = len(x) + len(y)
    X = np.fft.fft(x, n=n)
    Y = np.fft.fft(y, n=n)
    R = X * np.conj(Y)
    R_phat = R / (np.abs(R) + 1e-15)
    cc = np.real(np.fft.ifft(R_phat))
    cc = np.concatenate([cc[-len(x) + 1:], cc[:len(x)]])
    delay = -int(np.argmax(np.abs(cc)) - (len(x) - 1))
    return delay


class GccPhatParity(P3ParityCheck):
    technique_id = "p3_gcc_phat"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "GCC-PHAT is closed-form FFT-based correlation peak "
        "estimation. The engine arm invokes gcc_phat_delay.run() "
        "via RunContext and reads the recovered delay from "
        "audit_fields; the reference is the Knapp-Carter 1976 "
        "argmax formula. (Prior to the F-CL-GCC-DELAY fix this "
        "arm called the reference reimplementation in BOTH arms "
        "and never exercised the engine, so the broken read-off "
        "went undetected.)"
    )
    DGP_N = 512
    TRUE_DELAY = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_delayed_pair(
            seed=seed, n=self.DGP_N, true_delay=self.TRUE_DELAY,
        )
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke the engine wrapper via RunContext and read the recovered
        delay from audit_fields (genuinely exercises gcc_phat_delay.run())."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.gcc_phat_delay as gcc_mod  # type: ignore

        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_gcc_phat_parity",
            "technique_id": "gcc_phat_delay",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(x))),
            "series": [
                {"name": "x", "values": x.tolist()},
                {"name": "y", "values": y.tolist()},
            ],
            "params": {},
        })
        resp = gcc_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"engine gcc_phat_delay failed: {resp.get('error_message')}"
            )
        delay = float(resp["audit_fields"]["estimated_delay_samples"])
        return {"delay": delay}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        return {"delay": int(_gcc_phat(x, y))}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "delay": _compare_scalar(
                float(tsl["delay"]), float(ref["delay"]), ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "true_delay": int(self.TRUE_DELAY),
                "tsl_delay": int(tsl["delay"]), "ref_delay": int(ref["delay"]),
            },
        )
