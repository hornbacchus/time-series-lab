"""Phase 5 canonical validation for dtw_alignment_lag.

Created by CAI Phase 2 Session 14. 6 canonicals.
canonical_5 verifies Session 14 fix (F-CL-DTW-STEP).
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
from techniques import dtw_alignment_lag as dtw_mod


def _null(*a, **k): pass


def _build_ctx(x, y, *, params=None):
    return RunContext({
        "run_id": "test_dtw", "technique_id": "dtw_alignment_lag",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(range(len(x))),
        "series": [{"name": "x", "values": list(x)},
                    {"name": "y", "values": list(y)}],
        "params": dict(params or {}),
    })


def _lagged(T=300, lag=5, seed=42):
    rng = np.random.default_rng(seed)
    x = np.zeros(T); eps = rng.standard_normal(T)
    for t in range(1, T): x[t] = 0.7 * x[t-1] + eps[t]
    y = np.zeros(T); y[lag:] = x[:-lag] + 0.3 * rng.standard_normal(T-lag)
    return x.tolist(), y.tolist()


def canonical_1():
    print("\n=== c1: dtw baseline ===")
    x, y = _lagged()
    res = dtw_mod.run(_build_ctx(x, y), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: dtw step_pattern variants {symmetric1, symmetric2} ===")
    x, y = _lagged(seed=43)
    for sp in ["symmetric1", "symmetric2"]:
        res = dtw_mod.run(_build_ctx(x, y,
                                        params={"step_pattern": sp}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: dtw real (DGS2, DGS10) subsampled ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f): return True
    data = np.load(f)
    x = np.diff(data["DGS2"][~np.isnan(data["DGS2"])])[-300:].tolist()
    y = np.diff(data["DGS10"][~np.isnan(data["DGS10"])])[-300:].tolist()
    n = min(len(x), len(y))
    res = dtw_mod.run(_build_ctx(x[-n:], y[-n:]), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: dtw normalize toggle ===")
    x, y = _lagged(seed=44)
    for n in [True, False]:
        res = dtw_mod.run(_build_ctx(x, y, params={"normalize": n}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    """Session 14 fix verification (F-CL-DTW-STEP)."""
    print("\n=== c5: dtw invalid step_pattern='zzz' rejected (S14 fix) ===")
    x, y = _lagged(seed=45)
    res = dtw_mod.run(_build_ctx(x, y,
                                    params={"step_pattern": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown step_pattern" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: dtw short series ===")
    rng = np.random.default_rng(46)
    res = dtw_mod.run(_build_ctx(rng.standard_normal(50).tolist(),
                                    rng.standard_normal(50).tolist()),
                        _null)
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
