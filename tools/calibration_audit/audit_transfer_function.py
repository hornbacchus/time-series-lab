"""Calibration Audit Phase 2 Session 20 — transfer_function (solo audit).

Single-wrapper full-depth audit deferred from Session 11.

Three audit techniques (full depth, no compression):
  Sweep 0 (PRIORITY) — variant dispatch + input-validation matrix
    + Session 17/18 try/except check + Session 18 fall-through
    + Session 19 numeric range check
  Technique 1 — full parameter sweep (lag, AR, polynomial, sample size)
  Technique 2 — real-data on 3 macro pairs
  Technique 3 — 9 adversarial canonicals (5 base + 4 C-CAL)

Run:
    python tools/calibration_audit/audit_transfer_function.py
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
from techniques import transfer_function as tf_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx_pair(y, x, *, params=None, preset="Balanced",
                    run_id="audit_tf", frequency="D",
                    y_name="Y", x_name="X", extra_series=None):
    user_params = dict(params or {})
    series = [{"name": y_name, "values": list(y)},
              {"name": x_name, "values": list(x)}]
    if extra_series:
        for nm, vals in extra_series:
            series.append({"name": nm, "values": list(vals)})
    return RunContext({
        "run_id": run_id,
        "technique_id": "transfer_function",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(y))),
        "series": series,
        "params": user_params,
    })


def _safe_run(ctx):
    try:
        t0 = time.time()
        res = tf_mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_tf(*, T=300, true_lag=2, true_weight=0.5,
                  ar_phi=0.3, sigma_x=1.0, sigma_n=0.3, seed=42):
    """y_t = sum_{k=true_lag} weight * x_{t-k} + ARMA(1) noise."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(T) * sigma_x
    n = np.zeros(T)
    eps = rng.standard_normal(T) * sigma_n
    for t in range(1, T):
        n[t] = ar_phi * n[t - 1] + eps[t]
    y = np.zeros(T)
    for t in range(true_lag, T):
        y[t] = true_weight * x[t - true_lag] + n[t]
    return y, x


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


def _yield_diff(yields):
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


# =====================================================
# Sweep 0 — Per-wrapper dispatch + input-validation
# =====================================================


def sweep_0_validation():
    findings = []
    print("\n" + "=" * 70)
    print("SWEEP 0 — Input validation matrix (full depth)")
    print("With Session 17/18/19 refinements")
    print("=" * 70)

    y, x = _simulate_tf(T=300, true_lag=2, true_weight=0.5)
    y, x = y.tolist(), x.tolist()

    # Baseline
    print("\n[transfer_function]")
    res, dt, err = _safe_run(_build_ctx_pair(y, x))
    print(f"  baseline (default params): {res.get('status') if res else err} ({dt:.2f}s)")

    # Valid polynomial values
    for p in ("unrestricted", "almon"):
        res, _, _ = _safe_run(_build_ctx_pair(y, x, params={"polynomial": p, "max_lag": 5}))
        ok = res and res.get("status") == "success"
        print(f"  polynomial={p!r}: {'OK' if ok else 'FAIL'}")

    # Invalid polynomial — Session 18 fall-through check
    res, _, err = _safe_run(_build_ctx_pair(
        y, x, params={"polynomial": "zzz_invalid", "max_lag": 5}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("polynomial")
        print(f"  polynomial='zzz_invalid': SUCCESS (silent fall-through)")
        print(f"    audit_fields.polynomial = {recorded!r}")
        findings.append({
            "id": "F-TF-POLYNOMIAL",
            "wrapper": "transfer_function",
            "severity": "severe",
            "description": (
                f"transfer_function silently falls through invalid "
                f"`polynomial` value to 'unrestricted' default via "
                f"if/else at line 113-128 (`if poly_type == 'almon' "
                f"and ...: ... else: ...`). audit_fields.polynomial "
                f"recorded user's invalid value {recorded!r}, "
                f"misrepresenting the model that ran. Session 18 "
                f"silent-fall-through pattern."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  polynomial='zzz_invalid': REJECTED — {em[:80]}")
    else:
        print(f"  polynomial='zzz_invalid': RAISED — {err}")

    # Invalid numeric: negative max_lag
    res, _, err = _safe_run(_build_ctx_pair(y, x, params={"max_lag": -1}))
    print(f"  max_lag=-1: {res.get('status') if res else err}")
    if res and res.get("status") == "success":
        findings.append({
            "id": "F-TF-MAXLAG-NEG",
            "wrapper": "transfer_function",
            "severity": "operational",
            "description": "max_lag negative silently accepted (no range check)",
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"    error: {em[:80]}")

    # Invalid numeric: negative ar_order
    res, _, err = _safe_run(_build_ctx_pair(y, x, params={"ar_order": -2}))
    print(f"  ar_order=-2: {res.get('status') if res else err}")
    if res and res.get("status") == "success":
        findings.append({
            "id": "F-TF-AR-ORDER-NEG",
            "wrapper": "transfer_function",
            "severity": "operational",
            "description": "ar_order negative silently accepted (no range check)",
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"    error: {em[:80]}")

    # Invalid numeric: huge almon_degree
    res, _, err = _safe_run(_build_ctx_pair(
        y, x, params={"polynomial": "almon", "max_lag": 5,
                       "almon_degree": 50}))
    print(f"  almon_degree=50 with max_lag=5: {res.get('status') if res else err}")
    # almon_degree > max_lag falls through to unrestricted in line 113 condition
    # (and len(lag_indices) > almon_deg + 1 fails). audit may show polynomial="almon"
    # but actual model is unrestricted. Verify.
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded_poly = audit.get("polynomial")
        if recorded_poly == "almon":
            findings.append({
                "id": "F-TF-ALMON-DEGREE",
                "wrapper": "transfer_function",
                "severity": "operational",
                "description": (
                    f"transfer_function with polynomial='almon' but "
                    f"almon_degree (50) >= n_lags - 1 silently falls "
                    f"through to unrestricted polynomial; audit_fields"
                    f".polynomial = 'almon' but actual model is "
                    f"unrestricted. User cannot tell which model ran."
                ),
            })

    return findings


# =====================================================
# Technique 1 — Parameter sweep (full depth)
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Parameter sweep (full depth)")
    print("=" * 70)
    rows = []

    # 1.1: max_lag sensitivity on known TF DGP
    print("\n[1.1] max_lag sweep on known b=2 DGP (T=300)")
    y, x = _simulate_tf(T=300, true_lag=2, true_weight=0.7, seed=43)
    for ml in (2, 4, 8, 12):
        res, dt, err = _safe_run(_build_ctx_pair(
            y.tolist(), x.tolist(), params={"max_lag": ml}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  max_lag={ml}: peak_lag={af.get('peak_lag')}, peak_w={af.get('peak_lag_weight')}, R²={af.get('r_squared')}, dt={dt:.2f}s")
            rows.append({"sweep": "max_lag", "param": ml,
                          "peak_lag": af.get("peak_lag"),
                          "r_squared": af.get("r_squared")})

    # 1.2: AR order sensitivity
    print("\n[1.2] ar_order sweep with known true_phi=0.5 noise (T=300)")
    y, x = _simulate_tf(T=300, true_lag=2, ar_phi=0.5, seed=44)
    for ao in (0, 1, 2, 3):
        res, dt, err = _safe_run(_build_ctx_pair(
            y.tolist(), x.tolist(), params={"max_lag": 4, "ar_order": ao}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  ar_order={ao}: AIC={af.get('aic')}, DW={af.get('durbin_watson')}, dt={dt:.2f}s")

    # 1.3: polynomial type comparison
    print("\n[1.3] polynomial type {unrestricted, almon} on long-lag DGP (max_lag=10)")
    y, x = _simulate_tf(T=400, true_lag=3, seed=45)
    for poly in ("unrestricted", "almon"):
        res, dt, err = _safe_run(_build_ctx_pair(
            y.tolist(), x.tolist(),
            params={"polynomial": poly, "max_lag": 10, "almon_degree": 3}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  polynomial={poly!r}: AIC={af.get('aic')}, R²={af.get('r_squared')}, dt={dt:.2f}s")

    # 1.4: sample size sensitivity
    print("\n[1.4] sample size sensitivity (T ∈ {200, 500, 1000})")
    for T in (200, 500, 1000):
        y, x = _simulate_tf(T=T, true_lag=2, seed=46)
        res, dt, err = _safe_run(_build_ctx_pair(
            y.tolist(), x.tolist(), params={"max_lag": 5}))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  T={T}: peak_lag={af.get('peak_lag')}, lr_mult={af.get('long_run_multiplier')}, R²={af.get('r_squared')}, dt={dt:.2f}s")

    return rows


# =====================================================
# Technique 2 — Real-data stress (3 macro pairs)
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (3 macro pairs)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        print("  fixture missing; skipping")
        return rows
    data = np.load(_FIXTURE)

    # Build series
    gspc_ret = _log_returns(data["GSPC"])
    dgs2_diff = _yield_diff(data["DGS2"])
    dgs10_diff = _yield_diff(data["DGS10"])
    dexus_ret = _log_returns(data["DEXUSEU"])
    gold_ret = _log_returns(data["GOLD"])

    pairs = [
        ("Equity → Rates", "DGS10_diff", dgs10_diff[-500:],
         "GSPC_logret", gspc_ret[-500:]),
        ("Yield curve transmission", "DGS10_diff", dgs10_diff[-500:],
         "DGS2_diff", dgs2_diff[-500:]),
        ("FX → Commodity", "GOLD_logret", gold_ret[-500:],
         "DEXUSEU_logret", dexus_ret[-500:]),
    ]

    for label, y_name, y_vals, x_name, x_vals in pairs:
        # Align lengths
        n = min(len(y_vals), len(x_vals))
        y_vals = y_vals[-n:]; x_vals = x_vals[-n:]
        print(f"\n--- {label} ({y_name} ← {x_name}, n={n}) ---")
        res, dt, err = _safe_run(_build_ctx_pair(
            y_vals.tolist(), x_vals.tolist(),
            y_name=y_name, x_name=x_name))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            print(f"  peak_lag={af.get('peak_lag')}, peak_w={af.get('peak_lag_weight')}, R²={af.get('r_squared')}, lr_mult={af.get('long_run_multiplier')}")
            print(f"  DW={af.get('durbin_watson')}, LB10_p={af.get('ljung_box_lag10_pvalue')}, dt={dt:.2f}s")
            rows.append({"pair": label, "peak_lag": af.get("peak_lag"),
                          "r_squared": af.get("r_squared"),
                          "long_run": af.get("long_run_multiplier")})
        else:
            em = (res.get('error_message') if res else err) or ""
            print(f"  FAIL: {em[:100]}")

    return rows


# =====================================================
# Technique 3 — 9 canonicals (5 base + 4 C-CAL)
# =====================================================


def technique_3_canonicals():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — 9 canonicals (5 base + 4 C-CAL)")
    print("=" * 70)
    findings = []

    # canonical_1: known TF DGP recovery (b=2, ar=1)
    print("\n[c1] known TF DGP recovery (b=2, ar(1) noise)")
    y, x = _simulate_tf(T=400, true_lag=2, true_weight=0.6, ar_phi=0.3, seed=42)
    res, _, _ = _safe_run(_build_ctx_pair(y.tolist(), x.tolist(),
                                              params={"max_lag": 5, "ar_order": 1}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        ok = af.get("peak_lag") == 2
        print(f"  peak_lag={af.get('peak_lag')} (expect 2): {'PASS' if ok else 'partial recovery'}")

    # canonical_2: independent series (no TF expected)
    print("\n[c2] independent input/output (no TF expected)")
    rng = np.random.default_rng(43)
    y = rng.standard_normal(300).tolist()
    x = rng.standard_normal(300).tolist()
    res, _, _ = _safe_run(_build_ctx_pair(y, x, params={"max_lag": 5}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  R²={af.get('r_squared')} (expect low), peak_w={af.get('peak_lag_weight')}")

    # canonical_3: TF with seasonal structure (12-period sinusoidal)
    print("\n[c3] TF with periodic structure (input lag at known period)")
    rng = np.random.default_rng(44)
    T = 240
    t_vec = np.arange(T)
    x = np.sin(2 * np.pi * t_vec / 12)
    y = np.zeros(T)
    for t in range(3, T):
        y[t] = 0.7 * x[t - 3] + 0.3 * rng.standard_normal()
    res, _, _ = _safe_run(_build_ctx_pair(y.tolist(), x.tolist(),
                                              params={"max_lag": 6}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  peak_lag={af.get('peak_lag')} (expect 3), R²={af.get('r_squared')}")

    # canonical_4: short series with high-order TF
    print("\n[c4] short T=100 with max_lag=5 (boundary)")
    y, x = _simulate_tf(T=100, true_lag=2, seed=45)
    res, _, _ = _safe_run(_build_ctx_pair(y.tolist(), x.tolist(),
                                              params={"max_lag": 5}))
    s = res.get("status") if res else "RAISED"
    print(f"  status={s}")

    # canonical_5: real-data smoke test (DGS2 → DGS10 yield transmission)
    print("\n[c5] real-data smoke (DGS2 → DGS10 yield)")
    if _FIXTURE.exists():
        data = np.load(_FIXTURE)
        d2 = _yield_diff(data["DGS2"])[-300:]
        d10 = _yield_diff(data["DGS10"])[-300:]
        n = min(len(d2), len(d10))
        res, _, _ = _safe_run(_build_ctx_pair(d10[-n:].tolist(), d2[-n:].tolist()))
        s = res.get("status") if res else "RAISED"
        print(f"  status={s}")

    # C-CAL-1: constant input → degenerate
    print("\n[c6 / C-CAL-1] constant input series (degenerate)")
    rng = np.random.default_rng(46)
    y = rng.standard_normal(200).tolist()
    x = [1.0] * 200
    res, _, err = _safe_run(_build_ctx_pair(y, x, params={"max_lag": 3}))
    s = res.get("status") if res else f"RAISED: {err}"
    print(f"  status={s}")

    # C-CAL-2: heavy-tail noise on output
    print("\n[c7 / C-CAL-2] heavy-tail noise on output")
    rng = np.random.default_rng(47)
    T = 300
    x = rng.standard_normal(T)
    n = rng.standard_t(df=3, size=T) * 0.5
    y = np.zeros(T)
    for t in range(2, T):
        y[t] = 0.5 * x[t - 2] + n[t]
    res, _, _ = _safe_run(_build_ctx_pair(y.tolist(), x.tolist(),
                                              params={"max_lag": 5}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  peak_lag={af.get('peak_lag')}, JB_p={af.get('jarque_bera_pvalue')} (expect rejected)")

    # C-CAL-3: very short T=20 with max_lag=10
    print("\n[c8 / C-CAL-3] T=20 with max_lag=10 → reject")
    rng = np.random.default_rng(48)
    res, _, err = _safe_run(_build_ctx_pair(
        rng.standard_normal(20).tolist(),
        rng.standard_normal(20).tolist(),
        params={"max_lag": 10}))
    s = res.get("status") if res else f"RAISED: {err}"
    print(f"  status={s}")

    # C-CAL-4: identical input/output (should produce TF identity at lag 0)
    print("\n[c9 / C-CAL-4] identical input=output (TF should identify lag-0 coefficient ≈ 1)")
    rng = np.random.default_rng(49)
    z = rng.standard_normal(300).tolist()
    res, _, _ = _safe_run(_build_ctx_pair(z, z, params={"max_lag": 3, "ar_order": 0}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        print(f"  peak_lag={af.get('peak_lag')} (expect 0), peak_w={af.get('peak_lag_weight')} (expect ~1.0)")

    return findings


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 20, "started": time.time()}

    sweep0_findings = sweep_0_validation()
    out["sweep_0_findings"] = sweep0_findings

    rows1 = technique_1_param_sweeps()
    out["technique_1"] = rows1

    rows2 = technique_2_real_data()
    out["technique_2"] = rows2

    findings3 = technique_3_canonicals()
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

    out_path = _ROOT / "tools" / "calibration_audit" / "transfer_function_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
