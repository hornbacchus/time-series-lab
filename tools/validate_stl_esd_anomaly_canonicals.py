"""Phase 5 canonical validation for stl_esd_anomaly.

Created by CAI Phase 2 Session 15. 6 canonicals.
canonical_5 verifies Session 15 fix (F-CP-STL-DIRECTION).
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
from techniques import stl_esd_anomaly as stl_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced", frequency="daily"):
    return RunContext({
        "run_id": "test_stl", "technique_id": "stl_esd_anomaly",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _seasonal_with_anomalies(T=240, period=12, n_anom=3, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y = np.sin(2 * np.pi * t / period) + 0.3 * rng.standard_normal(T)
    anom_indices = rng.choice(T, size=n_anom, replace=False)
    y[anom_indices] += 4.0 * np.sign(rng.standard_normal(n_anom))
    return y.tolist(), anom_indices


def canonical_1():
    print("\n=== c1: stl_esd baseline (seasonal+anomaly DGP) ===")
    y, _ = _seasonal_with_anomalies()
    res = stl_mod.run(_build_ctx(y, params={"period": 12}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: stl_esd direction variants {both, upper, lower} ===")
    y, _ = _seasonal_with_anomalies(seed=43)
    for d in ("both", "upper", "lower"):
        res = stl_mod.run(_build_ctx(y, params={"period": 12, "direction": d}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: stl_esd alpha sensitivity ===")
    y, _ = _seasonal_with_anomalies(seed=44)
    for a in (0.01, 0.05, 0.10):
        res = stl_mod.run(_build_ctx(y, params={"period": 12, "alpha": a}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: stl_esd no period + no frequency → reject ===")
    rng = np.random.default_rng(45)
    res = stl_mod.run(_build_ctx(
        rng.standard_normal(100).tolist(), frequency=""), _null)
    return res.get("status") == "failure"


def canonical_5():
    """Session 15 fix verification (F-CP-STL-DIRECTION)."""
    print("\n=== c5: stl_esd invalid direction='zzz' rejected (S15 fix) ===")
    y, _ = _seasonal_with_anomalies(seed=46)
    res = stl_mod.run(_build_ctx(y, params={"period": 12, "direction": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown direction" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: stl_esd short series < 2*period+1 → reject ===")
    res = stl_mod.run(_build_ctx(
        [1.0, 2.0, 3.0, 4.0, 5.0],
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
