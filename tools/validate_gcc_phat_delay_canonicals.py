"""Phase 5 canonical validation for gcc_phat_delay.

Created by CAI Phase 2 Session 14. 6 canonicals.
canonical_5 verifies Session 14 fix (F-CL-GCC-WEIGHTING).
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
from techniques import gcc_phat_delay as gcc_mod


def _null(*a, **k): pass


def _build_ctx(x, y, *, params=None):
    return RunContext({
        "run_id": "test_gcc", "technique_id": "gcc_phat_delay",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(range(len(x))),
        "series": [{"name": "x", "values": list(x)},
                    {"name": "y", "values": list(y)}],
        "params": dict(params or {}),
    })


def _lagged(T=400, lag=5, seed=42):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(T)
    y = np.zeros(T); y[lag:] = x[:-lag] + 0.3 * rng.standard_normal(T-lag)
    return x.tolist(), y.tolist()


def canonical_1():
    print("\n=== c1: gcc baseline (phat) ===")
    x, y = _lagged()
    res = gcc_mod.run(_build_ctx(x, y, params={"max_lag": 20}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: gcc weighting variants {phat, scot, roth, unfiltered} ===")
    x, y = _lagged(seed=43)
    for w in ["phat", "scot", "roth", "unfiltered"]:
        res = gcc_mod.run(_build_ctx(x, y, params={"weighting": w,
                                                      "max_lag": 20}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: gcc real (DGS2, DGS10) ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f): return True
    data = np.load(f)
    x = np.diff(data["DGS2"][~np.isnan(data["DGS2"])])[-500:].tolist()
    y = np.diff(data["DGS10"][~np.isnan(data["DGS10"])])[-500:].tolist()
    n = min(len(x), len(y))
    res = gcc_mod.run(_build_ctx(x[-n:], y[-n:],
                                   params={"max_lag": 20}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: gcc independent series ===")
    rng = np.random.default_rng(44)
    res = gcc_mod.run(_build_ctx(rng.standard_normal(300).tolist(),
                                   rng.standard_normal(300).tolist(),
                                   params={"max_lag": 20}), _null)
    return res.get("status") == "success"


def canonical_5():
    """Session 14 fix verification (F-CL-GCC-WEIGHTING)."""
    print("\n=== c5: gcc invalid weighting='zzz' rejected (S14 fix) ===")
    x, y = _lagged(seed=45)
    res = gcc_mod.run(_build_ctx(x, y, params={"weighting": "zzz",
                                                  "max_lag": 20}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown weighting" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: gcc short series T=50 ===")
    rng = np.random.default_rng(46)
    res = gcc_mod.run(_build_ctx(rng.standard_normal(50).tolist(),
                                   rng.standard_normal(50).tolist(),
                                   params={"max_lag": 10}), _null)
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
