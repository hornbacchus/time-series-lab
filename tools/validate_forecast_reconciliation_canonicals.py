"""Phase 5 canonical validation for forecast_reconciliation. Session 22. 6 canonicals.

NB: validate_mint_reconciliation_canonicals.py already exists (B1 follow-up
specifically for MinT). This Session 22 file complements it with broader
forecast_reconciliation parameter coverage.
"""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import forecast_reconciliation as fr_mod

def _null(*a, **k): pass
def _ctx(Y, names, **p):
    return RunContext({"run_id": "test_fr", "technique_id": "forecast_reconciliation",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(Y[0]))),
        "series": [{"name": n, "values": list(s)} for n, s in zip(names, Y)],
        "params": p})

def _hier(T=120, seed=42):
    rng = np.random.default_rng(seed)
    bs = [(np.cumsum(rng.standard_normal(T)) + 100.0).tolist() for _ in range(4)]
    top = np.sum(bs, axis=0).tolist()
    return [top] + bs

def c1():
    print("\n=== c1: fr baseline ===")
    return fr_mod.run(_ctx(_hier(), ["top","b1","b2","b3","b4"]), _null).get("status") == "success"

def c2():
    print("\n=== c2: fr method variants ===")
    Y = _hier(seed=43)
    for m in ("bottom_up", "top_down", "ols", "wls_variance"):
        r = fr_mod.run(_ctx(Y, ["top","b1","b2","b3","b4"], method=m), _null)
        if r.get("status") != "success":
            print(f"    method={m} FAIL: {(r.get('error_message') or '')[:60]}")
            return False
    return True

def c3():
    print("\n=== c3: fr base_forecaster variants ===")
    Y = _hier(seed=44)
    for bf in ("naive", "drift", "ets"):
        r = fr_mod.run(_ctx(Y, ["top","b1","b2","b3","b4"], base_forecaster=bf), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: fr top_down_weights variants ===")
    Y = _hier(seed=45)
    for tdw in ("proportions_avg", "proportions_last"):
        r = fr_mod.run(_ctx(Y, ["top","b1","b2","b3","b4"],
                              method="top_down", top_down_weights=tdw), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S22 fix verification (BASEFC + TDWEIGHTS)."""
    print("\n=== c5: fr invalid base_forecaster + top_down_weights rejected (S22 fix) ===")
    Y = _hier(seed=46)
    r = fr_mod.run(_ctx(Y, ["top","b1","b2","b3","b4"], base_forecaster="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown base_forecaster" not in (r.get("error_message") or ""): return False
    r = fr_mod.run(_ctx(Y, ["top","b1","b2","b3","b4"],
                          method="top_down", top_down_weights="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown top_down_weights" not in (r.get("error_message") or ""): return False
    print("  PASS: both invalid base_forecaster and top_down_weights rejected")
    return True

def c6():
    print("\n=== c6: fr short series T=20 ===")
    return fr_mod.run(_ctx(_hier(T=20, seed=47), ["top","b1","b2","b3","b4"]), _null).get("status") in ("success", "failure")

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
