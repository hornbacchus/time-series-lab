"""Calibration Audit Phase 2 Session 10 — ARIMA family batch.

Three forecasting wrappers in this batch:
  - arima (technique_id="arima"; manual order specification)
  - auto_arima (technique_id="auto_arima"; pmdarima auto-search)
    Both route to engine/techniques/arima.py (single module
    dispatching on ctx.technique_id at line 80).
  - sarima (engine/techniques/sarima.py; SARIMAX backend)

Three audit techniques per CAI Phase 1 §3.10:

  Sweep 0 — Variant dispatch + input-validation matrix
  (PRIORITY per Session 9 VECM precedent):
    Tests:
      - technique_id="arima" → manual ARIMA path
      - technique_id="auto_arima" → auto-search path
      - Invalid trend (sarima): zzz silently accepted?
      - Invalid order (arima/sarima): silently coerced?
      - Invalid information_criterion (auto_arima): silently
        accepted?

  Technique 1 — Parameter sweep:
    Sweep 1.1: Manual ARIMA order on synthetic ARMA(1,0,1)
    Sweep 1.2: auto_arima IC selection
    Sweep 1.3: SARIMA seasonal differencing

  Technique 2 — Real-data stress:
    5 macro series × 3 wrappers = 15 cells. Subsampled.

  Technique 3 — Adversarial canonicals (4 cases per wrapper):
    Constant series, white noise, random walk, short series.

CAL-R2 (parameter API):
  arima:
    - order (list/tuple of 3 ints; required for manual)
      with strict validation (returns error_response on bad
      input); auto_arima override via technique_id
    - seasonal_order (list/tuple of 4 ints; default [0,0,0,0])
    - horizon (int, default 10)
  auto_arima (same module):
    - seasonal (bool, default False)
    - m (int, default 1)
    - d (int, optional; None = auto)
    - max_p, max_q, max_d (int, preset-driven)
    - information_criterion (str, default "aic")
  sarima:
    - order (list/tuple of 3; default [1,1,1]; SILENT FALLBACK
      with warning on invalid)
    - seasonal_order (list/tuple of 4; default [1,1,1,m])
    - trend (str, default "n"; passed to SARIMAX without
      wrapper validation — Session 9-pattern candidate)
    - enforce_stationarity, enforce_invertibility (bool)
    - m (int)
    - horizon (int, default 10)

Run:
    python tools/calibration_audit/audit_arima_family.py
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
from techniques import arima as arima_mod
from techniques import sarima as sarima_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_arima",
                frequency="daily"):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_arma11(*, T=500, ar=0.7, ma=0.3, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = ar * y[t - 1] + eps[t] + ma * eps[t - 1]
    return y


def _simulate_random_walk(*, T=500, seed=42):
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.standard_normal(T))


def _simulate_seasonal_arma(*, T=500, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    seasonal = 2.0 * np.sin(2 * np.pi * t / period)
    eps = rng.standard_normal(T)
    arma = np.zeros(T)
    for i in range(1, T):
        arma[i] = 0.5 * arma[i - 1] + eps[i]
    return seasonal + arma


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0 — Dispatch + input-validation
# =====================================================


def sweep_0_dispatch_validation():
    print("\n" + "=" * 60)
    print("SWEEP 0: DISPATCH + INPUT-VALIDATION PROBE")
    print("=" * 60)

    findings = []
    y = _simulate_arma11(T=300, seed=42)

    # ---- Probe 1: technique_id dispatch arima vs auto_arima ----
    print("\n--- arima dispatch (manual path) ---")
    ctx = _build_ctx(y, technique_id="arima",
                     params={"order": [1, 0, 1]})
    res, elapsed, err = _safe_run(arima_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-AR-DISPATCH-MANUAL",
            "severity": "severe",
            "title": "ARIMA manual dispatch failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        method = a.get("method", "?")
        print(f"  status=success, method={method}, "
              f"AIC={a.get('aic')}, t={elapsed:.2f}s")
        if method != "manual":
            findings.append({
                "id": "F-AR-DISPATCH-MANUAL",
                "severity": "severe",
                "title": (
                    f"technique_id='arima' produced method={method!r}, "
                    f"expected 'manual'"
                ),
                "details": a,
            })

    print("\n--- auto_arima dispatch (auto path) ---")
    ctx = _build_ctx(y, technique_id="auto_arima",
                     params={})
    res, elapsed, err = _safe_run(arima_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-AR-DISPATCH-AUTO",
            "severity": "severe",
            "title": "auto_arima dispatch failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        method = a.get("method", "?")
        print(f"  status=success, method={method}, "
              f"AIC={a.get('aic')}, t={elapsed:.2f}s")
        if method != "auto_arima":
            findings.append({
                "id": "F-AR-DISPATCH-AUTO",
                "severity": "severe",
                "title": (
                    f"technique_id='auto_arima' produced method={method!r}, "
                    f"expected 'auto_arima'"
                ),
                "details": a,
            })

    # ---- Probe 2: ARIMA invalid order ----
    print("\n--- arima with invalid order=[1, 'abc', 0] ---")
    ctx = _build_ctx(y, technique_id="arima",
                     params={"order": [1, "abc", 0]})
    res, elapsed, err = _safe_run(arima_mod, ctx)
    arima_invalid_order_status = "unknown"
    if err:
        arima_invalid_order_status = f"raised: {err}"
    elif res:
        arima_invalid_order_status = (
            f"status={res.get('status')}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {arima_invalid_order_status}")

    # ---- Probe 3: SARIMA invalid trend (Session 9 VECM analog) ----
    print("\n--- sarima with invalid trend='zzz' ---")
    ctx = _build_ctx(y, technique_id="sarima",
                     params={"order": [1, 0, 1],
                             "seasonal_order": [0, 0, 0, 0],
                             "trend": "zzz"})
    res, elapsed, err = _safe_run(sarima_mod, ctx)
    sarima_invalid_trend_status = "unknown"
    if err:
        sarima_invalid_trend_status = f"raised: {err}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        sarima_invalid_trend_status = (
            f"status={res.get('status')}, "
            f"audit_trend={a.get('trend')!r}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {sarima_invalid_trend_status}")

    # If status=success AND audit_trend reports the invalid value,
    # that's a Session 9-style finding.
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("trend") == "zzz"):
        findings.append({
            "id": "F-AR-SARIMA-TREND",
            "severity": "severe",
            "title": (
                "SARIMA accepted invalid trend='zzz' silently (Session "
                "9-pattern: silent acceptance with audit_fields "
                "reporting the invalid value)"
            ),
            "details": {"audit_trend": "zzz"},
        })

    # ---- Probe 4: SARIMA invalid order (silent fallback documented) ----
    print("\n--- sarima with invalid order='abc' ---")
    ctx = _build_ctx(y, technique_id="sarima",
                     params={"order": "abc", "seasonal_order": [0, 0, 0, 0]})
    res, elapsed, err = _safe_run(sarima_mod, ctx)
    sarima_invalid_order_status = "unknown"
    if err:
        sarima_invalid_order_status = f"raised: {err}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        sarima_invalid_order_status = (
            f"status={res.get('status')}, "
            f"audit_order={a.get('order')!r}, "
            f"warnings={res.get('warnings')}"
        )
    print(f"  {sarima_invalid_order_status}")

    # ---- Probe 5: auto_arima invalid IC ----
    print("\n--- auto_arima with invalid information_criterion='xyz' ---")
    ctx = _build_ctx(y, technique_id="auto_arima",
                     params={"information_criterion": "xyz"})
    res, elapsed, err = _safe_run(arima_mod, ctx)
    auto_invalid_ic_status = "unknown"
    if err:
        auto_invalid_ic_status = f"raised: {err}"
    elif res:
        auto_invalid_ic_status = (
            f"status={res.get('status')}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {auto_invalid_ic_status}")

    return {
        "arima_invalid_order": arima_invalid_order_status,
        "sarima_invalid_trend": sarima_invalid_trend_status,
        "sarima_invalid_order": sarima_invalid_order_status,
        "auto_arima_invalid_ic": auto_invalid_ic_status,
        "findings": findings,
    }


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    y = _simulate_arma11(T=500, ar=0.7, ma=0.3, seed=42)

    # ---- Sweep 1.1: Manual ARIMA order ----
    print("\n--- Sweep 1.1: manual ARIMA order on ARMA(1,0,1) DGP ---")
    sweep11 = []
    for order_label, order in [
        ("(1,0,1)_truth", [1, 0, 1]),
        ("(2,0,1)", [2, 0, 1]),
        ("(1,0,2)", [1, 0, 2]),
        ("(2,0,2)", [2, 0, 2]),
        ("(3,0,3)_overparam", [3, 0, 3]),
    ]:
        ctx = _build_ctx(y, technique_id="arima",
                          params={"order": order})
        res, elapsed, err = _safe_run(arima_mod, ctx)
        if err:
            sweep11.append({"order_label": order_label,
                            "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "order_label": order_label,
            "order": order,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep11)} orders swept")
    for r in sweep11:
        print(f"    {r.get('order_label'):20s}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}")

    # Truth (1,0,1) should win on BIC (penalizes complexity more)
    bics = [(r["order_label"], r.get("bic")) for r in sweep11
            if r.get("bic") is not None]
    if bics:
        best_label = min(bics, key=lambda x: x[1])[0]
        print(f"  Best BIC: {best_label}")

    # ---- Sweep 1.2: auto_arima IC selection ----
    print("\n--- Sweep 1.2: auto_arima IC selection ---")
    sweep12 = []
    for ic in ["aic", "bic", "aicc"]:
        ctx = _build_ctx(y, technique_id="auto_arima",
                          params={"information_criterion": ic})
        res, elapsed, err = _safe_run(arima_mod, ctx)
        if err:
            sweep12.append({"ic": ic, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "ic": ic,
            "wrapper_status": res.get("status"),
            "selected_order": a.get("order") or a.get("selected_order"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep12)} IC values")
    for r in sweep12:
        print(f"    ic={r.get('ic'):4s}: order={r.get('selected_order')}, "
              f"AIC={r.get('aic')}, BIC={r.get('bic')}, "
              f"t={r.get('elapsed_s')}s")

    # ---- Sweep 1.3: SARIMA seasonal differencing ----
    print("\n--- Sweep 1.3: SARIMA seasonal differencing ---")
    y_seas = _simulate_seasonal_arma(T=500, period=12, seed=43)
    sweep13 = []
    for D in [0, 1]:
        ctx = _build_ctx(y_seas, technique_id="sarima",
                          params={"order": [1, 0, 0],
                                  "seasonal_order": [1, D, 1, 12]})
        res, elapsed, err = _safe_run(sarima_mod, ctx)
        if err:
            sweep13.append({"D": D, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "seasonal_D": D,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "rmse": a.get("rmse"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep13)} D values")
    for r in sweep13:
        print(f"    D={r.get('seasonal_D')}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}, RMSE={r.get('rmse')}, "
              f"t={r.get('elapsed_s')}s")

    return {
        "sweep_1_1_manual_order": sweep11,
        "sweep_1_2_ic_selection": sweep12,
        "sweep_1_3_seasonal_D": sweep13,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress (5 series × 3 wrappers)
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (5 series × 3 wrappers)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-AR-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_specs = [
        ("GSPC", "log_returns"),
        ("DGS10", "level"),
        ("DGS2", "level"),
        ("DEXUSEU", "log_returns"),
        ("GOLD", "log_returns"),
    ]
    cells = []
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        if prep == "log_returns":
            preprocessed = _log_returns(raw)
        else:
            preprocessed = raw[~np.isnan(raw)]
        T = preprocessed.size
        # Subsample to last 500 to keep auto_arima runtime bounded
        if T > 500:
            preprocessed = preprocessed[-500:]
            T = 500
        print(f"\n--- {sid} ({prep}, T={T}) ---")
        for tid, mod in [("arima", arima_mod),
                          ("auto_arima", arima_mod),
                          ("sarima", sarima_mod)]:
            params = {}
            if tid == "arima":
                params["order"] = [1, 1, 1] if prep == "level" else [1, 0, 1]
            elif tid == "auto_arima":
                pass  # use defaults
            else:  # sarima
                params["order"] = [1, 1, 1] if prep == "level" else [1, 0, 1]
                params["seasonal_order"] = [0, 0, 0, 0]
            ctx = _build_ctx(preprocessed, technique_id=tid,
                              params=params, preset="Balanced")
            res, elapsed, err = _safe_run(mod, ctx)
            if err:
                cells.append({"series": sid, "wrapper": tid, "T": T,
                              "status": "ERROR", "error": err})
                findings.append({
                    "id": f"F-AR-T2-{sid}-{tid.upper()}-ERROR",
                    "severity": "severe",
                    "title": f"Wrapper {tid} crashed on {sid}",
                    "details": err,
                })
                print(f"  {tid:11s}: ERROR — {err[:80]}")
                continue
            if res.get("status") != "success":
                findings.append({
                    "id": f"F-AR-T2-{sid}-{tid.upper()}-NONSUCCESS",
                    "severity": "operational",
                    "title": (
                        f"{tid} status={res.get('status')} on {sid}"
                    ),
                    "details": res.get("error_message"),
                })
                cells.append({"series": sid, "wrapper": tid, "T": T,
                              "status": res.get("status"),
                              "error_message": res.get("error_message")})
                print(f"  {tid:11s}: status={res.get('status')}, "
                      f"err={res.get('error_message')}")
                continue
            a = res.get("audit_fields", {}) or {}
            cells.append({
                "series": sid, "wrapper": tid, "T": T,
                "preprocessing": prep,
                "wrapper_status": res.get("status"),
                "order": a.get("order") or a.get("selected_order"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "rmse": a.get("rmse"),
                "method": a.get("method"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:11s}: order={a.get('order') or a.get('selected_order')}, "
                  f"AIC={a.get('aic')}, BIC={a.get('bic')}, "
                  f"t={elapsed:.1f}s")
            if elapsed > 30.0:
                findings.append({
                    "id": f"F-AR-T2-{sid}-{tid.upper()}-SLOW",
                    "severity": "operational",
                    "title": f"{tid} runtime {elapsed:.1f}s exceeds 30s on {sid}",
                    "details": {"series": sid, "wrapper": tid,
                                "elapsed_s": elapsed},
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

    # ---- C-CAL-1: Constant series ----
    print("\n--- C-CAL-1: Constant series (y=5.0) T=200 ---")
    y_const = np.full(200, 5.0)
    for tid, mod, params in [
        ("arima", arima_mod, {"order": [1, 0, 1]}),
        ("auto_arima", arima_mod, {}),
        ("sarima", sarima_mod, {"order": [1, 0, 1],
                                  "seasonal_order": [0, 0, 0, 0]}),
    ]:
        ctx = _build_ctx(y_const, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-1", "wrapper": tid,
                                       "status": "ERROR", "error": err})
            print(f"  {tid:11s}: EXCEPTION — {err[:60]}")
            continue
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-1", "wrapper": tid,
            "case": "constant series",
            "status": res.get("status"),
            "error_message": res.get("error_message"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:11s}: status={res.get('status')}, "
              f"err={res.get('error_message')!s:.60s}")

    # ---- C-CAL-2: Pure white noise ----
    print("\n--- C-CAL-2: White noise N(0,1) T=300 ---")
    rng = np.random.default_rng(42)
    y_wn = rng.standard_normal(300)
    for tid, mod, params in [
        ("auto_arima", arima_mod, {}),
    ]:
        ctx = _build_ctx(y_wn, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-2", "wrapper": tid,
                                       "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-2", "wrapper": tid,
            "case": "white noise (expect order ≈ (0,0,0))",
            "status": res.get("status"),
            "selected_order": a.get("order") or a.get("selected_order"),
            "aic": a.get("aic"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:11s}: order={a.get('order') or a.get('selected_order')}, "
              f"AIC={a.get('aic')}")

    # ---- C-CAL-3: Random walk ----
    print("\n--- C-CAL-3: Random walk T=300 (auto_arima should pick d=1) ---")
    y_rw = _simulate_random_walk(T=300, seed=43)
    ctx = _build_ctx(y_rw, technique_id="auto_arima", params={})
    res, elapsed, err = _safe_run(arima_mod, ctx)
    if err:
        canonical_results.append({"id": "C-CAL-3", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        order = a.get("order") or a.get("selected_order")
        canonical_results.append({
            "id": "C-CAL-3", "wrapper": "auto_arima",
            "case": "random walk (expect d=1)",
            "status": res.get("status"),
            "selected_order": order,
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  auto_arima: order={order}")

    # ---- C-CAL-4: Short series ----
    print("\n--- C-CAL-4: Short series T=30 ---")
    y_short = _simulate_arma11(T=30, seed=44)
    for tid, mod, params in [
        ("arima", arima_mod, {"order": [1, 0, 1]}),
        ("auto_arima", arima_mod, {}),
        ("sarima", sarima_mod, {"order": [1, 0, 1],
                                  "seasonal_order": [0, 0, 0, 0]}),
    ]:
        ctx = _build_ctx(y_short, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-4", "wrapper": tid,
                                       "status": "ERROR",
                                       "error": err[:120]})
            print(f"  {tid:11s}: EXCEPTION — {err[:60]}")
            continue
        canonical_results.append({
            "id": "C-CAL-4", "wrapper": tid,
            "case": "short series T=30",
            "status": res.get("status"),
            "error_message": res.get("error_message"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:11s}: status={res.get('status')}, "
              f"err={res.get('error_message')!s:.60s}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — ARIMA family (CAI Session 10)")
    print("Date: 2026-04-26")
    print()

    s0 = sweep_0_dispatch_validation()
    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (
        s0.get("findings", []) +
        t1.get("findings", []) +
        t2.get("findings", []) +
        t3.get("findings", []) +
        list(_EXTRA_FINDINGS)
    )
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
        "wrappers": ["arima", "auto_arima", "sarima"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "arima_family_audit_results.json"
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
        if isinstance(o, (bool, int, float, str, type(None))):
            return o
        return str(o)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_coerce(results), f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    return 1 if by_sev["severe"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
