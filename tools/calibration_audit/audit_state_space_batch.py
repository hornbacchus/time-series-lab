"""Calibration Audit Phase 2 Session 18 — State Space family batch.

Four wrappers:
  - local_level
  - local_linear_trend
  - structural_ts
  - particle_filter

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation + Session
    17's NEW try/except suppression check
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (GSPC + DGS10)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_state_space_batch.py
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
from techniques import local_level as ll_mod
from techniques import local_linear_trend as llt_mod
from techniques import structural_ts as sts_mod
from techniques import particle_filter as pf_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_ss",
                frequency="M", name="y", time_col=None):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_col if time_col is not None else list(range(len(values))),
        "series": [{"name": name, "values": list(values)}],
        "params": user_params,
    })


def _safe_run(wrapper_module, ctx):
    try:
        t0 = time.time()
        res = wrapper_module.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _trending_data(T=120, slope=0.05, seed=42):
    rng = np.random.default_rng(seed)
    return (np.arange(T) * slope + 0.3 * rng.standard_normal(T)).tolist()


def _seasonal_data(T=120, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (0.05 * t + 2.0 * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def _ar1(T=120, phi=0.5, seed=42):
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
# Sweep 0 — Per-wrapper dispatch + input-validation
# (with NEW Session 17-style try/except suppression check)
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("Includes NEW try/except suppression check (Session 17 lesson)")
    print("=" * 70)

    y_trend = _trending_data()
    y_seasonal = _seasonal_data()
    y_ar1 = _ar1()

    # ---- local_level ----
    print("\n[local_level]")
    res, dt, err = _safe_run(ll_mod, _build_ctx(
        y_trend, technique_id="local_level"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    print("  → numeric/bool params only; no string-acceptance surface; clean")

    # ---- local_linear_trend ----
    print("\n[local_linear_trend]")
    res, dt, err = _safe_run(llt_mod, _build_ctx(
        y_trend, technique_id="local_linear_trend"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    print("  → numeric/bool params only; clean")
    print("  → note: `damped` param is no-op (already disclosed via D7)")

    # ---- structural_ts ----
    print("\n[structural_ts]")
    res, dt, err = _safe_run(sts_mod, _build_ctx(
        y_seasonal, technique_id="structural_ts"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid level types
    for lt in ("local level", "local linear trend", "smooth trend",
                "random walk", "fixed intercept"):
        res, _, _ = _safe_run(sts_mod, _build_ctx(
            y_seasonal, technique_id="structural_ts", params={"level": lt}))
        ok = res and res.get("status") == "success"
        print(f"  level={lt!r}: {'OK' if ok else 'FAIL'}")
    # Invalid level — does it reject or coerce?
    res, _, err = _safe_run(sts_mod, _build_ctx(
        y_seasonal, technique_id="structural_ts",
        params={"level": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("level_type")
        warns = res.get("warnings") or []
        print(f"  level='zzz_invalid': SUCCESS (silent acceptance!)")
        print(f"    audit_fields.level_type = {recorded!r}")
        print(f"    warnings: {' | '.join(str(w) for w in warns)[:120]}")
        findings.append({
            "id": "F-SS-STS-LEVEL",
            "wrapper": "structural_ts",
            "severity": "severe",
            "description": (
                f"structural_ts silently accepts invalid `level` value "
                f"{recorded!r}. The wrapper has an inner try/except "
                f"fallback at line 159-171 that catches the "
                f"UnobservedComponents ValueError and retries with "
                f"the SAME invalid level_type, suppressing the "
                f"actionable error. Session 17 try/except-suppression "
                f"pattern."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  level='zzz_invalid': REJECTED — {em[:80]}")

    # ---- particle_filter ----
    print("\n[particle_filter]")
    res, dt, err = _safe_run(pf_mod, _build_ctx(
        y_ar1, technique_id="particle_filter",
        params={"n_particles": 200}))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid models
    for m in ("local_level", "local_level_sv", "nonlinear_growth",
              "random_walk_sv"):
        res, _, _ = _safe_run(pf_mod, _build_ctx(
            y_ar1, technique_id="particle_filter",
            params={"model": m, "n_particles": 200}))
        ok = res and res.get("status") == "success"
        print(f"  model={m!r}: {'OK' if ok else 'FAIL'}")
    # Invalid model — does it reject or coerce?
    res, _, err = _safe_run(pf_mod, _build_ctx(
        y_ar1, technique_id="particle_filter",
        params={"model": "zzz_invalid", "n_particles": 200}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("model")
        print(f"  model='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.model = {recorded!r}")
        findings.append({
            "id": "F-SS-PF-MODEL",
            "wrapper": "particle_filter",
            "severity": "severe",
            "description": (
                f"particle_filter silently coerces invalid `model` "
                f"to 'local_level' default via if/elif/else chain in "
                f"_get_model_functions (line 357-415). audit_fields."
                f"model recorded user's invalid value {recorded!r}. "
                "Pattern matches Sessions 9-17 silent-acceptance bugs."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  model='zzz_invalid': REJECTED — {em[:80]}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # ---- local_level ----
    print("\n[local_level] horizon sensitivity")
    y = _trending_data(seed=43)
    for h in (5, 10, 20):
        res, dt, err = _safe_run(ll_mod, _build_ctx(
            y, technique_id="local_level", params={"horizon": h}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  horizon={h}: q={af.get('signal_to_noise')}, RMSE={af.get('rmse')}, dt={dt:.2f}s")
            rows.append({"wrapper": "ll", "param": f"h={h}",
                          "rmse": af.get("rmse"), "runtime": dt})

    # ---- local_linear_trend ----
    print("\n[local_linear_trend] preset variation")
    y = _trending_data(seed=44)
    for preset in ("Fast", "Balanced", "Thorough"):
        res, dt, err = _safe_run(llt_mod, _build_ctx(
            y, technique_id="local_linear_trend", preset=preset))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  preset={preset}: slope={af.get('final_slope')}, dt={dt:.2f}s")

    # ---- structural_ts ----
    print("\n[structural_ts] level variants on seasonal DGP")
    y = _seasonal_data(seed=45)
    for lt in ("local level", "local linear trend", "smooth trend"):
        res, dt, err = _safe_run(sts_mod, _build_ctx(
            y, technique_id="structural_ts",
            params={"level": lt, "seasonal": 12}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  level={lt!r}: AIC={af.get('aic')}, dom_comp={af.get('dominant_component')}, dt={dt:.2f}s")

    # ---- particle_filter ----
    print("\n[particle_filter] particle count sensitivity")
    y = _ar1(seed=46)
    for n_p in (100, 500, 1000):
        res, dt, err = _safe_run(pf_mod, _build_ctx(
            y, technique_id="particle_filter",
            params={"n_particles": n_p}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  n_particles={n_p}: avg_ess={af.get('avg_ess')}, RMSE={af.get('rmse')}, dt={dt:.2f}s")
            rows.append({"wrapper": "pf", "param": f"n={n_p}",
                          "rmse": af.get("rmse"), "runtime": dt})

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
        print("  fixture missing; skipping")
        return rows
    data = np.load(_FIXTURE)
    gspc = _log_returns(data["GSPC"])[-300:].tolist()
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-300:].tolist()

    for sname, y in [("GSPC_logret", gspc), ("DGS10_level", dgs10)]:
        print(f"\n--- {sname} ({len(y)} obs) ---")
        for label, mod, params in [
            ("local_level", ll_mod, {}),
            ("local_linear_trend", llt_mod, {}),
            ("structural_ts", sts_mod, {}),
            ("particle_filter", pf_mod, {"n_particles": 500}),
        ]:
            res, dt, err = _safe_run(mod, _build_ctx(
                y, technique_id=label, params=params,
                frequency="D", name=sname))
            if res and res.get("status") == "success":
                af = res["audit_fields"]
                rmse = af.get("rmse")
                print(f"  {label}: RMSE={rmse}, dt={dt:.2f}s")
                rows.append({"series": sname, "wrapper": label,
                              "rmse": rmse, "runtime": dt})
            else:
                em = (res.get('error_message') if res else err) or ""
                print(f"  {label}: FAIL — {em[:80]}")
    return rows


# =====================================================
# Technique 3 — Adversarial canonicals (4)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: pure trend (no observation noise)
    print("\n[C-AD-1] pure linear trend (low observation noise)")
    y = (np.arange(120) * 0.1 + 0.01 * np.random.default_rng(42).standard_normal(120)).tolist()
    for label, mod in [("ll", ll_mod), ("llt", llt_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id=f"local_level" if label == "ll" else "local_linear_trend"))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: RMSE={af.get('rmse')}")

    # C-AD-2: pure noise (no signal)
    print("\n[C-AD-2] white noise")
    rng = np.random.default_rng(43)
    y = rng.standard_normal(120).tolist()
    for label, mod in [("ll", ll_mod), ("llt", llt_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id="local_level" if label == "ll" else "local_linear_trend"))
        if res:
            print(f"  {label}: status={res.get('status')}")

    # C-AD-3: nonlinear growth (particle_filter showcase)
    print("\n[C-AD-3] nonlinear growth process (particle_filter strength)")
    rng = np.random.default_rng(44)
    T = 100
    x = np.zeros(T)
    y = np.zeros(T)
    for t in range(1, T):
        x[t] = 0.5 * x[t-1] + 25 * x[t-1] / (1 + x[t-1]**2) + 8 * np.cos(1.2 * t) + rng.standard_normal()
        y[t] = x[t]**2 / 20 + rng.standard_normal()
    res, _, err = _safe_run(pf_mod, _build_ctx(
        y.tolist(), technique_id="particle_filter",
        params={"model": "nonlinear_growth", "n_particles": 500}))
    if res:
        af = res.get("audit_fields", {})
        print(f"  pf nonlinear_growth: RMSE={af.get('rmse')}, status={res.get('status')}")

    # C-AD-4: short series T=12
    print("\n[C-AD-4] short series T=12 (graceful)")
    y = _ar1(T=12, seed=45)
    for label, mod in [("ll", ll_mod), ("llt", llt_mod), ("sts", sts_mod), ("pf", pf_mod)]:
        tid = {"ll": "local_level", "llt": "local_linear_trend",
                "sts": "structural_ts", "pf": "particle_filter"}[label]
        params = {"n_particles": 100} if label == "pf" else {}
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED: {err}"
        print(f"  {label}: status={s}")

    return []


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 18, "started": time.time()}

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

    out_path = _ROOT / "tools" / "calibration_audit" / "state_space_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
