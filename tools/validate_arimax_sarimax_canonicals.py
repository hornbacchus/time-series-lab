"""Phase 5 canonical validation for arimax_sarimax
(`engine/techniques/arimax_sarimax.py`).

Created from scratch by CAI Phase 2 Session 11.

Nine canonicals:

  Base set (1-5):
    canonical_1 — SARIMAX(1,0,1) recovery on synthetic ARMA(1,1)
    canonical_2 — With exogenous regressor
    canonical_3 — Real DGS10 yield level smoke test
    canonical_4 — Trend variants {n, c, t, ct}
    canonical_5 — Invalid trend rejected by statsmodels

  CAI Session 11 adversarial set (6-9):
    canonical_6 (C-CAL-1) — Constant series
    canonical_7 (C-CAL-2) — Random walk + ARIMA(0,1,0)
    canonical_8 (C-CAL-3) — Short series T=30
    canonical_9 (C-CAL-4) — Seasonal with non-zero seasonal_order

Run from project root:
    python tools/validate_arimax_sarimax_canonicals.py
"""

import math
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import arimax_sarimax as ax_mod


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(values, *, params=None, preset="Balanced",
                series_extra=None):
    series = [{"name": "y", "values": list(values)}]
    if series_extra:
        for name, vals in series_extra:
            series.append({"name": name, "values": list(vals)})
    return RunContext({
        "run_id": "test_ax",
        "technique_id": "sarimax",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(values))),
        "series": series,
        "params": dict(params or {}),
    })


def _simulate_arma11(*, T=500, ar=0.7, ma=0.3, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = ar * y[t - 1] + eps[t] + ma * eps[t - 1]
    return y.tolist()


def canonical_1():
    print("\n=== canonical_1: SARIMAX(1,0,1) recovery T=500 ===")
    y = _simulate_arma11(T=500, seed=42)
    ctx = _build_ctx(y, params={"order": [1, 0, 1]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  AIC={a.get('aic')}")
    return True


def canonical_2():
    print("\n=== canonical_2: SARIMAX with exogenous regressor ===")
    y = _simulate_arma11(T=300, seed=43)
    rng = np.random.default_rng(44)
    x = rng.standard_normal(300)
    ctx = _build_ctx(y, params={"order": [1, 0, 1]},
                      series_extra=[("x_exog", x)])
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  AIC={a.get('aic')}")
    return True


def canonical_3():
    print("\n=== canonical_3: Real DGS10 yield level smoke ===")
    fixture = os.path.join(
        _ROOT, "tools", "calibration_audit", "fixtures",
        "macro_canonical_series.npz",
    )
    if not os.path.exists(fixture):
        print("  SKIP")
        return True
    data = np.load(fixture)
    y = data["DGS10"][~np.isnan(data["DGS10"])][-500:].tolist()
    ctx = _build_ctx(y, params={"order": [1, 1, 1]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  AIC={a.get('aic')}")
    return True


def canonical_4():
    print("\n=== canonical_4: Trend variants {n, c, t, ct} ===")
    y = _simulate_arma11(T=300, seed=45)
    for trend in ["n", "c", "t", "ct"]:
        ctx = _build_ctx(y, params={"order": [1, 0, 1], "trend": trend})
        res = ax_mod.run(ctx, _null_progress)
        if res.get("status") != "success":
            print(f"  FAIL trend={trend}")
            return False
        a = res.get("audit_fields") or {}
        print(f"  trend={trend!r}: AIC={a.get('aic')}")
    return True


def canonical_5():
    print("\n=== canonical_5: Invalid trend rejected ===")
    y = _simulate_arma11(T=200, seed=46)
    ctx = _build_ctx(y, params={"order": [1, 0, 1], "trend": "zzz"})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "failure":
        print(f"  FAIL: status={res.get('status')} (expect failure)")
        return False
    print(f"  PASS rejected: {res.get('error_message')!s:.80s}")
    return True


def canonical_6():
    print("\n=== C-CAL-1 (canonical_6): Constant series y=5.0 ===")
    y = [5.0] * 200
    ctx = _build_ctx(y, params={"order": [1, 0, 1]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    print(f"  PASS constant series handled")
    return True


def canonical_7():
    print("\n=== C-CAL-2 (canonical_7): Random walk + ARIMA(0,1,0) ===")
    rng = np.random.default_rng(47)
    y = np.cumsum(rng.standard_normal(300)).tolist()
    ctx = _build_ctx(y, params={"order": [0, 1, 0]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields") or {}
    print(f"  AIC={a.get('aic')}")
    return True


def canonical_8():
    print("\n=== C-CAL-3 (canonical_8): Short series T=30 ===")
    y = _simulate_arma11(T=30, seed=48)
    ctx = _build_ctx(y, params={"order": [1, 0, 1]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        return False
    print(f"  status={res.get('status')}")
    return True


def canonical_9():
    print("\n=== C-CAL-4 (canonical_9): Seasonal SARIMAX(1,0,1)(1,1,1)_12 ===")
    rng = np.random.default_rng(49)
    t = np.arange(400)
    y = (2.0 * np.sin(2 * np.pi * t / 12)
         + 0.5 * rng.standard_normal(400)).tolist()
    ctx = _build_ctx(y, params={"order": [1, 0, 1],
                                 "seasonal_order": [1, 1, 1, 12]})
    res = ax_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields") or {}
    print(f"  AIC={a.get('aic')}")
    return True


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3, canonical_4,
               canonical_5, canonical_6, canonical_7, canonical_8,
               canonical_9):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            ok = False
        results.append((fn.__name__, ok))
    print("\nCANONICAL VALIDATION SUMMARY")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
