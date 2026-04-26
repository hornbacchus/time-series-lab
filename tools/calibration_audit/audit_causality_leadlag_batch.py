"""Calibration Audit Phase 2 Session 14 — Causality / Lead-Lag batch.

Six wrappers:
  - granger_causality
  - cross_correlation_lag
  - gcc_phat_delay
  - prewhitened_ccf_lag
  - rolling_ccf_lag
  - dtw_alignment_lag

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation
    matrix per wrapper.
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (rates pair primary)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_causality_leadlag_batch.py
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
from techniques import granger_causality as gr_mod
from techniques import cross_correlation_lag as ccf_mod
from techniques import gcc_phat_delay as gcc_mod
from techniques import prewhitened_ccf_lag as pwccf_mod
from techniques import rolling_ccf_lag as rccf_mod
from techniques import dtw_alignment_lag as dtw_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx_pair(y1, y2, *, technique_id, params=None,
                     preset="Balanced", run_id="audit_cl",
                     frequency="daily", names=("x", "y")):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(y1))),
        "series": [{"name": names[0], "values": list(y1)},
                    {"name": names[1], "values": list(y2)}],
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_lagged_pair(*, T=400, lag=5, seed=42):
    """y_t = x_{t-lag} + noise"""
    rng = np.random.default_rng(seed)
    x = np.zeros(T)
    eps = rng.standard_normal(T)
    for t in range(1, T):
        x[t] = 0.7 * x[t - 1] + eps[t]
    y = np.zeros(T)
    y[lag:] = x[:-lag] + 0.3 * rng.standard_normal(T - lag)
    return x, y


def _simulate_independent(*, T=400, seed=42):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(T), rng.standard_normal(T)


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
    print("SWEEP 0: DISPATCH + INPUT-VALIDATION (6 wrappers)")
    print("=" * 60)

    findings = []
    x, y = _simulate_lagged_pair(T=400, lag=5, seed=42)

    # ---- granger_causality ----
    print("\n--- granger_causality baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="granger_causality",
                          params={"max_lag": 5})
    res, elapsed, err = _safe_run(gr_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-CL-GR-BASELINE", "severity": "severe",
                          "title": "granger_causality baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    # ---- cross_correlation_lag ----
    print("\n--- cross_correlation_lag baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="cross_correlation_lag",
                          params={"max_lag": 20})
    res, elapsed, err = _safe_run(ccf_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-CL-CCF-BASELINE", "severity": "severe",
                          "title": "cross_correlation_lag baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    # ---- gcc_phat_delay baseline + invalid weighting ----
    print("\n--- gcc_phat_delay baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="gcc_phat_delay",
                          params={"max_lag": 20})
    res, elapsed, err = _safe_run(gcc_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-CL-GCC-BASELINE", "severity": "severe",
                          "title": "gcc_phat_delay baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- gcc_phat_delay invalid weighting='zzz' ---")
    ctx = _build_ctx_pair(x, y, technique_id="gcc_phat_delay",
                          params={"weighting": "zzz", "max_lag": 20})
    res, elapsed, err = _safe_run(gcc_mod, ctx)
    gcc_inv_w = "unknown"
    if err:
        gcc_inv_w = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        gcc_inv_w = (
            f"status={res.get('status')}, "
            f"audit_weighting={a.get('weighting')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {gcc_inv_w}")
    if (res and res.get("status") == "success"
            and str((res.get("audit_fields") or {}).get("weighting", ""))
                .lower() == "zzz"):
        findings.append({
            "id": "F-CL-GCC-WEIGHTING",
            "severity": "severe",
            "title": "gcc_phat_delay accepted invalid weighting='zzz' silently",
            "details": {"audit_weighting": "zzz"},
        })

    # ---- prewhitened_ccf_lag baseline ----
    print("\n--- prewhitened_ccf_lag baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="prewhitened_ccf_lag",
                          params={"max_lag": 20})
    res, elapsed, err = _safe_run(pwccf_mod, ctx)
    pwccf_baseline_status = "unknown"
    if err:
        pwccf_baseline_status = f"ERROR: {err[:120]}"
        # Important: this may surface the Session 10 pmdarima bug
        # if pwccf calls pm.auto_arima with default seasonal=False
        # and triggers start_P > max_P.
        findings.append({
            "id": "F-CL-PWCCF-BASELINE",
            "severity": "severe",
            "title": (
                "prewhitened_ccf_lag baseline failed; check for "
                "Session 10 pmdarima start_P bug inheritance"
            ),
            "details": err[:200],
        })
    elif res.get("status") != "success":
        findings.append({"id": "F-CL-PWCCF-BASELINE", "severity": "severe",
                          "title": "prewhitened_ccf_lag baseline failed",
                          "details": res.get("error_message")})
        pwccf_baseline_status = (
            f"status={res.get('status')}, "
            f"err={res.get('error_message')!s:.120s}"
        )
    else:
        a = res.get("audit_fields", {}) or {}
        pwccf_baseline_status = f"status=success, t={elapsed:.2f}s"
    print(f"  {pwccf_baseline_status}")

    # ---- rolling_ccf_lag baseline ----
    print("\n--- rolling_ccf_lag baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="rolling_ccf_lag",
                          params={"max_lag": 20})
    res, elapsed, err = _safe_run(rccf_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-CL-RCCF-BASELINE", "severity": "severe",
                          "title": "rolling_ccf_lag baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    # ---- dtw_alignment_lag baseline + invalid step_pattern ----
    print("\n--- dtw_alignment_lag baseline ---")
    ctx = _build_ctx_pair(x, y, technique_id="dtw_alignment_lag",
                          params={})
    res, elapsed, err = _safe_run(dtw_mod, ctx)
    if err or res.get("status") != "success":
        findings.append({"id": "F-CL-DTW-BASELINE", "severity": "severe",
                          "title": "dtw_alignment_lag baseline failed",
                          "details": err or res.get("error_message")})
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    print("\n--- dtw_alignment_lag invalid step_pattern='zzz' ---")
    ctx = _build_ctx_pair(x, y, technique_id="dtw_alignment_lag",
                          params={"step_pattern": "zzz"})
    res, elapsed, err = _safe_run(dtw_mod, ctx)
    dtw_inv_sp = "unknown"
    if err:
        dtw_inv_sp = f"raised: {err[:80]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        dtw_inv_sp = (
            f"status={res.get('status')}, "
            f"audit_step_pattern={a.get('step_pattern')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {dtw_inv_sp}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("step_pattern") == "zzz"):
        findings.append({
            "id": "F-CL-DTW-STEP",
            "severity": "severe",
            "title": "dtw_alignment_lag accepted invalid step_pattern='zzz' silently",
            "details": {"audit_step_pattern": "zzz"},
        })

    return {
        "gcc_invalid_weighting": gcc_inv_w,
        "dtw_invalid_step_pattern": dtw_inv_sp,
        "pwccf_baseline_status": pwccf_baseline_status,
        "findings": findings,
    }


# =====================================================
# Technique 1 — Compressed parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: COMPRESSED PARAMETER SWEEPS")
    print("=" * 60)

    findings = []
    x, y = _simulate_lagged_pair(T=400, lag=5, seed=42)

    # GCC weighting comparison (other than baseline)
    print("\n--- GCC weighting sweep ---")
    gcc_sweep = []
    for w in ["phat", "scot", "roth"]:
        ctx = _build_ctx_pair(x, y, technique_id="gcc_phat_delay",
                              params={"weighting": w, "max_lag": 20})
        res, elapsed, err = _safe_run(gcc_mod, ctx)
        if err:
            gcc_sweep.append({"w": w, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        gcc_sweep.append({
            "weighting": w,
            "wrapper_status": res.get("status"),
            "delay": a.get("estimated_delay") or a.get("delay"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  weighting={w}: status={res.get('status')}, "
              f"t={elapsed:.2f}s")

    # CCF normalize toggle
    print("\n--- CCF normalize toggle ---")
    ccf_sweep = []
    for norm in [True, False]:
        ctx = _build_ctx_pair(x, y, technique_id="cross_correlation_lag",
                              params={"normalize": norm, "max_lag": 20})
        res, elapsed, err = _safe_run(ccf_mod, ctx)
        if err:
            ccf_sweep.append({"norm": norm, "status": "ERROR",
                              "error": err})
            continue
        ccf_sweep.append({
            "normalize": norm,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  normalize={norm}: status={res.get('status')}, "
              f"t={elapsed:.2f}s")

    # DTW step_pattern symmetric1 vs symmetric2
    print("\n--- DTW step_pattern sweep ---")
    dtw_sweep = []
    for sp in ["symmetric1", "symmetric2"]:
        ctx = _build_ctx_pair(x, y, technique_id="dtw_alignment_lag",
                              params={"step_pattern": sp})
        res, elapsed, err = _safe_run(dtw_mod, ctx)
        if err:
            dtw_sweep.append({"sp": sp, "status": "ERROR", "error": err})
            continue
        dtw_sweep.append({
            "step_pattern": sp,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  step_pattern={sp}: status={res.get('status')}, "
              f"t={elapsed:.2f}s")

    return {"gcc_weighting": gcc_sweep, "ccf_normalize": ccf_sweep,
             "dtw_step_pattern": dtw_sweep, "findings": findings}


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (rates pair)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({"id": "F-CL-T2-MISSING", "severity": "severe",
                          "title": "Real-data fixture missing"})
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    dgs2 = _yield_diffs(data["DGS2"])[-500:]
    dgs10 = _yield_diffs(data["DGS10"])[-500:]
    n = min(len(dgs2), len(dgs10))
    dgs2 = dgs2[-n:]
    dgs10 = dgs10[-n:]
    print(f"\n--- Rates pair (DGS2, DGS10) T={n} ---")
    cells = []
    for tid, mod, params in [
        ("granger_causality", gr_mod, {"max_lag": 5}),
        ("cross_correlation_lag", ccf_mod, {"max_lag": 20}),
        ("gcc_phat_delay", gcc_mod, {"max_lag": 20}),
        ("prewhitened_ccf_lag", pwccf_mod, {"max_lag": 20}),
        ("rolling_ccf_lag", rccf_mod, {"max_lag": 20}),
        ("dtw_alignment_lag", dtw_mod, {}),
    ]:
        ctx = _build_ctx_pair(dgs2, dgs10, technique_id=tid,
                              params=params, preset="Balanced",
                              names=("DGS2", "DGS10"))
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            cells.append({"wrapper": tid, "status": "ERROR",
                          "error": err[:80]})
            findings.append({
                "id": f"F-CL-T2-{tid.upper()}-ERROR",
                "severity": "severe",
                "title": f"{tid} crashed on rates pair",
                "details": err[:200],
            })
            print(f"  {tid:25s}: ERROR — {err[:60]}")
            continue
        a = res.get("audit_fields", {}) or {}
        cells.append({
            "wrapper": tid, "T": int(n),
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:25s}: status={res.get('status')}, "
              f"t={elapsed:.1f}s")
        if elapsed > 30.0:
            findings.append({
                "id": f"F-CL-T2-{tid.upper()}-SLOW",
                "severity": "operational",
                "title": f"{tid} runtime {elapsed:.1f}s on rates pair",
                "details": {"elapsed_s": elapsed},
            })

    return {"baselines": cells, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonical exercises
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Independent series — should NOT find spurious ----
    print("\n--- C-CAL-1: Independent series T=400 ---")
    x, y = _simulate_independent(T=400, seed=42)
    for tid, mod, params in [
        ("granger_causality", gr_mod, {"max_lag": 5}),
        ("cross_correlation_lag", ccf_mod, {"max_lag": 20}),
        ("gcc_phat_delay", gcc_mod, {"max_lag": 20}),
    ]:
        ctx = _build_ctx_pair(x, y, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-1", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:25s}: status={s}")

    # ---- C-CAL-2: Known lag recovery ----
    print("\n--- C-CAL-2: Known lag=8 recovery T=400 ---")
    x, y = _simulate_lagged_pair(T=400, lag=8, seed=44)
    for tid, mod, params in [
        ("cross_correlation_lag", ccf_mod, {"max_lag": 20}),
        ("gcc_phat_delay", gcc_mod, {"max_lag": 20}),
    ]:
        ctx = _build_ctx_pair(x, y, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-2", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:25s}: status={s}")

    # ---- C-CAL-3: Constant series ----
    print("\n--- C-CAL-3: Constant + variable ---")
    rng = np.random.default_rng(45)
    x_const = np.full(300, 5.0)
    y_var = rng.standard_normal(300)
    for tid, mod, params in [
        ("cross_correlation_lag", ccf_mod, {"max_lag": 10}),
        ("dtw_alignment_lag", dtw_mod, {}),
    ]:
        ctx = _build_ctx_pair(x_const, y_var, technique_id=tid,
                              params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-3", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:25s}: status={s}")

    # ---- C-CAL-4: Short series ----
    print("\n--- C-CAL-4: Short series T=50 ---")
    rng = np.random.default_rng(46)
    x_short, y_short = rng.standard_normal(50), rng.standard_normal(50)
    for tid, mod, params in [
        ("granger_causality", gr_mod, {"max_lag": 3}),
        ("cross_correlation_lag", ccf_mod, {"max_lag": 10}),
    ]:
        ctx = _build_ctx_pair(x_short, y_short, technique_id=tid,
                              params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-4", "wrapper": tid,
            "status": res.get("status") if res else "ERROR",
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:25s}: status={s}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — Causality/Lead-Lag batch (CAI Session 14)")
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
        "wrappers": ["granger_causality", "cross_correlation_lag",
                      "gcc_phat_delay", "prewhitened_ccf_lag",
                      "rolling_ccf_lag", "dtw_alignment_lag"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (_ROOT / "tools" / "calibration_audit"
                / "causality_leadlag_batch_audit_results.json")

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
