"""Phase 5 canonical validation for Follow-up 3d — Johansen
finite-sample Bartlett correction (Reimers 1992 modified LR form).

Five canonicals:
  1. Synthetic cointegrated bivariate VAR at T = 120,
     `finite_sample_correction=False` — backward-compat baseline.
     Legacy D8 `_trigger_small_sample` does not fire (T >= 100);
     no 3d triggers.
  2. Same data, `finite_sample_correction=True` (critical test).
     Bartlett factor applied; Tier 1 closer renders only if rank
     flips; Declustering-analogue methodology block renders in
     Tier 2; Legacy D8 suppressed.
  3. Long sample T = 600, correction=True. Bartlett factor ~ 1.0;
     D2 suppressed (|1-factor| < 1%); no rank flip; validates
     Q4 large-T short-circuit.
  4. Very short sample T = 45, correction=True. D3
     `sample_size_below_threshold` fires (T < 50). Bartlett factor
     ~ 0.73-0.85 depending on auto-selected lag; may flip rank.
  5. Runtime-error monkey-patch of `_bartlett_factor`. Cascade
     catches; `finite_sample_correction_applied=False`;
     `fallback_reason` starts with `runtime_error`; D4 fires.

Run from project root:

    python tools/validate_johansen_finite_sample_canonicals.py
"""

import os
import sys
import time

# Windows cp1252 stdout can't encode Unicode (θ, σ, ξ, etc.).
# Reconfigure before any printing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np

from techniques.base import RunContext
from techniques import johansen_cointegration as jc


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(time_, names, values_list, *, preset, params,
               frequency="quarterly"):
    return RunContext({
        "run_id": "test",
        "technique_id": "johansen_cointegration",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_,
        "series": [
            {"name": names[i], "values": values_list[i]}
            for i in range(len(names))
        ],
        "params": params,
    })


def _synthetic_cointegrated_var(T, seed=42, beta=0.5, noise=0.5):
    """Generate a bivariate cointegrated VAR(1):
        y_t = y_{t-1} + eps_t       (I(1))
        x_t = beta * y_t + nu_t      (cointegrated with y at coef beta)
    Returns (time_labels, ['y', 'x'], [y_values, x_values]).
    """
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    nu = rng.standard_normal(T) * noise
    y = np.cumsum(eps)
    x = beta * y + nu
    time_ = [f"q_{i+1}" for i in range(T)]
    return time_, ["y", "x"], [y.tolist(), x.tolist()]


def _render(result, label):
    print(f"\n=== {label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    print(
        f"n_obs={a.get('n_observations')} k={a.get('n_variables')} "
        f"p={a.get('lag_order')} det={a.get('det_order')}"
    )
    print(
        f"trace_rank (uncorrected)={a.get('trace_rank')} "
        f"max_eig_rank (uncorrected)={a.get('max_eig_rank')} "
        f"tests_agree={a.get('tests_agree')}"
    )
    print(
        f"correction_requested={a.get('finite_sample_correction_requested')} "
        f"correction_applied={a.get('finite_sample_correction_applied')} "
        f"fallback_reason={a.get('finite_sample_correction_fallback_reason')}"
    )
    if a.get("finite_sample_correction_applied"):
        print(
            f"  bartlett_factor={a.get('bartlett_factor')} "
            f"pct_reduction={a.get('correction_pct_reduction')} "
            f"method={a.get('correction_method')}"
        )
        print(
            f"  trace_rank_corrected={a.get('trace_rank_corrected')} "
            f"max_eig_rank_corrected={a.get('max_eig_rank_corrected')} "
            f"impact_material={a.get('correction_impact_material')}"
        )
        print(
            f"  trace_stats pre ={a.get('trace_stat_at_decision')} "
            f"(cv={a.get('trace_cv_at_decision')})"
        )
        print(
            f"  trace_stats_c   ={a.get('trace_stat_corrected')}"
        )
        print(
            f"  max_eig_stats_c ={a.get('max_eig_stat_corrected')}"
        )
    # Output tables
    tables = result.get("tables") or []
    titles = [
        t.get("name", t.get("title", "?"))
        for t in tables if isinstance(t, dict)
    ]
    print(f"  Tables: {titles}")
    interp = result.get("interpretation") or {}
    tier1 = interp.get("tier1", "(missing)")
    tier2 = interp.get("tier2", "(missing)")
    print(f"\n  Tier 1: {tier1}")
    tier2_preview = tier2 if len(tier2) <= 500 else tier2[:500] + "..."
    print(f"\n  Tier 2: {tier2_preview}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        t_preview = t if len(t) <= 250 else t[:250] + "..."
        print(f"    \u2022 {t_preview}")
    return True


# ── Canonicals ─────────────────────────────────────────────────────


def canonical_1():
    """Synthetic cointegrated VAR at T = 120, correction=False."""
    time_, names, values = _synthetic_cointegrated_var(T=120, seed=42)
    t0 = time.time()
    ctx = _build_ctx(time_, names, values, preset="Balanced",
                     params={"det_order": 0})
    result = jc.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C1 Johansen T=120 synthetic VAR — correction=False")
    if ok:
        a = result.get("audit_fields", {})
        if a.get("finite_sample_correction_applied"):
            print("  !!! correction_applied=True unexpectedly")
            ok = False
        if a.get("bartlett_factor") is not None:
            print("  !!! bartlett_factor should be None on opt-out path")
            ok = False
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        legacy_fires = any("finite_sample_correction=True" in t for t in tier3)
        if a.get("n_observations", 0) < 100:
            if not legacy_fires:
                print("  ⚠ Legacy D8 trigger expected to fire on T<100")
        print(f"  Legacy small-sample trigger fires: {legacy_fires}")
    return ok


def canonical_2():
    """Synthetic cointegrated VAR at T = 120, correction=True."""
    time_, names, values = _synthetic_cointegrated_var(T=120, seed=42)
    t0 = time.time()
    ctx = _build_ctx(time_, names, values, preset="Balanced",
                     params={"det_order": 0,
                             "finite_sample_correction": True})
    result = jc.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C2 Johansen T=120 synthetic VAR — correction=True")
    if ok:
        a = result.get("audit_fields", {})
        if not a.get("finite_sample_correction_applied"):
            print("  !!! correction_applied=False unexpectedly")
            ok = False
        B = a.get("bartlett_factor")
        if B is None or not (0.0 < float(B) <= 1.0):
            print(f"  !!! bartlett_factor out of range: {B}")
            ok = False
        else:
            print(f"  ✓ bartlett_factor={B:.4f} in (0, 1]")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        legacy_suppressed = not any(
            "finite_sample_correction=True" in t for t in tier3
        )
        if legacy_suppressed:
            print("  ✓ Legacy D8 trigger suppressed when user opts in")
        else:
            print("  ⚠ Legacy D8 trigger still fires on opt-in path")
        tables = [
            t.get("name") for t in (result.get("tables") or [])
            if isinstance(t, dict)
        ]
        if "Finite-Sample Correction (Reimers 1992)" in tables:
            print("  ✓ Finite-Sample Correction table present")
        else:
            print(f"  ⚠ Correction table missing; tables: {tables}")
    return ok


def canonical_3():
    """Long sample T = 600 — Bartlett near 1.0, D2 suppressed."""
    time_, names, values = _synthetic_cointegrated_var(T=600, seed=1234)
    t0 = time.time()
    ctx = _build_ctx(time_, names, values, preset="Balanced",
                     params={"det_order": 0,
                             "finite_sample_correction": True})
    result = jc.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C3 Johansen T=600 — correction near-identity (Q4)")
    if ok:
        a = result.get("audit_fields", {})
        pct = a.get("correction_pct_reduction")
        if pct is None:
            print("  !!! pct_reduction None on applied correction")
            ok = False
        else:
            print(f"  pct_reduction={float(pct):.4f}")
            if float(pct) < 0.05:
                print("  ✓ Correction immaterial at large T (< 5% reduction)")
            else:
                print("  ⚠ Unexpectedly large reduction on T=600")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        d2_fires = any(
            "Reimers (1992) Bartlett-type correction reduces" in t
            and "stable" in t for t in tier3
        )
        if float(pct or 0.0) < 0.01:
            if not d2_fires:
                print("  ✓ D2 suppressed (|1-factor| < 1%) as Q4 specifies")
            else:
                print("  ⚠ D2 fired despite correction < 1% (Q4 violation)")
    return ok


def canonical_4():
    """Very short sample T = 45 — D3 fires (T < 50)."""
    time_, names, values = _synthetic_cointegrated_var(T=45, seed=5678)
    t0 = time.time()
    ctx = _build_ctx(time_, names, values, preset="Fast",
                     params={"det_order": 0,
                             "finite_sample_correction": True,
                             "lag": 1})
    result = jc.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C4 Johansen T=45 — D3 sample_size_below_threshold")
    if ok:
        a = result.get("audit_fields", {})
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        d3_fires = any(
            "very small" in t.lower() and
            ("cavaliere" in t.lower() or "t = 45" in t.lower())
            for t in tier3
        )
        if d3_fires:
            print("  ✓ D3 sample_size_below_threshold fires")
        else:
            print("  !!! D3 did NOT fire on T=45")
            ok = False
    return ok


def canonical_5():
    """Force-test D4 runtime-error fallback via monkey-patch."""
    time_, names, values = _synthetic_cointegrated_var(T=120, seed=42)

    orig_fn = jc._bartlett_factor

    def _failing(*args, **kwargs):
        raise RuntimeError(
            "Simulated Bartlett failure (Phase 5 D4 probe)"
        )

    jc._bartlett_factor = _failing
    try:
        t0 = time.time()
        ctx = _build_ctx(time_, names, values, preset="Balanced",
                         params={"det_order": 0,
                                 "finite_sample_correction": True})
        result = jc.run(ctx, _null_progress)
        print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    finally:
        jc._bartlett_factor = orig_fn

    ok = _render(result, "C5 Johansen force-failure — D4 runtime_error")
    if ok:
        a = result.get("audit_fields", {})
        if a.get("finite_sample_correction_applied"):
            print("  !!! correction_applied=True despite forced failure")
            return False
        reason = str(
            a.get("finite_sample_correction_fallback_reason") or ""
        )
        if not reason.startswith("runtime_error"):
            print(
                f"  !!! fallback_reason does not start with 'runtime_error': "
                f"{reason!r}"
            )
            return False
        print(f"  ✓ fallback_reason starts with 'runtime_error': {reason}")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        d4_fires = any(
            "runtime error" in t.lower() and "uncorrected" in t.lower()
            for t in tier3
        )
        if d4_fires:
            print("  ✓ D4 runtime-error trigger fires")
        else:
            print("  !!! D4 did not fire")
            return False
    return ok


# ─────────────────────────────────────────────────────────
# Calibration Audit Phase 2 Session 4 — adversarial canonicals
# C-CAL-1 .. C-CAL-4 per CAI Phase 1 §3.4 (numbered as
# canonical_6 .. canonical_9 per CAL-R4 numbering convention).
# Findings doc: docs/calibration_audit/
# johansen_findings_2026_04_26.md
# ─────────────────────────────────────────────────────────


def _synthetic_indep_random_walks(T, seed=43, noise=0.5):
    """Two independent random walks (no cointegration; rank=0)."""
    rng = np.random.default_rng(seed)
    y = np.cumsum(rng.standard_normal(T) * noise)
    x = np.cumsum(rng.standard_normal(T) * noise)
    time_ = [f"d_{i+1}" for i in range(T)]
    return time_, ["y", "x"], [y.tolist(), x.tolist()]


def _synthetic_triplet_rank2(T, seed=45):
    """3-variable system with rank=2 (one common stochastic trend)."""
    rng = np.random.default_rng(seed)
    z = np.cumsum(rng.standard_normal(T) * 0.5)
    y = z + rng.standard_normal(T) * 0.3
    x = 0.5 * z + rng.standard_normal(T) * 0.3
    time_ = [f"d_{i+1}" for i in range(T)]
    return time_, ["z", "y", "x"], [z.tolist(), y.tolist(), x.tolist()]


def _synthetic_near_unit_root(T, seed=44, phi_adj=0.98, noise=0.4):
    """Bivariate rank-1 with near-unit-root adjustment (slow ECM).

    The slow adjustment makes finite-sample inference much harder;
    this is the case where Reimers correction is theoretically most
    valuable.
    """
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T) * noise
    nu = rng.standard_normal(T) * noise
    y = np.cumsum(eps)
    x = np.zeros(T)
    for t in range(1, T):
        x[t] = phi_adj * x[t - 1] + (1 - phi_adj) * y[t] + nu[t]
    time_ = [f"d_{i+1}" for i in range(T)]
    return time_, ["y", "x"], [y.tolist(), x.tolist()]


def canonical_6():
    """C-CAL-1: Known rank-1 bivariate VAR T=500.

    DGP has no constant (y_t = y_{t-1} + eps_t; x_t = 0.5*y_t + nu_t),
    so canonical specifies det_order=-1 to match. Verifies wrapper
    correctly recovers rank=1 under correctly-specified deterministic
    structure.
    """
    print("\n" + "=" * 60)
    print("C-CAL-1 (canonical_6): Known rank-1 T=500, det_order=-1")
    print("=" * 60)
    time_, names, values = _synthetic_cointegrated_var(
        T=500, seed=42, beta=0.5,
    )
    ctx = _build_ctx(
        time_, names, values, preset="Balanced",
        params={"det_order": -1},
    )
    res = jc.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL: status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    rank = a.get("trace_rank")
    if rank != 1:
        print(f"  FAIL: trace_rank={rank}, expected 1")
        return False
    print(f"  PASS trace_rank={rank} (correctly specified det_order=-1)")
    return True


def canonical_7():
    """C-CAL-2: Two independent random walks T=500.

    Verifies wrapper does NOT spuriously detect cointegration. Rank
    must be 0 (false-positive control).
    """
    print("\n" + "=" * 60)
    print("C-CAL-2 (canonical_7): Two indep RW T=500")
    print("=" * 60)
    time_, names, values = _synthetic_indep_random_walks(
        T=500, seed=43,
    )
    ctx = _build_ctx(
        time_, names, values, preset="Balanced",
        params={"det_order": 0},
    )
    res = jc.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL: status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    rank = a.get("trace_rank")
    if rank != 0:
        print(f"  FAIL: trace_rank={rank}, expected 0 (no spurious detection)")
        return False
    print(f"  PASS trace_rank={rank} (no spurious detection)")
    return True


def canonical_8():
    """C-CAL-3: Near-unit-root small-sample T=80.

    Tests Reimers correction's small-sample value: with phi_adj=0.98
    (very slow ECM adjustment), finite-sample inference is hardest at
    T=80. Whether the correction changes the rank decision in this
    fixture depends on the realization; the canonical only verifies
    the wrapper runs cleanly under both fsc=False and fsc=True and
    produces a reasonable Bartlett factor when fsc=True.
    """
    print("\n" + "=" * 60)
    print("C-CAL-3 (canonical_8): Near-unit-root T=80 (Reimers test)")
    print("=" * 60)
    time_, names, values = _synthetic_near_unit_root(
        T=80, seed=44, phi_adj=0.98,
    )
    for fsc in [False, True]:
        ctx = _build_ctx(
            time_, names, values, preset="Balanced",
            params={"finite_sample_correction": fsc, "det_order": 0},
        )
        res = jc.run(ctx, _null_progress)
        if res.get("status") != "success":
            print(f"  FAIL fsc={fsc}: status={res.get('status')}")
            return False
        a = res.get("audit_fields", {}) or {}
        if fsc:
            bart = a.get("bartlett_factor")
            if bart is None or bart <= 0 or bart > 1.0:
                print(f"  FAIL fsc=True: bartlett_factor={bart} not in (0, 1]")
                return False
            print(f"  PASS fsc=True: bartlett={bart}, "
                  f"corrected_rank={a.get('trace_rank_corrected')}")
        else:
            print(f"  PASS fsc=False: trace_rank={a.get('trace_rank')}")
    return True


def canonical_9():
    """C-CAL-4: Triplet rank-2 T=500.

    3-variable system with one common stochastic trend → rank=2.
    DGP has no constant → det_order=-1. Verifies wrapper handles
    multi-rank cointegration correctly.
    """
    print("\n" + "=" * 60)
    print("C-CAL-4 (canonical_9): Triplet rank-2 T=500, det_order=-1")
    print("=" * 60)
    time_, names, values = _synthetic_triplet_rank2(T=500, seed=45)
    ctx = _build_ctx(
        time_, names, values, preset="Balanced",
        params={"det_order": -1},
    )
    res = jc.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL: status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    rank = a.get("trace_rank")
    if rank != 2:
        print(f"  FAIL: trace_rank={rank}, expected 2")
        return False
    print(f"  PASS trace_rank={rank}, max_eig_rank={a.get('max_eig_rank')}, "
          f"lag={a.get('lag_order')}")
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
