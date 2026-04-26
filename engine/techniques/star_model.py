"""
STAR (Smooth Transition AutoRegressive) Model for Time Series Lab.

Implements LSTAR (logistic) and ESTAR (exponential) smooth transition
AR models. The regime transition is governed by a smooth logistic or
exponential function rather than a hard threshold (as in SETAR).

Estimation via nonlinear least squares (scipy.optimize).
"""

import numpy as np

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None
from scipy.optimize import minimize
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"max_ar": 2, "star_type": "LSTAR", "maxiter": 200},
    "Balanced": {"max_ar": 4, "star_type": "LSTAR", "maxiter": 500},
    "Thorough": {"max_ar": 6, "star_type": "both", "maxiter": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a Smooth Transition AutoRegressive (STAR) model.

    y(t) = phi1'x(t) * (1 - G(s(t))) + phi2'x(t) * G(s(t)) + e(t)

    where G(s) is a transition function:
      LSTAR: G(s) = 1 / (1 + exp(-gamma * (s - c)))
      ESTAR: G(s) = 1 - exp(-gamma * (s - c)^2)

    Parameters (via ctx.params)
    ---------------------------
    ar_order : int, optional
        AR order for each regime. Preset-dependent.
    star_type : str, optional
        'LSTAR', 'ESTAR', or 'both' (fit both, report best). Preset-dependent.
    delay : int, optional
        Delay for transition variable s(t) = y(t-d). Default 1.
    horizon : int
        Forecast horizon. Default 10.

    Series layout
    -------------
    First series -> observed time series.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 10:
            warnings.append(f"{nan_count} NaN values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
        elif nan_count >= n - 10:
            return make_error_response(ctx, "Too few non-missing values to fit STAR model.")
        else:
            filled = values

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        ar_order = int(ctx.get_param("ar_order", min(cfg["max_ar"], max(1, n // 15))))
        star_type = ctx.get_param("star_type", cfg["star_type"]).upper()
        # CAI Phase 2 Session 12 fix (F-MR-STAR-TYPE): explicit
        # allowlist for star_type. Pre-fix the wrapper uppercased
        # any string and threaded it through `types_to_fit`,
        # ultimately fitting whichever transition function the
        # internal `_fit_star` defaulted to (typically LSTAR) and
        # reporting the user's invalid string in audit_fields. Add
        # an explicit check parallel to caviar's specification
        # validation pattern.
        _STAR_TYPES = ("LSTAR", "ESTAR", "BOTH")
        if star_type not in _STAR_TYPES:
            return make_error_response(
                ctx,
                f"Unknown star_type '{star_type}'. Must be one of: "
                f"LSTAR, ESTAR, both.",
                error_fixes=[
                    "Use 'LSTAR' (logistic transition), 'ESTAR' "
                    "(exponential transition), or 'both' (fit both "
                    "and report best by IC).",
                ],
            )
        delay = int(ctx.get_param("delay", 1))
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        maxiter = cfg["maxiter"]

        start_idx = max(ar_order, delay)
        effective_n = n - start_idx

        if effective_n < 20:
            return make_error_response(
                ctx,
                f"Only {effective_n} effective observations. STAR model needs at least 20.",
                error_fixes=["Reduce AR order or provide more data."],
            )

        # Build dependent variable and lag matrix
        y_dep = filled[start_idx:]
        lag_matrix = np.column_stack([
            filled[start_idx - j: n - j] for j in range(1, ar_order + 1)
        ])
        # Transition variable
        s_t = filled[start_idx - delay: n - delay]

        # Standardize transition variable for numerical stability
        s_mean = np.mean(s_t)
        s_std = np.std(s_t, ddof=1)
        if s_std < 1e-10:
            return make_error_response(
                ctx,
                "Transition variable has near-zero variance. STAR model requires variability.",
                error_fixes=["Check for constant series."],
            )

        progress_callback("Fitting STAR model(s)", 15)

        results = {}

        types_to_fit = ["LSTAR", "ESTAR"] if star_type == "BOTH" else [star_type]

        for st_type in types_to_fit:
            progress_callback(f"Fitting {st_type} model", 15 + 30 * (types_to_fit.index(st_type)))

            result = _fit_star(y_dep, lag_matrix, s_t, s_mean, s_std,
                               ar_order, st_type, maxiter, ctx.seed)

            if result is not None:
                results[st_type] = result
            else:
                warnings.append(f"{st_type} fitting failed; skipped.")

        if not results:
            return make_error_response(
                ctx,
                "STAR model fitting failed for all specifications.",
                error_fixes=[
                    "Try a lower AR order.",
                    "Check for constant or near-constant series.",
                    "Try specifying star_type='LSTAR' explicitly.",
                ],
            )

        # Select best by AIC
        best_type = min(results, key=lambda k: results[k]["aic"])
        best = results[best_type]

        progress_callback("Generating forecasts", 70)

        # Forecast via simulation
        n_sims = 500
        fc_paths = np.zeros((n_sims, horizon))
        phi1 = best["phi1"]
        phi2 = best["phi2"]
        gamma = best["gamma"]
        c = best["c"]

        for sim in range(n_sims):
            history = list(filled[-max(ar_order, delay):])
            for h in range(horizon):
                x_t = np.array([history[-(j + 1)] for j in range(ar_order)])
                s_val = history[-delay]

                if best_type == "LSTAR":
                    G = 1.0 / (1.0 + np.exp(-gamma * (s_val - c)))
                else:  # ESTAR
                    G = 1.0 - np.exp(-gamma * (s_val - c) ** 2)

                pred = float(np.dot(phi1, np.concatenate([[1], x_t])) * (1 - G) +
                             np.dot(phi2, np.concatenate([[1], x_t])) * G)
                pred += best["sigma"] * np.random.randn()
                fc_paths[sim, h] = pred
                history.append(pred)

        fc_mean = np.mean(fc_paths, axis=0)
        fc_q05 = np.percentile(fc_paths, 5, axis=0)
        fc_q95 = np.percentile(fc_paths, 95, axis=0)

        progress_callback("Building output tables", 80)

        tables = []

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc_mean[h]), 6),
                round(float(fc_q05[h]), 6),
                round(float(fc_q95[h]), 6),
            ])
        tables.append(make_table("Forecast", ["Step", "Forecast", "Lower 90%", "Upper 90%"], fc_rows))

        # ---- Coefficients table ----
        coef_rows = []
        coef_rows.append(["Regime 1 (G=0)", "Intercept", round(float(phi1[0]), 6)])
        for j in range(ar_order):
            coef_rows.append(["Regime 1 (G=0)", f"AR({j+1})", round(float(phi1[j+1]), 6)])
        coef_rows.append(["Regime 2 (G=1)", "Intercept", round(float(phi2[0]), 6)])
        for j in range(ar_order):
            coef_rows.append(["Regime 2 (G=1)", f"AR({j+1})", round(float(phi2[j+1]), 6)])
        coef_rows.append(["Transition", "Type", best_type])
        coef_rows.append(["Transition", "Gamma (speed)", round(float(gamma), 6)])
        coef_rows.append(["Transition", "c (location)", round(float(c), 6)])
        coef_rows.append(["Transition", "Delay (d)", delay])
        tables.append(make_table("Model Coefficients", ["Regime", "Parameter", "Value"], coef_rows))

        # ---- Transition function values ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else list(range(1, n + 1))
        trans_rows = []
        fitted = best["fitted"]
        residuals = best["residuals"]
        G_vals = best["G_values"]

        for t in range(effective_n):
            trans_rows.append([
                time_col[start_idx + t] if start_idx + t < len(time_col) else start_idx + t + 1,
                round(float(filled[start_idx + t]), 6),
                round(float(fitted[t]), 6),
                round(float(residuals[t]), 6),
                round(float(G_vals[t]), 4),
                round(float(s_t[t]), 6),
            ])
        tables.append(make_table(
            "Fitted Values & Transition",
            ["Time", name, "Fitted", "Residual", "G(s_t)", "s_t"],
            trans_rows,
        ))

        # ---- Model comparison (if both fitted) ----
        if len(results) > 1:
            comp_rows = []
            for st_type, res in results.items():
                comp_rows.append([
                    st_type,
                    round(res["aic"], 2),
                    round(res["bic"], 2),
                    round(res["rmse"], 4),
                    round(res["gamma"], 4),
                    round(res["c"], 4),
                ])
            tables.append(make_table(
                "Model Comparison",
                ["Type", "AIC", "BIC", "RMSE", "Gamma", "c"],
                comp_rows,
            ))

        # ---- Model summary ----
        summary_rows = [
            ["Model", f"{best_type}({ar_order})"],
            ["AR Order", ar_order],
            ["Transition Type", best_type],
            ["Gamma (speed)", round(float(gamma), 6)],
            ["c (location)", round(float(c), 6)],
            ["Delay", delay],
            ["Observations (effective)", effective_n],
            ["RMSE", round(best["rmse"], 4)],
            ["AIC", round(best["aic"], 2)],
            ["BIC", round(best["bic"], 2)],
            ["Sigma", round(best["sigma"], 6)],
            ["Forecast Horizon", horizon],
        ]
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Residual diagnostics ----
        progress_callback("Residual diagnostics", 90)
        diag_rows = []
        valid_resid = residuals[~np.isnan(residuals)]
        if len(valid_resid) > 1:
            diag_rows.append(["Residual Mean", round(float(np.mean(valid_resid)), 6)])
            diag_rows.append(["Residual Std", round(float(np.std(valid_resid, ddof=1)), 6)])
        if len(valid_resid) > 10:
            jb, jb_p = sp_stats.jarque_bera(valid_resid)
            diag_rows.append(["Jarque-Bera", round(float(jb), 4)])
            diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
            if jb_p < 0.05:
                warnings.append("Residuals may not be normally distributed.")
            dw = float(np.sum(np.diff(valid_resid) ** 2) / np.sum(valid_resid ** 2))
            diag_rows.append(["Durbin-Watson", round(dw, 4)])
        tables.append(make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows))

        # Transition speed interpretation
        if gamma < 1:
            speed_desc = "very gradual (nearly linear)"
        elif gamma < 10:
            speed_desc = "moderate"
        elif gamma < 100:
            speed_desc = "fast"
        else:
            speed_desc = "very fast (nearly SETAR-like)"

        # ---- Plain English ----
        plain = (
            f"{best_type}({ar_order}) model fitted to '{name}' ({n} observations). "
            f"Transition speed gamma = {gamma:.4f} ({speed_desc}), "
            f"centered at c = {c:.4f}. "
            f"RMSE = {best['rmse']:.4f}, AIC = {best['aic']:.1f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Three-panel chart: (1) Time series with fitted values, colored by transition "
            "function value G(s_t) using a gradient from regime 1 to regime 2. "
            "(2) Transition function G(s) plotted against the transition variable. "
            "(3) Residuals over time."
        )

        progress_callback("Done", 100)

        audit = {
            "model": f"{best_type}({ar_order})",
            "star_type": best_type,
            "ar_order": ar_order,
            "gamma": round(float(gamma), 6),
            "c": round(float(c), 6),
            "delay": delay,
            "transition_speed": speed_desc,
            "rmse": round(best["rmse"], 4),
            "aic": round(best["aic"], 2),
            "bic": round(best["bic"], 2),
            "n_effective": effective_n,
            "horizon": horizon,
        }

        # Fit a linear AR(ar_order) baseline for Tier 3's AIC-improvement
        # trigger (per Prompt C1 Phase 1 audit Decision — star_model
        # needs ~5 extra LOC for aic_linear_baseline).
        _aic_linear_baseline = None
        try:
            from statsmodels.tsa.ar_model import AutoReg
            _linear_fit = AutoReg(filled, lags=ar_order, old_names=False).fit()
            _aic_linear_baseline = float(_linear_fit.aic)
        except Exception:
            _aic_linear_baseline = None

        interp = build_interpretation("star_model", {
            "series_name": name,
            "transition_type": best_type,
            "ar_order": int(ar_order),
            "delay": int(delay),
            "gamma": float(gamma),
            "c": float(c),
            "G_at_latest": float(G_vals[-1]) if len(G_vals) > 0 else None,
            "phi_lower": [float(p) for p in phi1[1:]] if len(phi1) > 1 else [],
            "phi_upper": [float(p) for p in phi2[1:]] if len(phi2) > 1 else [],
            "aic": float(best["aic"]),
            "aic_linear_baseline": _aic_linear_baseline,
        })
        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
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
            f"STAR model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Try a lower AR order.",
                "Try star_type='LSTAR' if 'ESTAR' fails.",
                "Check for constant or near-constant series.",
            ],
        )


# ---------------------------------------------------------------------------
# Core fitting
# ---------------------------------------------------------------------------

def _fit_star(y, lag_matrix, s_t, s_mean, s_std, ar_order, star_type, maxiter, seed):
    """
    Fit a STAR model via nonlinear least squares.

    Returns dict with fitted parameters or None on failure.
    """
    T = len(y)
    n_params = 2 * (ar_order + 1) + 2  # phi1, phi2, gamma, c

    # Build design: X = [1, y(t-1), ..., y(t-p)]
    X = np.column_stack([np.ones(T), lag_matrix])

    # Initialize with linear AR as starting point
    try:
        beta_init, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    except Exception:
        beta_init = np.zeros(ar_order + 1)

    # Initial parameter vector: [phi1_0, ..., phi1_p, phi2_0, ..., phi2_p, gamma, c]
    phi1_init = beta_init.copy()
    phi2_init = beta_init.copy() * 1.1  # slightly different
    gamma_init = 1.0
    c_init = s_mean

    theta0 = np.concatenate([phi1_init, phi2_init, [gamma_init, c_init]])

    def objective(theta):
        phi1 = theta[:ar_order + 1]
        phi2 = theta[ar_order + 1: 2 * (ar_order + 1)]
        gamma = np.abs(theta[-2]) + 1e-6  # ensure positive
        c = theta[-1]

        if star_type == "LSTAR":
            G = 1.0 / (1.0 + np.exp(-gamma * (s_t - c)))
        else:
            G = 1.0 - np.exp(-gamma * (s_t - c) ** 2)

        y_hat = X @ phi1 * (1 - G) + X @ phi2 * G
        resid = y - y_hat
        return np.sum(resid ** 2)

    # Try multiple starting points
    best_result = None
    best_obj = np.inf
    rng = np.random.RandomState(seed)

    for attempt in range(5):
        try:
            if attempt > 0:
                # Perturb starting values
                theta_start = theta0 + rng.randn(len(theta0)) * 0.1
                theta_start[-2] = np.abs(theta_start[-2]) + 0.1
                theta_start[-1] = s_mean + rng.randn() * s_std * 0.5
            else:
                theta_start = theta0.copy()

            result = minimize(
                objective, theta_start,
                method="L-BFGS-B",
                options={"maxiter": maxiter, "ftol": 1e-10},
            )

            if result.fun < best_obj:
                best_obj = result.fun
                best_result = result
        except Exception:
            continue

    if best_result is None:
        return None

    theta = best_result.x
    phi1 = theta[:ar_order + 1]
    phi2 = theta[ar_order + 1: 2 * (ar_order + 1)]
    gamma = abs(float(theta[-2])) + 1e-6
    c = float(theta[-1])

    # Compute fitted values and residuals
    if star_type == "LSTAR":
        G_vals = 1.0 / (1.0 + np.exp(-gamma * (s_t - c)))
    else:
        G_vals = 1.0 - np.exp(-gamma * (s_t - c) ** 2)

    fitted = X @ phi1 * (1 - G_vals) + X @ phi2 * G_vals
    residuals = y - fitted
    sse = float(np.sum(residuals ** 2))
    sigma = float(np.sqrt(sse / max(T - n_params, 1)))
    rmse = float(np.sqrt(sse / T))

    aic = T * np.log(sse / T) + 2 * n_params
    bic = T * np.log(sse / T) + n_params * np.log(T)

    return {
        "phi1": phi1,
        "phi2": phi2,
        "gamma": gamma,
        "c": c,
        "fitted": fitted,
        "residuals": residuals,
        "G_values": G_vals,
        "sse": sse,
        "sigma": sigma,
        "rmse": rmse,
        "aic": float(aic),
        "bic": float(bic),
    }
