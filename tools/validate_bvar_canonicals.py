"""Phase 5 canonical validation for bvar. Session 22. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import bvar as bvar_mod

def _null(*a, **k): pass
def _ctx(Y, names, **p):
    return RunContext({"run_id": "test_bv", "technique_id": "bvar",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(Y[0]))),
        "series": [{"name": n, "values": list(s)} for n, s in zip(names, Y)],
        "params": p})

def _var3(T=150, seed=42):
    rng = np.random.default_rng(seed)
    A = np.array([[0.5, 0.1, 0.05],[0.05, 0.6, 0.1],[0.1, 0.05, 0.4]])
    Y = np.zeros((T, 3))
    for t in range(1, T):
        Y[t] = A @ Y[t-1] + rng.standard_normal(3) * 0.5
    return [Y[:, i].tolist() for i in range(3)]

def c1():
    print("\n=== c1: bvar baseline ===")
    return bvar_mod.run(_ctx(_var3(), ["y1","y2","y3"], n_draws=50), _null).get("status") == "success"

def c2():
    print("\n=== c2: bvar lag variants ===")
    Y = _var3(seed=43)
    for p in (1, 2, 4):
        r = bvar_mod.run(_ctx(Y, ["y1","y2","y3"], lags=p, n_draws=50), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: bvar lambda hyperparam variants ===")
    Y = _var3(seed=44)
    for l1 in (0.05, 0.1, 0.3):
        r = bvar_mod.run(_ctx(Y, ["y1","y2","y3"], lambda1=l1, n_draws=50), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: bvar with constant toggle ===")
    Y = _var3(seed=45)
    for ic in (True, False):
        r = bvar_mod.run(_ctx(Y, ["y1","y2","y3"], include_constant=ic, n_draws=50), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S22 fix verification."""
    print("\n=== c5: bvar invalid params rejected (S22 fix) ===")
    Y = _var3(seed=46)
    for p in [{"lambda1": -0.5}, {"lambda2": -0.1}, {"lambda3": -1.0}, {"lags": 0}]:
        p.update({"n_draws": 50})
        r = bvar_mod.run(_ctx(Y, ["y1","y2","y3"], **p), _null)
        if r.get("status") != "failure":
            print(f"    FAIL: {list(p.keys())[0]} not rejected")
            return False
    print("  PASS: 4 invalid params rejected")
    return True

def c6():
    print("\n=== c6: bvar short series T=30 ===")
    return bvar_mod.run(_ctx(_var3(T=30, seed=47), ["y1","y2","y3"], n_draws=50), _null).get("status") in ("success", "failure")

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
