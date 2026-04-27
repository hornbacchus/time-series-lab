"""Phase 5 canonical validation for particle_filter.

Created by CAI Phase 2 Session 18. 6 canonicals.
canonical_5 verifies Session 18 fix (F-SS-PF-MODEL).
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
from techniques import particle_filter as pf_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Fast"):
    # Use Fast preset for speed in canonicals
    p = {"n_particles": 200}
    p.update(params or {})
    return RunContext({
        "run_id": "test_pf", "technique_id": "particle_filter",
        "preset": preset, "seed": 42, "frequency": "M",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": p,
    })


def _ar1(T=100, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def canonical_1():
    print("\n=== c1: pf baseline local_level ===")
    res = pf_mod.run(_build_ctx(_ar1()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: pf model variants {local_level, local_level_sv, nonlinear_growth, random_walk_sv} ===")
    y = _ar1(seed=43)
    for m in ("local_level", "local_level_sv", "nonlinear_growth", "random_walk_sv"):
        res = pf_mod.run(_build_ctx(y, params={"model": m}), _null)
        if res.get("status") != "success":
            print(f"    {m!r}: FAIL {(res.get('error_message') or '')[:60]}")
            return False
    return True


def canonical_3():
    print("\n=== c3: pf particle count sensitivity ===")
    y = _ar1(seed=44)
    for n_p in (100, 500, 1000):
        res = pf_mod.run(_build_ctx(y, params={"n_particles": n_p}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: pf with NaN observations (skip-update path) ===")
    rng = np.random.default_rng(45)
    y = rng.standard_normal(80)
    y[20:25] = np.nan
    y[50:52] = np.nan
    res = pf_mod.run(_build_ctx(y.tolist()), _null)
    return res.get("status") == "success"


def canonical_5():
    """Session 18 fix verification (F-SS-PF-MODEL)."""
    print("\n=== c5: pf invalid model='zzz' rejected (S18 fix) ===")
    res = pf_mod.run(_build_ctx(_ar1(seed=46),
                                  params={"model": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown model" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: pf short series T=8 (boundary) ===")
    res = pf_mod.run(_build_ctx(_ar1(T=8, seed=47)), _null)
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
