"""Phase 5 canonical validation for loess_interpolation.

Created by CAI Phase 2 Session 19. 6 canonicals.
canonical_5 verifies Session 19 fix (F-MD-LOESS-FRAC).
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
from techniques import loess_interpolation as loess_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_loess", "technique_id": "loess_interpolation",
        "preset": preset, "seed": 42, "frequency": "M",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _ar1_with_missing(T=100, phi=0.7, missing_frac=0.1, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    n_miss = int(T * missing_frac)
    miss_idx = rng.choice(T, size=n_miss, replace=False)
    y[miss_idx] = np.nan
    return y.tolist()


def canonical_1():
    print("\n=== c1: loess baseline (sparse missing) ===")
    res = loess_mod.run(_build_ctx(_ar1_with_missing()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: loess frac variants {0.1, 0.3, 0.5} ===")
    y = _ar1_with_missing(seed=43)
    for f in (0.1, 0.3, 0.5):
        res = loess_mod.run(_build_ctx(y, params={"frac": f}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: loess auto-frac via CV (Thorough preset) ===")
    y = _ar1_with_missing(seed=44)
    res = loess_mod.run(_build_ctx(y, preset="Thorough"), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: loess no missing → reject ===")
    rng = np.random.default_rng(45)
    res = loess_mod.run(_build_ctx(rng.standard_normal(100).tolist()), _null)
    return res.get("status") == "failure"


def canonical_5():
    """Session 19 fix verification (F-MD-LOESS-FRAC)."""
    print("\n=== c5: loess invalid frac rejected (S19 fix) ===")
    res = loess_mod.run(_build_ctx(_ar1_with_missing(seed=46),
                                       params={"frac": 1.5}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "LOESS fraction" not in err: return False
    # Also test frac<=0
    res = loess_mod.run(_build_ctx(_ar1_with_missing(seed=46),
                                       params={"frac": -0.1}), _null)
    if res.get("status") != "failure": return False
    print(f"  PASS: both out-of-range frac rejected")
    return True


def canonical_6():
    print("\n=== c6: loess block-missing (extrapolation tested) ===")
    rng = np.random.default_rng(47)
    y = rng.standard_normal(100)
    y[0] = np.nan; y[-1] = np.nan; y[40:50] = np.nan
    res = loess_mod.run(_build_ctx(y.tolist()), _null)
    return res.get("status") == "success"


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
