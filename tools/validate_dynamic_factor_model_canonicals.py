"""Phase 5 canonical validation for dynamic_factor_model. Session 22. 6 canonicals."""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import dynamic_factor_model as dfm_mod

def _null(*a, **k): pass
def _ctx(Y, names, **p):
    return RunContext({"run_id": "test_dfm", "technique_id": "dynamic_factor_model",
        "preset": "Fast", "seed": 42, "frequency": "M",
        "time": list(range(len(Y[0]))),
        "series": [{"name": n, "values": list(s)} for n, s in zip(names, Y)],
        "params": p})

def _factor(T=200, n_vars=5, n_factors=2, seed=42):
    rng = np.random.default_rng(seed)
    F = np.zeros((T, n_factors))
    for t in range(1, T): F[t] = 0.7 * F[t-1] + rng.standard_normal(n_factors)
    L = rng.standard_normal((n_vars, n_factors)) * 0.5
    Y = F @ L.T + rng.standard_normal((T, n_vars)) * 0.3
    return [Y[:, i].tolist() for i in range(n_vars)]

def c1():
    print("\n=== c1: dfm baseline ===")
    Y = _factor()
    return dfm_mod.run(_ctx(Y, [f"y{i}" for i in range(5)], k_factors=2), _null).get("status") == "success"

def c2():
    print("\n=== c2: dfm k_factors variants ===")
    Y = _factor(seed=43)
    for k in (1, 2, 3):
        r = dfm_mod.run(_ctx(Y, [f"y{i}" for i in range(5)], k_factors=k), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: dfm transform variants {auto, diff, none} ===")
    Y = _factor(seed=44)
    for t in ("auto", "diff", "none"):
        r = dfm_mod.run(_ctx(Y, [f"y{i}" for i in range(5)], transform=t, k_factors=2), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: dfm transform=log_diff with positive data ===")
    Y_pos = [list(np.exp(np.array(s) * 0.1)) for s in _factor(seed=45)]
    r = dfm_mod.run(_ctx(Y_pos, [f"y{i}" for i in range(5)], transform="log_diff", k_factors=2), _null)
    return r.get("status") == "success"

def c5():
    """S22 fix verification."""
    print("\n=== c5: dfm invalid transform rejected (S22 fix) ===")
    Y = _factor(seed=46)
    r = dfm_mod.run(_ctx(Y, [f"y{i}" for i in range(5)], transform="zzz", k_factors=2), _null)
    if r.get("status") != "failure": return False
    if "Unknown transform" not in (r.get("error_message") or ""): return False
    print(f"  PASS: {(r.get('error_message') or '')[:80]}")
    return True

def c6():
    print("\n=== c6: dfm short series T=30 ===")
    Y = _factor(T=30, seed=47)
    r = dfm_mod.run(_ctx(Y, [f"y{i}" for i in range(5)], k_factors=2), _null)
    return r.get("status") in ("success", "failure")

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
