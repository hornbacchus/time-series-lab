"""
Vector Error Correction Model (VECM) for Time Series Lab.

Fits a VECM to 2+ cointegrated time series using statsmodels VECM.
VECM is appropriate when series are individually non-stationary (I(1))
but share cointegrating relationships.
"""

import numpy as np
import warnings as _warnings
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import VECM as SM_VECM, select_order, select_coint_rank

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a VECM to 2+ series.

    Parameters (via ctx.params)
    ---------------------------
    lag : int, optional
        Number of lagged differences. If omitted, selected by IC.
    max_lag : int, optional
        Max lag for order selection. Default depends on preset.
    coint_rank : int, optional
        Number of cointegrating relations. If omitted, estimated from data.
    deterministic : str, optional
        'ci' (restricted constant, default), 'co' (constant outside),
        'li' (restricted linear trend), 'lo' (linear trend outside), 'n' (none).
    horizon : int, optional
        Forecast steps. Default 10.
    significance_level : float, optional
        For cointegration rank test. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        k = len(names)
        warn_list = []

        # Build aligned data matrix
        arrays = [vals for _, vals in all_series]
        lengths = [len(a) for a in arrays]
        if len(set(lengths)) > 1:
            min_len = min(lengths)
            arrays = [a[:min_len] for a in arrays]
            warn_list.append(f"Series truncated to shortest length ({min_len}).")

        stacked = np.column_stack(arrays)

        # Interpolate NaN
        for col in range(stacked.shape[1]):
            nan_idx = np.where(np.isnan(stacked[:, col]))[0]
            valid_idx = np.where(~np.isnan(stacked[:, col]))[0]
            if len(nan_idx) > 0 and len(valid_idx) >= 2:
                stacked[nan_idx, col] = np.interp(nan_idx, valid_idx, stacked[valid_idx, col])
                warn_list.append(f"'{names[col]}': {len(nan_idx)} NaN values interpolated.")

        # Drop any remaining NaN rows
        mask = np.all(~np.isnan(stacked), axis=1)
        stacked = stacked[mask]
        n = stacked.shape[0]

        if n < 4 * k + 10:
            return make_error_response(
                ctx,
                f"Too few observations ({n}) for VECM with {k} variables.",
                error_fixes=["Provide longer series."],
            )

        df = pd.DataFrame(stacked, columns=names)

        horizon = int(ctx.get_param("horizon", 10))
        deterministic = ctx.get_param("deterministic", "ci")
        significance = ctx.get_param("significance_level", 0.05)

        # Lag order selection
        progress_callback("Selecting lag order", 15)
        preset_max = {"Fast": 4, "Balanced": 8, "Thorough": 12}
        max_lag = int(ctx.get_param("max_lag", preset_max.get(ctx.preset, 8)))
        max_lag = min(max_lag, n // (2 * k) - 1, n // 4)
        max_lag = max(max_lag, 1)

        fixed_lag = ctx.get_param("lag")
        if fixed_lag is not None:
            p = int(fixed_lag)
        else:
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                try:
                    order_result = select_order(df, maxlags=max_lag, deterministic=deterministic)
                    p = order_result.aic
                    if p == 0:
                        p = max(1, order_result.bic)
                    if p == 0:
                        p = 1
                except Exception:
                    p = min(2, max_lag)
                    warn_list.append(f"Automatic lag selection failed. Using p={p}.")

        # Cointegration rank
        progress_callback("Estimating cointegration rank", 25)
        coint_rank_param = ctx.get_param("coint_rank")
        if coint_rank_param is not None:
            r = int(coint_rank_param)
        else:
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                try:
                    rank_result = select_coint_rank(stacked, det_order=0 if deterministic in ("ci", "n") else 1, k_ar_diff=p, signif=significance)
                    r = rank_result.rank
                    if r == 0:
                        warn_list.append(
                            "No cointegrating relations detected at the given significance level. "
                            "Using rank=1 anyway; consider a VAR model in differences instead."
                        )
                        r = 1
                    if r >= k:
                        warn_list.append(
                            f"Cointegration rank ({r}) equals the number of variables ({k}). "
                            "All series may be stationary; a VAR in levels might be more appropriate."
                        )
                        r = k - 1
                except Exception as e:
                    r = min(1, k - 1)
                    warn_list.append(f"Cointegration rank selection failed ({e}). Using r={r}.")

        progress_callback(f"Fitting VECM(p={p}, r={r})", 40)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                vecm = SM_VECM(df, k_ar_diff=p, coint_rank=r, deterministic=deterministic)
                fit = vecm.fit()
            except np.linalg.LinAlgError:
                warn_list.append("Singular matrix. Trying with deterministic='n'.")
                vecm = SM_VECM(df, k_ar_diff=p, coint_rank=r, deterministic="n")
                fit = vecm.fit()
                deterministic = "n"

        progress_callback("Generating forecasts", 60)

        # Forecasts
        fc = fit.predict(steps=horizon)
        fc_arr = fc.values if hasattr(fc, 'values') else np.asarray(fc)
        fc_rows = []
        for i in range(horizon):
            row = [n + i + 1]
            for j in range(k):
                row.append(round(float(fc_arr[i, j]), 6))
            fc_rows.append(row)
        fc_table = make_table("VECM Forecast", ["Step"] + names, fc_rows)

        # Cointegrating vectors
        progress_callback("Extracting cointegrating vectors", 70)
        beta = fit.beta  # shape (k, r)
        beta_arr = np.asarray(beta).astype(float).copy()
        alpha = fit.alpha  # shape (k, r)
        alpha_arr = np.asarray(alpha).astype(float).copy()

        # Normalize to Phillips triangular form: divide each
        # cointegrating vector by its first nonzero coefficient so that
        # β[0, j] = 1 (or β[p, j] = 1 for the first nonzero index p).
        # Simultaneously multiply α's j-th column by the same scalar so
        # that the product α β' (which drives the error-correction
        # dynamics) is unchanged. Without this normalization the scales
        # of β and α are arbitrary and user-facing numbers change
        # across re-fits.
        for j in range(r):
            # Find first coefficient with meaningful magnitude to use
            # as the normalization pivot. Prefer index 0 (user's first
            # selected series); fall back to whichever index has the
            # largest absolute value if index 0 is near zero.
            pivot_idx = 0
            if abs(beta_arr[pivot_idx, j]) < 1e-10:
                pivot_idx = int(np.argmax(np.abs(beta_arr[:, j])))
                if abs(beta_arr[pivot_idx, j]) < 1e-10:
                    continue  # degenerate column; leave as-is
            scale = beta_arr[pivot_idx, j]
            beta_arr[:, j] = beta_arr[:, j] / scale
            alpha_arr[:, j] = alpha_arr[:, j] * scale

        coint_rows = []
        for j in range(r):
            row = [f"Vector {j + 1}"]
            for i in range(k):
                row.append(round(float(beta_arr[i, j]), 6))
            coint_rows.append(row)
        coint_table = make_table(
            "Cointegrating Vectors (beta)",
            ["Vector"] + names,
            coint_rows,
        )
        alpha_rows = []
        for i in range(k):
            row = [names[i]]
            for j in range(r):
                row.append(round(float(alpha_arr[i, j]), 6))
            alpha_rows.append(row)
        alpha_table = make_table(
            "Adjustment Coefficients (alpha)",
            ["Variable"] + [f"Coint. Eq. {j + 1}" for j in range(r)],
            alpha_rows,
        )

        # Model summary
        progress_callback("Building output", 85)
        summary_rows = [
            ["Lag Order (lagged differences)", p],
            ["Cointegration Rank", r],
            ["Variables", k],
            ["Deterministic", deterministic],
            ["Observations (effective)", n - p - 1],
            ["Forecast Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Error correction terms
        ec_rows = []
        try:
            resid = fit.resid
            resid_arr = resid.values if hasattr(resid, 'values') else np.asarray(resid)
            for j in range(k):
                col_resid = resid_arr[:, j]
                ec_rows.append([
                    names[j],
                    round(float(np.mean(col_resid)), 6),
                    round(float(np.std(col_resid, ddof=1)), 6),
                ])
        except Exception:
            pass
        if ec_rows:
            ec_table = make_table(
                "Residual Summary",
                ["Equation", "Mean", "Std Dev"],
                ec_rows,
            )
        else:
            ec_table = None

        # Plain English
        plain = (
            f"VECM fitted to {k} series ({', '.join(names)}) with {p} lagged difference(s) "
            f"and {r} cointegrating relation(s). "
        )
        if r > 0:
            plain += (
                f"The {r} cointegrating vector(s) capture long-run equilibrium relationships. "
                "Deviations from equilibrium are corrected via the adjustment coefficients (alpha)."
            )
        plain += f" {horizon}-step forecast produced."

        charting = (
            "Multi-panel line chart showing each variable with forecasts. "
            "Separate panel showing the error correction term(s) over time."
        )

        progress_callback("Done", 100)

        tables = [fc_table, summary_table, coint_table, alpha_table]
        if ec_table:
            tables.append(ec_table)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "lag_order": p,
                "coint_rank": r,
                "n_variables": k,
                "deterministic": deterministic,
                "horizon": horizon,
                "variable_names": names,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"VECM failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Provide at least 2 series.",
                "Check that series are I(1) (non-stationary in levels, stationary in differences).",
                "Try adjusting the cointegration rank or lag order.",
                "If no cointegration exists, use a VAR model in differences instead.",
            ],
        )
