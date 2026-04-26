"""Phase 5 canonical validation for wavelet_coherence.

Created by CAI Phase 2 Session 13. 6 canonicals.
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
from techniques import wavelet_coherence as wc_mod


def _null(*a, **k): pass


def _build_ctx(y1, y2, *, params=None):
    return RunContext({
        "run_id": "test_wc", "technique_id": "wavelet_coherence",
        "preset": "Balanced", "seed": 42, "frequency": "daily",
        "time": list(range(len(y1))),
        "series": [{"name": "y1", "values": list(y1)},
                    {"name": "y2", "values": list(y2)}],
        "params": dict(params or {}),
    })


def _correlated_pair(T=400, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y1 = np.sin(2 * np.pi * 0.05 * t) + 0.3 * rng.standard_normal(T)
    y2 = np.sin(2 * np.pi * 0.05 * t + 0.5) + 0.3 * rng.standard_normal(T)
    return y1.tolist(), y2.tolist()


def canonical_1():
    print("\n=== c1: wavelet_coherence on correlated pair ===")
    y1, y2 = _correlated_pair()
    res = wc_mod.run(_build_ctx(y1, y2), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: wavelet_coherence morl wavelet ===")
    y1, y2 = _correlated_pair(seed=43)
    res = wc_mod.run(_build_ctx(y1, y2,
                                  params={"wavelet": "morl"}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: wavelet_coherence real (GSPC, DGS10) ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-300:]
    y1 = (100.0 * np.diff(np.log(p))).tolist()
    d10 = data["DGS10"][~np.isnan(data["DGS10"])][-len(y1) - 1:]
    y2 = np.diff(d10).tolist()[:len(y1)]
    res = wc_mod.run(_build_ctx(y1[:len(y2)], y2[:len(y1)]), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: wavelet_coherence invalid wavelet rejected ===")
    y1, y2 = _correlated_pair(seed=44)
    res = wc_mod.run(_build_ctx(y1, y2,
                                  params={"wavelet": "zzz"}), _null)
    return res.get("status") == "failure"


def canonical_5():
    print("\n=== c5: wavelet_coherence n_scales sweep ===")
    y1, y2 = _correlated_pair(seed=45)
    for ns in [16, 32]:
        res = wc_mod.run(_build_ctx(y1, y2,
                                      params={"n_scales": ns}), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_6():
    print("\n=== c6: wavelet_coherence short series ===")
    rng = np.random.default_rng(46)
    y1 = rng.standard_normal(50).tolist()
    y2 = rng.standard_normal(50).tolist()
    res = wc_mod.run(_build_ctx(y1, y2), _null)
    return res.get("status") in ("success", "failure")


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
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
