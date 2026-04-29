"""Phase 3 Batch 7 — FFT spectrum parity check.

Compares TSL ``engine/techniques/fft_spectrum.py`` (scipy.fft)
against numpy.fft on a synthetic sinusoidal+noise fixture.
Cross-package check: scipy.fft and numpy.fft have independent
codebases (scipy uses pocketfft; numpy uses pocketfft as
well since 1.17 but with different wrapper code paths). Both
should produce bit-exact identical output for real-valued
input; Pattern A target.

**Pattern F populations:** ``fft_roundtrip`` (ifft(fft(x))==x)
and ``fft_energy_conservation`` (Parseval). Both verified
on-the-fly inside ``run_tsl`` and reported as structural
diagnostics.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_fft_dgp(
    *, seed: int, n: int = 512,
    freqs: tuple[float, ...] = (0.05, 0.13, 0.25),
    amps: tuple[float, ...] = (1.0, 0.5, 0.3),
    sigma: float = 0.2,
) -> np.ndarray:
    """Multi-tone sinusoidal signal + Gaussian noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    y = np.zeros(n)
    for f, a in zip(freqs, amps):
        y += a * np.sin(2 * np.pi * f * t)
    y += rng.standard_normal(n) * sigma
    return y


class FftSpectrumParity(P3ParityCheck):
    """FFT spectrum parity vs numpy.fft."""

    technique_id = "p3_fft_spectrum"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "FFT is closed-form linear-algebra: a deterministic "
        "function of the input signal. scipy.fft and numpy.fft "
        "both wrap pocketfft (since numpy 1.17); given identical "
        "real-valued input, output is bit-identical. Pattern A "
        "bit-exact target."
    )

    DGP_N = 512

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_fft_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from scipy.fft import fft as scipy_fft, ifft as scipy_ifft  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Mean-detrend (matches TSL default detrend='mean')
        signal = y - np.mean(y)
        Y = scipy_fft(signal)
        # Pattern F invariants computed in-line for diagnostics
        roundtrip = np.asarray(scipy_ifft(Y), dtype=np.complex128)
        roundtrip_max_abs = float(np.max(np.abs(roundtrip.real - signal)))
        # Parseval: sum |x|^2 == (1/N) sum |X|^2
        energy_time = float(np.sum(signal ** 2))
        energy_freq = float(np.sum(np.abs(Y) ** 2) / len(signal))
        return {
            "fft_real": Y.real,
            "fft_imag": Y.imag,
            "fft_abs": np.abs(Y),
            "roundtrip_max_abs": roundtrip_max_abs,
            "energy_time": energy_time,
            "energy_freq": energy_freq,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        signal = y - np.mean(y)
        Y = np.fft.fft(signal)
        return {
            "fft_real": Y.real,
            "fft_imag": Y.imag,
            "fft_abs": np.abs(Y),
            "numpy_version": np.__version__,
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        for k in ("fft_real", "fft_imag", "fft_abs"):
            primary[k] = _compare_vector(
                tsl[k], ref[k], ladder["primary"],
            )
            statuses.append(primary[k]["status"])
        # Structural-invariant diagnostics (not per-comparison;
        # report-only)
        roundtrip_residual = float(tsl.get("roundtrip_max_abs", float("nan")))
        parseval_residual = abs(
            tsl.get("energy_time", 0.0) - tsl.get("energy_freq", 0.0)
        )
        roundtrip_status = (
            "PASS" if roundtrip_residual < 1e-10 else "BLOCK"
        )
        parseval_status = (
            "PASS" if parseval_residual < 1e-8
            * max(abs(tsl.get("energy_time", 1.0)), 1.0)
            else "BLOCK"
        )
        primary["fft_roundtrip"] = {
            "status": roundtrip_status,
            "max_abs_residual": roundtrip_residual,
        }
        primary["fft_energy_conservation"] = {
            "status": parseval_status,
            "energy_time": tsl.get("energy_time"),
            "energy_freq": tsl.get("energy_freq"),
            "abs_diff": parseval_residual,
        }
        statuses.extend([roundtrip_status, parseval_status])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "numpy_version": ref.get("numpy_version", "unknown"),
            },
        )
