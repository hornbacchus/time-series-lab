"""Calibration Audit Phase 2 Session 19 — Missing Data batch.

Three wrappers:
  - denton_chowlin_disaggregation
  - kalman_imputation
  - loess_interpolation

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation matrix
    + Session 17 try/except check + Session 18 fallthrough check
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (synthetic-missing GSPC + DGS10)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_missing_data_batch.py
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
from techniques import denton_chowlin_disaggregation as dcd_mod
from techniques import kalman_imputation as ki_mod
from techniques import loess_interpolation as loess_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_md",
                frequency="Q", name="y", series_2nd=None):
    user_params = dict(params or {})
    series = [{"name": name, "values": list(values)}]
    if series_2nd is not None:
        s2_name, s2_vals = series_2nd
        series.append({"name": s2_name, "values": list(s2_vals)})
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


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _ar1_with_missing(T=120, phi=0.7, missing_frac=0.1, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    n_miss = int(T * missing_frac)
    miss_idx = rng.choice(T, size=n_miss, replace=False)
    y[miss_idx] = np.nan
    return y.tolist()


def _quarterly_data(n_quarters=20, seed=42):
    """Synthetic quarterly series for disaggregation."""
    rng = np.random.default_rng(seed)
    return (10.0 + np.cumsum(rng.standard_normal(n_quarters) * 0.5)).tolist()


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# =====================================================
# Sweep 0 — Per-wrapper dispatch + input-validation
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (3 wrappers)")
    print("With Session 17/18 try/except + fallthrough checks")
    print("=" * 70)

    y_quarterly = _quarterly_data()
    y_with_missing = _ar1_with_missing()

    # ---- denton_chowlin_disaggregation ----
    print("\n[denton_chowlin_disaggregation]")
    res, dt, err = _safe_run(dcd_mod, _build_ctx(
        y_quarterly, technique_id="denton_chowlin_disaggregation",
        params={"conversion_ratio": 3}))
    print(f"  baseline (chowlin Q→M): {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid methods
    for m in ("denton", "chowlin"):
        res, _, _ = _safe_run(dcd_mod, _build_ctx(
            y_quarterly, technique_id="denton_chowlin_disaggregation",
            params={"method": m, "conversion_ratio": 3}))
        ok = res and res.get("status") == "success"
        print(f"  method={m!r}: {'OK' if ok else 'FAIL'}")
    # Invalid method
    res, _, err = _safe_run(dcd_mod, _build_ctx(
        y_quarterly, technique_id="denton_chowlin_disaggregation",
        params={"method": "zzz_invalid", "conversion_ratio": 3}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("method")
        warns = res.get("warnings") or []
        print(f"  method='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.method = {recorded!r}")
        print(f"    warnings: {' | '.join(str(w) for w in warns)[:120]}")
        findings.append({
            "id": "F-MD-DENTON-METHOD",
            "wrapper": "denton_chowlin_disaggregation",
            "severity": "severe",
            "description": (
                f"denton_chowlin_disaggregation silently coerces invalid "
                f"`method` to 'chowlin' (with warning). audit_fields."
                f"method = {recorded!r} (the coerced value, NOT the "
                f"user's invalid input — but the user's intended "
                f"computation differs from what ran). Pattern: "
                f"loud-and-coerced is SEVERE per Session 15 protocol."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  method='zzz_invalid': REJECTED — {em[:80]}")
    # Invalid conversion_ratio
    res, _, err = _safe_run(dcd_mod, _build_ctx(
        y_quarterly, technique_id="denton_chowlin_disaggregation",
        params={"conversion_ratio": 1}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("conversion_ratio")
        print(f"  conversion_ratio=1: SUCCESS (silent coercion)")
        print(f"    audit_fields.conversion_ratio = {recorded}")
        findings.append({
            "id": "F-MD-DENTON-CONVRATIO",
            "wrapper": "denton_chowlin_disaggregation",
            "severity": "operational",
            "description": (
                "denton_chowlin_disaggregation silently coerces "
                "conversion_ratio < 2 to 3 (with warning). Numeric "
                "range coercion. Should reject explicitly to give "
                "user actionable error rather than silent fallback."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  conversion_ratio=1: REJECTED — {em[:80]}")
    # Invalid rho
    res, _, err = _safe_run(dcd_mod, _build_ctx(
        y_quarterly, technique_id="denton_chowlin_disaggregation",
        params={"method": "chowlin", "conversion_ratio": 3, "rho": 1.5}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("rho")
        print(f"  rho=1.5 (out of (0,1)): SUCCESS (silent coercion)")
        print(f"    audit_fields.rho = {recorded}")
        findings.append({
            "id": "F-MD-DENTON-RHO",
            "wrapper": "denton_chowlin_disaggregation",
            "severity": "operational",
            "description": (
                "denton_chowlin_disaggregation silently coerces rho "
                "out of (0,1) to 0.5 (with warning). Numeric range "
                "coercion. Should reject explicitly."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  rho=1.5: REJECTED — {em[:80]}")

    # ---- kalman_imputation ----
    print("\n[kalman_imputation]")
    res, dt, err = _safe_run(ki_mod, _build_ctx(
        y_with_missing, technique_id="kalman_imputation"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid model_types
    for m in ("local level", "local linear trend"):
        res, _, _ = _safe_run(ki_mod, _build_ctx(
            y_with_missing, technique_id="kalman_imputation",
            params={"model_type": m}))
        ok = res and res.get("status") == "success"
        print(f"  model_type={m!r}: {'OK' if ok else 'FAIL'}")
    # Invalid model_type — Session 18 fall-through check
    res, _, err = _safe_run(ki_mod, _build_ctx(
        y_with_missing, technique_id="kalman_imputation",
        params={"model_type": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("model_type")
        print(f"  model_type='zzz_invalid': SUCCESS (silent fall-through)")
        print(f"    audit_fields.model_type = {recorded!r}")
        findings.append({
            "id": "F-MD-KALMAN-MODELTYPE",
            "wrapper": "kalman_imputation",
            "severity": "severe",
            "description": (
                f"kalman_imputation silently falls through invalid "
                f"`model_type` to 'local linear trend' default via "
                f"if/else at line 99-102. audit_fields.model_type = "
                f"{recorded!r}. Session 18 fall-through pattern."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  model_type='zzz_invalid': REJECTED — {em[:80]}")

    # ---- loess_interpolation ----
    print("\n[loess_interpolation]")
    res, dt, err = _safe_run(loess_mod, _build_ctx(
        y_with_missing, technique_id="loess_interpolation"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Invalid frac
    res, _, err = _safe_run(loess_mod, _build_ctx(
        y_with_missing, technique_id="loess_interpolation",
        params={"frac": 1.5}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("frac")
        print(f"  frac=1.5 (out of (0,1]): SUCCESS (silent coercion)")
        print(f"    audit_fields.frac = {recorded}")
        findings.append({
            "id": "F-MD-LOESS-FRAC",
            "wrapper": "loess_interpolation",
            "severity": "operational",
            "description": (
                "loess_interpolation silently coerces frac out of "
                "(0,1] to 0.3 (with warning). Numeric range coercion. "
                "Should reject explicitly."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  frac=1.5: REJECTED — {em[:80]}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # ---- denton_chowlin: method comparison ----
    print("\n[denton_chowlin] method comparison on Q→M synthetic")
    y = _quarterly_data(n_quarters=20, seed=43)
    for m in ("denton", "chowlin"):
        res, dt, err = _safe_run(dcd_mod, _build_ctx(
            y, technique_id="denton_chowlin_disaggregation",
            params={"method": m, "conversion_ratio": 3}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  method={m!r}: max_disc={af.get('max_discrepancy')}, dt={dt:.2f}s")
            rows.append({"wrapper": "dcd", "param": m,
                          "max_disc": af.get("max_discrepancy"), "runtime": dt})

    # ---- kalman_imputation: missing pattern sensitivity ----
    print("\n[kalman_imputation] missing pattern sensitivity")
    for label, miss_frac in [("sparse 5%", 0.05), ("moderate 15%", 0.15), ("heavy 30%", 0.30)]:
        y = _ar1_with_missing(T=200, missing_frac=miss_frac, seed=44)
        res, dt, err = _safe_run(ki_mod, _build_ctx(
            y, technique_id="kalman_imputation"))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: n_imputed={af.get('n_missing')}, RMSE={af.get('rmse_observed')}, dt={dt:.2f}s")

    # ---- loess_interpolation: frac sensitivity ----
    print("\n[loess_interpolation] frac sensitivity")
    y = _ar1_with_missing(T=200, missing_frac=0.15, seed=45)
    for f in (0.1, 0.3, 0.5):
        res, dt, err = _safe_run(loess_mod, _build_ctx(
            y, technique_id="loess_interpolation", params={"frac": f}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  frac={f}: RMSE={af.get('rmse_observed')}, dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data stress (synthetic-missing GSPC/DGS10)
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (synthetic-missing macro)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        print("  fixture missing; skipping")
        return rows
    data = np.load(_FIXTURE)
    gspc_full = _log_returns(data["GSPC"])[-300:]
    dgs10_full = data["DGS10"][~np.isnan(data["DGS10"])][-300:]

    rng = np.random.default_rng(42)

    for sname, base in [("GSPC_logret", gspc_full), ("DGS10_level", dgs10_full)]:
        # Inject 10% random missing
        y = base.copy()
        n_miss = int(len(y) * 0.10)
        miss_idx = rng.choice(len(y), size=n_miss, replace=False)
        truth = y[miss_idx].copy()
        y[miss_idx] = np.nan

        print(f"\n--- {sname} ({len(y)} obs, 10% missing) ---")
        for label, mod in [
            ("kalman_imputation", ki_mod),
            ("loess_interpolation", loess_mod),
        ]:
            res, dt, err = _safe_run(mod, _build_ctx(
                y.tolist(), technique_id=label, frequency="D", name=sname))
            if res and res.get("status") == "success":
                af = res["audit_fields"]
                print(f"  {label}: rmse_obs={af.get('rmse_observed')}, dt={dt:.2f}s")
                rows.append({"series": sname, "wrapper": label,
                              "rmse": af.get("rmse_observed"), "runtime": dt})
            else:
                em = (res.get('error_message') if res else err) or ""
                print(f"  {label}: FAIL — {em[:80]}")

    # denton_chowlin: synthetic monthly-from-quarterly
    print(f"\n--- Synthetic Q→M disaggregation (20 quarters → 60 months) ---")
    y_q = _quarterly_data(n_quarters=20, seed=42)
    for m in ("denton", "chowlin"):
        res, dt, err = _safe_run(dcd_mod, _build_ctx(
            y_q, technique_id="denton_chowlin_disaggregation",
            params={"method": m, "conversion_ratio": 3}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  method={m}: max_disc={af.get('max_discrepancy')}, dt={dt:.2f}s")
            rows.append({"series": "synthetic_Q", "wrapper": f"dcd_{m}",
                          "max_disc": af.get("max_discrepancy"), "runtime": dt})

    return rows


# =====================================================
# Technique 3 — Adversarial canonicals (4)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: single missing value
    print("\n[C-AD-1] single missing value")
    y = _ar1_with_missing(T=100, missing_frac=0, seed=42)
    y_arr = np.array(y); y_arr[50] = np.nan
    for label, mod in [("ki", ki_mod), ("loess", loess_mod)]:
        tid = "kalman_imputation" if label == "ki" else "loess_interpolation"
        res, _, err = _safe_run(mod, _build_ctx(y_arr.tolist(), technique_id=tid))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: n_imputed={af.get('n_missing')}, RMSE={af.get('rmse_observed')}")

    # C-AD-2: block-missing
    print("\n[C-AD-2] block-missing (consecutive 20 values)")
    y = _ar1_with_missing(T=200, missing_frac=0, seed=43)
    y_arr = np.array(y); y_arr[80:100] = np.nan
    for label, mod in [("ki", ki_mod), ("loess", loess_mod)]:
        tid = "kalman_imputation" if label == "ki" else "loess_interpolation"
        res, _, _ = _safe_run(mod, _build_ctx(y_arr.tolist(), technique_id=tid))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: max_gap={af.get('max_gap_length')}, RMSE={af.get('rmse_observed')}")

    # C-AD-3: boundary missing (first/last values)
    print("\n[C-AD-3] boundary missing (extrapolation)")
    y = _ar1_with_missing(T=100, missing_frac=0, seed=44)
    y_arr = np.array(y); y_arr[0] = np.nan; y_arr[-1] = np.nan
    for label, mod in [("ki", ki_mod), ("loess", loess_mod)]:
        tid = "kalman_imputation" if label == "ki" else "loess_interpolation"
        res, _, _ = _safe_run(mod, _build_ctx(y_arr.tolist(), technique_id=tid))
        s = res.get("status") if res else "RAISED"
        print(f"  {label}: status={s}")

    # C-AD-4: short series with high missing rate
    print("\n[C-AD-4] short series T=20 with 30% missing")
    y = _ar1_with_missing(T=20, missing_frac=0.3, seed=45)
    for label, mod in [("ki", ki_mod), ("loess", loess_mod)]:
        tid = "kalman_imputation" if label == "ki" else "loess_interpolation"
        res, _, err = _safe_run(mod, _build_ctx(y, technique_id=tid))
        s = res.get("status") if res else f"RAISED: {err}"
        print(f"  {label}: status={s}")

    return []


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 19, "started": time.time()}

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

    out_path = _ROOT / "tools" / "calibration_audit" / "missing_data_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
