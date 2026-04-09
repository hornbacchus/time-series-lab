"""
Dynamic Factor Model for Time Series Lab.

Fits a dynamic factor model using statsmodels DynamicFactor.
Extracts common latent factors from multiple observed time series.
"""

import numpy as np
from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor

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
    "Fast": {"max_factors": 1, "factor_order": 1, "error_order": 0, "maxiter": 200},
    "Balanced": {"max_factors": 2, "factor_order": 2, "error_order": 1, "maxiter": 500},
    "Thorough": {"max_factors": 3, "factor_order": 2, "error_order": 2, "maxiter": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a dynamic factor model.

    Parameters (via ctx.params)
    ---------------------------
    k_factors : int, optional
        Number of latent factors. Preset-dependent or auto-selected.
    factor_order : int, optional
        AR order of the factor dynamics. Preset-dependent.
    error_order : int, optional
        AR order of idiosyncratic errors. Preset-dependent.
    horizon : int
        Forecast horizon. Default 10.

    Series layout
    -------------
    All series are observed variables. Need at least 2.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        arrays = [s[1] for s in all_series]
        n_vars = len(names)

        # Align
        min_len = min(len(a) for a in arrays)
        Y = np.column_stack([a[:min_len] for a in arrays])
        T = Y.shape[0]

        # Handle NaN: interpolate each column
        n_interp = 0
        for col in range(n_vars):
            nan_idx = np.where(np.isnan(Y[:, col]))[0]
            valid_idx = np.where(~np.isnan(Y[:, col]))[0]
            if len(nan_idx) > 0:
                if len(valid_idx) < 3:
                    return make_error_response(
                        ctx,
                        f"Series '{names[col]}' has too few non-missing values ({len(valid_idx)}).",
                        error_fixes=["Fill missing values or exclude this series."],
                    )
                Y[nan_idx, col] = np.interp(nan_idx, valid_idx, Y[valid_idx, col])
                n_interp += len(nan_idx)
        if n_interp > 0:
            warnings.append(f"{n_interp} total NaN values interpolated across all series.")

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        k_factors = int(ctx.get_param("k_factors", min(cfg["max_factors"], n_vars - 1)))
        factor_order = int(ctx.get_param("factor_order", cfg["factor_order"]))
        error_order = int(ctx.get_param("error_order", cfg["error_order"]))
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        maxiter = cfg["maxiter"]

        # Ensure k_factors is valid
        k_factors = max(1, min(k_factors, n_vars - 1))

        if T < 2 * (k_factors * factor_order + n_vars * error_order + n_vars * k_factors):
            warnings.append(
                "The number of observations is small relative to model complexity. "
                "Results may be unreliable."
            )

        if T < 15:
            return make_error_response(
                ctx,
                f"Only {T} observations. Dynamic factor model needs at least 15.",
                error_fixes=["Provide a longer time series."],
            )

        progress_callback("Standardizing data", 15)

        # Standardize for numerical stability
        means = np.mean(Y, axis=0)
        stds = np.std(Y, axis=0, ddof=1)
        stds[stds < 1e-10] = 1.0
        Y_std = (Y - means) / stds

        progress_callback(f"Fitting dynamic factor model ({k_factors} factors)", 25)

        model = DynamicFactor(
            Y_std,
            k_factors=k_factors,
            factor_order=factor_order,
            error_order=error_order,
        )

        try:
            fit = model.fit(maxiter=maxiter, disp=False)
        except Exception as e1:
            # Fallback: try simpler model
            warnings.append(f"Initial fit failed ({e1}). Trying simpler specification.")
            try:
                model = DynamicFactor(
                    Y_std,
                    k_factors=max(1, k_factors - 1),
                    factor_order=1,
                    error_order=0,
                )
                fit = model.fit(maxiter=maxiter, disp=False)
                k_factors = max(1, k_factors - 1)
                factor_order = 1
                error_order = 0
            except Exception as e2:
                return make_error_response(
                    ctx,
                    f"Dynamic factor model failed to converge: {e2}",
                    error_fixes=[
                        "Reduce k_factors or factor_order.",
                        "Provide more observations.",
                        "Check for constant or highly collinear series.",
                    ],
                )

        if not fit.mle_retvals.get("converged", True):
            warnings.append("Model did not fully converge. Results may be approximate.")

        progress_callback("Extracting factors and loadings", 55)

        # Extract smoothed factors
        factors = fit.factors.filtered_state.T  # (T, k_factors)
        if factors.shape[0] > T:
            factors = factors[:T]

        # Factor loadings
        # The loading matrix is stored in params; extract from model structure
        loading_matrix = np.zeros((n_vars, k_factors))
        param_names = fit.param_names if hasattr(fit, 'param_names') else []

        for i, pname in enumerate(param_names):
            if 'loading' in pname.lower():
                parts = pname.split('.')
                try:
                    # Parse "loading.fN.yM" style names
                    for pi, p in enumerate(parts):
                        if p.startswith('f') and p[1:].isdigit():
                            f_idx = int(p[1:])
                        if p.startswith('y') and p[1:].isdigit():
                            v_idx = int(p[1:])
                    if f_idx < k_factors and v_idx < n_vars:
                        loading_matrix[v_idx, f_idx] = fit.params.iloc[i] if hasattr(fit.params, 'iloc') else fit.params[i]
                except Exception:
                    pass

        # If we couldn't parse loadings, try alternative extraction
        if np.all(loading_matrix == 0):
            try:
                # Direct extraction from state space representation
                design = fit.model.ssm['design']
                if design.ndim == 3:
                    loading_matrix = design[:n_vars, :k_factors, 0]
                else:
                    loading_matrix = design[:n_vars, :k_factors]
            except Exception:
                warnings.append("Could not extract factor loadings from model structure.")

        progress_callback("Generating forecasts", 70)

        # Forecast
        fc_result = fit.get_forecast(steps=horizon)
        fc_mean_std = fc_result.predicted_mean
        if hasattr(fc_mean_std, 'values'):
            fc_mean_std = fc_mean_std.values
        fc_mean_std = np.asarray(fc_mean_std).reshape(horizon, n_vars)

        ci = fc_result.conf_int(alpha=0.10)
        if hasattr(ci, 'values'):
            ci = ci.values

        # De-standardize
        fc_mean = fc_mean_std * stds + means
        fitted_std = fit.fittedvalues
        if hasattr(fitted_std, 'values'):
            fitted_std = fitted_std.values
        fitted_std = np.asarray(fitted_std).reshape(-1, n_vars)
        if fitted_std.shape[0] < T:
            pad = np.full((T - fitted_std.shape[0], n_vars), np.nan)
            fitted_std = np.vstack([pad, fitted_std])
        fitted_orig = fitted_std * stds + means

        progress_callback("Building output tables", 80)

        tables = []

        # ---- Factor loadings table ----
        loading_rows = []
        for i in range(n_vars):
            row = [names[i]]
            for f in range(k_factors):
                row.append(round(float(loading_matrix[i, f]), 4))
            # Communality
            comm = float(np.sum(loading_matrix[i, :] ** 2))
            row.append(round(comm, 4))
            loading_rows.append(row)
        factor_cols = [f"Factor {f+1}" for f in range(k_factors)]
        loading_table = make_table(
            "Factor Loadings",
            ["Variable"] + factor_cols + ["Communality"],
            loading_rows,
        )
        tables.append(loading_table)

        # ---- Extracted factors table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= T else list(range(1, T + 1))
        factor_rows = []
        step = max(1, T // 100) if ctx.preset == "Fast" else 1
        for t in range(0, T, step):
            row = [time_col[t]]
            for f in range(k_factors):
                row.append(round(float(factors[t, f]) if t < factors.shape[0] else 0.0, 4))
            factor_rows.append(row)
        factor_table = make_table(
            "Extracted Factors",
            ["Time"] + factor_cols,
            factor_rows,
        )
        tables.append(factor_table)

        # ---- Forecast tables per variable ----
        for i in range(n_vars):
            fc_rows = []
            for h in range(horizon):
                lower = float(ci[h, i]) * stds[i] + means[i] if ci.shape[1] > i else float(fc_mean[h, i]) * 0.9
                upper = float(ci[h, n_vars + i]) * stds[i] + means[i] if ci.shape[1] > n_vars + i else float(fc_mean[h, i]) * 1.1
                fc_rows.append([
                    h + 1,
                    round(float(fc_mean[h, i]), 4),
                    round(lower, 4),
                    round(upper, 4),
                ])
            tables.append(make_table(
                f"Forecast: {names[i]}",
                ["Step", "Forecast", "Lower 90%", "Upper 90%"],
                fc_rows,
            ))

        # ---- Model summary ----
        # Variance explained by factors
        total_var = np.sum(np.var(Y_std, axis=0))
        factor_var = 0.0
        for f in range(k_factors):
            if f < factors.shape[1]:
                factor_var += np.var(factors[:, f]) * np.sum(loading_matrix[:, f] ** 2)
        var_explained = factor_var / total_var if total_var > 0 else 0.0

        rmse_vals = []
        for i in range(n_vars):
            valid = ~np.isnan(fitted_orig[:, i])
            if valid.any():
                rmse_vals.append(float(np.sqrt(np.mean((Y[valid, i] - fitted_orig[valid, i]) ** 2))))
            else:
                rmse_vals.append(None)

        summary_rows = [
            ["Variables", ", ".join(names)],
            ["Number of Variables", n_vars],
            ["Number of Factors", k_factors],
            ["Factor AR Order", factor_order],
            ["Error AR Order", error_order],
            ["Observations", T],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["Variance Explained (approx)", f"{var_explained * 100:.1f}%"],
            ["Forecast Horizon", horizon],
        ]
        for i in range(n_vars):
            summary_rows.append([f"RMSE ({names[i]})", round(rmse_vals[i], 4) if rmse_vals[i] else None])
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        plain = (
            f"Dynamic factor model with {k_factors} latent factor(s) extracted from "
            f"{n_vars} variables ({', '.join(names)}), {T} observations. "
            f"Factor AR order = {factor_order}. "
            f"Approximate variance explained by factors: {var_explained * 100:.1f}%. "
            f"AIC = {fit.aic:.1f}, BIC = {fit.bic:.1f}. "
            f"{horizon}-step forecasts produced for all variables."
        )

        charting = (
            "Multi-panel chart: (1) Extracted factor(s) over time as line plot(s). "
            "(2) Factor loading bar chart per variable. "
            "(3) Original vs fitted values per variable with forecast continuation. "
            "Heatmap of factor loadings is also informative."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields={
                "variables": names,
                "n_variables": n_vars,
                "k_factors": k_factors,
                "factor_order": factor_order,
                "error_order": error_order,
                "aic": round(float(fit.aic), 2),
                "bic": round(float(fit.bic), 2),
                "log_likelihood": round(float(fit.llf), 2),
                "variance_explained_pct": round(var_explained * 100, 1),
                "n_observations": T,
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Dynamic factor model failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Reduce k_factors if fewer than 3 series are provided.",
                "Try setting error_order=0 if convergence fails.",
                "Check for constant or highly collinear series.",
            ],
        )
