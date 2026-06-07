"""Phase 7+ — fft_spectrum hollow-strong record-correction: a genuine
external-AUTHORITY check (engine-invoked) replacing the same-backend record.

★ The existing `p3_fft_spectrum` is M4-same-lib: `run_tsl` calls `scipy.fft`
DIRECTLY (not engine-invoked) and `run_reference` calls `numpy.fft` — both wrap
**pocketfft** (admitted in its own docstring), so the recorded "cross-package"
is self-consistency that validates nothing about correctness, and the engine is
not even in the loop. The FFT itself is correct (library primitive); the RECORD
overstated.

This check is the genuine fix: ENGINE-INVOKED (RunContext) validation of the
engine's emitted DOMINANT FREQUENCY against the ANALYTIC truth of a KNOWN
multi-tone signal (external authority — the construction is the reference, not
another pocketfft). Plus a white-noise NEGATIVE CONTROL wired in-harness (no
dominant tone → low power-concentration). Closes BOTH hollows: the same-backend
trap (external-authority reference) and scipy-direct-not-engine (RunContext).
`p3_fft_spectrum` stays byte-identical.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N = 512
_K1, _K2 = 32, 96          # integer DFT bins → exact frequencies k/N
_AMP1, _AMP2 = 1.0, 0.5    # f1 is the DOMINANT tone (larger amplitude)


def _multitone():
    t = np.arange(_N)
    f1, f2 = _K1 / _N, _K2 / _N
    y = (_AMP1 * np.cos(2 * np.pi * f1 * t)
         + _AMP2 * np.cos(2 * np.pi * f2 * t)
         + 0.01 * np.random.default_rng(0).standard_normal(_N))
    return y, f1, f2


def _white_noise():
    return np.random.default_rng(1).standard_normal(_N)


def _run_engine_fft(y):
    from techniques.base import RunContext  # type: ignore
    import techniques.fft_spectrum as fft_mod  # type: ignore
    ctx = RunContext({
        "run_id": "p3_fft_analytic", "technique_id": "fft_spectrum",
        "preset": "Balanced", "seed": 42, "frequency": "",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(map(float, y))}], "params": {},
    })
    with _w.catch_warnings():
        _w.simplefilter("ignore")
        resp = fft_mod.run(ctx, lambda *a, **k: None)
    if resp.get("status") != "success":
        raise RuntimeError(f"engine fft_spectrum failed: {resp.get('error_message')}")
    au = resp.get("audit_fields", {})
    peak_tbl = next((t for t in resp["tables"]
                     if t.get("name") == "Dominant Frequencies"), None)
    peak_freqs = ([float(r[1]) for r in peak_tbl["rows"]] if peak_tbl else [])
    return {"dominant_frequency": float(au.get("dominant_frequency", float("nan"))),
            "top_peak_power_pct": float(au.get("top_peak_power_pct", float("nan"))),
            "peak_freqs": peak_freqs,
            "freq_resolution": float(au.get("frequency_resolution", 1.0 / _N))}


class FftAnalyticParity(P3ParityCheck):
    """Engine FFT dominant-frequency vs the analytic truth of a known
    multi-tone signal (external authority) + white-noise negative control."""

    technique_id = "p3_fft_analytic"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The FFT of a KNOWN multi-tone signal has an ANALYTIC spectrum — the "
        "dominant frequency is the larger-amplitude tone's bin, exactly. The "
        "engine's emitted dominant_frequency is validated against that "
        "construction (external authority), engine-invoked, with a white-noise "
        "negative control (no dominant tone → low power concentration). NOT a "
        "same-backend FFT-vs-FFT check (the prior scipy.fft-vs-numpy.fft record "
        "was both pocketfft) — this validates correctness against the math."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, f1, f2 = _multitone()
        return {"tone": y, "noise": _white_noise(), "f1": f1, "f2": f2}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        tone = _run_engine_fft(fixture["tone"])
        noise = _run_engine_fft(fixture["noise"])
        return {"tone": tone, "noise_top_pct": noise["top_peak_power_pct"]}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # The analytic truth: the known tone frequencies. No FFT library used.
        return {"f1": float(fixture["f1"]), "f2": float(fixture["f2"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        tone = tsl["tone"]
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Arm 1 — dominant frequency == the dominant tone f1 (exact bin).
        dom_diff = abs(tone["dominant_frequency"] - ref["f1"])
        dstat = "PASS" if dom_diff < ladder["dominant_freq"]["abs_tol"] else "BLOCK"
        primary["dominant_frequency_vs_analytic"] = {
            "status": dstat, "engine": tone["dominant_frequency"],
            "analytic_f1": ref["f1"], "abs_diff": dom_diff}
        statuses.append(dstat)

        # Arm 2 — both known tones present in the engine's peak table.
        tol = float(ladder["tone_match"]["tol"])
        pf = np.asarray(tone["peak_freqs"], float)
        f1_in = bool(pf.size and np.min(np.abs(pf - ref["f1"])) < tol)
        f2_in = bool(pf.size and np.min(np.abs(pf - ref["f2"])) < tol)
        tstat = "PASS" if (f1_in and f2_in) else "BLOCK"
        primary["tones_detected"] = {"status": tstat, "f1_in": f1_in,
                                     "f2_in": f2_in, "peak_freqs": tone["peak_freqs"]}
        statuses.append(tstat)

        # Arm 3 — white-noise NEGATIVE CONTROL (in-harness, asserted):
        # the tone concentrates power; white noise does not. Discriminates.
        disc = ladder["discrimination"]
        tone_pct = tone["top_peak_power_pct"]
        noise_pct = tsl["noise_top_pct"]
        ok = (tone_pct >= disc["tone_min_pct"]) and (noise_pct <= disc["noise_max_pct"])
        cstat = "PASS" if ok else "BLOCK"
        primary["discrimination_tone_vs_noise"] = {
            "status": cstat, "tone_top_power_pct": tone_pct,
            "noise_top_power_pct": noise_pct,
            "note": ("negative control: white noise has no dominant tone -> low "
                     "power concentration vs the tone's high concentration")}
        statuses.append(cstat)

        any_block = any(s == "BLOCK" for s in statuses)
        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "reference": ("analytic dominant-frequency of a known multi-tone "
                              "signal (external authority) — NOT same-backend FFT"),
                "engine_invoked": True,
                "dominant_freq_abs_diff": dom_diff,
                "tone_top_power_pct": tone_pct, "noise_top_power_pct": noise_pct,
                "freq_resolution": tone["freq_resolution"],
            },
        )
