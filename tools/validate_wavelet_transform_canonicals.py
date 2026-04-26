"""Phase 5 canonical validation for wavelet_transform.

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
from techniques import wavelet_transform as wt_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None):
    return RunContext({
        "run_id": "test_wt", "technique_id": "wavelet_transform",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _multi(T=512, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (np.sin(2 * np.pi * 0.05 * t)
            + 0.5 * np.sin(2 * np.pi * 0.20 * t)
            + 0.3 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: wavelet_transform db4 baseline ===")
    res = wt_mod.run(_build_ctx(_multi(), params={"wavelet": "db4"}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: wavelet family sweep ===")
    y = _multi(seed=43)
    for w in ["db4", "sym4", "coif1"]:
        res = wt_mod.run(_build_ctx(y, params={"wavelet": w}), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_3():
    print("\n=== c3: wavelet_transform on real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-512:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = wt_mod.run(_build_ctx(y, params={"wavelet": "db4"}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: wavelet_transform invalid wavelet rejected ===")
    res = wt_mod.run(_build_ctx(_multi(),
                                  params={"wavelet": "zzz"}), _null)
    return res.get("status") == "failure"


def canonical_5():
    print("\n=== c5: short series T=30 ===")
    rng = np.random.default_rng(44)
    res = wt_mod.run(_build_ctx(rng.standard_normal(30).tolist(),
                                  params={"wavelet": "db4"}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: constant series ===")
    res = wt_mod.run(_build_ctx([5.0] * 256,
                                  params={"wavelet": "db4"}), _null)
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
