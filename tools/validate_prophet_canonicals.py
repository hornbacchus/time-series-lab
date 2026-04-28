"""Phase 5 canonical validation for prophet_forecast. Session 26. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import prophet_forecast as p_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_p", "technique_id": "prophet_forecast",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _seasonal(T=240, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05*t + 2.0*np.sin(2*np.pi*t/12) + 0.3*rng.standard_normal(T)).tolist()

def c1():
    print("\n=== c1: prophet baseline ===")
    return p_mod.run(_ctx(_seasonal()), _null).get("status") == "success"

def c2():
    print("\n=== c2: prophet horizon variants ===")
    y = _seasonal(seed=43)
    for h in (1, 12, 30):
        r = p_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: prophet seasonality toggles ===")
    y = _seasonal(seed=44)
    for ys in (True, False, "auto"):
        r = p_mod.run(_ctx(y, yearly_seasonality=ys), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: prophet changepoint_prior_scale variants ===")
    y = _seasonal(seed=45)
    for cps in (0.01, 0.05, 0.5):
        r = p_mod.run(_ctx(y, changepoint_prior_scale=cps), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S26 fix verification."""
    print("\n=== c5: prophet invalid horizon rejected (S26 fix) ===")
    y = _seasonal(seed=46)
    r = p_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: prophet short series T=20 ===")
    return p_mod.run(_ctx(_seasonal(T=20, seed=47)), _null).get("status") in ("success", "failure")

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
