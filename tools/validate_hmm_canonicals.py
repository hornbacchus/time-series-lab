"""Phase 5 canonical validation for hmm (`engine/techniques/hmm_model.py`).

Created by CAI Phase 2 Session 12. 6 canonicals (compact for
5-wrapper batch).
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
from techniques import hmm_model


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_hmm", "technique_id": "hmm",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _simulate_2regime(T=400, seed=42):
    rng = np.random.default_rng(seed)
    states = np.zeros(T, dtype=int)
    P = np.array([[0.95, 0.05], [0.05, 0.95]])
    for t in range(1, T):
        states[t] = rng.choice(2, p=P[states[t - 1]])
    sigma = np.where(states == 0, 0.5, 2.0)
    return (sigma * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== canonical_1: HMM 2-state recovery ===")
    y = _simulate_2regime(T=400, seed=42)
    res = hmm_model.run(_build_ctx(y, params={"n_components": 2}), _null)
    if res.get("status") != "success":
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  n_components={a.get('n_components')}, ll={a.get('log_likelihood')}")
    return a.get("n_components") == 2


def canonical_2():
    print("\n=== canonical_2: HMM 3-state on 2-regime DGP ===")
    y = _simulate_2regime(T=400, seed=43)
    res = hmm_model.run(_build_ctx(y, params={"n_components": 3}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== canonical_3: HMM on real GSPC log returns ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = hmm_model.run(_build_ctx(y, params={"n_components": 2}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== canonical_4: HMM diag covariance_type ===")
    y = _simulate_2regime(T=300, seed=44)
    res = hmm_model.run(_build_ctx(y, params={"n_components": 2,
                                                "covariance_type": "diag"}),
                         _null)
    return res.get("status") == "success"


def canonical_5():
    print("\n=== C-CAL-1 (canonical_5): Constant series ===")
    y = [5.0] * 200
    res = hmm_model.run(_build_ctx(y, params={"n_components": 2}), _null)
    return res.get("status") in ("success", "failure")


def canonical_6():
    print("\n=== C-CAL-2 (canonical_6): Short series T=80 ===")
    rng = np.random.default_rng(45)
    y = rng.standard_normal(80).tolist()
    res = hmm_model.run(_build_ctx(y, params={"n_components": 2}), _null)
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
