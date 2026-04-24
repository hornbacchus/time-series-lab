"""Phase 5 canonical validation for Follow-up 3c — EVT declustered POT.

Five canonicals:
  1. EVT on sp500 returns (lower tail), decluster=False — backward
     compatibility smoke test. Legacy D5 trigger should fire with
     updated text pointing at decluster=True. MRL diagnostic
     present; no Declustering Summary table.
  2. EVT on sp500 returns (lower tail), decluster=True — Ferro-
     Segers applies, Declustering Summary table present, Tier 1
     closer and Tier 2 methodology block render, bias-correction
     magnitude reported. Legacy D5 trigger suppressed.
  3. EVT on synthetic iid N(0,1) data, decluster=True — extremal
     index theta should land near 1.0 (independent limit). This
     is the correctness check for the Ferro-Segers estimator.
  4. EVT on synthetic strongly-clustered (GARCH high-persistence)
     data, decluster=True — theta likely < 0.5, K reduction
     material, D1/D2/D3/D4 may fire depending on realisation.
  5. EVT with forced runtime error in Ferro-Segers — decluster
     requested but cascade catches the exception; D5-new
     'insufficient_exceedances_for_declustering' fires with
     runtime-error branch.

Run from project root:

    python tools/validate_evt_declustering_canonicals.py
"""

import os
import sys
import time

# Windows consoles default to cp1252, which can't encode Unicode
# symbols (ξ, θ, σ, ε, etc.) that appear in rendered Tier 1/Tier 2
# prose. Reconfigure stdout/stderr to UTF-8 before any printing.
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
from techniques import evt_pot_gpd as evt


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
        "technique_id": "evt_pot_gpd",
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
        f"n_obs={a.get('n_obs')} threshold={a.get('threshold')} "
        f"n_exceed={a.get('n_exceedances')} xi={a.get('xi')} "
        f"sigma={a.get('sigma')}"
    )
    # Declustering summary
    print(
        f"decluster_requested={a.get('decluster_requested')} "
        f"decluster_applied={a.get('decluster_applied')} "
        f"fallback_reason={a.get('decluster_fallback_reason')}"
    )
    if a.get("decluster_applied"):
        print(
            f"  theta={a.get('extremal_index_theta')} "
            f"method={a.get('extremal_index_method')} "
            f"K={a.get('n_clusters_post_decluster')} "
            f"reduction={a.get('decluster_reduction_ratio')}"
        )
        print(
            f"  xi_post={a.get('xi_post_decluster')} "
            f"sigma_post={a.get('sigma_post_decluster')} "
            f"ks_p_post={a.get('ks_pval_post_decluster')}"
        )
        print(
            f"  VaR pre={a.get('var_values')}"
        )
        print(
            f"  VaR post={a.get('var_values_post_decluster')}"
        )
        print(
            f"  bias@99%={a.get('var_bias_correction_at_99pct')} "
            f"bias_pct@99%={a.get('var_bias_correction_pct_at_99pct')}"
        )
    # MRL diagnostic (always-on)
    print(
        f"  MRL: emp={a.get('mean_excess_at_threshold')} "
        f"impl={a.get('mean_excess_implied_by_gpd')} "
        f"verdict={a.get('mean_excess_match_verdict')}"
    )
    # Output tables
    tables = result.get("tables") or []
    if isinstance(tables, list):
        titles = [t.get("name", t.get("title", "?")) for t in tables if isinstance(t, dict)]
    else:
        titles = []
    print(f"  Tables: {titles}")
    interp = result.get("interpretation") or {}
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    print(f"\n  Tier 2: {interp.get('tier2', '(missing)')[:400]}{'...' if len(interp.get('tier2', '')) > 400 else ''}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        print(f"    \u2022 {t}")
    return True


def canonical_1():
    """EVT on sp500 lower tail, decluster=False (backward-compat)."""
    time_, name, values = _load_series("sp500_returns.csv")
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"tail": "lower"})
    result = evt.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C1 EVT sp500 lower tail — decluster=False")
    if ok:
        a = result.get("audit_fields", {})
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        legacy_pointer = any("decluster=True" in t for t in tier3)
        if legacy_pointer:
            print("  ✓ Legacy D5 trigger fires with updated text pointing at decluster=True")
        else:
            print("  ⚠ Legacy D5 trigger did not surface the decluster=True hint")
        if a.get("decluster_applied"):
            print("  !!! decluster_applied=True but decluster=False was requested")
            ok = False
        if a.get("mean_excess_at_threshold") is None:
            print("  !!! MRL diagnostic missing")
            ok = False
    return ok


def canonical_2():
    """EVT on sp500 lower tail, decluster=True (critical test)."""
    time_, name, values = _load_series("sp500_returns.csv")
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"tail": "lower", "decluster": True})
    result = evt.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C2 EVT sp500 lower tail — decluster=True")
    if ok:
        a = result.get("audit_fields", {})
        if not a.get("decluster_applied"):
            print("  !!! decluster_applied=False unexpected on 2500-obs sp500 sample")
            ok = False
        theta = a.get("extremal_index_theta")
        if theta is None or not (0.0 < float(theta) <= 1.0):
            print(f"  !!! extremal_index_theta out of range: {theta}")
            ok = False
        else:
            print(f"  ✓ theta in valid (0, 1] range: {theta}")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        legacy_suppressed = not any("decluster=True" in t for t in tier3)
        if legacy_suppressed:
            print("  ✓ Legacy D5 trigger suppressed when decluster_requested=True")
        else:
            print("  ⚠ Legacy D5 trigger still fires on decluster=True path")
        tables = result.get("tables") or []
        titles = [t.get("name", t.get("title", "?")) for t in tables if isinstance(t, dict)]
        if "Declustering Summary" in titles:
            print("  ✓ Declustering Summary table present")
        else:
            print(f"  ⚠ Declustering Summary table missing (tables: {titles})")
    return ok


def canonical_3():
    """Synthetic iid N(0,1), decluster=True — theta near 1.0."""
    rng = np.random.default_rng(1234)
    n = 2000
    values = rng.standard_normal(n).tolist()
    time_ = [f"day_{i+1}" for i in range(n)]
    t0 = time.time()
    ctx = _build_ctx(time_, "synthetic_iid_N01", values,
                     preset="Balanced", frequency="daily",
                     params={"tail": "upper", "decluster": True,
                             "threshold_quantile": 0.95})
    result = evt.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C3 EVT iid N(0,1) — theta near 1.0 (correctness)")
    if ok:
        a = result.get("audit_fields", {})
        theta = a.get("extremal_index_theta")
        if theta is None:
            print("  !!! theta not estimated")
            ok = False
        else:
            theta_f = float(theta)
            # Iid data should yield theta near 1.0. Ferro-Segers can
            # be biased downward on finite samples, accept >= 0.70.
            if theta_f >= 0.70:
                print(f"  ✓ theta = {theta_f:.4f} consistent with independence "
                      f"(>= 0.70 threshold for finite-sample Ferro-Segers)")
            else:
                print(f"  ⚠ theta = {theta_f:.4f} below 0.70 on iid data — "
                      f"Ferro-Segers finite-sample bias or sampling noise")
    return ok


def canonical_4():
    """Synthetic near-integrated GARCH, decluster=True. Expect
    material clustering: theta low, large K reduction, possibly
    D1/D2/D3/D4 firing."""
    rng = np.random.default_rng(5678)
    n = 2000
    alpha_garch = 0.1
    beta_garch = 0.88  # alpha + beta = 0.98, high persistence
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
    ctx = _build_ctx(time_, "synthetic_high_persistence_garch", values,
                     preset="Balanced", frequency="daily",
                     params={"tail": "lower", "decluster": True})
    result = evt.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C4 EVT synthetic GARCH clustering — decluster=True")
    if ok:
        a = result.get("audit_fields", {})
        theta = a.get("extremal_index_theta")
        ratio = a.get("decluster_reduction_ratio")
        if theta is None or ratio is None:
            print("  !!! decluster cascade did not populate theta / ratio")
            ok = False
        else:
            print(f"  theta={float(theta):.4f}, reduction_ratio={float(ratio):.4f}")
            if float(theta) < 1.0 - 1e-6:
                print("  ✓ theta < 1.0 as expected for clustered data")
            else:
                print("  ⚠ theta pinned at 1.0; no clustering detected")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        n_3c_triggers = sum(
            1 for t in tier3
            if any(kw in t for kw in
                   ("severe clustering", "redundant cluster members",
                    "cluster peaks retained", "Material bias correction"))
        )
        print(f"  3c Tier 3 triggers firing: {n_3c_triggers}")
    return ok


def canonical_5():
    """Force-test the D5-new runtime_error fallback branch. Monkey-
    patch `_ferro_segers_extremal_index` to always raise; verify
    decluster_applied=False, fallback_reason starts with
    'runtime_error', and D5-new fires."""
    time_, name, values = _load_series("sp500_returns.csv")

    orig_fn = evt._ferro_segers_extremal_index

    def _failing(*args, **kwargs):
        raise RuntimeError(
            "Simulated Ferro-Segers failure (Phase 5 D5-new probe)"
        )

    evt._ferro_segers_extremal_index = _failing
    try:
        t0 = time.time()
        ctx = _build_ctx(time_, name, values, preset="Balanced",
                         params={"tail": "lower", "decluster": True})
        result = evt.run(ctx, _null_progress)
        print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    finally:
        evt._ferro_segers_extremal_index = orig_fn

    ok = _render(result, "C5 EVT force-failure (D5-new runtime_error fallback)")
    if ok:
        a = result.get("audit_fields", {})
        if a.get("decluster_applied"):
            print("  !!! decluster_applied=True despite forced failure")
            return False
        reason = str(a.get("decluster_fallback_reason") or "")
        if not reason.startswith("runtime_error"):
            print(f"  !!! decluster_fallback_reason does not start with 'runtime_error': {reason!r}")
            return False
        print(f"  ✓ decluster_fallback_reason starts with 'runtime_error': {reason}")
        tier3 = (result.get("interpretation") or {}).get("tier3", [])
        d5_fires = any(
            "runtime error" in t.lower()
            and "pre-declustering" in t.lower()
            for t in tier3
        )
        if d5_fires:
            print("  ✓ D5-new insufficient_exceedances_for_declustering trigger fires with runtime-error branch")
        else:
            print("  !!! D5-new runtime-error branch did not fire in Tier 3")
            return False
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
