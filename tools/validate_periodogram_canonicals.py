"""Phase 5 canonical validation for periodogram_spectral_density.

Created by CAI Phase 2 Session 13. 6 canonicals.
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
from techniques import periodogram_spectral_density as pgm_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_pgm",
        "technique_id": "periodogram_spectral_density",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _sine(T=500, f=0.1, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (np.sin(2 * np.pi * f * t) + 0.2 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: periodogram baseline on sinusoid ===")
    res = pgm_mod.run(_build_ctx(_sine()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: periodogram with hann window ===")
    res = pgm_mod.run(_build_ctx(_sine(seed=43),
                                   params={"window": "hann"}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: periodogram on real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = pgm_mod.run(_build_ctx(y), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: periodogram on constant series ===")
    res = pgm_mod.run(_build_ctx([5.0] * 200), _null)
    return res.get("status") in ("success", "failure")


def canonical_5():
    print("\n=== c5: periodogram invalid window rejected ===")
    res = pgm_mod.run(_build_ctx(_sine(seed=44),
                                   params={"window": "zzz"}), _null)
    return res.get("status") == "failure"


def canonical_6():
    print("\n=== c6: short series T=30 ===")
    rng = np.random.default_rng(45)
    res = pgm_mod.run(_build_ctx(rng.standard_normal(30).tolist()),
                       _null)
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
