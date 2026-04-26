"""Calibration Audit Phase 2 Session 11 — forecasting classical batch 2.

Closes the forecasting-classical extension batch. Three wrappers:
  - arimax_sarimax (engine/techniques/arimax_sarimax.py;
    statsmodels SARIMAX backend, NOT pmdarima — Session 10's
    start_P bug NOT inherited)
  - intermittent_demand (engine/techniques/intermittent_demand.py;
    Croston/SBA/TSB methods)
  - theta_forecast (engine/techniques/theta_forecast.py;
    statsmodels ThetaModel)

Three audit techniques per CAI Phase 1 §3.11:

  Sweep 0 — Variant dispatch + input-validation matrix
  (priority per Sessions 9-10 VECM/auto_arima precedents):
    arimax_sarimax: invalid trend / invalid order
    intermittent_demand: invalid method / dispatch correctness
    theta_forecast: edge cases on horizon and deseasonalize

  Technique 1 — Parameter sweep
  Technique 2 — Real-data stress
  Technique 3 — Adversarial canonicals (mirrored in 3 NEW
    canonical scripts per CAL-R4)

CAL-R2 (parameter API):
  arimax_sarimax:
    - order (list[int] of 3; auto via grid_search if absent)
    - seasonal_order (list[int] of 4; default [0,0,0,0])
    - trend (str, default 'c'; passed to SARIMAX without
      wrapper allowlist)
    - enforce_stationarity, enforce_invertibility (bool)
    - horizon (int, default 10)
  intermittent_demand:
    - method (str or list, optional; preset-driven defaults
      Croston/SBA/TSB)
    - alpha, beta (float, optional)
    - horizon (int, default 10)
    - Invalid method: warn + skip (NOT error_response)
  theta_forecast:
    - horizon (int, default 10)
    - period (optional int; auto-inferred from frequency)
    - deseasonalize (bool, default True)

Run:
    python tools/calibration_audit/audit_forecasting_classical_batch2.py
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
from techniques import arimax_sarimax as ax_mod
from techniques import intermittent_demand as id_mod
from techniques import theta_forecast as th_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_fc",
                frequency="daily", series_extra=None):
    user_params = dict(params or {})
    series = [{"name": "y", "values": list(values)}]
    if series_extra:
        for name, vals in series_extra:
            series.append({"name": name, "values": list(vals)})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
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


def _simulate_arma11(*, T=500, ar=0.7, ma=0.3, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = ar * y[t - 1] + eps[t] + ma * eps[t - 1]
    return y


def _simulate_intermittent(*, T=200, zero_density=0.7, seed=42):
    """Synthetic intermittent demand series.

    Generates zero/positive sequence with given zero_density.
    Positive values are integer Poisson(lambda=3) draws.
    """
    rng = np.random.default_rng(seed)
    is_zero = rng.random(T) < zero_density
    demand = rng.poisson(3.0, size=T) + 1  # positive
    demand = np.where(is_zero, 0, demand)
    return demand.astype(float)


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

    # ---- arimax_sarimax: valid baseline (no exog) ----
    print("\n--- arimax_sarimax baseline (no exog) ---")
    ctx = _build_ctx(y, technique_id="sarimax",
                     params={"order": [1, 0, 1]})
    res, elapsed, err = _safe_run(ax_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-FC-AX-BASELINE",
            "severity": "severe",
            "title": "arimax_sarimax baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, AIC={a.get('aic')}, t={elapsed:.2f}s")

    # ---- arimax_sarimax: with exogenous regressor ----
    print("\n--- arimax_sarimax with exog ---")
    rng = np.random.default_rng(43)
    x_exog = rng.standard_normal(300)
    ctx = _build_ctx(y, technique_id="sarimax",
                     params={"order": [1, 0, 1]},
                     series_extra=[("x", x_exog)])
    res, elapsed, err = _safe_run(ax_mod, ctx)
    if err or res is None or res.get("status") != "success":
        print(f"  exog: ERROR — {err or res.get('error_message')}")
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  exog status=success, AIC={a.get('aic')}, "
              f"t={elapsed:.2f}s")

    # ---- arimax_sarimax: invalid trend ----
    print("\n--- arimax_sarimax invalid trend='zzz' ---")
    ctx = _build_ctx(y, technique_id="sarimax",
                     params={"order": [1, 0, 1], "trend": "zzz"})
    res, elapsed, err = _safe_run(ax_mod, ctx)
    ax_invalid_trend = "unknown"
    if err:
        ax_invalid_trend = f"raised: {err[:100]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        ax_invalid_trend = (
            f"status={res.get('status')}, "
            f"audit_trend={a.get('trend')!r}, "
            f"err_msg={res.get('error_message')!s:.80s}"
        )
    print(f"  {ax_invalid_trend}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("trend") == "zzz"):
        findings.append({
            "id": "F-FC-AX-TREND",
            "severity": "severe",
            "title": (
                "arimax_sarimax accepted invalid trend='zzz' silently "
                "(Session 9-pattern)"
            ),
            "details": {"audit_trend": "zzz"},
        })

    # ---- intermittent_demand: valid baseline ----
    print("\n--- intermittent_demand baseline (default Croston) ---")
    y_int = _simulate_intermittent(T=200, zero_density=0.6, seed=44)
    ctx = _build_ctx(y_int, technique_id="intermittent_demand",
                     params={})
    res, elapsed, err = _safe_run(id_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-FC-ID-BASELINE",
            "severity": "severe",
            "title": "intermittent_demand baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, "
              f"selected_method={a.get('best_method')}, "
              f"t={elapsed:.2f}s")

    # ---- intermittent_demand: each method explicitly ----
    print("\n--- intermittent_demand method dispatch ---")
    for method in ["croston", "sba", "tsb"]:
        ctx = _build_ctx(y_int, technique_id="intermittent_demand",
                         params={"method": method})
        res, elapsed, err = _safe_run(id_mod, ctx)
        if err or res is None or res.get("status") != "success":
            findings.append({
                "id": f"F-FC-ID-{method.upper()}",
                "severity": "severe",
                "title": f"intermittent_demand method={method} failed",
                "details": err or res.get("error_message"),
            })
            print(f"  method={method}: ERROR — {err or res.get('error_message')}")
            continue
        a = res.get("audit_fields", {}) or {}
        print(f"  method={method}: status=success, "
              f"best_method={a.get('best_method')}, "
              f"t={elapsed:.2f}s")
        # Verify dispatch correctness (case-insensitive — wrapper
        # normalizes method names to uppercase per audit-field
        # convention): when explicitly requesting one method,
        # best_method.lower() should match the request.
        bm = a.get("best_method")
        if bm and str(bm).lower() != method.lower():
            findings.append({
                "id": f"F-FC-ID-{method.upper()}-DISPATCH",
                "severity": "severe",
                "title": (
                    f"Requested method={method!r}, but best_method="
                    f"{bm!r} reported (case-insensitive mismatch)"
                ),
                "details": a,
            })

    # ---- intermittent_demand: invalid method ----
    print("\n--- intermittent_demand invalid method='xxx' ---")
    ctx = _build_ctx(y_int, technique_id="intermittent_demand",
                     params={"method": "xxx"})
    res, elapsed, err = _safe_run(id_mod, ctx)
    id_invalid_method = "unknown"
    if err:
        id_invalid_method = f"raised: {err[:100]}"
    elif res:
        warns = res.get("warnings") or []
        warn_about_xxx = any("xxx" in str(w).lower() for w in warns)
        id_invalid_method = (
            f"status={res.get('status')}, "
            f"warning_about_xxx={warn_about_xxx}, "
            f"err_msg={res.get('error_message')!s:.80s}"
        )
    print(f"  {id_invalid_method}")

    # ---- theta_forecast: baseline ----
    print("\n--- theta_forecast baseline ---")
    ctx = _build_ctx(y, technique_id="theta_forecast", params={})
    res, elapsed, err = _safe_run(th_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-FC-TH-BASELINE",
            "severity": "severe",
            "title": "theta_forecast baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.2f}s")

    return {
        "ax_invalid_trend": ax_invalid_trend,
        "id_invalid_method": id_invalid_method,
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
    y = _simulate_arma11(T=500, seed=42)

    # ---- Sweep 1.1 (arimax_sarimax): order ----
    print("\n--- Sweep 1.1: arimax_sarimax orders on ARMA(1,0,1) ---")
    sweep11 = []
    for order in [[1, 0, 1], [2, 0, 1], [1, 0, 2], [2, 0, 2]]:
        ctx = _build_ctx(y, technique_id="sarimax",
                          params={"order": order})
        res, elapsed, err = _safe_run(ax_mod, ctx)
        if err:
            sweep11.append({"order": order, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "order": order,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep11:
        print(f"    order={r.get('order')}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}, t={r.get('elapsed_s')}s")

    # ---- Sweep 1.2 (intermittent_demand): method comparison ----
    print("\n--- Sweep 1.2: id method comparison on intermittent ---")
    y_int = _simulate_intermittent(T=200, zero_density=0.7, seed=45)
    sweep12 = []
    for method in ["croston", "sba", "tsb"]:
        ctx = _build_ctx(y_int, technique_id="intermittent_demand",
                          params={"method": method})
        res, elapsed, err = _safe_run(id_mod, ctx)
        if err:
            sweep12.append({"method": method, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "method": method,
            "wrapper_status": res.get("status"),
            "best_method": a.get("best_method"),
            "best_alpha": a.get("best_alpha"),
            "mse": a.get("mse"),
            "demand_density": a.get("demand_density"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep12:
        print(f"    method={r.get('method')}: MSE={r.get('mse')}, "
              f"alpha={r.get('best_alpha')}, "
              f"density={r.get('demand_density')}, "
              f"t={r.get('elapsed_s')}s")

    # ---- Sweep 1.3 (theta_forecast): horizon ----
    print("\n--- Sweep 1.3: theta_forecast horizon sweep ---")
    sweep13 = []
    for h in [1, 5, 10, 22]:
        ctx = _build_ctx(y, technique_id="theta_forecast",
                          params={"horizon": h})
        res, elapsed, err = _safe_run(th_mod, ctx)
        if err:
            sweep13.append({"horizon": h, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "horizon": h,
            "wrapper_status": res.get("status"),
            "n_obs": a.get("n_obs"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep13:
        print(f"    horizon={r.get('horizon')}: status={r.get('wrapper_status')}, "
              f"t={r.get('elapsed_s')}s")

    return {
        "sweep_1_1_ax_order": sweep11,
        "sweep_1_2_id_method": sweep12,
        "sweep_1_3_th_horizon": sweep13,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-FC-T2-MISSING",
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

    # arimax_sarimax + theta_forecast on all 5 series
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        if prep == "log_returns":
            preprocessed = _log_returns(raw)
        else:
            preprocessed = raw[~np.isnan(raw)]
        T = preprocessed.size
        if T > 500:
            preprocessed = preprocessed[-500:]
            T = 500
        print(f"\n--- {sid} ({prep}, T={T}) ---")
        for tid, mod, default_params in [
            ("sarimax", ax_mod,
             {"order": [1, 1, 1] if prep == "level" else [1, 0, 1]}),
            ("theta_forecast", th_mod, {}),
        ]:
            ctx = _build_ctx(preprocessed, technique_id=tid,
                              params=default_params, preset="Balanced")
            res, elapsed, err = _safe_run(mod, ctx)
            if err:
                cells.append({"series": sid, "wrapper": tid,
                              "status": "ERROR", "error": err})
                findings.append({
                    "id": f"F-FC-T2-{sid}-{tid.upper()}-ERROR",
                    "severity": "severe",
                    "title": f"{tid} crashed on {sid}",
                    "details": err,
                })
                print(f"  {tid:15s}: ERROR — {err[:80]}")
                continue
            if res.get("status") != "success":
                findings.append({
                    "id": f"F-FC-T2-{sid}-{tid.upper()}-NONSUCCESS",
                    "severity": "operational",
                    "title": f"{tid} status={res.get('status')} on {sid}",
                    "details": res.get("error_message"),
                })
            a = res.get("audit_fields", {}) or {}
            cells.append({
                "series": sid, "wrapper": tid, "T": T,
                "preprocessing": prep,
                "wrapper_status": res.get("status"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "rmse": a.get("rmse"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:15s}: status={res.get('status')}, "
                  f"AIC={a.get('aic')}, t={elapsed:.1f}s")
            if elapsed > 30.0:
                findings.append({
                    "id": f"F-FC-T2-{sid}-{tid.upper()}-SLOW",
                    "severity": "operational",
                    "title": f"{tid} runtime {elapsed:.1f}s on {sid}",
                    "details": {"series": sid, "elapsed_s": elapsed},
                })

    # intermittent_demand: synthetic intermittent fixtures
    print("\n--- intermittent_demand on synthetic fixtures ---")
    for label, density in [
        ("low_density_30", 0.3),
        ("typical_60", 0.6),
        ("sparse_85", 0.85),
    ]:
        y_int = _simulate_intermittent(T=200, zero_density=density,
                                         seed=46)
        ctx = _build_ctx(y_int, technique_id="intermittent_demand",
                          params={}, preset="Balanced")
        res, elapsed, err = _safe_run(id_mod, ctx)
        if err:
            cells.append({"label": label, "status": "ERROR",
                          "error": err})
            print(f"  {label}: ERROR — {err[:80]}")
            continue
        a = res.get("audit_fields", {}) or {}
        cells.append({
            "label": label,
            "wrapper": "intermittent_demand",
            "zero_density_dgp": density,
            "wrapper_status": res.get("status"),
            "best_method": a.get("best_method"),
            "demand_density": a.get("demand_density"),
            "mse": a.get("mse"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {label}: best_method={a.get('best_method')}, "
              f"density={a.get('demand_density')}, "
              f"MSE={a.get('mse')}, t={elapsed:.1f}s")

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
    print("\n--- C-CAL-1: Constant series y=5.0 T=200 ---")
    y_const = np.full(200, 5.0)
    for tid, mod, params in [
        ("sarimax", ax_mod, {"order": [1, 0, 1]}),
        ("theta_forecast", th_mod, {}),
    ]:
        ctx = _build_ctx(y_const, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-1", "wrapper": tid,
            "case": "constant series",
            "status": res.get("status") if res else "ERROR",
            "error_message": (res.get("error_message") if res
                              else err),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:15s}: status={res.get('status') if res else 'ERROR'}, "
              f"err={res.get('error_message') if res else err!s:.50s}")

    # ---- C-CAL-2: Random walk ----
    print("\n--- C-CAL-2: Random walk T=300 ---")
    rng = np.random.default_rng(43)
    y_rw = np.cumsum(rng.standard_normal(300))
    ctx = _build_ctx(y_rw, technique_id="sarimax",
                      params={"order": [0, 1, 0]})
    res, elapsed, err = _safe_run(ax_mod, ctx)
    if err:
        canonical_results.append({"id": "C-CAL-2", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-2", "wrapper": "sarimax",
            "case": "random walk + ARIMA(0,1,0)",
            "status": res.get("status"),
            "aic": a.get("aic"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  sarimax: status={res.get('status')}, AIC={a.get('aic')}")

    # ---- C-CAL-3: Short series ----
    print("\n--- C-CAL-3: Short series T=30 ---")
    y_short = _simulate_arma11(T=30, seed=44)
    for tid, mod, params in [
        ("sarimax", ax_mod, {"order": [1, 0, 1]}),
        ("theta_forecast", th_mod, {}),
    ]:
        ctx = _build_ctx(y_short, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-3", "wrapper": tid,
            "case": "short series T=30",
            "status": res.get("status") if res else "ERROR",
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  {tid:15s}: status={res.get('status') if res else 'ERROR'}")

    # ---- C-CAL-4: All-zeros (intermittent edge case) ----
    print("\n--- C-CAL-4: All-zeros series + intermittent_demand ---")
    y_zeros = np.zeros(200)
    ctx = _build_ctx(y_zeros, technique_id="intermittent_demand",
                      params={})
    res, elapsed, err = _safe_run(id_mod, ctx)
    canonical_results.append({
        "id": "C-CAL-4", "wrapper": "intermittent_demand",
        "case": "all-zeros (degenerate)",
        "status": res.get("status") if res else "ERROR",
        "error_message": (res.get("error_message") if res else err),
        "elapsed_s": round(elapsed, 2),
    })
    print(f"  intermittent: status={res.get('status') if res else 'ERROR'}, "
          f"err={res.get('error_message') if res else err!s:.60s}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — Forecasting Classical batch 2 "
          "(CAI Session 11)")
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
        "wrappers": ["arimax_sarimax", "intermittent_demand",
                      "theta_forecast"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "forecasting_classical_batch2_audit_results.json"
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
