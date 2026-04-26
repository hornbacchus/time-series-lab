"""Phase 5 canonical validation for Follow-up 2a.

Exercises all 6 canonicals from the plan:
  1. kalman_filter template=local_level on sp500_returns (Balanced)
  2. kalman_filter template=local_linear_trend on macro_var GDP (Balanced)
  3. kalman_filter template=seasonal on airline_passengers (Balanced, period=12)
  4. kalman_smoother template=local_level on sp500_returns (Balanced)
  5. kalman_smoother template=local_linear_trend on macro_var GDP (Balanced)
  6. kalman_filter template=custom on sp500_returns with user matrices (Fast)

Bonus: custom-path matrix-shape validation error (verifies ValueError
on mismatched shapes).

Run from the project root:
    python tools/validate_kalman_canonicals.py
"""

import os
import sys

# Reconfigure stdout/stderr for UTF-8 on Windows (Tier 2 prose
# contains Greek + math symbols: μ, ≤, ε that cp1252 can't
# encode). Pre-existing print failures surfaced during Phase 2
# Session 1 calibration audit (CAI). Same fix pattern as
# tools/parity_b7_h_latent_vs_stochvol.py and similar scripts.
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
from techniques import kalman_filter as kfilter_mod
from techniques import kalman_smoother as ksmoother_mod


SAMPLE_DIR = os.path.join(_ROOT, "resources", "sample_data")


def _null_progress(*args, **kwargs):
    pass


def _load_series(filename, col_idx=1):
    """Return (time_list, series_name, values) from a sample CSV."""
    df = pd.read_csv(os.path.join(SAMPLE_DIR, filename))
    time = df.iloc[:, 0].tolist()
    name = df.columns[col_idx]
    values = df.iloc[:, col_idx].tolist()
    return time, name, values


def _build_ctx(time, name, values, *, preset, params, frequency):
    raw = {
        "run_id": "test",
        "technique_id": "kalman_filter",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time,
        "series": [{"name": name, "values": values}],
        "params": params,
    }
    return RunContext(raw)


def _render_interp(result, case_label):
    interp = result.get("interpretation") or {}
    print(f"\n=== Canonical: {case_label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        return False
    audit = result.get("audit_fields", {})
    print(f"state_dim={audit.get('state_dim')} / "
          f"state_space_model={audit.get('state_space_model')} / "
          f"initialization={audit.get('initialization')}")
    print(f"llf={audit.get('log_likelihood')} "
          f"aic={audit.get('aic')} "
          f"bic={audit.get('bic')} "
          f"rmse={audit.get('rmse')} "
          f"baseline_rmse={audit.get('baseline_rmse')}")
    print(f"n_free_params={audit.get('n_free_params')} "
          f"converged={audit.get('converged')}")
    if audit.get("disturbance_smoother_computed") is not None:
        print(f"disturbance_smoother_computed={audit.get('disturbance_smoother_computed')}")
    if audit.get("custom_matrix_shapes"):
        print(f"custom_matrix_shapes={audit.get('custom_matrix_shapes')}")
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    print(f"\n  Tier 2: {interp.get('tier2', '(missing)')}")
    tier3 = interp.get("tier3") or []
    if tier3:
        print(f"\n  Tier 3 ({len(tier3)} trigger(s)):")
        for t in tier3:
            print(f"    • {t}")
    else:
        print("\n  Tier 3: (no triggers fired)")
    return True


def canonical_1():
    """kalman_filter template=local_level on sp500_returns (Balanced)."""
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(
        time, name, values, preset="Balanced",
        params={"state_space_model": "local_level", "horizon": 20},
        frequency="nyse_daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    return _render_interp(result, "C1 kalman_filter local_level sp500_returns Balanced")


def canonical_2():
    """kalman_filter template=local_linear_trend on macro_var GDP (Balanced)."""
    time, name, values = _load_series("macro_var.csv", col_idx=1)
    ctx = _build_ctx(
        time, name, values, preset="Balanced",
        params={"state_space_model": "local_linear_trend", "horizon": 20},
        frequency="Quarterly",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    return _render_interp(result, "C2 kalman_filter local_linear_trend macro_var GDP Balanced")


def canonical_3():
    """kalman_filter template=seasonal on airline_passengers (Balanced, period=12)."""
    time, name, values = _load_series("airline_passengers.csv")
    ctx = _build_ctx(
        time, name, values, preset="Balanced",
        params={"state_space_model": "seasonal",
                "seasonal_period": 12, "horizon": 20},
        frequency="Monthly",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    return _render_interp(result, "C3 kalman_filter seasonal airline_passengers Balanced (p=12)")


def canonical_4():
    """kalman_smoother template=local_level on sp500_returns (Balanced)."""
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(
        time, name, values, preset="Balanced",
        params={"state_space_model": "local_level", "horizon": 20},
        frequency="nyse_daily",
    )
    ctx.technique_id = "kalman_smoother"
    result = ksmoother_mod.run(ctx, _null_progress)
    return _render_interp(result, "C4 kalman_smoother local_level sp500_returns Balanced")


def canonical_5():
    """kalman_smoother template=local_linear_trend on macro_var GDP (Balanced)."""
    time, name, values = _load_series("macro_var.csv", col_idx=1)
    ctx = _build_ctx(
        time, name, values, preset="Balanced",
        params={"state_space_model": "local_linear_trend", "horizon": 20},
        frequency="Quarterly",
    )
    ctx.technique_id = "kalman_smoother"
    result = ksmoother_mod.run(ctx, _null_progress)
    return _render_interp(result, "C5 kalman_smoother local_linear_trend macro_var GDP Balanced")


def canonical_6():
    """kalman_filter custom matrices on sp500_returns (Fast).

    Simple AR(1) spec:
      s_t = 0.15 s_{t-1} + η_t   (AR(1) state with mean-reversion)
      y_t = s_t + ε_t
    """
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(
        time, name, values, preset="Fast",
        params={
            "state_space_model": "custom",
            "observation_matrix_Z": [[1.0]],
            "transition_matrix_T": [[0.15]],
            "process_noise_Q": [[1.1]],
            "observation_noise_H": [[0.0]],
            "initial_state": [0.048],
            "initial_covariance": [[1.0]],
            "horizon": 10,
        },
        frequency="nyse_daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    return _render_interp(result, "C6 kalman_filter custom sp500_returns Fast")


def bonus_shape_validation():
    """Verify informative ValueError on mismatched custom-path matrix shape."""
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(
        time, name, values, preset="Fast",
        params={
            "state_space_model": "custom",
            # Mismatched: Z is (1, 2) but T is (1, 1) — state_dim mismatch
            "observation_matrix_Z": [[1.0, 0.0]],
            "transition_matrix_T": [[0.15]],
            "process_noise_Q": [[1.1]],
            "observation_noise_H": [[0.0]],
            "initial_state": [0.048],
            "initial_covariance": [[1.0]],
        },
        frequency="nyse_daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    print("\n=== Bonus: custom-path shape validation ===")
    print(f"Status: {result.get('status')}")
    msg = result.get("error_message", "")
    print(f"Error message: {msg}")
    # Should mention the shape mismatch
    ok = "expected shape" in msg.lower() or "shape" in msg.lower()
    print(f"Validation OK (shape-mismatch message detected): {ok}")
    return ok


# ─────────────────────────────────────────────────────────
# Calibration Audit Phase 2 Session 1 — adversarial canonicals
# C-CAL-1 .. C-CAL-4 per CAI Phase 1 §3.1 (numbered as
# canonical_7 .. canonical_10 to match existing convention).
# Findings doc: docs/calibration_audit/kalman_findings_2026_04_25.md
# ─────────────────────────────────────────────────────────


def _generate_ar1(T, phi, sigma, seed):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    eps = rng.standard_normal(T) * sigma
    for t in range(1, T):
        y[t] = phi * y[t - 1] + eps[t]
    return y


def canonical_7():
    """C-CAL-1: T=5 minimum-viable series. Wrapper should reject
    gracefully with status=failure (not raise an unhandled
    exception). Establishes lower bound for stable Kalman
    estimation."""
    rng = np.random.default_rng(42)
    y = rng.standard_normal(5)
    ctx = _build_ctx(
        list(range(5)), "y", y.tolist(),
        preset="Balanced",
        params={"state_space_model": "local_level"},
        frequency="daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    print(f"\n=== Canonical: C-CAL-1 T=5 minimum-viable ===")
    print(f"Status: {result.get('status')}")
    if result.get("status") == "failure":
        print(f"Error message: {result.get('error_message')}")
        # Graceful failure is the expected behavior here.
        return True
    elif result.get("status") == "success":
        # Wrapper succeeded on T=5 — also acceptable.
        a = result.get("audit_fields", {})
        print(f"  log_lik={a.get('log_likelihood')}")
        return True
    return False


def canonical_8():
    """C-CAL-2: T=200 with 5% NaN gaps. Kalman filter is one of
    the canonical methods that handles missing observations
    gracefully (treated as missing data via standard Kalman
    update skip)."""
    y = _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=43)
    rng = np.random.default_rng(43)
    n_gaps = int(0.05 * 200)
    gap_idx = rng.choice(200, size=n_gaps, replace=False)
    y_gaps = y.copy()
    y_gaps[gap_idx] = np.nan
    ctx = _build_ctx(
        list(range(200)), "y", y_gaps.tolist(),
        preset="Balanced",
        params={"state_space_model": "local_level"},
        frequency="daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    print(f"\n=== Canonical: C-CAL-2 T=200 with 5% NaN gaps ===")
    print(f"Status: {result.get('status')}")
    if result.get("status") != "success":
        print(f"  Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    ll = a.get("log_likelihood")
    finite = ll is not None and np.isfinite(ll)
    print(f"  log_lik={ll}, finite={finite}")
    return finite


def canonical_9():
    """C-CAL-3: T=200 AR(1) with single 10sigma outlier injected
    at midpoint. Wrapper should produce finite log-likelihood
    despite the outlier (large prediction error in one step,
    but no NaN/Inf propagation)."""
    y = _generate_ar1(T=200, phi=0.7, sigma=1.0, seed=44)
    y_outlier = y.copy()
    y_outlier[100] = y_outlier[100] + 10.0 * float(y.std())
    ctx = _build_ctx(
        list(range(200)), "y", y_outlier.tolist(),
        preset="Balanced",
        params={"state_space_model": "local_level"},
        frequency="daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    print(f"\n=== Canonical: C-CAL-3 T=200 with 10sigma outlier at t=100 ===")
    print(f"Status: {result.get('status')}")
    if result.get("status") != "success":
        print(f"  Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    ll = a.get("log_likelihood")
    finite = ll is not None and np.isfinite(ll)
    print(f"  log_lik={ll}, finite={finite}")
    return finite


def canonical_10():
    """C-CAL-4: T=200 near-unit-root AR(1) (phi=0.99). Kalman
    filter should handle high-persistence dynamics without
    instability (no NaN/Inf log-likelihood)."""
    y = _generate_ar1(T=200, phi=0.99, sigma=1.0, seed=45)
    ctx = _build_ctx(
        list(range(200)), "y", y.tolist(),
        preset="Balanced",
        params={"state_space_model": "local_level"},
        frequency="daily",
    )
    result = kfilter_mod.run(ctx, _null_progress)
    print(f"\n=== Canonical: C-CAL-4 T=200 near-unit-root AR(1) phi=0.99 ===")
    print(f"Status: {result.get('status')}")
    if result.get("status") != "success":
        print(f"  Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    ll = a.get("log_likelihood")
    finite = ll is not None and np.isfinite(ll)
    print(f"  log_lik={ll}, finite={finite}")
    return finite


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6,
               canonical_7, canonical_8, canonical_9, canonical_10):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            ok = False
        results.append((fn.__name__, ok))
    bonus_ok = bonus_shape_validation()
    print("\n\n" + "=" * 60)
    print("CANONICAL VALIDATION SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    print(f"  {'PASS' if bonus_ok else 'FAIL'}: bonus_shape_validation")
    all_ok = all(ok for _, ok in results) and bonus_ok
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
