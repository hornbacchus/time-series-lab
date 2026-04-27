"""Calibration Audit Phase 2 Session 17 — Stationarity Tests batch.

Three wrappers (per status doc inventory):
  - adf_test
  - kpss_test
  - pp_test

Three audit techniques:
  Sweep 0 (PRIORITY) — variant dispatch + input-validation matrix
  Technique 1 — compressed parameter sweeps
  Technique 2 — real-data stress (GSPC + DGS10)
  Technique 3 — adversarial canonicals

Run:
    python tools/calibration_audit/audit_stationarity_tests_batch.py
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
from techniques import adf_test as adf_mod
from techniques import kpss_test as kpss_mod
from techniques import pp_test as pp_mod


_FIXTURE = (
    _ROOT / "tools" / "calibration_audit" / "fixtures"
    / "macro_canonical_series.npz"
)
_NULL_PROGRESS = lambda *a, **k: None


# =====================================================
# Helpers
# =====================================================


def _build_ctx(values, *, technique_id, params=None,
                preset="Balanced", run_id="udf_audit",
                frequency="D", name="y"):
    # Use udf_ prefix for adf_test to avoid triage mode
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


def _ar1(T=300, phi=0.5, sigma=1.0, seed=42):
    """Stationary AR(1) for phi in (-1, 1)."""
    rng = np.random.default_rng(seed)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = phi * y[t - 1] + sigma * rng.standard_normal()
    return y.tolist()


def _random_walk(T=300, sigma=1.0, seed=42):
    rng = np.random.default_rng(seed)
    return np.cumsum(sigma * rng.standard_normal(T)).tolist()


def _trend_stationary(T=300, slope=0.05, sigma=1.0, seed=42):
    rng = np.random.default_rng(seed)
    return (slope * np.arange(T) + sigma * rng.standard_normal(T)).tolist()


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
    print("SWEEP 0 — Input validation matrix (3 wrappers)")
    print("=" * 70)

    y_stationary = _ar1(T=300, phi=0.5)
    y_rw = _random_walk(T=300)

    # ---- adf_test ----
    print("\n[adf_test]")
    res, _, err = _safe_run(adf_mod, _build_ctx(
        y_stationary, technique_id="adf_test", run_id="udf_test"))
    print(f"  baseline (stationary): {res.get('status') if res else err}")
    # Valid regressions
    for reg in ("c", "ct", "ctt", "n"):
        res, _, err = _safe_run(adf_mod, _build_ctx(
            y_stationary, technique_id="adf_test", run_id="udf_test",
            params={"regression": reg}))
        ok = res and res.get("status") == "success"
        print(f"  regression={reg!r}: {'OK' if ok else 'FAIL'}")
    # Invalid regression — does it reject or coerce?
    res, _, err = _safe_run(adf_mod, _build_ctx(
        y_stationary, technique_id="adf_test", run_id="udf_test",
        params={"regression": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("regression")
        print(f"  regression='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.regression = {recorded!r}")
        findings.append({
            "id": "F-ST-ADF-REGRESSION",
            "wrapper": "adf_test",
            "severity": "severe",
            "description": (
                f"adf_test silently accepts invalid `regression` value "
                f"{recorded!r} (statsmodels.adfuller may have its own "
                f"behavior — verify this is genuinely silent)."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  regression='zzz_invalid': REJECTED — {em[:80]}")
    else:
        print(f"  regression='zzz_invalid': RAISED — {err}")
    # Invalid autolag
    res, _, err = _safe_run(adf_mod, _build_ctx(
        y_stationary, technique_id="adf_test", run_id="udf_test",
        params={"autolag": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("autolag")
        print(f"  autolag='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.autolag = {recorded!r}")
        findings.append({
            "id": "F-ST-ADF-AUTOLAG",
            "wrapper": "adf_test",
            "severity": "severe",
            "description": (
                f"adf_test silently accepts invalid `autolag` "
                f"value {recorded!r}."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  autolag='zzz_invalid': REJECTED — {em[:80]}")
    else:
        print(f"  autolag='zzz_invalid': RAISED — {err}")

    # ---- kpss_test ----
    print("\n[kpss_test]")
    res, _, err = _safe_run(kpss_mod, _build_ctx(
        y_stationary, technique_id="kpss_test"))
    print(f"  baseline (stationary): {res.get('status') if res else err}")
    # Valid regressions
    for reg in ("c", "ct"):
        res, _, err = _safe_run(kpss_mod, _build_ctx(
            y_stationary, technique_id="kpss_test",
            params={"regression": reg}))
        ok = res and res.get("status") == "success"
        print(f"  regression={reg!r}: {'OK' if ok else 'FAIL'}")
    # Invalid regression
    res, _, err = _safe_run(kpss_mod, _build_ctx(
        y_stationary, technique_id="kpss_test",
        params={"regression": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("regression")
        print(f"  regression='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.regression = {recorded!r}")
        findings.append({
            "id": "F-ST-KPSS-REGRESSION",
            "wrapper": "kpss_test",
            "severity": "severe",
            "description": (
                f"kpss_test silently accepts invalid `regression` "
                f"{recorded!r}."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  regression='zzz_invalid': REJECTED — {em[:80]}")
    # Invalid nlags string
    res, _, err = _safe_run(kpss_mod, _build_ctx(
        y_stationary, technique_id="kpss_test",
        params={"nlags": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("nlags_rule")
        print(f"  nlags='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.nlags_rule = {recorded!r}")
        findings.append({
            "id": "F-ST-KPSS-NLAGS",
            "wrapper": "kpss_test",
            "severity": "severe",
            "description": (
                f"kpss_test silently accepts invalid `nlags` value "
                f"{recorded!r}."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  nlags='zzz_invalid': REJECTED — {em[:80]}")

    # ---- pp_test ----
    print("\n[pp_test]")
    res, _, err = _safe_run(pp_mod, _build_ctx(
        y_stationary, technique_id="pp_test"))
    print(f"  baseline (stationary): {res.get('status') if res else err}")
    # Valid regressions
    for reg in ("c", "ct", "n", "nc"):
        res, _, err = _safe_run(pp_mod, _build_ctx(
            y_stationary, technique_id="pp_test",
            params={"regression": reg}))
        ok = res and res.get("status") == "success"
        print(f"  regression={reg!r}: {'OK' if ok else 'FAIL'}")
    # Invalid regression — does it reject or coerce?
    res, _, err = _safe_run(pp_mod, _build_ctx(
        y_stationary, technique_id="pp_test",
        params={"regression": "zzz_invalid"}))
    if res and res.get("status") == "success":
        audit = res.get("audit_fields") or {}
        recorded = audit.get("regression")
        print(f"  regression='zzz_invalid': SUCCESS (silent acceptance)")
        print(f"    audit_fields.regression = {recorded!r}")
        findings.append({
            "id": "F-ST-PP-REGRESSION",
            "wrapper": "pp_test",
            "severity": "severe",
            "description": (
                f"pp_test silently accepts invalid `regression` "
                f"{recorded!r}. Backend dispatcher (arch.unitroot) "
                f"silently coerces to 'c' via "
                f"`trend = regression if regression in ('n','c','ct') else 'c'` "
                f"at pp_test.py line 92, AND the manual fallback at "
                f"line 118-119 also silently falls through to 'c'. "
                f"Pattern matches Sessions 9-16 silent-acceptance bugs."
            ),
        })
    elif res and res.get("status") == "failure":
        em = res.get("error_message") or ""
        print(f"  regression='zzz_invalid': REJECTED — {em[:80]}")

    return findings


# =====================================================
# Technique 1 — Compressed parameter sweeps
# =====================================================


def technique_1_param_sweeps():
    print("\n" + "=" * 70)
    print("TECHNIQUE 1 — Compressed parameter sweeps")
    print("=" * 70)
    rows = []

    # Stationary, RW, trend-stationary fixtures
    fixtures = [
        ("AR(1) phi=0.5 (stationary)", _ar1(T=300, phi=0.5, seed=42)),
        ("Random walk (unit root)", _random_walk(T=300, seed=43)),
        ("Trend-stationary", _trend_stationary(T=300, slope=0.05, seed=44)),
    ]

    for fname, y in fixtures:
        print(f"\n--- {fname} ---")
        for label, mod, params in [
            ("ADF (c)", adf_mod, {"regression": "c"}),
            ("ADF (ct)", adf_mod, {"regression": "ct"}),
            ("KPSS (c)", kpss_mod, {"regression": "c"}),
            ("KPSS (ct)", kpss_mod, {"regression": "ct"}),
            ("PP (c)", pp_mod, {"regression": "c"}),
        ]:
            run_id = "udf_test" if label.startswith("ADF") else "test"
            res, dt, err = _safe_run(mod, _build_ctx(
                y, technique_id="adf_test" if label.startswith("ADF")
                else "kpss_test" if label.startswith("KPSS")
                else "pp_test",
                run_id=run_id, params=params))
            if res and res.get("status") == "success":
                # Extract test stat / p-value from result
                # Format depends on wrapper output structure
                af = res.get("audit_fields", {})
                # Look in tables for the test statistic
                tables = res.get("tables", []) or []
                stat = pval = "?"
                for t in tables:
                    rows_t = t.get("rows", []) if isinstance(t, dict) else []
                    if rows_t and len(rows_t[0]) >= 3:
                        try:
                            stat = rows_t[0][1]
                            pval = rows_t[0][2]
                        except (IndexError, TypeError):
                            pass
                        break
                print(f"  {label}: stat={stat}, p={pval}, dt={dt:.2f}s")
            else:
                em = (res.get('error_message') if res else err) or ""
                print(f"  {label}: FAIL — {em[:80]}")

    return rows


# =====================================================
# Technique 2 — Real-data stress
# =====================================================


def technique_2_real_data():
    print("\n" + "=" * 70)
    print("TECHNIQUE 2 — Real-data stress (GSPC log returns + DGS10 levels)")
    print("=" * 70)
    rows = []
    if not _FIXTURE.exists():
        print("  fixture missing; skipping")
        return rows
    data = np.load(_FIXTURE)
    gspc = _log_returns(data["GSPC"])[-500:].tolist()
    dgs10 = data["DGS10"][~np.isnan(data["DGS10"])][-500:].tolist()

    for sname, y in [("GSPC_logret", gspc), ("DGS10_level", dgs10)]:
        print(f"\n--- {sname} ({len(y)} obs) ---")
        for label, mod, run_id in [
            ("adf_test", adf_mod, "udf_test"),
            ("kpss_test", kpss_mod, "test"),
            ("pp_test", pp_mod, "test"),
        ]:
            res, dt, err = _safe_run(mod, _build_ctx(
                y, technique_id=label, run_id=run_id, name=sname))
            if res and res.get("status") == "success":
                # Extract main result
                tables = res.get("tables", []) or []
                stat = pval = "?"
                if tables:
                    rows_t = tables[0].get("rows", [])
                    if rows_t:
                        try:
                            stat = rows_t[0][1]
                            pval = rows_t[0][2]
                        except (IndexError, TypeError):
                            pass
                print(f"  {label}: stat={stat}, p={pval}, dt={dt:.2f}s")
                rows.append({"series": sname, "wrapper": label,
                             "stat": stat, "pvalue": pval, "runtime": dt})
            else:
                em = (res.get('error_message') if res else err) or ""
                print(f"  {label}: FAIL — {em[:80]}")

    return rows


# =====================================================
# Technique 3 — Adversarial canonicals (4)
# =====================================================


def technique_3_adversarial():
    print("\n" + "=" * 70)
    print("TECHNIQUE 3 — Adversarial canonicals (4)")
    print("=" * 70)

    # C-AD-1: clean AR(1) — ADF rejects, KPSS doesn't reject
    print("\n[C-AD-1] AR(1) phi=0.5 stationary (ADF should reject UR)")
    y = _ar1(T=300, phi=0.5, seed=42)
    for label, mod, run_id in [
        ("adf", adf_mod, "udf_test"), ("kpss", kpss_mod, "test"),
        ("pp", pp_mod, "test")]:
        res, _, _ = _safe_run(mod, _build_ctx(y, technique_id=label, run_id=run_id))
        if res and res.get("status") == "success":
            tables = res.get("tables", []) or []
            stat = pval = "?"
            if tables:
                rows_t = tables[0].get("rows", [])
                if rows_t:
                    try: stat, pval = rows_t[0][1], rows_t[0][2]
                    except: pass
            print(f"  {label}: stat={stat}, p={pval}")

    # C-AD-2: random walk — ADF doesn't reject UR, KPSS rejects stationarity
    print("\n[C-AD-2] random walk (ADF should NOT reject UR)")
    y = _random_walk(T=300, seed=43)
    for label, mod, run_id in [
        ("adf", adf_mod, "udf_test"), ("kpss", kpss_mod, "test"),
        ("pp", pp_mod, "test")]:
        res, _, _ = _safe_run(mod, _build_ctx(y, technique_id=label, run_id=run_id))
        if res and res.get("status") == "success":
            tables = res.get("tables", []) or []
            stat = pval = "?"
            if tables:
                rows_t = tables[0].get("rows", [])
                if rows_t:
                    try: stat, pval = rows_t[0][1], rows_t[0][2]
                    except: pass
            print(f"  {label}: stat={stat}, p={pval}")

    # C-AD-3: near-unit-root — edge case
    print("\n[C-AD-3] near-unit-root AR(1) phi=0.99 (edge case; tests have low power)")
    y = _ar1(T=300, phi=0.99, seed=44)
    for label, mod, run_id in [
        ("adf", adf_mod, "udf_test"), ("kpss", kpss_mod, "test"),
        ("pp", pp_mod, "test")]:
        res, _, _ = _safe_run(mod, _build_ctx(y, technique_id=label, run_id=run_id))
        if res and res.get("status") == "success":
            tables = res.get("tables", []) or []
            stat = pval = "?"
            if tables:
                rows_t = tables[0].get("rows", [])
                if rows_t:
                    try: stat, pval = rows_t[0][1], rows_t[0][2]
                    except: pass
            print(f"  {label}: stat={stat}, p={pval}")

    # C-AD-4: short series T=30
    print("\n[C-AD-4] short series T=30 (graceful)")
    y = _ar1(T=30, phi=0.5, seed=45)
    for label, mod, run_id in [
        ("adf", adf_mod, "udf_test"), ("kpss", kpss_mod, "test"),
        ("pp", pp_mod, "test")]:
        res, _, err = _safe_run(mod, _build_ctx(y, technique_id=label, run_id=run_id))
        s = res.get("status") if res else f"RAISED: {err}"
        print(f"  {label}: status={s}")

    return []


# =====================================================
# Main
# =====================================================


def main():
    out = {"session": 17, "started": time.time()}

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

    out_path = _ROOT / "tools" / "calibration_audit" / "stationarity_tests_batch_audit_results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nResults: {out_path}")

    return 0 if len(severe) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
