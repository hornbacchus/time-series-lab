"""Phase 5 canonical validation for forecast_combination. Session 21. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import forecast_combination as fc_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_fc", "technique_id": "forecast_combination",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _seas(T=240, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05*t + 2.0*np.sin(2*np.pi*t/12) + 0.3*rng.standard_normal(T)).tolist()

def c1():
    print("\n=== c1: fc baseline ===")
    return fc_mod.run(_ctx(_seas()), _null).get("status") == "success"

def c2():
    print("\n=== c2: fc holdout_fraction variants ===")
    y = _seas(seed=43)
    for hf in (0.15, 0.20, 0.30):
        r = fc_mod.run(_ctx(y, holdout_fraction=hf), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: fc horizon variants ===")
    y = _seas(seed=44)
    for h in (5, 10, 20):
        r = fc_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: fc seasonal toggle ===")
    y = _seas(seed=45)
    for s in (True, False):
        r = fc_mod.run(_ctx(y, seasonal=s), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S21 fix verification."""
    print("\n=== c5: fc invalid holdout_fraction rejected (S21 fix) ===")
    y = _seas(seed=46)
    r = fc_mod.run(_ctx(y, holdout_fraction=1.5), _null)
    if r.get("status") != "failure": return False
    if "holdout_fraction must be" not in (r.get("error_message") or ""): return False
    print(f"  PASS: {(r.get('error_message') or '')[:80]}")
    return True

def c6():
    print("\n=== c6: fc short series T=30 ===")
    return fc_mod.run(_ctx(_seas(T=30, seed=47)), _null).get("status") in ("success", "failure")

def main():
    results = []
    for fn in (c1, c2, c3, c4, c5, c6):
        try: ok = fn()
        except Exception as e:
            print(f"  RAISED: {e}"); ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__": main()
