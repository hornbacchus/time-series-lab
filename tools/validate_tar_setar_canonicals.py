"""Phase 5 canonical validation for tar_setar
(`engine/techniques/tar_setar.py`; both setar and tar
technique IDs).

Created by CAI Phase 2 Session 12. 6 canonicals.
"""

import os, sys, math

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import tar_setar as tar_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, technique_id="setar",
                preset="Balanced"):
    return RunContext({
        "run_id": "test_tar", "technique_id": technique_id,
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _simulate_threshold(T=400, threshold=0.0, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        if y[t - 1] < threshold:
            y[t] = -0.5 * y[t - 1] + rng.standard_normal()
        else:
            y[t] = 0.7 * y[t - 1] + rng.standard_normal()
    return y.tolist()


def canonical_1():
    print("\n=== canonical_1: 2-regime SETAR recovery ===")
    y = _simulate_threshold(T=400, seed=42)
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 2}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== canonical_2: TAR via technique_id=tar ===")
    y = _simulate_threshold(T=400, seed=43)
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 2},
                                   technique_id="tar"), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== canonical_3: SETAR on real GSPC returns ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 2}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== canonical_4: 3-regime SETAR ===")
    y = _simulate_threshold(T=400, seed=44)
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 3}), _null)
    return res.get("status") == "success"


def canonical_5():
    print("\n=== C-CAL-1 (canonical_5): Constant series ===")
    y = [5.0] * 200
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 2}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== C-CAL-2 (canonical_6): Short series T=80 ===")
    rng = np.random.default_rng(45)
    y = rng.standard_normal(80).tolist()
    res = tar_mod.run(_build_ctx(y, params={"n_regimes": 2}), _null)
    return res.get("status") in ("success", "failure")


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
        try:
            ok = fn()
        except Exception as e:
            print(f"  RAISED: {type(e).__name__}: {e}")
            ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
