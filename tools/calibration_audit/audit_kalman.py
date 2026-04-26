"""Calibration Audit Phase 2 Session 1 — Kalman filter / smoother.

Three audit techniques per CAI Phase 1 §3.1:

  Technique 1 — Parameter sweep:
    Sweep operationally-relevant parameter ranges and tabulate
    output behavior. Flag non-monotonic, discontinuous,
    NaN/Inf, or no-effect cases.

  Technique 2 — Real-data stress test:
    Run wrapper at default Balanced preset on 5 macro series
    (DGS10, DGS2, DEXUSEU, GSPC, GOLD). Inspect filtered/
    smoothed states, log-likelihood finiteness, runtime.
    Establish baseline summary stats for future sessions.

  Technique 3 — Adversarial canonical extension:
    Build C-CAL-1 through C-CAL-4 covering minimum-viable T,
    NaN gaps, single outlier, near-unit-root.

Run:
    python tools/calibration_audit/audit_kalman.py

CAL-R2 (parameter API): Kalman wrapper uses template-based
parametrization. The handoff §3.1 sketch listed
``process_noise_var`` / ``observation_noise_var`` etc.; actual
schema is:
  - ``state_space_model`` template: "local_level" (default),
    "local_linear_trend", "seasonal", "ar1", "custom"
  - ``initialization``: "diffuse" (default), "known",
    "approximate_diffuse"
  - ``seasonal_period`` (int, default 12)
  - ``ar_order`` (int, default 1)
  - ``maxiter`` (int, preset-driven)
  - ``initial_state``, ``initial_covariance`` (optional override)
  - For custom path: ``Z``, ``T``, ``R``, ``H``, ``Q`` matrices

The sweep maps the handoff's process/observation noise to the
custom path's ``Q`` / ``H`` matrices (1x1 for univariate). All
other parameters swept directly from the actual schema.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from typing import Any

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import kalman_filter as kf_mod
from techniques import kalman_smoother as ks_mod


_FIXTURE = _ROOT / "tools" / "calibration_audit" / "fixtures" / "macro_canonical_series.npz"
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helper construction
# =====================================================


def _build_ctx(
    y, params=None, preset="Balanced",
    technique_id="kalman_filter", run_id="audit_kalman",
):
    """Build RunContext for Kalman wrapper."""
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": params or {},
    })


def _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    eps = rng.standard_normal(T) * sigma
    for t in range(1, T):
        y[t] = phi * y[t - 1] + eps[t]
    return y


def _safe_run(ctx, technique="filter"):
    """Wrap run in try/except so the sweep doesn't abort on
    individual failures; capture the error for the findings table."""
    try:
        t0 = time.time()
        if technique == "filter":
            res = kf_mod.run(ctx, _NULL_PROGRESS)
        else:
            res = ks_mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    """Sweep operationally-relevant Kalman parameters; tabulate
    output behavior."""
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    y_base = _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=42)

    # ---- Sweep 1: state_space_model template ----
    print("\n--- Sweep 1: state_space_model template ---")
    sweep1 = []
    for tmpl in ["local_level", "local_linear_trend", "ar1", "seasonal"]:
        params = {"state_space_model": tmpl}
        if tmpl == "seasonal":
            params["seasonal_period"] = 7  # short period for length-200 series
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep1.append({"template": tmpl, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        ll_finite = ll is not None and np.isfinite(ll)
        sweep1.append({
            "template": tmpl,
            "status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
            "log_likelihood": ll,
            "log_likelihood_finite": ll_finite,
        })
    print(f"  {len(sweep1)} templates swept")
    for row in sweep1:
        print(f"    {row}")
    if not all(r.get("log_likelihood_finite", False) or r.get("status") == "ERROR" for r in sweep1):
        findings.append({
            "id": "F-K-T1-1",
            "severity": "operational",
            "title": "Some template log-likelihoods non-finite on synthetic AR(1)",
            "details": sweep1,
        })

    # ---- Sweep 2: initialization ----
    print("\n--- Sweep 2: initialization ---")
    sweep2 = []
    for init in ["diffuse", "known", "approximate_diffuse"]:
        params = {"state_space_model": "local_level", "initialization": init}
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep2.append({"init": init, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep2.append({
            "init": init,
            "status": res.get("status"),
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep2)} initializations swept")
    for row in sweep2:
        print(f"    {row}")

    # ---- Sweep 3: maxiter (template path; effective on ML estimation) ----
    print("\n--- Sweep 3: maxiter ---")
    sweep3 = []
    for mx in [10, 50, 100, 250, 1000]:
        params = {"state_space_model": "local_level", "maxiter": mx}
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep3.append({"maxiter": mx, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep3.append({
            "maxiter": mx,
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep3)} maxiter values swept")
    for row in sweep3:
        print(f"    {row}")
    # Check: log-likelihood should be approximately monotone non-decreasing
    # in maxiter (more iterations = better optimum, modulo convergence).
    lls = [r.get("log_likelihood") for r in sweep3 if r.get("log_likelihood") is not None]
    if len(lls) >= 2:
        ll_range = max(lls) - min(lls)
        if ll_range > 1e-3:
            findings.append({
                "id": "F-K-T1-2",
                "severity": "cosmetic",
                "title": "log-likelihood varies across maxiter (range > 1e-3)",
                "details": {"maxiter_lls": lls, "range": ll_range,
                            "note": "Expected — different maxiter caps mean different MLE convergence; informational only."},
            })

    # ---- Sweep 4: custom path Q (process noise variance) ----
    print("\n--- Sweep 4: custom path Q (process noise) ---")
    sweep4 = []
    for q in [0.01, 0.1, 1.0, 10.0]:
        params = {
            "state_space_model": "custom",
            "observation_matrix_Z": [[1.0]],
            "transition_matrix_T": [[1.0]],
            "state_intercept_R": [[1.0]],
            "observation_noise_H": [[1.0]],
            "process_noise_Q": [[q]],
            "initial_state": [0.0],
            "initial_covariance": [[1.0]],
        }
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep4.append({"Q": q, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep4.append({
            "Q": q,
            "wrapper_status": res.get("status"),
            "wrapper_error_message": res.get("error_message"),
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep4)} Q values swept")
    for row in sweep4:
        print(f"    {row}")
    # Check: NO sweep4 row should be a failure (custom path with valid 1x1 matrices)
    custom_failures = [r for r in sweep4 if r.get("wrapper_status") not in (None, "success")]
    if custom_failures:
        findings.append({
            "id": "F-K-T1-3",
            "severity": "operational",
            "title": "Custom path returns non-success status on valid 1x1 matrices for some Q values",
            "details": custom_failures,
        })

    # ---- Sweep 5: custom path H (observation noise variance) ----
    print("\n--- Sweep 5: custom path H (observation noise) ---")
    sweep5 = []
    for h in [0.01, 0.1, 1.0, 10.0]:
        params = {
            "state_space_model": "custom",
            "observation_matrix_Z": [[1.0]],
            "transition_matrix_T": [[1.0]],
            "state_intercept_R": [[1.0]],
            "observation_noise_H": [[h]],
            "process_noise_Q": [[1.0]],
            "initial_state": [0.0],
            "initial_covariance": [[1.0]],
        }
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep5.append({"H": h, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep5.append({
            "H": h,
            "wrapper_status": res.get("status"),
            "wrapper_error_message": res.get("error_message"),
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep5)} H values swept")
    for row in sweep5:
        print(f"    {row}")

    # ---- Sweep 6: initial_state effect (custom path) ----
    print("\n--- Sweep 6: initial_state values (custom path) ---")
    sweep6 = []
    y_mean = float(np.mean(y_base))
    y_median = float(np.median(y_base))
    for label, x0 in [("zero", 0.0), ("mean", y_mean), ("median", y_median),
                       ("far_off", 1e6)]:
        params = {
            "state_space_model": "custom",
            "observation_matrix_Z": [[1.0]],
            "transition_matrix_T": [[1.0]],
            "state_intercept_R": [[1.0]],
            "observation_noise_H": [[1.0]],
            "process_noise_Q": [[1.0]],
            "initial_state": [x0],
            "initial_covariance": [[1.0]],
        }
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep6.append({"label": label, "x0": x0, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep6.append({
            "label": label, "x0": x0,
            "wrapper_status": res.get("status"),
            "wrapper_error_message": res.get("error_message"),
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
        })
    print(f"  {len(sweep6)} initial-state values swept")
    for row in sweep6:
        print(f"    {row}")
    # The far_off=1e6 case should still produce a finite log-likelihood
    # (Kalman filter is robust to bad initial state given enough data
    # and reasonable initial_covariance). If log-lik is NaN/Inf, that's
    # operational.
    far_off = next((r for r in sweep6 if r.get("label") == "far_off"), None)
    if far_off and far_off.get("log_likelihood") is None:
        findings.append({
            "id": "F-K-T1-4",
            "severity": "operational",
            "title": "Far-off initial state (1e6) produces non-finite log-likelihood",
            "details": far_off,
        })

    # ---- Sweep 7: initial_covariance effect (custom path) ----
    print("\n--- Sweep 7: initial_covariance values (custom path) ---")
    sweep7 = []
    for cov in [0.01, 1.0, 100.0, 1e6]:
        params = {
            "state_space_model": "custom",
            "observation_matrix_Z": [[1.0]],
            "transition_matrix_T": [[1.0]],
            "state_intercept_R": [[1.0]],
            "observation_noise_H": [[1.0]],
            "process_noise_Q": [[1.0]],
            "initial_state": [0.0],
            "initial_covariance": [[cov]],
        }
        ctx = _build_ctx(y_base, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep7.append({"cov": cov, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        sweep7.append({
            "cov": cov,
            "wrapper_status": res.get("status"),
            "wrapper_error_message": res.get("error_message"),
            "log_likelihood": float(ll) if ll is not None and np.isfinite(ll) else None,
        })
    print(f"  {len(sweep7)} initial_covariance values swept")
    for row in sweep7:
        print(f"    {row}")

    return {
        "sweep_1_template": sweep1,
        "sweep_2_initialization": sweep2,
        "sweep_3_maxiter": sweep3,
        "sweep_4_Q_process_noise": sweep4,
        "sweep_5_H_observation_noise": sweep5,
        "sweep_6_initial_state": sweep6,
        "sweep_7_initial_covariance": sweep7,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress test
# =====================================================


def technique_2_real_data_stress():
    """Run wrapper on 5 macro series; establish baseline stats."""
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS TEST")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-K-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baseline_stats": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_ids = ["DGS10", "DGS2", "DEXUSEU", "GSPC", "GOLD"]
    baseline_stats = []
    for sid in series_ids:
        y = np.asarray(data[sid], dtype=np.float64)
        T = len(y)
        print(f"\n--- {sid}: T={T}, range=[{y.min():.4f}, {y.max():.4f}] ---")
        # Run with default Balanced preset, default params
        ctx = _build_ctx(y)
        res, elapsed, err = _safe_run(ctx)
        if err:
            baseline_stats.append({
                "series": sid, "T": T, "status": "ERROR", "error": err,
            })
            print(f"  ERROR: {err}")
            findings.append({
                "id": f"F-K-T2-{sid}-ERROR",
                "severity": "severe",
                "title": f"Wrapper crashed on {sid}",
                "details": err,
            })
            continue
        if res.get("status") != "success":
            findings.append({
                "id": f"F-K-T2-{sid}-NONSUCCESS",
                "severity": "severe",
                "title": f"Wrapper status={res.get('status')} on {sid}",
                "details": res.get("error_message"),
            })
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        ll_finite = ll is not None and np.isfinite(ll)
        # Look for filtered/smoothed state outputs in audit_fields
        # or tables. Don't assert specific keys; just collect what's there.
        present_keys = sorted([k for k in a.keys()
                                if "filter" in k or "smooth" in k or "state" in k or "kalman" in k.lower()
                                or "log_lik" in k.lower()])
        baseline_stats.append({
            "series": sid,
            "T": T,
            "status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
            "log_likelihood": float(ll) if ll_finite else None,
            "log_likelihood_finite": ll_finite,
            "audit_state_keys": present_keys,
            "input_mean": float(y.mean()),
            "input_std": float(y.std()),
        })
        print(f"  status={res.get('status')}, log_lik={ll}, elapsed={elapsed:.2f}s")
        if not ll_finite:
            findings.append({
                "id": f"F-K-T2-{sid}-NANLL",
                "severity": "operational",
                "title": f"log_likelihood non-finite on {sid}",
                "details": {"log_likelihood": ll},
            })
        # Runtime budget per handoff §1.2: ≤30s for fast operations
        if elapsed > 30.0:
            findings.append({
                "id": f"F-K-T2-{sid}-SLOW",
                "severity": "operational",
                "title": f"Runtime {elapsed:.1f}s exceeds 30s budget on {sid}",
                "details": {"series": sid, "T": T, "elapsed_s": elapsed},
            })

    return {"baseline_stats": baseline_stats, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonical extension
# =====================================================


def technique_3_adversarial():
    """Build C-CAL-1..4 adversarial canonicals."""
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXTENSION")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: T=5 minimum-viable ----
    print("\n--- C-CAL-1: T=5 minimum-viable series ---")
    rng = np.random.default_rng(42)
    y = rng.standard_normal(5)
    ctx = _build_ctx(y)
    res, elapsed, err = _safe_run(ctx)
    canonical_results.append({
        "id": "C-CAL-1", "case": "T=5 minimum-viable",
        "status": res.get("status") if res else "ERROR",
        "error": err,
        "elapsed_s": round(elapsed, 2),
    })
    if err:
        print(f"  ERROR: {err}")
        # Crashing on T=5 is operational (probably should produce
        # an error-status result instead of raising).
        findings.append({
            "id": "F-K-T3-1",
            "severity": "operational",
            "title": "Wrapper raises on T=5 instead of returning error status",
            "details": err,
        })
    else:
        print(f"  status={res.get('status')}, elapsed={elapsed:.2f}s")

    # ---- C-CAL-2: T=200 with 5% NaN gaps ----
    print("\n--- C-CAL-2: T=200 with 5% NaN gaps ---")
    rng = np.random.default_rng(43)
    y = _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=43)
    n_gaps = int(0.05 * 200)
    gap_idx = rng.choice(200, size=n_gaps, replace=False)
    y_gaps = y.copy()
    y_gaps[gap_idx] = np.nan
    ctx = _build_ctx(y_gaps)
    res, elapsed, err = _safe_run(ctx)
    canonical_results.append({
        "id": "C-CAL-2", "case": "T=200 with 5% NaN gaps",
        "status": res.get("status") if res else "ERROR",
        "error": err,
        "elapsed_s": round(elapsed, 2),
    })
    if err:
        print(f"  ERROR: {err}")
        findings.append({
            "id": "F-K-T3-2",
            "severity": "operational",
            "title": "Wrapper raises on series with NaN gaps",
            "details": err,
        })
    else:
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        print(f"  status={res.get('status')}, log_lik={ll}, elapsed={elapsed:.2f}s")
        # Kalman filter is one of the canonical methods that handles
        # NaN gaps (treats as missing observations); should NOT crash.

    # ---- C-CAL-3: T=200 with single 10sigma outlier at midpoint ----
    print("\n--- C-CAL-3: T=200 with single 10sigma outlier at midpoint ---")
    y = _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=44)
    y_outlier = y.copy()
    y_outlier[100] = y_outlier[100] + 10.0 * y.std()
    ctx = _build_ctx(y_outlier)
    res, elapsed, err = _safe_run(ctx)
    canonical_results.append({
        "id": "C-CAL-3", "case": "T=200 with 10sigma outlier at t=100",
        "status": res.get("status") if res else "ERROR",
        "error": err,
        "elapsed_s": round(elapsed, 2),
    })
    if err:
        print(f"  ERROR: {err}")
        findings.append({
            "id": "F-K-T3-3",
            "severity": "operational",
            "title": "Wrapper raises on outlier-injected series",
            "details": err,
        })
    else:
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        ll_finite = ll is not None and np.isfinite(ll)
        print(f"  status={res.get('status')}, log_lik={ll}, elapsed={elapsed:.2f}s")
        if not ll_finite:
            findings.append({
                "id": "F-K-T3-3-LL",
                "severity": "operational",
                "title": "log_likelihood non-finite on outlier series",
                "details": {"log_likelihood": ll},
            })

    # ---- C-CAL-4: T=200 near-unit-root AR(1) (φ=0.99) ----
    print("\n--- C-CAL-4: T=200 near-unit-root AR(1) (phi=0.99) ---")
    y = _generate_ar1(T=200, phi=0.99, sigma=1.0, seed=45)
    ctx = _build_ctx(y)
    res, elapsed, err = _safe_run(ctx)
    canonical_results.append({
        "id": "C-CAL-4", "case": "T=200 near-unit-root AR(1) (phi=0.99)",
        "status": res.get("status") if res else "ERROR",
        "error": err,
        "elapsed_s": round(elapsed, 2),
    })
    if err:
        print(f"  ERROR: {err}")
        findings.append({
            "id": "F-K-T3-4",
            "severity": "operational",
            "title": "Wrapper raises on near-unit-root AR(1) series",
            "details": err,
        })
    else:
        a = res.get("audit_fields", {}) or {}
        ll = a.get("log_likelihood")
        ll_finite = ll is not None and np.isfinite(ll)
        print(f"  status={res.get('status')}, log_lik={ll}, elapsed={elapsed:.2f}s")
        if not ll_finite:
            findings.append({
                "id": "F-K-T3-4-LL",
                "severity": "operational",
                "title": "log_likelihood non-finite on near-unit-root AR(1)",
                "details": {"log_likelihood": ll},
            })

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — Kalman filter / smoother")
    print("Date: 2026-04-25")
    print()

    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    # Discovered during Phase 2 Session 1 regression sweep
    # (K6); included here for findings-doc completeness.
    extra_findings = [
        {
            "id": "F-K-EXTRA-1",
            "severity": "operational",
            "title": "Pre-existing Windows cp1252 console UnicodeEncodeError in tools/validate_kalman_canonicals.py",
            "details": (
                "All 6 pre-existing canonicals failed to print "
                "Tier 2 prose containing Greek (mu, epsilon) or "
                "math (<=) symbols on Windows default console. "
                "Wrappers themselves succeed; failure is in the "
                "validation script's print statements only. "
                "Fixed in this session via stdout.reconfigure(utf-8) "
                "at script top (4 LOC, same pattern as "
                "parity_b7_h_latent_vs_stochvol.py)."
            ),
            "fix_applied": True,
            "fix_loc": 4,
            "fix_files": ["tools/validate_kalman_canonicals.py"],
        },
        {
            "id": "F-K-EXTRA-2",
            "severity": "operational",
            "title": "Same Windows cp1252 UnicodeEncodeError in SV validate scripts",
            "details": (
                "tools/validate_sv_mcmc_canonicals.py and "
                "tools/validate_sv_student_t_canonicals.py have the "
                "same pre-existing pattern as F-K-EXTRA-1. SV-specific "
                "Tier 2 prose contains phi (the persistence parameter) "
                "and check-mark symbols which fail to encode on Windows. "
                "Surfaced during K6 regression sweep on this session. "
                "Fixed inline at 6 LOC per file = 12 LOC, 2 files; "
                "satisfies CAL-R6 threshold."
            ),
            "fix_applied": True,
            "fix_loc": 12,
            "fix_files": [
                "tools/validate_sv_mcmc_canonicals.py",
                "tools/validate_sv_student_t_canonicals.py",
            ],
        },
    ]
    all_findings = (
        t1.get("findings", []) +
        t2.get("findings", []) +
        t3.get("findings", []) +
        extra_findings
    )

    by_sev = {"severe": 0, "operational": 0, "cosmetic": 0}
    for f in all_findings:
        sev = f.get("severity", "cosmetic")
        by_sev[sev] = by_sev.get(sev, 0) + 1

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

    # Save results JSON for the findings doc to render
    results = {
        "date": "2026-04-25",
        "wrapper": "kalman_filter / kalman_smoother",
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "kalman_audit_results.json"
    )

    def _coerce(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, dict):
            return {k: _coerce(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_coerce(v) for v in o]
        if isinstance(o, bool):
            return bool(o)
        if isinstance(o, (int, float, str, type(None))):
            return o
        return str(o)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_coerce(results), f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")

    # Per failure protocol: severe findings -> exit non-zero so caller knows
    return 1 if by_sev["severe"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
