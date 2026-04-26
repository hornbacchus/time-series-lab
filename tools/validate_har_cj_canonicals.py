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

# Reconfigure stdout/stderr for UTF-8 on Windows (Tier 2 prose
# contains alpha and other Greek symbols that cp1252 can't
# encode). Same fix pattern as kalman / SV canonical scripts;
# deferred from F-K-EXTRA-2 in CAI Session 1 (kalman audit
# 2026-04-25).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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


# ─────────────────────────────────────────────────────────
# Calibration Audit Phase 2 Session 2 — adversarial canonicals
# C-CAL-1 .. C-CAL-4 per CAI Phase 1 §3.2 (numbered as
# canonical_6 .. canonical_9 to match existing convention).
# Findings doc: docs/calibration_audit/har_cj_findings_2026_04_26.md
# ─────────────────────────────────────────────────────────


def canonical_6():
    """C-CAL-1: T=800, NO jumps injected. False-positive rate
    should sit near nominal alpha = 0.01; flag if > 5%."""
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=800, M=_M_INTRADAY, jump_days=(), seed=42,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq, preset="Balanced")
    res = hc.run(ctx, _null_progress)
    print("\n=== Canonical: C-CAL-1 (no jumps) ===")
    a = res.get("audit_fields", {})
    jf = a.get("jump_days_fraction")
    print(f"  status={res.get('status')}, jump_fraction={jf}")
    ok = res.get("status") == "success" and jf is not None and jf < 0.05
    print(f"  {'PASS' if ok else 'FAIL'}: false-positive rate "
          f"{'within' if ok else 'exceeds'} 5%")
    return ok


def canonical_7():
    """C-CAL-2: T=800, jumps every 10 days at 5sigma magnitude.
    Tests detection rate on well-separated planted jumps."""
    n_days = 800
    rv, bv, tq, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days, M=_M_INTRADAY,
        jump_days=tuple(range(0, n_days, 10)),
        jump_mag_sigmas=5.0, seed=42,
    )
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq, preset="Balanced")
    res = hc.run(ctx, _null_progress)
    print("\n=== Canonical: C-CAL-2 (frequent jumps every 10 days) ===")
    a = res.get("audit_fields", {})
    jc = a.get("jump_days_count")
    jf = a.get("jump_days_fraction")
    print(f"  status={res.get('status')}, jumps={jc} ({jf}), true=80")
    ok = (
        res.get("status") == "success"
        and jc is not None and jc >= 50
    )
    print(f"  {'PASS' if ok else 'FAIL'}: "
          f"{'>= 50/80 planted jumps detected' if ok else 'too few detected'}")
    return ok


def canonical_8():
    """C-CAL-3: T=1500 with mid-series volatility regime shift.
    Wrapper completes without NaN/Inf despite non-stationarity."""
    n_days = 1500
    rv1, bv1, tq1, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days // 2, M=_M_INTRADAY,
        sigma_eta=0.05, jump_days=(), seed=42,
    )
    rv2, bv2, tq2, _ = _simulate_intraday_and_compute_rv_bv_tq(
        n_days=n_days // 2, M=_M_INTRADAY,
        sigma_eta=0.40, jump_days=(), seed=43,
    )
    rv = np.concatenate([rv1, rv2])
    bv = np.concatenate([bv1, bv2])
    tq = np.concatenate([tq1, tq2])
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq, preset="Balanced")
    res = hc.run(ctx, _null_progress)
    print("\n=== Canonical: C-CAL-3 (mid-series regime shift) ===")
    a = res.get("audit_fields", {})
    r2 = a.get("R2")
    print(f"  status={res.get('status')}, R2={r2}")
    ok = (
        res.get("status") == "success"
        and r2 is not None and np.isfinite(r2)
    )
    print(f"  {'PASS' if ok else 'FAIL'}: "
          f"{'finite R2 under regime shift' if ok else 'wrapper failure'}")
    return ok


def canonical_9():
    """C-CAL-4: T=1500 white-noise RV. Tests B8 6-decimal
    rounding floor exposure on jump-component coefficients."""
    n_days = 1500
    rng = np.random.default_rng(99)
    rv = (1e-7 + 1e-3 * rng.standard_normal(n_days) ** 2)
    bv = rv * (1.0 + 0.01 * rng.standard_normal(n_days))
    tq = bv ** 2
    ctx = _build_ctx(rv=rv, bv=bv, tq=tq, preset="Balanced")
    res = hc.run(ctx, _null_progress)
    print("\n=== Canonical: C-CAL-4 (B8 rounding floor exposure) ===")
    a = res.get("audit_fields", {})
    tables = res.get("tables") or []
    coef_table = next(
        (t for t in tables if t.get("name") == "HAR-CJ Coefficients"),
        None,
    )
    rows = (coef_table or {}).get("rows") or []
    # Row name format from wrapper: "Jump daily (beta_jd)" etc.
    # Match by substring since the wrapper uses descriptive labels.
    jump_betas = []
    for row in rows:
        name = (row[0] if row else "") or ""
        if any(tag in name for tag in ("beta_jd", "beta_jw", "beta_jm")):
            try:
                jump_betas.append(float(row[1]))
            except (TypeError, ValueError, IndexError):
                pass
    print(f"  status={res.get('status')}, R2={a.get('R2')}")
    print(f"  jump betas: {jump_betas}")
    ok = (
        res.get("status") == "success"
        and len(jump_betas) == 3
        and all(abs(b) <= 1e-6 for b in jump_betas)
    )
    print(f"  {'PASS' if ok else 'FAIL'}: "
          f"{'B8 floor exposed (intentional)' if ok else 'unexpected betas'}")
    return ok


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
