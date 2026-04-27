"""Phase 5 canonical validation for echo_state_network. Session 25. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import echo_state_network as esn_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    base = {"reservoir_size": 50, "warmup": 10}
    base.update(p)
    return RunContext({"run_id": "test_esn", "technique_id": "echo_state_network",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": base})

def _ar1(T=150, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = 0.5 * y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: esn baseline ===")
    return esn_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: esn spectral_radius variants ===")
    y = _ar1(seed=43)
    for sr in (0.5, 0.9, 1.2):
        r = esn_mod.run(_ctx(y, spectral_radius=sr), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: esn leak_rate variants ===")
    y = _ar1(seed=44)
    for lk in (0.1, 0.5, 1.0):
        r = esn_mod.run(_ctx(y, leak_rate=lk), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: esn horizon variants ===")
    y = _ar1(seed=45)
    for h in (1, 5, 10):
        r = esn_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S25 fix verification."""
    print("\n=== c5: esn invalid params rejected (S25 fix) ===")
    y = _ar1(seed=46)
    r = esn_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    r = esn_mod.run(_ctx(y, spectral_radius=-0.5), _null)
    if r.get("status") != "failure": return False
    if "spectral_radius" not in (r.get("error_message") or ""): return False
    r = esn_mod.run(_ctx(y, leak_rate=1.5), _null)
    if r.get("status") != "failure": return False
    if "leak_rate" not in (r.get("error_message") or ""): return False
    print("  PASS: 3 invalid params rejected")
    return True

def c6():
    print("\n=== c6: esn short series T=30 ===")
    return esn_mod.run(_ctx(_ar1(T=30, seed=47), warmup=5), _null).get("status") in ("success", "failure")

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
