"""Calibration Audit Phase 2 Session 7 — har_rv.

Three audit techniques per CAI Phase 1 §3.7 + Session 7 plan:

  Technique 1 — Parameter sweep:
    Sweep 1.1: lag tuple sweep (daily, weekly, monthly).
      Defaults (1, 5, 22) per Corsi 2009 plus alternatives
      ((1,5,21), (1,7,30), (1,3,15)).
    Sweep 1.2: h_ahead forecast horizon ∈ {1, 5, 10, 22}.
    Sweep 1.3: use_log toggle (False / True).
    Sweep 1.4: T (sample-size) sweep ∈ {200, 500, 1000, 2000}.

  Technique 2 — Real-data stress test:
    3 macro series (matching Session 2 HAR-CJ protocol):
      GSPC, DGS10, DEXUSEU. Daily-only RV proxy
      (RV_t = r_t^2; 100*log returns scale).
    Cross-reference Session 2 HAR-CJ baselines on overlapping
    series — sanity check: HAR-RV without jump component
    should explain LESS variance than HAR-CJ on same data.
    If R^2 is HIGHER, that's a finding worth investigating.

  Technique 3 — Adversarial canonical extension:
    Add canonical_1..9 to NEW
    tools/validate_har_rv_canonicals.py (no prior canonicals
    existed for HAR-RV; Session 7 creates from scratch).

CAL-R2 (parameter API): wrapper params verified by inspecting
engine/techniques/har_rv.py (Corsi 2009 implementation):
  - daily_lag (int, default 1)
  - weekly_lag (int, default 5)
  - monthly_lag (int, default 22)
  - use_log (bool, default False)
  - h_ahead (int, default 1)
  Hard guard: n < monthly_lag + h_ahead + 10 returns error.

Run:
    python tools/calibration_audit/audit_har_rv.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import har_rv as hr_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, params=None, preset="Balanced",
                run_id="audit_har_rv", frequency="daily"):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": "har_rv",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "RV", "values": list(values)}],
        "params": user_params,
    })


def _safe_run(ctx):
    try:
        t0 = time.time()
        res = hr_mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_har_rv_path(*, n_days, phi=0.95, sigma_eta=0.15,
                            seed=42, with_jumps=False):
    """Synthetic intraday-Brownian-motion realized-volatility path.

    Mirrors the simulator in tools/validate_har_cj_canonicals.py
    minus the jump-detection-relevant BV/TQ components — HAR-RV
    only needs RV.
    """
    rng = np.random.default_rng(seed)
    M = 80  # intraday observations
    h = np.empty(n_days)
    h[0] = 0.0
    for t in range(1, n_days):
        h[t] = phi * h[t - 1] + sigma_eta * rng.standard_normal()
    sigma_daily = np.exp(h / 2)
    rv = np.empty(n_days)
    for d in range(n_days):
        r = sigma_daily[d] * rng.standard_normal(M) / np.sqrt(M)
        if with_jumps and rng.random() < 0.05:
            jump_pos = int(rng.integers(M))
            r[jump_pos] += 4.0 * sigma_daily[d]
        rv[d] = float(np.sum(r ** 2))
    return rv


def _daily_only_rv_proxy(prices):
    """Daily-only RV proxy (single-return-per-day): RV_t = r_t^2.

    Same convention as Session 2's audit_har_cj.py for cross-
    reference. Returns scaled to 100*log returns so RV magnitudes
    are interpretable as percent-squared.
    """
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    r = 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))
    return r ** 2


def _yield_rv_proxy(yields):
    """Daily-only RV proxy from yield differences."""
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    dy = np.diff(y)
    return dy ** 2


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    rv = _simulate_har_rv_path(n_days=800, seed=42)

    # ---- Sweep 1.1: lag tuple ----
    print("\n--- Sweep 1.1: (daily, weekly, monthly) lag tuples ---")
    sweep11 = []
    for label, (d, w, m) in [
        ("classic_(1,5,22)", (1, 5, 22)),
        ("calendar_(1,5,21)", (1, 5, 21)),
        ("longer_(1,7,30)", (1, 7, 30)),
        ("short_(1,3,15)", (1, 3, 15)),
    ]:
        ctx = _build_ctx(rv, params={
            "daily_lag": d, "weekly_lag": w, "monthly_lag": m,
        })
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep11.append({"label": label, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "label": label, "lags": (d, w, m),
            "wrapper_status": res.get("status"),
            "R2": a.get("R2"),
            "beta_d": a.get("beta_d"),
            "beta_w": a.get("beta_w"),
            "beta_m": a.get("beta_m"),
            "persistence_sum": a.get("persistence_sum"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep11)} lag tuples swept")
    for r in sweep11:
        print(f"    {r.get('label'):20s}: R2={r.get('R2')}, "
              f"beta_d={r.get('beta_d')}, "
              f"persist={r.get('persistence_sum')}")

    # ---- Sweep 1.2: h_ahead ----
    print("\n--- Sweep 1.2: h_ahead forecast horizon ---")
    sweep12 = []
    for h in [1, 5, 10, 22]:
        ctx = _build_ctx(rv, params={"h_ahead": h})
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep12.append({"h": h, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "h_ahead": h,
            "wrapper_status": res.get("status"),
            "R2": a.get("R2"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep12)} h_ahead values")
    for r in sweep12:
        print(f"    h={r.get('h_ahead')}: R2={r.get('R2')}")

    # ---- Sweep 1.3: use_log ----
    print("\n--- Sweep 1.3: use_log toggle ---")
    sweep13 = []
    for ul in [False, True]:
        ctx = _build_ctx(rv, params={"use_log": ul})
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep13.append({"use_log": ul, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "use_log": ul,
            "wrapper_status": res.get("status"),
            "R2": a.get("R2"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep13:
        print(f"    use_log={r.get('use_log')}: R2={r.get('R2')}")

    # ---- Sweep 1.4: T (sample size) ----
    print("\n--- Sweep 1.4: T (sample size) ---")
    sweep14 = []
    for T in [200, 500, 1000, 2000]:
        rv_T = _simulate_har_rv_path(n_days=T, seed=42)
        ctx = _build_ctx(rv_T)
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep14.append({"T": T, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep14.append({
            "T": T,
            "wrapper_status": res.get("status"),
            "R2": a.get("R2"),
            "persistence_sum": a.get("persistence_sum"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep14:
        print(f"    T={r.get('T')}: R2={r.get('R2')}, "
              f"persist={r.get('persistence_sum')}")

    return {
        "sweep_1_1_lags": sweep11,
        "sweep_1_2_h_ahead": sweep12,
        "sweep_1_3_use_log": sweep13,
        "sweep_1_4_T": sweep14,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress test
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS TEST")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-HR-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_specs = [
        ("GSPC", "log_returns"),
        ("DGS10", "yield_diffs"),
        ("DEXUSEU", "log_returns"),
    ]
    baselines = []
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        rv = (
            _daily_only_rv_proxy(raw) if prep == "log_returns"
            else _yield_rv_proxy(raw)
        )
        T = rv.size
        print(f"\n--- {sid} ({prep}, T={T}) ---")
        ctx = _build_ctx(rv, preset="Balanced")
        res, elapsed, err = _safe_run(ctx)
        if err:
            baselines.append({"series": sid, "T": T,
                              "status": "ERROR", "error": err})
            findings.append({
                "id": f"F-HR-T2-{sid}-ERROR",
                "severity": "severe",
                "title": f"Wrapper crashed on {sid}",
                "details": err,
            })
            continue
        if res.get("status") != "success":
            findings.append({
                "id": f"F-HR-T2-{sid}-NONSUCCESS",
                "severity": "severe",
                "title": f"Wrapper status={res.get('status')} on {sid}",
                "details": res.get("error_message"),
            })
        a = res.get("audit_fields", {}) or {}
        r2 = a.get("R2")
        baselines.append({
            "series": sid,
            "preprocessing": (
                "daily_only_proxy: RV=r^2 on 100*log returns"
                if prep == "log_returns"
                else "daily_only_proxy: RV=(diff yield)^2"
            ),
            "T": T,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
            "R2": r2,
            "R2_adj": a.get("R2_adj"),
            "beta_0": a.get("beta_0"),
            "beta_d": a.get("beta_d"),
            "beta_w": a.get("beta_w"),
            "beta_m": a.get("beta_m"),
            "persistence_sum": a.get("persistence_sum"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "fit_rmse": a.get("fit_rmse"),
            "baseline_rmse": a.get("baseline_rmse"),
            "ljung_box_lag10_pvalue": a.get("ljung_box_lag10_pvalue"),
        })
        print(f"  status={res.get('status')}, R2={r2}, "
              f"persist={a.get('persistence_sum')}, "
              f"beta_d={a.get('beta_d')}, beta_w={a.get('beta_w')}, "
              f"beta_m={a.get('beta_m')}, t={elapsed:.2f}s")

        # Plausibility checks
        if r2 is not None and (r2 < 0.0 or r2 > 1.0):
            findings.append({
                "id": f"F-HR-T2-{sid}-R2",
                "severity": "operational",
                "title": f"R2={r2} on {sid} outside [0, 1]",
                "details": {"R2": r2},
            })
        persist = a.get("persistence_sum")
        if persist is not None and persist > 1.05:
            findings.append({
                "id": f"F-HR-T2-{sid}-PERSIST",
                "severity": "operational",
                "title": (
                    f"persistence_sum={persist} > 1.05 on {sid}; "
                    f"non-stationary HAR-RV fit"
                ),
                "details": {"series": sid, "persistence_sum": persist},
            })
        if elapsed > 30.0:
            findings.append({
                "id": f"F-HR-T2-{sid}-SLOW",
                "severity": "operational",
                "title": f"Runtime {elapsed:.1f}s exceeds 30s budget",
                "details": {"series": sid, "T": T, "elapsed_s": elapsed},
            })

    return {"baselines": baselines, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonicals (in-process exercise)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1 (canonical_6): Constant volatility ----
    print("\n--- C-CAL-1 (canonical_6): Constant volatility T=500 ---")
    rng = np.random.default_rng(42)
    rv = (1e-2 + 1e-3 * rng.standard_normal(500) ** 2)
    ctx = _build_ctx(rv)
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-1", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-1",
            "case": "Constant variance (no temporal structure)",
            "status": res.get("status"),
            "R2": a.get("R2"),
            "persistence_sum": a.get("persistence_sum"),
            "beta_d": a.get("beta_d"),
            "beta_w": a.get("beta_w"),
            "beta_m": a.get("beta_m"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, R2={a.get('R2')}, "
              f"persistence_sum={a.get('persistence_sum')}, "
              f"beta_d={a.get('beta_d')}, beta_w={a.get('beta_w')}, "
              f"beta_m={a.get('beta_m')}")

    # ---- C-CAL-2 (canonical_7): With-jumps fixture ----
    print("\n--- C-CAL-2 (canonical_7): T=800 with frequent jumps ---")
    rv_jumps = _simulate_har_rv_path(n_days=800, seed=43,
                                       with_jumps=True)
    ctx = _build_ctx(rv_jumps)
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-2", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-2",
            "case": "With-jumps DGP; HAR-RV is jump-blind",
            "status": res.get("status"),
            "R2": a.get("R2"),
            "persistence_sum": a.get("persistence_sum"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, R2={a.get('R2')}, "
              f"persist={a.get('persistence_sum')}")

    # ---- C-CAL-3 (canonical_8): Short series T<200 ----
    print("\n--- C-CAL-3 (canonical_8): T=80 short series ---")
    rv_short = _simulate_har_rv_path(n_days=80, seed=44)
    ctx = _build_ctx(rv_short)
    res, elapsed, err = _safe_run(ctx)
    canonical_results.append({
        "id": "C-CAL-3",
        "case": "T=80 short series; tests hard-guard",
        "status": (res.get("status") if res else "ERROR"),
        "error_message": (
            res.get("error_message") if res
            and res.get("status") == "failure" else None
        ),
        "elapsed_s": round(elapsed, 2),
    })
    if err:
        print(f"  EXCEPTION: {err}")
    else:
        print(f"  status={res.get('status')}, "
              f"err_msg={res.get('error_message')}")

    # ---- C-CAL-4 (canonical_9): Tiny coefficients (B8 floor) ----
    print("\n--- C-CAL-4 (canonical_9): T=1500 white-noise RV "
          "(B8 rounding floor) ---")
    rng = np.random.default_rng(99)
    rv_wn = 1e-7 + 1e-3 * rng.standard_normal(1500) ** 2
    ctx = _build_ctx(rv_wn)
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-4", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        # Per B8 (Phase 1 audit): TSL har_rv rounds to 6 decimals
        # via round(value, 6). Tiny coefficients display as 0.0
        # even though OLS computation is at full FP precision.
        betas_displayed = {
            "beta_0": a.get("beta_0"),
            "beta_d": a.get("beta_d"),
            "beta_w": a.get("beta_w"),
            "beta_m": a.get("beta_m"),
        }
        all_below_floor = all(
            v is not None and abs(v) <= 1e-6
            for v in betas_displayed.values()
        )
        canonical_results.append({
            "id": "C-CAL-4",
            "case": "T=1500 white-noise RV (B8 6-decimal floor)",
            "status": res.get("status"),
            "R2": a.get("R2"),
            "betas_displayed": betas_displayed,
            "all_below_floor": all_below_floor,
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, R2={a.get('R2')}, "
              f"betas={betas_displayed}, "
              f"all_below_floor={all_below_floor}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings list
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — har_rv "
          "(CAI Session 7, second extension)")
    print("Date: 2026-04-26")
    print()

    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (
        t1.get("findings", []) +
        t2.get("findings", []) +
        t3.get("findings", []) +
        list(_EXTRA_FINDINGS)
    )
    by_sev = {"severe": 0, "operational": 0, "cosmetic": 0}
    for f in all_findings:
        by_sev[f.get("severity", "cosmetic")] = (
            by_sev.get(f.get("severity", "cosmetic"), 0) + 1
        )

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Severe:      {by_sev['severe']}")
    print(f"Operational: {by_sev['operational']}")
    print(f"Cosmetic:    {by_sev['cosmetic']}")
    print(f"Total:       {sum(by_sev.values())}")
    if all_findings:
        print("\nFindings:")
        for f in all_findings:
            print(f"  [{f['severity'].upper()}] {f['id']}: {f['title']}")

    results = {
        "date": "2026-04-26",
        "wrapper": "har_rv",
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "har_rv_audit_results.json"
    )

    def _coerce(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, dict):
            return {k: _coerce(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_coerce(v) for v in o]
        if isinstance(o, (bool, int, float, str, type(None))):
            return o
        return str(o)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_coerce(results), f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    return 1 if by_sev["severe"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
