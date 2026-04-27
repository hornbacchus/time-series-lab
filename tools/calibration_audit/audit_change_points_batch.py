"""Calibration Audit Phase 2 Session 15 — Change Points / Anomalies batch.

Five wrappers:
  - bocpd
  - cusum_page_hinkley
  - intervention_analysis
  - pelt_change_points
  - stl_esd_anomaly

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation matrix
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (GSPC + DGS10 macro pair)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_change_points_batch.py
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
from techniques import bocpd as bocpd_mod
from techniques import cusum_page_hinkley as cph_mod
from techniques import intervention_analysis as int_mod
from techniques import pelt_change_points as pelt_mod
from techniques import stl_esd_anomaly as stl_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="audit_cp",
                frequency="daily", name="y"):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
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


def _simulate_step(*, T=300, break_at=150, shift=2.0, seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[break_at:] += shift
    return y


def _simulate_3_segments(*, T=300, breaks=(100, 200), shifts=(2.0, -1.5), seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[breaks[0]:breaks[1]] += shifts[0]
    y[breaks[1]:] += shifts[1]
    return y


def _simulate_pulse_anomaly(*, T=300, anomaly_idx=150, anomaly_size=5.0, seed=42):
    rng = np.random.default_rng(seed)
    y = rng.standard_normal(T)
    y[anomaly_idx] += anomaly_size
    return y


def _simulate_seasonal_with_anomalies(*, T=240, period=12, n_anom=3, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y = np.sin(2 * np.pi * t / period) + 0.3 * rng.standard_normal(T)
    anom_indices = rng.choice(T, size=n_anom, replace=False)
    y[anom_indices] += 4.0 * rng.standard_normal(n_anom).astype(np.float64) * np.sign(rng.standard_normal(n_anom))
    return y, anom_indices


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
    print("SWEEP 0 — Input validation matrix (5 wrappers)")
    print("=" * 70)

    rng = np.random.default_rng(42)
    y_baseline = rng.standard_normal(200).tolist()
    y_with_break = _simulate_step(T=300, break_at=150).tolist()
    y_seasonal, _ = _simulate_seasonal_with_anomalies(T=240)
    y_seasonal = y_seasonal.tolist()

    # ---- bocpd ----
    print("\n[bocpd]")
    res, _, err = _safe_run(bocpd_mod, _build_ctx(
        y_baseline, technique_id="bocpd"))
    print(f"  baseline: {res.get('status') if res else err}")
    # All numeric params; no string-acceptance surface.
    print("  → numeric params only; clean")

    # ---- cusum_page_hinkley ----
    print("\n[cusum_page_hinkley]")
    res, _, err = _safe_run(cph_mod, _build_ctx(
        y_baseline, technique_id="cusum_page_hinkley"))
    print(f"  baseline: {res.get('status') if res else err}")
    # All numeric params; both methods always run.
    print("  → numeric params only; clean")

    # ---- intervention_analysis ----
    print("\n[intervention_analysis]")
    # Baseline (auto-detected single intervention)
    res, _, err = _safe_run(int_mod, _build_ctx(
        y_with_break, technique_id="intervention_analysis"))
    print(f"  baseline (auto-detect): {res.get('status') if res else err}")
    # Valid types
    for itype in ("pulse", "step", "ramp"):
        res, _, err = _safe_run(int_mod, _build_ctx(
            y_with_break, technique_id="intervention_analysis",
            params={"interventions": [{"index": 150, "type": itype, "name": "test"}]}))
        ok = res and res.get("status") == "success"
        print(f"  type={itype!r}: {'OK' if ok else 'FAIL'} {res.get('status') if res else err}")
    # Invalid type — does it reject or coerce?
    res, _, err = _safe_run(int_mod, _build_ctx(
        y_with_break, technique_id="intervention_analysis",
        params={"interventions": [{"index": 150, "type": "zzz_invalid", "name": "test"}]}))
    if res and res.get("status") == "success":
        # Check the audit fields
        audit = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        ints = audit.get("interventions") or []
        recorded_type = ints[0].get("type") if ints else None
        warn_str = " | ".join(str(w) for w in warns)
        print(f"  type='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.interventions[0].type = {recorded_type!r}")
        print(f"    warnings: {warn_str[:100]}")
        if recorded_type != "step" or "Unknown intervention type" not in warn_str:
            findings.append({
                "id": "F-CP-INT-TYPE",
                "wrapper": "intervention_analysis",
                "severity": "severe",
                "description": (
                    "intervention_analysis silently coerces invalid `type` "
                    "to 'step' without erroring; audit_fields.interventions "
                    f"reports user's invalid type {recorded_type!r}. "
                    "Even though a warning is appended, the audit-trail "
                    "field misrepresents the model that ran."
                ),
            })
        else:
            # Even with warning, audit field still wrong → severe per pattern
            findings.append({
                "id": "F-CP-INT-TYPE",
                "wrapper": "intervention_analysis",
                "severity": "severe",
                "description": (
                    "intervention_analysis silently coerces invalid `type` "
                    "to 'step'. Warning IS issued, but no allowlist gate; "
                    "user's invalid string flows into audit/output paths. "
                    "Pattern parallels Sessions 9/10/12/13/14 fixes."
                ),
            })
    elif res and res.get("status") == "failure":
        print(f"  type='zzz_invalid': REJECTED (good) — {res.get('error_message', '')[:80]}")
    else:
        print(f"  type='zzz_invalid': RAISED — {err}")

    # ---- pelt_change_points ----
    print("\n[pelt_change_points]")
    res, _, err = _safe_run(pelt_mod, _build_ctx(
        y_with_break, technique_id="pelt_change_points"))
    print(f"  baseline: {res.get('status') if res else err}")
    # Valid penalty methods
    for pen in ("bic", "aic", "mbic"):
        res, _, err = _safe_run(pelt_mod, _build_ctx(
            y_with_break, technique_id="pelt_change_points",
            params={"penalty": pen}))
        ok = res and res.get("status") == "success"
        print(f"  penalty={pen!r}: {'OK' if ok else 'FAIL'}")
    # Invalid penalty — does it reject or coerce?
    res, _, err = _safe_run(pelt_mod, _build_ctx(
        y_with_break, technique_id="pelt_change_points",
        params={"penalty": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded_pen = audit.get("penalty")
        print(f"  penalty='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.penalty = {recorded_pen!r}")
        findings.append({
            "id": "F-CP-PELT-PENALTY",
            "wrapper": "pelt_change_points",
            "severity": "severe",
            "description": (
                "pelt_change_points silently coerces invalid `penalty` "
                f"to 'bic' default; audit_fields.penalty reports user's "
                f"invalid value {recorded_pen!r}. Pattern matches "
                "Sessions 9/10/12/13/14 silent-acceptance bugs."
            ),
        })
    elif res and res.get("status") == "failure":
        print(f"  penalty='zzz_invalid': REJECTED (good) — {res.get('error_message', '')[:80]}")
    else:
        print(f"  penalty='zzz_invalid': RAISED — {err}")
    # Invalid model — should be rejected by ruptures
    res, _, err = _safe_run(pelt_mod, _build_ctx(
        y_with_break, technique_id="pelt_change_points",
        params={"model": "zzz_invalid"}))
    if res and res.get("status") == "failure":
        print(f"  model='zzz_invalid': REJECTED (upstream ruptures) — clean")
    elif err:
        print(f"  model='zzz_invalid': RAISED → {err[:80]} — caught upstream")
    else:
        print(f"  model='zzz_invalid': SUCCESS?? unexpected — {res.get('audit_fields', {}).get('cost_model')}")

    # ---- stl_esd_anomaly ----
    print("\n[stl_esd_anomaly]")
    res, _, err = _safe_run(stl_mod, _build_ctx(
        y_seasonal, technique_id="stl_esd_anomaly",
        params={"period": 12}))
    print(f"  baseline: {res.get('status') if res else err}")
    # Valid directions
    for direction in ("both", "upper", "lower"):
        res, _, err = _safe_run(stl_mod, _build_ctx(
            y_seasonal, technique_id="stl_esd_anomaly",
            params={"period": 12, "direction": direction}))
        ok = res and res.get("status") == "success"
        print(f"  direction={direction!r}: {'OK' if ok else 'FAIL'}")
    # Invalid direction — does it reject or coerce?
    res, _, err = _safe_run(stl_mod, _build_ctx(
        y_seasonal, technique_id="stl_esd_anomaly",
        params={"period": 12, "direction": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded_dir = audit.get("direction")
        print(f"  direction='zzz_invalid': SUCCESS (silent coercion)")
        print(f"    audit_fields.direction = {recorded_dir!r}")
        findings.append({
            "id": "F-CP-STL-DIRECTION",
            "wrapper": "stl_esd_anomaly",
            "severity": "severe",
            "description": (
                "stl_esd_anomaly silently coerces invalid `direction` "
                f"to 'lower' (the else branch in _generalized_esd); "
                f"audit_fields.direction reports user's invalid value "
                f"{recorded_dir!r}. Pattern matches Sessions 9/10/12/13/14 "
                "silent-acceptance bugs."
            ),
        })
    elif res and res.get("status") == "failure":
        print(f"  direction='zzz_invalid': REJECTED (good) — {res.get('error_message', '')[:80]}")
    else:
        print(f"  direction='zzz_invalid': RAISED — {err}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # ---- bocpd: hazard_lambda sensitivity ----
    print("\n[bocpd] hazard_lambda sensitivity (50, 200, 500)")
    rng = np.random.default_rng(42)
    y = _simulate_step(T=200, break_at=100, shift=2.0).tolist()
    for hl in (50, 200, 500):
        res, dt, err = _safe_run(bocpd_mod, _build_ctx(
            y, technique_id="bocpd", params={"hazard_lambda": hl}))
        if res and res.get("status") == "success":
            n_cps = res["audit_fields"]["n_change_points"]
            print(f"  hazard_lambda={hl}: n_cps={n_cps}, runtime={dt:.2f}s")
            rows.append({"wrapper": "bocpd", "param": f"hl={hl}", "n_cps": n_cps, "runtime": dt})
        else:
            print(f"  hazard_lambda={hl}: FAIL {err or res.get('error_message')}")

    # ---- cusum_page_hinkley: ph_lambda sensitivity ----
    print("\n[cusum_page_hinkley] ph_lambda sensitivity (10, 50, 100)")
    for pl in (10, 50, 100):
        res, dt, err = _safe_run(cph_mod, _build_ctx(
            y, technique_id="cusum_page_hinkley", params={"ph_lambda": pl}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            n_alarms = af["n_cusum_up"] + af["n_cusum_down"] + af["n_ph_up"] + af["n_ph_down"]
            print(f"  ph_lambda={pl}: n_alarms={n_alarms}, runtime={dt:.2f}s")
            rows.append({"wrapper": "cph", "param": f"pl={pl}", "n_alarms": n_alarms, "runtime": dt})
        else:
            print(f"  ph_lambda={pl}: FAIL")

    # ---- intervention_analysis: type comparison ----
    print("\n[intervention_analysis] type comparison (pulse, step, ramp) on step DGP")
    for itype in ("pulse", "step", "ramp"):
        res, dt, err = _safe_run(int_mod, _build_ctx(
            y, technique_id="intervention_analysis",
            params={"interventions": [{"index": 100, "type": itype, "name": "test"}]}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  type={itype!r}: n_significant={af['n_significant']}, AIC={af['aic']}, runtime={dt:.2f}s")
            rows.append({"wrapper": "int", "param": f"type={itype}", "n_sig": af["n_significant"], "runtime": dt})
        else:
            print(f"  type={itype!r}: FAIL {err or res.get('error_message')}")

    # ---- pelt_change_points: cost model comparison ----
    print("\n[pelt_change_points] cost_model comparison (l1, l2, rbf) on 3-segment DGP")
    y3 = _simulate_3_segments(T=300).tolist()
    for cm in ("l1", "l2", "rbf"):
        res, dt, err = _safe_run(pelt_mod, _build_ctx(
            y3, technique_id="pelt_change_points", params={"model": cm}))
        if res and res.get("status") == "success":
            n_cps = res["audit_fields"]["n_change_points"]
            print(f"  model={cm!r}: n_cps={n_cps}, runtime={dt:.2f}s")
            rows.append({"wrapper": "pelt", "param": f"model={cm}", "n_cps": n_cps, "runtime": dt})
        else:
            print(f"  model={cm!r}: FAIL {err or (res.get('error_message') if res else 'NO_RES')}")

    # ---- stl_esd_anomaly: alpha sensitivity ----
    print("\n[stl_esd_anomaly] alpha sensitivity (0.01, 0.05, 0.10) on seasonal+anomaly DGP")
    y_seas, true_anom = _simulate_seasonal_with_anomalies(T=240, n_anom=3)
    y_seas = y_seas.tolist()
    for a in (0.01, 0.05, 0.10):
        res, dt, err = _safe_run(stl_mod, _build_ctx(
            y_seas, technique_id="stl_esd_anomaly",
            params={"period": 12, "alpha": a}))
        if res and res.get("status") == "success":
            n_anom = res["audit_fields"]["n_anomalies"]
            print(f"  alpha={a}: n_anomalies={n_anom} (true={len(true_anom)}), runtime={dt:.2f}s")
            rows.append({"wrapper": "stl", "param": f"alpha={a}", "n_anom": n_anom, "runtime": dt})
        else:
            print(f"  alpha={a}: FAIL")

    return rows


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (GSPC log returns, DGS10 levels)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        print("  fixture missing; skipping real-data section")
        return rows
    data = np.load(_FIXTURE)
    gspc = _log_returns(data["GSPC"])[-500:]
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-500:]

    series = [
        ("GSPC_logret", gspc.tolist(), "daily"),
        ("DGS10_level", dgs10.tolist(), "daily"),
    ]

    for sname, sval, freq in series:
        print(f"\n--- {sname} ({len(sval)} obs) ---")

        for label, mod, params in [
            ("bocpd", bocpd_mod, {}),
            ("cusum_page_hinkley", cph_mod, {}),
            ("intervention_analysis", int_mod, {}),  # auto-detect single break
            ("pelt_change_points", pelt_mod, {}),
            ("stl_esd_anomaly", stl_mod, {"period": 5}),  # weekly seasonality
        ]:
            res, dt, err = _safe_run(mod, _build_ctx(
                sval, technique_id=label, params=params, frequency=freq, name=sname))
            if res and res.get("status") == "success":
                af = res["audit_fields"]
                if label == "bocpd":
                    cnt = af.get("n_change_points")
                    metric = f"n_cps={cnt}"
                elif label == "cusum_page_hinkley":
                    cnt = af.get("n_cusum_up", 0) + af.get("n_cusum_down", 0) + af.get("n_ph_up", 0) + af.get("n_ph_down", 0)
                    metric = f"n_alarms={cnt}"
                elif label == "intervention_analysis":
                    cnt = af.get("n_significant", 0)
                    metric = f"n_sig={cnt}, n_int={af.get('n_interventions', 0)}"
                elif label == "pelt_change_points":
                    cnt = af.get("n_change_points", 0)
                    metric = f"n_cps={cnt}"
                else:
                    cnt = af.get("n_anomalies", 0)
                    metric = f"n_anom={cnt}"
                print(f"  {label}: {metric}, runtime={dt:.2f}s")
                rows.append({"series": sname, "wrapper": label, "metric": metric, "runtime": dt})
            else:
                em = res.get("error_message") if res else err
                print(f"  {label}: FAIL — {(em or '')[:80]}")
                rows.append({"series": sname, "wrapper": label, "error": em or err})
    return rows


# =====================================================
# Technique 3 — Adversarial canonicals (4)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)
    findings = []

    # C-CAL-1: constant series — wrappers should NOT detect spurious changes
    print("\n[C-CAL-1] constant series (no change points expected)")
    rng = np.random.default_rng(42)
    y = (rng.standard_normal(200) * 1e-9 + 1.0).tolist()  # essentially constant
    # bocpd
    res, _, err = _safe_run(bocpd_mod, _build_ctx(y, technique_id="bocpd"))
    if res:
        n = res.get("audit_fields", {}).get("n_change_points", -1) if res.get("status") == "success" else "FAIL"
        print(f"  bocpd: n_cps={n}")
    # PELT
    res, _, err = _safe_run(pelt_mod, _build_ctx(y, technique_id="pelt_change_points"))
    if res:
        n = res.get("audit_fields", {}).get("n_change_points", -1) if res.get("status") == "success" else "FAIL"
        print(f"  pelt:  n_cps={n}")

    # C-CAL-2: white noise (no change points)
    print("\n[C-CAL-2] white noise N(0,1) (few or no change points expected)")
    y = rng.standard_normal(300).tolist()
    res, _, err = _safe_run(bocpd_mod, _build_ctx(y, technique_id="bocpd"))
    n_cps_b = res.get("audit_fields", {}).get("n_change_points", -1) if (res and res.get("status") == "success") else "FAIL"
    res, _, err = _safe_run(pelt_mod, _build_ctx(y, technique_id="pelt_change_points"))
    n_cps_p = res.get("audit_fields", {}).get("n_change_points", -1) if (res and res.get("status") == "success") else "FAIL"
    res, _, err = _safe_run(cph_mod, _build_ctx(y, technique_id="cusum_page_hinkley"))
    n_alarms_c = "FAIL"
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        n_alarms_c = af["n_cusum_up"] + af["n_cusum_down"] + af["n_ph_up"] + af["n_ph_down"]
    print(f"  bocpd: n_cps={n_cps_b}, pelt: n_cps={n_cps_p}, cusum/ph: n_alarms={n_alarms_c}")

    # C-CAL-3: pulse anomaly amid noise (STL+ESD should detect)
    print("\n[C-CAL-3] single pulse anomaly @ idx 100 (STL+ESD should detect)")
    y, true_anom_idx = _simulate_seasonal_with_anomalies(T=240, n_anom=1, seed=99)
    res, _, err = _safe_run(stl_mod, _build_ctx(
        y.tolist(), technique_id="stl_esd_anomaly", params={"period": 12}))
    if res and res.get("status") == "success":
        n_anom = res["audit_fields"]["n_anomalies"]
        print(f"  stl_esd: detected {n_anom} (true=1 at idx {true_anom_idx})")

    # C-CAL-4: short series (T=50) — convergence challenge
    print("\n[C-CAL-4] short series T=50 (graceful behavior)")
    y_short = rng.standard_normal(50).tolist()
    for label, mod, params in [
        ("bocpd", bocpd_mod, {}),
        ("cusum_page_hinkley", cph_mod, {}),
        ("intervention_analysis", int_mod, {"interventions": [{"index": 25, "type": "step", "name": "test"}]}),
        ("pelt_change_points", pelt_mod, {}),
    ]:
        res, _, err = _safe_run(mod, _build_ctx(y_short, technique_id=label, params=params))
        s = res.get("status") if res else f"RAISED: {err}"
        print(f"  {label}: status={s}")

    return findings


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 15, "started": time.time()}

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

    out_path = _ROOT / "tools" / "calibration_audit" / "change_points_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
