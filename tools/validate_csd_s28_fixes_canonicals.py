"""Phase 5 canonical validation for critical_slowing_down — Session 28 fix verification.

Complements existing validate_critical_slowing_down_canonicals.py (5 cases for
D-CSD-1 through D-CSD-5 spec triggers) with 6 cases verifying Session 28
input validation gates (F-CSD-COMPOSITE, F-CSD-ROLLINGWIN/-NEG, F-CSD-KENDALL).
"""

import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import critical_slowing_down as csd_mod


def _null(*a, **k): pass
def _ctx(y, **p):
    return RunContext({
        "run_id": "test_csd_s28", "technique_id": "critical_slowing_down",
        "preset": "Fast", "seed": 42, "frequency": "D",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": list(y)}],
        "params": p,
    })


def _ar1(T=600, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T): y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def c1():
    """Baseline still passes after S28 fixes."""
    print("\n=== c1: csd baseline (post-S28 fixes) ===")
    return csd_mod.run(_ctx(_ar1()), _null).get("status") == "success"


def c2():
    """Valid composite_method values still work."""
    print("\n=== c2: csd valid composite_method {equal_weight_zscore, fisher_combined} ===")
    y = _ar1(seed=43)
    for m in ("equal_weight_zscore", "fisher_combined"):
        params = {"composite_method": m}
        if m == "fisher_combined":
            params["compute_pvalues"] = True
        r = csd_mod.run(_ctx(y, **params), _null)
        if r.get("status") != "success":
            print(f"    method={m} FAIL")
            return False
    return True


def c3():
    """Valid rolling_window and kendall_lookback still work."""
    print("\n=== c3: csd valid rolling_window/kendall_lookback ===")
    y = _ar1(seed=44)
    for rw in (50, 100, 200):
        r = csd_mod.run(_ctx(y, rolling_window=rw), _null)
        if r.get("status") != "success": return False
    for kl in (30, 50, 80):
        r = csd_mod.run(_ctx(y, kendall_lookback=kl), _null)
        if r.get("status") != "success": return False
    return True


def c4():
    """Existing detrending_method allowlist still works."""
    print("\n=== c4: csd valid detrending_method {gaussian, first_diff, linear} ===")
    y = _ar1(seed=45)
    for d in ("gaussian", "first_diff", "linear"):
        r = csd_mod.run(_ctx(y, detrending_method=d), _null)
        if r.get("status") != "success": return False
    return True


def c5():
    """S28 fix verification: invalid params rejected with actionable errors."""
    print("\n=== c5: csd invalid params rejected (S28 fixes) ===")
    y = _ar1(seed=46)
    # Invalid composite_method
    r = csd_mod.run(_ctx(y, composite_method="zzz"), _null)
    if r.get("status") != "failure": return False
    if "Unknown composite_method" not in (r.get("error_message") or ""): return False
    # Invalid rolling_window (zero, negative, non-numeric)
    r = csd_mod.run(_ctx(y, rolling_window=0), _null)
    if r.get("status") != "failure": return False
    if "rolling_window" not in (r.get("error_message") or ""): return False
    r = csd_mod.run(_ctx(y, rolling_window=-10), _null)
    if r.get("status") != "failure": return False
    # Invalid kendall_lookback
    r = csd_mod.run(_ctx(y, kendall_lookback=-5), _null)
    if r.get("status") != "failure": return False
    if "kendall_lookback" not in (r.get("error_message") or ""): return False
    print("  PASS: 4 invalid params rejected with actionable errors")
    return True


def c6():
    """Existing detrending_method allowlist (pre-S28) still rejects invalid."""
    print("\n=== c6: csd invalid detrending_method rejected (pre-S28 gate) ===")
    r = csd_mod.run(_ctx(_ar1(seed=47), detrending_method="zzz"), _null)
    if r.get("status") != "failure": return False
    if "detrending_method" not in (r.get("error_message") or ""): return False
    return True


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
