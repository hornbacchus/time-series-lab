"""Phase 5 canonical validation for local_linear_trend.

Created by CAI Phase 2 Session 18. 6 canonicals.
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
from techniques import local_linear_trend as llt_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_llt", "technique_id": "local_linear_trend",
        "preset": preset, "seed": 42, "frequency": "M",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _trending(T=120, slope=0.05, seed=42):
    rng = np.random.default_rng(seed)
    return (np.arange(T) * slope + 0.3 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: llt baseline trending ===")
    res = llt_mod.run(_build_ctx(_trending()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: llt horizon variation ===")
    y = _trending(seed=43)
    for h in (5, 10, 20):
        res = llt_mod.run(_build_ctx(y, params={"horizon": h}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: llt damped param accepted (no-op; honest disclosure D7) ===")
    y = _trending(seed=44)
    for d in (True, False):
        res = llt_mod.run(_build_ctx(y, params={"damped": d}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: llt preset variation ===")
    y = _trending(seed=45)
    for preset in ("Fast", "Balanced", "Thorough"):
        res = llt_mod.run(_build_ctx(y, preset=preset), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    print("\n=== c5: llt downward trend recovered ===")
    rng = np.random.default_rng(46)
    y = (np.arange(120) * (-0.1) + 0.3 * rng.standard_normal(120)).tolist()
    res = llt_mod.run(_build_ctx(y), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["trend_direction"] == "downward"


def canonical_6():
    print("\n=== c6: llt short series T=10 (boundary) ===")
    res = llt_mod.run(_build_ctx(_trending(T=10, seed=47)), _null)
    return res.get("status") in ("success", "failure")


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
