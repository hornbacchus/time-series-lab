"""Phase 5 canonical validation for theta_forecast.

Created from scratch by CAI Phase 2 Session 11.

Nine canonicals.

Run from project root:
    python tools/validate_theta_forecast_canonicals.py
"""

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
from techniques import theta_forecast as th_mod


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(values, *, params=None, preset="Balanced",
                frequency="daily"):
    return RunContext({
        "run_id": "test_theta",
        "technique_id": "theta_forecast",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _simulate_arma11(*, T=300, ar=0.7, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = ar * y[t - 1] + eps[t]
    return y.tolist()


def canonical_1():
    print("\n=== canonical_1: Theta on synthetic AR(1) T=300 ===")
    y = _simulate_arma11(T=300, seed=42)
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    print(f"  status=success")
    return True


def canonical_2():
    print("\n=== canonical_2: Real GSPC log returns ===")
    fixture = os.path.join(
        _ROOT, "tools", "calibration_audit", "fixtures",
        "macro_canonical_series.npz",
    )
    if not os.path.exists(fixture):
        print("  SKIP")
        return True
    data = np.load(fixture)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-300:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    print(f"  status=success")
    return True


def canonical_3():
    print("\n=== canonical_3: Horizon=22 (longer-range) ===")
    y = _simulate_arma11(T=300, seed=43)
    ctx = _build_ctx(y, params={"horizon": 22})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    print(f"  status=success at horizon=22")
    return True


def canonical_4():
    print("\n=== canonical_4: deseasonalize=False (toggle) ===")
    y = _simulate_arma11(T=300, seed=44)
    ctx = _build_ctx(y, params={"deseasonalize": False})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    return True


def canonical_5():
    print("\n=== canonical_5: Series too short for deseasonalize ===")
    y = _simulate_arma11(T=20, seed=45)
    ctx = _build_ctx(y, params={"deseasonalize": True}, frequency="daily")
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        return False
    print(f"  status={res.get('status')}")
    return True


def canonical_6():
    print("\n=== C-CAL-1 (canonical_6): Constant series ===")
    y = [5.0] * 100
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        return False
    print(f"  status={res.get('status')}")
    return True


def canonical_7():
    print("\n=== C-CAL-2 (canonical_7): Pure white noise ===")
    rng = np.random.default_rng(46)
    y = rng.standard_normal(200).tolist()
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    return True


def canonical_8():
    print("\n=== C-CAL-3 (canonical_8): Short series T=10 ===")
    y = _simulate_arma11(T=10, seed=47)
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        return False
    print(f"  status={res.get('status')}")
    return True


def canonical_9():
    print("\n=== C-CAL-4 (canonical_9): Strong trend ===")
    rng = np.random.default_rng(48)
    t = np.arange(200)
    y = (0.05 * t + rng.standard_normal(200)).tolist()
    ctx = _build_ctx(y, params={})
    res = th_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
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
