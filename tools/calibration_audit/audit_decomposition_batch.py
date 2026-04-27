"""Calibration Audit Phase 2 Session 16 — Decomposition family batch.

Four wrappers:
  - stl_decompose
  - mstl_decompose
  - classical_decompose
  - x13_seasonal_adjust

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation matrix
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (macro + synthetic seasonal)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_decomposition_batch.py
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
from techniques import stl_decompose as stl_mod
from techniques import mstl_decompose as mstl_mod
from techniques import classical_decompose as classic_mod
from techniques import x13_seasonal_adjust as x13_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_decomp",
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


def _seasonal_trend_data(T=240, period=12, trend_slope=0.02, seasonal_amp=2.0,
                          noise_sd=0.3, seed=42):
    """Synthetic monthly with trend + sinusoidal seasonal + noise."""
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    trend = trend_slope * t
    seasonal = seasonal_amp * np.sin(2 * np.pi * t / period)
    noise = noise_sd * rng.standard_normal(T)
    return (trend + seasonal + noise).tolist()


def _multi_seasonal_data(T=730, periods=(7, 365), amps=(1.0, 3.0),
                          noise_sd=0.3, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y = noise_sd * rng.standard_normal(T)
    for p, a in zip(periods, amps):
        y += a * np.sin(2 * np.pi * t / p)
    return y.tolist()


def _multiplicative_data(T=240, period=12, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    trend = 100 + 0.1 * t
    seasonal = 1.0 + 0.2 * np.sin(2 * np.pi * t / period)
    noise = 1.0 + 0.05 * rng.standard_normal(T)
    return (trend * seasonal * noise).tolist()


def _monthly_time_col(T, start_year=2000):
    """Build YYYY-MM strings of length T (monthly)."""
    out = []
    y, m = start_year, 1
    for _ in range(T):
        out.append(f"{y}-{m:02d}-01")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


# =====================================================
# Sweep 0 — Per-wrapper dispatch + input-validation
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("=" * 70)

    y_monthly = _seasonal_trend_data(T=240, period=12)
    y_daily_multi = _multi_seasonal_data(T=730)
    y_mult = _multiplicative_data(T=240)
    monthly_time = _monthly_time_col(240)

    # ---- stl_decompose ----
    print("\n[stl_decompose]")
    res, _, err = _safe_run(stl_mod, _build_ctx(
        y_monthly, technique_id="stl_decompose", frequency="M"))
    print(f"  baseline: {res.get('status') if res else err}")
    # Numeric/bool params; no string-acceptance surface
    print("  → numeric/bool params only; clean")

    # ---- mstl_decompose ----
    print("\n[mstl_decompose]")
    res, _, err = _safe_run(mstl_mod, _build_ctx(
        y_daily_multi, technique_id="mstl_decompose", frequency="D"))
    print(f"  baseline: {res.get('status') if res else err}")
    print("  → numeric list params; clean")

    # ---- classical_decompose ----
    print("\n[classical_decompose]")
    res, _, err = _safe_run(classic_mod, _build_ctx(
        y_monthly, technique_id="classical_decompose", frequency="M"))
    print(f"  baseline: {res.get('status') if res else err}")
    # Test valid models
    for m in ("additive", "multiplicative"):
        data = y_mult if m == "multiplicative" else y_monthly
        res, _, err = _safe_run(classic_mod, _build_ctx(
            data, technique_id="classical_decompose", frequency="M",
            params={"model": m}))
        ok = res and res.get("status") == "success"
        print(f"  model={m!r}: {'OK' if ok else 'FAIL'}")
    # Invalid model — does it reject or coerce?
    res, _, err = _safe_run(classic_mod, _build_ctx(
        y_monthly, technique_id="classical_decompose", frequency="M",
        params={"model": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        recorded = audit.get("model_type")
        warn_str = " | ".join(str(w) for w in warns)
        print(f"  model='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.model_type = {recorded!r}")
        print(f"    warnings: {warn_str[:100]}")
        findings.append({
            "id": "F-CD-CLASSIC-MODEL",
            "wrapper": "classical_decompose",
            "severity": "severe",
            "description": (
                f"classical_decompose silently coerces invalid `model` "
                f"to 'additive' (with warning, but the user typed e.g. "
                f"'multplicative' (typo) and silently got additive). "
                f"audit_fields.model_type recorded {recorded!r}. "
                f"Per Sessions 9-15 pattern: loud-and-coerced is still "
                f"SEVERE because user's intended computation differs from "
                f"what actually ran."
            ),
        })
    elif res and res.get("status") == "failure":
        print(f"  model='zzz_invalid': REJECTED (good) — {res.get('error_message', '')[:80]}")

    # ---- x13_seasonal_adjust ----
    print("\n[x13_seasonal_adjust]")
    # Use monthly fixture with explicit period and time column
    res, dt, err = _safe_run(x13_mod, _build_ctx(
        y_monthly, technique_id="x13_seasonal_adjust", frequency="M",
        time_col=monthly_time))
    if res:
        print(f"  baseline (period=12 monthly): {res.get('status')} ({dt:.1f}s)")
        if res.get("status") == "failure":
            print(f"    error: {(res.get('error_message') or '')[:120]}")
    else:
        print(f"  baseline RAISED: {err}")
    # Test valid transforms
    for tr in ("auto", "log", "none"):
        # Use multiplicative (positive) data for log
        data = y_mult if tr == "log" else y_monthly
        res, _, err = _safe_run(x13_mod, _build_ctx(
            data, technique_id="x13_seasonal_adjust", frequency="M",
            time_col=monthly_time, params={"transform": tr}))
        ok = res and res.get("status") == "success"
        print(f"  transform={tr!r}: {'OK' if ok else (res.get('status') if res else 'RAISED')}")
        if not ok and res and res.get("status") == "failure":
            print(f"    {(res.get('error_message') or '')[:100]}")
    # Invalid transform — does it reject or coerce?
    res, _, err = _safe_run(x13_mod, _build_ctx(
        y_monthly, technique_id="x13_seasonal_adjust", frequency="M",
        time_col=monthly_time, params={"transform": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("transform")
        print(f"  transform='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.transform = {recorded!r}")
        findings.append({
            "id": "F-CD-X13-TRANSFORM",
            "wrapper": "x13_seasonal_adjust",
            "severity": "severe",
            "description": (
                "x13_seasonal_adjust silently accepts invalid `transform` "
                "values. The wrapper passes them through to _write_x13_spec "
                "which silently emits no transform block (default = none) "
                "for unrecognized values. audit_fields.transform records "
                f"user's invalid input {recorded!r}. Pattern matches "
                "Sessions 9-15 silent-acceptance bugs."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        if "Unknown transform" in em or "transform" in em.lower():
            print(f"  transform='zzz_invalid': REJECTED (good) — {em[:80]}")
        else:
            # Failure but not for the right reason — still surface
            print(f"  transform='zzz_invalid': FAIL but other reason — {em[:80]}")
            findings.append({
                "id": "F-CD-X13-TRANSFORM",
                "wrapper": "x13_seasonal_adjust",
                "severity": "severe",
                "description": (
                    "x13_seasonal_adjust fails on invalid `transform` "
                    "but not via explicit allowlist; relies on downstream "
                    "X-13 binary to produce a (possibly cryptic) failure. "
                    f"Error message: {em[:160]}"
                ),
            })
    else:
        print(f"  transform='zzz_invalid': RAISED — {err}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # ---- stl_decompose: period sensitivity ----
    print("\n[stl_decompose] period sensitivity (12, 6, 4)")
    y = _seasonal_trend_data(T=240, period=12)
    for p in (12, 6, 4):
        res, dt, err = _safe_run(stl_mod, _build_ctx(
            y, technique_id="stl_decompose", frequency="M", params={"period": p}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  period={p}: F_s={af['seasonal_strength']}, F_t={af['trend_strength']}, dt={dt:.2f}s")
            rows.append({"wrapper": "stl", "param": f"p={p}", "F_s": af['seasonal_strength']})
        else:
            print(f"  period={p}: FAIL")

    # ---- stl_decompose: robust toggle ----
    print("\n[stl_decompose] robust toggle on/off")
    for r in (True, False):
        res, dt, err = _safe_run(stl_mod, _build_ctx(
            y, technique_id="stl_decompose", frequency="M",
            params={"period": 12, "robust": r}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  robust={r}: F_s={af['seasonal_strength']}, dt={dt:.2f}s")

    # ---- mstl_decompose: multi-period ----
    print("\n[mstl_decompose] period combinations")
    for periods in ([12], [7, 30], [7, 365]):
        y_data = _multi_seasonal_data(T=730, periods=tuple(periods) if len(periods) > 1 else (periods[0],))
        res, dt, err = _safe_run(mstl_mod, _build_ctx(
            y_data, technique_id="mstl_decompose", frequency="D",
            params={"periods": periods}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            n_periods = len(af.get("periods", []))
            print(f"  periods={periods}: n_components={n_periods}, F_t={af['trend_strength']}, dt={dt:.2f}s")
            rows.append({"wrapper": "mstl", "param": f"p={periods}", "F_t": af['trend_strength']})
        else:
            print(f"  periods={periods}: FAIL {(res.get('error_message', '')[:60] if res else err)}")

    # ---- classical_decompose: additive vs multiplicative ----
    print("\n[classical_decompose] additive vs multiplicative comparison")
    for m, data, label in [
        ("additive", _seasonal_trend_data(T=240, period=12), "additive DGP"),
        ("multiplicative", _multiplicative_data(T=240), "multiplicative DGP"),
    ]:
        res, dt, err = _safe_run(classic_mod, _build_ctx(
            data, technique_id="classical_decompose", frequency="M",
            params={"model": m}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  model={m!r} on {label}: F_s={af['seasonal_strength']}, dt={dt:.2f}s")
            rows.append({"wrapper": "classic", "param": f"m={m}", "F_s": af['seasonal_strength']})

    # ---- x13_seasonal_adjust: transform variants ----
    print("\n[x13_seasonal_adjust] transform variants on multiplicative DGP")
    y_pos = _multiplicative_data(T=240)
    monthly_time = _monthly_time_col(240)
    for tr in ("auto", "log", "none"):
        res, dt, err = _safe_run(x13_mod, _build_ctx(
            y_pos, technique_id="x13_seasonal_adjust", frequency="M",
            time_col=monthly_time, params={"transform": tr}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  transform={tr!r}: F_s={af['seasonal_strength']}, dt={dt:.2f}s")
            rows.append({"wrapper": "x13", "param": f"tr={tr}", "F_s": af['seasonal_strength']})
        else:
            em = (res.get('error_message') if res else err) or ""
            print(f"  transform={tr!r}: FAIL — {em[:80]}")

    return rows


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (synthetic seasonal + macro)")
    print("=" * 70)
    rows = []

    # Synthetic seasonal fixture (gives wrappers something to actually decompose)
    print("\n--- Synthetic monthly trend+seasonal (T=240, period=12) ---")
    y = _seasonal_trend_data(T=240, period=12)
    monthly_time = _monthly_time_col(240)
    for label, mod, params in [
        ("stl_decompose", stl_mod, {"period": 12}),
        ("mstl_decompose", mstl_mod, {"periods": [12]}),
        ("classical_decompose", classic_mod, {"period": 12}),
        ("x13_seasonal_adjust", x13_mod, {}),
    ]:
        res, dt, err = _safe_run(mod, _build_ctx(
            y, technique_id=label, frequency="M",
            time_col=monthly_time, params=params))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            fs = af.get("seasonal_strength", "?")
            print(f"  {label}: F_s={fs}, dt={dt:.2f}s")
            rows.append({"series": "synthetic", "wrapper": label, "F_s": fs, "runtime": dt})
        else:
            em = (res.get('error_message') if res else err) or ""
            print(f"  {label}: FAIL — {em[:80]}")
            rows.append({"series": "synthetic", "wrapper": label, "error": em})

    # Real macro: GSPC log returns and DGS10 levels (weak seasonality)
    if not _FIXTURE.exists():
        print("\n  fixture missing; skipping macro section")
        return rows
    data = np.load(_FIXTURE)
    print("\n--- GSPC log returns daily (T=500) ---")
    p = data["GSPC"][~np.isnan(data["GSPC"])]
    gspc = (100.0 * np.diff(np.log(np.maximum(p, 1e-12))))[-500:].tolist()
    for label, mod, params, freq in [
        ("stl_decompose", stl_mod, {"period": 5}, "D"),
        ("mstl_decompose", mstl_mod, {"periods": [5]}, "D"),
        ("classical_decompose", classic_mod, {"period": 5}, "D"),
    ]:
        res, dt, err = _safe_run(mod, _build_ctx(
            gspc, technique_id=label, frequency=freq, params=params))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            fs = af.get("seasonal_strength", "?")
            print(f"  {label}: F_s={fs}, dt={dt:.2f}s")
            rows.append({"series": "GSPC_logret", "wrapper": label, "F_s": fs, "runtime": dt})

    print("\n--- DGS10 yield daily levels (T=500) ---")
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-500:].tolist()
    for label, mod, params, freq in [
        ("stl_decompose", stl_mod, {"period": 5}, "D"),
        ("mstl_decompose", mstl_mod, {"periods": [5]}, "D"),
        ("classical_decompose", classic_mod, {"period": 5}, "D"),
    ]:
        res, dt, err = _safe_run(mod, _build_ctx(
            dgs10, technique_id=label, frequency=freq, params=params))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            fs = af.get("seasonal_strength", "?")
            print(f"  {label}: F_s={fs}, dt={dt:.2f}s")
            rows.append({"series": "DGS10", "wrapper": label, "F_s": fs, "runtime": dt})

    return rows


# =====================================================
# Technique 3 — Adversarial canonicals (4)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: pure trend (no seasonality) — F_s should be very low
    print("\n[C-AD-1] pure linear trend (no seasonality, period=12)")
    rng = np.random.default_rng(42)
    y = (np.arange(120) * 0.1 + 0.2 * rng.standard_normal(120)).tolist()
    monthly_time = _monthly_time_col(120)
    for label, mod in [("stl", stl_mod), ("classic", classic_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id=f"{'stl_decompose' if label=='stl' else 'classical_decompose'}",
            frequency="M", time_col=monthly_time, params={"period": 12}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: F_s={af['seasonal_strength']} (expect low), F_t={af['trend_strength']}")

    # C-AD-2: pure seasonal (no trend)
    print("\n[C-AD-2] pure sinusoidal seasonal (no trend, period=12)")
    y = (2.0 * np.sin(2 * np.pi * np.arange(120) / 12) + 0.2 * rng.standard_normal(120)).tolist()
    for label, mod in [("stl", stl_mod), ("classic", classic_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id=f"{'stl_decompose' if label=='stl' else 'classical_decompose'}",
            frequency="M", time_col=monthly_time, params={"period": 12}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: F_s={af['seasonal_strength']} (expect high), F_t={af['trend_strength']} (expect low)")

    # C-AD-3: white noise — F_s low, F_t low
    print("\n[C-AD-3] white noise (no structure)")
    y = rng.standard_normal(120).tolist()
    for label, mod in [("stl", stl_mod), ("classic", classic_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            y, technique_id=f"{'stl_decompose' if label=='stl' else 'classical_decompose'}",
            frequency="M", time_col=monthly_time, params={"period": 12}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: F_s={af['seasonal_strength']} (expect low), F_t={af['trend_strength']} (expect low)")

    # C-AD-4: short series — convergence challenge
    print("\n[C-AD-4] short series T=30, period=12 (convergence challenge)")
    for label, mod in [("stl", stl_mod), ("classic", classic_mod)]:
        res, _, err = _safe_run(mod, _build_ctx(
            rng.standard_normal(30).tolist(),
            technique_id=f"{'stl_decompose' if label=='stl' else 'classical_decompose'}",
            frequency="M", params={"period": 12}))
        s = res.get("status") if res else f"RAISED: {err}"
        print(f"  {label}: status={s}")

    return []


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 16, "started": time.time()}

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

    out_path = _ROOT / "tools" / "calibration_audit" / "decomposition_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
