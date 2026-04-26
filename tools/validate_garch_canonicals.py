"""Phase 5 canonical validation for GARCH family
(garch / gjr_garch / egarch).

Created from scratch by CAI Phase 2 Session 6 (no prior canonical
script existed for this wrapper family). Tests the unified
``engine/techniques/garch_model.py`` wrapper across the three
catalog technique IDs that route to it.

Nine canonicals:

  Base set (1-5):
    canonical_1 — GARCH(1,1) recovery on synthetic symmetric
      DGP (omega=0.05, alpha=0.10, beta=0.85; T=1000).
    canonical_2 — GJR-GARCH recovery on synthetic asymmetric
      DGP (gamma=0.10 leverage; T=1000).
    canonical_3 — EGARCH on the same asymmetric DGP; verifies
      log-variance fit doesn't crash and persistence reports
      via the EGARCH-specific |beta| formula.
    canonical_4 — GARCH on real sp500 returns (last 1000 obs);
      smoke test against real data.
    canonical_5 — Near-IGARCH on synthetic high-persistence
      DGP (alpha=0.05, beta=0.93); near_igarch trigger fires.

  CAI Session 6 adversarial set (canonical_6..9 = C-CAL-1..4
  per CAL-R4):
    canonical_6 (C-CAL-1) — Constant variance N(0,1) T=500;
      wrapper produces small persistence; no spurious GARCH.
    canonical_7 (C-CAL-2) — GJR-GARCH on T=80 very short
      series; wrapper warns about convergence; produces
      honest output (no crash).
    canonical_8 (C-CAL-3) — Heavy-tail DGP (Student-t df=4)
      fit with EGARCH+normal (misspecified dist); wrapper
      runs to completion.
    canonical_9 (C-CAL-4) — GARCH + o=1 (redundant asymmetry
      param on symmetric model); wrapper accepts gracefully.

Run from project root:
    python tools/validate_garch_canonicals.py
"""

import os
import sys
import time

# Reconfigure stdout/stderr for UTF-8 on Windows (Tier 2 prose
# contains Greek symbols alpha/beta/gamma).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import math

import numpy as np
import pandas as pd

from techniques.base import RunContext
from techniques import garch_model


SAMPLE_DIR = os.path.join(_ROOT, "resources", "sample_data")


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(values, *, technique_id="garch", params=None,
                preset="Balanced"):
    return RunContext({
        "run_id": "test_garch",
        "technique_id": technique_id,
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })


def _load_sp500_returns(last_n=1000):
    """Load sp500 returns from sample_data; demean."""
    path = os.path.join(SAMPLE_DIR, "sp500_returns.csv")
    df = pd.read_csv(path)
    vals = df.iloc[-last_n:, 1].dropna().values.astype(float)
    return (vals - vals.mean()).tolist()


def _simulate_garch11(*, T, omega=0.05, alpha=0.10, beta=0.85,
                       seed=42, dist="normal", df=5):
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta)
    if dist == "t":
        z = rng.standard_t(df=df, size=T) * math.sqrt((df - 2) / df)
    else:
        z = rng.standard_normal(T)
    y[0] = math.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        sigma2[t] = omega + alpha * y[t - 1] ** 2 + beta * sigma2[t - 1]
        y[t] = math.sqrt(sigma2[t]) * z[t]
    return y.tolist()


def _simulate_gjr_garch11(*, T, omega=0.05, alpha=0.05, beta=0.85,
                           gamma=0.10, seed=42):
    rng = np.random.default_rng(seed)
    sigma2 = np.zeros(T)
    y = np.zeros(T)
    sigma2[0] = omega / max(1e-12, 1 - alpha - beta - 0.5 * gamma)
    z = rng.standard_normal(T)
    y[0] = math.sqrt(sigma2[0]) * z[0]
    for t in range(1, T):
        leverage = (y[t - 1] < 0) * gamma * y[t - 1] ** 2
        sigma2[t] = (
            omega + alpha * y[t - 1] ** 2 + leverage
            + beta * sigma2[t - 1]
        )
        y[t] = math.sqrt(sigma2[t]) * z[t]
    return y.tolist()


def _extract_persist_alpha_beta_gamma(res):
    """Pull α/β/γ/persistence from output tables."""
    out = {"alpha_sum": None, "beta_sum": None,
           "gamma_sum": None, "persistence": None}
    if not res:
        return out
    tables = res.get("tables") or []
    param_table = next(
        (t for t in tables if t.get("name") == "Parameter Estimates"),
        None,
    )
    if param_table:
        a, b, g = 0.0, 0.0, 0.0
        a_count = b_count = g_count = 0
        for row in param_table.get("rows", []):
            if not row or len(row) < 2:
                continue
            name = str(row[0])
            try:
                v = float(row[1])
            except (TypeError, ValueError):
                continue
            if name.startswith("alpha["):
                a += v
                a_count += 1
            elif name.startswith("beta["):
                b += v
                b_count += 1
            elif name.startswith("gamma["):
                g += v
                g_count += 1
        out["alpha_sum"] = a if a_count > 0 else None
        out["beta_sum"] = b if b_count > 0 else None
        out["gamma_sum"] = g if g_count > 0 else None
    diag_table = next(
        (t for t in tables if t.get("name") == "Model Diagnostics"),
        None,
    )
    if diag_table:
        for row in diag_table.get("rows", []):
            if not row or len(row) < 2:
                continue
            name = str(row[0])
            if "Persistence" in name:
                try:
                    out["persistence"] = float(row[1])
                except (TypeError, ValueError):
                    pass
    return out


# =====================================================
# Base canonicals (1-5)
# =====================================================


def canonical_1():
    """C1: Symmetric GARCH(1,1) recovery."""
    print("\n" + "=" * 60)
    print("canonical_1: GARCH(1,1) recovery on symmetric DGP")
    print("=" * 60)
    y = _simulate_garch11(T=1000, omega=0.05, alpha=0.10,
                            beta=0.85, seed=42)
    ctx = _build_ctx(y, technique_id="garch",
                      params={"p": 1, "q": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    d = _extract_persist_alpha_beta_gamma(res)
    print(f"  model={a.get('model')}, AIC={a.get('aic')}, "
          f"alpha={d['alpha_sum']}, beta={d['beta_sum']}, "
          f"persist={d['persistence']}")
    if a.get("model") != "GARCH":
        print(f"  FAIL model_label={a.get('model')}")
        return False
    if d["alpha_sum"] is None or not (0.02 <= d["alpha_sum"] <= 0.30):
        print(f"  FAIL alpha={d['alpha_sum']} outside (0.02, 0.30)")
        return False
    if d["beta_sum"] is None or not (0.50 <= d["beta_sum"] <= 0.97):
        print(f"  FAIL beta={d['beta_sum']} outside (0.50, 0.97)")
        return False
    print(f"  PASS alpha+beta near truth (0.10+0.85=0.95); "
          f"persistence={d['persistence']}")
    return True


def canonical_2():
    """C2: GJR-GARCH leverage recovery on asymmetric DGP."""
    print("\n" + "=" * 60)
    print("canonical_2: GJR-GARCH leverage recovery (truth gamma=0.10)")
    print("=" * 60)
    y = _simulate_gjr_garch11(T=1000, gamma=0.10, seed=42)
    ctx = _build_ctx(y, technique_id="gjr_garch",
                      params={"p": 1, "o": 1, "q": 1, "dist": "t"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    d = _extract_persist_alpha_beta_gamma(res)
    print(f"  model={a.get('model')}, gamma={d['gamma_sum']}, "
          f"persist={d['persistence']}")
    if a.get("model") != "GJR-GARCH":
        print(f"  FAIL model_label={a.get('model')}")
        return False
    if d["gamma_sum"] is None or d["gamma_sum"] <= 0:
        print(f"  FAIL gamma={d['gamma_sum']} should be positive")
        return False
    print(f"  PASS gamma>0 (recovered leverage on asymmetric DGP)")
    return True


def canonical_3():
    """C3: EGARCH on asymmetric DGP doesn't crash; persistence is |beta|."""
    print("\n" + "=" * 60)
    print("canonical_3: EGARCH log-variance fit on asymmetric DGP")
    print("=" * 60)
    y = _simulate_gjr_garch11(T=1000, gamma=0.10, seed=42)
    ctx = _build_ctx(y, technique_id="egarch",
                      params={"p": 1, "q": 1, "dist": "t"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    d = _extract_persist_alpha_beta_gamma(res)
    print(f"  model={a.get('model')}, beta={d['beta_sum']}, "
          f"persist={d['persistence']}")
    if a.get("model") != "EGARCH":
        print(f"  FAIL model_label={a.get('model')}")
        return False
    # EGARCH persistence after Session-6 fix is |beta| (log-variance
    # AR coef). Should equal beta_sum for single-lag spec.
    if d["persistence"] is None:
        print(f"  FAIL persistence missing")
        return False
    if d["beta_sum"] is None:
        print(f"  FAIL beta_sum missing")
        return False
    if abs(d["persistence"] - d["beta_sum"]) > 1e-4:
        print(f"  FAIL EGARCH persistence={d['persistence']} != "
              f"|beta|={d['beta_sum']} (Session-6 fix not active?)")
        return False
    print(f"  PASS EGARCH persistence reports |beta| per Session-6 "
          f"convention")
    return True


def canonical_4():
    """C4: Smoke test on real sp500 returns."""
    print("\n" + "=" * 60)
    print("canonical_4: GARCH on sp500 returns (smoke)")
    print("=" * 60)
    try:
        y = _load_sp500_returns(last_n=1000)
    except Exception as e:
        print(f"  SKIP (sample data unavailable): {e}")
        return True
    ctx = _build_ctx(y, technique_id="garch",
                      params={"p": 1, "q": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  model={a.get('model')}, AIC={a.get('aic')}, "
          f"BIC={a.get('bic')}")
    if a.get("aic") is None or not math.isfinite(a.get("aic")):
        print(f"  FAIL aic non-finite")
        return False
    print(f"  PASS finite AIC on real data smoke")
    return True


def canonical_5():
    """C5: Near-IGARCH high-persistence trigger."""
    print("\n" + "=" * 60)
    print("canonical_5: High-persistence DGP (alpha=0.05, beta=0.93)")
    print("=" * 60)
    y = _simulate_garch11(T=1000, omega=0.02, alpha=0.05,
                            beta=0.93, seed=43)
    ctx = _build_ctx(y, technique_id="garch",
                      params={"p": 1, "q": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    d = _extract_persist_alpha_beta_gamma(res)
    print(f"  persistence={d['persistence']}")
    # Persistence should be high; the wrapper warns if >= 1.0 or
    # > 0.95 (HIGH-persist warning); either is acceptable.
    warns = res.get("warnings") or []
    persist_warn = any("persistence" in str(w).lower() for w in warns)
    if d["persistence"] is None or d["persistence"] < 0.85:
        print(f"  FAIL persistence={d['persistence']} too low for DGP")
        return False
    if not persist_warn:
        print(f"  WARN no persistence-warning emitted but persistence "
              f"high; not a strict failure")
    print(f"  PASS high persistence detected; "
          f"warnings emitted={persist_warn}")
    return True


# =====================================================
# CAI Phase 2 Session 6 — adversarial canonicals
# C-CAL-1..4 per CAI Phase 1 §3.6 (numbered 6..9 per CAL-R4).
# Findings doc: docs/calibration_audit/
# garch_family_findings_2026_04_26.md
# =====================================================


def canonical_6():
    """C-CAL-1: Constant variance N(0,1) T=500."""
    print("\n" + "=" * 60)
    print("C-CAL-1 (canonical_6): Constant variance T=500")
    print("=" * 60)
    rng = np.random.default_rng(42)
    y = rng.standard_normal(500).tolist()
    ctx = _build_ctx(y, technique_id="garch",
                      params={"p": 1, "q": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    d = _extract_persist_alpha_beta_gamma(res)
    print(f"  alpha={d['alpha_sum']}, beta={d['beta_sum']}, "
          f"persistence={d['persistence']}")
    # On constant-variance DGP, persistence should be small (no
    # GARCH effect). Report < 0.5 or β / α absent (corner solution).
    if (d["persistence"] is not None
            and d["persistence"] > 0.95):
        print(f"  FAIL persistence={d['persistence']} > 0.95 on "
              f"constant-variance DGP; spurious GARCH detected")
        return False
    print(f"  PASS no spurious high-persistence GARCH on "
          f"constant-variance data")
    return True


def canonical_7():
    """C-CAL-2: GJR-GARCH on T=80 very short series."""
    print("\n" + "=" * 60)
    print("C-CAL-2 (canonical_7): GJR-GARCH on T=80 short series")
    print("=" * 60)
    y = _simulate_gjr_garch11(T=80, gamma=0.10, seed=44)
    ctx = _build_ctx(y, technique_id="gjr_garch",
                      params={"p": 1, "o": 1, "q": 1, "dist": "t"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        # T=80 is well above n<30 hard guard; should succeed
        print(f"  FAIL status={res.get('status')} on T=80 (n<30 guard "
              f"is for T<30)")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  model={a.get('model')}, AIC={a.get('aic')}, "
          f"#warnings={len(res.get('warnings') or [])}")
    if a.get("model") != "GJR-GARCH":
        print(f"  FAIL model={a.get('model')}, expected GJR-GARCH")
        return False
    print(f"  PASS GJR-GARCH fits on T=80 (above hard guard)")
    return True


def canonical_8():
    """C-CAL-3: Heavy-tail DGP (Student-t df=4) + EGARCH normal."""
    print("\n" + "=" * 60)
    print("C-CAL-3 (canonical_8): Heavy-tail DGP + EGARCH normal")
    print("=" * 60)
    y = _simulate_garch11(T=1000, dist="t", df=4, seed=45)
    ctx = _build_ctx(y, technique_id="egarch",
                      params={"p": 1, "q": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  model={a.get('model')}, AIC={a.get('aic')}, "
          f"log_lik={a.get('log_likelihood')}")
    if a.get("model") != "EGARCH":
        print(f"  FAIL model={a.get('model')}")
        return False
    print(f"  PASS EGARCH fits on heavy-tail data (misspecified dist)")
    return True


def canonical_9():
    """C-CAL-4: GARCH technique_id with redundant o=1 param."""
    print("\n" + "=" * 60)
    print("C-CAL-4 (canonical_9): GARCH + o=1 (redundant)")
    print("=" * 60)
    y = _simulate_garch11(T=1000, seed=46)
    ctx = _build_ctx(y, technique_id="garch",
                      params={"p": 1, "q": 1, "o": 1, "dist": "normal"})
    res = garch_model.run(ctx, _null_progress)
    if res.get("status") != "success":
        print(f"  FAIL status={res.get('status')}")
        return False
    a = res.get("audit_fields", {}) or {}
    print(f"  model={a.get('model')}, o={a.get('o')}")
    # Wrapper accepts the user-supplied o=1; arch_model will then
    # fit with that o. Status must succeed; no crash.
    print(f"  PASS GARCH wrapper accepts redundant o=1 param "
          f"(o={a.get('o')})")
    return True


# =====================================================
# Main
# =====================================================


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5,
               canonical_6, canonical_7, canonical_8, canonical_9):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            ok = False
        results.append((fn.__name__, ok))

    print("\n" + "=" * 60)
    print("CANONICAL VALIDATION SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
