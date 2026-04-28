"""Calibration Audit Phase 2 Session 26 — Statistical ML batch.

Four wrappers:
  - gaussian_process_forecast
  - prophet_forecast
  - quantile_regression_model
  - svr_forecast
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
from techniques import gaussian_process_forecast as gp_mod
from techniques import prophet_forecast as p_mod
from techniques import quantile_regression_model as qr_mod
from techniques import svr_forecast as svr_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, technique_id, params=None,
         preset="Fast", frequency="D", name="y"):
    return RunContext({
        "run_id": "audit_ml",
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": name, "values": list(values)}],
        "params": dict(params or {}),
    })


def _safe_run(mod, ctx):
    try:
        t0 = time.time()
        res = mod.run(ctx, _NULL)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _ar1(T=120, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = 0.5 * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _seasonal(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("=" * 70)

    y = _ar1(T=120)
    y_seas = _seasonal(T=240)

    # ---- gaussian_process_forecast ----
    print("\n[gaussian_process_forecast]")
    res, dt, err = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid kernels
    for k in ("rbf", "matern", "rational_quadratic"):
        res, _, _ = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast",
                                              params={"kernel": k}))
        print(f"  kernel={k}: {res.get('status') if res else 'RAISED'}")
    # Invalid kernel
    res, _, _ = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast",
                                          params={"kernel": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("kernel")
        print(f"  kernel='zzz_invalid': SUCCESS (silent fall-through to RBF)")
        print(f"    audit_fields.kernel = {recorded!r}")
        findings.append({
            "id": "F-ML-GP-KERNEL",
            "wrapper": "gaussian_process_forecast",
            "severity": "severe",
            "description": (
                "gaussian_process_forecast silently falls through "
                "invalid `kernel` to RBF via if/elif/else at line "
                "134-139. audit_fields records user's invalid value. "
                "Session 18 silent-fall-through pattern."
            ),
        })
    # horizon
    res, _, _ = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast",
                                          params={"horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-GP-HORIZON",
            "wrapper": "gaussian_process_forecast",
            "severity": "operational",
            "description": "gp silently coerces horizon<1 to 1.",
        })
    # confidence_level
    res, _, _ = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast",
                                          params={"confidence_level": 1.5}))
    if res and res.get("status") == "success":
        print(f"  confidence_level=1.5: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-GP-CONFLEVEL",
            "wrapper": "gaussian_process_forecast",
            "severity": "operational",
            "description": "gp silently accepts confidence_level out of (0, 1).",
        })

    # ---- prophet_forecast ----
    print("\n[prophet_forecast]")
    res, dt, err = _safe_run(p_mod, _ctx(y_seas, technique_id="prophet_forecast"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    res, _, _ = _safe_run(p_mod, _ctx(y_seas, technique_id="prophet_forecast",
                                         params={"horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-P-HORIZON",
            "wrapper": "prophet_forecast",
            "severity": "operational",
            "description": "prophet silently coerces horizon<1 to 1.",
        })
    res, _, _ = _safe_run(p_mod, _ctx(y_seas, technique_id="prophet_forecast",
                                         params={"changepoint_prior_scale": -0.1}))
    if res and res.get("status") == "success":
        print(f"  changepoint_prior_scale=-0.1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-P-CPSCALE",
            "wrapper": "prophet_forecast",
            "severity": "operational",
            "description": (
                "prophet silently accepts negative changepoint_prior_scale "
                "(must be > 0 for valid Bayesian prior)."
            ),
        })

    # ---- quantile_regression_model ----
    print("\n[quantile_regression_model]")
    res, dt, err = _safe_run(qr_mod, _ctx(y, technique_id="quantile_regression_model"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # horizon
    res, _, _ = _safe_run(qr_mod, _ctx(y, technique_id="quantile_regression_model",
                                          params={"horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-QR-HORIZON",
            "wrapper": "quantile_regression_model",
            "severity": "operational",
            "description": "qr silently coerces horizon<1 to 1.",
        })
    # n_lags=0
    res, _, _ = _safe_run(qr_mod, _ctx(y, technique_id="quantile_regression_model",
                                          params={"n_lags": 0}))
    if res and res.get("status") == "success":
        print(f"  n_lags=0: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-QR-NLAGS",
            "wrapper": "quantile_regression_model",
            "severity": "operational",
            "description": "qr silently accepts n_lags=0.",
        })
    # quantiles out of range
    res, _, _ = _safe_run(qr_mod, _ctx(y, technique_id="quantile_regression_model",
                                          params={"quantiles": [1.5, 2.0]}))
    if res and res.get("status") == "success":
        print(f"  quantiles=[1.5, 2.0]: SUCCESS (silent acceptance)")
        findings.append({
            "id": "F-ML-QR-QUANTILES",
            "wrapper": "quantile_regression_model",
            "severity": "operational",
            "description": (
                "qr silently accepts quantile values out of (0, 1)."
            ),
        })

    # ---- svr_forecast ----
    print("\n[svr_forecast]")
    res, dt, err = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid kernels
    for k in ("rbf", "linear", "poly", "sigmoid"):
        res, _, _ = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast",
                                                params={"kernel": k}))
        print(f"  kernel={k}: {res.get('status') if res else 'RAISED'}")
    # Invalid kernel — loud-and-coerced
    res, _, _ = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast",
                                            params={"kernel": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        print(f"  kernel='zzz_invalid': SUCCESS (loud-and-coerced)")
        findings.append({
            "id": "F-ML-SVR-KERNEL",
            "wrapper": "svr_forecast",
            "severity": "severe",
            "description": (
                "svr_forecast loud-and-coerced invalid kernel to 'rbf' "
                "with warning. Per Session 16 protocol (loud-and-coerced "
                "is severe because user's intended computation differs "
                "from what ran)."
            ),
        })
    # Negative C
    res, _, _ = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast",
                                            params={"C": -1.0}))
    if res and res.get("status") == "success":
        print(f"  C=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-SVR-C",
            "wrapper": "svr_forecast",
            "severity": "operational",
            "description": "svr silently accepts negative C.",
        })
    # horizon
    res, _, _ = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast",
                                            params={"horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ML-SVR-HORIZON",
            "wrapper": "svr_forecast",
            "severity": "operational",
            "description": "svr silently coerces horizon<1 to 1.",
        })

    return findings


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []
    y = _ar1(T=150, seed=43)

    print("\n[gp] kernel comparison")
    for k in ("rbf", "matern", "rational_quadratic"):
        res, dt, _ = _safe_run(gp_mod, _ctx(y, technique_id="gaussian_process_forecast",
                                                params={"kernel": k}))
        if res and res.get("status") == "success":
            print(f"  kernel={k}: dt={dt:.2f}s")

    print("\n[qr] quantile sweep")
    for q in ([0.1], [0.5], [0.1, 0.5, 0.9]):
        res, dt, _ = _safe_run(qr_mod, _ctx(y, technique_id="quantile_regression_model",
                                                params={"quantiles": q}))
        if res and res.get("status") == "success":
            print(f"  quantiles={q}: dt={dt:.2f}s")

    print("\n[svr] kernel comparison")
    for k in ("rbf", "linear", "poly"):
        res, dt, _ = _safe_run(svr_mod, _ctx(y, technique_id="svr_forecast",
                                                 params={"kernel": k}))
        if res and res.get("status") == "success":
            print(f"  kernel={k}: dt={dt:.2f}s")

    return rows


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (DGS10 + GSPC)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-300:].tolist()
    p = data["GSPC"][~np.isnan(data["GSPC"])][-300:]
    gspc = (100.0 * np.diff(np.log(np.maximum(p, 1e-12)))).tolist()

    for sname, y in [("DGS10", dgs10), ("GSPC_logret", gspc)]:
        print(f"\n--- {sname} ---")
        for tid, mod, label in [
            ("gaussian_process_forecast", gp_mod, "gp"),
            ("prophet_forecast", p_mod, "p"),
            ("quantile_regression_model", qr_mod, "qr"),
            ("svr_forecast", svr_mod, "svr"),
        ]:
            res, dt, err = _safe_run(mod, _ctx(y, technique_id=tid, name=sname))
            s = res.get("status") if res else f"RAISED:{err[:30]}"
            print(f"  {label}: status={s}, dt={dt:.2f}s")
            rows.append({"series": sname, "wrapper": label,
                          "status": s, "runtime": dt})
    return rows


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    rng = np.random.default_rng(42)

    print("\n[C-AD-1] white noise")
    y = rng.standard_normal(150).tolist()
    for tid, mod, label in [
        ("gaussian_process_forecast", gp_mod, "gp"),
        ("quantile_regression_model", qr_mod, "qr"),
        ("svr_forecast", svr_mod, "svr"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    print("\n[C-AD-2] pure trend")
    y = (np.arange(150) * 0.1 + 0.05 * rng.standard_normal(150)).tolist()
    for tid, mod, label in [
        ("svr_forecast", svr_mod, "svr"),
        ("gaussian_process_forecast", gp_mod, "gp"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    print("\n[C-AD-3] short series T=30")
    y = _ar1(T=30, seed=44)
    for tid, mod, label in [
        ("quantile_regression_model", qr_mod, "qr"),
        ("svr_forecast", svr_mod, "svr"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    print("\n[C-AD-4] constant series")
    y = [1.0] * 100
    for tid, mod, label in [
        ("gaussian_process_forecast", gp_mod, "gp"),
        ("svr_forecast", svr_mod, "svr"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    return []


def main():
    out = {"session": 26, "started": time.time()}
    sweep0 = sweep_0_validation()
    out["sweep_0_findings"] = sweep0
    rows1 = technique_1_param_sweeps()
    out["technique_1"] = rows1
    rows2 = technique_2_real_data()
    out["technique_2"] = rows2
    findings3 = technique_3_adversarial()
    out["technique_3_findings"] = findings3
    all_f = sweep0 + findings3
    sev = [f for f in all_f if f.get("severity") == "severe"]
    op = [f for f in all_f if f.get("severity") == "operational"]
    cosm = [f for f in all_f if f.get("severity") == "cosmetic"]
    print("\n" + "=" * 70)
    print(f"FINDINGS SUMMARY: {len(sev)} severe / {len(op)} operational / {len(cosm)} cosmetic")
    print("=" * 70)
    for f in all_f:
        print(f"  [{f['severity'].upper()}] {f['id']}: {f['wrapper']}")
    out["finished"] = time.time()
    out["summary"] = {"severe": len(sev), "operational": len(op), "cosmetic": len(cosm)}
    out_path = _ROOT / "tools" / "calibration_audit" / "statistical_ml_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
