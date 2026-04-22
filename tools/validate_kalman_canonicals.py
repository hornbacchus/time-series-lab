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


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
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
