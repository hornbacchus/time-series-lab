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
        # Accept both "n_factors" (the catalog parameter name used in the
        # Run-pane UI) and "k_factors" (the older internal name, kept for
        # backward compatibility with any notebooks / scripts that set it).
        n_factors_param = ctx.get_param("n_factors")
        k_factors_param = ctx.get_param("k_factors")
        if n_factors_param is not None:
            k_factors = int(n_factors_param)
        elif k_factors_param is not None:
            k_factors = int(k_factors_param)
        else:
            k_factors = min(cfg["max_factors"], n_vars - 1)
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

        # ── Input transform ─────────────────────────────────────────────
        # DFM is a stationary-input model. Fitting on levels of a trending
        # series (e.g., real GDP, industrial production, payrolls) produces
        # a factor that captures the secular growth trend rather than the
        # business cycle — exactly the opposite of what most users want.
        # Stock & Watson's canonical DFM works on month-over-month log
        # changes for that reason.
        #
        # Supported values for `transform`:
        #   "auto" (default): run an ADF test on each series. If any are
        #     non-stationary (p > 0.05), apply log-diff (or simple diff if
        #     any values are non-positive).
        #   "log_diff": apply month-over-month % log change to all series.
        #   "diff":     apply simple first difference to all series.
        #   "none":     use input as-is (original behavior).
        transform_param = str(ctx.get_param("transform", "auto")).strip().lower()
        applied_transform = "none"

        def _is_nonstationary(col):
            try:
                from statsmodels.tsa.stattools import adfuller
                sample = col[-500:] if len(col) > 500 else col
                p = adfuller(sample, autolag="AIC")[1]
                return p > 0.05
            except Exception:
                return True  # treat as non-stationary if ADF can't run

        if transform_param == "auto":
            nonstationary_count = sum(1 for j in range(n_vars)
                                       if _is_nonstationary(Y[:, j]))
            if nonstationary_count >= 1:
                if np.all(Y > 0):
                    applied_transform = "log_diff"
                else:
                    applied_transform = "diff"
                warnings.append(
                    f"Auto-transform: {nonstationary_count} of {n_vars} input "
                    f"series appear non-stationary (ADF p > 0.05). Applied "
                    f"{applied_transform} so the factor captures cyclical "
                    f"variation rather than the secular trend. Set "
                    f"transform='none' to override."
                )
        elif transform_param == "log_diff":
            if np.all(Y > 0):
                applied_transform = "log_diff"
            else:
                warnings.append(
                    "log_diff requires strictly positive values; "
                    "falling back to simple diff."
                )
                applied_transform = "diff"
        elif transform_param == "diff":
            applied_transform = "diff"
        # else "none": leave Y as-is

        if applied_transform == "log_diff":
            Y = np.diff(np.log(Y), axis=0) * 100.0  # percent MoM
            T -= 1
            if ctx.time and len(ctx.time) > T:
                ctx.time = list(ctx.time)[1:]
            names = [n + " (% MoM)" for n in names]
        elif applied_transform == "diff":
            Y = np.diff(Y, axis=0)
            T -= 1
            if ctx.time and len(ctx.time) > T:
                ctx.time = list(ctx.time)[1:]
            names = [n + " (diff)" for n in names]

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

        # Extract smoothed factors. Modern statsmodels (>= 0.14) exposes
        # these as fit.factors.smoothed / .filtered with shape
        # (k_factors, T); older versions used fit.factors.filtered_state.
        # We prefer `smoothed` over `filtered` because smoothed uses the
        # full sample at each time point (two-pass Kalman) and is the
        # right series for ex-post factor interpretation / plotting.
        if hasattr(fit.factors, "smoothed") and fit.factors.smoothed is not None:
            factors = fit.factors.smoothed.T  # (T, k_factors)
        elif hasattr(fit.factors, "filtered") and fit.factors.filtered is not None:
            factors = fit.factors.filtered.T
        else:
            # Pre-0.14 fallback
            factors = fit.factors.filtered_state.T
        if factors.shape[0] > T:
            factors = factors[:T]

        # Factor loadings.
        #
        # statsmodels DynamicFactor labels parameters as "loading.fN.yM"
        # where N and M are 1-based indices (e.g. "loading.f1.y1" is the
        # loading of the first observed variable on the first factor).
        # We need to convert to 0-based indices for the loading matrix.
        loading_matrix = np.zeros((n_vars, k_factors))
        param_names = fit.param_names if hasattr(fit, 'param_names') else []

        for i, pname in enumerate(param_names):
            if 'loading' not in pname.lower():
                continue
            f_idx_1b = v_idx_1b = None
            for p in pname.split('.'):
                if p.startswith('f') and p[1:].isdigit():
                    f_idx_1b = int(p[1:])
                elif p.startswith('y') and p[1:].isdigit():
                    v_idx_1b = int(p[1:])
            if f_idx_1b is None or v_idx_1b is None:
                continue
            f_idx = f_idx_1b - 1  # convert 1-based -> 0-based
            v_idx = v_idx_1b - 1
            if 0 <= f_idx < k_factors and 0 <= v_idx < n_vars:
                val = fit.params.iloc[i] if hasattr(fit.params, 'iloc') else fit.params[i]
                loading_matrix[v_idx, f_idx] = val

        # Fallback: pull the loading matrix directly from the state-space
        # design matrix. Modern statsmodels returns (n_vars, k_factors)
        # for time-invariant systems; older versions returned a 3-D array
        # with a trailing time axis.
        if np.all(loading_matrix == 0):
            try:
                design = np.asarray(fit.model.ssm['design'])
                if design.ndim == 3:
                    loading_matrix = design[:n_vars, :k_factors, 0]
                else:
                    loading_matrix = design[:n_vars, :k_factors]
            except Exception:
                warnings.append("Could not extract factor loadings from model structure.")

        # ── Rescale & sign-normalize factors and loadings ──────────────
        # statsmodels' DynamicFactor identification leaves the factor
        # scale ambiguous: the pair (factor * c, loading / c) produces an
        # identical fit for any nonzero c. In practice this ships loadings
        # like +/-0.03 with factor scores of magnitude 50 — technically
        # correct but uninterpretable (communality = sum of squared
        # loadings comes out as 0.001).
        #
        # Anchor each factor to unit sample variance. That absorbs the
        # scale into the loadings, so for standardized Y each loading
        # becomes the correlation between a variable and a factor. Then
        # communality = sum_f loading^2 is the fraction of the variable's
        # standardized variance explained by the factors (0 to 1).
        #
        # After rescaling, flip the sign of each factor so its largest-
        # absolute loading is positive. For correlated pro-cyclical
        # inputs this makes the leading factor a "level" factor where
        # scores rise when the underlying economic level rises — the
        # orientation a macro strategist expects to see.
        for f in range(k_factors):
            sigma = float(np.std(factors[:, f], ddof=1))
            if sigma > 1e-10:
                factors[:, f] = factors[:, f] / sigma
                loading_matrix[:, f] = loading_matrix[:, f] * sigma
            abs_argmax = int(np.argmax(np.abs(loading_matrix[:, f])))
            if loading_matrix[abs_argmax, f] < 0:
                factors[:, f] = -factors[:, f]
                loading_matrix[:, f] = -loading_matrix[:, f]

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

        # ---- Communality ----
        # The correct variance-decomposition formula uses the full factor
        # covariance matrix, not just the diagonal:
        #     comm_i = Lambda[i, :] @ Cov(F) @ Lambda[i, :]'
        # We rescaled each factor to unit sample variance above, so
        # Cov(F) has 1s on the diagonal. But the factors are NOT
        # guaranteed to be orthogonal — DFM fitting can converge to
        # local optima where two factors end up nearly collinear,
        # giving loading magnitudes that blow up (the variance is
        # split ambiguously between near-parallel axes). Using the
        # diagonal-only formula (sum of squared loadings) in that
        # regime produces nonsense communalities > 1 and variance-
        # explained > 100%. The quadratic form below handles
        # correlated factors correctly.
        factor_cov = np.cov(factors, rowvar=False)
        if factor_cov.ndim == 0:  # k_factors == 1
            factor_cov = np.array([[float(factor_cov)]])
        elif factor_cov.ndim == 1:
            factor_cov = factor_cov.reshape(1, 1)

        communalities = np.array([
            float(loading_matrix[i, :] @ factor_cov @ loading_matrix[i, :])
            for i in range(n_vars)
        ])

        # Diagnostic: warn when factors are nearly collinear (degenerate
        # fit — the second factor isn't adding independent information).
        if k_factors >= 2:
            # Off-diagonal entries of factor_cov are the factor
            # correlations (diagonal is ~1 after our rescaling).
            max_corr = 0.0
            for a in range(k_factors):
                for b in range(a + 1, k_factors):
                    r = abs(factor_cov[a, b])
                    if r > max_corr:
                        max_corr = r
            if max_corr > 0.90:
                warnings.append(
                    f"Factors are highly correlated (max |corr| = {max_corr:.2f}), "
                    f"suggesting a degenerate fit. Try reducing k_factors — the "
                    f"model is probably over-parameterized for this data."
                )

        # ---- Factor loadings table ----
        loading_rows = []
        for i in range(n_vars):
            row = [names[i]]
            for f in range(k_factors):
                row.append(round(float(loading_matrix[i, f]), 4))
            row.append(round(float(communalities[i]), 4))
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
        # Variance explained by factors = mean communality across
        # variables. communalities[] was computed above using the
        # correct quadratic form Lambda @ Cov(F) @ Lambda.T, which
        # handles the case where the factors aren't perfectly orthogonal
        # (common when DFM converges to a local optimum with correlated
        # factors — reporting sum-of-squared-loadings there gave the
        # nonsensical "1935% variance explained" bug).
        var_explained = float(np.mean(communalities))

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

        # ── Interpretation layer (Prompt C5) ──────────────────────────
        # Expose the loadings matrix + communalities so the dfm spec can
        # render the named-loading-per-factor Tier 1 (Decision D3
        # Option A: spec-side extraction, zero wrapper change beyond
        # field export).
        loadings_per_factor = []
        for f in range(k_factors):
            loadings_per_factor.append([float(loading_matrix[i, f]) for i in range(n_vars)])

        audit = {
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
            "loadings_per_factor": loadings_per_factor,
            "communalities": [float(c) for c in communalities],
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        interp = build_interpretation("dynamic_factor_model", _interp_dict)

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
            f"Dynamic factor model failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Reduce k_factors if fewer than 3 series are provided.",
                "Try setting error_order=0 if convergence fails.",
                "Check for constant or highly collinear series.",
            ],
        )
