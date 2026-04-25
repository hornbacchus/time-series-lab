"""
Stochastic Volatility (SV) model for Time Series Lab.

Estimates a basic stochastic volatility model via quasi-maximum likelihood.
The model is:
    y_t = exp(h_t / 2) * eps_t,   eps_t ~ N(0, 1)   [Gaussian path, default]
                    or  eps_t ~ t_nu(0, 1)          [Student-t path]
    h_t = mu + phi * (h_{t-1} - mu) + sigma_eta * eta_t,   eta_t ~ N(0, 1)

Parameters estimated:
  - Gaussian path (3 params): mu, phi, sigma_eta
  - Student-t path (4 params): mu, phi, sigma_eta, nu (degrees of freedom)

Quasi-ML on log(y^2): y_star = log(y^2) = h_t + log(eps_t^2). Under
Gaussian eps, log(eps_t^2) has mean -1.2704 and variance pi^2/2 (log-
chi-squared(1) distribution). Under Student-t_nu eps, eps_t^2 ~ F(1, nu),
so log(eps_t^2) has closed-form mean and variance via digamma/trigamma:

  offset(nu)  = E[log(t_nu^2)]    = psi(1/2) - psi(nu/2) + log(nu)
  obs_var(nu) = Var[log(t_nu^2)]  = psi'(1/2) + psi'(nu/2)

Gaussian (nu -> infinity) limit: (-1.2704, pi^2/2) as expected.

Graceful degradation (Follow-up 2c D13): if Student-t optimization
fails on all restarts, wrapper falls back to Gaussian fit and flags
the event via requested_innovations / fitted_innovations audit fields
(visible to the user through the spec's Tier 2 fallback disclosure
and Tier 3 D3 trigger).

Follow-up 2b — MCMC option. Users can opt into full Bayesian
inference via ``inference_method="mcmc"`` (default remains
``"quasi_ml"`` for backward compatibility). MCMC removes the log-
squared transformation bias by sampling directly on the returns
likelihood; see ``_sv_mcmc.py`` for the backend-agnostic dispatcher
(pymc NUTS preferred, Kim-Shephard-Chib Gibbs fallback).

Three-step graceful-degradation cascade (Follow-up 2b D11):
  1. Fast preset + MCMC → D9 auto-downgrade to quasi-ML (Fast's
     latency budget incompatible with MCMC compute cost).
  2. Balanced/Thorough + MCMC runtime failure (R-hat gross failure,
     import error, exception) → D7 fallback to quasi-ML.
  3. Quasi-ML + Student-t MLE failure → 2c D3 fallback to Gaussian
     (unchanged from 2c).
"""

import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import digamma, polygamma
from scipy.stats import norm

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)


# ---------------------------------------------------------------------
# Student-t support (Follow-up 2c)
# ---------------------------------------------------------------------

# ν reparameterization bounds. See Follow-up 2c Phase 1 audit:
#   nu < 2 -> infinite variance (pathological for return data)
#   nu > 200 -> essentially Gaussian
_NU_LOWER = 2.01
_NU_UPPER = 200.0
_NU_SPAN = _NU_UPPER - _NU_LOWER
_NU_INIT = 10.0  # initial guess (moderate tails, non-degenerate)


def _unconstrained_to_nu(x3):
    """Map the 4th optimization coordinate to nu via sigmoid.

    R -> (_NU_LOWER, _NU_UPPER). At x3 = 0, nu = NU_LOWER + NU_SPAN/2.
    """
    return _NU_LOWER + _NU_SPAN / (1.0 + np.exp(-x3))


def _nu_to_unconstrained(nu):
    """Inverse of _unconstrained_to_nu — used to compute initial x3
    from a target nu (e.g., _NU_INIT)."""
    frac = (nu - _NU_LOWER) / _NU_SPAN
    frac = np.clip(frac, 1e-6, 1.0 - 1e-6)
    return float(np.log(frac / (1.0 - frac)))


def _log_chi2_moments(nu):
    """Closed-form moments of log(t_nu^2) for the observation noise.

    Parameters
    ----------
    nu : float or None
        Degrees of freedom. None or nu >= 200 treated as Gaussian
        (returns the log-chi-squared(1) constants).

    Returns
    -------
    (offset, obs_var) : tuple of float
        offset  = E[log(eps_t^2)]
        obs_var = Var[log(eps_t^2)]

    Gaussian (nu -> inf) limit: (-1.2704, pi^2/2).
    """
    if nu is None or nu >= _NU_UPPER:
        return -1.2704, (np.pi ** 2) / 2.0
    nu = float(nu)
    psi_half = digamma(0.5)                      # ≈ -1.9635
    psi_nu_half = digamma(nu / 2.0)
    offset = float(psi_half - psi_nu_half + np.log(nu))
    trig_half = polygamma(1, 0.5)                # = π²/2
    trig_nu_half = polygamma(1, nu / 2.0)
    obs_var = float(trig_half + trig_nu_half)
    return offset, obs_var


def _nu_band(nu):
    """Adjective-band mapping for ν (Follow-up 2c interpretation).

    Returns None when nu is None (Gaussian path).
    """
    if nu is None:
        return None
    v = float(nu)
    if v < 5.0:
        return "very_heavy_tails"
    if v < 10.0:
        return "heavy_tails"
    if v < 30.0:
        return "moderate_tails"
    return "near_gaussian"

_PRESET_CONFIG = {
    "Fast":     {"n_restarts": 1,  "method": "Nelder-Mead", "maxiter": 500},
    "Balanced": {"n_restarts": 3,  "method": "Nelder-Mead", "maxiter": 2000},
    "Thorough": {"n_restarts": 10, "method": "Nelder-Mead", "maxiter": 5000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Estimate a stochastic volatility model on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    None required. The series should be returns (or mean-zero).
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN
        clean = values[~np.isnan(values)]
        n_dropped = len(values) - len(clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(clean)
        if n < 50:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. The SV model needs at least 50 for reliable estimation.",
                error_fixes=["Provide a longer return series (ideally 200+)."],
            )

        # Demean the series
        y = clean - np.mean(clean)

        # Replace exact zeros to avoid log(0)
        zero_mask = y == 0.0
        n_zeros = int(zero_mask.sum())
        if n_zeros > 0:
            y[zero_mask] = np.finfo(float).eps
            warnings.append(f"{n_zeros} zero values replaced with machine epsilon for log transform.")

        progress_callback("Transforming data", 15)

        # Log-squared transformation: y*_t = log(y_t^2) = h_t + log(eps_t^2)
        # log(eps_t^2) ~ log-chi-squared(1): mean = -1.2704, variance = pi^2/2
        y_star = np.log(y ** 2)

        # The transformed model is a linear Gaussian state-space:
        #   y*_t = h_t + offset(nu) + u_t,
        #   where u_t has mean 0, variance obs_var(nu)
        #   h_t = mu + phi*(h_{t-1} - mu) + sigma_eta * eta_t
        # For Gaussian innovations (nu = inf): offset = -1.2704, obs_var = pi^2/2.
        # For Student-t innovations: closed-form via digamma/trigamma
        # (see _log_chi2_moments).

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        # Resolve innovations parameter (Follow-up 2c)
        requested_innovations = str(
            ctx.get_param("innovations", "gaussian")
        ).strip().lower()
        if requested_innovations not in ("gaussian", "student_t"):
            return make_error_response(
                ctx,
                f"innovations must be 'gaussian' or 'student_t', "
                f"got {requested_innovations!r}.",
                error_fixes=[
                    "Set innovations='gaussian' (default) or "
                    "innovations='student_t'.",
                ],
            )

        # Resolve inference_method parameter (Follow-up 2b)
        requested_inference_method = str(
            ctx.get_param("inference_method", "quasi_ml")
        ).strip().lower()
        if requested_inference_method not in ("quasi_ml", "mcmc"):
            return make_error_response(
                ctx,
                f"inference_method must be 'quasi_ml' or 'mcmc', "
                f"got {requested_inference_method!r}.",
                error_fixes=[
                    "Set inference_method='quasi_ml' (default) or "
                    "inference_method='mcmc' (Balanced/Thorough only).",
                ],
            )

        # Cascade step 1 (D11): Fast + MCMC → D9 auto-downgrade.
        # Decision Q3: graceful auto-downgrade with disclosure.
        fast_preset_mcmc_downgrade = False
        if requested_inference_method == "mcmc" and ctx.preset == "Fast":
            warnings.append(
                "MCMC requested on Fast preset; Fast preset's latency "
                "budget is incompatible with MCMC compute cost "
                "(30-120 s minimum). Auto-downgraded to quasi-ML for "
                "this fit. Switch to Balanced or Thorough preset to "
                "perform MCMC inference."
            )
            fast_preset_mcmc_downgrade = True
            effective_inference_method = "quasi_ml"
        else:
            effective_inference_method = requested_inference_method

        def _attempt_fit(innovations):
            """Run n_restarts optimizations on the chosen innovation
            distribution. Returns (best_result, best_nll, best_x_dim).
            best_result is None on full failure.
            """
            best_result = None
            best_nll = np.inf
            for restart in range(cfg["n_restarts"]):
                pct = 25 + int(40 * restart / cfg["n_restarts"])
                progress_callback(
                    f"Optimization restart {restart + 1}/{cfg['n_restarts']} "
                    f"({innovations})", pct,
                )

                mu0 = np.log(np.var(y)) + np.random.randn() * 0.5
                phi0_raw = np.random.uniform(0.5, 0.99)
                phi0 = np.log(phi0_raw / (1 - phi0_raw))
                sigma_eta0 = np.log(0.1 + np.random.exponential(0.2))

                if innovations == "student_t":
                    # Start near ν = 10 with small noise in the
                    # unconstrained coordinate.
                    nu0_unc = (
                        _nu_to_unconstrained(_NU_INIT)
                        + np.random.randn() * 0.3
                    )
                    x0 = np.array([mu0, phi0, sigma_eta0, nu0_unc])
                else:
                    x0 = np.array([mu0, phi0, sigma_eta0])

                try:
                    res = minimize(
                        _neg_log_likelihood,
                        x0,
                        args=(y_star, innovations),
                        method=cfg["method"],
                        options={"maxiter": cfg["maxiter"],
                                 "xatol": 1e-6, "fatol": 1e-8},
                    )
                    if np.isfinite(res.fun) and res.fun < best_nll:
                        best_nll = res.fun
                        best_result = res
                except Exception:
                    continue
            return best_result, best_nll

        # ── Inference dispatch (Follow-up 2b) ──────────────────────
        # Three-step cascade (D11):
        #   1. Fast + MCMC → D9 auto-downgrade (handled above).
        #   2. MCMC runtime failure → D7 fallback to quasi-ML.
        #   3. Quasi-ML + Student-t MLE failure → 2c D3 fallback.
        mcmc_result = None
        mcmc_backend = None
        mcmc_fallback_occurred = False
        fitted_inference_method = effective_inference_method
        fitted_innovations = requested_innovations
        fallback_occurred = False  # 2c D13 Student-t → Gaussian flag

        if effective_inference_method == "mcmc":
            progress_callback(
                f"Running MCMC inference ({requested_innovations})", 20,
            )
            try:
                from techniques import _sv_mcmc  # lazy import
                requested_backend = ctx.get_param("mcmc_backend", None)
                backend_hint = (
                    str(requested_backend).strip().lower()
                    if requested_backend else None
                )
                mcmc_result = _sv_mcmc.fit(
                    y=y,
                    innovations=requested_innovations,
                    preset=ctx.preset,
                    seed=int(ctx.seed),
                    compute_ppc=bool(ctx.get_param(
                        "compute_ppc", ctx.preset == "Thorough",
                    )),
                    progress_callback=progress_callback,
                    backend_hint=backend_hint,
                )
                mcmc_backend = mcmc_result["backend"]
            except Exception as mcmc_err:
                # Cascade step 2: MCMC runtime failure → D7 fallback
                warnings.append(
                    f"MCMC sampling failed "
                    f"({type(mcmc_err).__name__}: {mcmc_err}); "
                    f"automatically fell back to quasi-ML. See Tier 2 "
                    f"remediation guidance."
                )
                mcmc_fallback_occurred = True
                fitted_inference_method = "quasi_ml"
                mcmc_result = None
                # Fall through to quasi-ML path

        # ── Parameter extraction ────────────────────────────────────
        if mcmc_result is not None:
            # MCMC path — use posterior means as point estimates
            progress_callback("Extracting MCMC posterior means", 80)
            mu_hat = float(mcmc_result["posterior"]["mu"]["mean"])
            phi_hat = float(mcmc_result["posterior"]["phi"]["mean"])
            sigma_eta_hat = float(mcmc_result["posterior"]["sigma_eta"]["mean"])
            if requested_innovations == "student_t":
                nu_hat = float(mcmc_result["posterior"]["nu"]["mean"])
            else:
                nu_hat = None
            # Compute neg-log-lik at the posterior means for downstream
            # AIC/BIC reporting (consistent with 2c's interpretation-
            # field semantics).
            x_at_post = np.array([
                mu_hat,
                math.log(phi_hat / (1.0 - phi_hat)),  # logit(phi) for _neg_log_likelihood
                math.log(sigma_eta_hat),
            ])
            if nu_hat is not None:
                x_at_post = np.append(x_at_post, _nu_to_unconstrained(nu_hat))
            try:
                best_nll = float(_neg_log_likelihood(
                    x_at_post, y_star, requested_innovations,
                ))
            except Exception:
                best_nll = None
        else:
            # Quasi-ML path — 2c behavior preserved including D13
            # Student-t → Gaussian fallback.
            progress_callback(
                f"Estimating SV model ({requested_innovations})", 25,
            )
            best_result, best_nll = _attempt_fit(requested_innovations)

            # 2c D13 Student-t → Gaussian fallback (quasi-ML path only)
            if (requested_innovations == "student_t"
                    and (best_result is None or not np.isfinite(best_nll))):
                warnings.append(
                    f"Student-t optimization did not converge after "
                    f"{cfg['n_restarts']} restarts; automatically fell "
                    f"back to Gaussian fit. See Tier 2 interpretation "
                    f"for remediation guidance."
                )
                progress_callback(
                    "Student-t optimization failed — falling back to Gaussian",
                    60,
                )
                best_result, best_nll = _attempt_fit("gaussian")
                fitted_innovations = "gaussian"
                fallback_occurred = True

            if best_result is None or not np.isfinite(best_nll):
                return make_error_response(
                    ctx,
                    "SV model optimization failed to converge on all restarts.",
                    error_fixes=[
                        "Ensure the series represents returns (not prices).",
                        "Try the 'Thorough' preset for more optimization restarts.",
                        "Check for extreme outliers or structural breaks.",
                    ],
                )

            progress_callback("Extracting parameters", 80)
            mu_hat = best_result.x[0]
            phi_hat = 1.0 / (1.0 + np.exp(-best_result.x[1]))
            sigma_eta_hat = np.exp(best_result.x[2])
            if fitted_innovations == "student_t":
                nu_hat = float(_unconstrained_to_nu(best_result.x[3]))
            else:
                nu_hat = None

        # Precompute offset/obs_var at the converged ν so the
        # extraction KF/KS passes don't re-evaluate digamma per step.
        offset_star, obs_var_star = _log_chi2_moments(nu_hat)

        # Run Kalman filter/smoother to get filtered volatilities
        h_filtered, h_var = _kalman_filter(
            y_star, offset_star, obs_var_star,
            mu_hat, phi_hat, sigma_eta_hat,
        )
        h_smoothed = _kalman_smoother(h_filtered, h_var, mu_hat, phi_hat, sigma_eta_hat)

        # Convert log-volatility to annualized volatility (assuming daily returns)
        vol_filtered = np.exp(h_filtered / 2)
        vol_smoothed = np.exp(h_smoothed / 2)

        # Half-life of volatility shocks
        if phi_hat < 1.0 and phi_hat > 0.0:
            half_life = np.log(2) / (-np.log(phi_hat))
        else:
            half_life = np.inf

        # Unconditional variance of log-volatility
        if abs(phi_hat) < 1.0:
            unc_var_h = sigma_eta_hat ** 2 / (1 - phi_hat ** 2)
        else:
            unc_var_h = np.inf

        progress_callback("Building output", 90)

        # Time series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        # Adjust if we dropped NaN
        if n_dropped > 0:
            time_col = list(range(1, n + 1))

        ts_rows = []
        for i in range(n):
            ts_rows.append([
                time_col[i],
                round(float(y[i]), 6),
                round(float(h_smoothed[i]), 4),
                round(float(vol_smoothed[i]), 6),
                round(float(h_filtered[i]), 4),
                round(float(vol_filtered[i]), 6),
            ])

        ts_table = make_table(
            "Stochastic Volatility Estimates",
            ["Time", "Return", "Log-Vol (smoothed)", "Vol (smoothed)",
             "Log-Vol (filtered)", "Vol (filtered)"],
            ts_rows,
        )

        # Parameter table
        param_rows = [
            ["mu (log-var level)", round(mu_hat, 6)],
            ["phi (persistence)", round(phi_hat, 6)],
            ["sigma_eta (vol of vol)", round(sigma_eta_hat, 6)],
            ["Half-life (periods)", round(half_life, 2) if np.isfinite(half_life) else "Inf"],
            ["Unconditional log-vol std", round(np.sqrt(unc_var_h), 4) if np.isfinite(unc_var_h) else "Inf"],
            ["Neg log-likelihood", round(best_nll, 4)],
            ["Observations", n],
        ]
        param_table = make_table("Model Parameters", ["Parameter", "Value"], param_rows)

        # Summary statistics of volatility
        vol_mean = float(np.mean(vol_smoothed))
        vol_std = float(np.std(vol_smoothed))
        vol_min = float(np.min(vol_smoothed))
        vol_max = float(np.max(vol_smoothed))

        stats_rows = [
            ["Mean volatility", round(vol_mean, 6)],
            ["Std of volatility", round(vol_std, 6)],
            ["Min volatility", round(vol_min, 6)],
            ["Max volatility", round(vol_max, 6)],
            ["Vol range ratio (max/min)", round(vol_max / vol_min, 2) if vol_min > 0 else "Inf"],
        ]
        stats_table = make_table("Volatility Summary", ["Metric", "Value"], stats_rows)

        # Plain English summary
        if phi_hat > 0.95:
            persist_desc = "very high"
        elif phi_hat > 0.8:
            persist_desc = "high"
        elif phi_hat > 0.5:
            persist_desc = "moderate"
        else:
            persist_desc = "low"

        plain_english = (
            f"Stochastic volatility model estimated on '{name}' ({n} observations). "
            f"Volatility persistence (phi) is {phi_hat:.4f} ({persist_desc}), meaning "
            f"volatility shocks have a half-life of approximately {half_life:.1f} periods. "
            f"The vol-of-vol parameter (sigma_eta) is {sigma_eta_hat:.4f}. "
            f"Smoothed volatility ranges from {vol_min:.4f} to {vol_max:.4f} "
            f"(ratio {vol_max / vol_min:.1f}x)."
        )

        charting = (
            "Two-panel chart: top panel shows the return series, bottom panel shows "
            "the smoothed volatility as a line with a shaded confidence band. "
            "Optionally overlay filtered volatility as a dashed line. "
            "A secondary y-axis can show log-volatility."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C6 + Follow-up 2c) ──────────
        # AIC / BIC approximation from quasi-ML neg-log-likelihood:
        # AIC = 2k - 2·LL, BIC = k·log(n) - 2·LL, where
        #   k = 3 on Gaussian path (mu, phi, sigma_eta)
        #   k = 4 on Student-t path (mu, phi, sigma_eta, nu)
        # and LL = -best_nll (wrapper reports neg-log-likelihood).
        _k_params = 4 if fitted_innovations == "student_t" else 3
        try:
            _aic = 2 * _k_params + 2 * float(best_nll)
            _bic = _k_params * np.log(n) + 2 * float(best_nll)
        except Exception:
            _aic = None
            _bic = None

        # Input excess kurtosis for SV Gaussian-only Tier 3 trigger.
        try:
            _arr = np.asarray(values, dtype=float)
            _arr = _arr[np.isfinite(_arr)]
            if len(_arr) >= 4:
                _m = _arr.mean()
                _s = _arr.std(ddof=1)
                if _s > 0:
                    _input_kurtosis = float(np.mean(((_arr - _m) / _s) ** 4))
                else:
                    _input_kurtosis = None
            else:
                _input_kurtosis = None
        except Exception:
            _input_kurtosis = None

        # Unconditional log-vol std: σ_η / √(1 − φ²). Diverges as φ→1;
        # report None near the unit root boundary.
        try:
            if abs(phi_hat) < 0.999:
                _unc_log_vol_std = float(
                    sigma_eta_hat / np.sqrt(max(1e-12, 1.0 - phi_hat * phi_hat))
                )
            else:
                _unc_log_vol_std = None
        except Exception:
            _unc_log_vol_std = None

        # Smoothed-vol dynamic range for Tier 1 color (D1: Tier 1
        # headlines filtered vol for GARCH-comparability; smoothed
        # range is Tier 2 informational).
        try:
            _smoothed_vol_min = float(np.min(vol_smoothed))
            _smoothed_vol_max = float(np.max(vol_smoothed))
            _filtered_vol_min = float(np.min(vol_filtered))
            _filtered_vol_max = float(np.max(vol_filtered))
        except Exception:
            _smoothed_vol_min = None
            _smoothed_vol_max = None
            _filtered_vol_min = None
            _filtered_vol_max = None

        audit = {
            "mu": round(mu_hat, 6),
            "phi": round(phi_hat, 6),
            "sigma_eta": round(sigma_eta_hat, 6),
            "half_life": round(half_life, 2) if np.isfinite(half_life) else None,
            "neg_loglik": round(best_nll, 4),
            "aic": round(_aic, 2) if _aic is not None else None,
            "bic": round(_bic, 2) if _bic is not None else None,
            "n_obs": n,
            "n_restarts": cfg["n_restarts"],
            "method": cfg["method"],
            "input_kurtosis": round(_input_kurtosis, 4) if _input_kurtosis is not None else None,
            "unconditional_log_vol_std": round(_unc_log_vol_std, 4) if _unc_log_vol_std is not None else None,
            "smoothed_vol_min": round(_smoothed_vol_min, 4) if _smoothed_vol_min is not None else None,
            "smoothed_vol_max": round(_smoothed_vol_max, 4) if _smoothed_vol_max is not None else None,
            "filtered_vol_min": round(_filtered_vol_min, 4) if _filtered_vol_min is not None else None,
            "filtered_vol_max": round(_filtered_vol_max, 4) if _filtered_vol_max is not None else None,
            "series_name": name,
            # Follow-up 2c — innovations path disclosure. The
            # requested/fitted split captures D13 fallback events
            # when they differ; the spec's D3 trigger fires when
            # requested=='student_t' but fitted=='gaussian'.
            "innovations": fitted_innovations,
            "requested_innovations": requested_innovations,
            "fitted_innovations": fitted_innovations,
            "fallback_occurred": bool(fallback_occurred),
            "nu_degrees_of_freedom": (
                round(float(nu_hat), 4) if nu_hat is not None else None
            ),
            "nu_interpretation_band": _nu_band(nu_hat),
            "n_free_params": _k_params,
            # Follow-up 2b — inference-method path disclosure. The
            # requested/fitted split captures D7 fallback events
            # when MCMC runtime failure forces quasi-ML fallback;
            # fast_preset_mcmc_downgrade captures D9 auto-downgrade.
            "inference_method": fitted_inference_method,
            "requested_inference_method": requested_inference_method,
            "fitted_inference_method": fitted_inference_method,
            "fast_preset_mcmc_downgrade": bool(fast_preset_mcmc_downgrade),
            "mcmc_fallback_occurred": bool(mcmc_fallback_occurred),
        }

        # Populate MCMC-specific audit fields when MCMC path succeeded.
        # Quasi-ML path (incl. post-fallback) gets None on all of them.
        if mcmc_result is not None:
            audit["mcmc_backend"] = mcmc_backend
            # Follow-up B6 — backend-resolution disclosure fields.
            # backend_requested captures the user's pinned choice
            # ("pymc" / "gibbs") or "auto" when unspecified;
            # backend_applied records what actually ran;
            # backend_fallback_reason explains any cascade event;
            # c_backend_available exposes the probe result.
            audit["mcmc_backend_requested"] = mcmc_result.get(
                "backend_requested"
            )
            audit["mcmc_backend_applied"] = mcmc_result.get(
                "backend_applied"
            )
            audit["mcmc_backend_fallback_reason"] = mcmc_result.get(
                "backend_fallback_reason"
            )
            audit["c_backend_available"] = mcmc_result.get(
                "c_backend_available"
            )
            audit["mcmc_chains"] = mcmc_result["config"]["chains"]
            audit["mcmc_draws_per_chain"] = mcmc_result["config"]["draws"]
            audit["mcmc_tune"] = mcmc_result["config"]["tune"]
            audit["mcmc_total_draws"] = (
                mcmc_result["config"]["chains"]
                * mcmc_result["config"]["draws"]
            )
            audit["mcmc_fit_time_seconds"] = mcmc_result["fit_time_seconds"]
            d = mcmc_result["diagnostics"]
            audit["rhat_max"] = round(float(d["rhat_max"]), 4) if d["rhat_max"] is not None else None
            audit["rhat_max_param"] = d["rhat_max_param"]
            audit["ess_min"] = round(float(d["ess_min"]), 1) if d["ess_min"] is not None else None
            audit["ess_min_param"] = d["ess_min_param"]
            audit["divergences_count"] = int(d["divergences_count"])
            audit["divergences_fraction"] = round(float(d["divergences_fraction"]), 6)
            for pname in ("mu", "phi", "sigma_eta", "nu"):
                summ = mcmc_result["posterior"].get(pname)
                if summ is not None:
                    audit[f"{pname}_posterior_mean"] = round(float(summ["mean"]), 6)
                    audit[f"{pname}_posterior_sd"] = round(float(summ["sd"]), 6)
                    audit[f"{pname}_posterior_hdi_lower"] = round(float(summ["hdi_lower"]), 6)
                    audit[f"{pname}_posterior_hdi_upper"] = round(float(summ["hdi_upper"]), 6)
                else:
                    audit[f"{pname}_posterior_mean"] = None
                    audit[f"{pname}_posterior_sd"] = None
                    audit[f"{pname}_posterior_hdi_lower"] = None
                    audit[f"{pname}_posterior_hdi_upper"] = None
            audit["ppc_coverage_90pct"] = (
                round(float(mcmc_result["ppc_coverage_90pct"]), 4)
                if mcmc_result["ppc_coverage_90pct"] is not None else None
            )
            audit["waic"] = (
                round(float(mcmc_result["waic"]), 2)
                if mcmc_result["waic"] is not None else None
            )
            audit["loo"] = (
                round(float(mcmc_result["loo"]), 2)
                if mcmc_result["loo"] is not None else None
            )
        else:
            # Quasi-ML path: all MCMC fields None (Q7 null-guard)
            for key in (
                "mcmc_backend", "mcmc_chains", "mcmc_draws_per_chain",
                "mcmc_tune", "mcmc_total_draws", "mcmc_fit_time_seconds",
                # Follow-up B6 — backend-resolution disclosure fields
                # default to None on the quasi-ML path (no MCMC fit
                # was attempted, so no probe was run and no cascade
                # decision was made).
                "mcmc_backend_requested", "mcmc_backend_applied",
                "mcmc_backend_fallback_reason", "c_backend_available",
                "rhat_max", "rhat_max_param", "ess_min", "ess_min_param",
                "divergences_count", "divergences_fraction",
                "mu_posterior_mean", "mu_posterior_sd",
                "mu_posterior_hdi_lower", "mu_posterior_hdi_upper",
                "phi_posterior_mean", "phi_posterior_sd",
                "phi_posterior_hdi_lower", "phi_posterior_hdi_upper",
                "sigma_eta_posterior_mean", "sigma_eta_posterior_sd",
                "sigma_eta_posterior_hdi_lower", "sigma_eta_posterior_hdi_upper",
                "nu_posterior_mean", "nu_posterior_sd",
                "nu_posterior_hdi_lower", "nu_posterior_hdi_upper",
                "ppc_coverage_90pct", "waic", "loo",
            ):
                audit[key] = None

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("stochastic_volatility", dict(audit))

        return make_response(
            ctx,
            tables=[param_table, stats_table, ts_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Stochastic volatility estimation failed: {e}",
            error_fixes=[
                "Ensure the series represents returns (not levels/prices).",
                "Check for excessive zeros or constant stretches.",
                "Try the 'Thorough' preset for better convergence.",
            ],
        )


def _neg_log_likelihood(params, y_star, innovations="gaussian"):
    """Quasi-likelihood via Kalman filter on the transformed model.

    Under Gaussian innovations: 3-parameter problem (mu, phi, sigma_eta)
    with pinned observation moments (-1.2704, pi^2/2).

    Under Student-t innovations: 4-parameter problem (mu, phi,
    sigma_eta, nu) with observation offset/variance computed via
    digamma/trigamma closed-forms. As nu -> infinity, the moments
    recover the Gaussian constants (sanity check — see tests).
    """
    mu = params[0]
    phi = 1.0 / (1.0 + np.exp(-params[1]))       # logit -> (0,1)
    sigma_eta = np.exp(params[2])                  # exp -> positive

    if innovations == "student_t":
        nu = _unconstrained_to_nu(params[3])
    else:
        nu = None

    offset, obs_var = _log_chi2_moments(nu)

    n = len(y_star)

    # Initialize Kalman filter
    if abs(phi) < 1.0:
        h_pred = mu
        P_pred = sigma_eta ** 2 / (1 - phi ** 2)
    else:
        h_pred = mu
        P_pred = sigma_eta ** 2 * 10.0

    nll = 0.0
    for t in range(n):
        # Prediction error
        v_t = y_star[t] - (h_pred + offset)
        F_t = P_pred + obs_var

        if F_t <= 0:
            F_t = 1e-10

        # Log-likelihood contribution
        nll += 0.5 * (np.log(F_t) + v_t ** 2 / F_t)

        # Kalman gain
        K_t = P_pred / F_t

        # Update
        h_filt = h_pred + K_t * v_t
        P_filt = P_pred - K_t * P_pred

        # Predict next
        h_pred = mu + phi * (h_filt - mu)
        P_pred = phi ** 2 * P_filt + sigma_eta ** 2

    return nll


def _kalman_filter(y_star, offset, obs_var, mu, phi, sigma_eta):
    """Run Kalman filter, return filtered states and variances.

    obs_var is supplied rather than pinned so the filter works for
    both Gaussian and Student-t paths (the latter having a variable
    obs_var as a function of the converged nu).
    """
    n = len(y_star)

    h_filt = np.zeros(n)
    P_filt = np.zeros(n)

    if abs(phi) < 1.0:
        h_pred = mu
        P_pred = sigma_eta ** 2 / (1 - phi ** 2)
    else:
        h_pred = mu
        P_pred = sigma_eta ** 2 * 10.0

    for t in range(n):
        v_t = y_star[t] - (h_pred + offset)
        F_t = P_pred + obs_var
        if F_t <= 0:
            F_t = 1e-10
        K_t = P_pred / F_t

        h_filt[t] = h_pred + K_t * v_t
        P_filt[t] = P_pred - K_t * P_pred

        if t < n - 1:
            h_pred = mu + phi * (h_filt[t] - mu)
            P_pred = phi ** 2 * P_filt[t] + sigma_eta ** 2

    return h_filt, P_filt


def _kalman_smoother(h_filt, P_filt, mu, phi, sigma_eta):
    """Rauch-Tung-Striebel smoother for the state sequence."""
    n = len(h_filt)
    h_smooth = np.zeros(n)
    h_smooth[-1] = h_filt[-1]

    for t in range(n - 2, -1, -1):
        P_pred_next = phi ** 2 * P_filt[t] + sigma_eta ** 2
        if P_pred_next <= 0:
            P_pred_next = 1e-10
        J_t = phi * P_filt[t] / P_pred_next

        h_pred_next = mu + phi * (h_filt[t] - mu)
        h_smooth[t] = h_filt[t] + J_t * (h_smooth[t + 1] - h_pred_next)

    return h_smooth
