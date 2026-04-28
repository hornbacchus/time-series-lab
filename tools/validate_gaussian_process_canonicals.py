"""Phase 5 canonical validation for gaussian_process_forecast. Session 26. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import gaussian_process_forecast as gp_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_gp", "technique_id": "gaussian_process_forecast",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _ar1(T=120, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = 0.5 * y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: gp baseline ===")
    return gp_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: gp kernel variants ===")
    y = _ar1(seed=43)
    for k in ("rbf", "matern", "rational_quadratic"):
        r = gp_mod.run(_ctx(y, kernel=k), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: gp confidence_level variants ===")
    y = _ar1(seed=44)
    for c in (0.90, 0.95, 0.99):
        r = gp_mod.run(_ctx(y, confidence_level=c), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: gp horizon variants ===")
    y = _ar1(seed=45)
    for h in (1, 5, 20):
        r = gp_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S26 fix verification."""
    print("\n=== c5: gp invalid params rejected (S26 fix) ===")
    y = _ar1(seed=46)
    r = gp_mod.run(_ctx(y, kernel="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown kernel" not in (r.get("error_message") or ""): return False
    r = gp_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    r = gp_mod.run(_ctx(y, confidence_level=2.0), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: gp short series T=15 ===")
    return gp_mod.run(_ctx(_ar1(T=15, seed=47)), _null).get("status") in ("success", "failure")

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
