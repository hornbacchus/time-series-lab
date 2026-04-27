"""Calibration Audit Phase 2 Session 21 — Evaluation/Uncertainty batch.

Five wrappers:
  - block_bootstrap
  - conformal_intervals
  - forecast_combination
  - robust_estimators
  - rolling_origin_cv

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
from techniques import block_bootstrap as bb_mod
from techniques import conformal_intervals as ci_mod
from techniques import forecast_combination as fc_mod
from techniques import robust_estimators as re_mod
from techniques import rolling_origin_cv as rocv_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", frequency="M", name="y"):
    return RunContext({
        "run_id": "audit_eu",
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
        res = mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _ar1(T=200, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _seasonal(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0 — Per-wrapper input-validation
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (5 wrappers)")
    print("Full Session 17/18/19/20 refinement coverage")
    print("=" * 70)

    y = _ar1(T=200)
    y_seas = _seasonal(T=240, period=12)

    # ---- block_bootstrap ----
    print("\n[block_bootstrap]")
    res, dt, err = _safe_run(bb_mod, _build_ctx(y, technique_id="block_bootstrap"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Test invalid numeric: block_length=0 (already coerced to 1 in code)
    res, _, _ = _safe_run(bb_mod, _build_ctx(
        y, technique_id="block_bootstrap", params={"block_length": 0}))
    print(f"  block_length=0: {res.get('status') if res else 'RAISED'}")
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("block_length")
        print(f"    audit_fields.block_length = {recorded}")
        # Per code: block_length<1 silently coerced to 1
        if recorded == 1:
            findings.append({
                "id": "F-EU-BB-BLOCKLEN",
                "wrapper": "block_bootstrap",
                "severity": "operational",
                "description": (
                    "block_bootstrap silently coerces block_length<1 to 1 "
                    "without warning. Numeric range coercion. Pre-fix "
                    "behavior accepts 0 as block_length, sets to 1 silently."
                ),
            })
    # Test invalid n_bootstrap=0
    res, _, _ = _safe_run(bb_mod, _build_ctx(
        y, technique_id="block_bootstrap", params={"n_bootstrap": 0}))
    print(f"  n_bootstrap=0: {res.get('status') if res else 'RAISED'}")
    # Test invalid confidence_level=2.0
    res, _, _ = _safe_run(bb_mod, _build_ctx(
        y, technique_id="block_bootstrap", params={"confidence_level": 2.0}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("confidence_level")
        print(f"  confidence_level=2.0: SUCCESS (silent acceptance)")
        print(f"    audit_fields.confidence_level = {recorded}")
        findings.append({
            "id": "F-EU-BB-CONFLEVEL",
            "wrapper": "block_bootstrap",
            "severity": "operational",
            "description": (
                f"block_bootstrap silently accepts confidence_level=2.0 "
                f"(out of (0,1) range). audit_fields.confidence_level = "
                f"{recorded}. Range gate missing."
            ),
        })

    # ---- conformal_intervals ----
    print("\n[conformal_intervals]")
    res, dt, err = _safe_run(ci_mod, _build_ctx(
        y, technique_id="conformal_intervals", frequency="M"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Invalid cal_fraction=1.5
    res, _, _ = _safe_run(ci_mod, _build_ctx(
        y, technique_id="conformal_intervals", frequency="M",
        params={"cal_fraction": 1.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("cal_fraction")
        print(f"  cal_fraction=1.5: SUCCESS")
        print(f"    audit_fields.cal_fraction = {recorded}")
        findings.append({
            "id": "F-EU-CI-CALFRAC",
            "wrapper": "conformal_intervals",
            "severity": "operational",
            "description": (
                f"conformal_intervals silently accepts cal_fraction=1.5 "
                f"(out of (0,1) range). audit_fields recorded {recorded}."
            ),
        })
    # Invalid confidence_level=1.5
    res, _, _ = _safe_run(ci_mod, _build_ctx(
        y, technique_id="conformal_intervals", frequency="M",
        params={"confidence_level": 1.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  confidence_level=1.5: SUCCESS (silent)")
        findings.append({
            "id": "F-EU-CI-CONFLEVEL",
            "wrapper": "conformal_intervals",
            "severity": "operational",
            "description": (
                "conformal_intervals silently accepts confidence_level "
                "out of (0,1) range."
            ),
        })

    # ---- forecast_combination ----
    print("\n[forecast_combination]")
    res, dt, err = _safe_run(fc_mod, _build_ctx(
        y_seas, technique_id="forecast_combination", frequency="M"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Invalid holdout_fraction=1.5
    res, _, _ = _safe_run(fc_mod, _build_ctx(
        y_seas, technique_id="forecast_combination", frequency="M",
        params={"holdout_fraction": 1.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  holdout_fraction=1.5: SUCCESS (silent)")
        findings.append({
            "id": "F-EU-FC-HOLDOUT",
            "wrapper": "forecast_combination",
            "severity": "operational",
            "description": (
                "forecast_combination silently accepts holdout_fraction "
                "out of (0,1) range."
            ),
        })

    # ---- robust_estimators ----
    print("\n[robust_estimators]")
    res, dt, err = _safe_run(re_mod, _build_ctx(
        y, technique_id="robust_estimators"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Invalid trim_fraction=0.6 (>0.5 makes no sense)
    res, _, _ = _safe_run(re_mod, _build_ctx(
        y, technique_id="robust_estimators",
        params={"trim_fraction": 0.6, "winsor_fraction": 0.6}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  trim_fraction=0.6: SUCCESS (silent)")
        findings.append({
            "id": "F-EU-RE-TRIM",
            "wrapper": "robust_estimators",
            "severity": "operational",
            "description": (
                "robust_estimators silently accepts trim_fraction/"
                "winsor_fraction > 0.5 (where they're undefined for "
                "two-sided trimming/winsorization)."
            ),
        })

    # ---- rolling_origin_cv ----
    print("\n[rolling_origin_cv]")
    res, dt, err = _safe_run(rocv_mod, _build_ctx(
        y_seas, technique_id="rolling_origin_cv", frequency="M"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Invalid folds=0
    res, _, _ = _safe_run(rocv_mod, _build_ctx(
        y_seas, technique_id="rolling_origin_cv", frequency="M",
        params={"folds": 0}))
    print(f"  folds=0: {res.get('status') if res else 'RAISED'}")
    # Invalid horizon=0
    res, _, _ = _safe_run(rocv_mod, _build_ctx(
        y_seas, technique_id="rolling_origin_cv", frequency="M",
        params={"horizon": 0}))
    print(f"  horizon=0: {res.get('status') if res else 'RAISED'}")
    # Invalid confidence_level=2.0
    res, _, _ = _safe_run(rocv_mod, _build_ctx(
        y_seas, technique_id="rolling_origin_cv", frequency="M",
        params={"confidence_level": 2.0}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  confidence_level=2.0: SUCCESS (silent)")
        findings.append({
            "id": "F-EU-ROCV-CONFLEVEL",
            "wrapper": "rolling_origin_cv",
            "severity": "operational",
            "description": (
                "rolling_origin_cv silently accepts confidence_level "
                "out of (0,1) range."
            ),
        })

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # block_bootstrap: block_length sensitivity
    print("\n[block_bootstrap] block_length sensitivity")
    y = _ar1(T=200, phi=0.7, seed=43)
    for bl in (5, 10, 20, "auto"):
        res, dt, err = _safe_run(bb_mod, _build_ctx(
            y, technique_id="block_bootstrap",
            params={"block_length": bl, "n_bootstrap": 500}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  block_length={bl}: dt={dt:.2f}s")

    # conformal_intervals: cal_fraction sensitivity
    print("\n[conformal_intervals] cal_fraction sensitivity")
    y = _seasonal(T=240, period=12, seed=44)
    for cf in (0.1, 0.2, 0.3):
        res, dt, err = _safe_run(ci_mod, _build_ctx(
            y, technique_id="conformal_intervals", frequency="M",
            params={"cal_fraction": cf}))
        if res and res.get("status") == "success":
            print(f"  cal_fraction={cf}: dt={dt:.2f}s")

    # forecast_combination: holdout_fraction sensitivity
    print("\n[forecast_combination] holdout_fraction sensitivity")
    for hf in (0.1, 0.2, 0.3):
        res, dt, err = _safe_run(fc_mod, _build_ctx(
            y, technique_id="forecast_combination", frequency="M",
            params={"holdout_fraction": hf}))
        if res and res.get("status") == "success":
            print(f"  holdout_fraction={hf}: dt={dt:.2f}s")

    # robust_estimators: trim_fraction sweep (Thorough preset)
    print("\n[robust_estimators] trim_fraction sweep (Thorough)")
    for tf in (0.05, 0.10, 0.20):
        res, dt, err = _safe_run(re_mod, _build_ctx(
            y, technique_id="robust_estimators", preset="Thorough",
            params={"trim_fraction": tf}))
        if res and res.get("status") == "success":
            print(f"  trim_fraction={tf}: dt={dt:.2f}s")

    # rolling_origin_cv: folds sweep
    print("\n[rolling_origin_cv] folds sweep")
    for f in (3, 5, 10):
        res, dt, err = _safe_run(rocv_mod, _build_ctx(
            y, technique_id="rolling_origin_cv", frequency="M",
            params={"folds": f, "horizon": 5}))
        if res and res.get("status") == "success":
            print(f"  folds={f}: dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (GSPC + DGS10)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    gspc = _log_returns(data["GSPC"])[-300:].tolist()
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-300:].tolist()

    for sname, y in [("GSPC_logret", gspc), ("DGS10_level", dgs10)]:
        print(f"\n--- {sname} ---")
        for label, mod in [
            ("block_bootstrap", bb_mod),
            ("conformal_intervals", ci_mod),
            ("forecast_combination", fc_mod),
            ("robust_estimators", re_mod),
            ("rolling_origin_cv", rocv_mod),
        ]:
            res, dt, err = _safe_run(mod, _build_ctx(
                y, technique_id=label, frequency="D", name=sname))
            s = res.get("status") if res else f"RAISED: {err[:60]}"
            print(f"  {label}: status={s}, dt={dt:.2f}s")
            rows.append({"series": sname, "wrapper": label,
                          "status": s, "runtime": dt})
    return rows


# =====================================================
# Technique 3 — Adversarial canonicals
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: white noise
    print("\n[C-AD-1] white noise")
    rng = np.random.default_rng(42)
    y = rng.standard_normal(200).tolist()
    for label, mod in [("bb", bb_mod), ("ci", ci_mod), ("re", re_mod)]:
        tid = {"bb": "block_bootstrap", "ci": "conformal_intervals",
                "re": "robust_estimators"}[label]
        res, _, _ = _safe_run(mod, _build_ctx(y, technique_id=tid, frequency="D"))
        s = res.get("status") if res else "RAISED"
        print(f"  {label}: {s}")

    # C-AD-2: with outliers
    print("\n[C-AD-2] series with extreme outliers (robust_estimators showcase)")
    y = rng.standard_normal(200)
    y[10] = 50; y[100] = -50; y[150] = 30
    res, _, _ = _safe_run(re_mod, _build_ctx(y.tolist(), technique_id="robust_estimators"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  robust_estimators: status=success, audit keys={list(af.keys())[:5]}")

    # C-AD-3: short series T=30
    print("\n[C-AD-3] short series T=30")
    y = _ar1(T=30, seed=46)
    for label, mod in [("bb", bb_mod), ("ci", ci_mod), ("rocv", rocv_mod)]:
        tid = {"bb": "block_bootstrap", "ci": "conformal_intervals",
                "rocv": "rolling_origin_cv"}[label]
        res, _, err = _safe_run(mod, _build_ctx(y, technique_id=tid, frequency="M"))
        s = res.get("status") if res else f"RAISED: {err[:40]}"
        print(f"  {label}: {s}")

    # C-AD-4: constant series
    print("\n[C-AD-4] constant series")
    y_const = [1.0] * 100
    for label, mod in [("bb", bb_mod), ("re", re_mod)]:
        tid = "block_bootstrap" if label == "bb" else "robust_estimators"
        res, _, err = _safe_run(mod, _build_ctx(y_const, technique_id=tid))
        s = res.get("status") if res else f"RAISED: {err[:40]}"
        print(f"  {label}: {s}")

    return []


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 21, "started": time.time()}

    sweep0_findings = sweep_0_validation()
    out["sweep_0_findings"] = sweep0_findings

    rows1 = technique_1_param_sweeps()
    out["technique_1"] = rows1

    rows2 = technique_2_real_data()
    out["technique_2"] = rows2

    findings3 = technique_3_adversarial()
    out["technique_3_findings"] = findings3

    all_findings = sweep0_findings + findings3
    severe = [f for f in all_findings if f.get("severity") == "severe"]
    op = [f for f in all_findings if f.get("severity") == "operational"]
    cosm = [f for f in all_findings if f.get("severity") == "cosmetic"]

    print("\n" + "=" * 70)
    print(f"FINDINGS SUMMARY: {len(severe)} severe / {len(op)} operational / {len(cosm)} cosmetic")
    print("=" * 70)
    for f in all_findings:
        print(f"  [{f['severity'].upper()}] {f['id']}: {f['wrapper']}")
        print(f"      {f['description'][:160]}")

    out["finished"] = time.time()
    out["summary"] = {
        "severe": len(severe), "operational": len(op), "cosmetic": len(cosm),
    }
    out_path = _ROOT / "tools" / "calibration_audit" / "evaluation_uncertainty_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
