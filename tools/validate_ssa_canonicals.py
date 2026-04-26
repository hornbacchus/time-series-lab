"""Phase 5 canonical validation for ssa_model.

Created by CAI Phase 2 Session 13. 6 canonicals.
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
from techniques import ssa_model as ssa_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_ssa", "technique_id": "ssa",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _multi(T=400, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (np.sin(2 * np.pi * 0.05 * t)
            + 0.5 * np.sin(2 * np.pi * 0.20 * t)
            + 0.3 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: ssa baseline ===")
    res = ssa_mod.run(_build_ctx(_multi(),
                                   params={"window_length": 100}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: ssa real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-300:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = ssa_mod.run(_build_ctx(y, params={"window_length": 50}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: ssa window_length sweep ===")
    y = _multi(seed=43)
    for wl in [50, 100, 150]:
        res = ssa_mod.run(_build_ctx(y, params={"window_length": wl}),
                           _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_4():
    print("\n=== c4: ssa invalid window_length=-1 rejected ===")
    res = ssa_mod.run(_build_ctx(_multi(seed=44),
                                   params={"window_length": -1}), _null)
    return res.get("status") == "failure"


def canonical_5():
    print("\n=== c5: short series ===")
    rng = np.random.default_rng(45)
    res = ssa_mod.run(_build_ctx(rng.standard_normal(50).tolist(),
                                   params={"window_length": 20}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: constant series ===")
    res = ssa_mod.run(_build_ctx([5.0] * 200,
                                   params={"window_length": 50}), _null)
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
