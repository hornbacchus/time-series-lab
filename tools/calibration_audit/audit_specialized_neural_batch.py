"""Calibration Audit Phase 2 Session 25 — Specialized Neural batch.

Three wrappers:
  - nhits_forecast (probe Session 24 N-BEATS pattern)
  - autoencoder_anomaly
  - echo_state_network
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
from techniques import nhits_forecast as nh_mod
from techniques import autoencoder_anomaly as ae_mod
from techniques import echo_state_network as esn_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, technique_id, params=None,
         preset="Fast", frequency="D", name="y"):
    return RunContext({
        "run_id": "audit_sn",
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


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


_NH_SMALL = {"epochs": 5, "n_stacks": 2, "n_blocks": 1, "hidden_size": 16, "n_lags": 8}
_AE_SMALL = {"epochs": 5, "hidden_dim": 16, "window_size": 12}
_ESN_SMALL = {"reservoir_size": 50, "warmup": 10}


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (3 wrappers)")
    print("=" * 70)

    y = _ar1(T=150)

    # ---- nhits_forecast ----
    print("\n[nhits_forecast]")
    res, dt, err = _safe_run(nh_mod, _ctx(y, technique_id="nhits_forecast",
                                              params=_NH_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # PRIORITY: stack_types probe (Session 24 N-BEATS pattern)
    res, _, _ = _safe_run(nh_mod, _ctx(y, technique_id="nhits_forecast",
                                          params={**_NH_SMALL, "pooling_sizes": "zzz"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("pooling_sizes")
        print(f"  pooling_sizes='zzz' (str instead of list): SUCCESS (silent fall-through)")
        print(f"    audit_fields.pooling_sizes = {recorded}")
        findings.append({
            "id": "F-SN-NHITS-POOLING",
            "wrapper": "nhits_forecast",
            "severity": "severe",
            "description": (
                "nhits_forecast silently falls through invalid "
                "`pooling_sizes` to preset default (line 331-338's "
                "try/except pass swallows TypeError on `list(str)`). "
                "Session 24 N-BEATS stack_types pattern PROPAGATES."
            ),
        })
    # Invalid pooling_sizes as list with negative values
    res, _, _ = _safe_run(nh_mod, _ctx(y, technique_id="nhits_forecast",
                                          params={**_NH_SMALL, "pooling_sizes": [-1, 0]}))
    if res and res.get("status") == "success":
        print(f"  pooling_sizes=[-1, 0]: SUCCESS (silent fall-through to preset)")
        findings.append({
            "id": "F-SN-NHITS-POOLING-NEG",
            "wrapper": "nhits_forecast",
            "severity": "severe",
            "description": (
                "nhits_forecast silently falls through invalid "
                "`pooling_sizes` containing non-positive values to "
                "preset default. Same Session 24 silent-fall-through "
                "pattern as pooling_sizes string param."
            ),
        })
    # horizon range
    res, _, _ = _safe_run(nh_mod, _ctx(y, technique_id="nhits_forecast",
                                          params={**_NH_SMALL, "horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-SN-NHITS-HORIZON",
            "wrapper": "nhits_forecast",
            "severity": "operational",
            "description": "nhits_forecast silently coerces horizon<1 to 1.",
        })

    # ---- autoencoder_anomaly ----
    print("\n[autoencoder_anomaly]")
    res, dt, err = _safe_run(ae_mod, _ctx(y, technique_id="autoencoder_anomaly",
                                              params=_AE_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # contamination range
    res, _, _ = _safe_run(ae_mod, _ctx(y, technique_id="autoencoder_anomaly",
                                          params={**_AE_SMALL, "contamination": 1.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        print(f"  contamination=1.5: SUCCESS (silent reset to 0.05)")
        findings.append({
            "id": "F-SN-AE-CONTAMINATION",
            "wrapper": "autoencoder_anomaly",
            "severity": "operational",
            "description": (
                "autoencoder_anomaly silently resets contamination "
                "out of (0,1) to 0.05 (with warning). Should reject "
                "explicitly per Session 19 numeric range protocol."
            ),
        })

    # ---- echo_state_network ----
    print("\n[echo_state_network]")
    res, dt, err = _safe_run(esn_mod, _ctx(y, technique_id="echo_state_network",
                                               params=_ESN_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # horizon range
    res, _, _ = _safe_run(esn_mod, _ctx(y, technique_id="echo_state_network",
                                            params={**_ESN_SMALL, "horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-SN-ESN-HORIZON",
            "wrapper": "echo_state_network",
            "severity": "operational",
            "description": "echo_state_network silently coerces horizon<1 to 1.",
        })
    # spectral_radius — should be >0; >>1 leads to unstable reservoir
    res, _, _ = _safe_run(esn_mod, _ctx(y, technique_id="echo_state_network",
                                            params={**_ESN_SMALL, "spectral_radius": -0.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  spectral_radius=-0.5: SUCCESS (silent)")
        findings.append({
            "id": "F-SN-ESN-SPECTRAL",
            "wrapper": "echo_state_network",
            "severity": "operational",
            "description": (
                "echo_state_network silently accepts negative "
                "spectral_radius (must be > 0; values >> 1 also "
                "unstable but technically the user's responsibility)."
            ),
        })
    # leak_rate range (must be in [0, 1])
    res, _, _ = _safe_run(esn_mod, _ctx(y, technique_id="echo_state_network",
                                            params={**_ESN_SMALL, "leak_rate": 1.5}))
    if res and res.get("status") == "success":
        print(f"  leak_rate=1.5: SUCCESS (silent)")
        findings.append({
            "id": "F-SN-ESN-LEAK",
            "wrapper": "echo_state_network",
            "severity": "operational",
            "description": (
                "echo_state_network silently accepts leak_rate "
                "out of [0, 1] (leaky-integrator parameter)."
            ),
        })

    return findings


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Parameter sweeps")
    print("=" * 70)
    rows = []
    y = _ar1(T=150, seed=43)

    print("\n[nhits] n_stacks sweep")
    for ns in (2, 3):
        res, dt, _ = _safe_run(nh_mod, _ctx(y, technique_id="nhits_forecast",
                                                params={**_NH_SMALL, "n_stacks": ns}))
        if res and res.get("status") == "success":
            print(f"  n_stacks={ns}: dt={dt:.2f}s")

    print("\n[autoencoder] hidden_dim sweep")
    for hd in (8, 16, 32):
        res, dt, _ = _safe_run(ae_mod, _ctx(y, technique_id="autoencoder_anomaly",
                                                params={**_AE_SMALL, "hidden_dim": hd}))
        if res and res.get("status") == "success":
            print(f"  hidden_dim={hd}: dt={dt:.2f}s")

    print("\n[esn] spectral_radius sweep")
    for sr in (0.5, 0.9, 1.2):
        res, dt, _ = _safe_run(esn_mod, _ctx(y, technique_id="echo_state_network",
                                                 params={**_ESN_SMALL, "spectral_radius": sr}))
        if res and res.get("status") == "success":
            print(f"  spectral_radius={sr}: dt={dt:.2f}s")

    return rows


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (DGS10 + GSPC subsampled)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-200:].tolist()
    gspc = _log_returns(data["GSPC"])[-200:].tolist()

    print("\n--- DGS10 (T=200) ---")
    for tid, mod, params, label in [
        ("nhits_forecast", nh_mod, _NH_SMALL, "nh"),
        ("autoencoder_anomaly", ae_mod, _AE_SMALL, "ae"),
        ("echo_state_network", esn_mod, _ESN_SMALL, "esn"),
    ]:
        res, dt, err = _safe_run(mod, _ctx(dgs10, technique_id=tid, params=params,
                                              name="DGS10"))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: status={s}, dt={dt:.2f}s")

    print("\n--- GSPC log returns (T=200, autoencoder anomaly check) ---")
    res, dt, _ = _safe_run(ae_mod, _ctx(gspc, technique_id="autoencoder_anomaly",
                                            params=_AE_SMALL, name="GSPC_logret"))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        n_anom = af.get("n_anomalies")
        print(f"  ae on GSPC: n_anomalies={n_anom}, dt={dt:.2f}s")
        rows.append({"wrapper": "ae", "n_anomalies": n_anom, "runtime": dt})

    return rows


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    rng = np.random.default_rng(42)

    print("\n[C-AD-1] white noise")
    y = rng.standard_normal(120).tolist()
    for tid, mod, params, label in [
        ("nhits_forecast", nh_mod, _NH_SMALL, "nh"),
        ("autoencoder_anomaly", ae_mod, _AE_SMALL, "ae"),
        ("echo_state_network", esn_mod, _ESN_SMALL, "esn"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    print("\n[C-AD-2] pure trend (forecast)")
    y = (np.arange(150) * 0.1 + 0.05 * rng.standard_normal(150)).tolist()
    for tid, mod, params, label in [
        ("nhits_forecast", nh_mod, _NH_SMALL, "nh"),
        ("echo_state_network", esn_mod, _ESN_SMALL, "esn"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    print("\n[C-AD-3] short series T=30")
    y = _ar1(T=30, seed=44)
    for tid, mod, params, label in [
        ("nhits_forecast", nh_mod, {**_NH_SMALL, "n_lags": 4}, "nh"),
        ("autoencoder_anomaly", ae_mod, {**_AE_SMALL, "window_size": 4}, "ae"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    print("\n[C-AD-4] constant series")
    y = [1.0] * 100
    for tid, mod, params, label in [
        ("autoencoder_anomaly", ae_mod, _AE_SMALL, "ae"),
        ("echo_state_network", esn_mod, _ESN_SMALL, "esn"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    return []


def main():
    out = {"session": 25, "started": time.time()}
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
    out_path = _ROOT / "tools" / "calibration_audit" / "specialized_neural_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
