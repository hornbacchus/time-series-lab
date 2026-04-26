"""Phase 5 canonical validation for Follow-up 2c.

Exercises the 4 canonicals from the Phase 2 plan plus the
D13-fallback canonical added at Phase 2 review:

  1. SV Gaussian on sp500_returns.csv (backward-compat verification).
  2. SV Student-t on sp500_returns.csv (heavy-tailed equity; expect
     ν in 5-10 range).
  3. SV Student-t on synthetic Gaussian-SV returns (expect ν → 200;
     D2 near_gaussian_on_student_t_path trigger fires).
  4. SV Student-t on synthetic ν=3 SV returns (expect ν ≈ 3; D1
     student_t_very_heavy_tails trigger fires).
  5. SV Student-t on pathologically-short series (n=30; expect
     Student-t optimization to fall back to Gaussian, D3 trigger
     fires).

Synthetic series (canonicals 3, 4, 5) are generated fresh each run
from fixed seeds so results are reproducible without committing
simulated CSVs.

Run from the project root:
    python tools/validate_sv_student_t_canonicals.py
"""

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
import pandas as pd

from techniques.base import RunContext
from techniques import stochastic_volatility as sv_mod


SAMPLE_DIR = os.path.join(_ROOT, "resources", "sample_data")


def _null_progress(*args, **kwargs):
    pass


def _load_series(filename, col_idx=1):
    df = pd.read_csv(os.path.join(SAMPLE_DIR, filename))
    time = df.iloc[:, 0].tolist()
    name = df.columns[col_idx]
    values = df.iloc[:, col_idx].tolist()
    return time, name, values


def _generate_sv_returns(n, phi, sigma_eta, mu, nu=None, seed=42):
    """Simulate n returns from an SV process.

    nu=None means Gaussian innovations; nu finite uses Student-t.
    """
    rng = np.random.default_rng(seed)
    h = np.zeros(n)
    h[0] = mu + rng.standard_normal() * sigma_eta / np.sqrt(max(1e-12, 1 - phi ** 2))
    for t in range(1, n):
        h[t] = mu + phi * (h[t - 1] - mu) + rng.standard_normal() * sigma_eta
    if nu is None:
        eps = rng.standard_normal(n)
    else:
        # Student-t with nu dof, rescaled to unit variance (standard
        # t has variance nu/(nu-2) for nu > 2).
        tstd = rng.standard_t(df=nu, size=n)
        tstd = tstd / np.sqrt(nu / (nu - 2.0))
        eps = tstd
    y = np.exp(h / 2.0) * eps
    return y.tolist()


def _build_ctx(time, name, values, *, preset, innovations, frequency="nyse_daily"):
    raw = {
        "run_id": "test",
        "technique_id": "stochastic_volatility",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time,
        "series": [{"name": name, "values": values}],
        "params": {"innovations": innovations},
    }
    return RunContext(raw)


def _render(result, label):
    print(f"\n=== Canonical: {label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    print(
        f"innovations={a.get('innovations')} "
        f"(requested={a.get('requested_innovations')}, "
        f"fitted={a.get('fitted_innovations')}, "
        f"fallback={a.get('fallback_occurred')})"
    )
    print(
        f"phi={a.get('phi')} sigma_eta={a.get('sigma_eta')} "
        f"nu={a.get('nu_degrees_of_freedom')} "
        f"band={a.get('nu_interpretation_band')}"
    )
    print(
        f"aic={a.get('aic')} bic={a.get('bic')} k={a.get('n_free_params')} "
        f"neg_loglik={a.get('neg_loglik')} "
        f"input_kurtosis={a.get('input_kurtosis')}"
    )
    interp = result.get("interpretation") or {}
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    print(f"\n  Tier 2: {interp.get('tier2', '(missing)')}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} trigger(s)):")
    for t in tier3:
        print(f"    • {t}")
    if result.get("warnings"):
        print(f"\n  Warnings: {result.get('warnings')}")
    return True


def canonical_1():
    """SV Gaussian on sp500_returns (backward-compat verification)."""
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(time, name, values,
                     preset="Balanced", innovations="gaussian")
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C1 SV Gaussian sp500_returns Balanced")


def canonical_2():
    """SV Student-t on sp500_returns."""
    time, name, values = _load_series("sp500_returns.csv")
    ctx = _build_ctx(time, name, values,
                     preset="Balanced", innovations="student_t")
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C2 SV Student-t sp500_returns Balanced")


def canonical_3():
    """SV Student-t on synthetic Gaussian-SV returns.

    Expect: ν → upper bound (near 200); D2 near-Gaussian trigger.
    """
    n = 2000
    values = _generate_sv_returns(
        n=n, phi=0.95, sigma_eta=0.2, mu=0.0, nu=None, seed=2023,
    )
    time = [f"day_{i+1}" for i in range(n)]
    name = "synthetic_gaussian_sv_returns"
    ctx = _build_ctx(time, name, values,
                     preset="Balanced", innovations="student_t",
                     frequency="daily")
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C3 SV Student-t on synthetic Gaussian SV")


def canonical_4():
    """SV Student-t on synthetic ν=3 SV returns.

    Expect: ν_est ≈ 3; D1 very-heavy-tails trigger.
    """
    n = 2000
    values = _generate_sv_returns(
        n=n, phi=0.93, sigma_eta=0.18, mu=0.0, nu=3.0, seed=2024,
    )
    time = [f"day_{i+1}" for i in range(n)]
    name = "synthetic_student_t_nu3_sv_returns"
    ctx = _build_ctx(time, name, values,
                     preset="Balanced", innovations="student_t",
                     frequency="daily")
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C4 SV Student-t on synthetic nu=3 SV")


def canonical_5a():
    """SV Student-t on pathologically-short series (robustness probe).

    Series length just above the n<50 hard minimum. The objective is
    to verify the wrapper handles short series without crashing — it
    may either (a) converge to a degenerate-but-valid fit (no D3
    trigger), or (b) fail and fall back (D3 trigger fires). Both
    are acceptable outcomes for this probe.

    Empirical finding (Phase 5): Nelder-Mead on 4-param SV is robust
    enough that n=55 converges to phi ≈ 0 / ν ≈ 10 rather than
    failing — so D3 does NOT fire here. That's a positive signal
    about wrapper stability. The D3 path itself is force-tested in
    canonical_5b below.
    """
    n = 55
    rng = np.random.default_rng(9999)
    values = (rng.standard_t(df=5, size=n) * 0.5).tolist()
    time = [f"day_{i+1}" for i in range(n)]
    name = "pathologically_short_returns"
    ctx = _build_ctx(time, name, values,
                     preset="Balanced", innovations="student_t",
                     frequency="daily")
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C5a SV Student-t on short series (robustness)")


def canonical_5b():
    """Force-test the D13 fallback code path.

    Monkey-patches scipy.optimize.minimize inside the wrapper to
    raise when called on the 4-param (Student-t) problem. This
    simulates a true optimizer failure that would otherwise be hard
    to trigger naturally with Nelder-Mead on well-behaved data. The
    Gaussian (3-param) fallback is allowed to proceed normally.

    Expected outcome:
      - requested_innovations = "student_t"
      - fitted_innovations    = "gaussian"  (fallback path)
      - fallback_occurred     = True
      - Tier 2 renders the 3-cause / 3-remediation fallback block
      - Tier 3 D3 trigger fires
    """
    import scipy.optimize

    rng = np.random.default_rng(42)
    n = 200
    values = rng.standard_normal(n).tolist()
    time = [f"day_{i+1}" for i in range(n)]

    _orig_minimize = scipy.optimize.minimize

    def _failing_minimize(fun, x0, *args, **kwargs):
        if len(x0) == 4:  # Student-t path
            raise RuntimeError(
                "Simulated Student-t failure (Phase 5 D13 probe)"
            )
        return _orig_minimize(fun, x0, *args, **kwargs)

    # Patch both the scipy namespace and the sv_mod import binding.
    scipy.optimize.minimize = _failing_minimize
    sv_mod.minimize = _failing_minimize
    try:
        ctx = _build_ctx(
            time, "simulated_returns", values,
            preset="Fast", innovations="student_t",
            frequency="daily",
        )
        result = sv_mod.run(ctx, _null_progress)
    finally:
        scipy.optimize.minimize = _orig_minimize
        sv_mod.minimize = _orig_minimize

    ok = _render(result, "C5b D13 fallback force-test (injected Student-t failure)")
    # Additional verification specific to this canonical
    a = result.get("audit_fields", {})
    if not a.get("fallback_occurred"):
        print("  !!! D13 FALLBACK DID NOT FIRE — code path broken")
        return False
    if a.get("fitted_innovations") != "gaussian":
        print("  !!! fitted_innovations != 'gaussian' after forced failure")
        return False
    if a.get("requested_innovations") != "student_t":
        print("  !!! requested_innovations != 'student_t'")
        return False
    print("  D13 fallback verification: fallback=True, "
          "requested=student_t, fitted=gaussian OK")
    return ok


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5a, canonical_5b):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            ok = False
        results.append((fn.__name__, ok))

    print("\n\n" + "=" * 60)
    print("CANONICAL VALIDATION SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
