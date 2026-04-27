"""Phase 5 canonical validation for pelt_change_points.

Created by CAI Phase 2 Session 15. 6 canonicals.
canonical_5 verifies Session 15 fix (F-CP-PELT-PENALTY).
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
from techniques import pelt_change_points as pelt_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_pelt", "technique_id": "pelt_change_points",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _three_seg(T=300, breaks=(100, 200), shifts=(2.0, -1.5), seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[breaks[0]:breaks[1]] += shifts[0]
    y[breaks[1]:] += shifts[1]
    return y.tolist()


def canonical_1():
    print("\n=== c1: pelt baseline (3-segment DGP) ===")
    res = pelt_mod.run(_build_ctx(_three_seg()), _null)
    if res.get("status") != "success": return False
    n_cps = res["audit_fields"]["n_change_points"]
    print(f"  detected {n_cps} change points (true=2)")
    return n_cps >= 1


def canonical_2():
    print("\n=== c2: pelt cost_model variants {l1, l2, rbf} ===")
    y = _three_seg(seed=43)
    for cm in ("l1", "l2", "rbf"):
        res = pelt_mod.run(_build_ctx(y, params={"model": cm}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: pelt penalty variants {bic, aic, mbic} ===")
    y = _three_seg(seed=44)
    for pen in ("bic", "aic", "mbic"):
        res = pelt_mod.run(_build_ctx(y, params={"penalty": pen}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: pelt fixed n_bkps via Binseg ===")
    res = pelt_mod.run(_build_ctx(
        _three_seg(seed=45),
        params={"n_bkps": 2}), _null)
    if res.get("status") != "success": return False
    n_cps = res["audit_fields"]["n_change_points"]
    return n_cps == 2


def canonical_5():
    """Session 15 fix verification (F-CP-PELT-PENALTY)."""
    print("\n=== c5: pelt invalid penalty='zzz' rejected (S15 fix) ===")
    res = pelt_mod.run(_build_ctx(
        _three_seg(seed=46),
        params={"penalty": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown penalty method" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: pelt short series T=20 (graceful) ===")
    rng = np.random.default_rng(47)
    res = pelt_mod.run(_build_ctx(rng.standard_normal(20).tolist()), _null)
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
