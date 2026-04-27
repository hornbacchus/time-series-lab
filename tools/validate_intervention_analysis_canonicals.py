"""Phase 5 canonical validation for intervention_analysis.

Created by CAI Phase 2 Session 15. 6 canonicals.
canonical_5 verifies Session 15 fix (F-CP-INT-TYPE).
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
from techniques import intervention_analysis as int_mod


def _null(*a, **k): pass


def _build_ctx(values, *, params=None, preset="Fast"):
    return RunContext({
        "run_id": "test_int", "technique_id": "intervention_analysis",
        "preset": preset, "seed": 42, "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _step_series(T=200, break_at=100, shift=2.0, seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[break_at:] += shift
    return y.tolist()


def canonical_1():
    print("\n=== c1: int baseline (auto-detect single break) ===")
    res = int_mod.run(_build_ctx(_step_series()), _null)
    return res.get("status") == "success"


def canonical_2():
    print("\n=== c2: int explicit pulse ===")
    res = int_mod.run(_build_ctx(
        _step_series(seed=43),
        params={"interventions": [{"index": 100, "type": "pulse", "name": "test"}]}), _null)
    return res.get("status") == "success"


def canonical_3():
    print("\n=== c3: int explicit step ===")
    res = int_mod.run(_build_ctx(
        _step_series(seed=44),
        params={"interventions": [{"index": 100, "type": "step", "name": "test"}]}), _null)
    return res.get("status") == "success"


def canonical_4():
    print("\n=== c4: int explicit ramp ===")
    res = int_mod.run(_build_ctx(
        _step_series(seed=45),
        params={"interventions": [{"index": 100, "type": "ramp", "name": "test"}]}), _null)
    return res.get("status") == "success"


def canonical_5():
    """Session 15 fix verification (F-CP-INT-TYPE)."""
    print("\n=== c5: int invalid type='zzz' rejected (S15 fix) ===")
    res = int_mod.run(_build_ctx(
        _step_series(seed=46),
        params={"interventions": [{"index": 100, "type": "zzz", "name": "test"}]}), _null)
    if res.get("status") != "failure": return False
    err = res.get("error_message") or ""
    if "Unknown intervention type" not in err: return False
    print(f"  PASS: {err[:80]}")
    return True


def canonical_6():
    print("\n=== c6: int short series T=40 (graceful) ===")
    rng = np.random.default_rng(47)
    res = int_mod.run(_build_ctx(
        rng.standard_normal(40).tolist(),
        params={"interventions": [{"index": 20, "type": "step", "name": "test"}]}), _null)
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
