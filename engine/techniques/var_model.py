"""
Vector Autoregression (VAR) model for Time Series Lab.

Fits a VAR(p) model to two or more series, producing impulse responses,
forecast error variance decomposition, and multi-step forecasts.
"""

import numpy as np
import warnings as _warnings
from statsmodels.tsa.api import VAR

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
)


def _prepare_series(values):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([])
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
    return trimmed


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a VAR model to 2+ series.

    Parameters (via ctx.params)
    ---------------------------
    max_lag : int, optional
        Maximum lag for order selection. Default depends on preset.
    ic : str, optional
        Information criterion for lag selection: 'aic', 'bic', 'hqic', 'fpe'. Default 'aic'.
    lag : int, optional
        Fixed lag order. If provided, overrides automatic selection.
    horizon : int, optional
        Forecast steps. Default 10.
    irf_periods : int, optional
        Number of periods for impulse response function. Default 20.
    trend : str, optional
        'c' (constant, default), 'ct' (constant+trend), 'n' (none).
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        warn_list = []

        # Prepare and align all series
        arrays = []
        for name, vals in all_series:
            arrays.append(vals)

        # Check equal lengths
        lengths = [len(a) for a in arrays]
        if len(set(lengths)) > 1:
            min_len = min(lengths)
            warn_list.append(
                f"Series have different lengths {lengths}. Truncating all to {min_len}."
            )
            arrays = [a[:min_len] for a in arrays]

        # Aligned NaN removal
        stacked = np.column_stack(arrays)
        mask = np.all(~np.isnan(stacked), axis=1)
        n_dropped = int(np.sum(~mask))
        if n_dropped > 0:
            # Interpolate instead of dropping to keep alignment
            for col in range(stacked.shape[1]):
                nan_idx = np.where(np.isnan(stacked[:, col]))[0]
                valid_idx = np.where(~np.isnan(stacked[:, col]))[0]
                if len(valid_idx) >= 2 and len(nan_idx) > 0:
                    stacked[nan_idx, col] = np.interp(nan_idx, valid_idx, stacked[valid_idx, col])
            warn_list.append(f"{n_dropped} rows had missing values that were interpolated.")

        # Final NaN check
        final_mask = np.all(~np.isnan(stacked), axis=1)
        stacked = stacked[final_mask]
        n = stacked.shape[0]
        k = stacked.shape[1]

        if n < 3 * k + 5:
            return make_error_response(
                ctx,
                f"Too few observations ({n}) for {k} variables. Need at least {3 * k + 5}.",
                error_fixes=["Provide longer series or fewer variables."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        irf_periods = int(ctx.get_param("irf_periods", 20))
        trend_param = ctx.get_param("trend", "c")

        # Lag selection
        progress_callback("Selecting VAR lag order", 15)

        preset_max = {"Fast": 4, "Balanced": 8, "Thorough": 16}
        max_lag = int(ctx.get_param("max_lag", preset_max.get(ctx.preset, 8)))
        max_lag = min(max_lag, (n // (k + 1)) - 1, n // 3)
        max_lag = max(max_lag, 1)

        ic = ctx.get_param("ic", "aic")

        fixed_lag = ctx.get_param("lag")
        if fixed_lag is not None:
            p = int(fixed_lag)
        else:
            import pandas as pd
            df = pd.DataFrame(stacked, columns=names)
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                var_model = VAR(df, missing="drop")
                try:
                    lag_select = var_model.select_order(maxlags=max_lag, trend=trend_param)
                    p = getattr(lag_select, ic, None)
                    if p is None or p == 0:
                        p = lag_select.aic
                    if p == 0:
                        p = 1
                except Exception:
                    p = min(2, max_lag)
                    warn_list.append(f"Automatic lag selection failed. Using p={p}.")

        progress_callback(f"Fitting VAR({p})", 30)

        import pandas as pd
        df = pd.DataFrame(stacked, columns=names)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            model = VAR(df)
            try:
                fit = model.fit(maxlags=p, trend=trend_param)
            except np.linalg.LinAlgError:
                warn_list.append("Singular matrix. Trying with 'n' trend.")
                fit = model.fit(maxlags=p, trend="n")

        progress_callback("Generating forecasts", 55)

        # Forecasts
        fc = fit.forecast(stacked[-p:], steps=horizon)
        fc_rows = []
        for i in range(horizon):
            row = [n + i + 1]
            for j in range(k):
                row.append(round(float(fc[i, j]), 6))
            fc_rows.append(row)
        fc_table = make_table(
            "VAR Forecast",
            ["Step"] + names,
            fc_rows,
        )

        # Impulse Response Function (orthogonalized via Cholesky).
        # The Cholesky factorization depends on the order of variables
        # in the input, so the choice of ordering is a structural
        # assumption the user is making: variable 1 can contemporaneously
        # affect variables 2..k; variable 2 can contemporaneously affect
        # 3..k but NOT 1; etc. This is the standard recursive identification.
        # We pin the ordering to the user's selection order (names[]) and
        # surface a warning so the user knows the output is ordering-sensitive.
        progress_callback("Computing impulse responses", 65)
        warn_list.append(
            "Impulse responses and FEVD are orthogonalized using a Cholesky "
            f"decomposition with ordering = {list(names)}. This is an identifying "
            "assumption: the first-listed variable can contemporaneously affect "
            "all others, but not vice versa. Re-running with a different series "
            "order will give different IRF and FEVD numbers."
        )
        try:
            irf = fit.irf(irf_periods)
            # Use orthogonalized IRFs (orth_irfs) so they're consistent
            # with the Cholesky-based FEVD reported below. The raw
            # `irfs` attribute contains non-orthogonalized responses,
            # which don't correspond to interpretable "shocks."
            irf_data = getattr(irf, "orth_irfs", None)
            if irf_data is None:
                irf_data = irf.irfs  # fallback for older statsmodels
            irf_rows = []
            for t in range(min(irf_periods + 1, irf_data.shape[0])):
                for shock_idx in range(k):
                    for resp_idx in range(k):
                        irf_rows.append([
                            t,
                            names[shock_idx],
                            names[resp_idx],
                            round(float(irf_data[t, resp_idx, shock_idx]), 6),
                        ])
            irf_table = make_table(
                "Impulse Response Function (Orthogonalized)",
                ["Period", "Shock", "Response", "IRF"],
                irf_rows,
            )
        except Exception as e:
            irf_table = make_table("Impulse Response Function", ["Note"], [["IRF computation failed: " + str(e)]])
            warn_list.append(f"IRF computation failed: {e}")

        # Forecast Error Variance Decomposition
        progress_callback("Variance decomposition", 75)
        try:
            fevd = fit.fevd(irf_periods)
            fevd_rows = []
            for var_idx in range(k):
                decomp = fevd.decomp[var_idx]  # shape: (periods, k)
                for t in range(decomp.shape[0]):
                    row = [names[var_idx], t + 1]
                    for src_idx in range(k):
                        row.append(round(float(decomp[t, src_idx]) * 100, 2))
                    fevd_rows.append(row)
            fevd_table = make_table(
                "Forecast Error Variance Decomposition (%)",
                ["Variable", "Period"] + [f"Due to {n}" for n in names],
                fevd_rows,
            )
        except Exception as e:
            fevd_table = make_table("FEVD", ["Note"], [["FEVD computation failed: " + str(e)]])
            warn_list.append(f"FEVD computation failed: {e}")

        # Model summary table
        progress_callback("Building output", 85)
        aic = float(fit.aic)
        bic = float(fit.bic)
        fpe = float(fit.fpe) if hasattr(fit, 'fpe') else None

        summary_rows = [
            ["VAR Order (p)", p],
            ["Variables", k],
            ["Observations (effective)", fit.nobs],
            ["AIC", round(aic, 4)],
            ["BIC", round(bic, 4)],
        ]
        if fpe is not None:
            summary_rows.append(["FPE", round(fpe, 6)])
        summary_rows.append(["Trend", trend_param])
        summary_rows.append(["Forecast Horizon", horizon])
        summary_rows.append(["IRF Periods", irf_periods])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Coefficient table
        coef_rows = []
        for eq_name in names:
            params = fit.params[eq_name] if eq_name in fit.params.columns else None
            if params is not None:
                for param_name, value in params.items():
                    coef_rows.append([eq_name, str(param_name), round(float(value), 6)])
        coef_table = make_table(
            "Coefficients",
            ["Equation", "Parameter", "Estimate"],
            coef_rows,
        )

        # Granger causality summary (quick check)
        gc_rows = []
        if ctx.preset in ("Balanced", "Thorough"):
            try:
                for caused in names:
                    for causing in names:
                        if caused != causing:
                            test = fit.test_causality(caused, [causing], kind="f", signif=0.05)
                            gc_rows.append([
                                causing, caused,
                                round(float(test.test_statistic), 4),
                                round(float(test.pvalue), 6),
                                "Yes" if test.pvalue < 0.05 else "No",
                            ])
            except Exception:
                pass

        tables = [fc_table, summary_table, coef_table, irf_table, fevd_table]
        if gc_rows:
            gc_table = make_table(
                "Granger Causality (from VAR)",
                ["Causing", "Caused", "F-Statistic", "P-Value", "Significant"],
                gc_rows,
            )
            tables.append(gc_table)

        # Plain English
        plain = (
            f"VAR({p}) model fitted to {k} series: {', '.join(names)} "
            f"({fit.nobs} effective observations). AIC={aic:.2f}. "
            f"{horizon}-step forecasts and {irf_periods}-period impulse responses produced."
        )
        if gc_rows:
            sig_pairs = [(r[0], r[1]) for r in gc_rows if r[4] == "Yes"]
            if sig_pairs:
                plain += " Significant Granger causality: " + "; ".join(
                    f"{a} -> {b}" for a, b in sig_pairs
                ) + "."

        charting = (
            "Multi-panel line chart: one panel per variable showing original, "
            "fitted, and forecast. Separate IRF chart: grid of impulse-response "
            "plots. FEVD stacked area chart."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "var_order": p,
                "n_variables": k,
                "variable_names": names,
                "aic": round(aic, 4),
                "bic": round(bic, 4),
                "ic_used": ic,
                "horizon": horizon,
                "irf_periods": irf_periods,
                "trend": trend_param,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"VAR model failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Provide at least 2 series for VAR.",
                "Reduce max_lag if the series is short.",
                "Check for constant or collinear series.",
            ],
        )
