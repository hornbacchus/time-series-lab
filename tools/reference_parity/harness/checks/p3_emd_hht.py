"""Phase 3 Batch 7 — EMD/HHT parity check.

Compares TSL ``engine/techniques/emd_hht.py`` (uses ``emd``
package if available, else custom numpy fallback) against
``PyEMD.EMD`` on a synthetic multi-component signal.

**Pattern J classic:** TSL's ``emd`` (AOE Quinn) and reference
``PyEMD.EMD`` (Laszuk) are independent implementations of the
Huang 1998 sifting algorithm. They use different envelope-
extension heuristics, different convergence criteria, and may
extract different numbers of IMFs on the same signal. Per-IMF
bitwise parity is NOT achievable; comparison via structural
properties:

- Reconstruction identity: sum(IMFs) + residual ≈ original
  signal (both implementations should reach machine
  precision on this).
- IMF count: typically agrees within ±1 on smooth signals;
  reported as diagnostic.
- Energy concentration: cumulative IMF energy curve shape
  (Pearson correlation between TSL and reference cumulative
  energy curves; > 0.85 PASS).

This is a **NO-REFERENCE Tier C** wrapper per master plan
§5; correlation-based parity per the Tier C convention from
``p3_nar_narx``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_emd_dgp(
    *, seed: int, n: int = 512,
) -> np.ndarray:
    """Multi-component non-stationary signal: chirp + low-freq
    sinusoid + linear trend + noise. Standard EMD test fixture.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64) / n
    chirp = np.sin(2 * np.pi * (5 + 20 * t) * t)
    slow = 0.5 * np.sin(2 * np.pi * 1.5 * t)
    trend = 0.3 * t
    noise = 0.1 * rng.standard_normal(n)
    return chirp + slow + trend + noise


def _numpy_emd_minimal(signal: np.ndarray, max_imfs: int = 8,
                       max_iter: int = 200) -> np.ndarray:
    """Minimal EMD sifter mirroring TSL's ``_numpy_emd``."""
    def _find_extrema(x):
        maxima, minima = [], []
        for i in range(1, len(x) - 1):
            if x[i] > x[i - 1] and x[i] >= x[i + 1]:
                maxima.append(i)
            elif x[i] < x[i - 1] and x[i] <= x[i + 1]:
                minima.append(i)
        return np.array(maxima, dtype=int), np.array(minima, dtype=int)

    def _envelope_mean(x, maxima, minima):
        t = np.arange(len(x))
        if len(maxima) < 2 or len(minima) < 2:
            return np.zeros_like(x), False
        max_idx = np.concatenate([[0], maxima, [len(x) - 1]])
        max_val = np.concatenate([[x[0]], x[maxima], [x[-1]]])
        min_idx = np.concatenate([[0], minima, [len(x) - 1]])
        min_val = np.concatenate([[x[0]], x[minima], [x[-1]]])
        upper = np.interp(t, max_idx, max_val)
        lower = np.interp(t, min_idx, min_val)
        return (upper + lower) / 2.0, True

    def _sift(s):
        h = s.copy()
        for _ in range(max_iter):
            maxima, minima = _find_extrema(h)
            if len(maxima) < 2 or len(minima) < 2:
                break
            mean_env, ok = _envelope_mean(h, maxima, minima)
            if not ok:
                break
            h_new = h - mean_env
            sd = np.sum((h - h_new) ** 2) / (np.sum(h ** 2) + 1e-15)
            h = h_new
            if sd < 0.001:
                break
        return h

    imfs = []
    residual = signal.copy()
    for _ in range(max_imfs):
        maxima, minima = _find_extrema(residual)
        if len(maxima) < 2 or len(minima) < 2:
            break
        imf = _sift(residual)
        imfs.append(imf)
        residual = residual - imf
        maxr, minr = _find_extrema(residual)
        if len(maxr) + len(minr) < 2:
            break
    return np.array(imfs) if imfs else np.empty((0, len(signal)))


class EmdHhtParity(P3ParityCheck):
    """EMD/HHT parity vs PyEMD (different sifting libraries)."""

    technique_id = "p3_emd_hht"
    tier = "fast"
    fixture_id = ""

    verdict_class = "em_stochastic"
    verdict_class_rationale = (
        "EMD's sifting is iterative with stopping criteria "
        "that differ between implementations (TSL numpy "
        "fallback vs PyEMD). Per-IMF bitwise parity not "
        "achievable. Comparison via reconstruction identity "
        "(machine precision) + IMF count agreement + "
        "energy-curve correlation. Tier C / Pattern K-style "
        "correlation-based check."
    )

    DGP_N = 512

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_emd_dgp(
            seed=seed, n=self.DGP_N,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # Phase 4a-harden #1: invoke the ENGINE (was a _numpy_emd MIRROR that never
        # ran engine code -- the engine-never-invoked hollow class). Extract the
        # IMF component series from the engine's published "IMF Components" table
        # (Index | IMF 1..n | Residual); at n=512 Balanced the table is full
        # resolution (step 1). Values are 6dp-rounded (the wrapper floor) so the
        # engine-side reconstruction holds to ~1e-4, not 1e-10 (PyEMD, unrounded,
        # still hits 1e-10). The real engine-vs-PyEMD comparison is n_imfs + the
        # energy-curve correlation, both robust to 6dp.
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.emd_hht as emd_mod  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_emd_hht", "technique_id": "emd_hht",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"max_imfs": 8},
        })
        resp = emd_mod.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine emd_hht failed: {resp.get('error_message')}")
        tbl = next(t for t in resp.get("tables", []) if t.get("name") == "IMF Components")
        cols, rows = tbl["columns"], tbl["rows"]
        n_imfs = len(cols) - 2  # minus Index + Residual
        idxs = [int(r[0]) - 1 for r in rows]
        imfs = np.array([[float(r[j]) for r in rows] for j in range(1, 1 + n_imfs)]) \
            if n_imfs > 0 else np.empty((0, len(rows)))
        residual = np.array([float(r[-1]) for r in rows])
        y_aligned = y[idxs]
        recon = (imfs.sum(axis=0) + residual) if n_imfs > 0 else residual
        recon_max_abs = float(np.max(np.abs(recon - y_aligned)))
        imf_energies = np.array([float(np.sum(imf ** 2)) for imf in imfs])
        cum_energy = (
            np.cumsum(imf_energies) / imf_energies.sum()
            if imf_energies.sum() > 0
            else np.zeros_like(imf_energies)
        )
        return {
            "n_imfs": n_imfs,
            "reconstruction_max_abs": recon_max_abs,
            "imf_energies": imf_energies,
            "cum_energy_curve": cum_energy,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        from PyEMD import EMD  # type: ignore
        import PyEMD  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        emd = EMD(MAX_ITERATION=200)
        imfs = emd(y, max_imf=8)
        # PyEMD returns IMFs as 2-D array; last row may be the
        # residual depending on version.
        imfs_arr = np.asarray(imfs, dtype=np.float64)
        n_imfs = int(imfs_arr.shape[0])
        residual = y - imfs_arr.sum(axis=0)
        recon_max_abs = float(np.max(np.abs(
            imfs_arr.sum(axis=0) + residual - y,
        )))
        imf_energies = np.array([
            float(np.sum(imf ** 2)) for imf in imfs_arr
        ])
        cum_energy = (
            np.cumsum(imf_energies) / imf_energies.sum()
            if imf_energies.sum() > 0
            else np.zeros_like(imf_energies)
        )
        return {
            "n_imfs": n_imfs,
            "reconstruction_max_abs": recon_max_abs,
            "imf_energies": imf_energies,
            "cum_energy_curve": cum_energy,
            "PyEMD_version": getattr(PyEMD, "__version__", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        # Reconstruction identity. The engine arm is extracted from the published
        # 6dp-rounded "IMF Components" table, so its floor is ~1e-4 (not 1e-10);
        # the PyEMD arm is unrounded -> 1e-10. The threshold difference reflects
        # the wrapper rounding, NOT a divergence.
        primary["reconstruction_identity_tsl"] = {
            "status": ("PASS"
                       if tsl.get("reconstruction_max_abs", 1.0) < 1e-3
                       else "BLOCK"),
            "max_abs_residual": tsl.get("reconstruction_max_abs"),
        }
        primary["reconstruction_identity_ref"] = {
            "status": ("PASS"
                       if ref.get("reconstruction_max_abs", 1.0) < 1e-10
                       else "BLOCK"),
            "max_abs_residual": ref.get("reconstruction_max_abs"),
        }
        # IMF count agreement (within ±1 acceptable; ±2+ CAVEAT)
        n_diff = abs(int(tsl["n_imfs"]) - int(ref["n_imfs"]))
        primary["n_imfs_match"] = {
            "status": "PASS" if n_diff <= 1 else
                     ("CAVEAT" if n_diff <= 2 else "BLOCK"),
            "tsl_n_imfs": int(tsl["n_imfs"]),
            "ref_n_imfs": int(ref["n_imfs"]),
            "abs_diff": n_diff,
        }
        # Energy-curve correlation (Tier C convention)
        if (
            len(tsl["cum_energy_curve"]) >= 3
            and len(ref["cum_energy_curve"]) >= 3
        ):
            n_common = min(
                len(tsl["cum_energy_curve"]),
                len(ref["cum_energy_curve"]),
            )
            tsl_curve = np.asarray(
                tsl["cum_energy_curve"], dtype=np.float64,
            )[:n_common]
            ref_curve = np.asarray(
                ref["cum_energy_curve"], dtype=np.float64,
            )[:n_common]
            if np.std(tsl_curve) > 0 and np.std(ref_curve) > 0:
                corr = float(np.corrcoef(tsl_curve, ref_curve)[0, 1])
            else:
                corr = float("nan")
            corr_thresh_pass = float(
                ladder["primary"].get("corr_pass", 0.85)
            )
            corr_thresh_caveat = float(
                ladder["primary"].get("corr_caveat", 0.6)
            )
            corr_status = (
                "PASS" if corr >= corr_thresh_pass else
                ("CAVEAT" if corr >= corr_thresh_caveat else "BLOCK")
            )
        else:
            corr = float("nan")
            corr_status = "CAVEAT"
        primary["cum_energy_curve_correlation"] = {
            "status": corr_status,
            "pearson_corr": corr,
            "n_compared": n_common
            if "n_common" in dir() else 0,
        }
        statuses = [v["status"] for v in primary.values()]
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
                "tsl_n_imfs": int(tsl["n_imfs"]),
                "ref_n_imfs": int(ref["n_imfs"]),
                "PyEMD_version": ref.get("PyEMD_version", "unknown"),
            },
        )
