"""Phase 5 canonical validation for block_bootstrap. Session 21. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import block_bootstrap as bb_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({"run_id": "test_bb", "technique_id": "block_bootstrap",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p})

def _ar1(T=200, phi=0.6, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = phi * y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: bb baseline ===")
    return bb_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: bb block_length variants ===")
    y = _ar1(seed=43)
    for bl in (5, 10, "auto"):
        r = bb_mod.run(_ctx(y, block_length=bl), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: bb confidence_level variants ===")
    y = _ar1(seed=44)
    for c in (0.90, 0.95, 0.99):
        r = bb_mod.run(_ctx(y, confidence_level=c), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: bb white noise ===")
    rng = np.random.default_rng(45)
    return bb_mod.run(_ctx(rng.standard_normal(200).tolist()), _null).get("status") == "success"

def c5():
    """S21 fix verification."""
    print("\n=== c5: bb invalid params rejected (S21 fix) ===")
    y = _ar1(seed=46)
    r = bb_mod.run(_ctx(y, block_length=0), _null)
    if r.get("status") != "failure": return False
    if "block_length must be >= 1" not in (r.get("error_message") or ""): return False
    r = bb_mod.run(_ctx(y, confidence_level=2.0), _null)
    if r.get("status") != "failure": return False
    if "confidence_level must be" not in (r.get("error_message") or ""): return False
    r = bb_mod.run(_ctx(y, n_bootstrap=1), _null)
    if r.get("status") != "failure": return False
    print("  PASS: 3 invalid params rejected")
    return True

def c6():
    print("\n=== c6: bb short series T=15 ===")
    return bb_mod.run(_ctx(_ar1(T=15, seed=47)), _null).get("status") in ("success", "failure")

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
