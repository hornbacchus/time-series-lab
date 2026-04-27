"""Phase 5 canonical validation for transfer_function.

Created by CAI Phase 2 Session 20. 9 canonicals (5 base + 4 C-CAL).
canonical_5 verifies Session 20 fixes (F-TF-POLYNOMIAL,
F-TF-MAXLAG-NEG, F-TF-AR-ORDER-NEG, F-TF-ALMON-DEGREE).
"""

import os, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import transfer_function as tf_mod


def _null(*a, **k): pass


def _build_ctx(y, x, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_tf", "technique_id": "transfer_function",
        "preset": preset, "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "Y", "values": list(y)},
                    {"name": "X", "values": list(x)}],
        "params": dict(params or {}),
    })


def _simulate_tf(T=300, true_lag=2, true_weight=0.6, ar_phi=0.3, seed=42):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(T)
    n = np.zeros(T)
    eps = rng.standard_normal(T) * 0.3
    for t in range(1, T):
        n[t] = ar_phi * n[t - 1] + eps[t]
    y = np.zeros(T)
    for t in range(true_lag, T):
        y[t] = true_weight * x[t - true_lag] + n[t]
    return y.tolist(), x.tolist()


def canonical_1():
    print("\n=== c1: TF baseline (b=2 DGP recovery) ===")
    y, x = _simulate_tf(T=400)
    res = tf_mod.run(_build_ctx(y, x, params={"max_lag": 5, "ar_order": 1}), _null)
    if res.get("status") != "success": return False
    af = res["audit_fields"]
    return af.get("peak_lag") == 2


def canonical_2():
    print("\n=== c2: TF max_lag variants ===")
    y, x = _simulate_tf(T=300, seed=43)
    for ml in (2, 4, 8):
        res = tf_mod.run(_build_ctx(y, x, params={"max_lag": ml}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_3():
    print("\n=== c3: TF ar_order variants ===")
    y, x = _simulate_tf(T=300, ar_phi=0.5, seed=44)
    for ao in (0, 1, 2):
        res = tf_mod.run(_build_ctx(y, x, params={"max_lag": 4, "ar_order": ao}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_4():
    print("\n=== c4: TF polynomial variants {unrestricted, almon} ===")
    y, x = _simulate_tf(T=400, seed=45)
    for poly in ("unrestricted", "almon"):
        res = tf_mod.run(_build_ctx(y, x,
                                       params={"polynomial": poly,
                                               "max_lag": 8, "almon_degree": 3}), _null)
        if res.get("status") != "success": return False
    return True


def canonical_5():
    """Session 20 fix verification (F-TF-* findings)."""
    print("\n=== c5: TF invalid params rejected (S20 fixes) ===")
    y, x = _simulate_tf(T=300, seed=46)
    # Invalid polynomial
    res = tf_mod.run(_build_ctx(y, x, params={"polynomial": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown polynomial" not in (res.get("error_message") or ""): return False
    # Negative max_lag
    res = tf_mod.run(_build_ctx(y, x, params={"max_lag": -1}), _null)
    if res.get("status") != "failure": return False
    if "max_lag must be >= 0" not in (res.get("error_message") or ""): return False
    # Negative ar_order
    res = tf_mod.run(_build_ctx(y, x, params={"ar_order": -2}), _null)
    if res.get("status") != "failure": return False
    if "ar_order must be >= 0" not in (res.get("error_message") or ""): return False
    # almon_degree too high
    res = tf_mod.run(_build_ctx(y, x,
                                   params={"polynomial": "almon", "max_lag": 5,
                                           "almon_degree": 50}), _null)
    if res.get("status") != "failure": return False
    if "almon" not in (res.get("error_message") or ""): return False
    print("  PASS: all 4 invalid params rejected")
    return True


def canonical_6():
    """C-CAL-1: identical input=output (lag-0 coefficient ≈ 1)."""
    print("\n=== c6 (C-CAL-1): identical input=output ===")
    rng = np.random.default_rng(47)
    z = rng.standard_normal(300).tolist()
    res = tf_mod.run(_build_ctx(z, z,
                                   params={"max_lag": 3, "ar_order": 0}), _null)
    if res.get("status") != "success": return False
    af = res["audit_fields"]
    return af.get("peak_lag") == 0 and abs(af.get("peak_lag_weight", 0) - 1.0) < 0.01


def canonical_7():
    """C-CAL-2: independent series (no TF expected)."""
    print("\n=== c7 (C-CAL-2): independent input/output ===")
    rng = np.random.default_rng(48)
    res = tf_mod.run(_build_ctx(rng.standard_normal(300).tolist(),
                                   rng.standard_normal(300).tolist(),
                                   params={"max_lag": 5}), _null)
    if res.get("status") != "success": return False
    af = res["audit_fields"]
    return af.get("r_squared", 1.0) < 0.1


def canonical_8():
    """C-CAL-3: short series with high-order TF (boundary)."""
    print("\n=== c8 (C-CAL-3): short T=20 with max_lag=10 ===")
    rng = np.random.default_rng(49)
    res = tf_mod.run(_build_ctx(rng.standard_normal(20).tolist(),
                                   rng.standard_normal(20).tolist(),
                                   params={"max_lag": 10}), _null)
    return res.get("status") == "failure"


def canonical_9():
    """C-CAL-4: heavy-tail noise on output."""
    print("\n=== c9 (C-CAL-4): heavy-tail noise on output ===")
    rng = np.random.default_rng(50)
    T = 300
    x = rng.standard_normal(T)
    n = rng.standard_t(df=3, size=T) * 0.5
    y = np.zeros(T)
    for t in range(2, T):
        y[t] = 0.5 * x[t - 2] + n[t]
    res = tf_mod.run(_build_ctx(y.tolist(), x.tolist(),
                                   params={"max_lag": 5}), _null)
    return res.get("status") == "success"


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6,
               canonical_7, canonical_8, canonical_9):
        try: ok = fn()
        except Exception as e:
            print(f"  RAISED: {type(e).__name__}: {e}"); ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
