"""Phase 5 canonical validation for intermittent_demand.

Created from scratch by CAI Phase 2 Session 11.

Nine canonicals covering Croston / SBA / TSB methods.

Run from project root:
    python tools/validate_intermittent_demand_canonicals.py
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
from techniques import intermittent_demand as id_mod


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_id",
        "technique_id": "intermittent_demand",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "demand", "values": list(values)}],
        "params": dict(params or {}),
    })


def _simulate_intermittent(*, T=200, zero_density=0.7, seed=42):
    rng = np.random.default_rng(seed)
    is_zero = rng.random(T) < zero_density
    demand = rng.poisson(3.0, size=T) + 1
    demand = np.where(is_zero, 0, demand)
    return demand.astype(float).tolist()


def canonical_1():
    print("\n=== canonical_1: Croston on typical intermittent T=200 ===")
    y = _simulate_intermittent(T=200, zero_density=0.6, seed=42)
    ctx = _build_ctx(y, params={"method": "croston"})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    if str(a.get("best_method", "")).lower() != "croston":
        print(f"  FAIL best_method={a.get('best_method')}")
        return False
    print(f"  best_method={a.get('best_method')}, MSE={a.get('mse')}")
    return True


def canonical_2():
    print("\n=== canonical_2: SBA on intermittent ===")
    y = _simulate_intermittent(T=200, zero_density=0.6, seed=42)
    ctx = _build_ctx(y, params={"method": "sba"})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    if str(a.get("best_method", "")).lower() != "sba":
        return False
    print(f"  best_method={a.get('best_method')}")
    return True


def canonical_3():
    print("\n=== canonical_3: TSB on intermittent ===")
    y = _simulate_intermittent(T=200, zero_density=0.6, seed=42)
    ctx = _build_ctx(y, params={"method": "tsb"})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    if str(a.get("best_method", "")).lower() != "tsb":
        return False
    print(f"  best_method={a.get('best_method')}")
    return True


def canonical_4():
    print("\n=== canonical_4: Auto method selection (Balanced preset) ===")
    y = _simulate_intermittent(T=200, zero_density=0.6, seed=43)
    ctx = _build_ctx(y, params={})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  selected method={a.get('best_method')}, MSE={a.get('mse')}")
    return True


def canonical_5():
    print("\n=== canonical_5: Invalid method 'xxx' rejected ===")
    y = _simulate_intermittent(T=200, seed=44)
    ctx = _build_ctx(y, params={"method": "xxx"})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "failure":
        print(f"  FAIL status={res.get('status')} (expect failure)")
        return False
    print(f"  rejected: {res.get('error_message')!s:.80s}")
    return True


def canonical_6():
    print("\n=== C-CAL-1 (canonical_6): Low density (30% zeros) ===")
    y = _simulate_intermittent(T=200, zero_density=0.3, seed=45)
    ctx = _build_ctx(y, params={})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  best_method={a.get('best_method')}")
    return True


def canonical_7():
    print("\n=== C-CAL-2 (canonical_7): Sparse density (85% zeros) ===")
    y = _simulate_intermittent(T=200, zero_density=0.85, seed=46)
    ctx = _build_ctx(y, params={})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields") or {}
    print(f"  best_method={a.get('best_method')}")
    return True


def canonical_8():
    print("\n=== C-CAL-3 (canonical_8): All-zeros (degenerate) ===")
    y = [0.0] * 200
    ctx = _build_ctx(y, params={})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") != "failure":
        print(f"  FAIL: status={res.get('status')}; expect failure on all-zeros")
        return False
    print(f"  failure: {res.get('error_message')!s:.80s}")
    return True


def canonical_9():
    print("\n=== C-CAL-4 (canonical_9): Single-spike series ===")
    y = [0.0] * 200
    y[100] = 50.0  # single non-zero spike
    ctx = _build_ctx(y, params={})
    res = id_mod.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        return False
    print(f"  status={res.get('status')}")
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
