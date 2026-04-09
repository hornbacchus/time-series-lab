"""
Johansen Cointegration Test for Time Series Lab.

Tests for the number of cointegrating relations among 2+ I(1) time series
using the Johansen trace and maximum eigenvalue statistics.
"""

import numpy as np
import warnings as _warnings
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen, select_order

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Johansen cointegration test on 2+ series.

    Parameters (via ctx.params)
    ---------------------------
    lag : int, optional
        Number of lagged differences (k_ar_diff). If omitted, auto-selected.
    max_lag : int, optional
        Maximum lag for automatic selection. Default depends on preset.
    det_order : int, optional
        Deterministic term: -1 (no deterministic), 0 (constant in coint eq),
        1 (linear trend in coint eq). Default 0.
    significance_level : float, optional
        Threshold for rank determination. Default 0.05.
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
        for col in range(k):
            nan_idx = np.where(np.isnan(stacked[:, col]))[0]
            valid_idx = np.where(~np.isnan(stacked[:, col]))[0]
            if len(nan_idx) > 0 and len(valid_idx) >= 2:
                stacked[nan_idx, col] = np.interp(nan_idx, valid_idx, stacked[valid_idx, col])
                warn_list.append(f"'{names[col]}': {len(nan_idx)} NaN values interpolated.")

        mask = np.all(~np.isnan(stacked), axis=1)
        stacked = stacked[mask]
        n = stacked.shape[0]

        if n < 3 * k + 10:
            return make_error_response(
                ctx,
                f"Too few observations ({n}) for Johansen test with {k} variables.",
                error_fixes=["Provide longer series."],
            )

        det_order = int(ctx.get_param("det_order", 0))
        significance = ctx.get_param("significance_level", 0.05)

        # Lag selection
        progress_callback("Selecting lag order", 15)

        preset_max = {"Fast": 4, "Balanced": 8, "Thorough": 12}
        max_lag = int(ctx.get_param("max_lag", preset_max.get(ctx.preset, 8)))
        max_lag = min(max_lag, n // (2 * k) - 1, n // 4)
        max_lag = max(max_lag, 1)

        fixed_lag = ctx.get_param("lag")
        if fixed_lag is not None:
            p = int(fixed_lag)
        else:
            df = pd.DataFrame(stacked, columns=names)
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                try:
                    det_map = {-1: "n", 0: "ci", 1: "li"}
                    order_result = select_order(df, maxlags=max_lag, deterministic=det_map.get(det_order, "ci"))
                    p = order_result.aic
                    if p == 0:
                        p = 1
                except Exception:
                    p = min(2, max_lag)
                    warn_list.append(f"Automatic lag selection failed. Using p={p}.")

        progress_callback("Running Johansen test", 30)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            result = coint_johansen(stacked, det_order=det_order, k_ar_diff=p)

        progress_callback("Building output", 65)

        # Trace test results
        trace_stats = result.lr1       # trace statistics
        trace_cvs = result.cvt         # critical values: columns = 90%, 95%, 99%
        trace_rows = []
        determined_rank_trace = 0

        cv_labels = ["90%", "95%", "99%"]
        # Determine significance column index based on significance_level
        if significance <= 0.01:
            sig_col = 2  # 99%
        elif significance <= 0.05:
            sig_col = 1  # 95%
        else:
            sig_col = 0  # 90%

        for i in range(k):
            h0 = f"r <= {i}"
            stat = float(trace_stats[i])
            cv90 = float(trace_cvs[i, 0])
            cv95 = float(trace_cvs[i, 1])
            cv99 = float(trace_cvs[i, 2])
            reject = stat > trace_cvs[i, sig_col]
            if reject and i >= determined_rank_trace:
                determined_rank_trace = i + 1
            trace_rows.append([
                h0, round(stat, 4), round(cv90, 4), round(cv95, 4), round(cv99, 4),
                "Reject" if reject else "Fail to Reject"
            ])

        trace_table = make_table(
            "Trace Test",
            ["H0", "Trace Stat", "CV 90%", "CV 95%", "CV 99%", "Decision"],
            trace_rows,
        )

        # Max Eigenvalue test results
        max_eig_stats = result.lr2
        max_eig_cvs = result.cvm
        eig_rows = []
        determined_rank_eig = 0

        for i in range(k):
            h0 = f"r <= {i}"
            stat = float(max_eig_stats[i])
            cv90 = float(max_eig_cvs[i, 0])
            cv95 = float(max_eig_cvs[i, 1])
            cv99 = float(max_eig_cvs[i, 2])
            reject = stat > max_eig_cvs[i, sig_col]
            if reject and i >= determined_rank_eig:
                determined_rank_eig = i + 1
            eig_rows.append([
                h0, round(stat, 4), round(cv90, 4), round(cv95, 4), round(cv99, 4),
                "Reject" if reject else "Fail to Reject"
            ])

        eig_table = make_table(
            "Maximum Eigenvalue Test",
            ["H0", "Max Eig Stat", "CV 90%", "CV 95%", "CV 99%", "Decision"],
            eig_rows,
        )

        # Eigenvalues
        eigenvalues = result.eig
        eig_val_rows = []
        for i, ev in enumerate(eigenvalues):
            eig_val_rows.append([i + 1, round(float(ev), 6)])
        eig_val_table = make_table("Eigenvalues", ["#", "Eigenvalue"], eig_val_rows)

        # Cointegrating vectors (eigenvectors)
        evecs = result.evec  # shape (k, k)
        evec_rows = []
        for j in range(k):
            row = [f"Vector {j + 1}"]
            for i in range(k):
                row.append(round(float(evecs[i, j]), 6))
            evec_rows.append(row)
        evec_table = make_table(
            "Cointegrating Vectors (Eigenvectors)",
            ["Vector"] + names,
            evec_rows,
        )

        # Summary
        summary_rows = [
            ["Variables", k],
            ["Variable Names", ", ".join(names)],
            ["Lag Order (k_ar_diff)", p],
            ["Deterministic Order", det_order],
            ["Observations", n],
            ["Trace Test Rank", determined_rank_trace],
            ["Max Eigenvalue Test Rank", determined_rank_eig],
            ["Significance Level Used", significance],
        ]
        summary_table = make_table("Summary", ["Field", "Value"], summary_rows)

        # Plain English
        if determined_rank_trace == determined_rank_eig:
            rank_msg = (
                f"Both trace and max-eigenvalue tests indicate {determined_rank_trace} "
                f"cointegrating relation(s) among the {k} series."
            )
        else:
            rank_msg = (
                f"Trace test indicates {determined_rank_trace} cointegrating relation(s), "
                f"while max-eigenvalue test indicates {determined_rank_eig}. "
                "The results are not unanimous; consider the trace test as more robust."
            )

        plain = (
            f"Johansen cointegration test on {k} series ({', '.join(names)}), "
            f"lag order {p}. {rank_msg}"
        )

        if determined_rank_trace == 0 and determined_rank_eig == 0:
            plain += (
                " No cointegration detected. The series do not share a long-run equilibrium. "
                "A VAR model in first differences may be more appropriate."
            )
        elif determined_rank_trace >= k - 1:
            plain += (
                " High cointegration rank suggests the series may all be stationary. "
                "Consider a VAR in levels rather than a VECM."
            )
        else:
            plain += (
                " Cointegration implies a long-run equilibrium relationship. "
                "A VECM (Vector Error Correction Model) is recommended for modelling."
            )

        charting = (
            "Table display with color coding for reject/fail-to-reject. "
            "Bar chart comparing test statistics to critical values at each rank."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[summary_table, trace_table, eig_table, eig_val_table, evec_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "n_variables": k,
                "variable_names": names,
                "lag_order": p,
                "det_order": det_order,
                "trace_rank": determined_rank_trace,
                "max_eig_rank": determined_rank_eig,
                "significance_level": significance,
                "eigenvalues": [round(float(ev), 6) for ev in eigenvalues],
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Johansen test failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Provide at least 2 series.",
                "Series should be I(1) for meaningful cointegration testing.",
                "Try a different lag order or det_order.",
            ],
        )
