"""Phase 3 — GCC-PHAT delay-RECOVERY discrimination check (F-CL-GCC-DELAY).

A verified-discriminating check that the engine's ``gcc_phat_delay.run()``
recovers a KNOWN delay correctly across three axes the prior read-off got wrong:

  - SIGN:       a known +5 recovers +5 AND a known -5 recovers -5.
  - SCALE:      a known integer recovers EXACTLY on Fast / Balanced / Thorough
                (interp_factor 1 / 4 / 16) -- the presets where the broken
                read-off reported -5.0 / -1.25 / -0.31 (= -true / interp_factor).
  - SUB-SAMPLE: a fractional delay (+5.5, -3.25) recovers to the interpolation
                grid at Balanced / Thorough (confirming the frequency-domain
                interpolation works once the lag axis is rescaled correctly).

This is engine-vs-known-truth (the "reference" is the injected true delay), and
it FAILS the pre-fix build / PASSES the fixed build by construction. It exists
because the sibling p3_gcc_phat parity check called the reference reimplementation
in BOTH arms and never exercised the engine -- so the broken read-off shipped
undetected (a bocpd-S79-class non-check). The fixture is broadband white noise:
PHAT (1/|Gxy|) whitens all frequencies, so it needs a full-band signal.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _broadband_pair(n: int, D: float, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Broadband white noise where the second series is the first delayed by D
    (x leads y by D, so the GCC-PHAT delay convention reports +D). Integer D via
    slicing; fractional D via an exact FFT phase shift (band-limited recovery)."""
    rng = np.random.default_rng(seed)
    src = rng.standard_normal(n + 200)
    if float(D).is_integer():
        di = int(D)
        x = src[100:100 + n]
        y = src[100 - di:100 - di + n]
    else:
        base = src[100:100 + n]
        Xf = np.fft.rfft(base)
        f = np.fft.rfftfreq(n)
        y = np.fft.irfft(Xf * np.exp(-1j * 2 * np.pi * f * D), n=n)
        x = base
    x = x + 0.01 * rng.standard_normal(n)
    y = y + 0.01 * rng.standard_normal(n)
    return x, y


class GccPhatRecoveryParity(P3ParityCheck):
    technique_id = "p3_gcc_phat_recovery"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Delay recovery against an injected ground-truth delay -- the argmax of "
        "the (frequency-domain interpolated) GCC-PHAT surface is a deterministic, "
        "closed-form read-off. Discriminating by construction: the pre-fix "
        "read-off reported -true/interp_factor; the fix recovers the true signed "
        "real-sample delay."
    )
    DGP_N = 2048
    FIX_SEED = 11

    # (label, true_delay, preset). Integer cases on all three presets (sign +
    # scale across interp 1/4/16); sub-sample cases on Balanced/Thorough only
    # (Fast interp_factor=1 has 1-sample resolution and cannot resolve a fraction).
    CASES: tuple[tuple[str, float, str], ...] = (
        ("Fast/+5", 5.0, "Fast"),
        ("Balanced/+5", 5.0, "Balanced"),
        ("Thorough/+5", 5.0, "Thorough"),
        ("Fast/-5", -5.0, "Fast"),
        ("Balanced/-5", -5.0, "Balanced"),
        ("Thorough/-5", -5.0, "Thorough"),
        ("Balanced/+5.5", 5.5, "Balanced"),
        ("Thorough/+5.5", 5.5, "Thorough"),
        ("Balanced/-3.25", -3.25, "Balanced"),
        ("Thorough/-3.25", -3.25, "Thorough"),
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"seed": seed}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Run the engine on each (delay, preset) case; return the recovered
        delay per case from audit_fields."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.gcc_phat_delay as gcc_mod  # type: ignore

        recovered: dict[str, float] = {}
        for label, D, preset in self.CASES:
            x, y = _broadband_pair(self.DGP_N, D, seed=self.FIX_SEED)
            ctx = RunContext({
                "run_id": "p3_gcc_phat_recovery",
                "technique_id": "gcc_phat_delay",
                "preset": preset,
                "seed": 42,
                "frequency": "",
                "time": list(range(self.DGP_N)),
                "series": [
                    {"name": "x", "values": x.tolist()},
                    {"name": "y", "values": y.tolist()},
                ],
                "params": {},
            })
            resp = gcc_mod.run(ctx, lambda *a, **kw: None)
            if resp.get("status") != "success":
                raise RuntimeError(
                    f"engine gcc_phat_delay failed on {label}: "
                    f"{resp.get('error_message')}"
                )
            recovered[label] = float(resp["audit_fields"]["estimated_delay_samples"])
        return recovered

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, float]:
        """The 'reference' is the injected ground-truth delay per case."""
        return {label: float(D) for label, D, _ in self.CASES}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        for label, D, _ in self.CASES:
            primary[label] = _compare_scalar(
                float(tsl[label]), float(ref[label]), ladder["primary"],
            )
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "recovered": {k: round(float(v), 4) for k, v in tsl.items()},
                "true": {k: float(v) for k, v in ref.items()},
            },
        )
