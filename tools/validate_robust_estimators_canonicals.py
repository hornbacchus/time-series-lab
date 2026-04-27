"""Phase 5 canonical validation for robust_estimators. Session 21. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import robust_estimators as re_mod

def _null(*a, **k): pass
def _ctx(y, *, preset="Balanced", **p):
    return RunContext({"run_id": "test_re", "technique_id": "robust_estimators",
        "preset": preset, "seed": 42, "frequency": "M",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _ar1(T=200, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = 0.5*y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: re baseline ===")
    return re_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: re trim_fraction variants ===")
    y = _ar1(seed=43)
    for tf in (0.05, 0.10, 0.20):
        r = re_mod.run(_ctx(y, trim_fraction=tf), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: re winsor_fraction variants ===")
    y = _ar1(seed=44)
    for wf in (0.05, 0.10, 0.20):
        r = re_mod.run(_ctx(y, winsor_fraction=wf), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: re Thorough preset (multi-fraction sweep) ===")
    y = _ar1(seed=45)
    r = re_mod.run(_ctx(y, preset="Thorough"), _null)
    return r.get("status") == "success"

def c5():
    """S21 fix verification."""
    print("\n=== c5: re invalid trim_fraction rejected (S21 fix) ===")
    y = _ar1(seed=46)
    r = re_mod.run(_ctx(y, trim_fraction=0.6), _null)
    if r.get("status") != "failure": return False
    if "trim_fraction must be" not in (r.get("error_message") or ""): return False
    r = re_mod.run(_ctx(y, winsor_fraction=0.6), _null)
    if r.get("status") != "failure": return False
    if "winsor_fraction must be" not in (r.get("error_message") or ""): return False
    print("  PASS: trim and winsor fractions rejected when out of range")
    return True

def c6():
    print("\n=== c6: re series with extreme outliers ===")
    rng = np.random.default_rng(47)
    y = rng.standard_normal(200)
    y[10] = 50; y[100] = -50
    return re_mod.run(_ctx(y.tolist()), _null).get("status") == "success"

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
