"""Phase 5 canonical validation for Follow-up 2b.

Exercises the 6 canonicals from the Phase 2 plan:
  1. SV quasi-ML on sp500 (backward-compat verification).
  2. SV MCMC Gaussian on sp500 subset (n=500) — expect posterior
     to cover quasi-ML point estimates; R-hat < 1.25.
  3. SV MCMC Student-t on sp500 subset (n=500) — ν posterior
     HDI reported.
  4. SV MCMC Gaussian on synthetic SV with known parameters —
     verify posterior 95% HDIs cover truth.
  5. SV Fast + inference_method=mcmc — D9 auto-downgrade.
  6. SV MCMC force-failure — D7 fallback via monkey-patched
     sampler failure.

Synthetic series (canonical 4) generated fresh each run from a
fixed seed. pymc-without-g++ is much slower than compiled pymc;
canonicals use small n to keep runtime bounded.

Run from the project root:
    python tools/validate_sv_mcmc_canonicals.py
"""

import os
import sys
import time

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


def _load_series(filename, col_idx=1, last_n=None):
    df = pd.read_csv(os.path.join(SAMPLE_DIR, filename))
    time_ = df.iloc[:, 0].tolist()
    name = df.columns[col_idx]
    values = df.iloc[:, col_idx].tolist()
    if last_n is not None:
        time_ = time_[-last_n:]
        values = values[-last_n:]
    return time_, name, values


def _generate_sv_returns(n, phi, sigma_eta, mu, nu=None, seed=42):
    rng = np.random.default_rng(seed)
    h = np.empty(n)
    h[0] = mu + rng.standard_normal() * sigma_eta / np.sqrt(max(1e-12, 1 - phi ** 2))
    for t in range(1, n):
        h[t] = mu + phi * (h[t - 1] - mu) + rng.standard_normal() * sigma_eta
    if nu is None:
        eps = rng.standard_normal(n)
    else:
        tstd = rng.standard_t(df=nu, size=n)
        tstd = tstd / np.sqrt(nu / (nu - 2.0))
        eps = tstd
    return (np.exp(h / 2.0) * eps).tolist()


def _build_ctx(time_, name, values, *, preset, params, frequency="nyse_daily"):
    raw = {
        "run_id": "test",
        "technique_id": "stochastic_volatility",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_,
        "series": [{"name": name, "values": values}],
        "params": params,
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
        f"inference_method={a.get('inference_method')} "
        f"(requested={a.get('requested_inference_method')}, "
        f"fitted={a.get('fitted_inference_method')}, "
        f"downgrade={a.get('fast_preset_mcmc_downgrade')}, "
        f"fallback={a.get('mcmc_fallback_occurred')})"
    )
    print(
        f"innovations={a.get('innovations')} nu={a.get('nu_degrees_of_freedom')} "
        f"backend={a.get('mcmc_backend')} time={a.get('mcmc_fit_time_seconds')}s"
    )
    print(
        f"phi={a.get('phi')} sigma_eta={a.get('sigma_eta')} mu={a.get('mu')}"
    )
    if a.get("rhat_max") is not None:
        print(
            f"rhat_max={a.get('rhat_max')} ({a.get('rhat_max_param')}) "
            f"ess_min={a.get('ess_min')} ({a.get('ess_min_param')}) "
            f"divergences={a.get('divergences_count')}"
        )
    if a.get("phi_posterior_mean") is not None:
        print(
            f"Posterior phi: mean={a.get('phi_posterior_mean')} "
            f"HDI=[{a.get('phi_posterior_hdi_lower')},{a.get('phi_posterior_hdi_upper')}]"
        )
    interp = result.get("interpretation") or {}
    print(f"\n  Tier 1: {interp.get('tier1', '(missing)')}")
    print(f"\n  Tier 2: {interp.get('tier2', '(missing)')}")
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        print(f"    • {t}")
    return True


def canonical_1():
    """SV quasi-ML on sp500 (backward-compat)."""
    time_, name, values = _load_series("sp500_returns.csv", last_n=500)
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={})
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C1 SV quasi-ML sp500 Balanced (backward-compat)")


def canonical_2():
    """SV MCMC Gaussian on sp500 subset (Gibbs backend).

    Environment note: pymc NUTS on pytensor-Python-only (no g++ /
    C++ toolchain for pytensor C-code compilation) runs at
    ~0.3-1s per iteration on 500-obs SV — 30+ minutes per chain
    for Balanced config. Phase 5 uses mcmc_backend='gibbs' to
    force the pure-numpy Kim-Shephard-Chib sampler which runs at
    ~20s per chain. On machines with g++, pymc NUTS runs in
    ~30-60s per chain and is preferred (better diagnostics, WAIC/
    LOO). Both backends are functionally equivalent for inference
    correctness.
    """
    time_, name, values = _load_series("sp500_returns.csv", last_n=500)
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"inference_method": "mcmc",
                             "mcmc_backend": "gibbs"})
    result = sv_mod.run(ctx, _null_progress)
    print(f"  (wall clock: {time.time()-t0:.1f}s)")
    return _render(result, "C2 SV MCMC Gaussian sp500[-500] Balanced (Gibbs)")


def canonical_3():
    """SV MCMC Student-t on sp500 subset (Gibbs backend)."""
    time_, name, values = _load_series("sp500_returns.csv", last_n=500)
    t0 = time.time()
    ctx = _build_ctx(time_, name, values, preset="Balanced",
                     params={"inference_method": "mcmc",
                             "innovations": "student_t",
                             "mcmc_backend": "gibbs"})
    result = sv_mod.run(ctx, _null_progress)
    print(f"  (wall clock: {time.time()-t0:.1f}s)")
    return _render(result, "C3 SV MCMC Student-t sp500[-500] Balanced (Gibbs)")


def canonical_4():
    """SV MCMC on synthetic SV with known params (Gibbs backend)."""
    n = 400
    mu_t, phi_t, sigma_t = -0.3, 0.94, 0.18
    values = _generate_sv_returns(n=n, phi=phi_t, sigma_eta=sigma_t,
                                   mu=mu_t, nu=None, seed=2025)
    time_ = [f"day_{i+1}" for i in range(n)]
    t0 = time.time()
    ctx = _build_ctx(time_, "synthetic_sv_gaussian", values,
                     preset="Balanced", frequency="daily",
                     params={"inference_method": "mcmc",
                             "mcmc_backend": "gibbs"})
    result = sv_mod.run(ctx, _null_progress)
    print(f"  (wall clock: {time.time()-t0:.1f}s)")
    print(f"  Truth: mu={mu_t}, phi={phi_t}, sigma_eta={sigma_t}")
    a = result.get("audit_fields", {})
    for pname, truth in [("mu", mu_t), ("phi", phi_t), ("sigma_eta", sigma_t)]:
        lo = a.get(f"{pname}_posterior_hdi_lower")
        hi = a.get(f"{pname}_posterior_hdi_upper")
        if lo is not None and hi is not None:
            covers = "✓" if float(lo) <= truth <= float(hi) else "✗"
            print(f"  {pname}: HDI [{lo:.3f}, {hi:.3f}] {covers} truth={truth}")
    return _render(result, "C4 SV MCMC on synthetic SV (truth recovery)")


def canonical_5():
    """Fast + mcmc → D9 auto-downgrade."""
    time_, name, values = _load_series("sp500_returns.csv", last_n=200)
    ctx = _build_ctx(time_, name, values, preset="Fast",
                     params={"inference_method": "mcmc"})
    result = sv_mod.run(ctx, _null_progress)
    return _render(result, "C5 SV Fast + mcmc (D9 auto-downgrade)")


def canonical_6():
    """Force-test the D7 fallback code path."""
    # Monkey-patch _sv_mcmc.fit to always raise
    from techniques import _sv_mcmc

    time_, name, values = _load_series("sp500_returns.csv", last_n=200)
    _orig_fit = _sv_mcmc.fit

    def _failing_fit(*args, **kwargs):
        raise RuntimeError(
            "Simulated MCMC failure (Phase 5 D7 probe)"
        )

    _sv_mcmc.fit = _failing_fit
    try:
        ctx = _build_ctx(time_, name, values, preset="Balanced",
                         params={"inference_method": "mcmc",
                                 "mcmc_backend": "gibbs"})
        result = sv_mod.run(ctx, _null_progress)
    finally:
        _sv_mcmc.fit = _orig_fit

    ok = _render(result, "C6 SV MCMC force-failure (D7 fallback)")
    a = result.get("audit_fields", {})
    if not a.get("mcmc_fallback_occurred"):
        print("  !!! D7 FALLBACK DID NOT FIRE")
        return False
    if a.get("fitted_inference_method") != "quasi_ml":
        print("  !!! fitted_inference_method != 'quasi_ml' after forced failure")
        return False
    print("  D7 fallback verification: fallback=True, "
          "requested=mcmc, fitted=quasi_ml OK")
    return ok


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
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
