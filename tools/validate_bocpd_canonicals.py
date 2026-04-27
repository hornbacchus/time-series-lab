"""Phase 5 canonical validation for bocpd.

Created by CAI Phase 2 Session 15. 6 canonicals.
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
from techniques import bocpd as bocpd_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_bocpd", "technique_id": "bocpd",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _step_series(T=200, break_at=100, shift=2.5, seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[break_at:] += shift
    return y.tolist()


def canonical_1():
    print("\n=== c1: bocpd baseline (step DGP) ===")
    res = bocpd_mod.run(_build_ctx(_step_series()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: bocpd hazard_lambda sensitivity ===")
    y = _step_series(seed=43)
    for hl in (50, 200, 500):
        res = bocpd_mod.run(_build_ctx(y, params={"hazard_lambda": hl}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: bocpd threshold sensitivity ===")
    y = _step_series(seed=44)
    for thr in (0.3, 0.5, 0.8):
        res = bocpd_mod.run(_build_ctx(y, params={"threshold": thr}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: bocpd white noise (no spurious cps) ===")
    rng = np.random.default_rng(45)
    res = bocpd_mod.run(_build_ctx(rng.standard_normal(200).tolist()), _null)
    if res.get("status") != "success": return False
    n_cps = res["audit_fields"]["n_change_points"]
    print(f"  white noise n_cps={n_cps} (expect small)")
    return n_cps <= 5


def canonical_5():
    print("\n=== c5: bocpd short series T=30 ===")
    rng = np.random.default_rng(46)
    res = bocpd_mod.run(_build_ctx(rng.standard_normal(30).tolist()), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== c6: bocpd preset variation (Fast vs Thorough) ===")
    y = _step_series(seed=47)
    for preset in ("Fast", "Balanced", "Thorough"):
        res = bocpd_mod.run(_build_ctx(y, preset=preset), _null)
        if res.get("status") != "success": return False
    return True


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
