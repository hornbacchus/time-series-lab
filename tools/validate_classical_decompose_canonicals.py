"""Phase 5 canonical validation for classical_decompose.

Created by CAI Phase 2 Session 16. 6 canonicals.
canonical_5 verifies Session 16 fix (F-CD-CLASSIC-MODEL).
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
from techniques import classical_decompose as classic_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced", frequency="M"):
    return RunContext({
        "run_id": "test_classic", "technique_id": "classical_decompose",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _additive_data(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.02 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def _multiplicative_data(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    trend = 100 + 0.1 * t
    seasonal = 1.0 + 0.2 * np.sin(2 * np.pi * t / period)
    noise = 1.0 + 0.05 * rng.standard_normal(T)
    return (trend * seasonal * noise).tolist()


def canonical_1():
    print("\n=== c1: classic baseline additive ===")
    res = classic_mod.run(_build_ctx(_additive_data(),
                                       params={"period": 12}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: classic multiplicative on positive DGP ===")
    res = classic_mod.run(_build_ctx(_multiplicative_data(seed=43),
                                       params={"period": 12, "model": "multiplicative"}), _null)
    if res.get("status") != "success": return False
    return res["audit_fields"]["model_type"] == "multiplicative"


def canonical_3():
    print("\n=== c3: classic multiplicative on series with negatives → coerce to additive ===")
    rng = np.random.default_rng(44)
    y = (np.arange(120) * 0.1 - 10 + rng.standard_normal(120)).tolist()
    res = classic_mod.run(_build_ctx(y, params={"period": 12, "model": "multiplicative"}), _null)
    if res.get("status") != "success": return False
    # Auto-fallback to additive when negatives present
    return res["audit_fields"]["model_type"] == "additive"


def canonical_4():
    print("\n=== c4: classic two_sided toggle ===")
    y = _additive_data(seed=45)
    for ts in (True, False):
        res = classic_mod.run(_build_ctx(y, params={"period": 12, "two_sided": ts}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    """Session 16 fix verification (F-CD-CLASSIC-MODEL)."""
    print("\n=== c5: classic invalid model='zzz' rejected (S16 fix) ===")
    res = classic_mod.run(_build_ctx(_additive_data(seed=46),
                                       params={"period": 12, "model": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown model" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: classic short series < 2*period → reject ===")
    res = classic_mod.run(_build_ctx([1.0, 2.0, 3.0, 4.0, 5.0],
                                       params={"period": 12}), _null)
    return res.get("status") == "failure"


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
