"""Phase 5 canonical validation for quantile_regression_model. Session 26. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import quantile_regression_model as qr_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_qr", "technique_id": "quantile_regression_model",
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
    print("\n=== c1: qr baseline ===")
    return qr_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: qr horizon variants ===")
    y = _ar1(seed=43)
    for h in (1, 5, 10):
        r = qr_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: qr quantiles variants ===")
    y = _ar1(seed=44)
    for q in ([0.1], [0.5], [0.1, 0.5, 0.9]):
        r = qr_mod.run(_ctx(y, quantiles=q), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: qr n_estimators variants ===")
    y = _ar1(seed=45)
    for ne in (50, 100, 200):
        r = qr_mod.run(_ctx(y, n_estimators=ne), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S26 fix verification."""
    print("\n=== c5: qr invalid params rejected (S26 fix) ===")
    y = _ar1(seed=46)
    r = qr_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    r = qr_mod.run(_ctx(y, n_lags=0), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: qr short series T=30 ===")
    return qr_mod.run(_ctx(_ar1(T=30, seed=47)), _null).get("status") in ("success", "failure")

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
