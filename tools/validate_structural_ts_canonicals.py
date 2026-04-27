"""Phase 5 canonical validation for structural_ts.

Created by CAI Phase 2 Session 18. 6 canonicals.
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
from techniques import structural_ts as sts_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced", frequency="M"):
    return RunContext({
        "run_id": "test_sts", "technique_id": "structural_ts",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _seasonal(T=120, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: sts baseline (default level=local linear trend) ===")
    res = sts_mod.run(_build_ctx(_seasonal()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: sts level variants {local level, local linear trend, smooth trend} ===")
    y = _seasonal(seed=43)
    for lt in ("local level", "local linear trend", "smooth trend"):
        res = sts_mod.run(_build_ctx(y, params={"level": lt, "seasonal": 12}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: sts seasonal=12 with explicit period ===")
    y = _seasonal(seed=44)
    res = sts_mod.run(_build_ctx(y, params={"seasonal": 12}), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["seasonal_period"] == 12


def canonical_4():
    print("\n=== c4: sts AR component ===")
    y = _seasonal(seed=45)
    res = sts_mod.run(_build_ctx(y, params={"autoregressive": 2}), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["ar_order"] == 2


def canonical_5():
    print("\n=== c5: sts invalid level rejected (upstream UnobservedComponents) ===")
    res = sts_mod.run(_build_ctx(_seasonal(seed=46),
                                    params={"level": "zzz_invalid"}), _null)
    if res.get("status") != "failure": return False
    err = (res.get("error_message") or "").lower()
    if "level" not in err and "specification" not in err: return False
    print(f"  PASS: {(res.get('error_message') or '')[:80]}")
    return True


def canonical_6():
    print("\n=== c6: sts short series T=10 (boundary) ===")
    res = sts_mod.run(_build_ctx(_seasonal(T=10, seed=47)), _null)
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
