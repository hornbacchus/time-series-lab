"""Phase 5 canonical validation for stl_decompose.

Created by CAI Phase 2 Session 16. 6 canonicals.
"""

import os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import stl_decompose as stl_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced", frequency="M"):
    return RunContext({
        "run_id": "test_stl", "technique_id": "stl_decompose",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _seasonal_data(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.02 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: stl baseline (period=12 monthly) ===")
    res = stl_mod.run(_build_ctx(_seasonal_data(), params={"period": 12}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: stl period sensitivity (12, 6, 4) ===")
    y = _seasonal_data(seed=43)
    for p in (12, 6, 4):
        res = stl_mod.run(_build_ctx(y, params={"period": p}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: stl robust toggle ===")
    y = _seasonal_data(seed=44)
    for r in (True, False):
        res = stl_mod.run(_build_ctx(y, params={"period": 12, "robust": r}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: stl frequency inference (M → period=12) ===")
    res = stl_mod.run(_build_ctx(_seasonal_data(seed=45), frequency="M"), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["period"] == 12


def canonical_5():
    print("\n=== c5: stl no period + no frequency → reject ===")
    rng = np.random.default_rng(46)
    res = stl_mod.run(_build_ctx(rng.standard_normal(100).tolist(),
                                  frequency=""), _null)
    return res.get("status") == "failure"


def canonical_6():
    print("\n=== c6: stl preset variation (Fast vs Thorough) ===")
    y = _seasonal_data(seed=47)
    for preset in ("Fast", "Balanced", "Thorough"):
        res = stl_mod.run(_build_ctx(y, preset=preset, params={"period": 12}), _null)
        if res.get("status") != "success": return False
    return True


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
        try: ok = fn()
        except Exception as e:
            print(f"  RAISED: {type(e).__name__}: {e}"); ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
