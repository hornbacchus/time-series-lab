"""Phase 5 canonical validation for autoencoder_anomaly. Session 25. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import autoencoder_anomaly as ae_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    base = {"epochs": 5, "hidden_dim": 16, "window_size": 12}
    base.update(p)
    return RunContext({"run_id": "test_ae", "technique_id": "autoencoder_anomaly",
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
    print("\n=== c1: ae baseline ===")
    return ae_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: ae contamination variants ===")
    y = _ar1(seed=43)
    for c in (0.01, 0.05, 0.10):
        r = ae_mod.run(_ctx(y, contamination=c), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: ae hidden_dim variants ===")
    y = _ar1(seed=44)
    for h in (8, 16, 32):
        r = ae_mod.run(_ctx(y, hidden_dim=h), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: ae window_size variants ===")
    y = _ar1(seed=45)
    for w in (8, 16):
        r = ae_mod.run(_ctx(y, window_size=w), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S25 fix verification."""
    print("\n=== c5: ae invalid contamination rejected (S25 fix) ===")
    y = _ar1(seed=46)
    r = ae_mod.run(_ctx(y, contamination=1.5), _null)
    if r.get("status") != "failure": return False
    if "contamination" not in (r.get("error_message") or ""): return False
    r = ae_mod.run(_ctx(y, contamination=-0.1), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: ae short series T=30 ===")
    return ae_mod.run(_ctx(_ar1(T=30, seed=47), window_size=4), _null).get("status") in ("success", "failure")

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
