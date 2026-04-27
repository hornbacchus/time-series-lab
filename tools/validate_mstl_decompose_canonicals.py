"""Phase 5 canonical validation for mstl_decompose.

Created by CAI Phase 2 Session 16. 6 canonicals.
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
from techniques import mstl_decompose as mstl_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced", frequency="D"):
    return RunContext({
        "run_id": "test_mstl", "technique_id": "mstl_decompose",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _multi_seasonal(T=730, periods=(7, 365), amps=(1.0, 3.0), seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y = 0.3 * rng.standard_normal(T)
    for p, a in zip(periods, amps):
        y += a * np.sin(2 * np.pi * t / p)
    return y.tolist()


def canonical_1():
    print("\n=== c1: mstl baseline (periods=[7, 365] daily) ===")
    res = mstl_mod.run(_build_ctx(_multi_seasonal(),
                                    params={"periods": [7, 365]}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: mstl single period ===")
    res = mstl_mod.run(_build_ctx(_multi_seasonal(seed=43),
                                    params={"periods": [12]}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: mstl frequency inference (D → [7, 365]) ===")
    res = mstl_mod.run(_build_ctx(_multi_seasonal(seed=44), frequency="D"), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["periods"] == [7, 365]


def canonical_4():
    print("\n=== c4: mstl too-short for any period → reject ===")
    rng = np.random.default_rng(45)
    res = mstl_mod.run(_build_ctx(rng.standard_normal(20).tolist(),
                                    params={"periods": [365]}), _null)
    return res.get("status") == "failure"


def canonical_5():
    print("\n=== c5: mstl drops too-large periods, keeps usable ones ===")
    res = mstl_mod.run(_build_ctx(_multi_seasonal(T=200, periods=(7,), amps=(1.0,), seed=46),
                                    params={"periods": [7, 365]}), _null)
    if res.get("status") != "success": return False
    # Should have dropped 365, kept 7
    return res["audit_fields"]["periods"] == [7]


def canonical_6():
    print("\n=== c6: mstl preset variation ===")
    y = _multi_seasonal(seed=47)
    for preset in ("Fast", "Balanced", "Thorough"):
        res = mstl_mod.run(_build_ctx(y, preset=preset,
                                         params={"periods": [7, 365]}), _null)
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
