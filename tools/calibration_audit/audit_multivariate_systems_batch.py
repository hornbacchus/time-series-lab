"""Calibration Audit Phase 2 Session 22 — Multivariate Systems batch.

Four wrappers:
  - bvar
  - dynamic_factor_model
  - forecast_reconciliation
  - pca_analysis

Sweep 0 + Technique 1 + 2 + 3 per established protocol with full
S17/18/19/20 methodology refinements (5 failure modes).
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
from techniques import bvar as bvar_mod
from techniques import dynamic_factor_model as dfm_mod
from techniques import forecast_reconciliation as fr_mod
from techniques import pca_analysis as pca_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


def _build_ctx(values_list, names, *, technique_id, params=None,
                preset="Fast", frequency="M", time_col=None):
    series = []
    n = len(values_list[0])
    for nm, vals in zip(names, values_list):
        series.append({"name": nm, "values": list(vals)})
    return RunContext({
        "run_id": "audit_mv",
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_col if time_col is not None else list(range(n)),
        "series": series,
        "params": dict(params or {}),
    })


def _safe_run(mod, ctx):
    try:
        t0 = time.time()
        res = mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _multi_var_data(T=200, n_vars=3, seed=42):
    rng = np.random.default_rng(seed)
    # Multivariate VAR(1) with mild contemporaneous correlation
    A = np.array([[0.5, 0.1, 0.05],
                   [0.05, 0.6, 0.1],
                   [0.1, 0.05, 0.4]])[:n_vars, :n_vars]
    Y = np.zeros((T, n_vars))
    for t in range(1, T):
        Y[t] = A @ Y[t-1] + rng.standard_normal(n_vars) * 0.5
    return [Y[:, i].tolist() for i in range(n_vars)]


def _hierarchy_data(T=120, seed=42):
    """Top + 4 bottom series; bottom sums to top by construction."""
    rng = np.random.default_rng(seed)
    bottoms = []
    for _ in range(4):
        b = np.cumsum(rng.standard_normal(T)) + 100.0
        bottoms.append(b.tolist())
    top = np.sum(bottoms, axis=0).tolist()
    return [top] + bottoms


def _factor_data(T=200, n_vars=5, n_factors=2, seed=42):
    """Y = L @ F + noise; common factors visible."""
    rng = np.random.default_rng(seed)
    F = np.zeros((T, n_factors))
    for t in range(1, T):
        F[t] = 0.7 * F[t-1] + rng.standard_normal(n_factors)
    L = rng.standard_normal((n_vars, n_factors)) * 0.5
    Y = F @ L.T + rng.standard_normal((T, n_vars)) * 0.3
    return [Y[:, i].tolist() for i in range(n_vars)]


# =====================================================
# Sweep 0
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (4 wrappers)")
    print("=" * 70)

    # Multivariate fixture
    Y3 = _multi_var_data(T=150, n_vars=3, seed=42)
    Y5 = _factor_data(T=200, n_vars=5, n_factors=2, seed=42)
    H = _hierarchy_data(T=120, seed=42)

    # ---- bvar ----
    print("\n[bvar]")
    res, dt, err = _safe_run(bvar_mod, _build_ctx(
        Y3, ["y1", "y2", "y3"], technique_id="bvar"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Numeric ranges
    res, _, _ = _safe_run(bvar_mod, _build_ctx(
        Y3, ["y1", "y2", "y3"], technique_id="bvar",
        params={"lags": -1}))
    print(f"  lags=-1: {res.get('status') if res else 'RAISED'}")
    res, _, _ = _safe_run(bvar_mod, _build_ctx(
        Y3, ["y1", "y2", "y3"], technique_id="bvar",
        params={"lambda1": -0.5}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  lambda1=-0.5: SUCCESS audit.lambda1={af.get('lambda1')}")
        findings.append({
            "id": "F-MV-BVAR-LAMBDA",
            "wrapper": "bvar",
            "severity": "operational",
            "description": (
                "bvar silently accepts negative lambda1 prior shrinkage "
                "parameter (must be > 0 for valid Minnesota prior)."
            ),
        })

    # ---- dynamic_factor_model ----
    print("\n[dynamic_factor_model]")
    res, dt, err = _safe_run(dfm_mod, _build_ctx(
        Y5, [f"y{i}" for i in range(5)], technique_id="dynamic_factor_model"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid transforms
    for t in ("auto", "log_diff", "diff", "none"):
        # log_diff requires positive; use exponentiated
        Y_pos = [list(np.exp(np.array(s) * 0.1)) for s in Y5] if t == "log_diff" else Y5
        res, _, _ = _safe_run(dfm_mod, _build_ctx(
            Y_pos, [f"y{i}" for i in range(5)],
            technique_id="dynamic_factor_model",
            params={"transform": t, "k_factors": 2}))
        ok = res and res.get("status") == "success"
        print(f"  transform={t!r}: {'OK' if ok else 'FAIL'}")
    # Invalid transform (silent fall-through to "none")
    res, _, _ = _safe_run(dfm_mod, _build_ctx(
        Y5, [f"y{i}" for i in range(5)],
        technique_id="dynamic_factor_model",
        params={"transform": "zzz_invalid", "k_factors": 2}))
    if res and res.get("status") == "success":
        warns = res.get("warnings") or []
        # Check if there's a warning mentioning the invalid value
        has_warn = any("zzz_invalid" in str(w) for w in warns)
        print(f"  transform='zzz_invalid': SUCCESS (silent fall-through)")
        print(f"    has_warn_mentioning_invalid={has_warn}")
        findings.append({
            "id": "F-MV-DFM-TRANSFORM",
            "wrapper": "dynamic_factor_model",
            "severity": "severe",
            "description": (
                "dynamic_factor_model silently falls through invalid "
                "`transform` value via if/elif/else chain at line 141-167; "
                "applied_transform stays 'none', no warning emitted, "
                "audit_fields doesn't even include 'transform'. User "
                "cannot tell which transform actually ran. Session 18 "
                "silent-fall-through pattern."
            ),
        })

    # ---- forecast_reconciliation ----
    print("\n[forecast_reconciliation]")
    res, dt, err = _safe_run(fr_mod, _build_ctx(
        H, ["top", "b1", "b2", "b3", "b4"],
        technique_id="forecast_reconciliation"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid base_forecasters
    for bf in ("naive", "drift", "ets"):
        res, _, _ = _safe_run(fr_mod, _build_ctx(
            H, ["top", "b1", "b2", "b3", "b4"],
            technique_id="forecast_reconciliation",
            params={"base_forecaster": bf}))
        ok = res and res.get("status") == "success"
        print(f"  base_forecaster={bf!r}: {'OK' if ok else 'FAIL'}")
    # Invalid base_forecaster — silent fall-through
    res, _, _ = _safe_run(fr_mod, _build_ctx(
        H, ["top", "b1", "b2", "b3", "b4"],
        technique_id="forecast_reconciliation",
        params={"base_forecaster": "zzz_invalid"}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        print(f"  base_forecaster='zzz_invalid': SUCCESS (silent fall-through to naive)")
        findings.append({
            "id": "F-MV-FR-BASEFC",
            "wrapper": "forecast_reconciliation",
            "severity": "severe",
            "description": (
                "forecast_reconciliation _base_forecast helper "
                "silently falls through invalid `base_forecaster` to "
                "'naive' via if/elif/else chain at line 842-867. "
                "Session 18 silent-fall-through pattern."
            ),
        })
    # Valid top_down_weights
    for tdw in ("proportions_avg", "proportions_last"):
        res, _, _ = _safe_run(fr_mod, _build_ctx(
            H, ["top", "b1", "b2", "b3", "b4"],
            technique_id="forecast_reconciliation",
            params={"method": "top_down", "top_down_weights": tdw}))
        ok = res and res.get("status") == "success"
        print(f"  top_down_weights={tdw!r}: {'OK' if ok else 'FAIL'}")
    # Invalid top_down_weights — silent fall-through to proportions_avg
    res, _, _ = _safe_run(fr_mod, _build_ctx(
        H, ["top", "b1", "b2", "b3", "b4"],
        technique_id="forecast_reconciliation",
        params={"method": "top_down", "top_down_weights": "zzz_invalid"}))
    if res and res.get("status") == "success":
        print(f"  top_down_weights='zzz_invalid': SUCCESS (silent fall-through to proportions_avg)")
        findings.append({
            "id": "F-MV-FR-TDWEIGHTS",
            "wrapper": "forecast_reconciliation",
            "severity": "severe",
            "description": (
                "forecast_reconciliation silently falls through invalid "
                "`top_down_weights` to 'proportions_avg' via if/else at "
                "line 344. audit_fields doesn't track which td_weights "
                "actually applied. Session 18 silent-fall-through pattern."
            ),
        })

    # ---- pca_analysis ----
    print("\n[pca_analysis]")
    res, dt, err = _safe_run(pca_mod, _build_ctx(
        Y5, [f"y{i}" for i in range(5)], technique_id="pca_analysis"))
    print(f"  baseline: {res.get('status') if res else err} ({dt:.2f}s)")
    # Valid rotations
    for r in (None, "varimax"):
        res, _, _ = _safe_run(pca_mod, _build_ctx(
            Y5, [f"y{i}" for i in range(5)],
            technique_id="pca_analysis",
            params={"rotation": r, "n_components": 2}))
        ok = res and res.get("status") == "success"
        print(f"  rotation={r!r}: {'OK' if ok else 'FAIL'}")
    # Invalid rotation — silent skip
    res, _, _ = _safe_run(pca_mod, _build_ctx(
        Y5, [f"y{i}" for i in range(5)],
        technique_id="pca_analysis",
        params={"rotation": "zzz_invalid", "n_components": 2}))
    if res and res.get("status") == "success":
        af = res.get("audit_fields") or {}
        recorded = af.get("rotation")
        print(f"  rotation='zzz_invalid': SUCCESS (silent skip)")
        print(f"    audit_fields.rotation = {recorded!r}")
        findings.append({
            "id": "F-MV-PCA-ROTATION",
            "wrapper": "pca_analysis",
            "severity": "severe",
            "description": (
                f"pca_analysis silently skips invalid `rotation` value "
                f"(only applies if rotation == 'varimax'); audit_fields."
                f"rotation = {recorded!r}, recording user's invalid input "
                f"verbatim — but no rotation was actually applied. "
                f"Session 18 silent-skip pattern."
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

    # bvar lag sweep
    print("\n[bvar] lag sweep")
    Y3 = _multi_var_data(T=200, n_vars=3, seed=43)
    for p in (1, 2, 4):
        res, dt, err = _safe_run(bvar_mod, _build_ctx(
            Y3, ["y1", "y2", "y3"], technique_id="bvar",
            params={"lags": p, "n_draws": 50}))
        if res and res.get("status") == "success":
            print(f"  lags={p}: dt={dt:.2f}s")

    # dfm k_factors sweep
    print("\n[dynamic_factor_model] k_factors sweep")
    Y5 = _factor_data(T=200, n_vars=5, n_factors=2, seed=44)
    for k in (1, 2, 3):
        res, dt, err = _safe_run(dfm_mod, _build_ctx(
            Y5, [f"y{i}" for i in range(5)],
            technique_id="dynamic_factor_model",
            params={"k_factors": k}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  k_factors={k}: var_explained={af.get('variance_explained_pct')}%, dt={dt:.2f}s")

    # forecast_reconciliation method comparison
    print("\n[forecast_reconciliation] method comparison")
    H = _hierarchy_data(T=120, seed=45)
    for m in ("bottom_up", "top_down", "ols", "wls_variance", "mint_shrinkage"):
        res, dt, err = _safe_run(fr_mod, _build_ctx(
            H, ["top", "b1", "b2", "b3", "b4"],
            technique_id="forecast_reconciliation",
            params={"method": m}))
        if res and res.get("status") == "success":
            print(f"  method={m!r}: dt={dt:.2f}s")

    # pca n_components sweep
    print("\n[pca_analysis] n_components sweep")
    Y5 = _factor_data(T=200, n_vars=5, n_factors=2, seed=46)
    for nc in (1, 2, 3):
        res, dt, err = _safe_run(pca_mod, _build_ctx(
            Y5, [f"y{i}" for i in range(5)],
            technique_id="pca_analysis",
            params={"n_components": nc}))
        if res and res.get("status") == "success":
            print(f"  n_components={nc}: dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        return rows
    data = np.load(_FIXTURE)
    # Build the 5-series macro panel: GSPC, DGS10, DGS2, DEXUSEU, GOLD
    series_data = {}
    for nm in ("GSPC", "DGS10", "DGS2", "DEXUSEU", "GOLD"):
        v = data[nm]
        series_data[nm] = v[~np.isnan(v)][-300:].tolist()
    n = min(len(v) for v in series_data.values())
    for k in series_data:
        series_data[k] = series_data[k][-n:]

    # bvar on (DGS2, DGS10, GSPC) — natural macro VAR
    print("\n--- bvar on (DGS2, DGS10, GSPC) ---")
    res, dt, err = _safe_run(bvar_mod, _build_ctx(
        [series_data["DGS2"], series_data["DGS10"], series_data["GSPC"]],
        ["DGS2", "DGS10", "GSPC"], technique_id="bvar",
        frequency="D", params={"n_draws": 100}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  status=success, dt={dt:.2f}s")
        rows.append({"wrapper": "bvar", "runtime": dt})

    # dynamic_factor_model on 5 series
    print("\n--- dynamic_factor_model on 5-series macro ---")
    res, dt, err = _safe_run(dfm_mod, _build_ctx(
        list(series_data.values()), list(series_data.keys()),
        technique_id="dynamic_factor_model", frequency="D"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  k_factors={af.get('k_factors')}, var_explained={af.get('variance_explained_pct')}%, dt={dt:.2f}s")
        rows.append({"wrapper": "dfm", "runtime": dt})

    # forecast_reconciliation: synthetic hierarchy (real macro pairs don't have natural hierarchy)
    print("\n--- forecast_reconciliation on synthetic hierarchy (T=120) ---")
    H = _hierarchy_data(T=120, seed=42)
    res, dt, err = _safe_run(fr_mod, _build_ctx(
        H, ["top", "b1", "b2", "b3", "b4"],
        technique_id="forecast_reconciliation", frequency="M"))
    if res and res.get("status") == "success":
        print(f"  status=success, dt={dt:.2f}s")
        rows.append({"wrapper": "fr", "runtime": dt})

    # pca_analysis on 5 series
    print("\n--- pca_analysis on 5-series macro ---")
    res, dt, err = _safe_run(pca_mod, _build_ctx(
        list(series_data.values()), list(series_data.keys()),
        technique_id="pca_analysis", frequency="D"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        var_explained = af.get("variance_explained")
        print(f"  status=success, dt={dt:.2f}s")
        rows.append({"wrapper": "pca", "runtime": dt})

    return rows


# =====================================================
# Technique 3 — Adversarial
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: Independent series (bvar/dfm should detect minimal common structure)
    print("\n[C-AD-1] independent random walks")
    rng = np.random.default_rng(42)
    Y_ind = [np.cumsum(rng.standard_normal(150)).tolist() for _ in range(3)]
    res, _, _ = _safe_run(bvar_mod, _build_ctx(
        Y_ind, ["y1", "y2", "y3"], technique_id="bvar",
        params={"n_draws": 50}))
    print(f"  bvar: {res.get('status') if res else 'RAISED'}")

    # C-AD-2: Perfectly collinear series (PCA degenerate)
    print("\n[C-AD-2] perfectly collinear series")
    rng = np.random.default_rng(43)
    base = rng.standard_normal(100)
    Y_coll = [base.tolist(), (2*base).tolist(), (-base).tolist()]
    res, _, _ = _safe_run(pca_mod, _build_ctx(
        Y_coll, ["y1", "y2", "y3"], technique_id="pca_analysis",
        params={"n_components": 2}))
    if res:
        print(f"  pca: {res.get('status')}")

    # C-AD-3: Constant series (all zero variance)
    print("\n[C-AD-3] constant series")
    Y_const = [[1.0]*100, [2.0]*100, [3.0]*100]
    res, _, _ = _safe_run(pca_mod, _build_ctx(
        Y_const, ["y1", "y2", "y3"], technique_id="pca_analysis"))
    print(f"  pca: {res.get('status') if res else 'RAISED'}")

    # C-AD-4: Short series with high parameter count
    print("\n[C-AD-4] short series T=30 with multivariate models")
    Y_short = _multi_var_data(T=30, n_vars=3, seed=44)
    for label, mod, tid, params in [
        ("bvar", bvar_mod, "bvar", {"lags": 4, "n_draws": 50}),
        ("dfm", dfm_mod, "dynamic_factor_model", {"k_factors": 2}),
    ]:
        res, _, err = _safe_run(mod, _build_ctx(
            Y_short, ["y1", "y2", "y3"], technique_id=tid, params=params))
        s = res.get("status") if res else f"RAISED: {err[:30]}"
        print(f"  {label}: {s}")

    return []


def main():
    out = {"session": 22, "started": time.time()}
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
    out["summary"] = {"severe": len(severe), "operational": len(op), "cosmetic": len(cosm)}
    out_path = _ROOT / "tools" / "calibration_audit" / "multivariate_systems_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
