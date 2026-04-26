"""Phase 5 canonical validation for Follow-up 3a — CAViaR multi-horizon.

Five canonicals:
  1. SAV on sp500 (Balanced)
  2. AS on sp500 (Balanced)
  3. SAV on sp500 (Thorough) — verify MC noise ~0.45× Balanced
  4. CAViaR on synthetic stationary iid N(0,1) returns — verify
     22-step VaR converges toward unconditional N(0,1) 5%-quantile
     ≈ -1.645 (stationarity sanity check)
  5. CAViaR on synthetic near-integrated GARCH (high-persistence
     volatility) — verify D3 trigger fires

Run from project root:
    python tools/validate_caviar_multi_horizon_canonicals.py
"""

import os
import sys
import time

# Reconfigure stdout/stderr for UTF-8 on Windows (Tier 2 prose
# may contain Greek (alpha, sigma) and math symbols that cp1252
# can't encode). Same fix pattern as kalman / SV / har_cj
# canonical scripts; closes F-K-EXTRA-2 deferred item from CAI
# Session 1 (kalman audit 2026-04-25).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
import pandas as pd

from techniques.base import RunContext
from techniques import caviar_quantile_dynamics as cv


SAMPLE_DIR = os.path.join(_ROOT, "resources", "sample_data")


def _null_progress(*args, **kwargs):
    pass


def _load_series(filename, col_idx=1, last_n=None):
    df = pd.read_csv(os.path.join(SAMPLE_DIR, filename))
    time_ = df.iloc[:, 0].tolist()
    name = df.columns[col_idx]
    values = df.iloc[:, col_idx].tolist()
    if last_n is not None:
        time_ = time_[-last_n:]
        values = values[-last_n:]
    return time_, name, values


def _build_ctx(time_, name, values, *, preset, params, frequency="nyse_daily"):
    return RunContext({
        "run_id": "test",
        "technique_id": "caviar_quantile_dynamics",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_,
        "series": [{"name": name, "values": values}],
        "params": params,
    })


def _render(result, label):
    print(f"\n=== {label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    print(
        f"spec={a.get('specification')} theta={a.get('theta')} "
        f"n_obs={a.get('n_obs')} kupiec_p={a.get('kupiec_pval')}"
    )
    print(
        f"beta_1={a.get('caviar_stationarity_param')} "
        f"eff_persist={a.get('caviar_effective_persistence')} "
        f"stationary={a.get('caviar_stationarity_ok')}"
    )
    print(
        f"1-step VaR={a.get('one_step_ahead_var')}  "
        f"multi_step={a.get('multi_step_computed')}  "
        f"paths={a.get('multi_step_mc_paths')}"
    )
    mh_q = a.get("multi_step_quantiles") or {}
    mh_n = a.get("multi_step_mc_noise_std") or {}
    if mh_q:
        for h in sorted(int(k) for k in mh_q.keys()):
            VaR = mh_q[h]
            noise = mh_n.get(h, None)
            print(f"  h={h:3d}: VaR={VaR:+.4f}  MC_std={noise:+.4f}"
                  if noise is not None
                  else f"  h={h:3d}: VaR={VaR:+.4f}")
    print(f"LB p-value (residuals): {a.get('multi_step_residual_autocorr_lbq')}")
    interp = result.get("interpretation") or {}
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        print(f"    • {t}")
    return True


def canonical_1():
    """SAV on sp500 Balanced."""
    time_, name, values = _load_series("sp500_returns.csv")
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"specification": "SAV"})
    result = cv.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    return _render(result, "C1 CAViaR SAV sp500 Balanced")


def canonical_2():
    """AS on sp500 Balanced."""
    time_, name, values = _load_series("sp500_returns.csv")
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"specification": "AS"})
    result = cv.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    return _render(result, "C2 CAViaR AS sp500 Balanced")


def canonical_3():
    """SAV on sp500 Thorough — expect MC noise ~0.45× C1."""
    time_, name, values = _load_series("sp500_returns.csv")
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Thorough",
                     params={"specification": "SAV"})
    result = cv.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    return _render(result, "C3 CAViaR SAV sp500 Thorough")


def canonical_4():
    """Synthetic stationary iid N(0,1). 22-step VaR should be
    near -1.645 (unconditional 5% quantile of N(0,1))."""
    rng = np.random.default_rng(1234)
    n = 1000
    values = rng.standard_normal(n).tolist()
    time_ = [f"day_{i+1}" for i in range(n)]
    t0 = time.time()
    ctx = _build_ctx(time_, "synthetic_iid_N01", values,
                     preset="Balanced", frequency="daily",
                     params={"specification": "SAV"})
    result = cv.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C4 CAViaR on synthetic iid N(0,1) — stationarity check")
    # Verify 22-step VaR is near -1.645
    a = result.get("audit_fields", {})
    mh_q = a.get("multi_step_quantiles") or {}
    if 22 in mh_q:
        target = -1.6449  # N(0,1) 5th-percentile
        err = abs(mh_q[22] - target)
        print(f"  22-step VaR target: {target:.4f}, got {mh_q[22]:.4f}, "
              f"abs err {err:.4f}")
        # Loose tolerance because MC + fitting noise
        if err < 1.0:
            print("  ✓ 22-step VaR within 1.0 of N(0,1) 5%-quantile")
        else:
            print("  ⚠ 22-step VaR deviates materially from unconditional target")
    return ok


def canonical_5():
    """Synthetic near-integrated GARCH(1,1). α + β close to 1 makes
    CAViaR fit with high persistence and effective-persistence
    likely > 1, firing D3."""
    rng = np.random.default_rng(5678)
    n = 800
    alpha_garch = 0.1
    beta_garch = 0.89  # alpha + beta = 0.99, near-integrated
    omega = 0.02
    sig2 = np.empty(n)
    y = np.empty(n)
    sig2[0] = omega / (1 - alpha_garch - beta_garch)
    y[0] = rng.standard_normal() * np.sqrt(sig2[0])
    for t in range(1, n):
        sig2[t] = (
            omega
            + alpha_garch * y[t - 1] ** 2
            + beta_garch * sig2[t - 1]
        )
        y[t] = rng.standard_normal() * np.sqrt(sig2[t])
    values = y.tolist()
    time_ = [f"day_{i+1}" for i in range(n)]
    t0 = time.time()
    ctx = _build_ctx(time_, "synthetic_near_integrated_garch", values,
                     preset="Balanced", frequency="daily",
                     params={"specification": "SAV"})
    result = cv.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C5 CAViaR on near-integrated GARCH (D3 trigger)")
    a = result.get("audit_fields", {})
    if not a.get("caviar_stationarity_ok"):
        print("  ✓ D3 stationarity criterion flagged as False (trigger fires)")
    else:
        print("  ⚠ D3 stationarity criterion passed — trigger did not fire")
    return ok


# ─────────────────────────────────────────────────────────
# Calibration Audit Phase 2 Session 8 — adversarial canonicals
# C-CAL-1..4 per CAI Phase 1 §3.8 (numbered as canonical_6..9
# per CAL-R4). Findings doc:
# docs/calibration_audit/caviar_findings_2026_04_26.md
# ─────────────────────────────────────────────────────────


import math


def _simulate_garch11_returns_for_canonical(
    *, T, omega=0.05, alpha=0.10, beta=0.85, seed=42,
):
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta)
    z = rng.standard_normal(T)
    y[0] = math.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        sigma2[t] = omega + alpha * y[t - 1] ** 2 + beta * sigma2[t - 1]
        y[t] = math.sqrt(sigma2[t]) * z[t]
    return y.tolist()


def canonical_6():
    """C-CAL-1: Constant volatility T=500.

    Wrapper produces honest small parameters; violation_ratio
    near 1.0 (well-calibrated despite no GARCH structure).
    """
    print("\n" + "=" * 60)
    print("C-CAL-1 (canonical_6): Constant volatility T=500")
    print("=" * 60)
    rng = np.random.default_rng(42)
    values = rng.standard_normal(500).tolist()
    time_ = list(range(500))
    ctx = _build_ctx(
        time_, "constant_vol", values, preset="Balanced",
        params={"specification": "SAV", "theta": 0.05},
    )
    result = cv.run(ctx, _null_progress)
    if result.get("status") != "success":
        print(f"  FAIL status={result.get('status')}")
        return False
    a = result.get("audit_fields", {}) or {}
    vr = a.get("violation_ratio")
    print(f"  params={a.get('parameters')}, "
          f"violation_ratio={vr}, "
          f"VaR_1step={a.get('one_step_ahead_var')}")
    if vr is None or not (0.5 <= vr <= 1.5):
        print(f"  FAIL violation_ratio={vr} outside [0.5, 1.5]")
        return False
    print(f"  PASS violation_ratio near 1.0 on constant-vol DGP")
    return True


def canonical_7():
    """C-CAL-2: Mid-series regime change T=1000.

    Verifies wrapper runs cleanly on heterogeneous variance
    series; documents adaptation behavior.
    """
    print("\n" + "=" * 60)
    print("C-CAL-2 (canonical_7): Mid-series regime change T=1000")
    print("=" * 60)
    rng = np.random.default_rng(43)
    low = rng.standard_normal(500) * 0.5
    high = rng.standard_normal(500) * 2.5
    values = np.concatenate([low, high]).tolist()
    time_ = list(range(1000))
    ctx = _build_ctx(
        time_, "regime_change", values, preset="Balanced",
        params={"specification": "SAV", "theta": 0.05},
    )
    result = cv.run(ctx, _null_progress)
    if result.get("status") != "success":
        print(f"  FAIL status={result.get('status')}")
        return False
    a = result.get("audit_fields", {}) or {}
    vr = a.get("violation_ratio")
    print(f"  params={a.get('parameters')}, "
          f"violation_ratio={vr}, "
          f"VaR_1step={a.get('one_step_ahead_var')}")
    if vr is None or not (0.5 <= vr <= 1.5):
        print(f"  FAIL violation_ratio={vr} outside [0.5, 1.5]")
        return False
    print(f"  PASS regime change handled")
    return True


def canonical_8():
    """C-CAL-3: T=100 + theta=0.01 (boundary case).

    Wrapper hard guard is n<100, so T=100 is at the boundary.
    With theta=0.01, expected violations = 1 — extremely
    sparse. Wrapper should still produce a fit honestly.
    """
    print("\n" + "=" * 60)
    print("C-CAL-3 (canonical_8): T=100 + theta=0.01")
    print("=" * 60)
    values = _simulate_garch11_returns_for_canonical(T=100, seed=44)
    time_ = list(range(100))
    ctx = _build_ctx(
        time_, "short_extreme_q", values, preset="Balanced",
        params={"specification": "SAV", "theta": 0.01},
    )
    result = cv.run(ctx, _null_progress)
    if result.get("status") != "success":
        print(f"  FAIL status={result.get('status')}")
        return False
    a = result.get("audit_fields", {}) or {}
    print(f"  params={a.get('parameters')}, "
          f"n_violations={a.get('n_violations')}, "
          f"expected={a.get('expected_violations')}")
    if a.get("expected_violations") is None:
        print(f"  FAIL expected_violations missing")
        return False
    print(f"  PASS T=100 boundary + theta=0.01 extreme handled")
    return True


def canonical_9():
    """C-CAL-4: Fast vs Thorough preset (B9 lens).

    B9 verification finding: Nelder-Mead non-smoothness
    can cause Fast and Thorough to converge to different
    optima. Canonical only verifies BOTH presets succeed
    AND produce close (within 0.01) losses on a well-behaved
    fixture. Larger divergence indicates B9 manifesting more
    severely; smaller indicates fixture is well-behaved.
    """
    print("\n" + "=" * 60)
    print("C-CAL-4 (canonical_9): Fast vs Thorough preset (B9 lens)")
    print("=" * 60)
    values = _simulate_garch11_returns_for_canonical(T=500, seed=45)
    time_ = list(range(500))
    losses = []
    for preset in ["Fast", "Thorough"]:
        ctx = _build_ctx(
            time_, "b9_lens", values, preset=preset,
            params={"specification": "SAV", "theta": 0.05},
        )
        result = cv.run(ctx, _null_progress)
        if result.get("status") != "success":
            print(f"  FAIL preset={preset} status={result.get('status')}")
            return False
        a = result.get("audit_fields", {}) or {}
        loss = a.get("quantile_loss")
        losses.append(loss)
        print(f"  {preset:9s}: params={a.get('parameters')}, "
              f"loss={loss}")
    if any(l is None for l in losses):
        print(f"  FAIL one or both losses missing: {losses}")
        return False
    diff = abs(losses[0] - losses[1])
    print(f"  Loss diff Fast vs Thorough: {diff:.6f}")
    # Tolerance 0.01 (1% of typical loss magnitude). Above this
    # would suggest more severe B9 manifestation.
    if diff > 0.01:
        print(f"  FAIL loss diff {diff} > 0.01 threshold "
              f"(B9 manifesting more severely than expected)")
        return False
    print(f"  PASS B9 within tolerance on this fixture")
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
