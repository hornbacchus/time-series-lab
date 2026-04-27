"""Phase 5 canonical validation for denton_chowlin_disaggregation.

Created by CAI Phase 2 Session 19. 6 canonicals.
canonical_5 verifies Session 19 fixes (F-MD-DENTON-METHOD,
F-MD-DENTON-CONVRATIO, F-MD-DENTON-RHO).
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
from techniques import denton_chowlin_disaggregation as dcd_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_dcd", "technique_id": "denton_chowlin_disaggregation",
        "preset": preset, "seed": 42, "frequency": "Q",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _quarterly(n=20, seed=42):
    rng = np.random.default_rng(seed)
    return (10.0 + np.cumsum(rng.standard_normal(n) * 0.5)).tolist()


def canonical_1():
    print("\n=== c1: dcd baseline chowlin Q→M ===")
    res = dcd_mod.run(_build_ctx(_quarterly(),
                                    params={"method": "chowlin", "conversion_ratio": 3}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: dcd method variants {denton, chowlin} ===")
    y = _quarterly(seed=43)
    for m in ("denton", "chowlin"):
        res = dcd_mod.run(_build_ctx(y, params={"method": m, "conversion_ratio": 3}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: dcd conversion_ratio variants {3, 4, 12} ===")
    y = _quarterly(seed=44)
    for cr in (3, 4, 12):
        res = dcd_mod.run(_build_ctx(y, params={"conversion_ratio": cr}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: dcd rho 'auto' vs explicit ===")
    y = _quarterly(seed=45)
    for r in ("auto", 0.3, 0.7):
        res = dcd_mod.run(_build_ctx(y, params={"method": "chowlin", "rho": r,
                                                   "conversion_ratio": 3}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    """Session 19 fix verification (F-MD-DENTON-METHOD/CONVRATIO/RHO)."""
    print("\n=== c5: dcd invalid params rejected (S19 fixes) ===")
    y = _quarterly(seed=46)
    # Invalid method
    res = dcd_mod.run(_build_ctx(y, params={"method": "zzz", "conversion_ratio": 3}), _null)
    if res.get("status") != "failure": return False
    if "Unknown method" not in (res.get("error_message") or ""): return False
    # Invalid conversion_ratio
    res = dcd_mod.run(_build_ctx(y, params={"conversion_ratio": 1}), _null)
    if res.get("status") != "failure": return False
    if "conversion_ratio" not in (res.get("error_message") or ""): return False
    # Invalid rho
    res = dcd_mod.run(_build_ctx(y, params={"method": "chowlin", "rho": 1.5,
                                                "conversion_ratio": 3}), _null)
    if res.get("status") != "failure": return False
    if "rho must be" not in (res.get("error_message") or ""): return False
    print("  PASS: all 3 invalid params rejected")
    return True


def canonical_6():
    print("\n=== c6: dcd short series n_low=4 (boundary) ===")
    res = dcd_mod.run(_build_ctx(_quarterly(n=4, seed=47),
                                    params={"conversion_ratio": 3}), _null)
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
