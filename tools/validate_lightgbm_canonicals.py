"""Phase 5 canonical validation for lightgbm_forecast. Session 23. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import lightgbm_forecast as lgbm_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_lgbm", "technique_id": "lightgbm_forecast",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _ar1(T=200, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = 0.5 * y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: lgbm baseline ===")
    return lgbm_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: lgbm num_leaves variants ===")
    y = _ar1(seed=43)
    for nl in (15, 31, 63):
        r = lgbm_mod.run(_ctx(y, num_leaves=nl), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: lgbm horizon variants ===")
    y = _ar1(seed=44)
    for h in (1, 5, 10):
        r = lgbm_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: lgbm learning_rate variants ===")
    y = _ar1(seed=45)
    for lr in (0.01, 0.1, 0.3):
        r = lgbm_mod.run(_ctx(y, learning_rate=lr), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S23 fix verification."""
    print("\n=== c5: lgbm invalid params rejected (S23 fix) ===")
    y = _ar1(seed=46)
    r = lgbm_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    r = lgbm_mod.run(_ctx(y, max_lag=0), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: lgbm short series T=30 ===")
    return lgbm_mod.run(_ctx(_ar1(T=30, seed=47)), _null).get("status") in ("success", "failure")

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
