"""
Transfer Function / Distributed Lag Model for Time Series Lab.

Implements finite distributed lag (FDL) and rational distributed lag
(transfer function) models relating an output series Y to one or more
input series X with lagged effects. Estimation via OLS.
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
    format_significance_disclosure,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"max_lag": 4, "ar_order": 0, "include_contemporaneous": True},
    "Balanced": {"max_lag": 8, "ar_order": 1, "include_contemporaneous": True},
    "Thorough": {"max_lag": 12, "ar_order": 2, "include_contemporaneous": True},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a transfer function / distributed lag model.

    Y(t) = c + sum_{k=0}^{b} w_k * X(t-k) + sum_{j=1}^{r} phi_j * Y(t-j) + e(t)

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag for the distributed lag polynomial (b). Preset-dependent.
    ar_order : int, optional
        AR order for the output noise (r). Preset-dependent.
    include_contemporaneous : bool, optional
        Include X(t) (lag 0). Default True.
    polynomial : str, optional
        'unrestricted' (default) or 'almon' for Almon polynomial lags.
    almon_degree : int, optional
        Degree of Almon polynomial (used only if polynomial='almon'). Default 2.

    Series layout
    -------------
    First series  -> Y (output).
    Second series -> X (input / transfer input).
    Additional series -> additional exogenous inputs.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        # Note: transfer_function genuinely USES series beyond the first two
        # as additional exogenous inputs (see the extra_exog block below),
        # so no "pairs_ignored" disclosure is emitted — the extra series are
        # not silently dropped. We record them in audit_fields below.
        y_name, y_raw = all_series[0]
        x_name, x_raw = all_series[1]

        if len(y_raw) != len(x_raw):
            return make_error_response(
                ctx,
                f"Series lengths differ: '{y_name}'={len(y_raw)}, '{x_name}'={len(x_raw)}.",
                error_fixes=["Ensure both series cover the same time range."],
            )

        # Drop NaN
        y_clean, x_clean = dropna_aligned(y_raw, x_raw)
        n_dropped = len(y_raw) - len(y_clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to missing values.")

        n_orig = len(y_clean)

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        max_lag = int(ctx.get_param("max_lag", cfg["max_lag"]))
        ar_order = int(ctx.get_param("ar_order", cfg["ar_order"]))
        include_contemp = ctx.get_param("include_contemporaneous", cfg["include_contemporaneous"])
        poly_type = ctx.get_param("polynomial", "unrestricted")
        almon_deg = int(ctx.get_param("almon_degree", 2))

        min_start = max(max_lag, ar_order)
        if n_orig <= min_start + 5:
            return make_error_response(
                ctx,
                f"Series too short ({n_orig} obs) for max_lag={max_lag}, ar_order={ar_order}. "
                f"Need at least {min_start + 6}.",
                error_fixes=["Reduce max_lag or ar_order, or provide more data."],
            )

        progress_callback("Building lag matrix", 20)

        np.random.seed(ctx.seed)

        # Build design matrix
        start_idx = min_start
        effective_n = n_orig - start_idx
        y_dep = y_clean[start_idx:]

        lag_start = 0 if include_contemp else 1
        lag_indices = list(range(lag_start, max_lag + 1))

        if poly_type == "almon" and len(lag_indices) > almon_deg + 1:
            # Almon polynomial distributed lag
            Z_almon = _almon_basis(lag_indices, almon_deg)  # (n_lags, almon_deg+1)
            # Lag matrix of X
            X_lags = np.column_stack([
                x_clean[start_idx - k: n_orig - k] for k in lag_indices
            ])  # (effective_n, n_lags)
            X_poly = X_lags @ Z_almon  # (effective_n, almon_deg+1)
            col_names_x = [f"Almon_deg{d}" for d in range(almon_deg + 1)]
            is_almon = True
        else:
            X_poly = np.column_stack([
                x_clean[start_idx - k: n_orig - k] for k in lag_indices
            ])
            col_names_x = [f"{x_name}_lag{k}" for k in lag_indices]
            is_almon = False

        # AR terms on Y
        if ar_order > 0:
            Y_ar = np.column_stack([
                y_clean[start_idx - j: n_orig - j] for j in range(1, ar_order + 1)
            ])
            col_names_ar = [f"{y_name}_AR{j}" for j in range(1, ar_order + 1)]
        else:
            Y_ar = np.empty((effective_n, 0))
            col_names_ar = []

        # Additional exogenous
        extra_exog = []
        extra_names = []
        for sname, svals in all_series[2:]:
            if len(svals) >= n_orig:
                extra_exog.append(svals[start_idx:n_orig])
                extra_names.append(sname)
        if extra_exog:
            X_extra = np.column_stack(extra_exog)
        else:
            X_extra = np.empty((effective_n, 0))

        # Intercept
        ones = np.ones((effective_n, 1))

        X_full = np.hstack([ones, X_poly, Y_ar, X_extra])
        col_names = ["Intercept"] + col_names_x + col_names_ar + extra_names

        progress_callback("Fitting OLS", 50)

        # OLS estimation
        beta, residuals_arr, rank, sv = np.linalg.lstsq(X_full, y_dep, rcond=None)
        y_hat = X_full @ beta
        resid = y_dep - y_hat

        k = len(beta)
        dof = effective_n - k
        if dof <= 0:
            return make_error_response(
                ctx,
                "Model has more parameters than observations. Reduce max_lag or ar_order.",
            )

        sse = float(np.sum(resid ** 2))
        mse = sse / dof
        sigma = np.sqrt(mse)

        # Standard errors
        try:
            XtX_inv = np.linalg.inv(X_full.T @ X_full)
            se = np.sqrt(np.diag(XtX_inv) * mse)
        except np.linalg.LinAlgError:
            XtX_inv = np.linalg.pinv(X_full.T @ X_full)
            se = np.sqrt(np.abs(np.diag(XtX_inv) * mse))
            warnings.append("Design matrix near-singular; pseudo-inverse used for standard errors.")

        t_stats = beta / se
        p_values = 2 * sp_stats.t.sf(np.abs(t_stats), dof)

        # Goodness of fit
        ss_total = float(np.sum((y_dep - np.mean(y_dep)) ** 2))
        r_squared = 1 - sse / ss_total if ss_total > 0 else 0.0
        adj_r_squared = 1 - (1 - r_squared) * (effective_n - 1) / dof if dof > 0 else r_squared
        aic = effective_n * np.log(sse / effective_n) + 2 * k
        bic = effective_n * np.log(sse / effective_n) + k * np.log(effective_n)
        rmse = float(np.sqrt(np.mean(resid ** 2)))

        # Recover distributed lag weights if Almon
        if is_almon:
            lag_weights = Z_almon @ beta[1:1 + almon_deg + 1]
        else:
            lag_weights = beta[1:1 + len(lag_indices)]

        progress_callback("Building output", 75)

        # ---- Coefficients table ----
        coef_rows = []
        for i in range(k):
            sig = "***" if p_values[i] < 0.001 else "**" if p_values[i] < 0.01 else "*" if p_values[i] < 0.05 else ""
            coef_rows.append([
                col_names[i],
                round(float(beta[i]), 6),
                round(float(se[i]), 6),
                round(float(t_stats[i]), 4),
                round(float(p_values[i]), 6),
                sig,
            ])
        coef_table = make_table(
            "Coefficients",
            ["Parameter", "Estimate", "Std Error", "t-Stat", "P-Value", "Sig"],
            coef_rows,
        )

        # ---- Lag weights table ----
        lag_rows = []
        cum_weight = 0.0
        for i, k_lag in enumerate(lag_indices):
            w = float(lag_weights[i])
            cum_weight += w
            lag_rows.append([k_lag, round(w, 6), round(cum_weight, 6)])
        lag_table = make_table(
            "Distributed Lag Weights",
            ["Lag", "Weight", "Cumulative"],
            lag_rows,
        )

        # ---- Model summary ----
        summary_rows = [
            ["Dependent Variable", y_name],
            ["Transfer Input", x_name],
            ["Max Lag", max_lag],
            ["AR Order", ar_order],
            ["Polynomial Type", poly_type],
            ["Observations (effective)", effective_n],
            ["Parameters", k],
            ["R-squared", round(r_squared, 4)],
            ["Adjusted R-squared", round(adj_r_squared, 4)],
            ["RMSE", round(rmse, 4)],
            ["AIC", round(float(aic), 2)],
            ["BIC", round(float(bic), 2)],
            ["Residual Std Error", round(float(sigma), 4)],
            ["Long-Run Multiplier", round(float(cum_weight), 6)],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # ---- Residual diagnostics ----
        progress_callback("Residual diagnostics", 90)
        diag_rows = [
            ["Residual Mean", round(float(np.mean(resid)), 6)],
            ["Residual Std", round(float(np.std(resid, ddof=1)), 6)],
        ]
        jb_p_val = None
        dw_val = None
        lb_p_val = None
        if len(resid) > 10:
            jb, jb_p = sp_stats.jarque_bera(resid)
            jb_p_val = float(jb_p)
            diag_rows.append(["Jarque-Bera Statistic", round(float(jb), 4)])
            diag_rows.append(["Jarque-Bera P-Value", round(float(jb_p), 6)])
            if jb_p < 0.05:
                warnings.append("Residuals may not be normally distributed (Jarque-Bera p < 0.05).")

            # Durbin-Watson
            dw = float(np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2))
            dw_val = dw
            diag_rows.append(["Durbin-Watson", round(dw, 4)])
            if dw < 1.5:
                warnings.append(f"Durbin-Watson={dw:.2f} suggests positive autocorrelation in residuals.")
            elif dw > 2.5:
                warnings.append(f"Durbin-Watson={dw:.2f} suggests negative autocorrelation in residuals.")

            # Ljung-Box at lag 10 (Prompt C5 Decision D9 — transfer-function
            # model-order misspecification is the dominant failure mode;
            # Ljung-Box on residuals is the primary specification check).
            try:
                from statsmodels.stats.diagnostic import acorr_ljungbox
                lb_lag = min(10, max(1, len(resid) // 5))
                lb_result = acorr_ljungbox(resid, lags=[lb_lag], return_df=True)
                lb_p_val = float(lb_result["lb_pvalue"].iloc[0])
                diag_rows.append([f"Ljung-Box P-Value (lag {lb_lag})", round(lb_p_val, 6)])
                if lb_p_val < 0.05:
                    warnings.append(
                        f"Ljung-Box at lag {lb_lag} rejects white-noise (p={lb_p_val:.4f}); "
                        f"model orders (max_lag, ar_order) may be misspecified."
                    )
            except Exception:
                lb_p_val = None
        diag_table = make_table("Residual Diagnostics", ["Metric", "Value"], diag_rows)

        # ---- Plain English ----
        peak_lag = lag_indices[int(np.argmax(np.abs(lag_weights)))]
        plain = (
            f"Transfer function model: '{x_name}' -> '{y_name}' with distributed lag up to {max_lag} periods. "
            f"The strongest effect is at lag {peak_lag} (weight={float(lag_weights[int(np.argmax(np.abs(lag_weights)))]):.4f}). "
            f"Long-run multiplier = {cum_weight:.4f}. "
            f"R-squared = {r_squared:.3f}, RMSE = {rmse:.4f}."
        )
        if ar_order > 0:
            plain += f" AR({ar_order}) noise dynamics included."

        charting = (
            "Dual-panel chart: (1) Line plot of lag weights vs lag index with bars. "
            "(2) Time series overlay of original Y and fitted values, with residuals below. "
            "Optionally show cumulative impulse response."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C5) ──────────────────────────
        peak_lag_weight = float(lag_weights[int(np.argmax(np.abs(lag_weights)))])

        audit = {
            "y_series": y_name,
            "x_series": x_name,
            "max_lag": max_lag,
            "ar_order": ar_order,
            "polynomial": poly_type,
            "pair_used": [y_name, x_name],
            "additional_exog_used": [s[0] for s in all_series[2:]],
            "r_squared": round(r_squared, 4),
            "adj_r_squared": round(adj_r_squared, 4),
            "rmse": round(rmse, 4),
            "aic": round(float(aic), 2),
            "bic": round(float(bic), 2),
            "long_run_multiplier": round(float(cum_weight), 6),
            "peak_lag": peak_lag,
            "peak_lag_weight": round(peak_lag_weight, 6),
            "n_effective": effective_n,
            "n_observations": effective_n,
            "jarque_bera_pvalue": round(jb_p_val, 6) if jb_p_val is not None else None,
            "durbin_watson": round(dw_val, 4) if dw_val is not None else None,
            "ljung_box_lag10_pvalue": round(lb_p_val, 6) if lb_p_val is not None else None,
            **format_significance_disclosure(
                test_name="OLS t-test on distributed-lag coefficients",
                critical_value_formula=(
                    "t-distribution with (n_effective - k) DoF; no "
                    "HAC/Newey-West correction applied"
                ),
                ac_corrected=False,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        interp = build_interpretation("transfer_function", _interp_dict)

        return make_response(
            ctx,
            tables=[coef_table, lag_table, summary_table, diag_table],
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
            f"Transfer function model failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Try reducing max_lag if the series is short.",
                "Check for perfect multicollinearity among lagged variables.",
            ],
        )


def _almon_basis(lag_indices, degree):
    """
    Build the Almon polynomial basis matrix.

    Returns Z of shape (n_lags, degree+1) such that
    w_k = Z[k, :] @ gamma, where gamma is (degree+1,) vector.
    """
    lags = np.array(lag_indices, dtype=np.float64)
    Z = np.column_stack([lags ** d for d in range(degree + 1)])
    return Z
