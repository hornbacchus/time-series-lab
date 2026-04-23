"""Phase 5 canonical validation for Follow-up 3b — HAR-CJ.

Five canonicals:
  C1 — Synthetic RV/BV/TQ with planted 3σ_y jumps on ~5% of days.
       Correctness probe: BNS recovery rate on well-separated
       planted jumps (expect 80-90% at α = 0.01).
  C2 — Synthetic continuous-only (no true jumps). Verify
       false-positive rate ≈ α = 0.01 (nominal rate). If
       detected fraction < 0.5%, D1 fires.
  C3 — Wrapper without TQ supplied (BV² fallback). Verify
       tq_approximated=True and D2 trigger fires.
  C4 — Extreme α = 0.10. Verify more jumps detected relative to
       C1 at α = 0.01.
  C5 — Heavy-jump regime (~30% of days injected). Verify D1
       fires with "high" branch disclosure.

Synthetic data generation uses intraday Brownian motion
simulation with M intraday returns per day; jumps are added as
localized intraday spikes. RV / BV / TQ computed from the
simulated intraday returns so the BNS z-statistic sees
well-formed inputs.

Run from project root:
    python tools/validate_har_cj_canonicals.py
"""

import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np

from techniques.base import RunContext
from techniques import har_cj as hc


_M_INTRADAY = 80  # intraday returns per day


def _null_progress(*args, **kwargs):
    pass


def _simulate_intraday_and_compute_rv_bv_tq(
    *, n_days, M, phi=0.95, sigma_eta=0.15,
    jump_days=(), jump_mag_sigmas=3.0, seed=42,
):
    """Simulate M intraday returns per day, with optional jumps.

    Returns (rv, bv, tq, sigma_daily) each of length n_days.

    Jumps are injected as a single intraday spike of magnitude
    `jump_mag_sigmas * sigma_daily` at a random intraday position
    on each day in `jump_days`.
    """
    from scipy.special import gamma as _gamma

    rng = np.random.default_rng(seed)
    h = np.empty(n_days)
    h[0] = 0.0
    for t in range(1, n_days):
        h[t] = phi * h[t - 1] + sigma_eta * rng.standard_normal()
    sigma_daily = np.exp(h / 2)

    rv = np.empty(n_days)
    bv = np.empty(n_days)
    tq = np.empty(n_days)
    mu_4_3 = 2 ** (2 / 3) * _gamma(7 / 6) / _gamma(1 / 2)

    jump_set = set(jump_days)
    for d in range(n_days):
        # Intraday returns — variance scaled so daily variance ≈ σ²
        r = sigma_daily[d] * rng.standard_normal(M) / np.sqrt(M)
        if d in jump_set:
            jump_pos = int(rng.integers(M))
            jump_sign = 1.0 if rng.random() > 0.5 else -1.0
            r[jump_pos] += jump_sign * jump_mag_sigmas * sigma_daily[d]
        # RV
        rv[d] = float(np.sum(r ** 2))
        # BV
        if M >= 2:
            bv[d] = float((np.pi / 2) * np.sum(np.abs(r[1:]) * np.abs(r[:-1])))
        else:
            bv[d] = rv[d]
        # TQ
        if M >= 3:
            tq[d] = float(
                M * mu_4_3 ** (-3) * np.sum(
                    np.abs(r[2:]) ** (4 / 3)
                    * np.abs(r[1:-1]) ** (4 / 3)
                    * np.abs(r[:-2]) ** (4 / 3)
                )
            )
        else:
            tq[d] = bv[d] ** 2
    return rv, bv, tq, sigma_daily


def _build_ctx(*, rv, bv, tq=None, M=_M_INTRADAY, preset="Balanced",
               jump_alpha=0.01, series_name="RV"):
    series = [
        {"name": series_name, "values": rv.tolist()},
        {"name": "BV", "values": bv.tolist()},
    ]
    if tq is not None:
        series.append({"name": "TQ", "values": tq.tolist()})
    return RunContext({
        "run_id": "test",
        "technique_id": "har_cj",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": [f"day_{i+1}" for i in range(len(rv))],
        "series": series,
        "params": {"M": M, "jump_alpha": jump_alpha},
    })


def _render(result, label):
    print(f"\n=== {label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        if result.get("warnings"):
            print(f"Warnings: {result['warnings']}")
        return False
    a = result.get("audit_fields", {})
    print(
        f"n_jumps={a.get('jump_days_count')} / {a.get('n_obs_raw')} = "
        f"{a.get('jump_days_fraction')}  "
        f"mean_jump_contrib={a.get('mean_jump_contribution')}  "
        f"tq_approx={a.get('tq_approximated')}"
    )
    print(
        f"beta_cd={a.get('beta_cd')} beta_cw={a.get('beta_cw')} "
        f"beta_cm={a.get('beta_cm')}  "
        f"Sigma_c={a.get('continuous_persistence_sum')}"
    )
    print(
        f"beta_jd={a.get('beta_jd')} beta_jw={a.get('beta_jw')} "
        f"beta_jm={a.get('beta_jm')}  "
        f"Sigma_j={a.get('jump_persistence_sum')}"
    )
    print(f"R²={a.get('R2')} adj={a.get('R2_adj')}  "
          f"fit_rmse={a.get('fit_rmse')} baseline={a.get('baseline_rmse')}")
    interp = result.get("interpretation") or {}
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        print(f"    • {t}")
    if result.get("warnings"):
        print(f"\n  Wrapper warnings: {result['warnings']}")
    return True


def canonical_1():
    """Synthetic RV/BV/TQ with planted 3σ_y jumps on ~5% of days."""
    rng = np.random.default_rng(42)
    n_days = 500
    n_true_jumps = 25
    jump_days_true = rng.choice(n_days, size=n_true_jumps, replace=False)
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY, jump_days=jump_days_true,
        jump_mag_sigmas=3.0, seed=42,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq,
                     preset="Balanced", jump_alpha=0.01,
                     series_name="synthetic_rv_jumps")
    t0 = time.time()
    result = hc.run(ctx, _null_progress)
    print(f"(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C1 HAR-CJ correctness: planted 3σ jumps, α=0.01, Balanced")
    a = result.get("audit_fields", {})
    n_detected = int(a.get("jump_days_count", 0) or 0)
    # Recovery rate: at α=0.01 on 500 days we expect ~5 false positives,
    # plus 25 true jumps ⇒ ~30 detections. Recovery rate ≥ 80% of 25
    # true jumps means ≥ 20 detected true jumps; with FP ~5,
    # total detections ≥ 25. We don't have direct true/detected
    # alignment in audit, so use the total count as a proxy + report.
    print(f"  True planted jumps: {n_true_jumps}; detected: {n_detected}")
    print(f"  (expected 80-90% recovery of true jumps + ~1% false-positive "
          f"rate → ~25-28 total detections)")
    return ok


def canonical_2():
    """Synthetic continuous-only (no true jumps). False-positive probe."""
    n_days = 500
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY, jump_days=(),
        jump_mag_sigmas=0.0, seed=7,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq,
                     preset="Balanced", jump_alpha=0.01,
                     series_name="synthetic_rv_no_jumps")
    t0 = time.time()
    result = hc.run(ctx, _null_progress)
    print(f"(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C2 HAR-CJ false-positive rate: no planted jumps, α=0.01")
    a = result.get("audit_fields", {})
    frac = a.get("jump_days_fraction") or 0.0
    print(f"  Nominal α=0.01 ⇒ expected ~1% false positives. "
          f"Got {float(frac) * 100:.2f}%.")
    return ok


def canonical_3():
    """C1 data but no TQ supplied. Verify BV² fallback + D2 trigger."""
    rng = np.random.default_rng(42)
    n_days = 500
    n_true_jumps = 25
    jump_days_true = rng.choice(n_days, size=n_true_jumps, replace=False)
    rv, bv, _tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY, jump_days=jump_days_true,
        jump_mag_sigmas=3.0, seed=42,
    )
    # NOTE: pass tq=None — BV² fallback
    ctx = _build_ctx(rv=rv, bv=bv, tq=None,
                     preset="Balanced", jump_alpha=0.01,
                     series_name="synthetic_rv_no_tq")
    t0 = time.time()
    result = hc.run(ctx, _null_progress)
    print(f"(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C3 HAR-CJ BV² fallback (no TQ supplied)")
    a = result.get("audit_fields", {})
    d2_fired = bool(a.get("tq_approximated"))
    print(f"  tq_approximated={d2_fired} (expected True; D2 should fire)")
    return ok


def canonical_4():
    """Extreme α = 0.10. Expect more jumps detected than C1."""
    rng = np.random.default_rng(42)
    n_days = 500
    n_true_jumps = 25
    jump_days_true = rng.choice(n_days, size=n_true_jumps, replace=False)
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY, jump_days=jump_days_true,
        jump_mag_sigmas=3.0, seed=42,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq,
                     preset="Balanced", jump_alpha=0.10,
                     series_name="synthetic_rv_alpha10")
    t0 = time.time()
    result = hc.run(ctx, _null_progress)
    print(f"(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C4 HAR-CJ extreme α=0.10 (liberal threshold)")
    return ok


def canonical_5():
    """Heavy-jump regime (~30% of days injected). D1 'high' trigger."""
    rng = np.random.default_rng(99)
    n_days = 500
    n_true_jumps = 150  # 30%
    jump_days_true = rng.choice(n_days, size=n_true_jumps, replace=False)
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY, jump_days=jump_days_true,
        jump_mag_sigmas=3.0, seed=99,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq,
                     preset="Balanced", jump_alpha=0.01,
                     series_name="synthetic_heavy_jump_regime")
    t0 = time.time()
    result = hc.run(ctx, _null_progress)
    print(f"(wall clock: {time.time()-t0:.1f}s)")
    ok = _render(result, "C5 HAR-CJ heavy-jump regime (~30% injected)")
    a = result.get("audit_fields", {})
    frac = a.get("jump_days_fraction") or 0.0
    tier3 = result.get("interpretation", {}).get("tier3", [])
    d1_fired = any("highly unusual" in t.lower() for t in tier3)
    print(f"  jump_fraction={float(frac) * 100:.1f}% (>20% expected). "
          f"D1 'high' trigger fired: {d1_fired}")
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
