"""Phase 5 canonical validation for emd_hht.

Created by CAI Phase 2 Session 13. 6 canonicals.
canonical_4 verifies Session 13 fix (F-FD-EMD-METHOD).
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
from techniques import emd_hht as emd_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_emd", "technique_id": "emd_hht",
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
    print("\n=== c1: emd_hht baseline ===")
    res = emd_mod.run(_build_ctx(_multi()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: emd_hht real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-300:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = emd_mod.run(_build_ctx(y), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: emd_hht max_imfs sweep ===")
    y = _multi(seed=43)
    for n in [3, 5]:
        res = emd_mod.run(_build_ctx(y, params={"max_imfs": n}), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_4():
    """Session 13 fix verification (F-FD-EMD-METHOD)."""
    print("\n=== c4: emd_hht invalid method allowlist (S13 fix) ===")
    res = emd_mod.run(_build_ctx(_multi(seed=44),
                                   params={"method": "zzz"}), _null)
    if res.get("status") != "failure":
        print(f"  FAIL: expected failure")
        return False
    err = res.get("error_message") or ""
    if "Unknown method" not in err:
        return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_5():
    print("\n=== c5: short series ===")
    rng = np.random.default_rng(45)
    res = emd_mod.run(_build_ctx(rng.standard_normal(60).tolist()),
                       _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: constant series ===")
    res = emd_mod.run(_build_ctx([5.0] * 200), _null)
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
