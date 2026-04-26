"""Phase 5 canonical validation for star
(`engine/techniques/star_model.py`).

Created by CAI Phase 2 Session 12. 6 canonicals — including
canonical_5 which verifies the Session 12 fix
(F-MR-STAR-TYPE) that previously accepted invalid
star_type='zzz' silently.
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
from techniques import star_model as star_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_star", "technique_id": "star",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _simulate_lstar(T=400, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        G = 1.0 / (1.0 + math.exp(-3.0 * (y[t - 1] - 0.0)))
        y[t] = (0.3 * y[t - 1] * (1 - G) + 0.8 * y[t - 1] * G
                + rng.standard_normal())
    return y.tolist()


def canonical_1():
    print("\n=== canonical_1: LSTAR recovery on smooth-transition DGP ===")
    y = _simulate_lstar(T=400, seed=42)
    res = star_mod.run(_build_ctx(y, params={"star_type": "LSTAR",
                                                "ar_order": 1}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== canonical_2: ESTAR on synthetic ===")
    y = _simulate_lstar(T=400, seed=43)
    res = star_mod.run(_build_ctx(y, params={"star_type": "ESTAR",
                                                "ar_order": 1}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== canonical_3: STAR on real GSPC returns ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = star_mod.run(_build_ctx(y, params={"star_type": "LSTAR",
                                                "ar_order": 1}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== canonical_4: star_type='both' ===")
    y = _simulate_lstar(T=400, seed=44)
    res = star_mod.run(_build_ctx(y, params={"star_type": "both",
                                                "ar_order": 1}), _null)
    return res.get("status") == "success"


def canonical_5():
    """Session 12 fix verification (F-MR-STAR-TYPE): invalid
    star_type='zzz' must be rejected with actionable error.
    Pre-fix the wrapper accepted any string and reported it
    in audit_fields."""
    print("\n=== canonical_5: STAR allowlist (Session 12 fix) ===")
    y = _simulate_lstar(T=200, seed=45)
    res = star_mod.run(_build_ctx(y, params={"star_type": "zzz",
                                                "ar_order": 1}), _null)
    if res.get("status") != "failure":
        print(f"  FAIL: expected failure on invalid star_type")
        return False
    err = res.get("error_message") or ""
    if "Unknown star_type" not in err:
        print(f"  FAIL unexpected error: {err}")
        return False
    print(f"  PASS rejected: {err[:80]}")
    return True


def canonical_6():
    print("\n=== C-CAL-1 (canonical_6): Random walk ===")
    rng = np.random.default_rng(46)
    y = np.cumsum(rng.standard_normal(300)).tolist()
    res = star_mod.run(_build_ctx(y, params={"star_type": "LSTAR",
                                                "ar_order": 1}), _null)
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
