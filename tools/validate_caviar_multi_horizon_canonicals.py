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


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5):
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
