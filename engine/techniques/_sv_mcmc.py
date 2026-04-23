"""
Backend-agnostic MCMC entry point for stochastic_volatility (Follow-up
2b). Dispatches to pymc NUTS (Tier A) when pymc is importable; falls
back to Kim-Shephard-Chib mixture-of-normals Gibbs (Tier C) when pymc
is unavailable. Returns a uniform result dict regardless of backend so
the wrapper's audit-field population and the spec's Tier 2 rendering
stay backend-agnostic.

See plan file §Phase-2 decisions D9/D10 for the dispatch policy:
  - ImportError on `import pymc` → fall back to Gibbs silently
    (mcmc_backend="gibbs" in audit).
  - Runtime failure during pymc sampling (convergence gross-failure,
    compile error, etc.) → raise to caller, which triggers the
    wrapper-level D7 fallback to quasi-ML.

Tier A (pymc) strengths: NUTS on non-centered h_t handles the
geometrically-awkward SV posterior well; arviz gives WAIC/LOO;
divergent transitions are the first-class diagnostic.

Tier C (Gibbs) strengths: zero new dependencies, SV-specialized KSC
1998 algorithm, runs on any Python install. Weakness: sigma_eta mixes
slowly (lag-1 autocorrelation ~0.98 without non-centered
reparameterization); compensated by a permissive 1.25 R-hat
fallback threshold and D4 Tier 3 warnings when R-hat > 1.01.
"""

from __future__ import annotations

import time
import numpy as np


# ---------------------------------------------------------------------
# MCMC preset configuration (Phase 2 §6)
# ---------------------------------------------------------------------
#
# Fast is not listed — Fast + MCMC triggers the wrapper's D9
# auto-downgrade to quasi-ML before the dispatcher is called.

_MCMC_CONFIG = {
    "Balanced": {
        "chains": 2, "draws": 2000, "tune": 1000,
        "target_accept": 0.95,
    },
    "Thorough": {
        "chains": 4, "draws": 4000, "tune": 2000,
        "target_accept": 0.95,
    },
}


def fit(*, y, innovations, preset, seed, compute_ppc, progress_callback,
         backend_hint=None):
    """Backend-agnostic MCMC fit.

    Parameters
    ----------
    y : np.ndarray
        Demeaned return series (zeros replaced by machine epsilon
        upstream in the wrapper).
    innovations : str
        "gaussian" or "student_t".
    preset : str
        "Balanced" or "Thorough". Fast should never reach this
        entry point — wrapper's D9 auto-downgrade handles it.
    seed : int
        Base random seed for reproducibility.
    compute_ppc : bool
        Compute posterior predictive coverage. Adds ~1.5x runtime;
        Thorough default True, Balanced default False (user opt-in).
    progress_callback : callable
        Signature (label: str, percent: int).
    backend_hint : str | None, optional
        Force a specific backend: "pymc", "gibbs", or None (auto-
        select). Auto-select tries pymc first, falls back to Gibbs
        on ImportError. Users on pytensor-Python-only systems (no
        C++ toolchain) will find pymc extremely slow and may prefer
        backend_hint="gibbs" for predictable performance. The
        wrapper exposes this as the ``mcmc_backend`` user param.

    Returns
    -------
    dict with keys:
      "backend"             : "pymc" | "gibbs"
      "config"              : {"chains", "draws", "tune", ...}
      "fit_time_seconds"    : float
      "posterior"           : {pname: {"mean", "sd", "hdi_lower", "hdi_upper"}}
      "diagnostics"         : {"rhat_max", "rhat_max_param",
                               "ess_min", "ess_min_param",
                               "divergences_count", "divergences_fraction"}
      "ppc_coverage_90pct"  : float | None
      "waic"                : float | None (pymc-only)
      "loo"                 : float | None (pymc-only)
    """
    cfg = _MCMC_CONFIG.get(preset, _MCMC_CONFIG["Balanced"])
    t0 = time.time()

    hint = str(backend_hint or "").strip().lower() or None
    use_gibbs = hint == "gibbs"
    use_pymc_only = hint == "pymc"

    backend = None
    result = None

    if not use_gibbs:
        try:
            import pymc  # noqa: F401
            import arviz  # noqa: F401
            backend = "pymc"
            result = _fit_pymc(
                y=y, innovations=innovations, cfg=cfg, seed=seed,
                compute_ppc=compute_ppc,
                progress_callback=progress_callback,
            )
        except ImportError:
            if use_pymc_only:
                raise  # user forced pymc; propagate failure
            # Tier C fallback on ImportError only
            use_gibbs = True

    if use_gibbs:
        progress_callback(
            "Kim-Shephard-Chib Gibbs sampler "
            "(pure numpy/scipy; no external MCMC dependency)",
            30,
        )
        from techniques import _sv_mcmc_gibbs
        backend = "gibbs"
        result = _sv_mcmc_gibbs.fit(
            y=y, innovations=innovations, cfg=cfg, seed=seed,
            compute_ppc=compute_ppc,
            progress_callback=progress_callback,
        )

    result["backend"] = backend
    result["config"] = dict(cfg)
    result["fit_time_seconds"] = round(time.time() - t0, 2)
    return result


# ---------------------------------------------------------------------
# Tier A — pymc NUTS with non-centered h_t
# ---------------------------------------------------------------------


def _fit_pymc(*, y, innovations, cfg, seed, compute_ppc, progress_callback):
    """pymc NUTS backend for SV.

    Non-centered h_t via pm.AR with stationary initial distribution
    and tight target_accept to reduce divergences on SV's awkward
    geometry. Priors matched to 2c quasi-ML bounds where applicable.
    """
    import pymc as pm
    import arviz as az
    import pytensor.tensor as pt

    n = len(y)
    progress_callback("Building pymc SV model", 35)

    param_names = ["mu", "phi", "sigma_eta"]
    if innovations == "student_t":
        param_names.append("nu")

    with pm.Model() as sv_model:
        # Global priors (Phase 1 §5). phi constrained to (0, 1) to
        # match the quasi-ML convention (typical SV persistence is
        # positive-only anyway; Beta(20, 1.5) prior concentrates
        # mass near 1).
        mu = pm.Normal("mu", mu=0.0, sigma=10.0)
        phi = pm.Beta("phi", alpha=20.0, beta=1.5)
        sigma_eta = pm.HalfNormal("sigma_eta", sigma=2.0)

        # h_t: AR(1) with stationary init. pm.AR with constant=True
        # and rho=[intercept, ar_coeff] follows the state equation
        # h_t = intercept + phi * h_{t-1} + sigma_eta * eta_t, where
        # intercept = mu * (1 - phi) encodes the stationary mean.
        h = pm.AR(
            "h",
            rho=pt.stack([mu * (1.0 - phi), phi]),
            sigma=sigma_eta,
            init_dist=pm.Normal.dist(
                mu=mu,
                sigma=sigma_eta / pt.sqrt(pt.maximum(1e-6, 1.0 - phi * phi)),
            ),
            constant=True,
            shape=n,
        )

        if innovations == "student_t":
            nu = pm.TruncatedNormal(
                "nu", mu=10.0, sigma=10.0,
                lower=2.01, upper=200.0,
            )
            pm.StudentT("y_obs", nu=nu, mu=0.0,
                        sigma=pt.exp(h / 2.0), observed=y)
        else:
            pm.Normal("y_obs", mu=0.0,
                      sigma=pt.exp(h / 2.0), observed=y)

        progress_callback(
            f"pymc NUTS: {cfg['chains']}×{cfg['draws']} (tune={cfg['tune']})",
            40,
        )
        idata = pm.sample(
            draws=cfg["draws"], tune=cfg["tune"], chains=cfg["chains"],
            target_accept=cfg["target_accept"], random_seed=seed,
            return_inferencedata=True,
            idata_kwargs={"log_likelihood": True},
            progressbar=False,
        )

    progress_callback("Extracting posterior summaries", 80)
    summary = az.summary(
        idata, var_names=param_names, hdi_prob=0.95, kind="all",
    )

    # Diagnostics
    rhat_max = float(summary["r_hat"].max())
    rhat_max_param = str(summary["r_hat"].idxmax())
    ess_min = float(summary["ess_bulk"].min())
    ess_min_param = str(summary["ess_bulk"].idxmin())
    div_count = int(idata.sample_stats.diverging.sum().item())
    div_fraction = div_count / max(1, cfg["chains"] * cfg["draws"])
    diag = {
        "rhat_max": rhat_max,
        "rhat_max_param": rhat_max_param,
        "ess_min": ess_min,
        "ess_min_param": ess_min_param,
        "divergences_count": div_count,
        "divergences_fraction": div_fraction,
    }

    # Gross-failure threshold for pymc (tighter than Gibbs because
    # NUTS typically converges well; > 1.10 is a real problem).
    if rhat_max > 1.10:
        raise RuntimeError(
            f"pymc NUTS converged poorly: R-hat max = "
            f"{rhat_max:.3f} > 1.10 (param: {rhat_max_param})"
        )

    # Posterior summaries
    posterior = {}
    for p in param_names:
        row = summary.loc[p]
        # arviz summary columns may be "hdi_2.5%"/"hdi_97.5%" under
        # hdi_prob=0.95; be defensive across arviz versions.
        lo_col = next((c for c in summary.columns if c.startswith("hdi_") and "2.5" in c), "hdi_2.5%")
        hi_col = next((c for c in summary.columns if c.startswith("hdi_") and "97.5" in c), "hdi_97.5%")
        posterior[p] = {
            "mean": float(row["mean"]),
            "sd": float(row["sd"]),
            "hdi_lower": float(row[lo_col]),
            "hdi_upper": float(row[hi_col]),
        }

    # WAIC / LOO (pymc-only; Gibbs backend returns None)
    waic = loo = None
    try:
        waic = float(az.waic(idata).elpd_waic)
    except Exception:
        pass
    try:
        loo = float(az.loo(idata).elpd_loo)
    except Exception:
        pass

    # PPC (opt-in)
    ppc_coverage = None
    if compute_ppc:
        progress_callback("Posterior predictive check (pymc)", 90)
        with sv_model:
            ppc = pm.sample_posterior_predictive(
                idata, random_seed=seed,
                var_names=["y_obs"],
                progressbar=False,
            )
        ppc_arr = ppc.posterior_predictive["y_obs"].values
        ppc_flat = ppc_arr.reshape(-1, n)
        lower = np.percentile(ppc_flat, 5, axis=0)
        upper = np.percentile(ppc_flat, 95, axis=0)
        ppc_coverage = float(np.mean((y >= lower) & (y <= upper)))

    return {
        "posterior": posterior,
        "diagnostics": diag,
        "ppc_coverage_90pct": ppc_coverage,
        "waic": waic,
        "loo": loo,
    }
