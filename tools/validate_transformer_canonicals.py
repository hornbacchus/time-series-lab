"""Phase 5 canonical validation for transformer_forecast. Session 24. 6 canonicals.

NB: validate_transformer_attention_canonicals.py exists for the attention-
exposure mechanism (verification 3f). This Session 24 file complements
it with broader transformer_forecast parameter coverage.
"""
import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))
import numpy as np
from techniques.base import RunContext
from techniques import transformer_forecast as tf_mod

def _null(*a, **k): pass
def _ctx(y, **p):
    base = {"epochs": 5, "d_model": 16, "n_heads": 2, "n_lags": 8,
            "n_encoder_layers": 1, "dim_feedforward": 32}
    base.update(p)
    return RunContext({"run_id": "test_tf", "technique_id": "transformer_forecast",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": base})

def _ar1(T=120, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = 0.5 * y[t-1] + rng.standard_normal()
    return y.tolist()

def c1():
    print("\n=== c1: tf baseline ===")
    return tf_mod.run(_ctx(_ar1()), _null).get("status") == "success"

def c2():
    print("\n=== c2: tf n_heads variants (compatible d_model) ===")
    y = _ar1(seed=43)
    for h in (1, 2, 4):
        r = tf_mod.run(_ctx(y, d_model=16, n_heads=h), _null)
        if r.get("status") != "success": return False
    return True

def c3():
    print("\n=== c3: tf horizon variants ===")
    y = _ar1(seed=44)
    for h in (1, 5, 10):
        r = tf_mod.run(_ctx(y, horizon=h), _null)
        if r.get("status") != "success": return False
    return True

def c4():
    print("\n=== c4: tf n_encoder_layers variants ===")
    y = _ar1(seed=45)
    for n in (1, 2):
        r = tf_mod.run(_ctx(y, n_encoder_layers=n), _null)
        if r.get("status") != "success": return False
    return True

def c5():
    """S24 fix verification (DMODEL consistency, HORIZON range)."""
    print("\n=== c5: tf invalid params rejected (S24 fix) ===")
    y = _ar1(seed=46)
    r = tf_mod.run(_ctx(y, d_model=17, n_heads=4), _null)  # not divisible
    if r.get("status") != "failure": return False
    if "must be divisible" not in (r.get("error_message") or ""): return False
    r = tf_mod.run(_ctx(y, horizon=-1), _null)
    if r.get("status") != "failure": return False
    print("  PASS")
    return True

def c6():
    print("\n=== c6: tf short series T=30 ===")
    return tf_mod.run(_ctx(_ar1(T=30, seed=47), n_lags=4), _null).get("status") in ("success", "failure")

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
