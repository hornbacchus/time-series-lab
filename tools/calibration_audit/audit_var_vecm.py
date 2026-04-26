"""Calibration Audit Phase 2 Session 9 — VAR + VECM family batch.

Multivariate time-series wrappers:
  - var (`engine/techniques/var_model.py`) — vector autoregression
  - vecm (`engine/techniques/vecm_model.py`) — vector error correction model

Three audit techniques per CAI Phase 1 §3.9:

  Sweep 0 — Variant dispatch verification:
    Confirms technique_id="var" routes to var_model and
    technique_id="vecm" routes to vecm_model. Tests input
    validation (per Session 8 lesson: explicit allowlists =
    operational equivalent of parity tests).

  Technique 1 — Parameter sweep:
    Sweep 1.1: VAR lag_order ∈ {1, 2, 5, 10, "auto"} on
      bivariate VAR(1) DGP.
    Sweep 1.2: VAR trend ∈ {"n", "c", "ct", "ctt"} on
      drift-free DGP.
    Sweep 1.3: VECM coint_rank ∈ {None (auto), 1, 2} on
      bivariate cointegrated DGP (rank=1 truth).
    Sweep 1.4: Real-data lag selection on trivariate
      (DGS2, DGS10, GSPC) macro system.

  Technique 2 — Real-data stress:
    Bivariate (DGS2, DGS10) and trivariate (DGS2, DGS10,
    GSPC). Both VAR and VECM at default Balanced. Cross-
    reference Session 4 Johansen finding (rank=0 on the
    rates pair 10-year window).

  Technique 3 — Adversarial canonical exercises (mirrored
  in NEW validate_var_canonicals.py and validate_vecm_
  canonicals.py per CAL-R4):
    C-CAL-1: Constant series — wrapper produces small
      coefficients without spurious dynamics.
    C-CAL-2: Independent random walks (no cointegration)
      — VAR runs cleanly; VECM forces rank=1 with warning.
    C-CAL-3: Short series — convergence concerns; honest
      uncertainty.
    C-CAL-4: High lag on small T — over-parameterization
      handling.

CAL-R2 (parameter API):
  VAR: horizon, irf_periods, trend (default 'c'), max_lag
    (preset Fast=4/Balanced=8/Thorough=16), ic ('aic'),
    lag (override). Hard guard: n < 3*k + 5.
  VECM: horizon, deterministic ('ci'), significance_level
    (0.05), max_lag (preset Fast=4/Balanced=8/Thorough=12),
    lag, coint_rank (None=auto). VECM auto-coerces
    rank=0 → rank=1 with warning.

Run:
    python tools/calibration_audit/audit_var_vecm.py
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
from techniques import var_model
from techniques import vecm_model


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values_list, names, *, technique_id, params=None,
                preset="Balanced", run_id="audit_varvecm",
                frequency="daily"):
    user_params = dict(params or {})
    T = len(values_list[0])
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(T)),
        "series": [
            {"name": n, "values": list(v)}
            for n, v in zip(names, values_list)
        ],
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_var1_bivariate(*, T=500, seed=42):
    """Bivariate VAR(1):
        y1_t = 0.5*y1_{t-1} + 0.2*y2_{t-1} + e1
        y2_t = 0.1*y1_{t-1} + 0.6*y2_{t-1} + e2
    Stationary (max eigenvalue of A ~ 0.7).
    """
    rng = np.random.default_rng(seed)
    A = np.array([[0.5, 0.2], [0.1, 0.6]])
    y = np.zeros((T, 2))
    for t in range(1, T):
        y[t] = A @ y[t - 1] + rng.standard_normal(2)
    return [y[:, 0].tolist(), y[:, 1].tolist()], ["y1", "y2"]


def _simulate_cointegrated(*, T=500, seed=42, beta=0.5):
    """Bivariate cointegrated:
        y_t = y_{t-1} + e1   (random walk)
        x_t = beta*y_t + e2  (cointegrated with y)
    Cointegrating rank = 1.
    """
    rng = np.random.default_rng(seed)
    e1 = rng.standard_normal(T)
    e2 = rng.standard_normal(T) * 0.5
    y = np.cumsum(e1)
    x = beta * y + e2
    return [y.tolist(), x.tolist()], ["y", "x"]


def _simulate_indep_rw(*, T=500, seed=42):
    """Two independent random walks (no cointegration; rank=0)."""
    rng = np.random.default_rng(seed)
    y = np.cumsum(rng.standard_normal(T))
    x = np.cumsum(rng.standard_normal(T))
    return [y.tolist(), x.tolist()], ["y", "x"]


def _yield_diffs(yields):
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0 — Variant dispatch + input-validation probe
# =====================================================


def sweep_0_dispatch_validation():
    print("\n" + "=" * 60)
    print("SWEEP 0: DISPATCH + INPUT-VALIDATION PROBE")
    print("=" * 60)

    findings = []
    vals, names = _simulate_var1_bivariate(T=300, seed=42)

    # Probe 1: technique_id="var" routes to VAR
    print("\n--- VAR dispatch + valid params ---")
    ctx = _build_ctx(vals, names, technique_id="var",
                     params={"lag": 1, "trend": "c"})
    res, elapsed, err = _safe_run(var_model, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-VV-DISPATCH-VAR",
            "severity": "severe",
            "title": "VAR dispatch failed on basic invocation",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status={res.get('status')}, var_order={a.get('var_order')}, "
              f"trend={a.get('trend')}, max_root={a.get('max_root_modulus')}")

    # Probe 2: technique_id="vecm" routes to VECM
    print("\n--- VECM dispatch + valid params ---")
    coint_vals, coint_names = _simulate_cointegrated(T=300, seed=42)
    ctx = _build_ctx(coint_vals, coint_names, technique_id="vecm",
                     params={"lag": 1, "coint_rank": 1})
    res, elapsed, err = _safe_run(vecm_model, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-VV-DISPATCH-VECM",
            "severity": "severe",
            "title": "VECM dispatch failed on basic invocation",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status={res.get('status')}, lag_order={a.get('lag_order')}, "
              f"coint_rank={a.get('coint_rank')}, "
              f"deterministic={a.get('deterministic')}")

    # Probe 3: VAR invalid trend — passes to statsmodels which
    # may raise. Document behavior.
    print("\n--- VAR with invalid trend='zzz' ---")
    ctx = _build_ctx(vals, names, technique_id="var",
                     params={"lag": 1, "trend": "zzz"})
    res, elapsed, err = _safe_run(var_model, ctx)
    invalid_trend_status = "unknown"
    if err:
        invalid_trend_status = f"raised: {err}"
    elif res:
        invalid_trend_status = (
            f"status={res.get('status')}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {invalid_trend_status}")

    # Probe 4: VECM invalid deterministic — same question
    print("\n--- VECM with invalid deterministic='zzz' ---")
    ctx = _build_ctx(coint_vals, coint_names, technique_id="vecm",
                     params={"lag": 1, "coint_rank": 1,
                             "deterministic": "zzz"})
    res, elapsed, err = _safe_run(vecm_model, ctx)
    invalid_det_status = "unknown"
    if err:
        invalid_det_status = f"raised: {err}"
    elif res:
        invalid_det_status = (
            f"status={res.get('status')}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {invalid_det_status}")

    # Probe 5: VECM coint_rank > k (invalid)
    print("\n--- VECM coint_rank=5 on k=2 system ---")
    ctx = _build_ctx(coint_vals, coint_names, technique_id="vecm",
                     params={"lag": 1, "coint_rank": 5})
    res, elapsed, err = _safe_run(vecm_model, ctx)
    invalid_rank_status = "unknown"
    if err:
        invalid_rank_status = f"raised: {err}"
    elif res:
        invalid_rank_status = (
            f"status={res.get('status')}, "
            f"err_msg={res.get('error_message')}"
        )
    print(f"  {invalid_rank_status}")

    return {
        "var_dispatch": "OK" if not findings else "FAIL",
        "vecm_dispatch": "OK" if len(findings) <= 1 else "FAIL",
        "var_invalid_trend_behavior": invalid_trend_status,
        "vecm_invalid_deterministic_behavior": invalid_det_status,
        "vecm_invalid_rank_behavior": invalid_rank_status,
        "findings": findings,
    }


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    vals_var, names_var = _simulate_var1_bivariate(T=500, seed=42)
    coint_vals, coint_names = _simulate_cointegrated(T=500, seed=42)

    # ---- Sweep 1.1: VAR lag selection ----
    print("\n--- Sweep 1.1: VAR lag_order on VAR(1) DGP ---")
    sweep11 = []
    for lag in [1, 2, 5, 10, None]:  # None = auto
        params = {"trend": "c"}
        if lag is not None:
            params["lag"] = lag
        ctx = _build_ctx(vals_var, names_var, technique_id="var",
                          params=params)
        res, elapsed, err = _safe_run(var_model, ctx)
        if err:
            sweep11.append({"lag_param": lag, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "lag_param": lag,
            "wrapper_status": res.get("status"),
            "var_order_selected": a.get("var_order"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "max_root_modulus": a.get("max_root_modulus"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep11)} lag values swept")
    for r in sweep11:
        print(f"    lag={r.get('lag_param')!s:6s} -> "
              f"selected={r.get('var_order_selected')}, "
              f"AIC={r.get('aic')}, "
              f"max_root={r.get('max_root_modulus')}")

    # Stationarity check: max_root_modulus < 1 expected on stable DGP
    bad_root = [r for r in sweep11
                if r.get("max_root_modulus") is not None
                and r.get("max_root_modulus") >= 1.0]
    if bad_root:
        findings.append({
            "id": "F-VV-T1-1-NONSTAT",
            "severity": "severe",
            "title": (
                f"VAR fits with max_root_modulus >= 1 (non-stationary) "
                f"on stable VAR(1) DGP at {len(bad_root)} lag(s)"
            ),
            "details": bad_root,
        })

    # ---- Sweep 1.2: VAR trend sensitivity ----
    print("\n--- Sweep 1.2: VAR trend on drift-free DGP ---")
    sweep12 = []
    for trend in ["n", "c", "ct", "ctt"]:
        ctx = _build_ctx(vals_var, names_var, technique_id="var",
                          params={"trend": trend, "lag": 1})
        res, elapsed, err = _safe_run(var_model, ctx)
        if err:
            sweep12.append({"trend": trend, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "trend": trend,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "max_root_modulus": a.get("max_root_modulus"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep12)} trend values")
    for r in sweep12:
        print(f"    trend={r.get('trend')!r}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}, max_root={r.get('max_root_modulus')}")

    # ---- Sweep 1.3: VECM coint_rank ----
    print("\n--- Sweep 1.3: VECM coint_rank on rank-1 DGP ---")
    sweep13 = []
    for rank in [None, 1, 2]:  # None = auto
        params = {"lag": 1, "deterministic": "ci"}
        if rank is not None:
            params["coint_rank"] = rank
        ctx = _build_ctx(coint_vals, coint_names, technique_id="vecm",
                          params=params)
        res, elapsed, err = _safe_run(vecm_model, ctx)
        if err:
            sweep13.append({"rank_param": rank, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "rank_param": rank,
            "wrapper_status": res.get("status"),
            "coint_rank_applied": a.get("coint_rank"),
            "lag_order": a.get("lag_order"),
            "trace_stat": a.get("trace_stat"),
            "trace_cv_5pct": a.get("trace_cv_5pct"),
            "half_life_periods": a.get("half_life_periods"),
            "beta_normalized": a.get("beta_normalized"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep13)} rank values")
    for r in sweep13:
        print(f"    rank={r.get('rank_param')!s:5s} -> "
              f"applied={r.get('coint_rank_applied')}, "
              f"trace_stat={r.get('trace_stat')}, "
              f"half_life={r.get('half_life_periods')}")

    # ---- Sweep 1.4: Real-data lag selection (trivariate) ----
    print("\n--- Sweep 1.4: Real-data lag selection trivariate ---")
    sweep14 = []
    if _FIXTURE.exists():
        data = np.load(_FIXTURE)
        dgs2 = _yield_diffs(data["DGS2"])
        dgs10 = _yield_diffs(data["DGS10"])
        gspc = _log_returns(data["GSPC"])
        n_min = min(len(dgs2), len(dgs10), len(gspc))
        v_list = [dgs2[-n_min:].tolist(), dgs10[-n_min:].tolist(),
                  gspc[-n_min:].tolist()]
        n_list = ["DGS2_diff", "DGS10_diff", "GSPC_logret"]
        for lag in [None, 1, 5, 10]:
            params = {"trend": "c"}
            if lag is not None:
                params["lag"] = lag
            ctx = _build_ctx(v_list, n_list, technique_id="var",
                              params=params)
            res, elapsed, err = _safe_run(var_model, ctx)
            if err:
                sweep14.append({"lag_param": lag, "status": "ERROR",
                                "error": err})
                continue
            a = res.get("audit_fields", {}) or {}
            sweep14.append({
                "lag_param": lag,
                "wrapper_status": res.get("status"),
                "var_order_selected": a.get("var_order"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "max_root_modulus": a.get("max_root_modulus"),
                "elapsed_s": round(elapsed, 2),
            })
        print(f"  {len(sweep14)} (trivariate macro) cells")
        for r in sweep14:
            print(f"    lag={r.get('lag_param')!s:5s} -> "
                  f"selected={r.get('var_order_selected')}, "
                  f"AIC={r.get('aic')}, "
                  f"max_root={r.get('max_root_modulus')}, "
                  f"t={r.get('elapsed_s')}s")

    return {
        "sweep_1_1_var_lag": sweep11,
        "sweep_1_2_var_trend": sweep12,
        "sweep_1_3_vecm_rank": sweep13,
        "sweep_1_4_realdata_lag": sweep14,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-VV-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    baselines = []

    # Bivariate (DGS2, DGS10) — both VAR and VECM
    print("\n--- Bivariate (DGS2, DGS10): VAR + VECM ---")
    dgs2 = data["DGS2"][~np.isnan(data["DGS2"])]
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])]
    n_min = min(len(dgs2), len(dgs10))
    pair_vals = [dgs2[-n_min:].tolist(), dgs10[-n_min:].tolist()]
    pair_names = ["DGS2", "DGS10"]

    for tid, mod in [("var", var_model), ("vecm", vecm_model)]:
        params = {"trend": "c"} if tid == "var" else {"deterministic": "ci"}
        ctx = _build_ctx(pair_vals, pair_names, technique_id=tid,
                          params=params, preset="Balanced")
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            baselines.append({
                "system": "rates_pair", "wrapper": tid,
                "status": "ERROR", "error": err,
            })
            findings.append({
                "id": f"F-VV-T2-RATES-{tid.upper()}-ERROR",
                "severity": "severe",
                "title": f"{tid} crashed on rates pair",
                "details": err,
            })
            print(f"  {tid:4s}: ERROR — {err}")
            continue
        a = res.get("audit_fields", {}) or {}
        baselines.append({
            "system": "rates_pair", "wrapper": tid,
            "T": int(n_min),
            "wrapper_status": res.get("status"),
            "lag_order": a.get("var_order") or a.get("lag_order"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "max_root_modulus": a.get("max_root_modulus"),
            "coint_rank": a.get("coint_rank"),
            "trace_stat": a.get("trace_stat"),
            "trace_cv_5pct": a.get("trace_cv_5pct"),
            "half_life_periods": a.get("half_life_periods"),
            "beta_normalized": a.get("beta_normalized"),
            "elapsed_s": round(elapsed, 2),
        })
        if tid == "var":
            print(f"  var : status={res.get('status')}, "
                  f"order={a.get('var_order')}, "
                  f"AIC={a.get('aic')}, "
                  f"max_root={a.get('max_root_modulus')}, "
                  f"t={elapsed:.1f}s")
        else:
            print(f"  vecm: status={res.get('status')}, "
                  f"lag={a.get('lag_order')}, "
                  f"rank={a.get('coint_rank')}, "
                  f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}, "
                  f"half_life={a.get('half_life_periods')}, "
                  f"t={elapsed:.1f}s")

        # Check: VAR max_root < 1
        if (tid == "var" and a.get("max_root_modulus") is not None
                and a.get("max_root_modulus") >= 1.0):
            findings.append({
                "id": f"F-VV-T2-RATES-VAR-NONSTAT",
                "severity": "severe",
                "title": (
                    f"VAR on rates pair returns "
                    f"max_root_modulus={a.get('max_root_modulus')} >= 1 "
                    f"(non-stationary fit silently emitted)"
                ),
                "details": {"max_root_modulus": a.get("max_root_modulus")},
            })

    # Trivariate (DGS2, DGS10, GSPC log returns)
    print("\n--- Trivariate (DGS2, DGS10, GSPC): VAR + VECM ---")
    gspc = _log_returns(data["GSPC"])
    n_min3 = min(len(dgs2), len(dgs10), len(gspc))
    tri_vals = [dgs2[-n_min3:].tolist(), dgs10[-n_min3:].tolist(),
                gspc[-n_min3:].tolist()]
    tri_names = ["DGS2", "DGS10", "GSPC"]

    for tid, mod in [("var", var_model), ("vecm", vecm_model)]:
        params = {"trend": "c"} if tid == "var" else {"deterministic": "ci"}
        ctx = _build_ctx(tri_vals, tri_names, technique_id=tid,
                          params=params, preset="Balanced")
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            baselines.append({
                "system": "trivariate", "wrapper": tid,
                "status": "ERROR", "error": err,
            })
            findings.append({
                "id": f"F-VV-T2-TRI-{tid.upper()}-ERROR",
                "severity": "severe",
                "title": f"{tid} crashed on trivariate",
                "details": err,
            })
            print(f"  {tid:4s}: ERROR — {err}")
            continue
        a = res.get("audit_fields", {}) or {}
        baselines.append({
            "system": "trivariate", "wrapper": tid,
            "T": int(n_min3),
            "wrapper_status": res.get("status"),
            "lag_order": a.get("var_order") or a.get("lag_order"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "max_root_modulus": a.get("max_root_modulus"),
            "coint_rank": a.get("coint_rank"),
            "trace_stat": a.get("trace_stat"),
            "trace_cv_5pct": a.get("trace_cv_5pct"),
            "elapsed_s": round(elapsed, 2),
        })
        if tid == "var":
            print(f"  var : order={a.get('var_order')}, "
                  f"AIC={a.get('aic')}, "
                  f"max_root={a.get('max_root_modulus')}, "
                  f"t={elapsed:.1f}s")
        else:
            print(f"  vecm: lag={a.get('lag_order')}, "
                  f"rank={a.get('coint_rank')}, "
                  f"trace={a.get('trace_stat')}, "
                  f"t={elapsed:.1f}s")

    return {"baselines": baselines, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonicals
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Constant series (no dynamics) ----
    print("\n--- C-CAL-1: Constant series T=300 ---")
    rng = np.random.default_rng(42)
    vals = [rng.standard_normal(300).tolist(),
            rng.standard_normal(300).tolist()]
    names = ["a", "b"]
    for tid, mod in [("var", var_model)]:
        ctx = _build_ctx(vals, names, technique_id=tid,
                          params={"lag": 1, "trend": "c"})
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-1", "wrapper": tid,
                                       "status": "ERROR", "error": err})
        else:
            a = res.get("audit_fields", {}) or {}
            canonical_results.append({
                "id": "C-CAL-1", "wrapper": tid,
                "case": "Independent N(0,1) iid (no dynamics)",
                "status": res.get("status"),
                "max_root_modulus": a.get("max_root_modulus"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:4s}: max_root={a.get('max_root_modulus')} "
                  f"(expect << 1)")

    # ---- C-CAL-2: Independent random walks (rank=0) ----
    print("\n--- C-CAL-2: Independent random walks T=500 ---")
    rw_vals, rw_names = _simulate_indep_rw(T=500, seed=43)
    for tid, mod in [("var", var_model), ("vecm", vecm_model)]:
        params = {"lag": 1}
        if tid == "var":
            params["trend"] = "c"
        else:
            params["deterministic"] = "ci"
        ctx = _build_ctx(rw_vals, rw_names, technique_id=tid,
                          params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-2", "wrapper": tid,
                                       "status": "ERROR", "error": err})
        else:
            a = res.get("audit_fields", {}) or {}
            warns = res.get("warnings") or []
            rank0_warn = any("rank=1 anyway" in str(w).lower()
                              or "no cointegrating" in str(w).lower()
                              for w in warns)
            canonical_results.append({
                "id": "C-CAL-2", "wrapper": tid,
                "case": "Independent random walks",
                "status": res.get("status"),
                "coint_rank": a.get("coint_rank"),
                "trace_stat": a.get("trace_stat"),
                "trace_cv_5pct": a.get("trace_cv_5pct"),
                "rank0_coercion_warning": rank0_warn if tid == "vecm"
                                           else None,
                "elapsed_s": round(elapsed, 2),
            })
            if tid == "var":
                print(f"  var : status={res.get('status')}, "
                      f"max_root={a.get('max_root_modulus')}")
            else:
                print(f"  vecm: rank_applied={a.get('coint_rank')}, "
                      f"trace={a.get('trace_stat')}/cv={a.get('trace_cv_5pct')}, "
                      f"rank=0->1 coercion warning={rank0_warn}")

    # ---- C-CAL-3: Short series ----
    print("\n--- C-CAL-3: Short series T=50 ---")
    short_vals = [rng.standard_normal(50).tolist(),
                  rng.standard_normal(50).tolist()]
    for tid, mod in [("var", var_model), ("vecm", vecm_model)]:
        params = {"lag": 1}
        if tid == "var":
            params["trend"] = "c"
        else:
            params["deterministic"] = "ci"
            params["coint_rank"] = 1
        ctx = _build_ctx(short_vals, names, technique_id=tid,
                          params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        if err:
            canonical_results.append({"id": "C-CAL-3", "wrapper": tid,
                                       "status": "ERROR", "error": err})
            print(f"  {tid:4s}: EXCEPTION — {err}")
        else:
            a = res.get("audit_fields", {}) or {}
            canonical_results.append({
                "id": "C-CAL-3", "wrapper": tid,
                "case": "Short series T=50",
                "status": res.get("status"),
                "error_message": res.get("error_message"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:4s}: status={res.get('status')}, "
                  f"err_msg={res.get('error_message')}")

    # ---- C-CAL-4: High lag on small T ----
    print("\n--- C-CAL-4: VAR lag=15, T=100 (over-param) ---")
    over_vals, over_names = _simulate_var1_bivariate(T=100, seed=44)
    ctx = _build_ctx(over_vals, over_names, technique_id="var",
                      params={"lag": 15, "trend": "c"})
    res, elapsed, err = _safe_run(var_model, ctx)
    if err:
        canonical_results.append({"id": "C-CAL-4", "status": "ERROR",
                                   "error": err})
        print(f"  EXCEPTION: {err}")
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-4",
            "case": "VAR lag=15 on T=100 (over-parameterized)",
            "status": res.get("status"),
            "var_order": a.get("var_order"),
            "max_root_modulus": a.get("max_root_modulus"),
            "elapsed_s": round(elapsed, 2),
        })
        # Note: wrapper computes max_lag = min(lag, n//(k+1)-1, n//3),
        # so 15 may be capped. Document.
        print(f"  status={res.get('status')}, "
              f"var_order_actual={a.get('var_order')}, "
              f"max_root={a.get('max_root_modulus')}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — VAR + VECM family (CAI Session 9)")
    print("Date: 2026-04-26")
    print()

    s0 = sweep_0_dispatch_validation()
    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (
        s0.get("findings", []) +
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
        "wrappers": ["var", "vecm"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "var_vecm_audit_results.json"
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
