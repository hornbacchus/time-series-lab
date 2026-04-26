"""Calibration Audit Phase 2 Session 13 — Frequency Domain batch.

Largest CAI batch yet: 7 wrappers in one session.
  - fft_spectrum (engine/techniques/fft_spectrum.py)
  - periodogram_spectral_density (engine/techniques/...)
  - lomb_scargle (engine/techniques/lomb_scargle.py)
  - wavelet_transform (engine/techniques/wavelet_transform.py)
  - wavelet_coherence (engine/techniques/wavelet_coherence.py;
    also handles wavelet_coherence_phase_lag)
  - emd_hht (engine/techniques/emd_hht.py)
  - ssa_model (engine/techniques/ssa_model.py)

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation
    matrix per wrapper. Highest-yield section per the
    validation-presence pattern.
  Technique 1 — compressed parameter sweeps (2-3 cells per
    wrapper to manage 7-wrapper batch runtime)
  Technique 2 — real-data stress (subsampled appropriately)
  Technique 3 — adversarial canonicals (mirrored in 7 NEW
    canonical scripts; 6 each per Session 12 compressed
    protocol)

CAL-R6 budget tracking: aggressive STOP rules per session
plan if cumulative engine-fix LOC approaches 100.

Run:
    python tools/calibration_audit/audit_frequency_domain_batch.py
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import fft_spectrum as fft_mod
from techniques import periodogram_spectral_density as pgm_mod
from techniques import lomb_scargle as ls_mod
from techniques import wavelet_transform as wt_mod
from techniques import wavelet_coherence as wc_mod
from techniques import emd_hht as emd_mod
from techniques import ssa_model as ssa_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_fd",
                frequency="daily", series_extra=None,
                time_values=None):
    user_params = dict(params or {})
    series = [{"name": "y", "values": list(values)}]
    if series_extra:
        for name, vals in series_extra:
            series.append({"name": name, "values": list(vals)})
    if time_values is None:
        time_values = list(range(len(values)))
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(time_values),
        "series": series,
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_sinusoid(*, T=500, freq=0.1, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return np.sin(2 * np.pi * freq * t) + 0.2 * rng.standard_normal(T)


def _simulate_multicomponent(*, T=500, seed=42):
    """Sum of 2 sinusoids + noise; used for wavelet/EMD/SSA tests."""
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (np.sin(2 * np.pi * 0.05 * t)
            + 0.5 * np.sin(2 * np.pi * 0.20 * t)
            + 0.3 * rng.standard_normal(T))


def _simulate_uneven_time(*, T=300, seed=42):
    """Synthetic uneven-time series for lomb_scargle."""
    rng = np.random.default_rng(seed)
    t_full = np.linspace(0, 100, T * 2)
    keep = rng.random(len(t_full)) < 0.5
    t = t_full[keep]
    y = np.sin(2 * np.pi * 0.1 * t) + 0.2 * rng.standard_normal(len(t))
    return t.tolist(), y.tolist()


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


def _yield_diffs(yields):
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


# =====================================================
# Sweep 0 — Per-wrapper dispatch + input-validation
# =====================================================


def sweep_0_dispatch_validation():
    print("\n" + "=" * 60)
    print("SWEEP 0: DISPATCH + INPUT-VALIDATION (7 wrappers)")
    print("=" * 60)

    findings = []
    y = _simulate_sinusoid(T=500, seed=42)
    y_multi = _simulate_multicomponent(T=500, seed=42)

    # ---- fft_spectrum ----
    print("\n--- fft_spectrum baseline ---")
    ctx = _build_ctx(y, technique_id="fft_spectrum", params={})
    res, elapsed, err = _safe_run(fft_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-FFT-BASELINE", "severity": "severe",
                          "title": "fft_spectrum baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- fft_spectrum invalid window='zzz' ---")
    ctx = _build_ctx(y, technique_id="fft_spectrum",
                     params={"window": "zzz"})
    res, elapsed, err = _safe_run(fft_mod, ctx)
    fft_inv_window = "unknown"
    if err:
        fft_inv_window = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        fft_inv_window = (
            f"status={res.get('status')}, "
            f"audit_window={a.get('window')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {fft_inv_window}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("window") == "zzz"):
        findings.append({
            "id": "F-FD-FFT-WINDOW",
            "severity": "severe",
            "title": "fft_spectrum accepted invalid window='zzz' silently",
            "details": {"audit_window": "zzz"},
        })

    print("\n--- fft_spectrum invalid detrend='zzz' ---")
    ctx = _build_ctx(y, technique_id="fft_spectrum",
                     params={"detrend": "zzz"})
    res, elapsed, err = _safe_run(fft_mod, ctx)
    fft_inv_detrend = "unknown"
    if err:
        fft_inv_detrend = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        fft_inv_detrend = (
            f"status={res.get('status')}, "
            f"audit_detrend={a.get('detrend')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {fft_inv_detrend}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("detrend") == "zzz"):
        findings.append({
            "id": "F-FD-FFT-DETREND",
            "severity": "severe",
            "title": "fft_spectrum accepted invalid detrend='zzz' silently",
            "details": {"audit_detrend": "zzz"},
        })

    # ---- periodogram_spectral_density ----
    print("\n--- periodogram baseline ---")
    ctx = _build_ctx(y, technique_id="periodogram_spectral_density",
                     params={})
    res, elapsed, err = _safe_run(pgm_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-PGM-BASELINE", "severity": "severe",
                          "title": "periodogram baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- periodogram invalid window='zzz' ---")
    ctx = _build_ctx(y, technique_id="periodogram_spectral_density",
                     params={"window": "zzz"})
    res, elapsed, err = _safe_run(pgm_mod, ctx)
    pgm_inv_window = "unknown"
    if err:
        pgm_inv_window = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        pgm_inv_window = (
            f"status={res.get('status')}, audit_window={a.get('window')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {pgm_inv_window}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("window") == "zzz"):
        findings.append({
            "id": "F-FD-PGM-WINDOW",
            "severity": "severe",
            "title": "periodogram accepted invalid window='zzz' silently",
            "details": {"audit_window": "zzz"},
        })

    # ---- lomb_scargle ----
    print("\n--- lomb_scargle baseline (uneven time) ---")
    t_uneven, y_uneven = _simulate_uneven_time(T=300, seed=42)
    ctx = _build_ctx(y_uneven, technique_id="lomb_scargle",
                     params={}, time_values=t_uneven)
    res, elapsed, err = _safe_run(ls_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-LS-BASELINE", "severity": "severe",
                          "title": "lomb_scargle baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    # ---- wavelet_transform ----
    print("\n--- wavelet_transform baseline (db4) ---")
    ctx = _build_ctx(y_multi, technique_id="wavelet_transform",
                     params={"wavelet": "db4"})
    res, elapsed, err = _safe_run(wt_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-WT-BASELINE", "severity": "severe",
                          "title": "wavelet_transform baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- wavelet_transform invalid wavelet='zzz' ---")
    ctx = _build_ctx(y_multi, technique_id="wavelet_transform",
                     params={"wavelet": "zzz"})
    res, elapsed, err = _safe_run(wt_mod, ctx)
    wt_inv_wave = "unknown"
    if err:
        wt_inv_wave = f"raised: {err[:80]}"
    elif res:
        wt_inv_wave = (
            f"status={res.get('status')}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {wt_inv_wave}")
    # wavelet_transform has explicit validation at line 81-89 (verified
    # in M1); should reject

    print("\n--- wavelet_transform invalid mode='zzz' ---")
    ctx = _build_ctx(y_multi, technique_id="wavelet_transform",
                     params={"wavelet": "db4", "mode": "zzz"})
    res, elapsed, err = _safe_run(wt_mod, ctx)
    wt_inv_mode = "unknown"
    if err:
        wt_inv_mode = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        wt_inv_mode = (
            f"status={res.get('status')}, "
            f"audit_mode={a.get('mode')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {wt_inv_mode}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("mode") == "zzz"):
        findings.append({
            "id": "F-FD-WT-MODE",
            "severity": "severe",
            "title": "wavelet_transform accepted invalid mode='zzz' silently",
            "details": {"audit_mode": "zzz"},
        })

    # ---- wavelet_coherence ----
    print("\n--- wavelet_coherence baseline (2-series) ---")
    rng = np.random.default_rng(43)
    y2 = y_multi + 0.3 * rng.standard_normal(500)
    ctx = _build_ctx(y_multi, technique_id="wavelet_coherence",
                     params={}, series_extra=[("y2", y2)])
    res, elapsed, err = _safe_run(wc_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-WC-BASELINE", "severity": "severe",
                          "title": "wavelet_coherence baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- wavelet_coherence invalid wavelet='zzz' ---")
    ctx = _build_ctx(y_multi, technique_id="wavelet_coherence",
                     params={"wavelet": "zzz"},
                     series_extra=[("y2", y2)])
    res, elapsed, err = _safe_run(wc_mod, ctx)
    wc_inv_wave = "unknown"
    if err:
        wc_inv_wave = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        wc_inv_wave = (
            f"status={res.get('status')}, "
            f"audit_wavelet={a.get('wavelet')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {wc_inv_wave}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("wavelet") == "zzz"):
        findings.append({
            "id": "F-FD-WC-WAVELET",
            "severity": "severe",
            "title": "wavelet_coherence accepted invalid wavelet='zzz' silently",
            "details": {"audit_wavelet": "zzz"},
        })

    # ---- emd_hht ----
    print("\n--- emd_hht baseline ---")
    ctx = _build_ctx(y_multi, technique_id="emd_hht", params={})
    res, elapsed, err = _safe_run(emd_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-EMD-BASELINE", "severity": "severe",
                          "title": "emd_hht baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- emd_hht invalid method='zzz' ---")
    ctx = _build_ctx(y_multi, technique_id="emd_hht",
                     params={"method": "zzz"})
    res, elapsed, err = _safe_run(emd_mod, ctx)
    emd_inv_method = "unknown"
    if err:
        emd_inv_method = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        emd_inv_method = (
            f"status={res.get('status')}, "
            f"audit_method={a.get('method')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {emd_inv_method}")
    if (res and res.get("status") == "success"
            and str((res.get("audit_fields") or {}).get("method", ""))
                .lower() == "zzz"):
        findings.append({
            "id": "F-FD-EMD-METHOD",
            "severity": "severe",
            "title": "emd_hht accepted invalid method='zzz' silently",
            "details": {"audit_method": "zzz"},
        })

    # ---- ssa_model ----
    print("\n--- ssa_model baseline ---")
    ctx = _build_ctx(y_multi, technique_id="ssa", params={})
    res, elapsed, err = _safe_run(ssa_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-FD-SSA-BASELINE", "severity": "severe",
                          "title": "ssa_model baseline failed",
                          "details": err or res.get("error_message")})
    else:
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- ssa_model invalid window_length=-1 ---")
    ctx = _build_ctx(y_multi, technique_id="ssa",
                     params={"window_length": -1})
    res, elapsed, err = _safe_run(ssa_mod, ctx)
    ssa_inv_wl = "unknown"
    if err:
        ssa_inv_wl = f"raised: {err[:80]}"
    elif res:
        ssa_inv_wl = (
            f"status={res.get('status')}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {ssa_inv_wl}")

    return {
        "fft_inv_window": fft_inv_window,
        "fft_inv_detrend": fft_inv_detrend,
        "pgm_inv_window": pgm_inv_window,
        "wt_inv_wave": wt_inv_wave,
        "wt_inv_mode": wt_inv_mode,
        "wc_inv_wave": wc_inv_wave,
        "emd_inv_method": emd_inv_method,
        "ssa_inv_wl": ssa_inv_wl,
        "findings": findings,
    }


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: COMPRESSED PARAMETER SWEEPS")
    print("=" * 60)

    findings = []
    y = _simulate_sinusoid(T=500, seed=42)
    y_multi = _simulate_multicomponent(T=500, seed=42)

    # FFT detrend
    print("\n--- FFT detrend sweep ---")
    fft_sweep = []
    for d in ["mean", "linear", "none"]:
        ctx = _build_ctx(y, technique_id="fft_spectrum",
                          params={"detrend": d})
        res, elapsed, err = _safe_run(fft_mod, ctx)
        fft_sweep.append({"detrend": d,
                          "status": res.get("status") if res else "ERROR",
                          "elapsed_s": round(elapsed, 2)})
        print(f"  detrend={d}: status={res.get('status') if res else 'ERROR'}")

    # Wavelet family
    print("\n--- Wavelet family sweep ---")
    wt_sweep = []
    for w in ["db4", "sym4", "coif1"]:
        ctx = _build_ctx(y_multi, technique_id="wavelet_transform",
                          params={"wavelet": w})
        res, elapsed, err = _safe_run(wt_mod, ctx)
        wt_sweep.append({"wavelet": w,
                          "status": res.get("status") if res else "ERROR",
                          "elapsed_s": round(elapsed, 2)})
        print(f"  wavelet={w}: status={res.get('status') if res else 'ERROR'}, "
              f"t={elapsed:.2f}s")

    # SSA window length
    print("\n--- SSA window_length sweep ---")
    ssa_sweep = []
    for wl in [50, 100, 200]:
        ctx = _build_ctx(y_multi, technique_id="ssa",
                          params={"window_length": wl})
        res, elapsed, err = _safe_run(ssa_mod, ctx)
        ssa_sweep.append({"wl": wl,
                          "status": res.get("status") if res else "ERROR",
                          "elapsed_s": round(elapsed, 2)})
        print(f"  wl={wl}: status={res.get('status') if res else 'ERROR'}, "
              f"t={elapsed:.2f}s")

    return {
        "fft_detrend": fft_sweep,
        "wavelet_family": wt_sweep,
        "ssa_window_length": ssa_sweep,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress (subsampled)
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (subsampled to T=500)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({"id": "F-FD-T2-MISSING", "severity": "severe",
                          "title": "Real-data fixture missing"})
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    gspc_returns = _log_returns(data["GSPC"])[-500:]
    dgs10_diffs = _yield_diffs(data["DGS10"])[-500:]

    cells = []
    for sid, prep_data in [("GSPC", gspc_returns),
                             ("DGS10", dgs10_diffs)]:
        T = len(prep_data)
        print(f"\n--- {sid} (T={T}) ---")
        for tid, mod, params in [
            ("fft_spectrum", fft_mod, {}),
            ("periodogram", pgm_mod, {}),
            ("wavelet_transform", wt_mod, {"wavelet": "db4"}),
            ("emd_hht", emd_mod, {}),
            ("ssa", ssa_mod, {"window_length": 100}),
        ]:
            ctx = _build_ctx(prep_data, technique_id=tid, params=params,
                              preset="Balanced")
            res, elapsed, err = _safe_run(mod, ctx)
            if err:
                cells.append({"series": sid, "wrapper": tid,
                              "status": "ERROR", "error": err[:80]})
                findings.append({
                    "id": f"F-FD-T2-{sid}-{tid.upper()}-ERROR",
                    "severity": "severe",
                    "title": f"{tid} crashed on {sid}",
                    "details": err[:200],
                })
                print(f"  {tid:18s}: ERROR — {err[:60]}")
                continue
            a = res.get("audit_fields", {}) or {}
            cells.append({
                "series": sid, "wrapper": tid, "T": T,
                "wrapper_status": res.get("status"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:18s}: status={res.get('status')}, "
                  f"t={elapsed:.1f}s")
            if elapsed > 30.0:
                findings.append({
                    "id": f"F-FD-T2-{sid}-{tid.upper()}-SLOW",
                    "severity": "operational",
                    "title": f"{tid} runtime {elapsed:.1f}s on {sid}",
                    "details": {"elapsed_s": elapsed},
                })

    # wavelet_coherence: 2-series cross-coherence
    print("\n--- wavelet_coherence on (GSPC, DGS10) ---")
    n_min = min(len(gspc_returns), len(dgs10_diffs))
    ctx = _build_ctx(gspc_returns[-n_min:],
                      technique_id="wavelet_coherence",
                      params={},
                      series_extra=[("DGS10",
                                       dgs10_diffs[-n_min:].tolist())])
    res, elapsed, err = _safe_run(wc_mod, ctx)
    if err:
        cells.append({"series": "pair", "wrapper": "wavelet_coherence",
                      "status": "ERROR", "error": err[:80]})
        print(f"  ERROR — {err[:80]}")
    else:
        cells.append({"series": "pair", "wrapper": "wavelet_coherence",
                      "wrapper_status": res.get("status"),
                      "elapsed_s": round(elapsed, 2)})
        print(f"  status={res.get('status')}, t={elapsed:.1f}s")

    return {"baselines": cells, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonicals
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Constant series for spectral wrappers ----
    print("\n--- C-CAL-1: Constant series y=5.0 T=200 ---")
    y_const = np.full(200, 5.0)
    for tid, mod, params in [
        ("fft_spectrum", fft_mod, {}),
        ("periodogram", pgm_mod, {}),
        ("wavelet_transform", wt_mod, {"wavelet": "db4"}),
        ("ssa", ssa_mod, {"window_length": 50}),
    ]:
        ctx = _build_ctx(y_const, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-1", "wrapper": tid,
            "case": "constant series",
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:18s}: status={s}")

    # ---- C-CAL-2: Pure sinusoid (single dominant frequency) ----
    print("\n--- C-CAL-2: Pure sinusoid (freq=0.1) T=500 ---")
    y_sine = _simulate_sinusoid(T=500, freq=0.1, seed=42)
    for tid, mod, params in [
        ("fft_spectrum", fft_mod, {}),
        ("periodogram", pgm_mod, {}),
    ]:
        ctx = _build_ctx(y_sine, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-2", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })

    # ---- C-CAL-3: Short series ----
    print("\n--- C-CAL-3: Short series T=30 ---")
    rng = np.random.default_rng(42)
    y_short = rng.standard_normal(30)
    for tid, mod, params in [
        ("fft_spectrum", fft_mod, {}),
        ("wavelet_transform", wt_mod, {"wavelet": "db4"}),
    ]:
        ctx = _build_ctx(y_short, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-3", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
            "error_message": res.get("error_message") if res else err,
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:18s}: status={s}")

    # ---- C-CAL-4: Multi-component for EMD/SSA ----
    print("\n--- C-CAL-4: Multi-component T=500 ---")
    y_mc = _simulate_multicomponent(T=500, seed=44)
    for tid, mod, params in [
        ("emd_hht", emd_mod, {}),
        ("ssa", ssa_mod, {"window_length": 100}),
    ]:
        ctx = _build_ctx(y_mc, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-4", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:8s}: status={s}, t={elapsed:.1f}s")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — Frequency Domain batch (CAI Session 13)")
    print("Date: 2026-04-26")
    print()

    s0 = sweep_0_dispatch_validation()
    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (s0.get("findings", []) + t1.get("findings", [])
                    + t2.get("findings", []) + t3.get("findings", [])
                    + list(_EXTRA_FINDINGS))
    by_sev = {"severe": 0, "operational": 0, "cosmetic": 0}
    for f in all_findings:
        by_sev[f.get("severity", "cosmetic")] = (
            by_sev.get(f.get("severity", "cosmetic"), 0) + 1
        )

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Severe:      {by_sev['severe']}")
    print(f"Operational: {by_sev['operational']}")
    print(f"Cosmetic:    {by_sev['cosmetic']}")
    print(f"Total:       {sum(by_sev.values())}")
    if all_findings:
        print("\nFindings:")
        for f in all_findings:
            print(f"  [{f['severity'].upper()}] {f['id']}: {f['title']}")

    results = {
        "date": "2026-04-26",
        "wrappers": ["fft_spectrum", "periodogram_spectral_density",
                      "lomb_scargle", "wavelet_transform",
                      "wavelet_coherence", "emd_hht", "ssa_model"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (_ROOT / "tools" / "calibration_audit"
                / "frequency_domain_batch_audit_results.json")

    def _coerce(o):
        if isinstance(o, (np.floating, np.integer)): return o.item()
        if isinstance(o, np.ndarray): return o.tolist()
        if isinstance(o, dict): return {k: _coerce(v) for k, v in o.items()}
        if isinstance(o, list): return [_coerce(v) for v in o]
        if isinstance(o, (bool, int, float, str, type(None))): return o
        return str(o)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_coerce(results), f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    return 1 if by_sev["severe"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
