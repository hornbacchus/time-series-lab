"""
Stochastic Volatility (SV) model for Time Series Lab.

Estimates a basic stochastic volatility model via quasi-maximum likelihood.
The model is:
    y_t = exp(h_t / 2) * eps_t,   eps_t ~ N(0, 1)
    h_t = mu + phi * (h_{t-1} - mu) + sigma_eta * eta_t,   eta_t ~ N(0, 1)

Parameters estimated: mu (log-variance level), phi (persistence), sigma_eta (vol of vol).
Uses a quasi-likelihood approach based on log(y_t^2) transformation and Kalman filter.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)

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
        #   y*_t = h_t + offset + u_t,  where u_t has mean 0, variance pi^2/2
        #   h_t = mu + phi*(h_{t-1} - mu) + sigma_eta * eta_t
        # offset = E[log(eps_t^2)] = -1.2704 (psi(0.5) + log(2))
        offset = -1.2704

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback("Estimating SV model via quasi-likelihood", 25)

        best_result = None
        best_nll = np.inf

        for restart in range(cfg["n_restarts"]):
            pct = 25 + int(50 * restart / cfg["n_restarts"])
            progress_callback(f"Optimization restart {restart + 1}/{cfg['n_restarts']}", pct)

            # Random starting values
            mu0 = np.log(np.var(y)) + np.random.randn() * 0.5
            phi0_raw = np.random.uniform(0.5, 0.99)
            phi0 = np.log(phi0_raw / (1 - phi0_raw))  # logit transform
            sigma_eta0 = np.log(0.1 + np.random.exponential(0.2))  # log transform

            x0 = np.array([mu0, phi0, sigma_eta0])

            try:
                res = minimize(
                    _neg_log_likelihood,
                    x0,
                    args=(y_star, offset),
                    method=cfg["method"],
                    options={"maxiter": cfg["maxiter"], "xatol": 1e-6, "fatol": 1e-8},
                )
                if res.fun < best_nll:
                    best_nll = res.fun
                    best_result = res
            except Exception:
                continue

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

        # Extract parameters from unconstrained space
        mu_hat = best_result.x[0]
        phi_hat = 1.0 / (1.0 + np.exp(-best_result.x[1]))  # inverse logit -> (0,1)
        sigma_eta_hat = np.exp(best_result.x[2])  # exp -> positive

        # Run Kalman filter/smoother to get filtered volatilities
        h_filtered, h_var = _kalman_filter(y_star, offset, mu_hat, phi_hat, sigma_eta_hat)
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

        # ── Interpretation layer (Prompt C6) ──────────────────────────
        # AIC approximation from quasi-ML neg-log-likelihood:
        # AIC = 2k - 2·LL, where k=3 free parameters (mu, phi, sigma_eta)
        # and LL = -best_nll (since wrapper reports neg-log-likelihood).
        _k_params = 3
        try:
            _aic = 2 * _k_params + 2 * float(best_nll)
        except Exception:
            _aic = None

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
            "innovation_distribution": "Gaussian",
        }

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


def _neg_log_likelihood(params, y_star, offset):
    """Quasi-likelihood via Kalman filter on the transformed model."""
    mu = params[0]
    phi = 1.0 / (1.0 + np.exp(-params[1]))       # logit -> (0,1)
    sigma_eta = np.exp(params[2])                  # exp -> positive

    n = len(y_star)
    obs_var = (np.pi ** 2) / 2.0  # variance of log(chi2_1)

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


def _kalman_filter(y_star, offset, mu, phi, sigma_eta):
    """Run Kalman filter, return filtered states and variances."""
    n = len(y_star)
    obs_var = (np.pi ** 2) / 2.0

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
