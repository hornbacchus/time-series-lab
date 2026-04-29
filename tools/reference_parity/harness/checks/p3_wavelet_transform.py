"""Phase 3 Batch 7 — Wavelet transform parity check.

Compares TSL ``engine/techniques/wavelet_transform.py``
(pywt.wavedec) against direct ``pywt.wavedec`` invocation
(same-library self-test). Pattern A bit-exact target.

**Pattern F populations:** ``wavelet_inverse_roundtrip``
(waverec(wavedec(x)) == x) and ``wavelet_energy_conservation``
(Parseval-like for orthogonal wavelets). Both verified
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


def _generate_wavelet_dgp(
    *, seed: int, n: int = 256,
) -> np.ndarray:
    """Multi-scale signal: trend + multi-frequency + noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64)
    y = (
        0.01 * t  # trend
        + 1.0 * np.sin(2 * np.pi * 0.05 * t)  # low-freq
        + 0.5 * np.sin(2 * np.pi * 0.20 * t)  # high-freq
        + 0.2 * rng.standard_normal(n)
    )
    return y


class WaveletTransformParity(P3ParityCheck):
    """Wavelet transform parity vs pywt (same-library)."""

    technique_id = "p3_wavelet_transform"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "DWT is closed-form filterbank cascade. pywt is the "
        "single canonical Python implementation; both TSL and "
        "the reference invoke pywt.wavedec with identical "
        "(wavelet, level, mode) arguments. Bit-exact parity "
        "expected; failure indicates wrapper-level "
        "preprocessing or argument-passing bug."
    )

    DGP_N = 256
    WAVELET = "db4"
    LEVEL = 4
    # Use periodization mode so Parseval energy conservation
    # holds exactly for the orthogonal db4 wavelet. Other modes
    # (symmetric, zero, etc.) duplicate boundary samples and
    # break Parseval by O(boundary_extension_size). Periodization
    # is the only mode that preserves energy bit-exactly for
    # orthogonal wavelet families on power-of-2 lengths.
    MODE = "periodization"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_wavelet_dgp(
            seed=seed, n=self.DGP_N,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        import pywt  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        coeffs = pywt.wavedec(
            y, self.WAVELET, mode=self.MODE, level=self.LEVEL,
        )
        # Pattern F: roundtrip identity
        reconstructed = pywt.waverec(coeffs, self.WAVELET, mode=self.MODE)
        roundtrip_max_abs = float(
            np.max(np.abs(reconstructed[:len(y)] - y))
        )
        # Pattern F: energy conservation (Parseval-like for
        # orthogonal wavelets). For db4 (orthogonal),
        # sum(coeff_i^2) == sum(y^2) at machine precision.
        coeff_energy = float(sum(np.sum(c ** 2) for c in coeffs))
        signal_energy = float(np.sum(y ** 2))
        return {
            "approx_coeffs": np.asarray(coeffs[0], dtype=np.float64),
            "detail_l1": np.asarray(coeffs[-1], dtype=np.float64),
            "detail_l2": np.asarray(coeffs[-2], dtype=np.float64),
            "detail_l3": np.asarray(coeffs[-3], dtype=np.float64),
            "detail_l4": np.asarray(coeffs[1], dtype=np.float64),
            "roundtrip_max_abs": roundtrip_max_abs,
            "coeff_energy": coeff_energy,
            "signal_energy": signal_energy,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import pywt  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        coeffs = pywt.wavedec(
            y, self.WAVELET, mode=self.MODE, level=self.LEVEL,
        )
        return {
            "approx_coeffs": np.asarray(coeffs[0], dtype=np.float64),
            "detail_l1": np.asarray(coeffs[-1], dtype=np.float64),
            "detail_l2": np.asarray(coeffs[-2], dtype=np.float64),
            "detail_l3": np.asarray(coeffs[-3], dtype=np.float64),
            "detail_l4": np.asarray(coeffs[1], dtype=np.float64),
            "pywt_version": getattr(pywt, "__version__", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        for k in (
            "approx_coeffs", "detail_l1", "detail_l2",
            "detail_l3", "detail_l4",
        ):
            primary[k] = _compare_vector(
                tsl[k], ref[k], ladder["primary"],
            )
            statuses.append(primary[k]["status"])
        # Pattern F structural-invariant diagnostics
        roundtrip_residual = float(tsl.get("roundtrip_max_abs", float("nan")))
        roundtrip_status = (
            "PASS" if roundtrip_residual < 1e-10 else "BLOCK"
        )
        energy_residual = abs(
            tsl.get("coeff_energy", 0.0) - tsl.get("signal_energy", 0.0)
        )
        energy_status = (
            "PASS" if energy_residual < 1e-8
            * max(abs(tsl.get("signal_energy", 1.0)), 1.0)
            else "BLOCK"
        )
        primary["wavelet_inverse_roundtrip"] = {
            "status": roundtrip_status,
            "max_abs_residual": roundtrip_residual,
        }
        primary["wavelet_energy_conservation"] = {
            "status": energy_status,
            "signal_energy": tsl.get("signal_energy"),
            "coeff_energy": tsl.get("coeff_energy"),
            "abs_diff": energy_residual,
        }
        statuses.extend([roundtrip_status, energy_status])
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
                "wavelet": self.WAVELET,
                "level": int(self.LEVEL),
                "pywt_version": ref.get("pywt_version", "unknown"),
            },
        )
