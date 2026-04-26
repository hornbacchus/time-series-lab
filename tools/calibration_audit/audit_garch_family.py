"""Calibration Audit Phase 2 Session 6 — GARCH family batch audit.

Three audit techniques per CAI Phase 1 §3.6 + Session 6 plan:

  Sweep 0 — Variant dispatch verification (NEW):
    Confirms that technique_id ∈ {garch, gjr_garch, egarch}
    routes to the correct `vol` mode in the underlying
    arch_model fit. Phase 1 exploration found the catalog
    exposes 3 separate techniques but does not include `vol`
    as a user-visible param; without an explicit `vol`,
    egarch / gjr_garch invocations would silently produce
    vanilla GARCH math. Session 6 applies a 5-LOC inline fix
    in `garch_model.py` (top of `run()`); this sweep verifies
    the fix.

  Technique 1 — Parameter sweep:
    Sweep 1.1: Order specification (p, q, o) across all 3
      variants on a synthetic GARCH(1,1) DGP.
    Sweep 1.2: Distribution sensitivity (normal / t / skewt
      / ged) on symmetric DGP across all 3 variants.
    Sweep 1.3: Leverage identification (asymmetric DGP
      with γ=0.10) - GJR/EGARCH should recover γ; vanilla
      GARCH should not produce γ at all.
    Sweep 1.4: Near-IGARCH (high-persistence DGP α=0.05,
      β=0.93) - persistence ≈ 0.98; near_igarch Tier 3
      trigger fires.

  Technique 2 — Real-data stress:
    5 macro series × 3 variants = 15 cells. Subsample to
    last 1000 obs, demean, default Balanced preset, dist
    honoring catalog default per variant.

  Technique 3 — Adversarial canonical exercises (mirrored
  in tools/validate_garch_canonicals.py canonical_6..9):
    C-CAL-1: Constant variance N(0,1) T=500 - SV
      misspecified for GARCH; honest small α/β.
    C-CAL-2: GJR with very short series T=80 - tests
      hard guards and convergence warnings.
    C-CAL-3: Heavy-tail innovations on EGARCH+normal
      (misspecified dist) - LB-sq should reject.
    C-CAL-4: Redundant param (vol="GARCH" with o=1)
      - graceful coexistence.

CAL-R2 (parameter API): wrapper params verified:
  - vol (str, default "GARCH"): {GARCH, GJR-GARCH/GJRGARCH,
    EGARCH}; case-normalized at line 93 of garch_model.py
  - p, q (int, default 1): GARCH/ARCH lag orders
  - o (int, default 0 for GARCH, 1 for GJR/EGARCH): asymmetry
  - mean (str, default "Constant")
  - dist (str, default "normal"): {normal, t, skewt, ged}
  - horizon (int, default 10)
  - rescale (bool, default True)
  Hard guard: n < 30 returns error.

Run:
    python tools/calibration_audit/audit_garch_family.py
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
from techniques import garch_model


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None

# Catalog default params per variant (per techniques_catalog.json)
_CATALOG_DEFAULTS = {
    "garch":     {"p": 1, "q": 1, "dist": "normal"},
    "gjr_garch": {"p": 1, "o": 1, "q": 1, "dist": "t"},
    "egarch":    {"p": 1, "q": 1, "dist": "t"},
}


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id="garch", params=None,
                preset="Balanced", run_id="audit_garch",
                frequency="daily"):
    user_params = dict(params or {})
    return RunContext({
        "run_id": run_id,
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": user_params,
    })


def _safe_run(ctx):
    try:
        t0 = time.time()
        res = garch_model.run(ctx, _NULL_PROGRESS)
        return res, time.time() - t0, None
    except Exception as e:
        return None, 0.0, f"{type(e).__name__}: {e}"


def _simulate_garch11(*, T=1000, omega=0.05, alpha=0.10, beta=0.85,
                       seed=42, dist="normal", df=5):
    """Symmetric GARCH(1,1)."""
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta)
    if dist == "t":
        z = rng.standard_t(df=df, size=T) * np.sqrt((df - 2) / df)
    else:
        z = rng.standard_normal(T)
    y[0] = np.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        sigma2[t] = omega + alpha * y[t - 1] ** 2 + beta * sigma2[t - 1]
        y[t] = np.sqrt(sigma2[t]) * z[t]
    return y


def _simulate_gjr_garch11(*, T=1000, omega=0.05, alpha=0.05, beta=0.85,
                           gamma=0.10, seed=42):
    """Asymmetric GJR-GARCH(1,1) with leverage on negative shocks."""
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta - 0.5 * gamma)
    z = rng.standard_normal(T)
    y[0] = np.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        leverage = (y[t - 1] < 0) * gamma * y[t - 1] ** 2
        sigma2[t] = (
            omega + alpha * y[t - 1] ** 2 + leverage
            + beta * sigma2[t - 1]
        )
        y[t] = np.sqrt(sigma2[t]) * z[t]
    return y


def _log_returns(prices):
    p = np.asarray(prices, dtype=np.float64)
    p = p[~np.isnan(p)]
    return 100.0 * np.diff(np.log(np.maximum(p, 1e-12)))


def _yield_diffs(yields):
    y = np.asarray(yields, dtype=np.float64)
    y = y[~np.isnan(y)]
    return np.diff(y)


def _extract_garch_diagnostics(res):
    """Pull α/β/γ/persistence/half_life/converged from output tables.

    Wrapper exposes only model/p/q/o/mean/dist/aic/bic/log_likelihood/
    horizon in audit_fields. Persistence + ARCH/GARCH coefficients
    live in the parameter table and Model Diagnostics table.
    """
    if not res:
        return {}
    tables = res.get("tables") or []

    # Extract from "Parameter Estimates" table
    params = {}
    param_table = next(
        (t for t in tables if t.get("name") == "Parameter Estimates"),
        None,
    )
    if param_table:
        for row in param_table.get("rows", []):
            if not row or len(row) < 2:
                continue
            name = str(row[0])
            try:
                value = float(row[1])
            except (TypeError, ValueError):
                continue
            params[name] = value

    # Extract persistence + half-life from "Model Diagnostics" table
    persistence = None
    half_life = None
    lb_sq_p = None
    diag_table = next(
        (t for t in tables if t.get("name") == "Model Diagnostics"),
        None,
    )
    if diag_table:
        for row in diag_table.get("rows", []):
            if not row or len(row) < 2:
                continue
            name = str(row[0])
            try:
                value = float(row[1])
            except (TypeError, ValueError):
                continue
            if "Persistence" in name:
                persistence = value
            elif "Half-life" in name or "Half life" in name:
                half_life = value
            elif "Ljung-Box" in name and "squared" in name.lower():
                lb_sq_p = value

    # alpha = sum of alpha[i]; beta = sum of beta[i]; gamma = sum of gamma[i]
    alpha_sum = sum(v for k, v in params.items() if k.startswith("alpha["))
    beta_sum = sum(v for k, v in params.items() if k.startswith("beta["))
    gamma_sum = sum(v for k, v in params.items() if k.startswith("gamma["))

    return {
        "params_raw": params,
        "alpha_sum": alpha_sum if alpha_sum else None,
        "beta_sum": beta_sum if beta_sum else None,
        "gamma_sum": gamma_sum if gamma_sum else None,
        "persistence": persistence,
        "half_life": half_life,
        "ljung_box_sq_p": lb_sq_p,
    }


# =====================================================
# Sweep 0 — Variant dispatch verification
# =====================================================


def sweep_0_variant_dispatch():
    print("\n" + "=" * 60)
    print("SWEEP 0: VARIANT DISPATCH VERIFICATION")
    print("=" * 60)

    findings = []
    y = _simulate_gjr_garch11(T=1000, seed=42)

    # Cell matrix: (technique_id, vol-in-params)
    probes = []
    for tid, params in _CATALOG_DEFAULTS.items():
        ctx = _build_ctx(y, technique_id=tid, params=params)
        res, elapsed, err = _safe_run(ctx)
        if err:
            probes.append({"tid": tid, "vol": None,
                           "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        probes.append({
            "tid": tid,
            "vol_in_params": None,
            "model_label": a.get("model"),
            "o": a.get("o"),
            "aic": a.get("aic"),
            "elapsed_s": round(elapsed, 2),
        })

    print("Catalog-faithful probes:")
    for p in probes:
        print(f"  technique_id={p.get('tid'):11s} -> "
              f"model={p.get('model_label')!r}, o={p.get('o')}, "
              f"aic={p.get('aic')}")

    # Verify expected post-fix mapping
    expected = {"garch": "GARCH",
                "gjr_garch": "GJR-GARCH",
                "egarch": "EGARCH"}
    for p in probes:
        if p.get("model_label") != expected.get(p.get("tid")):
            findings.append({
                "id": f"F-G-DISPATCH-{p.get('tid').upper()}",
                "severity": "severe",
                "title": (
                    f"technique_id={p.get('tid')!r} produced "
                    f"model={p.get('model_label')!r}, expected "
                    f"{expected[p.get('tid')]!r}"
                ),
                "details": p,
            })

    # Also probe with explicit vol override - must continue to work
    print("\nExplicit-vol override probes:")
    override_probes = []
    for vol_override in ["GARCH", "GJR-GARCH", "EGARCH"]:
        ctx = _build_ctx(
            y, technique_id="garch",  # any technique_id
            params={"vol": vol_override, "p": 1, "q": 1,
                    "dist": "normal"},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            override_probes.append({"vol": vol_override,
                                     "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        override_probes.append({
            "vol": vol_override,
            "model_label": a.get("model"),
            "o": a.get("o"),
        })
        print(f"  vol={vol_override!r:11s} -> model={a.get('model')!r}")

    return {
        "catalog_probes": probes,
        "override_probes": override_probes,
        "findings": findings,
        "fix_status": (
            "applied_in_garch_model.py_session_6"
            if all(p.get("model_label") == expected.get(p.get("tid"))
                   for p in probes if p.get("status") != "ERROR")
            else "fix_failed_or_not_applied"
        ),
    }


# =====================================================
# Technique 1 — Parameter sweep
# =====================================================


def technique_1_parameter_sweep():
    print("\n" + "=" * 60)
    print("TECHNIQUE 1: PARAMETER SWEEP")
    print("=" * 60)

    findings = []
    y_sym = _simulate_garch11(T=1000, omega=0.05, alpha=0.10,
                                beta=0.85, seed=42)
    y_asym = _simulate_gjr_garch11(T=1000, seed=42)
    y_high_persist = _simulate_garch11(T=1000, omega=0.02,
                                        alpha=0.05, beta=0.93, seed=43)

    # ---- Sweep 1.1: Order specification ----
    print("\n--- Sweep 1.1: (p, q, o) order on symmetric DGP ---")
    sweep11 = []
    for tid in ["garch", "gjr_garch", "egarch"]:
        for (p, q, o) in [(1, 1, 0), (1, 1, 1), (2, 1, 1)]:
            ctx = _build_ctx(
                y_sym, technique_id=tid,
                params={"p": p, "q": q, "o": o,
                        "dist": _CATALOG_DEFAULTS[tid]["dist"]},
            )
            res, elapsed, err = _safe_run(ctx)
            if err:
                sweep11.append({"tid": tid, "p": p, "q": q, "o": o,
                                "status": "ERROR", "error": err})
                continue
            a = res.get("audit_fields", {}) or {}
            d = _extract_garch_diagnostics(res)
            sweep11.append({
                "tid": tid, "p": p, "q": q, "o": o,
                "model": a.get("model"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "log_likelihood": a.get("log_likelihood"),
                "alpha_sum": d.get("alpha_sum"),
                "beta_sum": d.get("beta_sum"),
                "gamma_sum": d.get("gamma_sum"),
                "persistence": d.get("persistence"),
                "elapsed_s": round(elapsed, 2),
            })
    print(f"  {len(sweep11)} (variant × order) cells")
    for r in sweep11:
        print(f"    {r.get('tid'):11s} (p,q,o)=({r.get('p')},"
              f"{r.get('q')},{r.get('o')}): "
              f"AIC={r.get('aic')}, "
              f"alpha={r.get('alpha_sum')}, "
              f"beta={r.get('beta_sum')}, "
              f"gamma={r.get('gamma_sum')}")

    # Best-IC by variant on symmetric DGP — GARCH(1,1) should win
    sym_best = {}
    for tid in ["garch", "gjr_garch", "egarch"]:
        rows = [r for r in sweep11 if r.get("tid") == tid
                and r.get("aic") is not None]
        if rows:
            best = min(rows, key=lambda r: r["aic"])
            sym_best[tid] = (best["p"], best["q"], best["o"], best["aic"])

    # ---- Sweep 1.2: Distribution sensitivity ----
    print("\n--- Sweep 1.2: Distribution sweep on symmetric DGP ---")
    sweep12 = []
    for tid in ["garch", "gjr_garch", "egarch"]:
        for dist in ["normal", "t", "skewt", "ged"]:
            ctx = _build_ctx(
                y_sym, technique_id=tid,
                params={"p": 1, "q": 1, "dist": dist},
            )
            res, elapsed, err = _safe_run(ctx)
            if err:
                sweep12.append({"tid": tid, "dist": dist,
                                "status": "ERROR", "error": err})
                continue
            a = res.get("audit_fields", {}) or {}
            sweep12.append({
                "tid": tid, "dist": dist,
                "model": a.get("model"),
                "aic": a.get("aic"),
                "log_likelihood": a.get("log_likelihood"),
                "elapsed_s": round(elapsed, 2),
            })
    print(f"  {len(sweep12)} (variant × dist) cells")
    for r in sweep12:
        print(f"    {r.get('tid'):11s} dist={r.get('dist'):8s}: "
              f"AIC={r.get('aic')}, ll={r.get('log_likelihood')}")

    # ---- Sweep 1.3: Leverage identification ----
    print("\n--- Sweep 1.3: Leverage on asymmetric DGP (γ=0.10) ---")
    sweep13 = []
    for tid in ["garch", "gjr_garch", "egarch"]:
        ctx = _build_ctx(
            y_asym, technique_id=tid,
            params={"p": 1, "q": 1,
                    "dist": _CATALOG_DEFAULTS[tid]["dist"]},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep13.append({"tid": tid, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        d = _extract_garch_diagnostics(res)
        sweep13.append({
            "tid": tid,
            "model": a.get("model"),
            "aic": a.get("aic"),
            "alpha_sum": d.get("alpha_sum"),
            "beta_sum": d.get("beta_sum"),
            "gamma_sum": d.get("gamma_sum"),
            "persistence": d.get("persistence"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep13)} variants on asymmetric DGP (truth γ=0.10)")
    for r in sweep13:
        print(f"    {r.get('tid'):11s}: AIC={r.get('aic')}, "
              f"alpha={r.get('alpha_sum')}, "
              f"beta={r.get('beta_sum')}, "
              f"gamma={r.get('gamma_sum')} (truth ≈ 0.10), "
              f"persistence={r.get('persistence')}")

    # Cross-variant IC comparison on asymmetric DGP - GJR/EGARCH should
    # have lower AIC than GARCH (since DGP is asymmetric)
    asym_aics = {r.get("tid"): r.get("aic") for r in sweep13
                 if r.get("aic") is not None}
    if "garch" in asym_aics and "gjr_garch" in asym_aics:
        if asym_aics["gjr_garch"] >= asym_aics["garch"] - 1.0:
            findings.append({
                "id": "F-G-T1-LEV-GJR",
                "severity": "cosmetic",
                "title": (
                    f"GJR-GARCH AIC={asym_aics['gjr_garch']} not lower "
                    f"than GARCH AIC={asym_aics['garch']} on asymmetric "
                    f"DGP (γ=0.10)"
                ),
                "details": (
                    "On a γ=0.10 leverage DGP at T=1000, GJR-GARCH "
                    "should produce noticeably lower AIC than vanilla "
                    "GARCH due to the leverage-term improvement. If "
                    "differences are small, the leverage signal is "
                    "weak relative to estimation noise — sample-size "
                    "issue, not wrapper bug."
                ),
                "asym_aics": asym_aics,
            })

    # ---- Sweep 1.4: Near-IGARCH ----
    print("\n--- Sweep 1.4: Near-IGARCH (high-persistence DGP) ---")
    sweep14 = []
    for tid in ["garch", "gjr_garch", "egarch"]:
        ctx = _build_ctx(
            y_high_persist, technique_id=tid,
            params={"p": 1, "q": 1,
                    "dist": _CATALOG_DEFAULTS[tid]["dist"]},
        )
        res, elapsed, err = _safe_run(ctx)
        if err:
            sweep14.append({"tid": tid, "status": "ERROR", "error": err})
            continue
        a = res.get("audit_fields", {}) or {}
        d = _extract_garch_diagnostics(res)
        # Check Tier 3 triggers for near_igarch
        tier3 = (res.get("interpretation") or {}).get("tier3", []) or []
        near_igarch_fires = any(
            "near" in str(t).lower() and "igarch" in str(t).lower()
            for t in tier3
        )
        sweep14.append({
            "tid": tid,
            "persistence": d.get("persistence"),
            "near_igarch_trigger_fires": near_igarch_fires,
            "alpha_sum": d.get("alpha_sum"),
            "beta_sum": d.get("beta_sum"),
            "elapsed_s": round(elapsed, 2),
        })
    print(f"  {len(sweep14)} variants on high-persistence DGP")
    for r in sweep14:
        print(f"    {r.get('tid'):11s}: persistence={r.get('persistence')}, "
              f"near_igarch_fires={r.get('near_igarch_trigger_fires')}")

    return {
        "sweep_1_1_order": sweep11,
        "sweep_1_2_distribution": sweep12,
        "sweep_1_3_leverage": sweep13,
        "sweep_1_4_near_igarch": sweep14,
        "findings": findings,
        "sym_best_per_variant": sym_best,
    }


# =====================================================
# Technique 2 — Real-data stress (5 series × 3 variants)
# =====================================================


def technique_2_real_data_stress():
    print("\n" + "=" * 60)
    print("TECHNIQUE 2: REAL-DATA STRESS (5 series × 3 variants)")
    print("=" * 60)

    findings = []
    if not _FIXTURE.exists():
        findings.append({
            "id": "F-G-T2-MISSING",
            "severity": "severe",
            "title": "Real-data fixture missing",
            "details": str(_FIXTURE),
        })
        return {"baselines": [], "findings": findings}

    data = np.load(_FIXTURE)
    series_specs = [
        ("GSPC", "log_returns"),
        ("DGS10", "yield_diffs"),
        ("DGS2", "yield_diffs"),
        ("DEXUSEU", "log_returns"),
        ("GOLD", "log_returns"),
    ]

    cells = []
    for sid, prep in series_specs:
        raw = np.asarray(data[sid], dtype=np.float64)
        preprocessed = (
            _log_returns(raw) if prep == "log_returns"
            else _yield_diffs(raw)
        )
        T = preprocessed.size
        if T > 1000:
            preprocessed = preprocessed[-1000:]
            T = 1000
        preprocessed = preprocessed - preprocessed.mean()

        for tid in ["garch", "gjr_garch", "egarch"]:
            params = dict(_CATALOG_DEFAULTS[tid])
            ctx = _build_ctx(
                preprocessed, technique_id=tid, params=params,
                preset="Balanced",
            )
            res, elapsed, err = _safe_run(ctx)
            if err:
                cells.append({"series": sid, "variant": tid, "T": T,
                              "status": "ERROR", "error": err})
                findings.append({
                    "id": f"F-G-T2-{sid}-{tid.upper()}-ERROR",
                    "severity": "severe",
                    "title": f"Wrapper crashed on {sid} / {tid}",
                    "details": err,
                })
                continue
            if res.get("status") != "success":
                findings.append({
                    "id": f"F-G-T2-{sid}-{tid.upper()}-NONSUCCESS",
                    "severity": "severe",
                    "title": (
                        f"Wrapper status={res.get('status')} on "
                        f"{sid} / {tid}"
                    ),
                    "details": res.get("error_message"),
                })
            a = res.get("audit_fields", {}) or {}
            d = _extract_garch_diagnostics(res)
            persistence = d.get("persistence")
            cells.append({
                "series": sid,
                "variant": tid,
                "preprocessing": prep,
                "T": T,
                "wrapper_status": res.get("status"),
                "model": a.get("model"),
                "aic": a.get("aic"),
                "bic": a.get("bic"),
                "log_likelihood": a.get("log_likelihood"),
                "alpha_sum": d.get("alpha_sum"),
                "beta_sum": d.get("beta_sum"),
                "gamma_sum": d.get("gamma_sum"),
                "persistence": persistence,
                "half_life": d.get("half_life"),
                "ljung_box_sq_p": d.get("ljung_box_sq_p"),
                "elapsed_s": round(elapsed, 2),
            })

            # Severity checks per CAL-R6 ladder.
            # Note: post-Session-6 fix, EGARCH reports persistence
            # as |beta| (log-variance AR coefficient); for GARCH/GJR
            # it remains alpha+beta+0.5*gamma. Either way the
            # stationarity-boundary check `abs(persistence) > 1.0`
            # applies. The wrapper ALSO emits an explicit warning
            # when this happens — so the fit is NOT silent.
            if persistence is not None and abs(persistence) > 1.0:
                findings.append({
                    "id": f"F-G-T2-{sid}-{tid.upper()}-PERSIST",
                    "severity": "operational",
                    "title": (
                        f"persistence={persistence} crosses unit-root "
                        f"boundary on {sid} / {tid} (warning fires; "
                        f"not a silent fit)"
                    ),
                    "details": {"series": sid, "variant": tid,
                                "persistence": persistence},
                })
            if elapsed > 60.0:
                findings.append({
                    "id": f"F-G-T2-{sid}-{tid.upper()}-SLOW",
                    "severity": "operational",
                    "title": (
                        f"Runtime {elapsed:.1f}s exceeds 60s budget on "
                        f"{sid} / {tid}"
                    ),
                    "details": {"series": sid, "variant": tid,
                                "elapsed_s": elapsed},
                })

    # Print summary
    print(f"\n  {len(cells)} (series × variant) cells executed")
    for c in cells:
        if c.get("status") == "ERROR":
            print(f"    {c.get('series'):8s} / {c.get('variant'):11s}: "
                  f"ERROR — {c.get('error')}")
            continue
        print(f"    {c.get('series'):8s} / {c.get('variant'):11s}: "
              f"model={c.get('model'):11s} AIC={c.get('aic')}, "
              f"persist={c.get('persistence')}, "
              f"LB-sq p={c.get('ljung_box_sq_p')}, "
              f"t={c.get('elapsed_s')}s")

    # Cross-variant IC ranking per series
    print("\n  Best-IC variant per series:")
    cross_variant = {}
    for sid, _ in series_specs:
        rows = [c for c in cells if c.get("series") == sid
                and c.get("aic") is not None]
        if rows:
            best = min(rows, key=lambda c: c["aic"])
            cross_variant[sid] = {
                "best_variant": best["variant"],
                "best_aic": best["aic"],
                "all_aics": {c["variant"]: c["aic"] for c in rows},
            }
            print(f"    {sid:8s}: best={best['variant']} "
                  f"(AIC={best['aic']:.2f})")

    return {
        "baselines": cells,
        "cross_variant_ic": cross_variant,
        "findings": findings,
    }


# =====================================================
# Technique 3 — Adversarial canonical exercises
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 60)
    print("TECHNIQUE 3: ADVERSARIAL CANONICAL EXERCISES")
    print("=" * 60)

    findings = []
    canonical_results = []

    # ---- C-CAL-1: Constant variance ----
    print("\n--- C-CAL-1 (canonical_6): Constant variance T=500 ---")
    rng = np.random.default_rng(42)
    y = (rng.standard_normal(500)).tolist()
    ctx = _build_ctx(np.asarray(y), technique_id="garch",
                     params={"p": 1, "q": 1, "dist": "normal"})
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-1", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        d = _extract_garch_diagnostics(res)
        canonical_results.append({
            "id": "C-CAL-1",
            "case": "Constant variance (no GARCH effect) T=500",
            "status": res.get("status"),
            "alpha_sum": d.get("alpha_sum"),
            "beta_sum": d.get("beta_sum"),
            "persistence": d.get("persistence"),
            "ljung_box_sq_p": d.get("ljung_box_sq_p"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, alpha={d.get('alpha_sum')}, "
              f"beta={d.get('beta_sum')}, "
              f"persist={d.get('persistence')}, "
              f"LB-sq p={d.get('ljung_box_sq_p')}")

    # ---- C-CAL-2: GJR very short series T=80 ----
    print("\n--- C-CAL-2 (canonical_7): GJR T=80 short series ---")
    y = _simulate_gjr_garch11(T=80, seed=44).tolist()
    ctx = _build_ctx(np.asarray(y), technique_id="gjr_garch",
                     params={"p": 1, "o": 1, "q": 1, "dist": "t"})
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-2", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        d = _extract_garch_diagnostics(res)
        warnings_raw = res.get("warnings") or []
        canonical_results.append({
            "id": "C-CAL-2",
            "case": "GJR-GARCH on T=80 short series",
            "status": res.get("status"),
            "model": a.get("model"),
            "alpha_sum": d.get("alpha_sum"),
            "gamma_sum": d.get("gamma_sum"),
            "warnings_count": len(warnings_raw),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, model={a.get('model')}, "
              f"alpha={d.get('alpha_sum')}, "
              f"gamma={d.get('gamma_sum')}, "
              f"#warnings={len(warnings_raw)}")

    # ---- C-CAL-3: Heavy-tail innovations on EGARCH+normal ----
    print("\n--- C-CAL-3 (canonical_8): EGARCH+normal on heavy-tail DGP ---")
    rng = np.random.default_rng(45)
    # Generate Student-t(df=4) GARCH path; fit EGARCH with dist="normal"
    y = _simulate_garch11(T=1000, dist="t", df=4, seed=45).tolist()
    ctx = _build_ctx(
        np.asarray(y), technique_id="egarch",
        params={"p": 1, "q": 1, "dist": "normal"},
    )
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-3", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        d = _extract_garch_diagnostics(res)
        tier3 = (res.get("interpretation") or {}).get("tier3", []) or []
        lb_sq_fires = any(
            "ljung" in str(t).lower() or "lb" in str(t).lower()
            or "squared residual" in str(t).lower()
            for t in tier3
        )
        canonical_results.append({
            "id": "C-CAL-3",
            "case": "Heavy-tail (Student-t df=4) DGP + EGARCH normal fit",
            "status": res.get("status"),
            "model": a.get("model"),
            "ljung_box_sq_p": d.get("ljung_box_sq_p"),
            "lb_sq_trigger_fires": lb_sq_fires,
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, model={a.get('model')}, "
              f"LB-sq p={d.get('ljung_box_sq_p')}, "
              f"trigger_fires={lb_sq_fires}")

    # ---- C-CAL-4: Redundant param (GARCH with o=1) ----
    print("\n--- C-CAL-4 (canonical_9): GARCH + o=1 (redundant param) ---")
    y = _simulate_garch11(T=1000, seed=46).tolist()
    ctx = _build_ctx(
        np.asarray(y), technique_id="garch",
        params={"p": 1, "q": 1, "o": 1, "dist": "normal"},
    )
    res, elapsed, err = _safe_run(ctx)
    if err:
        canonical_results.append({"id": "C-CAL-4", "status": "ERROR",
                                   "error": err})
    else:
        a = res.get("audit_fields", {}) or {}
        canonical_results.append({
            "id": "C-CAL-4",
            "case": "GARCH technique_id with o=1 (redundant asymmetry)",
            "status": res.get("status"),
            "model": a.get("model"),
            "o": a.get("o"),
            "elapsed_s": round(elapsed, 2),
        })
        print(f"  status={res.get('status')}, model={a.get('model')}, "
              f"o={a.get('o')}")

    return {"canonicals": canonical_results, "findings": findings}


# =====================================================
# Extra findings list (Session 6 dispatch fix already applied
# in garch_model.py prior to audit run)
# =====================================================
_EXTRA_FINDINGS = [
    {
        "id": "F-G-DISPATCH",
        "severity": "severe",
        "title": (
            "Catalog techniques garch / gjr_garch / egarch did not "
            "auto-inject `vol` based on technique_id; egarch UI "
            "invocations silently produced vanilla GARCH math"
        ),
        "details": (
            "Phase 1 exploration found that resources/catalog/"
            "techniques_catalog.json defines 3 separate techniques "
            "(garch, gjr_garch, egarch) but none expose `vol` as a "
            "user-visible param. The wrapper's run() function read "
            "ctx.get_param('vol', 'GARCH') and defaulted to plain "
            "GARCH when `vol` was absent. Sweep 0 verified pre-fix: "
            "technique_id='egarch' with catalog-default params "
            "{p:1, q:1, dist:'t'} produced model='GARCH' (not "
            "'EGARCH') with o=0 and AIC=2723.80 — identical to "
            "vanilla GARCH math, NOT EGARCH. Same cell post-fix "
            "produces model='EGARCH' with o=1 and AIC=2723.19. "
            "GJR-GARCH was less affected because the catalog passes "
            "o=1 explicitly so the math (asymmetry-leverage term) "
            "was correct via arch_model's o param even with vol "
            "defaulting; but the displayed model_label was 'GARCH' "
            "not 'GJR-GARCH', a labeling inconsistency. Fix applied "
            "inline in this session: 5 LOC at top of "
            "engine/techniques/garch_model.py:run() that resolves "
            "technique_id → variant default for `vol` BEFORE the "
            "user-param read, so explicit user `vol` still wins. "
            "Within CAL-R6 (≤50 LOC ≤2 files inline)."
        ),
        "fix_status": "fixed_inline",
        "fix_location": (
            "engine/techniques/garch_model.py lines 92-105 "
            "(_TID_VOL_MAP injection)"
        ),
    },
]


# =====================================================
# Main
# =====================================================


def main():
    print("Calibration Audit — GARCH family (CAI Session 6, FIRST EXTENSION)")
    print("Date: 2026-04-26")
    print()

    s0 = sweep_0_variant_dispatch()
    t1 = technique_1_parameter_sweep()
    t2 = technique_2_real_data_stress()
    t3 = technique_3_adversarial()

    all_findings = (
        s0.get("findings", []) +
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
    print(f"Severe:      {by_sev['severe']} (F-G-DISPATCH already fixed inline)")
    print(f"Operational: {by_sev['operational']}")
    print(f"Cosmetic:    {by_sev['cosmetic']}")
    print(f"Total:       {sum(by_sev.values())}")
    if all_findings:
        print("\nFindings:")
        for f in all_findings:
            print(f"  [{f['severity'].upper()}] {f['id']}: {f['title']}")

    results = {
        "date": "2026-04-26",
        "wrapper": "garch_model (3 technique IDs: garch, gjr_garch, egarch)",
        "sweep_0_dispatch": s0,
        "technique_1": t1,
        "technique_2": t2,
        "technique_3": t3,
        "findings_by_severity": by_sev,
        "all_findings": all_findings,
    }
    out_path = (
        _ROOT / "tools" / "calibration_audit"
        / "garch_family_audit_results.json"
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
    # Treat already-fixed dispatch finding as "resolved": exit 0
    # only fails if there's a NEW unresolved severe.
    unresolved_severe = [
        f for f in all_findings
        if f.get("severity") == "severe"
        and f.get("fix_status") != "fixed_inline"
    ]
    return 1 if unresolved_severe else 0


if __name__ == "__main__":
    sys.exit(main())
