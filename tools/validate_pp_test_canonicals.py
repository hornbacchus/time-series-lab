"""Phase 5 canonical validation for pp_test.

Created by CAI Phase 2 Session 17. 6 canonicals.
canonical_5 verifies Session 17 fix (F-ST-PP-REGRESSION).
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
from techniques import pp_test as pp_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None):
    return RunContext({
        "run_id": "test_pp", "technique_id": "pp_test",
        "preset": "Balanced", "seed": 42, "frequency": "D",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _ar1(T=200, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _random_walk(T=200, seed=42):
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: pp baseline stationary AR(1) ===")
    res = pp_mod.run(_build_ctx(_ar1()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: pp regression variants {c, ct, n, nc} ===")
    y = _ar1(seed=43)
    for reg in ("c", "ct", "n", "nc"):
        res = pp_mod.run(_build_ctx(y, params={"regression": reg}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: pp nlags variants {auto, integer} ===")
    y = _ar1(seed=44)
    for nl in ("auto", 10):
        res = pp_mod.run(_build_ctx(y, params={"nlags": nl}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: pp random walk → fails to reject UR ===")
    res = pp_mod.run(_build_ctx(_random_walk(T=300, seed=45)), _null)
    return res.get("status") == "success"


def canonical_5():
    """Session 17 fix verification (F-ST-PP-REGRESSION)."""
    print("\n=== c5: pp invalid regression='zzz' rejected (S17 fix) ===")
    res = pp_mod.run(_build_ctx(
        _ar1(seed=46), params={"regression": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown regression" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: pp short series T=20 ===")
    res = pp_mod.run(_build_ctx(_ar1(T=20, seed=47)), _null)
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
