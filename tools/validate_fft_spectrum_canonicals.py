"""Phase 5 canonical validation for fft_spectrum.

Created by CAI Phase 2 Session 13. 6 canonicals.
canonical_5 + canonical_6 verify Session 13 fixes
(F-FD-FFT-WINDOW + F-FD-FFT-DETREND).
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
from techniques import fft_spectrum as fft_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_fft", "technique_id": "fft_spectrum",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _sine(T=500, f=0.1, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (np.sin(2 * np.pi * f * t) + 0.2 * rng.standard_normal(T)).tolist()


def canonical_1():
    print("\n=== c1: FFT on pure sinusoid ===")
    res = fft_mod.run(_build_ctx(_sine()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: FFT detrend variants ===")
    y = _sine(seed=43)
    for d in ["mean", "linear", "none"]:
        res = fft_mod.run(_build_ctx(y, params={"detrend": d}), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_3():
    print("\n=== c3: FFT window variants ===")
    y = _sine(seed=44)
    for w in ["hann", "hamming", "blackman", "bartlett"]:
        res = fft_mod.run(_build_ctx(y, params={"window": w}), _null)
        if res.get("status") != "success":
            return False
    return True


def canonical_4():
    print("\n=== c4: FFT real GSPC ===")
    f = os.path.join(_ROOT, "tools", "calibration_audit", "fixtures",
                      "macro_canonical_series.npz")
    if not os.path.exists(f):
        return True
    data = np.load(f)
    p = data["GSPC"][~np.isnan(data["GSPC"])][-500:]
    y = (100.0 * np.diff(np.log(p))).tolist()
    res = fft_mod.run(_build_ctx(y), _null)
    return res.get("status") == "success"


def canonical_5():
    """C-CAL-1: Session 13 fix verification — invalid window."""
    print("\n=== c5: FFT invalid window allowlist (S13 fix) ===")
    res = fft_mod.run(_build_ctx(_sine(),
                                   params={"window": "zzz"}), _null)
    if res.get("status") != "failure":
        print(f"  FAIL: expected failure")
        return False
    err = res.get("error_message") or ""
    if "Unknown window" not in err:
        print(f"  FAIL: unexpected error: {err}")
        return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    """C-CAL-2: Session 13 fix verification — invalid detrend."""
    print("\n=== c6: FFT invalid detrend allowlist (S13 fix) ===")
    res = fft_mod.run(_build_ctx(_sine(),
                                   params={"detrend": "zzz"}), _null)
    if res.get("status") != "failure":
        print(f"  FAIL: expected failure")
        return False
    err = res.get("error_message") or ""
    if "Unknown detrend" not in err:
        return False
    print(f"  PASS: {err[:80]}")
    return True


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
