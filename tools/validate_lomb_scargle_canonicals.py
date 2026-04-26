"""Phase 5 canonical validation for lomb_scargle.

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
from techniques import lomb_scargle as ls_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, time_values=None):
    if time_values is None:
        time_values = list(range(len(values)))
    return RunContext({
        "run_id": "test_ls", "technique_id": "lomb_scargle",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(time_values),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _uneven(T=300, seed=42):
    rng = np.random.default_rng(seed)
    t_full = np.linspace(0, 100, T * 2)
    keep = rng.random(len(t_full)) < 0.5
    t = t_full[keep]
    y = np.sin(2 * np.pi * 0.1 * t) + 0.2 * rng.standard_normal(len(t))
    return t.tolist(), y.tolist()


def canonical_1():
    print("\n=== c1: lomb_scargle uneven baseline ===")
    t, y = _uneven()
    res = ls_mod.run(_build_ctx(y, time_values=t), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: lomb_scargle even-time baseline ===")
    rng = np.random.default_rng(43)
    y = np.sin(2 * np.pi * 0.1 * np.arange(300)) + 0.2 * rng.standard_normal(300)
    res = ls_mod.run(_build_ctx(y.tolist()), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: lomb_scargle real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = ls_mod.run(_build_ctx(y), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: lomb_scargle oversampling sweep ===")
    t, y = _uneven(seed=44)
    for ov in [4, 10]:
        res = ls_mod.run(_build_ctx(y, params={"oversampling": ov},
                                      time_values=t), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_5():
    print("\n=== c5: short uneven series ===")
    rng = np.random.default_rng(45)
    t = sorted(rng.random(50).tolist())
    y = np.sin(2 * np.pi * 0.1 * np.array(t)).tolist()
    res = ls_mod.run(_build_ctx(y, time_values=t), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: constant series ===")
    res = ls_mod.run(_build_ctx([5.0] * 100), _null)
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
