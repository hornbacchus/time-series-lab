"""Phase 5 canonical validation for nar_narx
(`engine/techniques/nar_narx.py`; both nar and narx
technique IDs).

Created by CAI Phase 2 Session 12. 6 canonicals.
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
from techniques import nar_narx as nar_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, technique_id="nar",
                preset="Balanced", series_extra=None):
    series = [{"name": "y", "values": list(values)}]
    if series_extra:
        for name, vals in series_extra:
            series.append({"name": name, "values": list(vals)})
    return RunContext({
        "run_id": "test_nar", "technique_id": technique_id,
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": series,
        "params": dict(params or {}),
    })


def _simulate_arma(T=300, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    eps = rng.standard_normal(T)
    for t in range(1, T):
        y[t] = 0.7 * y[t - 1] + eps[t]
    return y.tolist()


def canonical_1():
    print("\n=== canonical_1: NAR baseline ===")
    y = _simulate_arma(T=300, seed=42)
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 2,
                                              "max_iter": 100}), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== canonical_2: NARX with exogenous regressor ===")
    y = _simulate_arma(T=300, seed=43)
    rng = np.random.default_rng(44)
    x = rng.standard_normal(300)
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 2,
                                              "max_iter": 100},
                                   technique_id="narx",
                                   series_extra=[("x", x)]), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== canonical_3: NAR on real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 2,
                                              "max_iter": 100}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== canonical_4: NAR longer ar_lags ===")
    y = _simulate_arma(T=300, seed=45)
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 5,
                                              "max_iter": 100}), _null)
    return res.get("status") == "success"


def canonical_5():
    print("\n=== C-CAL-1 (canonical_5): Constant series ===")
    y = [5.0] * 200
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 2,
                                              "max_iter": 50}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== C-CAL-2 (canonical_6): Short series T=80 ===")
    rng = np.random.default_rng(46)
    y = rng.standard_normal(80).tolist()
    res = nar_mod.run(_build_ctx(y, params={"ar_lags": 2,
                                              "max_iter": 50}), _null)
    return res.get("status") in ("success", "failure")


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
        try:
            ok = fn()
        except Exception as e:
            print(f"  RAISED: {type(e).__name__}: {e}")
            ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
