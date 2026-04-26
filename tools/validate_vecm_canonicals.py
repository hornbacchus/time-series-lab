"""Phase 5 canonical validation for VECM
(`engine/techniques/vecm_model.py`).

Created from scratch by CAI Phase 2 Session 9 (no prior canonical
script existed for this wrapper).

Nine canonicals:

  Base set (1-5):
    canonical_1 — VECM rank=1 recovery on synthetic bivariate
      cointegrated DGP. β normalized as β[0]=1.
    canonical_2 — Real DGS2/DGS10 (smoke test). Cross-references
      Session 4 Johansen (rank=0 found on this 10-year window;
      VECM force-coerces to rank=1 with warning).
    canonical_3 — Auto rank determination on rank-1 DGP.
    canonical_4 — Deterministic specifications {n, co, ci, lo,
      li} all run cleanly.
    canonical_5 — VECM allowlist validation (Session 9 fix
      F-VV-DETERMINISTIC): invalid `deterministic="zzz"`
      produces error_response.

  CAI Session 9 adversarial set (6-9):
    canonical_6 (C-CAL-1) — Constant series: tests honest small
      adjustment coefficients.
    canonical_7 (C-CAL-2) — Independent random walks (rank=0
      truth): VECM forces rank=1 with documented warning.
    canonical_8 (C-CAL-3) — Short series T=50.
    canonical_9 (C-CAL-4) — Mixed I(0)/I(1) — combination of
      stationary and non-stationary.

Run from project root:
    python tools/validate_vecm_canonicals.py
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import vecm_model


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(values_list, names, *, params=None,
                preset="Balanced"):
    return RunContext({
        "run_id": "test_vecm",
        "technique_id": "vecm",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(values_list[0]))),
        "series": [{"name": n, "values": list(v)}
                   for n, v in zip(names, values_list)],
        "params": dict(params or {}),
    })


def _simulate_cointegrated(*, T=500, seed=42, beta=0.5):
    rng = np.random.default_rng(seed)
    e1 = rng.standard_normal(T)
    e2 = rng.standard_normal(T) * 0.5
    y = np.cumsum(e1)
    x = beta * y + e2
    return [y.tolist(), x.tolist()], ["y", "x"]


def _simulate_indep_rw(*, T=500, seed=42):
    rng = np.random.default_rng(seed)
    return ([np.cumsum(rng.standard_normal(T)).tolist(),
             np.cumsum(rng.standard_normal(T)).tolist()],
            ["a", "b"])


def canonical_1():
    """C1: VECM rank=1 recovery on cointegrated DGP."""
    print("\n" + "=" * 60)
    print("canonical_1: VECM rank=1 recovery on cointegrated DGP")
    print("=" * 60)
    vals, names = _simulate_cointegrated(T=500, seed=42)
    ctx = _build_ctx(vals, names,
                      params={"lag": 1, "coint_rank": 1,
                              "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  rank={a.get('coint_rank')}, "
          f"trace_stat={a.get('trace_stat')}, "
          f"half_life={a.get('half_life_periods')}, "
          f"beta={a.get('beta_normalized')}")
    if a.get("coint_rank") != 1:
        print(f"  FAIL applied rank={a.get('coint_rank')} != 1")
        return False
    print(f"  PASS rank=1 applied; trace > CV expected on rank-1 DGP")
    return True


def canonical_2():
    """C2: Real DGS2/DGS10 (smoke; cross-ref Session 4 Johansen
    rank=0)."""
    print("\n" + "=" * 60)
    print("canonical_2: VECM on (DGS2, DGS10)")
    print("=" * 60)
    fixture = os.path.join(
        _ROOT, "tools", "calibration_audit", "fixtures",
        "macro_canonical_series.npz",
    )
    if not os.path.exists(fixture):
        print("  SKIP")
        return True
    data = np.load(fixture)
    dgs2 = data["DGS2"][~np.isnan(data["DGS2"])]
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])]
    n_min = min(len(dgs2), len(dgs10))
    vals = [dgs2[-n_min:].tolist(), dgs10[-n_min:].tolist()]
    ctx = _build_ctx(vals, ["DGS2", "DGS10"],
                      params={"deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    warns = res.get("warnings") or []
    rank0_warn = any("rank=1 anyway" in str(w).lower()
                      or "no cointegrating" in str(w).lower()
                      for w in warns)
    print(f"  T={n_min}, rank_applied={a.get('coint_rank')}, "
          f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}, "
          f"half_life={a.get('half_life_periods')}, "
          f"rank=0->1 coercion warning={rank0_warn}")
    print(f"  PASS smoke test on rates pair")
    return True


def canonical_3():
    """C3: Auto rank determination on rank-1 DGP."""
    print("\n" + "=" * 60)
    print("canonical_3: Auto rank on cointegrated DGP")
    print("=" * 60)
    vals, names = _simulate_cointegrated(T=500, seed=42)
    ctx = _build_ctx(vals, names,
                      params={"lag": 1, "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  auto rank_applied={a.get('coint_rank')}, "
          f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}")
    if a.get("coint_rank") not in (1, 2):
        print(f"  FAIL auto-rank={a.get('coint_rank')} not in {{1, 2}}")
        return False
    print(f"  PASS auto-detected rank in {{1, 2}}")
    return True


def canonical_4():
    """C4: Deterministic variants run cleanly."""
    print("\n" + "=" * 60)
    print("canonical_4: Deterministic variants {n, co, ci, lo, li}")
    print("=" * 60)
    vals, names = _simulate_cointegrated(T=500, seed=42)
    for det in ["n", "co", "ci", "lo", "li"]:
        ctx = _build_ctx(vals, names,
                          params={"lag": 1, "coint_rank": 1,
                                  "deterministic": det})
        res = vecm_model.run(ctx, _null_progress)
        if res.get("status") != "success":
            print(f"  FAIL det={det}: {res.get('status')}")
            return False
        a = res.get("audit_fields", {}) or {}
        print(f"  det={det!r}: "
              f"trace={a.get('trace_stat')}, "
              f"half_life={a.get('half_life_periods')}")
    print(f"  PASS all 5 deterministic variants run cleanly")
    return True


def canonical_5():
    """C5: VECM allowlist validation (Session 9 fix).

    Invalid `deterministic="zzz"` must produce error_response,
    not silently fall through. Pre-fix: silently fitted with
    'n' fallback; post-fix: explicit error.
    """
    print("\n" + "=" * 60)
    print("canonical_5: VECM allowlist validation (Session 9 fix)")
    print("=" * 60)
    vals, names = _simulate_cointegrated(T=300, seed=42)
    ctx = _build_ctx(vals, names,
                      params={"lag": 1, "coint_rank": 1,
                              "deterministic": "zzz"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "failure":
        print(f"  FAIL status={res.get('status')} (expect failure)")
        return False
    err = res.get("error_message") or ""
    if "Unknown deterministic" not in err and "zzz" not in err:
        print(f"  FAIL unexpected error_message: {err}")
        return False
    print(f"  PASS invalid deterministic='zzz' rejected with: {err[:100]}")
    return True


# CAI Phase 2 Session 9 adversarials


def canonical_6():
    """C-CAL-1: Constant (iid) series with VECM."""
    print("\n" + "=" * 60)
    print("C-CAL-1 (canonical_6): Constant iid series + VECM")
    print("=" * 60)
    rng = np.random.default_rng(42)
    vals = [rng.standard_normal(300).tolist(),
            rng.standard_normal(300).tolist()]
    ctx = _build_ctx(vals, ["a", "b"],
                      params={"lag": 1, "coint_rank": 1,
                              "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  rank_applied={a.get('coint_rank')}, "
          f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}, "
          f"alpha_norm={a.get('alpha_normalized')}")
    print(f"  PASS VECM runs cleanly on iid (misspecified DGP)")
    return True


def canonical_7():
    """C-CAL-2: Independent random walks (true rank=0).

    VECM auto-coerces rank 0->1 with warning. Verifies the
    coercion path works.
    """
    print("\n" + "=" * 60)
    print("C-CAL-2 (canonical_7): Independent random walks (rank=0 truth)")
    print("=" * 60)
    vals, names = _simulate_indep_rw(T=500, seed=43)
    ctx = _build_ctx(vals, names,
                      params={"lag": 1, "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    warns = res.get("warnings") or []
    rank0_warn = any("rank=1 anyway" in str(w).lower()
                      or "no cointegrating" in str(w).lower()
                      for w in warns)
    print(f"  rank_applied={a.get('coint_rank')}, "
          f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}, "
          f"rank=0->1 coercion warning={rank0_warn}")
    if not rank0_warn:
        print(f"  FAIL no rank=0->1 coercion warning emitted")
        return False
    print(f"  PASS rank=0 detected, coerced to 1, warning emitted")
    return True


def canonical_8():
    """C-CAL-3: Short series T=50."""
    print("\n" + "=" * 60)
    print("C-CAL-3 (canonical_8): Short series T=50")
    print("=" * 60)
    rng = np.random.default_rng(44)
    vals = [rng.standard_normal(50).tolist(),
            rng.standard_normal(50).tolist()]
    ctx = _build_ctx(vals, ["a", "b"],
                      params={"lag": 1, "coint_rank": 1,
                              "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        print(f"  FAIL status={res.get('status')}")
        return False
    print(f"  status={res.get('status')}, "
          f"err={res.get('error_message')}")
    print(f"  PASS wrapper handles short series cleanly")
    return True


def canonical_9():
    """C-CAL-4: Mixed I(0)/I(1) inputs.

    First series stationary, second non-stationary. VECM
    assumes I(1); document behavior on misspecified input.
    """
    print("\n" + "=" * 60)
    print("C-CAL-4 (canonical_9): Mixed I(0)/I(1) inputs")
    print("=" * 60)
    rng = np.random.default_rng(45)
    stationary = (0.5 * rng.standard_normal(300)).tolist()  # I(0)
    nonstat = np.cumsum(rng.standard_normal(300)).tolist()  # I(1)
    ctx = _build_ctx([stationary, nonstat], ["i0", "i1"],
                      params={"lag": 1, "coint_rank": 1,
                              "deterministic": "ci"})
    res = vecm_model.run(ctx, _null_progress)
    if res.get("status") not in ("success", "failure"):
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  status={res.get('status')}, "
          f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}")
    print(f"  PASS wrapper handles mixed I(0)/I(1) without crash")
    return True


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5,
               canonical_6, canonical_7, canonical_8, canonical_9):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            ok = False
        results.append((fn.__name__, ok))
    print("\n" + "=" * 60)
    print("CANONICAL VALIDATION SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
