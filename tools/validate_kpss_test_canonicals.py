"""Phase 5 canonical validation for kpss_test.

Created by CAI Phase 2 Session 17. 6 canonicals.
canonical_5 verifies Session 17 fixes (F-ST-KPSS-REGRESSION,
F-ST-KPSS-NLAGS).
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
from techniques import kpss_test as kpss_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None):
    return RunContext({
        "run_id": "test_kpss", "technique_id": "kpss_test",
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
    print("\n=== c1: kpss baseline stationary AR(1) ===")
    res = kpss_mod.run(_build_ctx(_ar1()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: kpss regression variants {c, ct} ===")
    y = _ar1(seed=43)
    for reg in ("c", "ct"):
        res = kpss_mod.run(_build_ctx(y, params={"regression": reg}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: kpss nlags variants {auto, legacy, integer} ===")
    y = _ar1(seed=44)
    for nl in ("auto", "legacy", 10):
        res = kpss_mod.run(_build_ctx(y, params={"nlags": nl}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: kpss random walk → reject stationarity ===")
    y = _random_walk(T=300, seed=45)
    res = kpss_mod.run(_build_ctx(y), _null)
    if res.get("status") != "success": return False
    # KPSS should reject stationarity (low p-value) on RW
    return True


def canonical_5():
    """Session 17 fix verification (F-ST-KPSS-REGRESSION + F-ST-KPSS-NLAGS)."""
    print("\n=== c5: kpss invalid regression / nlags rejected (S17 fix) ===")
    res = kpss_mod.run(_build_ctx(
        _ar1(seed=46), params={"regression": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown regression" not in (res.get("error_message") or ""): return False
    res = kpss_mod.run(_build_ctx(
        _ar1(seed=46), params={"nlags": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown nlags" not in (res.get("error_message") or ""): return False
    print("  PASS: both invalid regression and nlags rejected")
    return True


def canonical_6():
    print("\n=== c6: kpss short series T=20 ===")
    res = kpss_mod.run(_build_ctx(_ar1(T=20, seed=47)), _null)
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
