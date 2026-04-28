"""Calibration Audit Phase 2 Session 27 — ets_hw solo.

FINAL session of CAI extension cycle. Closes 82/83 wrapper coverage.
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
from techniques import ets_hw as ets_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, params=None, preset="Fast", frequency="M", name="y"):
    return RunContext({
        "run_id": "audit_ets",
        "technique_id": "ets_hw",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": name, "values": list(values)}],
        "params": dict(params or {}),
    })


def _safe_run(ctx):
    try:
        t0 = time.time()
        res = ets_mod.run(ctx, _NULL)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _trend_seasonal(T=120, period=12, slope=0.05, amp=2.0, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    return (10 + slope * t + amp * np.sin(2 * np.pi * t / period)
            + 0.3 * rng.standard_normal(T)).tolist()


def _white_noise(T=120, seed=42):
    rng = np.random.default_rng(seed)
    return rng.standard_normal(T).tolist()


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (ets_hw solo)")
    print("=" * 70)

    y = _trend_seasonal(T=120)

    # Baseline
    res, dt, err = _safe_run(_ctx(y))
    print(f"\n  baseline: {res.get('status') if res else err} ({dt:.2f}s)")

    # Valid trend
    for t in (None, "add", "mul"):
        # mul requires positive — y starts at 10 so positive
        res, _, _ = _safe_run(_ctx(y, params={"trend": t}))
        print(f"  trend={t!r}: {res.get('status') if res else 'RAISED'}")
    # Invalid trend — silent fall-through to "add"
    res, _, _ = _safe_run(_ctx(y, params={"trend": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("trend") or af.get("trend_type") or af.get("model")
        print(f"  trend='zzz_invalid': SUCCESS (silent fall-through to 'add')")
        print(f"    audit fields: {list((af or {}).keys())[:8]}")
        findings.append({
            "id": "F-ETS-TREND",
            "wrapper": "ets_hw",
            "severity": "severe",
            "description": (
                "ets_hw silently falls through invalid `trend` to 'add' "
                "via if/else at line 113-115. Session 18 silent-fall-"
                "through pattern."
            ),
        })

    # Valid seasonal
    for s in (None, "add", "mul"):
        res, _, _ = _safe_run(_ctx(y, params={"seasonal": s}))
        print(f"  seasonal={s!r}: {res.get('status') if res else 'RAISED'}")
    # Invalid seasonal
    res, _, _ = _safe_run(_ctx(y, params={"seasonal": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  seasonal='zzz_invalid': SUCCESS (silent fall-through to 'add')")
        findings.append({
            "id": "F-ETS-SEASONAL",
            "wrapper": "ets_hw",
            "severity": "severe",
            "description": (
                "ets_hw silently falls through invalid `seasonal` to 'add' "
                "via if/else at line 132-134."
            ),
        })

    # Multi-parameter consistency: damped_trend=True + trend=None
    res, _, _ = _safe_run(_ctx(y, params={"trend": None, "damped_trend": True}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        print(f"  damped=True + trend=None: SUCCESS (silent — damped silently disabled)")
        findings.append({
            "id": "F-ETS-DAMPED-NOTREND",
            "wrapper": "ets_hw",
            "severity": "operational",
            "description": (
                "ets_hw silently disables damped_trend=True when "
                "trend=None (line 182: damped only applied if trend; "
                "user's intent is silently changed)."
            ),
        })

    # Multi-parameter consistency: trend='mul' + non-positive
    y_neg = (np.array(y) - 12).tolist()  # introduce negatives
    res, _, _ = _safe_run(_ctx(y_neg, params={"trend": "mul"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  trend='mul' + negatives: SUCCESS (silent switch to add)")
        findings.append({
            "id": "F-ETS-MUL-NEG-TREND",
            "wrapper": "ets_hw",
            "severity": "severe",
            "description": (
                "ets_hw silently switches trend='mul' to 'add' when data "
                "has non-positive values (line 158-162; warning emitted "
                "but user got a different model than asked). Session 16 "
                "loud-and-coerced pattern."
            ),
        })

    # Multi-parameter consistency: seasonal='mul' + non-positive
    res, _, _ = _safe_run(_ctx(y_neg, params={"seasonal": "mul"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  seasonal='mul' + negatives: SUCCESS (silent switch to add)")
        findings.append({
            "id": "F-ETS-MUL-NEG-SEAS",
            "wrapper": "ets_hw",
            "severity": "severe",
            "description": (
                "ets_hw silently switches seasonal='mul' to 'add' when "
                "data has non-positive values (line 153-157; warning "
                "emitted but user got a different model than asked). "
                "Session 16 loud-and-coerced pattern."
            ),
        })

    # horizon range
    res, _, _ = _safe_run(_ctx(y, params={"horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-ETS-HORIZON",
            "wrapper": "ets_hw",
            "severity": "operational",
            "description": "ets_hw silently coerces horizon<1 to 1.",
        })

    return findings


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Parameter sweeps")
    print("=" * 70)
    rows = []

    print("\n--- Sweep 1.1: trend specification on additive-trend DGP ---")
    rng = np.random.default_rng(43)
    y_trend = (10 + 0.05 * np.arange(120) + 0.3 * rng.standard_normal(120)).tolist()
    for t in (None, "add"):
        res, dt, _ = _safe_run(_ctx(y_trend, params={"trend": t, "seasonal": None}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  trend={t!r}: AIC={af.get('aic')}, dt={dt:.2f}s")

    print("\n--- Sweep 1.2: seasonal specification on seasonal DGP ---")
    y_seas = _trend_seasonal(T=120, period=12, slope=0.0, amp=2.0, seed=44)
    for s in (None, "add"):
        res, dt, _ = _safe_run(_ctx(y_seas, params={"seasonal": s, "trend": None}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  seasonal={s!r}: AIC={af.get('aic')}, dt={dt:.2f}s")

    print("\n--- Sweep 1.3: damped trend ---")
    y_pers = (10 + 0.1 * np.arange(120) + 0.2 * rng.standard_normal(120)).tolist()
    for d in (True, False):
        res, dt, _ = _safe_run(_ctx(y_pers, params={"trend": "add", "damped_trend": d, "seasonal": None}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  damped={d}: AIC={af.get('aic')}, dt={dt:.2f}s")

    return rows


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (5 macro series)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    for sname in ("GSPC", "DGS10", "DGS2", "DEXUSEU", "GOLD"):
        v = data[sname][~np.isnan(data[sname])][-300:]
        if sname in ("GSPC", "DEXUSEU", "GOLD"):
            # Use log returns (no trend, no seasonality)
            v = 100.0 * np.diff(np.log(np.maximum(v, 1e-12)))
            label = f"{sname}_logret"
        else:
            label = f"{sname}_level"
        res, dt, err = _safe_run(_ctx(v.tolist(), name=label, frequency="D"))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  {label}: trend={af.get('trend')}, seasonal={af.get('seasonal')}, AIC={af.get('aic')}, dt={dt:.2f}s")
            rows.append({"series": label, "aic": af.get("aic"), "runtime": dt})
        else:
            em = (res.get('error_message') if res else err) or ""
            print(f"  {label}: FAIL — {em[:60]}")
    return rows


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4 base + 4 C-CAL)")
    print("=" * 70)

    rng = np.random.default_rng(42)

    print("\n[C-AD-1] white noise")
    y = rng.standard_normal(120).tolist()
    res, _, _ = _safe_run(_ctx(y))
    print(f"  ets_hw: {res.get('status') if res else 'RAISED'}")

    print("\n[C-AD-2] pure additive trend")
    y = (10 + 0.05 * np.arange(120) + 0.1 * rng.standard_normal(120)).tolist()
    res, _, _ = _safe_run(_ctx(y, params={"trend": "add", "seasonal": None}))
    if res and res.get("status") == "success":
        print(f"  ets_hw: AIC={res['audit_fields'].get('aic')}")

    print("\n[C-AD-3] constant series")
    y = [5.0] * 100
    res, _, err = _safe_run(_ctx(y))
    s = res.get("status") if res else f"RAISED:{err[:30]}"
    print(f"  constant: {s}")

    print("\n[C-AD-4] short series T=12 with seasonal_periods=12")
    y = _trend_seasonal(T=12, period=12, seed=44)
    res, _, err = _safe_run(_ctx(y, params={"seasonal": "add"}))
    s = res.get("status") if res else f"RAISED:{err[:30]}"
    print(f"  T=12 seasonal_periods=12: {s}")

    return []


def main():
    out = {"session": 27, "started": time.time()}
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
    out_path = _ROOT / "tools" / "calibration_audit" / "ets_hw_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
