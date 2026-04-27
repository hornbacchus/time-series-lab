"""Calibration Audit Phase 2 Session 23 — Tree forecasters batch.

Four wrappers:
  - gradient_boosting_forecast (sklearn)
  - lightgbm_forecast
  - random_forest_forecast (sklearn)
  - xgboost_forecast

Sweep 0 + Technique 1 + 2 + 3 per established protocol.
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
from techniques import gradient_boosting_forecast as gbm_mod
from techniques import lightgbm_forecast as lgbm_mod
from techniques import random_forest_forecast as rf_mod
from techniques import xgboost_forecast as xgb_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, technique_id, params=None,
         preset="Fast", frequency="D", name="y"):
    return RunContext({
        "run_id": "audit_tree",
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


def _ar1(T=300, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("=" * 70)

    y = _ar1(T=300, seed=42)

    wrappers = [
        ("gradient_boosting_forecast", gbm_mod, "gbm"),
        ("lightgbm_forecast", lgbm_mod, "lgbm"),
        ("random_forest_forecast", rf_mod, "rf"),
        ("xgboost_forecast", xgb_mod, "xgb"),
    ]

    for tid, mod, label in wrappers:
        print(f"\n[{tid}]")
        # Baseline
        res, dt, err = _safe_run(mod, _ctx(y, technique_id=tid))
        print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")

        # Numeric range tests
        # Negative n_estimators
        res, _, err = _safe_run(mod, _ctx(
            y, technique_id=tid, params={"n_estimators": -10}))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        if res and res.get("status") == "success":
            af = res.get("audit_fields") or {}
            print(f"  n_estimators=-10: SUCCESS (silent)")
            findings.append({
                "id": f"F-TR-{label.upper()}-NEST",
                "wrapper": tid,
                "severity": "operational",
                "description": (
                    f"{tid} silently accepts n_estimators=-10 "
                    "(must be >= 1)."
                ),
            })
        else:
            print(f"  n_estimators=-10: {s}")

        # Zero n_lags
        param_name = "n_lags" if label == "gbm" else "max_lag"
        res, _, err = _safe_run(mod, _ctx(
            y, technique_id=tid, params={param_name: 0}))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        if res and res.get("status") == "success":
            print(f"  {param_name}=0: SUCCESS (silent — degenerate, no features)")
            findings.append({
                "id": f"F-TR-{label.upper()}-NLAGS",
                "wrapper": tid,
                "severity": "operational",
                "description": (
                    f"{tid} silently accepts {param_name}=0 "
                    "(no lag features — degenerate model)."
                ),
            })
        else:
            print(f"  {param_name}=0: {s}")

        # Negative max_depth (for gbm/rf/xgb; not lightgbm where -1 means no limit)
        if label != "lgbm":
            res, _, err = _safe_run(mod, _ctx(
                y, technique_id=tid, params={"max_depth": -2}))
            s = res.get("status") if res else f"RAISED:{err[:30]}"
            if res and res.get("status") == "success":
                print(f"  max_depth=-2: SUCCESS (silent)")
                findings.append({
                    "id": f"F-TR-{label.upper()}-MDEPTH",
                    "wrapper": tid,
                    "severity": "operational",
                    "description": (
                        f"{tid} silently accepts max_depth=-2."
                    ),
                })
            else:
                print(f"  max_depth=-2: {s}")
        else:
            res, _, err = _safe_run(mod, _ctx(
                y, technique_id=tid, params={"max_depth": -1}))
            print(f"  max_depth=-1 (lgbm: no limit): {res.get('status') if res else 'RAISED'}")

        # Invalid learning_rate (not for rf which doesn't have it)
        if label != "rf":
            res, _, err = _safe_run(mod, _ctx(
                y, technique_id=tid, params={"learning_rate": -0.5}))
            s = res.get("status") if res else f"RAISED:{err[:30]}"
            if res and res.get("status") == "success":
                print(f"  learning_rate=-0.5: SUCCESS (silent)")
                findings.append({
                    "id": f"F-TR-{label.upper()}-LR",
                    "wrapper": tid,
                    "severity": "operational",
                    "description": (
                        f"{tid} silently accepts negative learning_rate "
                        "(must be > 0)."
                    ),
                })
            else:
                print(f"  learning_rate=-0.5: {s}")

        # Negative horizon
        res, _, err = _safe_run(mod, _ctx(
            y, technique_id=tid, params={"horizon": -1}))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        if res and res.get("status") == "success":
            print(f"  horizon=-1: SUCCESS (silent)")
            findings.append({
                "id": f"F-TR-{label.upper()}-HORIZON",
                "wrapper": tid,
                "severity": "operational",
                "description": (
                    f"{tid} silently accepts horizon=-1."
                ),
            })
        else:
            print(f"  horizon=-1: {s}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []
    y = _ar1(T=300, seed=43)

    print("\n[gradient_boosting] n_estimators sweep")
    for ne in (50, 100, 200):
        res, dt, err = _safe_run(gbm_mod, _ctx(
            y, technique_id="gradient_boosting_forecast",
            params={"n_estimators": ne}))
        if res and res.get("status") == "success":
            print(f"  n_estimators={ne}: dt={dt:.2f}s")

    print("\n[lightgbm] num_leaves sweep")
    for nl in (15, 31, 63):
        res, dt, err = _safe_run(lgbm_mod, _ctx(
            y, technique_id="lightgbm_forecast",
            params={"num_leaves": nl}))
        if res and res.get("status") == "success":
            print(f"  num_leaves={nl}: dt={dt:.2f}s")

    print("\n[random_forest] max_depth sweep")
    for md in (5, 10, 20):
        res, dt, err = _safe_run(rf_mod, _ctx(
            y, technique_id="random_forest_forecast",
            params={"max_depth": md}))
        if res and res.get("status") == "success":
            print(f"  max_depth={md}: dt={dt:.2f}s")

    print("\n[xgboost] learning_rate sweep")
    for lr in (0.01, 0.1, 0.3):
        res, dt, err = _safe_run(xgb_mod, _ctx(
            y, technique_id="xgboost_forecast",
            params={"learning_rate": lr}))
        if res and res.get("status") == "success":
            print(f"  learning_rate={lr}: dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (GSPC + DGS10)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    gspc = _log_returns(data["GSPC"])[-300:].tolist()
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-300:].tolist()

    for sname, y in [("GSPC_logret", gspc), ("DGS10_level", dgs10)]:
        print(f"\n--- {sname} ---")
        for tid, mod, label in [
            ("gradient_boosting_forecast", gbm_mod, "gbm"),
            ("lightgbm_forecast", lgbm_mod, "lgbm"),
            ("random_forest_forecast", rf_mod, "rf"),
            ("xgboost_forecast", xgb_mod, "xgb"),
        ]:
            res, dt, err = _safe_run(mod, _ctx(y, technique_id=tid, name=sname))
            if res and res.get("status") == "success":
                af = res["audit_fields"]
                rmse = af.get("rmse") or af.get("test_rmse") or af.get("training_rmse")
                print(f"  {label}: rmse={rmse}, dt={dt:.2f}s")
                rows.append({"series": sname, "wrapper": label,
                              "rmse": rmse, "runtime": dt})
            else:
                em = (res.get('error_message') if res else err) or ""
                print(f"  {label}: FAIL — {em[:60]}")

    return rows


# =====================================================
# Technique 3 — Adversarial
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    rng = np.random.default_rng(42)

    # C-AD-1: white noise (no forecastable structure)
    print("\n[C-AD-1] white noise")
    y = rng.standard_normal(200).tolist()
    for tid, mod, label in [
        ("gradient_boosting_forecast", gbm_mod, "gbm"),
        ("lightgbm_forecast", lgbm_mod, "lgbm"),
        ("random_forest_forecast", rf_mod, "rf"),
        ("xgboost_forecast", xgb_mod, "xgb"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    # C-AD-2: pure trend (linearly increasing)
    print("\n[C-AD-2] pure linear trend")
    y = (np.arange(200) * 0.1 + 0.05 * rng.standard_normal(200)).tolist()
    for tid, mod, label in [
        ("gradient_boosting_forecast", gbm_mod, "gbm"),
        ("xgboost_forecast", xgb_mod, "xgb"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: {af.get('rmse') or af.get('training_rmse')}")

    # C-AD-3: short series T=30
    print("\n[C-AD-3] short series T=30")
    y = _ar1(T=30, seed=44)
    for tid, mod, label in [
        ("gradient_boosting_forecast", gbm_mod, "gbm"),
        ("random_forest_forecast", rf_mod, "rf"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    # C-AD-4: constant series (zero variance)
    print("\n[C-AD-4] constant series")
    y = [1.0] * 200
    for tid, mod, label in [
        ("lightgbm_forecast", lgbm_mod, "lgbm"),
        ("xgboost_forecast", xgb_mod, "xgb"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    return []


def main():
    out = {"session": 23, "started": time.time()}
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
    out_path = _ROOT / "tools" / "calibration_audit" / "tree_forecasters_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
