"""Path Q investigation: DEXUSEU EWS=6.57 signal cross-validation.

Standalone analytical use of TSL wrappers (no audit, no permanent
infrastructure). Investigates whether the Session 28 CSD finding
on DEXUSEU log returns is a genuine regime-change signal or an
artifact.

Run:
    python tools/investigations/dexuseu_ews_investigation_2026_04_28.py

Output:
    docs/investigations/dexuseu_ews_investigation_2026_04_28.md
    + JSON results: tools/investigations/dexuseu_results.json
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
from techniques import markov_switching as ms_mod
from techniques import bocpd as bocpd_mod
from techniques import pelt_change_points as pelt_mod
from techniques import stl_esd_anomaly as stl_mod
from techniques import garch_model as garch_mod
from techniques import caviar_quantile_dynamics as caviar_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL = lambda *a, **k: None


def _ctx(values, *, technique_id, params=None,
         preset="Fast", frequency="D", name="DEXUSEU_logret",
         time_axis=None):
    n = len(values)
    return RunContext({
        "run_id": "investigation",
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_axis if time_axis is not None else list(range(n)),
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


def _load_dexuseu():
    """Load DEXUSEU and convert to log returns."""
    data = np.load(_FIXTURE)
    raw = data["DEXUSEU"]
    valid = raw[~np.isnan(raw)] if np.issubdtype(raw.dtype, np.floating) else raw
    valid = valid.astype(np.float64)
    valid = valid[~np.isnan(valid)]
    log_ret = 100.0 * np.diff(np.log(np.maximum(valid, 1e-12)))
    return log_ret, valid


# =====================================================
# INV2 — Reproduce Session 28 finding
# =====================================================


def inv2_reproduce(log_ret):
    print("\n" + "=" * 70)
    print("INV2 — Reproduce Session 28 finding")
    print("=" * 70)

    # Session 28 audit used last 2000 obs with default Fast preset.
    y = log_ret[-2000:].tolist()
    res, dt, err = _safe_run(csd_mod, _ctx(y, technique_id="critical_slowing_down"))
    if not res or res.get("status") != "success":
        return {"error": f"reproduction failed: {err or res.get('error_message')}"}

    af = res["audit_fields"]
    out = {
        "T": len(y),
        "ews_composite_score": af.get("ews_composite_score"),
        "ews_state": af.get("ews_state"),
        "rolling_window": af.get("rolling_window"),
        "kendall_lookback": af.get("kendall_lookback"),
        "detrending_method": af.get("detrending_method"),
        "composite_method": af.get("composite_method"),
        # Component-wise contributions if available
        "kendall_tau_ar1": af.get("kendall_tau_ar1"),
        "kendall_tau_variance": af.get("kendall_tau_variance"),
        "kendall_tau_skewness": af.get("kendall_tau_skewness"),
        "kendall_tau_kurtosis": af.get("kendall_tau_kurtosis"),
        "runtime_s": round(dt, 2),
    }
    print(f"  T={out['T']} EWS={out['ews_composite_score']:.4f} state={out['ews_state']}")
    print(f"  rolling_window={out['rolling_window']} kendall_lookback={out['kendall_lookback']}")
    print(f"  detrending={out['detrending_method']} composite={out['composite_method']}")
    print(f"  Kendall τ: ar1={out['kendall_tau_ar1']} var={out['kendall_tau_variance']} skew={out['kendall_tau_skewness']} kurt={out['kendall_tau_kurtosis']}")
    return out


# =====================================================
# INV3 — Parameter sensitivity sweep
# =====================================================


def inv3_sensitivity(log_ret):
    print("\n" + "=" * 70)
    print("INV3 — Parameter sensitivity sweep")
    print("=" * 70)
    y = log_ret[-2000:].tolist()
    T = len(y)

    rows = []
    # rolling_window sensitivity
    print("\n  Rolling window sweep:")
    for rw in (max(50, T // 20), T // 10, T // 4, T // 2):
        res, _, _ = _safe_run(csd_mod, _ctx(
            y, technique_id="critical_slowing_down",
            params={"rolling_window": rw}))
        if res and res.get("status") == "success":
            ews = res["audit_fields"].get("ews_composite_score")
            state = res["audit_fields"].get("ews_state")
            print(f"    rolling_window={rw}: EWS={ews:.4f} state={state}")
            rows.append({"axis": "rolling_window", "value": rw,
                          "ews": ews, "state": state})

    # detrending sweep
    print("\n  Detrending method sweep:")
    for d in ("gaussian", "first_diff", "linear"):
        res, _, _ = _safe_run(csd_mod, _ctx(
            y, technique_id="critical_slowing_down",
            params={"detrending_method": d}))
        if res and res.get("status") == "success":
            ews = res["audit_fields"].get("ews_composite_score")
            state = res["audit_fields"].get("ews_state")
            print(f"    detrending={d}: EWS={ews:.4f} state={state}")
            rows.append({"axis": "detrending_method", "value": d,
                          "ews": ews, "state": state})

    # composite_method sweep
    print("\n  Composite method sweep:")
    for c in ("equal_weight_zscore", "fisher_combined"):
        params = {"composite_method": c}
        if c == "fisher_combined":
            params["compute_pvalues"] = True
        res, _, _ = _safe_run(csd_mod, _ctx(
            y, technique_id="critical_slowing_down", params=params))
        if res and res.get("status") == "success":
            ews = res["audit_fields"].get("ews_composite_score")
            state = res["audit_fields"].get("ews_state")
            print(f"    composite={c}: EWS={ews:.4f} state={state}")
            rows.append({"axis": "composite_method", "value": c,
                          "ews": ews, "state": state})

    # kendall_lookback sweep
    print("\n  Kendall lookback sweep:")
    for kl in (30, 60, 100):
        res, _, _ = _safe_run(csd_mod, _ctx(
            y, technique_id="critical_slowing_down",
            params={"kendall_lookback": kl}))
        if res and res.get("status") == "success":
            ews = res["audit_fields"].get("ews_composite_score")
            state = res["audit_fields"].get("ews_state")
            print(f"    kendall_lookback={kl}: EWS={ews:.4f} state={state}")
            rows.append({"axis": "kendall_lookback", "value": kl,
                          "ews": ews, "state": state})

    # Compute robustness metric: fraction of cells with EWS > 3
    high_ews = sum(1 for r in rows if r["ews"] > 3.0)
    pct_high = high_ews / max(1, len(rows))
    print(f"\n  Robustness: {high_ews}/{len(rows)} cells with EWS>3 ({pct_high:.1%})")
    return {"cells": rows, "n_cells": len(rows), "frac_high_ews": pct_high}


# =====================================================
# INV4 — Autocorrelation artifact test (most diagnostic)
# =====================================================


def inv4_autocorr_artifact(log_ret):
    print("\n" + "=" * 70)
    print("INV4 — Autocorrelation artifact test (MOST DIAGNOSTIC)")
    print("=" * 70)
    y = log_ret[-2000:]

    # (a) Original
    print("\n  (a) Original DEXUSEU log returns:")
    res, _, _ = _safe_run(csd_mod, _ctx(
        y.tolist(), technique_id="critical_slowing_down"))
    ews_a = res["audit_fields"]["ews_composite_score"] if res and res.get("status") == "success" else None
    print(f"    EWS={ews_a:.4f}" if ews_a is not None else "    FAILED")

    # (b) Shuffled — preserves marginal, destroys AC
    print("\n  (b) Shuffled (AC destroyed; marginal preserved):")
    rng = np.random.default_rng(42)
    y_shuf = rng.permutation(y)
    res, _, _ = _safe_run(csd_mod, _ctx(
        y_shuf.tolist(), technique_id="critical_slowing_down"))
    ews_b = res["audit_fields"]["ews_composite_score"] if res and res.get("status") == "success" else None
    print(f"    EWS={ews_b:.4f}" if ews_b is not None else "    FAILED")

    # Compute empirical AC1 of original
    ac1_obs = float(np.corrcoef(y[:-1], y[1:])[0, 1])
    print(f"\n  Empirical AC1 of DEXUSEU returns: {ac1_obs:.4f}")

    # (c) Synthetic AR(1) with same AC1 + same variance
    print("\n  (c) Synthetic AR(1) calibrated to DEXUSEU AC1:")
    sigma_obs = float(np.std(y, ddof=1))
    T = len(y)
    rng2 = np.random.default_rng(43)
    y_ar1 = np.zeros(T)
    # Innovation variance to match unconditional variance:
    # var(y) = sigma_eps^2 / (1 - phi^2) → sigma_eps = sigma_obs * sqrt(1 - phi^2)
    sigma_eps = sigma_obs * np.sqrt(max(0.0, 1.0 - ac1_obs ** 2))
    for t in range(1, T):
        y_ar1[t] = ac1_obs * y_ar1[t - 1] + sigma_eps * rng2.standard_normal()
    res, _, _ = _safe_run(csd_mod, _ctx(
        y_ar1.tolist(), technique_id="critical_slowing_down"))
    ews_c = res["audit_fields"]["ews_composite_score"] if res and res.get("status") == "success" else None
    print(f"    EWS={ews_c:.4f}" if ews_c is not None else "    FAILED")

    # (d) AR(1) residuals (remove first lag explicitly)
    print("\n  (d) DEXUSEU returns minus AR(1) component:")
    # Estimate phi via OLS, compute residuals
    phi_hat = float(np.sum(y[:-1] * y[1:]) / max(np.sum(y[:-1] ** 2), 1e-12))
    resid = y[1:] - phi_hat * y[:-1]
    res, _, _ = _safe_run(csd_mod, _ctx(
        resid.tolist(), technique_id="critical_slowing_down"))
    ews_d = res["audit_fields"]["ews_composite_score"] if res and res.get("status") == "success" else None
    print(f"    EWS={ews_d:.4f}" if ews_d is not None else "    FAILED")

    # Diagnostic interpretation
    print("\n  Diagnostic interpretation:")
    if ews_a is None:
        verdict = "INCONCLUSIVE — original CSD failed"
    elif abs(ews_a) > 3 and ews_b is not None and abs(ews_b) < 1.5:
        if ews_c is not None and abs(ews_c) > 3:
            verdict = "ARTIFACT — explained by AR(1) autocorrelation"
        elif ews_d is not None and abs(ews_d) < 1.5:
            verdict = "AR(1)-driven — disappears after removing first lag"
        elif ews_d is not None and abs(ews_d) > 3:
            verdict = "BEYOND AC1 — survives AR(1) residualization; signal is genuine higher-order dynamics"
        else:
            verdict = "PARTIAL — AC explains some, but residual structure also present"
    elif ews_a is not None and ews_b is not None and abs(ews_b) > 3:
        verdict = "WRAPPER ISSUE — even shuffled data flags critical"
    else:
        verdict = "WEAK SIGNAL — original EWS not striking enough to diagnose"
    print(f"    → {verdict}")

    return {
        "ews_a_original": ews_a,
        "ews_b_shuffled": ews_b,
        "ews_c_synthetic_ar1": ews_c,
        "ews_d_ar1_residuals": ews_d,
        "ac1_empirical": ac1_obs,
        "phi_hat": phi_hat,
        "verdict": verdict,
    }


# =====================================================
# INV5 — Rolling window timing (when did signal emerge?)
# =====================================================


def inv5_rolling_timing(log_ret, valid_levels):
    print("\n" + "=" * 70)
    print("INV5 — Rolling window timing")
    print("=" * 70)

    # Use a sliding 2000-day window, step 50 days, recompute EWS at each step.
    # For 2498 obs total, max ~10 windows. That's enough to see emergence.
    T = len(log_ret)
    win = 2000
    step = 50
    starts = list(range(0, T - win + 1, step))
    print(f"  Total obs: {T}, sliding window {win}, step {step} → {len(starts)} windows")

    rows = []
    for s in starts:
        sub = log_ret[s:s + win].tolist()
        res, _, _ = _safe_run(csd_mod, _ctx(
            sub, technique_id="critical_slowing_down"))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            ews = af.get("ews_composite_score")
            state = af.get("ews_state")
            # End-of-window index in original series
            end_idx = s + win - 1
            rows.append({
                "window_start": s, "window_end": end_idx,
                "ews": float(ews), "state": state,
            })
            print(f"    window [{s}:{end_idx}]: EWS={ews:.4f} state={state}")

    # Identify when EWS first crossed thresholds
    first_2 = next((r["window_end"] for r in rows if abs(r["ews"]) > 2.0), None)
    first_5 = next((r["window_end"] for r in rows if abs(r["ews"]) > 5.0), None)
    final_ews = rows[-1]["ews"] if rows else None
    peak_ews = max((r["ews"] for r in rows), default=None) if rows else None
    peak_idx = next((r["window_end"] for r in rows if r["ews"] == peak_ews), None) if peak_ews is not None else None

    print(f"\n  First crossed |EWS|>2: window ending at obs {first_2}")
    print(f"  First crossed |EWS|>5: window ending at obs {first_5}")
    print(f"  Peak EWS: {peak_ews:.4f} at window ending obs {peak_idx}")
    print(f"  Final EWS: {final_ews:.4f}")

    return {
        "rows": rows,
        "first_cross_2sigma_obs": first_2,
        "first_cross_5sigma_obs": first_5,
        "peak_ews": peak_ews,
        "peak_obs": peak_idx,
        "final_ews": final_ews,
    }


# =====================================================
# INV6 — Cross-methodology validation
# =====================================================


def inv6_cross_methods(log_ret):
    print("\n" + "=" * 70)
    print("INV6 — Cross-methodology validation")
    print("=" * 70)
    y = log_ret[-2000:].tolist()

    out = {}

    # Markov switching
    print("\n  markov_switching k=2:")
    res, dt, _ = _safe_run(ms_mod, _ctx(
        y, technique_id="markov_switching",
        params={"k_regimes": 2, "switching_variance": True}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        # Probability of being in high-vol regime at end
        out["markov_switching"] = {
            "status": "success",
            "n_regimes": af.get("k_regimes"),
            "smoothed_prob_regime_0_end": af.get("smoothed_prob_regime_0_end") or af.get("filtered_prob_end"),
            "regime_means": af.get("regime_means"),
            "regime_stds": af.get("regime_stds"),
            "runtime_s": round(dt, 2),
        }
        print(f"    runtime={dt:.1f}s; audit keys: {list(af.keys())[:8]}")
    else:
        out["markov_switching"] = {"status": "failed"}

    # BOCPD
    print("\n  bocpd:")
    res, dt, _ = _safe_run(bocpd_mod, _ctx(
        y, technique_id="bocpd"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        n_cps = af.get("n_change_points")
        cp_indices = af.get("change_point_indices") or []
        recent_cp = [cp for cp in cp_indices if cp > 1500] if cp_indices else []
        out["bocpd"] = {
            "status": "success",
            "n_change_points": n_cps,
            "n_recent_cp_post_1500": len(recent_cp),
            "recent_cp_indices": recent_cp[:5],
            "runtime_s": round(dt, 2),
        }
        print(f"    n_cps={n_cps}, recent post-obs-1500: {len(recent_cp)} ({recent_cp[:5]})")
    else:
        out["bocpd"] = {"status": "failed"}

    # PELT
    print("\n  pelt_change_points:")
    res, dt, _ = _safe_run(pelt_mod, _ctx(
        y, technique_id="pelt_change_points"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        n_cps = af.get("n_change_points")
        cp_positions = af.get("change_point_positions") or []
        recent_cp = [cp for cp in cp_positions if cp > 1500]
        out["pelt"] = {
            "status": "success",
            "n_change_points": n_cps,
            "n_recent_cp_post_1500": len(recent_cp),
            "recent_cp_positions": recent_cp[:5],
            "runtime_s": round(dt, 2),
        }
        print(f"    n_cps={n_cps}, recent post-obs-1500: {len(recent_cp)} ({recent_cp[:5]})")
    else:
        out["pelt"] = {"status": "failed"}

    # STL+ESD anomaly
    print("\n  stl_esd_anomaly:")
    res, dt, _ = _safe_run(stl_mod, _ctx(
        y, technique_id="stl_esd_anomaly", params={"period": 5}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        anom_idx = af.get("anomaly_indices") or []
        recent_anom = [a for a in anom_idx if a > 1500]
        out["stl_esd"] = {
            "status": "success",
            "n_anomalies": af.get("n_anomalies"),
            "n_recent_anom_post_1500": len(recent_anom),
            "runtime_s": round(dt, 2),
        }
        print(f"    n_anom={af.get('n_anomalies')}, recent post-1500: {len(recent_anom)}")
    else:
        out["stl_esd"] = {"status": "failed"}

    # EGARCH (Session 6 winner; uses garch_model with vol="EGARCH")
    print("\n  egarch (volatility regime):")
    res, dt, _ = _safe_run(garch_mod, _ctx(
        y, technique_id="egarch",
        params={"vol": "EGARCH", "dist": "t"}))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        out["egarch"] = {
            "status": "success",
            "persistence": af.get("persistence"),
            "alpha": af.get("alpha_mean"),
            "beta": af.get("beta_mean"),
            "loglik": af.get("loglikelihood"),
            "runtime_s": round(dt, 2),
        }
        print(f"    persistence={af.get('persistence')} loglik={af.get('loglikelihood')}")
    else:
        out["egarch"] = {"status": "failed", "error": (res.get("error_message") if res else "RAISED")}
        print(f"    FAILED — {out['egarch'].get('error', '')[:60]}")

    # CAViaR (VaR-based volatility regime)
    print("\n  caviar (VaR widening?):")
    res, dt, _ = _safe_run(caviar_mod, _ctx(
        y, technique_id="caviar_quantile_dynamics"))
    if res and res.get("status") == "success":
        af = res["audit_fields"]
        out["caviar"] = {
            "status": "success",
            "specification": af.get("specification"),
            "tail_var": af.get("var_estimates_tail")[:5] if af.get("var_estimates_tail") else None,
            "runtime_s": round(dt, 2),
        }
        print(f"    runtime={dt:.1f}s")
    else:
        out["caviar"] = {"status": "failed"}

    return out


# =====================================================
# INV7 — Idiosyncratic vs systemic test
# =====================================================


def inv7_other_macro():
    print("\n" + "=" * 70)
    print("INV7 — Idiosyncratic vs systemic test")
    print("=" * 70)
    if not _FIXTURE.exists():
        return {}
    data = np.load(_FIXTURE)

    out = {}
    for sname in ("GSPC", "DGS10", "DGS2", "GOLD"):
        v = data[sname].astype(np.float64)
        v = v[~np.isnan(v)]
        if sname in ("GSPC", "GOLD"):
            sub = (100.0 * np.diff(np.log(np.maximum(v, 1e-12))))[-2000:]
            label = f"{sname}_logret"
        else:
            sub = v[-2000:]
            label = f"{sname}_level"
        res, dt, _ = _safe_run(csd_mod, _ctx(
            sub.tolist(), technique_id="critical_slowing_down", name=label))
        if res and res.get("status") == "success":
            af = res["audit_fields"]
            ews = af.get("ews_composite_score")
            state = af.get("ews_state")
            print(f"  {label}: EWS={ews:.4f} state={state} ({dt:.1f}s)")
            out[label] = {"ews": ews, "state": state, "runtime_s": round(dt, 1)}
        else:
            out[label] = {"status": "failed"}

    return out


def main():
    out_results = {"started": time.time()}

    # Load DEXUSEU
    log_ret, valid_levels = _load_dexuseu()
    print(f"Loaded DEXUSEU: {len(valid_levels)} level obs, {len(log_ret)} return obs")
    out_results["data_summary"] = {
        "n_levels": len(valid_levels),
        "n_returns": len(log_ret),
        "fixture_start": "2015-04-25",
        "fixture_end": "2025-04-25",
        "return_mean_pct": float(np.mean(log_ret)),
        "return_std_pct": float(np.std(log_ret, ddof=1)),
    }

    # INV2: Reproduce
    out_results["inv2_reproduction"] = inv2_reproduce(log_ret)

    # INV3: Sensitivity
    out_results["inv3_sensitivity"] = inv3_sensitivity(log_ret)

    # INV4: AC artifact (MOST DIAGNOSTIC)
    out_results["inv4_autocorr"] = inv4_autocorr_artifact(log_ret)

    # INV5: Rolling window timing
    out_results["inv5_rolling"] = inv5_rolling_timing(log_ret, valid_levels)

    # INV6: Cross-methodology
    out_results["inv6_cross_methods"] = inv6_cross_methods(log_ret)

    # INV7: Other macro
    out_results["inv7_other_macro"] = inv7_other_macro()

    out_results["finished"] = time.time()

    out_path = _ROOT / "tools" / "investigations" / "dexuseu_results.json"
    out_path.write_text(json.dumps(out_results, indent=2, default=str))
    print(f"\nResults: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
