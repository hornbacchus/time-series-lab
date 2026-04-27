"""Phase 5 canonical validation for x13_seasonal_adjust.

Created by CAI Phase 2 Session 16. 6 canonicals.
canonical_5 verifies Session 16 fix (F-CD-X13-TRANSFORM).

Note: requires X-13 binary in resources/x13/. If unavailable,
canonicals using the binary may fall through to statsmodels
wrapper or fail; validation logic (c5) tests pre-binary input
gating and works regardless.
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
from techniques import x13_seasonal_adjust as x13_mod


def _null(*a, **k): pass


def _monthly_time(T, start_year=2000):
    out = []
    y, m = start_year, 1
    for _ in range(T):
        out.append(f"{y}-{m:02d}-01")
        m += 1
        if m > 12:
            m = 1; y += 1
    return out


def _build_ctx(values, *, params=None, preset="Balanced", frequency="M"):
    return RunContext({
        "run_id": "test_x13", "technique_id": "x13_seasonal_adjust",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": _monthly_time(len(values)),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _multiplicative_data(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    trend = 100 + 0.1 * t
    seasonal = 1.0 + 0.2 * np.sin(2 * np.pi * t / period)
    noise = 1.0 + 0.05 * rng.standard_normal(T)
    return (trend * seasonal * noise).tolist()


def canonical_1():
    print("\n=== c1: x13 baseline monthly (auto transform) ===")
    res = x13_mod.run(_build_ctx(_multiplicative_data()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: x13 transform variants {auto, log, none} ===")
    y = _multiplicative_data(seed=43)
    for tr in ("auto", "log", "none"):
        res = x13_mod.run(_build_ctx(y, params={"transform": tr}), _null)
        if res.get("status") != "success":
            print(f"    transform={tr!r} FAIL: {(res.get('error_message') or '')[:80]}")
            return False
    return True


def canonical_3():
    print("\n=== c3: x13 outlier detection toggle ===")
    y = _multiplicative_data(seed=44)
    for o in (True, False):
        res = x13_mod.run(_build_ctx(y, params={"outlier": o}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: x13 quarterly data (period=4) ===")
    rng = np.random.default_rng(45)
    t = np.arange(80)
    y = (100 + 0.5 * t + 5.0 * np.sin(2 * np.pi * t / 4)
         + 1.0 * rng.standard_normal(80)).tolist()
    ctx = RunContext({
        "run_id": "test_x13_q", "technique_id": "x13_seasonal_adjust",
        "preset": "Balanced", "seed": 42, "frequency": "Q",
        "time": [f"{2000+i//4}-Q{(i%4)+1}" for i in range(80)],
        "series": [{"name": "y", "values": y}],
        "params": {"period": 4},
    })
    res = x13_mod.run(ctx, _null)
    if res.get("status") != "success":
        print(f"    FAIL: {(res.get('error_message') or '')[:120]}")
        return False
    return True


def canonical_5():
    """Session 16 fix verification (F-CD-X13-TRANSFORM)."""
    print("\n=== c5: x13 invalid transform='zzz' rejected (S16 fix) ===")
    res = x13_mod.run(_build_ctx(_multiplicative_data(seed=46),
                                   params={"transform": "zzz"}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown transform" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: x13 unsupported period (period=7) → reject ===")
    res = x13_mod.run(_build_ctx(_multiplicative_data(T=120, period=7, seed=47),
                                   params={"period": 7}), _null)
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
