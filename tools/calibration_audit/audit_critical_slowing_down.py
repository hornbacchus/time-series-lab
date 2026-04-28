"""Calibration Audit Phase 2 Session 28 — critical_slowing_down (deferred wrapper).

FINAL session of CAI Phase 2 — closes the only deferred wrapper.
Brings audit coverage to 83/83 (100%).

Deferral rationale: "too new at audit start" (CSD wrapper shipped
2026-04-25, CAI cycle started simultaneously). 3 days later the
wrapper is stable, existing canonical script passes regression,
deferral can lift.
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
from techniques import critical_slowing_down as csd_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, params=None, preset="Fast", frequency="D", name="y"):
    return RunContext({
        "run_id": "audit_csd",
        "technique_id": "critical_slowing_down",
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
        res = csd_mod.run(ctx, _NULL)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _approaching_bifurcation(T=600, seed=42):
    """Synthetic AR(1) with phi increasing toward 1 over time —
    classic CSD-positive DGP."""
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        # phi grows from 0.5 to 0.99 linearly over T
        phi = 0.5 + 0.49 * (t / T)
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _stationary_ar1(T=600, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (CSD solo)")
    print("=" * 70)

    y = _stationary_ar1(T=600)

    # Baseline
    res, dt, err = _safe_run(_ctx(y))
    print(f"\n  baseline: {res.get('status') if res else err} ({dt:.2f}s)")

    # detrending_method allowlist (already implemented)
    for d in ("gaussian", "first_diff", "linear"):
        res, _, _ = _safe_run(_ctx(y, params={"detrending_method": d}))
        print(f"  detrending_method={d}: {res.get('status') if res else 'RAISED'}")
    res, _, _ = _safe_run(_ctx(y, params={"detrending_method": "zzz_invalid"}))
    if res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  detrending_method='zzz_invalid': REJECTED (good) — {em[:60]}")
    else:
        print(f"  detrending_method='zzz_invalid': UNEXPECTED — {res.get('status') if res else 'RAISED'}")

    # composite_method (probable severe finding)
    for c in ("equal_weight_zscore", "fisher_combined"):
        params = {"composite_method": c, "compute_pvalues": True} if c == "fisher_combined" else {"composite_method": c}
        res, _, _ = _safe_run(_ctx(y, params=params))
        print(f"  composite_method={c}: {res.get('status') if res else 'RAISED'}")
    # Invalid composite_method
    res, _, _ = _safe_run(_ctx(y, params={"composite_method": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("composite_method")
        print(f"  composite_method='zzz_invalid': SUCCESS (silent fall-through to equal_weight_zscore)")
        print(f"    audit_fields.composite_method = {recorded!r}")
        findings.append({
            "id": "F-CSD-COMPOSITE",
            "wrapper": "critical_slowing_down",
            "severity": "severe",
            "description": (
                f"critical_slowing_down silently falls through invalid "
                f"`composite_method` to 'equal_weight_zscore' default "
                f"via if/else at _csd_helpers.py:_composite_ews_score "
                f"line 492/513. audit_fields.composite_method records "
                f"user's invalid value {recorded!r}. Session 18 "
                f"silent-fall-through pattern."
            ),
        })

    # Numeric range tests
    res, _, _ = _safe_run(_ctx(y, params={"rolling_window": 0}))
    if res and res.get("status") == "success":
        print(f"  rolling_window=0: SUCCESS (silent — falls back to default)")
        findings.append({
            "id": "F-CSD-ROLLINGWIN",
            "wrapper": "critical_slowing_down",
            "severity": "operational",
            "description": (
                "critical_slowing_down silently falls back to default "
                "rolling_window when user passes 0 (line 258-261 uses "
                "truthy check; 0 is falsy). User's intent is silently "
                "changed."
            ),
        })
    elif res and res.get("status") in ("failure", "insufficient_data"):
        em = res.get("error_message") or ""
        print(f"  rolling_window=0: rejected — {em[:60]}")

    res, _, _ = _safe_run(_ctx(y, params={"rolling_window": -10}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  rolling_window=-10: SUCCESS (silent)")
        findings.append({
            "id": "F-CSD-ROLLINGWIN-NEG",
            "wrapper": "critical_slowing_down",
            "severity": "severe",
            "description": (
                "critical_slowing_down silently accepts negative "
                "rolling_window. Bypasses the truthy-check at line "
                "258 and reaches int() conversion."
            ),
        })

    res, _, _ = _safe_run(_ctx(y, params={"n_surrogates": -10}))
    if res and res.get("status") == "success":
        print(f"  n_surrogates=-10: SUCCESS (silent)")
        findings.append({
            "id": "F-CSD-NSURR",
            "wrapper": "critical_slowing_down",
            "severity": "operational",
            "description": (
                "critical_slowing_down silently accepts negative "
                "n_surrogates."
            ),
        })

    res, _, _ = _safe_run(_ctx(y, params={"kendall_lookback": -5}))
    if res and res.get("status") == "success":
        print(f"  kendall_lookback=-5: SUCCESS (silent)")
        findings.append({
            "id": "F-CSD-KENDALL",
            "wrapper": "critical_slowing_down",
            "severity": "operational",
            "description": (
                "critical_slowing_down silently accepts negative "
                "kendall_lookback."
            ),
        })

    return findings


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Parameter sweeps")
    print("=" * 70)
    rows = []

    print("\n--- detrending method comparison on approaching-bifurcation DGP ---")
    y_bif = _approaching_bifurcation(T=600, seed=43)
    for d in ("gaussian", "first_diff", "linear"):
        res, dt, _ = _safe_run(_ctx(y_bif, params={"detrending_method": d}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            ews_score = af.get("ews_composite_score")
            ews_state = af.get("ews_state")
            print(f"  detrending={d}: EWS score={ews_score}, state={ews_state}, dt={dt:.2f}s")

    print("\n--- composite method comparison ---")
    for c in ("equal_weight_zscore", "fisher_combined"):
        params = {"composite_method": c}
        if c == "fisher_combined":
            params["compute_pvalues"] = True
        res, dt, _ = _safe_run(_ctx(y_bif, params=params))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  method={c}: EWS={af.get('ews_composite_score')}, dt={dt:.2f}s")

    print("\n--- rolling_window sensitivity ---")
    for w in (50, 100, 200):
        res, dt, _ = _safe_run(_ctx(y_bif, params={"rolling_window": w}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  rolling_window={w}: EWS={af.get('ews_composite_score')}, dt={dt:.2f}s")

    return rows


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (5 macro series; expect mostly null)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    for sname in ("GSPC", "DGS10", "DGS2", "DEXUSEU", "GOLD"):
        v = data[sname][~np.isnan(data[sname])][-2000:]
        if sname in ("GSPC", "DEXUSEU", "GOLD"):
            v = 100.0 * np.diff(np.log(np.maximum(v, 1e-12)))
            label = f"{sname}_logret"
        else:
            label = f"{sname}_level"
        res, dt, err = _safe_run(_ctx(v.tolist(), name=label))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            ews = af.get("ews_composite_score")
            state = af.get("ews_state")
            print(f"  {label}: EWS={ews}, state={state}, dt={dt:.2f}s")
            rows.append({"series": label, "ews": ews, "state": state, "runtime": dt})
        else:
            em = (res.get('error_message') if res else err) or ""
            print(f"  {label}: {res.get('status') if res else 'RAISED'} — {em[:60]}")

    print("\n--- Synthetic bifurcation (CSD-positive control) ---")
    y_bif = _approaching_bifurcation(T=800, seed=99)
    res, dt, _ = _safe_run(_ctx(y_bif, name="approaching_bif"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        ews = af.get("ews_composite_score")
        state = af.get("ews_state")
        print(f"  approaching_bifurcation: EWS={ews}, state={state}, dt={dt:.2f}s")
        rows.append({"series": "approaching_bif", "ews": ews, "state": state})

    return rows


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4 base + 4 C-CAL)")
    print("=" * 70)

    rng = np.random.default_rng(42)

    print("\n[C-AD-1] white noise — should be normal state")
    y = rng.standard_normal(600).tolist()
    res, _, _ = _safe_run(_ctx(y))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  white noise: EWS={af.get('ews_composite_score')}, state={af.get('ews_state')}")

    print("\n[C-AD-2] approaching bifurcation — should signal elevated/critical")
    y = _approaching_bifurcation(T=600, seed=100)
    res, _, _ = _safe_run(_ctx(y))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  bifurcation: EWS={af.get('ews_composite_score')}, state={af.get('ews_state')}")

    print("\n[C-AD-3] constant series — graceful")
    res, _, err = _safe_run(_ctx([5.0] * 600))
    s = res.get("status") if res else f"RAISED:{err[:30]}"
    print(f"  constant: {s}")

    print("\n[C-AD-4] short series T=100 — insufficient data guard")
    res, _, err = _safe_run(_ctx(_stationary_ar1(T=100)))
    s = res.get("status") if res else f"RAISED:{err[:30]}"
    print(f"  T=100: {s}")

    return []


def main():
    out = {"session": 28, "started": time.time()}
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
    out_path = _ROOT / "tools" / "calibration_audit" / "critical_slowing_down_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
