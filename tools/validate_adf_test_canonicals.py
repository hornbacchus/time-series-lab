"""Phase 5 canonical validation for adf_test.

Created by CAI Phase 2 Session 17. 6 canonicals.
canonical_5 verifies Session 17 fixes (F-ST-ADF-REGRESSION,
F-ST-ADF-AUTOLAG).
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
from techniques import adf_test as adf_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, run_id="udf_test"):
    return RunContext({
        "run_id": run_id, "technique_id": "adf_test",
        "preset": "Balanced", "seed": 42, "frequency": "D",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _ar1(T=200, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def canonical_1():
    print("\n=== c1: adf baseline stationary AR(1) (single test) ===")
    res = adf_mod.run(_build_ctx(_ar1()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: adf regression variants {c, ct, ctt, n} ===")
    y = _ar1(seed=43)
    for reg in ("c", "ct", "ctt", "n"):
        res = adf_mod.run(_build_ctx(y, params={"regression": reg}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: adf autolag variants {AIC, BIC, t-stat} ===")
    y = _ar1(seed=44)
    for al in ("AIC", "BIC", "t-stat"):
        res = adf_mod.run(_build_ctx(y, params={"autolag": al}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: adf triage mode (default for non-udf run_id) ===")
    res = adf_mod.run(_build_ctx(_ar1(seed=45), run_id="ribbon_run"), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"].get("mode") == "triage"


def canonical_5():
    """Session 17 fix verification (F-ST-ADF-REGRESSION + F-ST-ADF-AUTOLAG)."""
    print("\n=== c5: adf invalid regression / autolag rejected (S17 fix) ===")
    # Invalid regression
    res = adf_mod.run(_build_ctx(
        _ar1(seed=46), params={"regression": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown regression" not in (res.get("error_message") or ""): return False
    # Invalid autolag
    res = adf_mod.run(_build_ctx(
        _ar1(seed=46), params={"autolag": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown autolag" not in (res.get("error_message") or ""): return False
    print("  PASS: both invalid regression and autolag rejected")
    return True


def canonical_6():
    print("\n=== c6: adf short series T=20 ===")
    res = adf_mod.run(_build_ctx(_ar1(T=20, seed=47)), _null)
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
