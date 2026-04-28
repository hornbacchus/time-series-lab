"""Phase 5 canonical validation for ets_hw. Session 27. 9 canonicals (5 base + 4 C-CAL).

FINAL session of CAI extension cycle.
"""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import ets_hw as ets_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_ets", "technique_id": "ets_hw",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _trend_seasonal(T=120, period=12, slope=0.05, amp=2.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (10 + slope * t + amp * np.sin(2*np.pi*t/period)
            + 0.3 * rng.standard_normal(T)).tolist()

def c1():
    """Known additive trend recovery."""
    print("\n=== c1: ets_hw additive trend recovery ===")
    rng = np.random.default_rng(42)
    y = (10 + 0.05 * np.arange(120) + 0.3 * rng.standard_normal(120)).tolist()
    r = ets_mod.run(_ctx(y, trend="add", seasonal=None), _null)
    return r.get("status") == "success"

def c2():
    """Known multiplicative seasonality recovery."""
    print("\n=== c2: ets_hw multiplicative seasonality recovery ===")
    rng = np.random.default_rng(43)
    t = np.arange(120)
    y = (100 * (1 + 0.2 * np.sin(2*np.pi*t/12)) + 1.0 * rng.standard_normal(120)).tolist()
    r = ets_mod.run(_ctx(y, seasonal="mul"), _null)
    return r.get("status") == "success"

def c3():
    """White noise."""
    print("\n=== c3: ets_hw white noise ===")
    rng = np.random.default_rng(44)
    y = rng.standard_normal(120).tolist()
    r = ets_mod.run(_ctx(y), _null)
    return r.get("status") == "success"

def c4():
    """Damped trend recovery."""
    print("\n=== c4: ets_hw damped trend variants ===")
    rng = np.random.default_rng(45)
    y = (10 + 0.1 * np.arange(120) + 0.2 * rng.standard_normal(120)).tolist()
    for d in (True, False):
        r = ets_mod.run(_ctx(y, trend="add", damped_trend=d, seasonal=None), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """Real series smoke test (synthetic seasonal)."""
    print("\n=== c5: ets_hw seasonal+trend combined ===")
    y = _trend_seasonal(seed=46)
    r = ets_mod.run(_ctx(y, trend="add", seasonal="add"), _null)
    return r.get("status") == "success"

def c6():
    """C-CAL-1: constant series."""
    print("\n=== c6: ets_hw constant series (graceful) ===")
    r = ets_mod.run(_ctx([5.0] * 100), _null)
    return r.get("status") in ("success", "failure")

def c7():
    """C-CAL-2 / S27 fix verification: multiplicative + non-positive rejected."""
    print("\n=== c7: ets_hw mul + negative rejected (S27 fix) ===")
    y = (np.array(_trend_seasonal(seed=47)) - 12).tolist()  # introduce negatives
    r = ets_mod.run(_ctx(y, seasonal="mul"), _null)
    if r.get("status") != "failure": return False
    if "positive" not in (r.get("error_message") or "").lower(): return False
    r = ets_mod.run(_ctx(y, trend="mul"), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c8():
    """C-CAL-3: short series + seasonal_periods=12 (graceful)."""
    print("\n=== c8: ets_hw short series T=12 seasonal_periods=12 ===")
    y = _trend_seasonal(T=12, seed=48)
    r = ets_mod.run(_ctx(y, seasonal="add"), _null)
    return r.get("status") in ("success", "failure")

def c9():
    """C-CAL-4 / S27 fix verification: invalid string + multi-param consistency."""
    print("\n=== c9: ets_hw invalid params rejected (S27 fix) ===")
    y = _trend_seasonal(seed=49)
    r = ets_mod.run(_ctx(y, trend="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown trend" not in (r.get("error_message") or ""): return False
    r = ets_mod.run(_ctx(y, seasonal="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown seasonal" not in (r.get("error_message") or ""): return False
    r = ets_mod.run(_ctx(y, trend=None, damped_trend=True), _null)
    if r.get("status") != "failure": return False
    if "damped_trend" not in (r.get("error_message") or ""): return False
    r = ets_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    print("  PASS: 4 invalid configs rejected")
    return True

def main():
    results = []
    for fn in (c1, c2, c3, c4, c5, c6, c7, c8, c9):
        try: ok = fn()
        except Exception as e:
            print(f"  RAISED: {e}"); ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__": main()
