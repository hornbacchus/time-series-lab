"""Phase 5 canonical validation for cusum_page_hinkley.

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
from techniques import cusum_page_hinkley as cph_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_cph", "technique_id": "cusum_page_hinkley",
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
    print("\n=== c1: cph baseline (step DGP) ===")
    res = cph_mod.run(_build_ctx(_step_series()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: cph cusum_h sensitivity ===")
    y = _step_series(seed=43)
    sigma = float(np.std(y, ddof=1))
    for h_mult in (3.0, 5.0, 8.0):
        res = cph_mod.run(_build_ctx(y, params={"cusum_h": h_mult * sigma}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: cph ph_lambda sensitivity ===")
    y = _step_series(seed=44)
    for pl in (10, 50, 100):
        res = cph_mod.run(_build_ctx(y, params={"ph_lambda": pl}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: cph white noise ===")
    rng = np.random.default_rng(45)
    res = cph_mod.run(_build_ctx(rng.standard_normal(300).tolist()), _null)
    return res.get("status") == "success"


def canonical_5():
    print("\n=== c5: cph constant series → reject (zero variance) ===")
    res = cph_mod.run(_build_ctx([1.0] * 50), _null)
    if res.get("status") != "failure": return False
    if "near-zero variance" not in (res.get("error_message") or ""):
        return False
    return True


def canonical_6():
    print("\n=== c6: cph short series T=30 ===")
    rng = np.random.default_rng(46)
    res = cph_mod.run(_build_ctx(rng.standard_normal(30).tolist()), _null)
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
