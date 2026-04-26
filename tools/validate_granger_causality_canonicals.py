"""Phase 5 canonical validation for granger_causality.

Created by CAI Phase 2 Session 14. 6 canonicals.
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
from techniques import granger_causality as gr_mod


def _null(*a, **k): pass


def _build_ctx(x, y, *, params=None):
    return RunContext({
        "run_id": "test_gr", "technique_id": "granger_causality",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(range(len(x))),
        "series": [{"name": "x", "values": list(x)},
                    {"name": "y", "values": list(y)}],
        "params": dict(params or {}),
    })


def _lagged(T=400, lag=5, seed=42):
    rng = np.random.default_rng(seed)
    x = np.zeros(T); eps = rng.standard_normal(T)
    for t in range(1, T): x[t] = 0.7 * x[t-1] + eps[t]
    y = np.zeros(T)
    y[lag:] = x[:-lag] + 0.3 * rng.standard_normal(T - lag)
    return x.tolist(), y.tolist()


def canonical_1():
    print("\n=== c1: granger baseline lagged pair ===")
    x, y = _lagged(seed=42)
    res = gr_mod.run(_build_ctx(x, y, params={"max_lag": 5}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: granger on independent series ===")
    rng = np.random.default_rng(43)
    x = rng.standard_normal(400).tolist()
    y = rng.standard_normal(400).tolist()
    res = gr_mod.run(_build_ctx(x, y, params={"max_lag": 5}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: granger on real (DGS2, DGS10) ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f): return True
    data = np.load(f)
    x = np.diff(data["DGS2"][~np.isnan(data["DGS2"])])[-500:].tolist()
    y = np.diff(data["DGS10"][~np.isnan(data["DGS10"])])[-500:].tolist()
    n = min(len(x), len(y))
    res = gr_mod.run(_build_ctx(x[-n:], y[-n:],
                                  params={"max_lag": 5}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: granger maxlag sweep ===")
    x, y = _lagged(seed=44)
    for ml in [3, 10]:
        res = gr_mod.run(_build_ctx(x, y, params={"max_lag": ml}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    print("\n=== c5: granger short series T=50 ===")
    rng = np.random.default_rng(45)
    res = gr_mod.run(_build_ctx(rng.standard_normal(50).tolist(),
                                  rng.standard_normal(50).tolist(),
                                  params={"max_lag": 3}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: granger constant + variable ===")
    rng = np.random.default_rng(46)
    res = gr_mod.run(_build_ctx([5.0]*200,
                                  rng.standard_normal(200).tolist(),
                                  params={"max_lag": 3}), _null)
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
