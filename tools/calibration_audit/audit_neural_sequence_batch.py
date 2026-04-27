"""Calibration Audit Phase 2 Session 24 — Neural sequence forecasters batch.

Four wrappers:
  - lstm_gru_forecast
  - tcn_forecast
  - transformer_forecast
  - nbeats_forecast

Sweep 0 + Technique 1 + 2 + 3.
Note: neural training is computationally expensive — uses small models
(hidden_size=16-32, epochs=5-10, T<=200) for tractable audit runtimes.
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
from techniques import lstm_gru_forecast as lg_mod
from techniques import tcn_forecast as tcn_mod
from techniques import transformer_forecast as tf_mod
from techniques import nbeats_forecast as nb_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, technique_id, params=None,
         preset="Fast", frequency="D", name="y"):
    return RunContext({
        "run_id": "audit_nn",
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


def _ar1(T=100, phi=0.5, seed=42):
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + rng.standard_normal()
    return y.tolist()


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


# Small model defaults for audit speed
_SMALL = {"epochs": 5, "hidden_size": 16, "n_lags": 8}
_TF_SMALL = {"epochs": 5, "d_model": 16, "n_heads": 2, "n_lags": 8,
              "n_encoder_layers": 1, "dim_feedforward": 32}
_NB_SMALL = {"epochs": 5, "hidden_size": 16, "n_blocks": 2, "n_lags": 8}
_TCN_SMALL = {"epochs": 5, "n_lags": 8, "kernel_size": 3}


# =====================================================
# Sweep 0
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("=" * 70)

    y = _ar1(T=120)

    # ---- lstm_gru_forecast ----
    print("\n[lstm_gru_forecast]")
    res, dt, err = _safe_run(lg_mod, _ctx(y, technique_id="lstm_gru_forecast",
                                             params=_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid model types
    for m in ("lstm", "gru"):
        res, _, _ = _safe_run(lg_mod, _ctx(y, technique_id="lstm_gru_forecast",
                                              params={**_SMALL, "model_type": m}))
        print(f"  model_type={m!r}: {res.get('status') if res else 'RAISED'}")
    # Invalid model_type — silent fall-through to LSTM
    res, _, _ = _safe_run(lg_mod, _ctx(y, technique_id="lstm_gru_forecast",
                                          params={**_SMALL, "model_type": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("model_type") or af.get("model")
        print(f"  model_type='zzz_invalid': SUCCESS (silent fall-through)")
        print(f"    audit_fields.model_type = {recorded!r}")
        findings.append({
            "id": "F-NN-LG-MODELTYPE",
            "wrapper": "lstm_gru_forecast",
            "severity": "severe",
            "description": (
                f"lstm_gru_forecast silently falls through invalid "
                f"`model_type` to LSTM via if/else at line 117-120. "
                f"audit_fields.model_type = {recorded!r}. Session 18 "
                f"silent-fall-through pattern."
            ),
        })
    # Numeric range tests
    res, _, err = _safe_run(lg_mod, _ctx(y, technique_id="lstm_gru_forecast",
                                            params={**_SMALL, "horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-NN-LG-HORIZON",
            "wrapper": "lstm_gru_forecast",
            "severity": "operational",
            "description": "lstm_gru_forecast silently accepts horizon=-1.",
        })

    # ---- tcn_forecast ----
    print("\n[tcn_forecast]")
    res, dt, err = _safe_run(tcn_mod, _ctx(y, technique_id="tcn_forecast",
                                               params=_TCN_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    res, _, _ = _safe_run(tcn_mod, _ctx(y, technique_id="tcn_forecast",
                                            params={**_TCN_SMALL, "horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-NN-TCN-HORIZON",
            "wrapper": "tcn_forecast",
            "severity": "operational",
            "description": "tcn_forecast silently accepts horizon=-1.",
        })

    # ---- transformer_forecast ----
    print("\n[transformer_forecast]")
    res, dt, err = _safe_run(tf_mod, _ctx(y, technique_id="transformer_forecast",
                                              params=_TF_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Multi-parameter consistency: d_model not divisible by n_heads
    res, _, _ = _safe_run(tf_mod, _ctx(y, technique_id="transformer_forecast",
                                           params={**_TF_SMALL, "d_model": 17, "n_heads": 4}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        warns = res.get("warnings") or []
        print(f"  d_model=17, n_heads=4 (incompat): SUCCESS (silent adjustment)")
        print(f"    warning: {' | '.join(str(w) for w in warns)[:100]}")
        findings.append({
            "id": "F-NN-TF-DMODEL",
            "wrapper": "transformer_forecast",
            "severity": "operational",
            "description": (
                "transformer_forecast silently adjusts d_model when not "
                "divisible by n_heads (loud-and-coerced with warning "
                "but user's d_model spec is changed). Should reject "
                "and ask user to fix the inconsistency."
            ),
        })
    res, _, _ = _safe_run(tf_mod, _ctx(y, technique_id="transformer_forecast",
                                           params={**_TF_SMALL, "horizon": -1}))
    if res and res.get("status") == "success":
        print(f"  horizon=-1: SUCCESS (silent)")
        findings.append({
            "id": "F-NN-TF-HORIZON",
            "wrapper": "transformer_forecast",
            "severity": "operational",
            "description": "transformer_forecast silently accepts horizon=-1.",
        })

    # ---- nbeats_forecast ----
    print("\n[nbeats_forecast]")
    res, dt, err = _safe_run(nb_mod, _ctx(y, technique_id="nbeats_forecast",
                                              params=_NB_SMALL))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid stack_types
    for st in (["generic"], ["trend", "seasonality"]):
        res, _, _ = _safe_run(nb_mod, _ctx(y, technique_id="nbeats_forecast",
                                              params={**_NB_SMALL, "stack_types": st}))
        print(f"  stack_types={st}: {res.get('status') if res else 'RAISED'}")
    # Invalid stack_types — silent fall-through
    res, _, _ = _safe_run(nb_mod, _ctx(y, technique_id="nbeats_forecast",
                                          params={**_NB_SMALL, "stack_types": ["zzz_invalid"]}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("stack_types")
        print(f"  stack_types=['zzz_invalid']: SUCCESS (silent fall-through to preset)")
        print(f"    audit_fields.stack_types = {recorded}")
        findings.append({
            "id": "F-NN-NB-STACKTYPES",
            "wrapper": "nbeats_forecast",
            "severity": "severe",
            "description": (
                f"nbeats_forecast silently falls through invalid "
                f"`stack_types` to preset default (line 297-305 has "
                f"an `if all(s in _valid for s in candidate)` check "
                f"that silently reverts to preset on any failure). "
                f"audit_fields.stack_types = {recorded} (the coerced "
                f"value). Session 18 silent-fall-through pattern."
            ),
        })

    return findings


# =====================================================
# Technique 1
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []
    y = _ar1(T=120, seed=43)

    print("\n[lstm_gru] cell type comparison (LSTM vs GRU)")
    for m in ("lstm", "gru"):
        res, dt, err = _safe_run(lg_mod, _ctx(y, technique_id="lstm_gru_forecast",
                                                  params={**_SMALL, "model_type": m}))
        if res and res.get("status") == "success":
            print(f"  model_type={m}: dt={dt:.2f}s")

    print("\n[tcn] kernel_size sweep")
    for k in (3, 5):
        res, dt, err = _safe_run(tcn_mod, _ctx(y, technique_id="tcn_forecast",
                                                   params={**_TCN_SMALL, "kernel_size": k}))
        if res and res.get("status") == "success":
            print(f"  kernel_size={k}: dt={dt:.2f}s")

    print("\n[transformer] n_heads sweep (d_model=16)")
    for h in (2, 4):
        res, dt, err = _safe_run(tf_mod, _ctx(y, technique_id="transformer_forecast",
                                                  params={**_TF_SMALL, "n_heads": h}))
        if res and res.get("status") == "success":
            print(f"  n_heads={h}: dt={dt:.2f}s")

    print("\n[nbeats] stack_types comparison")
    for st in (["generic"], ["trend", "seasonality"]):
        res, dt, err = _safe_run(nb_mod, _ctx(y, technique_id="nbeats_forecast",
                                                  params={**_NB_SMALL, "stack_types": st}))
        if res and res.get("status") == "success":
            print(f"  stack_types={st}: dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data (single 200-obs subsample)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    y = data["DGS10"][~np.isnan(data["DGS10"])][-200:].tolist()
    print(f"\n--- DGS10 (T=200) ---")
    for tid, mod, params, label in [
        ("lstm_gru_forecast", lg_mod, _SMALL, "lg"),
        ("tcn_forecast", tcn_mod, _TCN_SMALL, "tcn"),
        ("transformer_forecast", tf_mod, _TF_SMALL, "tf"),
        ("nbeats_forecast", nb_mod, _NB_SMALL, "nb"),
    ]:
        res, dt, err = _safe_run(mod, _ctx(y, technique_id=tid, params=params,
                                              name="DGS10"))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: status={s}, dt={dt:.2f}s")
        rows.append({"wrapper": label, "status": s, "runtime": dt})
    return rows


# =====================================================
# Technique 3 — Adversarial
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: white noise
    print("\n[C-AD-1] white noise T=80")
    rng = np.random.default_rng(42)
    y = rng.standard_normal(80).tolist()
    for tid, mod, params, label in [
        ("lstm_gru_forecast", lg_mod, _SMALL, "lg"),
        ("nbeats_forecast", nb_mod, _NB_SMALL, "nb"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    # C-AD-2: pure trend
    print("\n[C-AD-2] pure linear trend")
    y = (np.arange(100) * 0.1 + 0.05 * rng.standard_normal(100)).tolist()
    for tid, mod, params, label in [
        ("tcn_forecast", tcn_mod, _TCN_SMALL, "tcn"),
        ("transformer_forecast", tf_mod, _TF_SMALL, "tf"),
    ]:
        res, _, _ = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        print(f"  {label}: {res.get('status') if res else 'RAISED'}")

    # C-AD-3: short series T=30
    print("\n[C-AD-3] short series T=30")
    y = _ar1(T=30, seed=44)
    for tid, mod, params, label in [
        ("lstm_gru_forecast", lg_mod, {**_SMALL, "n_lags": 4}, "lg"),
        ("tcn_forecast", tcn_mod, {**_TCN_SMALL, "n_lags": 4}, "tcn"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    # C-AD-4: constant series
    print("\n[C-AD-4] constant series")
    y = [1.0] * 100
    for tid, mod, params, label in [
        ("lstm_gru_forecast", lg_mod, _SMALL, "lg"),
        ("nbeats_forecast", nb_mod, _NB_SMALL, "nb"),
    ]:
        res, _, err = _safe_run(mod, _ctx(y, technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED:{err[:30]}"
        print(f"  {label}: {s}")

    return []


def main():
    out = {"session": 24, "started": time.time()}
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
    out_path = _ROOT / "tools" / "calibration_audit" / "neural_sequence_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(sev) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
