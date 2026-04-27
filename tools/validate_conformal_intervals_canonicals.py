"""Phase 5 canonical validation for conformal_intervals. Session 21. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import conformal_intervals as ci_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_ci", "technique_id": "conformal_intervals",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _seas(T=240, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05*t + 2.0*np.sin(2*np.pi*t/12) + 0.3*rng.standard_normal(T)).tolist()

def c1():
    print("\n=== c1: ci baseline ===")
    return ci_mod.run(_ctx(_seas()), _null).get("status") == "success"

def c2():
    print("\n=== c2: ci cal_fraction variants ===")
    y = _seas(seed=43)
    for cf in (0.1, 0.2, 0.3):
        r = ci_mod.run(_ctx(y, cal_fraction=cf), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: ci confidence_level variants ===")
    y = _seas(seed=44)
    for c in (0.90, 0.95):
        r = ci_mod.run(_ctx(y, confidence_level=c), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: ci horizon variants ===")
    y = _seas(seed=45)
    for h in (5, 10, 20):
        r = ci_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S21 fix verification."""
    print("\n=== c5: ci invalid params rejected (S21 fix) ===")
    y = _seas(seed=46)
    r = ci_mod.run(_ctx(y, cal_fraction=1.5), _null)
    if r.get("status") != "failure": return False
    if "cal_fraction must be in" not in (r.get("error_message") or ""): return False
    r = ci_mod.run(_ctx(y, confidence_level=2.0), _null)
    if r.get("status") != "failure": return False
    print("  PASS: invalid cal_fraction and confidence_level rejected")
    return True

def c6():
    print("\n=== c6: ci short series T=30 ===")
    return ci_mod.run(_ctx(_seas(T=30, seed=47))).get("status") in ("success", "failure") if False else \
        ci_mod.run(_ctx(_seas(T=30, seed=47)), _null).get("status") in ("success", "failure")

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
