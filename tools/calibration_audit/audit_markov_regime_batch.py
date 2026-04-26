"""Calibration Audit Phase 2 Session 12 — Markov / Regime family batch.

Five wrappers in this batch:
  - hmm (`engine/techniques/hmm_model.py`; hmmlearn backend)
  - markov_switching (`engine/techniques/markov_switching.py`;
    statsmodels backend; also handles "markov_regression")
  - tar_setar (`engine/techniques/tar_setar.py`;
    handles "tar" + "setar")
  - star (`engine/techniques/star_model.py`; STAR variants)
  - nar_narx (`engine/techniques/nar_narx.py`;
    handles "nar" + "narx"; sklearn MLPRegressor backend)

Three audit techniques per CAI Phase 1 §3.12:

  Sweep 0 — Variant dispatch + input-validation matrix
  (priority per Sessions 9-10 precedents):
    Per-wrapper probes for invalid string-valued specs and
    invalid n_states/k_regimes/n_regimes values.

  Technique 1 — Parameter sweep (compact per-wrapper):
    HMM: n_components ∈ {2, 3} (kept compact; full sweep
      would balloon runtime)
    markov_switching: k_regimes ∈ {2, 3}
    tar_setar: n_regimes ∈ {2, 3}
    star: star_type ∈ {LSTAR, ESTAR}
    nar_narx: ar_lags ∈ {2, 5}

  Technique 2 — Real-data stress (subsampled to 500 obs):
    GSPC log returns + DGS10 yield levels for all 5 wrappers
    (reduced from 5 series to manage batch runtime)

  Technique 3 — Adversarial canonicals (4 cases, mirrored
  in 5 NEW canonical scripts per CAL-R4)

CAL-R2 (parameter API):
  hmm: n_components, covariance_type, n_iter, horizon
  markov_switching: k_regimes, order, switching_variance,
    switching_trend, horizon
  tar_setar: n_regimes, delay, trim, ar_order, thresholds,
    horizon
  star: ar_order, star_type ('LSTAR'/'ESTAR'/'both'), delay,
    horizon
  nar_narx: ar_lags, exog_lags, hidden_layers, activation,
    learning_rate_init, alpha, max_iter, horizon, cv_folds

Run:
    python tools/calibration_audit/audit_markov_regime_batch.py
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
from techniques import hmm_model
from techniques import markov_switching as ms_mod
from techniques import tar_setar as tar_mod
from techniques import star_model as star_mod
from techniques import nar_narx as nar_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_mr",
                frequency="daily", series_extra=None):
    user_params = dict(params or {})
    series = [{"name": "y", "values": list(values)}]
    if series_extra:
        for name, vals in series_extra:
            series.append({"name": name, "values": list(vals)})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": series,
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx, *, max_seconds=120):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        elapsed = time.time() - t0
        return res, elapsed, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_2regime_hmm(*, T=400, seed=42):
    """Synthetic 2-regime HMM-like fixture."""
    rng = np.random.default_rng(seed)
    # Regime 0: low vol N(0, 0.5); regime 1: high vol N(0, 2.0)
    states = np.zeros(T, dtype=int)
    P = np.array([[0.95, 0.05], [0.05, 0.95]])
    for t in range(1, T):
        states[t] = rng.choice(2, p=P[states[t - 1]])
    sigma = np.where(states == 0, 0.5, 2.0)
    y = sigma * rng.standard_normal(T)
    return y


def _simulate_threshold_ar(*, T=400, threshold=0.0, seed=42):
    """Synthetic 2-regime SETAR(1) DGP."""
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        if y[t - 1] < threshold:
            y[t] = -0.5 * y[t - 1] + rng.standard_normal()
        else:
            y[t] = 0.7 * y[t - 1] + rng.standard_normal()
    return y


def _simulate_smooth_transition(*, T=400, seed=42):
    """Synthetic LSTAR(1) DGP."""
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        # Smooth transition function on lagged y
        G = 1.0 / (1.0 + math.exp(-3.0 * (y[t - 1] - 0.0)))
        y[t] = (0.3 * y[t - 1] * (1 - G)
                + 0.8 * y[t - 1] * G
                + rng.standard_normal())
    return y


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0 — Dispatch + input-validation
# =====================================================


def sweep_0_dispatch_validation():
    print("\n" + "=" * 60)
    print("SWEEP 0: DISPATCH + INPUT-VALIDATION PROBE (5 wrappers)")
    print("=" * 60)

    findings = []
    y_hmm = _simulate_2regime_hmm(T=300, seed=42)
    y_thr = _simulate_threshold_ar(T=300, seed=42)
    y_lstar = _simulate_smooth_transition(T=300, seed=42)

    # ---- HMM baseline + invalid covariance_type ----
    print("\n--- HMM baseline ---")
    ctx = _build_ctx(y_hmm, technique_id="hmm",
                     params={"n_components": 2})
    res, elapsed, err = _safe_run(hmm_model, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-MR-HMM-BASELINE",
            "severity": "severe",
            "title": "HMM baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, n_components={a.get('n_components')}, "
              f"t={elapsed:.1f}s")

    print("\n--- HMM invalid covariance_type='zzz' ---")
    ctx = _build_ctx(y_hmm, technique_id="hmm",
                     params={"n_components": 2,
                             "covariance_type": "zzz"})
    res, elapsed, err = _safe_run(hmm_model, ctx)
    hmm_inv_cov = "unknown"
    if err:
        hmm_inv_cov = f"raised: {err[:100]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        hmm_inv_cov = (
            f"status={res.get('status')}, "
            f"audit_cov={a.get('covariance_type')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {hmm_inv_cov}")
    if (res and res.get("status") == "success"
            and (res.get("audit_fields") or {}).get("covariance_type")
                == "zzz"):
        findings.append({
            "id": "F-MR-HMM-COV",
            "severity": "severe",
            "title": (
                "HMM accepted invalid covariance_type='zzz' silently "
                "(Session 9-pattern)"
            ),
            "details": {"audit_covariance_type": "zzz"},
        })

    # ---- markov_switching baseline ----
    print("\n--- markov_switching baseline ---")
    ctx = _build_ctx(y_hmm, technique_id="markov_switching",
                     params={"k_regimes": 2})
    res, elapsed, err = _safe_run(ms_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-MR-MS-BASELINE",
            "severity": "severe",
            "title": "markov_switching baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, k_regimes={a.get('k_regimes')}, "
              f"t={elapsed:.1f}s")

    # ---- TAR/SETAR baseline + dispatch via technique_id ----
    print("\n--- tar_setar baseline (technique_id='setar') ---")
    ctx = _build_ctx(y_thr, technique_id="setar",
                     params={"n_regimes": 2})
    res, elapsed, err = _safe_run(tar_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-MR-TAR-BASELINE",
            "severity": "severe",
            "title": "tar_setar baseline (setar) failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, n_regimes={a.get('n_regimes')}, "
              f"t={elapsed:.1f}s")

    # ---- STAR baseline + invalid star_type ----
    print("\n--- star baseline (LSTAR) ---")
    ctx = _build_ctx(y_lstar, technique_id="star",
                     params={"star_type": "LSTAR", "ar_order": 1})
    res, elapsed, err = _safe_run(star_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-MR-STAR-BASELINE",
            "severity": "severe",
            "title": "star baseline (LSTAR) failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, star_type={a.get('star_type')}, "
              f"t={elapsed:.1f}s")

    print("\n--- star invalid star_type='zzz' ---")
    ctx = _build_ctx(y_lstar, technique_id="star",
                     params={"star_type": "zzz", "ar_order": 1})
    res, elapsed, err = _safe_run(star_mod, ctx)
    star_inv_type = "unknown"
    if err:
        star_inv_type = f"raised: {err[:100]}"
    elif res:
        a = res.get("audit_fields", {}) or {}
        star_inv_type = (
            f"status={res.get('status')}, "
            f"audit_star_type={a.get('star_type')!r}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {star_inv_type}")
    if (res and res.get("status") == "success"
            and str((res.get("audit_fields") or {}).get("star_type"))
                .upper() == "ZZZ"):
        findings.append({
            "id": "F-MR-STAR-TYPE",
            "severity": "severe",
            "title": (
                "star accepted invalid star_type='zzz' silently"
            ),
            "details": {"audit_star_type": "ZZZ"},
        })

    # ---- NAR/NARX baseline ----
    print("\n--- nar_narx baseline (technique_id='nar') ---")
    ctx = _build_ctx(y_thr, technique_id="nar",
                     params={"ar_lags": 2, "max_iter": 100})
    res, elapsed, err = _safe_run(nar_mod, ctx)
    if err or res is None or res.get("status") != "success":
        findings.append({
            "id": "F-MR-NAR-BASELINE",
            "severity": "severe",
            "title": "nar_narx baseline failed",
            "details": err or res.get("error_message"),
        })
    else:
        a = res.get("audit_fields", {}) or {}
        print(f"  status=success, t={elapsed:.1f}s")

    # ---- NAR/NARX with exogenous (NARX path) ----
    print("\n--- nar_narx NARX path (with exog) ---")
    rng = np.random.default_rng(43)
    x_exog = rng.standard_normal(300)
    ctx = _build_ctx(y_thr, technique_id="narx",
                     params={"ar_lags": 2, "max_iter": 100},
                     series_extra=[("x", x_exog)])
    res, elapsed, err = _safe_run(nar_mod, ctx)
    narx_status = "unknown"
    if err:
        narx_status = f"raised: {err[:100]}"
    elif res:
        narx_status = (
            f"status={res.get('status')}, "
            f"err={res.get('error_message')!s:.80s}"
        )
    print(f"  {narx_status}")

    return {
        "hmm_invalid_covariance": hmm_inv_cov,
        "star_invalid_type": star_inv_type,
        "narx_with_exog": narx_status,
        "findings": findings,
    }


# =====================================================
# Technique 1 — Parameter sweep (compact per-wrapper)
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP (compact)")
    print("=" * 60)

    findings = []
    y_hmm = _simulate_2regime_hmm(T=400, seed=42)
    y_thr = _simulate_threshold_ar(T=400, seed=42)
    y_lstar = _simulate_smooth_transition(T=400, seed=42)

    # ---- Sweep 1.1: HMM n_components ----
    print("\n--- Sweep 1.1: HMM n_components ---")
    sweep11 = []
    for n in [2, 3]:
        ctx = _build_ctx(y_hmm, technique_id="hmm",
                          params={"n_components": n})
        res, elapsed, err = _safe_run(hmm_model, ctx)
        if err:
            sweep11.append({"n": n, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep11.append({
            "n_components": n,
            "wrapper_status": res.get("status"),
            "log_likelihood": a.get("log_likelihood"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep11:
        print(f"    n={r.get('n_components')}: ll={r.get('log_likelihood')}, "
              f"AIC={r.get('aic')}, BIC={r.get('bic')}, "
              f"t={r.get('elapsed_s')}s")

    # ---- Sweep 1.2: markov_switching k_regimes ----
    print("\n--- Sweep 1.2: markov_switching k_regimes ---")
    sweep12 = []
    for k in [2, 3]:
        ctx = _build_ctx(y_hmm, technique_id="markov_switching",
                          params={"k_regimes": k})
        res, elapsed, err = _safe_run(ms_mod, ctx)
        if err:
            sweep12.append({"k": k, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep12.append({
            "k_regimes": k,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep12:
        print(f"    k={r.get('k_regimes')}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}, t={r.get('elapsed_s')}s")

    # ---- Sweep 1.3: tar_setar n_regimes ----
    print("\n--- Sweep 1.3: tar_setar n_regimes ---")
    sweep13 = []
    for n in [2, 3]:
        ctx = _build_ctx(y_thr, technique_id="setar",
                          params={"n_regimes": n})
        res, elapsed, err = _safe_run(tar_mod, ctx)
        if err:
            sweep13.append({"n": n, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep13.append({
            "n_regimes": n,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep13:
        print(f"    n={r.get('n_regimes')}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}")

    # ---- Sweep 1.4: STAR star_type (LSTAR vs ESTAR) ----
    print("\n--- Sweep 1.4: STAR star_type ---")
    sweep14 = []
    for st in ["LSTAR", "ESTAR"]:
        ctx = _build_ctx(y_lstar, technique_id="star",
                          params={"star_type": st, "ar_order": 1})
        res, elapsed, err = _safe_run(star_mod, ctx)
        if err:
            sweep14.append({"st": st, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep14.append({
            "star_type": st,
            "wrapper_status": res.get("status"),
            "aic": a.get("aic"),
            "bic": a.get("bic"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep14:
        print(f"    star_type={r.get('star_type')}: AIC={r.get('aic')}, "
              f"BIC={r.get('bic')}")

    # ---- Sweep 1.5: NAR ar_lags ----
    print("\n--- Sweep 1.5: NAR ar_lags ---")
    sweep15 = []
    for lags in [2, 5]:
        ctx = _build_ctx(y_thr, technique_id="nar",
                          params={"ar_lags": lags, "max_iter": 100})
        res, elapsed, err = _safe_run(nar_mod, ctx)
        if err:
            sweep15.append({"lags": lags, "status": "ERROR",
                            "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep15.append({
            "ar_lags": lags,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
        })
    for r in sweep15:
        print(f"    ar_lags={r.get('ar_lags')}: "
              f"status={r.get('wrapper_status')}, "
              f"t={r.get('elapsed_s')}s")

    return {
        "sweep_1_1_hmm_n": sweep11,
        "sweep_1_2_ms_k": sweep12,
        "sweep_1_3_tar_n": sweep13,
        "sweep_1_4_star_type": sweep14,
        "sweep_1_5_nar_lags": sweep15,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress (subsampled)
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (subsampled to T=500)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-MR-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_specs = [
        ("GSPC", "log_returns"),
        ("DGS10", "level"),
    ]
    cells = []
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        if prep == "log_returns":
            preprocessed = _log_returns(raw)
        else:
            preprocessed = raw[~np.isnan(raw)]
        if preprocessed.size > 500:
            preprocessed = preprocessed[-500:]
        T = preprocessed.size
        print(f"\n--- {sid} ({prep}, T={T}) ---")
        for tid, mod, params in [
            ("hmm", hmm_model, {"n_components": 2}),
            ("markov_switching", ms_mod, {"k_regimes": 2}),
            ("setar", tar_mod, {"n_regimes": 2}),
            ("star", star_mod,
             {"star_type": "LSTAR", "ar_order": 1}),
            ("nar", nar_mod, {"ar_lags": 2, "max_iter": 100}),
        ]:
            ctx = _build_ctx(preprocessed, technique_id=tid,
                              params=params, preset="Balanced")
            res, elapsed, err = _safe_run(mod, ctx)
            if err:
                cells.append({"series": sid, "wrapper": tid,
                              "status": "ERROR", "error": err[:120]})
                findings.append({
                    "id": f"F-MR-T2-{sid}-{tid.upper()}-ERROR",
                    "severity": "severe",
                    "title": f"{tid} crashed on {sid}",
                    "details": err[:200],
                })
                print(f"  {tid:18s}: ERROR — {err[:80]}")
                continue
            if res.get("status") != "success":
                findings.append({
                    "id": f"F-MR-T2-{sid}-{tid.upper()}-NONSUCCESS",
                    "severity": "operational",
                    "title": f"{tid} status={res.get('status')} on {sid}",
                    "details": res.get("error_message"),
                })
            a = res.get("audit_fields", {}) or {}
            cells.append({
                "series": sid, "wrapper": tid, "T": T,
                "wrapper_status": res.get("status"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "elapsed_s": round(elapsed, 2),
            })
            print(f"  {tid:18s}: status={res.get('status')}, "
                  f"AIC={a.get('aic')}, t={elapsed:.1f}s")
            if elapsed > 60.0:
                findings.append({
                    "id": f"F-MR-T2-{sid}-{tid.upper()}-SLOW",
                    "severity": "operational",
                    "title": f"{tid} runtime {elapsed:.1f}s on {sid}",
                    "details": {"series": sid, "elapsed_s": elapsed},
                })

    return {"baselines": cells, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonical exercises
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Constant series ----
    print("\n--- C-CAL-1: Constant series y=5.0 T=200 ---")
    y_const = np.full(200, 5.0)
    for tid, mod, params in [
        ("hmm", hmm_model, {"n_components": 2}),
        ("markov_switching", ms_mod, {"k_regimes": 2}),
        ("setar", tar_mod, {"n_regimes": 2}),
        ("star", star_mod, {"star_type": "LSTAR", "ar_order": 1}),
        ("nar", nar_mod, {"ar_lags": 2, "max_iter": 50}),
    ]:
        ctx = _build_ctx(y_const, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-1", "wrapper": tid,
            "case": "constant series",
            "status": (res.get("status") if res else "ERROR"),
            "error_message": (
                res.get("error_message") if res else err[:120]
            ),
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:18s}: status={s}")

    # ---- C-CAL-2: Pathological 2-regime DGP fed to 3-state HMM ----
    print("\n--- C-CAL-2: 2-regime DGP + 3-state HMM (over-spec) ---")
    y_hmm = _simulate_2regime_hmm(T=300, seed=44)
    ctx = _build_ctx(y_hmm, technique_id="hmm",
                      params={"n_components": 3})
    res, elapsed, err = _safe_run(hmm_model, ctx)
    canonical_results.append({
        "id": "C-CAL-2", "wrapper": "hmm",
        "case": "3-state HMM on 2-regime DGP",
        "status": res.get("status") if res else "ERROR",
        "elapsed_s": round(elapsed, 2),
    })
    print(f"  hmm: status={res.get('status') if res else 'ERROR'}")

    # ---- C-CAL-3: Short series ----
    print("\n--- C-CAL-3: Short series T=80 ---")
    rng = np.random.default_rng(45)
    y_short = rng.standard_normal(80)
    for tid, mod, params in [
        ("hmm", hmm_model, {"n_components": 2}),
        ("setar", tar_mod, {"n_regimes": 2}),
    ]:
        ctx = _build_ctx(y_short, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-3", "wrapper": tid,
            "case": "short series T=80",
            "status": (res.get("status") if res else "ERROR"),
            "error_message": res.get("error_message") if res else err,
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:8s}: status={s}, "
              f"err={res.get('error_message') if res else err!s:.50s}")

    # ---- C-CAL-4: Random walk (no nonlinear structure) ----
    print("\n--- C-CAL-4: Random walk T=300 ---")
    rng = np.random.default_rng(46)
    y_rw = np.cumsum(rng.standard_normal(300))
    for tid, mod, params in [
        ("setar", tar_mod, {"n_regimes": 2}),
        ("star", star_mod, {"star_type": "LSTAR", "ar_order": 1}),
    ]:
        ctx = _build_ctx(y_rw, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(mod, ctx)
        canonical_results.append({
            "id": "C-CAL-4", "wrapper": tid,
            "case": "random walk (no nonlinear structure)",
            "status": (res.get("status") if res else "ERROR"),
            "elapsed_s": round(elapsed, 2),
        })
        s = res.get("status") if res else "ERROR"
        print(f"  {tid:8s}: status={s}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings
# =====================================================
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — Markov / Regime family batch "
          "(CAI Session 12)")
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
        "wrappers": ["hmm", "markov_switching", "tar_setar",
                      "star", "nar_narx"],
        "sweep_0": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "markov_regime_batch_audit_results.json"
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
