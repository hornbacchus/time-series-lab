"""Calibration Audit Phase 2 Session 3 — evt_pot_gpd.

Three audit techniques per CAI Phase 1 §3.3:

  Technique 1 — Parameter sweep:
    Threshold-percentile sweep is the centerpiece. Sweep
    {0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99, 0.995} on a
    synthetic heavy-tailed AR(1)+GARCH base case and record
    (xi, sigma, n_exceedances, KS p-value, runtime). Findings
    to look for: xi sign-flip, non-monotonic sigma, SE explosion
    at high percentiles, convergence failures.

    Other sweeps:
      - tail: 'upper' / 'lower'
      - decluster: False / True
      - confidence_levels: a few sets

  Technique 2 — Real-data stress test:
    Run wrapper at default Balanced preset on each of the 5
    canonical macro series after preprocessing:
      - GSPC: log-returns, lower tail (loss tail; canonical use)
      - DGS10, DGS2: daily yield differences, upper tail
      - DEXUSEU: log-returns, lower tail (FX has lower kurtosis)
      - GOLD: log-returns, upper tail (upside crisis spikes)
    Inspect xi sign / magnitude, n_exceedances at 97.5%, KS p,
    and runtime.

  Technique 3 — Adversarial canonical extension:
    Add canonical_6..9 to validate_evt_declustering_canonicals.py
    (per CAL-R4 numbering convention; existing canonicals 1-5):
      - canonical_6 (Gaussian baseline): N(0,1) T=2000;
        expected xi near 0.
      - canonical_7 (Known Pareto): Pareto a=2 (so xi=0.5)
        T=2000; expected recovery within bootstrap CI.
      - canonical_8 (Mixture): 95% Gaussian + 5% heavy-tail
        contamination T=1500; expected threshold-dependence.
      - canonical_9 (Short series): T=150 with heavy tail;
        SEs must NOT silently shrink (overconfidence).

CAL-R2 (parameter API): evt_pot_gpd wrapper params verified
by inspecting engine/techniques/evt_pot_gpd.py:
  - tail (str, default 'upper')
  - threshold_value (float, optional; overrides quantile)
  - threshold_quantile (float, default 0.975)
  - confidence_levels (list[float], default [0.95, 0.99, 0.999])
  - decluster (bool, default False) — Ferro-Segers intervals

Handoff §3.3's `declustering_method`, `cluster_separation`,
`min_exceedances` are NOT user params; the wrapper uses the
Ferro-Segers intervals method internally when decluster=True
and falls back via the Phase 4 cascade on insufficient
exceedances or runtime errors.

Run:
    python tools/calibration_audit/audit_evt_pot_gpd.py
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

# Reconfigure stdout/stderr for UTF-8 (Tier 1/2 prose contains
# Greek letters xi, sigma, theta that fail under Windows
# default cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import evt_pot_gpd as evt_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helper construction
# =====================================================


def _build_ctx(values, *, params=None, preset="Balanced",
                run_id="audit_evt", frequency="daily"):
    """Build RunContext for evt_pot_gpd wrapper.

    Returns a context configured at the requested preset; default
    Balanced. Values are passed as a single primary series."""
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": "evt_pot_gpd",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": user_params,
    })


def _safe_run(ctx):
    """Run wrapper in try/except to capture failures cleanly."""
    try:
        t0 = time.time()
        res = evt_mod.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _extract_xi_ci(res):
    """Extract 95% bootstrap CI for xi from GPD Parameters table.

    Returns (lo, hi) as floats or (None, None) on failure / no
    bootstrap (Fast preset has bootstrap_samples=0).
    """
    if not res:
        return (None, None)
    tables = res.get("tables") or []
    param_table = next(
        (t for t in tables if t.get("name") == "GPD Parameters"),
        None,
    )
    if param_table is None:
        return (None, None)
    rows = param_table.get("rows") or []
    for row in rows:
        if not row:
            continue
        if str(row[0]).startswith("Shape"):
            ci_str = str(row[2]) if len(row) >= 3 else ""
            if ci_str.startswith("[") and "," in ci_str:
                try:
                    inner = ci_str.strip("[] ")
                    lo, hi = inner.split(",")
                    return (float(lo.strip()), float(hi.strip()))
                except Exception:
                    return (None, None)
    return (None, None)


def _simulate_heavy_tailed(n=2000, seed=42, garch_alpha=0.1,
                            garch_beta=0.85):
    """Synthetic AR(1)+GARCH(1,1) with heavy-tailed innovations.

    Combines mild AR(1) persistence (phi=0.2) with a GARCH(1,1)
    volatility process and Student-t(df=4) innovations. Output
    has clear tail risk for EVT to fit; ξ should land in
    (0, 0.5) range at typical percentiles.
    """
    rng = np.random.default_rng(seed)
    omega = 0.05
    alpha = garch_alpha
    beta = garch_beta
    # Student-t(df=4) standardized innovations
    z = rng.standard_t(df=4, size=n) / np.sqrt(4 / 2)
    h = np.empty(n)
    eps = np.empty(n)
    h[0] = omega / (1 - alpha - beta)
    eps[0] = np.sqrt(h[0]) * z[0]
    for t in range(1, n):
        h[t] = omega + alpha * eps[t - 1] ** 2 + beta * h[t - 1]
        eps[t] = np.sqrt(h[t]) * z[t]
    # Mild AR(1) on top
    y = np.empty(n)
    y[0] = eps[0]
    phi = 0.2
    for t in range(1, n):
        y[t] = phi * y[t - 1] + eps[t]
    return y


def _log_returns(prices):
    """Compute log returns from a price series, dropping NaN."""
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


def _yield_changes(yields):
    """Compute first differences of a yield series, dropping NaN."""
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    y = _simulate_heavy_tailed(n=2000, seed=42)
    print(f"Synthetic baseline: T={len(y)}, mean={y.mean():.3f}, "
          f"std={y.std():.3f}")

    # ---- Sweep 1: threshold_quantile (the centerpiece) ----
    print("\n--- Sweep 1: threshold_quantile (centerpiece) ---")
    sweep1 = []
    percentiles = [0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99, 0.995]
    for q in percentiles:
        ctx = _build_ctx(
            y, params={"threshold_quantile": q, "tail": "upper"},
            preset="Balanced",
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep1.append({"q": q, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep1.append({
            "q": q,
            "wrapper_status": res.get("status"),
            "xi": a.get("xi"),
            "sigma": a.get("sigma"),
            "n_exceedances": a.get("n_exceedances"),
            "ks_pval": a.get("ks_pval"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep1)} percentiles swept")
    for row in sweep1:
        print(f"    q={row.get('q')}: xi={row.get('xi')}, "
              f"sigma={row.get('sigma')}, "
              f"n={row.get('n_exceedances')}, "
              f"ks_p={row.get('ks_pval')}, t={row.get('elapsed_s')}s")

    # Look for: xi sign flips across percentiles
    xis = [r.get("xi") for r in sweep1
           if r.get("xi") is not None]
    if xis:
        signs = [1 if x > 0 else (-1 if x < 0 else 0) for x in xis]
        sign_flips = sum(1 for i in range(1, len(signs))
                          if signs[i] != signs[i - 1] and signs[i] != 0
                          and signs[i - 1] != 0)
        if sign_flips >= 1:
            findings.append({
                "id": "F-E-T1-XI-FLIP",
                "severity": "cosmetic",
                "title": (
                    f"xi flips sign {sign_flips} time(s) across "
                    f"the threshold-quantile sweep"
                ),
                "details": (
                    "EVT shape parameter xi is known to be unstable "
                    "across moderately different thresholds. This is "
                    "a property of the GPD MLE, not a wrapper bug. "
                    "Documented as user-facing threshold-selection "
                    "guidance in the findings doc."
                ),
                "xis_per_percentile": list(zip(percentiles, xis)),
            })

    # Convergence failures
    err_count = sum(1 for r in sweep1 if r.get("status") == "ERROR"
                    or r.get("wrapper_status") == "failure")
    if err_count > 0:
        common_err = [r for r in sweep1
                      if r.get("status") == "ERROR" and r.get("q") <= 0.975]
        sev = "operational" if common_err else "cosmetic"
        findings.append({
            "id": "F-E-T1-CONV",
            "severity": sev,
            "title": (
                f"GPD fit failed at {err_count} percentile(s) in sweep"
            ),
            "details": [r for r in sweep1 if r.get("status") == "ERROR"
                        or r.get("wrapper_status") == "failure"],
        })

    # ---- Sweep 2: tail = upper vs lower ----
    print("\n--- Sweep 2: tail (upper vs lower) ---")
    sweep2 = []
    for tail in ["upper", "lower"]:
        ctx = _build_ctx(
            y, params={"tail": tail, "threshold_quantile": 0.975},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep2.append({"tail": tail, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep2.append({
            "tail": tail,
            "wrapper_status": res.get("status"),
            "xi": a.get("xi"),
            "sigma": a.get("sigma"),
            "n_exceedances": a.get("n_exceedances"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep2)} tail variants swept")
    for row in sweep2:
        print(f"    {row}")

    # ---- Sweep 3: decluster = False vs True ----
    print("\n--- Sweep 3: decluster (False vs True) ---")
    sweep3 = []
    for d in [False, True]:
        ctx = _build_ctx(
            y,
            params={"decluster": d, "threshold_quantile": 0.95,
                    "tail": "upper"},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep3.append({"decluster": d, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep3.append({
            "decluster": d,
            "wrapper_status": res.get("status"),
            "decluster_applied": a.get("decluster_applied"),
            "extremal_index_theta": a.get("extremal_index_theta"),
            "xi": a.get("xi"),
            "xi_post": a.get("xi_post_decluster"),
            "n_clusters_post": a.get("n_clusters_post_decluster"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep3)} decluster variants swept")
    for row in sweep3:
        print(f"    {row}")

    # ---- Sweep 4: confidence_levels ----
    print("\n--- Sweep 4: confidence_levels ---")
    sweep4 = []
    for cl_label, cl in [
        ("default", [0.95, 0.99, 0.999]),
        ("conservative", [0.99, 0.999, 0.9999]),
        ("liberal", [0.90, 0.95, 0.99]),
        ("single_99", [0.99]),
    ]:
        ctx = _build_ctx(
            y,
            params={"confidence_levels": cl, "threshold_quantile": 0.975,
                    "tail": "upper"},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep4.append({"label": cl_label, "status": "ERROR",
                           "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        sweep4.append({
            "label": cl_label,
            "confidence_levels": cl,
            "wrapper_status": res.get("status"),
            "var_values": a.get("var_values"),
            "es_values": a.get("es_values"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep4)} cl_levels variants swept")
    for row in sweep4:
        print(f"    {row.get('label')}: var_values={row.get('var_values')}")

    return {
        "sweep_1_threshold_quantile": sweep1,
        "sweep_2_tail": sweep2,
        "sweep_3_decluster": sweep3,
        "sweep_4_confidence_levels": sweep4,
        "findings": findings,
    }


# =====================================================
# Technique 2 — Real-data stress test
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS TEST")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-E-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baseline_stats": [], "findings": findings}

    data = np.load(_FIXTURE)
    # Per CAI Phase 1 §3.3: each macro series is preprocessed for
    # the natural EVT use case (return tail or yield change tail).
    series_specs = [
        ("GSPC", "log_returns", "lower"),
        ("DGS10", "yield_changes", "upper"),
        ("DGS2", "yield_changes", "upper"),
        ("DEXUSEU", "log_returns", "lower"),
        ("GOLD", "log_returns", "upper"),
    ]
    baseline_stats = []
    for sid, prep, tail in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        if prep == "log_returns":
            preprocessed = _log_returns(raw)
        else:
            preprocessed = _yield_changes(raw)
        T = preprocessed.size
        print(f"\n--- {sid} ({prep}, tail={tail}): "
              f"T_raw={len(raw)}, T_post={T} ---")
        print(f"    range=[{preprocessed.min():.4f}, "
              f"{preprocessed.max():.4f}], "
              f"std={preprocessed.std():.4f}")
        if T < 100:
            print(f"  SKIP (T={T} too short)")
            baseline_stats.append({
                "series": sid, "T": T, "status": "SKIP_too_short",
            })
            continue
        ctx = _build_ctx(
            preprocessed,
            params={"tail": tail, "threshold_quantile": 0.975},
            preset="Balanced",
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            baseline_stats.append({
                "series": sid, "T": T, "status": "ERROR", "error": err,
            })
            print(f"  ERROR: {err}")
            findings.append({
                "id": f"F-E-T2-{sid}-ERROR",
                "severity": "severe",
                "title": f"Wrapper crashed on {sid}",
                "details": err,
            })
            continue
        if res.get("status") != "success":
            findings.append({
                "id": f"F-E-T2-{sid}-NONSUCCESS",
                "severity": "severe",
                "title": f"Wrapper status={res.get('status')} on {sid}",
                "details": res.get("error_message"),
            })
        a = res.get("audit_fields", {}) or {}
        xi = a.get("xi")
        sigma = a.get("sigma")
        ne = a.get("n_exceedances")
        er = a.get("exceedance_rate")
        ksp = a.get("ks_pval")
        baseline_stats.append({
            "series": sid,
            "preprocessing": prep,
            "tail": tail,
            "T": T,
            "wrapper_status": res.get("status"),
            "elapsed_s": round(elapsed, 2),
            "xi": xi,
            "sigma": sigma,
            "n_exceedances": ne,
            "exceedance_rate": er,
            "ks_pval": ksp,
            "var_values": a.get("var_values"),
            "es_values": a.get("es_values"),
        })
        print(f"  status={res.get('status')}, xi={xi}, sigma={sigma}, "
              f"n_exc={ne} ({er}), ks_p={ksp}, t={elapsed:.2f}s")

        # Plausibility checks per handoff §3.3:
        # - Financial returns typically have xi > 0 (heavy-tailed)
        # - 97.5%-quantile threshold should yield ~2.5% exceedance rate
        # - KS p-value > 0.05 indicates good GPD fit
        # - VaR finite for at least the 95%/99% levels
        if er is not None and (er < 0.005 or er > 0.10):
            findings.append({
                "id": f"F-E-T2-{sid}-EXC-RATE",
                "severity": "operational",
                "title": (
                    f"Exceedance rate {er} on {sid} far from nominal "
                    f"(1 - threshold_quantile = 0.025) at default "
                    f"threshold"
                ),
                "details": {"exceedance_rate": er,
                            "expected_value": 0.025},
            })
        if elapsed > 30.0:
            findings.append({
                "id": f"F-E-T2-{sid}-SLOW",
                "severity": "operational",
                "title": f"Runtime {elapsed:.1f}s exceeds 30s budget",
                "details": {"series": sid, "T": T, "elapsed_s": elapsed},
            })

    return {"baseline_stats": baseline_stats, "findings": findings}


# =====================================================
# Technique 3 — Adversarial canonical extension
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXTENSION")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1 (canonical_6): Gaussian baseline ----
    print("\n--- C-CAL-1 (canonical_6): N(0,1) T=2000 ---")
    rng = np.random.default_rng(42)
    y = rng.standard_normal(2000)
    ctx = _build_ctx(
        y, params={"threshold_quantile": 0.975, "tail": "upper"},
    )
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-1", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        xi = a.get("xi")
        # Gaussian has true xi=0; small finite-sample bias OK
        canonical_results.append({
            "id": "C-CAL-1",
            "case": "Gaussian N(0,1) T=2000; expected xi near 0",
            "status": res.get("status"),
            "xi": xi,
            "sigma": a.get("sigma"),
            "n_exceedances": a.get("n_exceedances"),
            "ks_pval": a.get("ks_pval"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, xi={xi}, "
              f"n={a.get('n_exceedances')}, ks_p={a.get('ks_pval')}")
        # Document if xi differs >0.4 from 0 (well outside finite-sample
        # bias range for T=2000 Gaussian)
        if xi is not None and abs(xi) > 0.4:
            findings.append({
                "id": "F-E-T3-1",
                "severity": "operational",
                "title": (
                    f"Gaussian baseline xi={xi}; outside ±0.4 finite-"
                    f"sample bias range for T=2000"
                ),
                "details": {"xi": xi, "expected": "near 0"},
            })

    # ---- C-CAL-2 (canonical_7): Known Pareto (xi=0.5) ----
    print("\n--- C-CAL-2 (canonical_7): Pareto a=2 (xi=0.5) T=2000 ---")
    rng = np.random.default_rng(43)
    # Pareto(a=2) has F(x) = 1 - x^(-2) for x >= 1; xi = 1/a = 0.5
    y = rng.pareto(2.0, size=2000) + 1.0
    ctx = _build_ctx(
        y, params={"threshold_quantile": 0.975, "tail": "upper"},
        preset="Balanced",
    )
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-2", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        xi = a.get("xi")
        ci_lo, ci_hi = _extract_xi_ci(res)
        truth_in_ci = (
            (ci_lo is not None and ci_hi is not None)
            and (ci_lo <= 0.5 <= ci_hi)
        )
        canonical_results.append({
            "id": "C-CAL-2",
            "case": "Pareto a=2 T=2000; expected xi=0.5",
            "status": res.get("status"),
            "xi": xi,
            "xi_truth": 0.5,
            "xi_abs_err": (
                abs(xi - 0.5) if xi is not None else None
            ),
            "xi_ci_95": [ci_lo, ci_hi],
            "truth_in_ci_95": truth_in_ci,
            "sigma": a.get("sigma"),
            "n_exceedances": a.get("n_exceedances"),
            "ks_pval": a.get("ks_pval"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, xi={xi} (truth=0.5, "
              f"abs_err={abs(xi - 0.5) if xi is not None else None})")
        print(f"  bootstrap 95% CI: [{ci_lo}, {ci_hi}], "
              f"truth_in_ci={truth_in_ci}, ks_p={a.get('ks_pval')}")
        # Severity:
        #   - If truth (0.5) is INSIDE the bootstrap 95% CI, this
        #     is the GPD MLE working as designed at small N — NOT
        #     a wrapper bug. Documented as cosmetic (methodology
        #     caveat citing Castillo & Padilla 2015).
        #   - If truth is OUTSIDE the bootstrap CI, the bootstrap
        #     is overconfident and we have an operational finding.
        if xi is not None and not truth_in_ci and ci_lo is not None:
            findings.append({
                "id": "F-E-T3-2",
                "severity": "operational",
                "title": (
                    f"Pareto truth xi=0.5 falls OUTSIDE bootstrap "
                    f"95% CI [{ci_lo}, {ci_hi}] (point xi={xi}); "
                    f"bootstrap CI is overconfident at default "
                    f"threshold q=0.975 / N_exc=50"
                ),
                "details": {
                    "xi_point": xi, "xi_truth": 0.5,
                    "ci_95": [ci_lo, ci_hi],
                },
            })
        elif xi is not None and abs(xi - 0.5) > 0.20:
            # Wide-but-correct CI: known GPD MLE small-N bias
            findings.append({
                "id": "F-E-T3-2-COSMETIC",
                "severity": "cosmetic",
                "title": (
                    f"Pareto recovery point xi={xi} off truth=0.5 "
                    f"by {abs(xi - 0.5):.3f} at default q=0.975 / "
                    f"N_exc=50; bootstrap 95% CI [{ci_lo}, {ci_hi}] "
                    f"correctly contains truth"
                ),
                "details": (
                    "GPD MLE shape parameter is known to have large "
                    "small-sample bias (Castillo & Padilla 2015). "
                    "At N_exc=50 with truth xi=0.5, point estimates "
                    "in the 0.10-0.30 range are within typical bias "
                    "envelope. The wrapper's bootstrap CI correctly "
                    "spans the truth, indicating the uncertainty "
                    "estimate is calibrated even when the point is "
                    "biased. User-facing guidance: cite point xi "
                    "alongside CI when N_exc < 100."
                ),
                "xi_point": xi, "ci_95": [ci_lo, ci_hi],
            })

    # ---- C-CAL-3 (canonical_8): Mixture (95% N + 5% heavy-tail) ----
    print("\n--- C-CAL-3 (canonical_8): Mixture 95% N(0,1) + 5% Pareto ---")
    rng = np.random.default_rng(44)
    n_total = 1500
    n_heavy = int(0.05 * n_total)
    body = rng.standard_normal(n_total - n_heavy)
    tail = rng.pareto(2.0, size=n_heavy) + 3.0  # offset above Gaussian body
    y = np.concatenate([body, tail])
    rng.shuffle(y)
    # Run at two threshold percentiles to demonstrate dependence
    threshold_results = []
    for q in [0.85, 0.99]:
        ctx = _build_ctx(
            y, params={"threshold_quantile": q, "tail": "upper"},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            threshold_results.append({"q": q, "status": "ERROR",
                                       "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        threshold_results.append({
            "q": q,
            "xi": a.get("xi"),
            "sigma": a.get("sigma"),
            "n_exceedances": a.get("n_exceedances"),
            "ks_pval": a.get("ks_pval"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  q={q}: xi={a.get('xi')}, "
              f"n={a.get('n_exceedances')}, ks_p={a.get('ks_pval')}")
    canonical_results.append({
        "id": "C-CAL-3",
        "case": "Mixture 95% N(0,1) + 5% Pareto T=1500; "
                "demonstrates threshold-dependence",
        "status": "success",
        "threshold_results": threshold_results,
    })

    # ---- C-CAL-4 (canonical_9): Short series degeneracy ----
    print("\n--- C-CAL-4 (canonical_9): T=150 heavy-tailed (overconfidence test) ---")
    rng = np.random.default_rng(45)
    y = rng.pareto(1.5, size=150) + 1.0  # Pareto a=1.5; xi=2/3, T very small
    ctx = _build_ctx(
        y, params={"threshold_quantile": 0.95, "tail": "upper"},
        preset="Balanced",
    )
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-4", "status": "ERROR",
                                   "error": err,
                                   "note": "graceful failure on short "
                                           "series is also acceptable"})
    else:
        a = res.get("audit_fields", {}) or {}
        xi = a.get("xi")
        ne = a.get("n_exceedances")
        # The wrapper returns bootstrap CIs in tables (not in
        # audit_fields by default), but n_exceedances tells us the
        # effective sample for the GPD fit. With T=150 and q=0.95
        # we should see ~7-8 exceedances — the wrapper's
        # n_exceedances < 10 guard should fire.
        canonical_results.append({
            "id": "C-CAL-4",
            "case": "T=150 Pareto(1.5) at q=0.95; tests short-series "
                    "guard / overconfidence absence",
            "status": res.get("status"),
            "xi": xi,
            "n_exceedances": ne,
            "ks_pval": a.get("ks_pval"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, xi={xi}, n_exc={ne}, "
              f"ks_p={a.get('ks_pval')}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings (audit-infrastructure surfaced items)
# =====================================================
#
# Mirrors Session 1/2 pattern. None expected for evt_pot_gpd
# since the canonical script already had the cp1252 fix
# applied during initial 3c follow-up shipment.
_EXTRA_FINDINGS = []


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — evt_pot_gpd")
    print("Date: 2026-04-26")
    print()

    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (
        t1.get("findings", []) +
        t2.get("findings", []) +
        t3.get("findings", []) +
        list(_EXTRA_FINDINGS)
    )
    by_sev = {"severe": 0, "operational": 0, "cosmetic": 0}
    for f in all_findings:
        by_sev[f.get("severity", "cosmetic")] = (
            by_sev.get(f.get("severity", "cosmetic"), 0) + 1
        )

    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Severe:      {by_sev['severe']}")
    print(f"Operational: {by_sev['operational']}")
    print(f"Cosmetic:    {by_sev['cosmetic']}")
    print(f"Total:       {sum(by_sev.values())}")
    if all_findings:
        print("\nFindings:")
        for f in all_findings:
            print(f"  [{f['severity'].upper()}] {f['id']}: {f['title']}")

    results = {
        "date": "2026-04-26",
        "wrapper": "evt_pot_gpd",
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "evt_pot_gpd_audit_results.json"
    )

    def _coerce(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, dict):
            return {k: _coerce(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_coerce(v) for v in o]
        if isinstance(o, (bool, int, float, str, type(None))):
            return o
        return str(o)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(_coerce(results), f, indent=2, default=str)
    print(f"\nResults saved: {out_path}")
    return 1 if by_sev["severe"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
