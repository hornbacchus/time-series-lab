"""Calibration Audit Phase 2 Session 8 — caviar_quantile_dynamics.

Closes the original volatility/risk extension batch
(garch family / har_rv / caviar = 5 wrappers across Sessions
6-8).

Three audit techniques per CAI Phase 1 §3.8:

  Technique 1 — Parameter sweep:
    Sweep 1.1: specification ∈ {SAV, AS, IG} on synthetic
      GARCH(1,1) returns. Verifies each spec produces
      distinguishable beta dynamics (pre-validated by
      wrapper's explicit allowlist; no Sweep 0 dispatch
      concern).
    Sweep 1.2: theta (quantile level) ∈ {0.01, 0.025, 0.05,
      0.10}. Monotonic VaR scaling expected.
    Sweep 1.3: n_restarts sensitivity (B9 lens).
      Tests effective n_restarts ∈ {3 (Fast), 10 (Balanced),
      30 (Thorough)} via preset switching. Per B9 finding,
      Nelder-Mead on non-smooth quantile loss is start-
      sensitive; document the divergence pattern at default.
    Sweep 1.4: horizon scaling. Multi-step VaR at h ∈
      {1, 5, 10, 22}. Compares to sqrt(h) Gaussian baseline
      for context (CAViaR doesn't follow sqrt scaling
      strictly).

  Technique 2 — Real-data stress (5 macro series):
    GSPC, DGS10, DGS2, DEXUSEU, GOLD at default Balanced
    + theta=0.05 + SAV. Captures: beta, loss, one-step-
    ahead VaR, Kupiec/Christoffersen/DQ p-values, runtime.

  Technique 3 — Adversarial canonicals (4 cases, mirrored
  in tools/validate_caviar_multi_horizon_canonicals.py
  canonical_6..9 per CAL-R4):
    C-CAL-1: Constant volatility T=500 — beta should not
      exhibit material time-variation; VaR approximately
      constant.
    C-CAL-2: Mid-series regime change T=1000 (low-vol
      first half + high-vol second half) — does beta
      adapt? Document adaptation lag.
    C-CAL-3: Short series T=100 + extreme quantile
      theta=0.01 — wrapper's hard guard at n<100 OR
      adverse extreme-quantile behavior.
    C-CAL-4: Same fixture, two presets (Fast vs Thorough)
      — B9 exposure: Fast's n_restarts=3 may converge to
      different beta than Thorough's n_restarts=30. Not a
      bug per B9; documents the calibration concern.

CAL-R2 (parameter API): wrapper params verified by
inspecting engine/techniques/caviar_quantile_dynamics.py:
  - theta (float, default 0.05): quantile level in (0, 1)
  - specification (str, default "SAV"): {SAV, AS, IG}
  - horizons (list, parsed; default _DEFAULT_HORIZONS)
  - n_simulation_paths (int, preset-driven)
  Preset: Fast n_restarts=3, Balanced 10, Thorough 30.
  Hard guard: n < 100 returns error.

Run:
    python tools/calibration_audit/audit_caviar.py
"""

from __future__ import annotations

import json
import math
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
from techniques import caviar_quantile_dynamics as cv_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, params=None, preset="Balanced",
                run_id="audit_cv", frequency="daily"):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": "caviar_quantile_dynamics",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": user_params,
    })


def _safe_run(ctx):
    try:
        t0 = time.time()
        res = cv_mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_garch11_returns(*, T=500, omega=0.05, alpha=0.10,
                                beta=0.85, seed=42):
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta)
    z = rng.standard_normal(T)
    y[0] = math.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        sigma2[t] = omega + alpha * y[t - 1] ** 2 + beta * sigma2[t - 1]
        y[t] = math.sqrt(sigma2[t]) * z[t]
    return y


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


def _yield_diffs(yields):
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    y = _simulate_garch11_returns(T=500, seed=42)

    # ---- Sweep 1.1: specification ----
    print("\n--- Sweep 1.1: specification ∈ {SAV, AS, IG} ---")
    sweep11 = []
    for spec in ["SAV", "AS", "IG"]:
        ctx = _build_ctx(y, params={"specification": spec,
                                     "theta": 0.05})
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep11.append({"spec": spec, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "specification": spec,
            "wrapper_status": res.get("status"),
            "parameters": a.get("parameters"),
            "parameter_names": a.get("parameter_names"),
            "quantile_loss": a.get("quantile_loss"),
            "n_violations": a.get("n_violations"),
            "kupiec_pval": a.get("kupiec_pval"),
            "one_step_ahead_var": a.get("one_step_ahead_var"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep11)} specifications swept")
    for r in sweep11:
        print(f"    {r.get('specification'):4s}: "
              f"params={r.get('parameters')}, "
              f"loss={r.get('quantile_loss')}, "
              f"VaR_1step={r.get('one_step_ahead_var')}")

    # Verify each spec produces distinguishable betas
    if all(r.get("status") != "ERROR" for r in sweep11):
        params_by_spec = {r.get("specification"): r.get("parameters")
                          for r in sweep11}
        # Cross-spec check: SAV and AS use different parameter
        # structures (SAV has 3 params, AS has 4). IG also differs.
        # If any two specs return identical parameters, that's a
        # dispatch issue.
        try:
            sav = params_by_spec.get("SAV") or []
            as_p = params_by_spec.get("AS") or []
            ig = params_by_spec.get("IG") or []
            if (len(sav) == len(as_p)
                    and all(abs(s - a) < 1e-9
                             for s, a in zip(sav, as_p))):
                findings.append({
                    "id": "F-V-T1-DISPATCH-SAV-AS",
                    "severity": "severe",
                    "title": (
                        "SAV and AS specs produce identical parameters; "
                        "dispatch may not honor specification"
                    ),
                    "details": params_by_spec,
                })
        except Exception:
            pass

    # ---- Sweep 1.2: theta ----
    print("\n--- Sweep 1.2: theta (quantile level) ---")
    sweep12 = []
    for theta in [0.01, 0.025, 0.05, 0.10]:
        ctx = _build_ctx(y, params={"theta": theta,
                                     "specification": "SAV"})
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep12.append({"theta": theta, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "theta": theta,
            "wrapper_status": res.get("status"),
            "one_step_ahead_var": a.get("one_step_ahead_var"),
            "violation_ratio": a.get("violation_ratio"),
            "kupiec_pval": a.get("kupiec_pval"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep12)} theta values swept")
    for r in sweep12:
        print(f"    theta={r.get('theta')}: "
              f"VaR_1step={r.get('one_step_ahead_var')}, "
              f"violation_ratio={r.get('violation_ratio')}")
    # Monotonicity check: VaR (lower-tail) should become more
    # negative as theta decreases (tail gets fatter)
    var_values = [r.get("one_step_ahead_var") for r in sweep12
                  if r.get("one_step_ahead_var") is not None]
    if len(var_values) >= 2 and not all(
        var_values[i] <= var_values[i + 1]
        for i in range(len(var_values) - 1)
    ):
        findings.append({
            "id": "F-V-T1-VAR-MONOTONIC",
            "severity": "operational",
            "title": (
                "VaR not monotone in theta on synthetic GARCH "
                "fixture (lower theta should yield more-negative VaR)"
            ),
            "details": sweep12,
        })

    # ---- Sweep 1.3: n_restarts sensitivity (preset switch) ----
    print("\n--- Sweep 1.3: n_restarts sensitivity (B9 lens) ---")
    sweep13 = []
    for preset, n_r in [("Fast", 3), ("Balanced", 10),
                          ("Thorough", 30)]:
        ctx = _build_ctx(y, preset=preset,
                          params={"specification": "SAV",
                                  "theta": 0.05})
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep13.append({"preset": preset, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "preset": preset,
            "n_restarts": n_r,
            "parameters": a.get("parameters"),
            "quantile_loss": a.get("quantile_loss"),
            "one_step_ahead_var": a.get("one_step_ahead_var"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep13)} preset values")
    for r in sweep13:
        print(f"    {r.get('preset'):9s} (n_r={r.get('n_restarts'):2d}): "
              f"loss={r.get('quantile_loss')}, "
              f"VaR_1step={r.get('one_step_ahead_var')}, "
              f"params={r.get('parameters')}, "
              f"t={r.get('elapsed_s')}s")
    # B9 lens: are losses across presets within a tight band?
    losses = [r.get("quantile_loss") for r in sweep13
              if r.get("quantile_loss") is not None]
    if len(losses) >= 2:
        loss_range = max(losses) - min(losses)
        loss_pct = (
            loss_range / max(1e-12, min(losses)) if losses else 0.0
        )
        print(f"  Loss range across presets: "
              f"abs={loss_range:.6f}, pct={loss_pct:.4f}")
        if loss_pct > 0.10:
            # > 10% loss variation across presets is operational
            findings.append({
                "id": "F-V-T1-N-RESTARTS",
                "severity": "operational",
                "title": (
                    f"Loss varies {loss_pct:.2%} across presets — "
                    f"Fast preset's n_restarts=3 may converge to "
                    f"materially worse local optimum than Thorough's "
                    f"n_restarts=30 (B9 finding extension)"
                ),
                "details": sweep13,
            })

    # ---- Sweep 1.4: horizon scaling ----
    print("\n--- Sweep 1.4: horizon scaling ---")
    ctx = _build_ctx(y, params={"specification": "SAV",
                                 "theta": 0.05,
                                 "horizons": "1, 5, 10, 22"})
    res, elapsed, err = _safe_run(ctx)
    if err:
        sweep14 = {"status": "ERROR", "error": err}
    else:
        a = res.get("audit_fields", {}) or {}
        sweep14 = {
            "horizons": a.get("horizons_forecasted"),
            "multi_step_quantiles": a.get("multi_step_quantiles"),
            "multi_step_mc_noise_std":
                a.get("multi_step_mc_noise_std"),
            "elapsed_s": round(elapsed, 2),
        }
        print(f"  horizons={sweep14['horizons']}")
        print(f"  VaR by horizon: {sweep14['multi_step_quantiles']}")
        # Compute sqrt(h)-scaled comparison
        msq = sweep14.get("multi_step_quantiles") or {}
        if isinstance(msq, dict) and "1" in msq:
            try:
                v1 = float(msq["1"])
                print("  sqrt(h)-scaled VaR vs actual:")
                for h_str in ["5", "10", "22"]:
                    if h_str in msq:
                        actual = float(msq[h_str])
                        sqrt_h_scaled = v1 * math.sqrt(int(h_str))
                        print(f"    h={h_str}: actual={actual:.4f}, "
                              f"sqrt(h)-scaled={sqrt_h_scaled:.4f}, "
                              f"ratio={actual / sqrt_h_scaled:.3f}")
            except Exception:
                pass

    return {
        "sweep_1_1_specification": sweep11,
        "sweep_1_2_theta": sweep12,
        "sweep_1_3_n_restarts": sweep13,
        "sweep_1_4_horizon": sweep14,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (5 macro series)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-V-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_specs = [
        ("GSPC", "log_returns"),
        ("DGS10", "yield_diffs"),
        ("DGS2", "yield_diffs"),
        ("DEXUSEU", "log_returns"),
        ("GOLD", "log_returns"),
    ]
    baselines = []
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        preprocessed = (
            _log_returns(raw) if prep == "log_returns"
            else _yield_diffs(raw)
        )
        T = preprocessed.size
        # Subsample to last 1000 to keep runtime bounded
        if T > 1000:
            preprocessed = preprocessed[-1000:]
            T = 1000
        print(f"\n--- {sid} ({prep}, T={T}) ---")
        ctx = _build_ctx(
            preprocessed, preset="Balanced",
            params={"specification": "SAV", "theta": 0.05},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            baselines.append({"series": sid, "T": T,
                              "status": "ERROR", "error": err})
            findings.append({
                "id": f"F-V-T2-{sid}-ERROR",
                "severity": "severe",
                "title": f"Wrapper crashed on {sid}",
                "details": err,
            })
            continue
        if res.get("status") != "success":
            findings.append({
                "id": f"F-V-T2-{sid}-NONSUCCESS",
                "severity": "severe",
                "title": f"Wrapper status={res.get('status')} on {sid}",
                "details": res.get("error_message"),
            })
            baselines.append({"series": sid, "T": T,
                              "status": res.get("status")})
            continue
        a = res.get("audit_fields", {}) or {}
        baselines.append({
            "series": sid,
            "preprocessing": prep,
            "T": T,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
            "parameters": a.get("parameters"),
            "quantile_loss": a.get("quantile_loss"),
            "n_violations": a.get("n_violations"),
            "expected_violations": a.get("expected_violations"),
            "violation_ratio": a.get("violation_ratio"),
            "kupiec_pval": a.get("kupiec_pval"),
            "christoffersen_pval": a.get("christoffersen_pval"),
            "dq_pval": a.get("dq_pval"),
            "one_step_ahead_var": a.get("one_step_ahead_var"),
            "caviar_effective_persistence":
                a.get("caviar_effective_persistence"),
            "caviar_stationarity_ok": a.get("caviar_stationarity_ok"),
        })
        print(f"  status=success, params={a.get('parameters')}, "
              f"loss={a.get('quantile_loss')}, "
              f"VaR_1step={a.get('one_step_ahead_var')}")
        print(f"  Kupiec p={a.get('kupiec_pval')}, "
              f"Christoffersen p={a.get('christoffersen_pval')}, "
              f"DQ p={a.get('dq_pval')}, t={elapsed:.1f}s")

        # Plausibility: for theta=0.05 and 1000 obs, expected ~50
        # violations; violation_ratio should be near 1.0
        vr = a.get("violation_ratio")
        if vr is not None and (vr < 0.3 or vr > 3.0):
            findings.append({
                "id": f"F-V-T2-{sid}-VR",
                "severity": "operational",
                "title": (
                    f"violation_ratio={vr} far from 1.0 on {sid} "
                    f"(theta=0.05 nominal coverage)"
                ),
                "details": {"series": sid, "violation_ratio": vr},
            })
        if elapsed > 60.0:
            findings.append({
                "id": f"F-V-T2-{sid}-SLOW",
                "severity": "operational",
                "title": f"Runtime {elapsed:.1f}s exceeds 60s budget",
                "details": {"series": sid, "elapsed_s": elapsed},
            })

    return {"baselines": baselines, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonical exercises
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Constant volatility ----
    print("\n--- C-CAL-1 (canonical_6): Constant volatility T=500 ---")
    rng = np.random.default_rng(42)
    y = rng.standard_normal(500).tolist()
    ctx = _build_ctx(y, params={"specification": "SAV",
                                 "theta": 0.05})
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-1", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-1",
            "case": "Constant volatility (no GARCH effect) T=500",
            "status": res.get("status"),
            "parameters": a.get("parameters"),
            "quantile_loss": a.get("quantile_loss"),
            "violation_ratio": a.get("violation_ratio"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, "
              f"params={a.get('parameters')}, "
              f"VR={a.get('violation_ratio')}")

    # ---- C-CAL-2: Mid-series volatility regime change ----
    print("\n--- C-CAL-2 (canonical_7): Mid-series regime change T=1000 ---")
    rng = np.random.default_rng(43)
    low = rng.standard_normal(500) * 0.5
    high = rng.standard_normal(500) * 2.5
    y = np.concatenate([low, high]).tolist()
    ctx = _build_ctx(y, params={"specification": "SAV",
                                 "theta": 0.05})
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-2", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-2",
            "case": "Mid-series regime change low->high vol T=1000",
            "status": res.get("status"),
            "parameters": a.get("parameters"),
            "quantile_loss": a.get("quantile_loss"),
            "violation_ratio": a.get("violation_ratio"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, "
              f"params={a.get('parameters')}, "
              f"VR={a.get('violation_ratio')}")

    # ---- C-CAL-3: Short series + extreme quantile ----
    print("\n--- C-CAL-3 (canonical_8): T=100 + theta=0.01 (boundary) ---")
    y = _simulate_garch11_returns(T=100, seed=44).tolist()
    ctx = _build_ctx(y, params={"specification": "SAV",
                                 "theta": 0.01})
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-3", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-3",
            "case": "T=100 (just above guard) + extreme theta=0.01",
            "status": res.get("status"),
            "parameters": a.get("parameters"),
            "n_violations": a.get("n_violations"),
            "expected_violations": a.get("expected_violations"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, "
              f"params={a.get('parameters')}, "
              f"n_viol={a.get('n_violations')}, "
              f"expected={a.get('expected_violations')}")

    # ---- C-CAL-4: Fast vs Thorough preset (B9 exposure) ----
    print("\n--- C-CAL-4 (canonical_9): Fast vs Thorough preset ---")
    y = _simulate_garch11_returns(T=500, seed=45).tolist()
    fast_thorough = []
    for preset in ["Fast", "Thorough"]:
        ctx = _build_ctx(y, preset=preset,
                          params={"specification": "SAV",
                                  "theta": 0.05})
        res, elapsed, err = _safe_run(ctx)
        if err:
            fast_thorough.append({"preset": preset,
                                    "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        fast_thorough.append({
            "preset": preset,
            "n_restarts": a.get("n_restarts"),
            "parameters": a.get("parameters"),
            "quantile_loss": a.get("quantile_loss"),
            "elapsed_s": round(elapsed, 2),
        })
    canonical_results.append({
        "id": "C-CAL-4",
        "case": "B9 lens: Fast (n_restarts=3) vs Thorough (30)",
        "results": fast_thorough,
    })
    for r in fast_thorough:
        print(f"  {r.get('preset'):9s}: params={r.get('parameters')}, "
              f"loss={r.get('quantile_loss')}, "
              f"t={r.get('elapsed_s')}s")
    # Document loss divergence (this is B9 finding documented as
    # cosmetic in verification 3a; we surface but don't classify
    # severe)
    if len(fast_thorough) == 2 and all(
        r.get("quantile_loss") is not None for r in fast_thorough
    ):
        loss_diff = abs(
            fast_thorough[0]["quantile_loss"]
            - fast_thorough[1]["quantile_loss"]
        )
        if loss_diff > 0.001:
            findings.append({
                "id": "F-V-T3-4-B9",
                "severity": "cosmetic",
                "title": (
                    f"Fast vs Thorough preset losses differ by "
                    f"{loss_diff:.6f} (B9 documented behavior; "
                    f"Nelder-Mead non-smoothness; not a wrapper bug)"
                ),
                "details": fast_thorough,
            })

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings list
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — caviar_quantile_dynamics "
          "(CAI Session 8)")
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
        "wrapper": "caviar_quantile_dynamics",
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "caviar_audit_results.json"
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
